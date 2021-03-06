#! /usr/bin/env python
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import tensorflow as tf
import numpy as np
import os
import time
import datetime
import data_helpers
from text_cnn import TextCNN
from tensorflow.contrib import learn
import yaml
import math
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, make_scorer
# Parameters
# ==================================================

# Data loading params
tf.flags.DEFINE_float("dev_sample_percentage", .1, "Percentage of the training data to use for validation")
tf.flags.DEFINE_string("traindir", None, "Train directory")
tf.flags.DEFINE_string("exp_name", 'newest', "Experiment name, use to name the checkpoint (tensorboard)")

# Model Hyperparameters
tf.flags.DEFINE_boolean("trainVocab", True, "Use existing vocabulary")

tf.flags.DEFINE_boolean("pretrain", True, "Enable/disable the word embedding (default: True)")
tf.flags.DEFINE_string("pretrain_data", None, "use what word embedding data")

tf.flags.DEFINE_integer("embedding_dim", 128, "Dimensionality of character embedding (default: 128)")
tf.flags.DEFINE_string("filter_sizes", "3,4,5", "Comma-separated filter sizes (default: '3,4,5')")
#baseline config
tf.flags.DEFINE_integer("num_filters", 100, "Number of filters per filter size (default: 128)")
tf.flags.DEFINE_float("dropout_keep_prob", 0.5, "Dropout keep probability (default: 0.5)")
tf.flags.DEFINE_float("l2_reg_lambda", 3, "L2 regularization lambda (default: 0.0)")
tf.flags.DEFINE_float("l1_reg_lambda", 0.0, "L1 regularization lambda (default: 0.0)")
tf.flags.DEFINE_integer("batch_size", 40, "Batch Size (default: 64)")
tf.flags.DEFINE_integer("num_epochs", 15, "Number of training epochs (default: 200)")

# Training parameters
tf.flags.DEFINE_integer("evaluate_every", 100, "Evaluate model on dev set after this many steps (default: 100)")
tf.flags.DEFINE_integer("checkpoint_every", 10, "Save model after this many steps (default: 100)")
tf.flags.DEFINE_integer("num_checkpoints", 5, "Number of checkpoints to store (default: 5)")
# Misc Parameters
tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")
tf.flags.DEFINE_float("decay_coefficient", 2.5, "Decay coefficient (default: 2.5)")

FLAGS = tf.flags.FLAGS
FLAGS._parse_flags()
print("\nParameters:")
for attr, value in sorted(FLAGS.__flags.items()):
    print("{}={}".format(attr.upper(), value))
print("")

with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

if FLAGS.pretrain:
    embedding_name = FLAGS.pretrain_data
    print 'use', embedding_name, 'as pretrain word embedding'
    embedding_dimension = cfg['word_embeddings'][embedding_name]['dimension']
else:
    embedding_dimension = FLAGS.embedding_dim

# Data Preparation
# ==================================================

# Load data
from knx.util.logging import Timing
with Timing("Loading data..."):
    datasets = None
    x_text, y = data_helpers.load_data_and_labels(FLAGS.traindir, used_onehot=True)

# Build vocabulary
import cPickle as pkl
if FLAGS.trainVocab:
    with Timing("Building vocabulary...\n"):
        maxlen = 0
        for e in x_text:
            maxlen = max(maxlen, len(set(e.split())))
        print 'sequence size =', maxlen

        vocab_processor = learn.preprocessing.VocabularyProcessor(maxlen)
        x = np.array(list(vocab_processor.fit_transform(x_text)))

        with open('vocab.pkl', "wb") as fp:
            pkl.dump(vocab_processor, fp)
            pkl.dump(x, fp)
            pkl.dump(maxlen, fp)
else:
    with Timing('Loading ...\n'):
        with open('vocab.pkl', "rb") as fp:
            vocab_processor = pkl.load(fp)
            x = pkl.load(fp)
            maxlen = pkl.load(fp)

# Randomly shuffle data
np.random.seed(10)
shuffle_indices = np.random.permutation(np.arange(len(y)))
x_shuffled = x[shuffle_indices]
y_shuffled = y[shuffle_indices]

# Split train/test set
# TODO: This is very crude, should use cross-validation
dev_sample_index = -1 * int(FLAGS.dev_sample_percentage * float(len(y)))
x_train, x_dev = x_shuffled[:dev_sample_index], x_shuffled[dev_sample_index:]
y_train, y_dev = y_shuffled[:dev_sample_index], y_shuffled[dev_sample_index:]
print("Vocabulary Size: {:d}".format(len(vocab_processor.vocabulary_)))
print("Train/Dev split: {:d}/{:d}".format(len(y_train), len(y_dev)))
print 'Dev: ', len(x_dev), len(y_dev)

classes = ['Adult', 'Car_accident', 'Death_tragedy', 'Hate_speech', 'Religion', 'Safe']
with Timing('Creating dev set ...\n'):
    with open('dev_set.pkl', "wb") as fp:
        y_dev = [classes[np.argmax(e)] for e in y_dev]
        pkl.dump(x_dev, fp)
        pkl.dump(y_dev, fp)

# Training
# ==================================================

with tf.Graph().as_default():
    session_conf = tf.ConfigProto(
      allow_soft_placement=FLAGS.allow_soft_placement)
    sess = tf.Session(config=session_conf)
    with sess.as_default():
        cnn = TextCNN(
            sequence_length=x_train.shape[1],
            num_classes=len(classes),
            vocab_size=len(vocab_processor.vocabulary_),
            embedding_size=embedding_dimension,
            filter_sizes=list(map(int, FLAGS.filter_sizes.split(","))),
            num_filters=FLAGS.num_filters,
            l1=FLAGS.l1_reg_lambda,
            l2=FLAGS.l2_reg_lambda)

        cnn.build_graph()

        # Define Training procedure
        # global_step = tf.Variable(0, name="global_step", trainable=False)
        # optimizer = tf.train.AdamOptimizer(cnn.learning_rate)
        # grads_and_vars = optimizer.compute_gradients(cnn.loss)
        # train_op = optimizer.apply_gradients(grads_and_vars, global_step=global_step)

        # Keep track of gradient values and sparsity (optional)
        # grad_summaries = []
        # for g, v in grads_and_vars:
        #     if g is not None:
        #         grad_hist_summary = tf.summary.histogram("{}/grad/hist".format(v.name), g)
        #         sparsity_summary = tf.summary.scalar("{}/grad/sparsity".format(v.name), tf.nn.zero_fraction(g))
        #         grad_summaries.append(grad_hist_summary)
        #         grad_summaries.append(sparsity_summary)
        # grad_summaries_merged = tf.summary.merge(grad_summaries)

        # Output directory for models and summaries
        # timestamp = str(int(time.time()))
        # timestamp = str(int(time.time()))
        #
        # # Summaries for loss and accuracy
        # loss_summary = tf.summary.scalar("loss", cnn.loss)
        # acc_summary = tf.summary.scalar("accuracy", cnn.accuracy)
        #
        # # Train Summaries
        # train_summary_op = tf.summary.merge([loss_summary, acc_summary, grad_summaries_merged])

        # # Dev summaries
        # dev_summary_op = tf.summary.merge([loss_summary, acc_summary])

        out_dir = os.path.abspath(os.path.join(os.path.curdir, "runs", FLAGS.exp_name))
        print("Writing to {}\n".format(out_dir))

        train_summary_dir = os.path.join(out_dir, "summaries", "train")
        train_summary_writer = tf.summary.FileWriter(train_summary_dir, sess.graph)

        # dev_summary_dir = os.path.join(out_dir, "summaries", "dev")
        # dev_summary_writer = tf.summary.FileWriter(dev_summary_dir, sess.graph)

        # Checkpoint directory. Tensorflow assumes this directory already exists so we need to create it
        checkpoint_dir = os.path.abspath(os.path.join(out_dir, "checkpoints"))
        checkpoint_prefix = os.path.join(checkpoint_dir, "model")
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
        saver = tf.train.Saver(tf.global_variables(), max_to_keep=FLAGS.num_checkpoints)

        # # Write vocabulary
        # vocab_processor.save(os.path.join(out_dir, "vocab"))

        # Initialize all variables
        sess.run(tf.global_variables_initializer())
        if FLAGS.pretrain:
            vocabulary = vocab_processor.vocabulary_
            initW = None
            if embedding_name == 'word2vec':
                # load embedding vectors from the word2vec
                print("Load word2vec file {}".format(cfg['word_embeddings']['word2vec']['path']))
                initW = data_helpers.load_embedding_vectors_word2vec(vocabulary,
                                                                     cfg['word_embeddings']['word2vec']['path'],
                                                                     cfg['word_embeddings']['word2vec']['binary'])
                print("word2vec file has been loaded")
            elif embedding_name == 'glove':
                # load embedding vectors from the glove
                print("Load glove file {}".format(cfg['word_embeddings']['glove']['path']))
                initW = data_helpers.load_embedding_vectors_glove(vocabulary,
                                                                  cfg['word_embeddings']['glove']['path'],
                                                                  embedding_dimension)
                print("glove file has been loaded\n")
            sess.run(cnn.W.assign(initW))

        def train_step(x_batch, y_batch, learning_rate, step):
            """
            A single training step
            """
            feed_dict = {
              cnn.input_x: x_batch,
              cnn.input_y: y_batch,
              cnn.dropout_keep_prob: FLAGS.dropout_keep_prob,
              cnn.learning_rate: learning_rate
            }
            _, summaries, loss, accuracy = sess.run(
                        [cnn.optimizer, cnn.summary_op, cnn.loss, cnn.accuracy], feed_dict)

            time_str = datetime.datetime.now().isoformat()
            print("{}: step {}, loss {:g}, acc {:g}, learning_rate {:g}"
                        .format(time_str, step, loss, accuracy, learning_rate))
            train_summary_writer.add_summary(summaries, step)

        # def dev_step(x_batch, y_batch, writer=None):
        #     """
        #     Evaluates model on a dev set
        #     """
        #     batches = data_helpers.batch_iter(x_batch, FLAGS.batch_size, 1, shuffle=False)
        #     # Collect the predictions here
        #     all_predictions = []
        #     all_probabilities = None
        #
        #     feed_dict = {
        #         cnn.input_x: x_batch,
        #         # cnn.input_y: y_batch,
        #         cnn.dropout_keep_prob: 1.0
        #     }
        #
        #     # avg_loss = 0
        #     for x_dev_batch in batches:
        #         preds = sess.run([cnn.predictions], feed_dict)
        #         all_predictions = np.concatenate([all_predictions, preds])
        #         # avg_loss += loss
        #     # avg_loss /= len(batches)
        #
        #     precision = precision_score(y_batch, all_predictions, pos_label=None, average='macro')
        #     # print 'precision: {0}, avg_loss: {1}\n'.format(precision, avg_loss)
        #     print 'precision: {0}\n'.format(precision)
        #     # time_str = datetime.datetime.now().isoformat()
        #     # print("{}: step {}, loss {:g}, acc {:g}".format(time_str, step, loss, accuracy))
        #     # if writer:
        #     #     writer.add_summary(summaries, step)

        # Generate batches
        batches = data_helpers.batch_iter(
            list(zip(x_train, y_train)), FLAGS.batch_size, FLAGS.num_epochs)
        # It uses dynamic learning rate with a high value at the beginning to speed up the training
        max_learning_rate = 0.005
        min_learning_rate = 0.0001
        decay_speed = FLAGS.decay_coefficient*len(y_train)/FLAGS.batch_size
        # Training loop. For each batch...
        counter = 0
        with Timing('Training loop. For each batch...\n'):
            for current_step, batch in enumerate(batches):
                learning_rate = min_learning_rate + (max_learning_rate - min_learning_rate) * math.exp(-counter/decay_speed)
                counter += 1
                x_batch, y_batch = zip(*batch)
                train_step(x_batch, y_batch, learning_rate, step=current_step)
                # if current_step % FLAGS.evaluate_every == 0:
                #     print("\nEvaluation:")
                #     dev_step(x_dev, y_dev)
                #     print("")

        # with Timing('Training set: ...\n'):
        #     dev_step(x_train, y_train)

        # with Timing('Dev set: ...\n'):
        #     dev_step(x_dev, y_dev)

        path = saver.save(sess, checkpoint_prefix)
        print("Saved model checkpoint to {}\n".format(path))