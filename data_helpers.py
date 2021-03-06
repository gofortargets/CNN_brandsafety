import numpy as np
import re
from sklearn.datasets import fetch_20newsgroups
from sklearn.datasets import load_files

def batch_iter(data, batch_size, num_epochs, shuffle=True):
    """
    Generates a batch iterator for a dataset.
    """
    data = np.array(data)
    data_size = len(data)
    num_batches_per_epoch = int((len(data)-1)/batch_size) + 1
    for epoch in range(num_epochs):
        # Shuffle the data at each epoch
        if shuffle:
            shuffle_indices = np.random.permutation(np.arange(data_size))
            shuffled_data = data[shuffle_indices]
        else:
            shuffled_data = data
        for batch_num in range(num_batches_per_epoch):
            start_index = batch_num * batch_size
            end_index = min((batch_num + 1) * batch_size, data_size)
            yield shuffled_data[start_index:end_index]

from os.path import isfile, join
from os import listdir

def load_data_and_labels(traindir, used_onehot=True, return_filenames=False):
    """
    Loads MR polarity data from files, splits the data into words and generates labels.
    Returns split sentences and labels.
    """
    classes = ['Adult', 'Car_accident', 'Death_tragedy', 'Hate_speech', 'Religion', 'Safe']
    # Load data from files
    x_text = []
    labels = []
    LABEL_SEPARATOR = '#'
    train_file_list = [f for f in listdir(traindir) if isfile(join(traindir, f))]
    for true_filename in train_file_list:
        file_path = join(traindir, true_filename)
        f_reader = open(file_path, "r")
        content = f_reader.read()
        x_text.append(content)

        label = true_filename[0:true_filename.find(LABEL_SEPARATOR)]
        if used_onehot:
            index = classes.index(label)
            onehot_vec = np.zeros(len(classes))
            onehot_vec[index] = 1
            labels.append(onehot_vec)
        else:
            labels.append(label)

    labels = np.array(labels)
    if return_filenames:
        return x_text, labels, train_file_list
    else:
        return x_text, labels

import gensim
def load_embedding_vectors_word2vec(vocabulary, filename, randomly):
    if randomly:
        embedding_vectors = np.random.uniform(-0.25, 0.25, (len(vocabulary), 300))
    else:
        embedding_vectors = np.zeros((len(vocabulary), 300))
        
    vocab_dict = vocabulary._mapping
    sorted_vocab = sorted(vocab_dict.items(), key=lambda x: x[1])
    vocabulary = list(list(zip(*sorted_vocab))[0])
    model = gensim.models.KeyedVectors.load_word2vec_format(filename, binary=True)
    for i, e in enumerate(vocabulary):
        try:
            embedding_vectors[i] = model[e]
        except:
            continue
    return embedding_vectors

def load_embedding_vectors_glove(vocabulary, filename, vector_size):
    # load embedding_vectors from the glove
    # initial matrix with random uniform
    embedding_vectors = np.zeros((len(vocabulary), 300))
    f = open(filename)
    for line in f:
        values = line.split()
        word = values[0]
        vector = np.asarray(values[1:], dtype="float32")
        idx = vocabulary.get(word)
        if idx != 0:
            embedding_vectors[idx] = vector
    f.close()
    return embedding_vectors
