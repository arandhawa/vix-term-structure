# TODO Logging and Tests are essential!

import logging
from typing import Tuple, Iterator

import pandas as pd
import numpy as np
import tensorflow.contrib.keras as keras

import vixstructure.models as models


def get_model(hidden_layers, past_days, days_to_future):
    model = models.naive_fully_connected(hidden_layers, past_days, days_to_future)
    sgd = keras.optimizers.SGD(0.01)
    model.compile(sgd, keras.losses.mean_squared_error, metrics=['accuracy'])
    return model


def data_generator(data: np.ndarray, past_days: int, days_to_future: int
                   ) -> Iterator[np.ndarray]:
    # TODO Specify batch size.
    while True:  # Generator should loop indefinitely.
        for i in range(past_days, len(data) - days_to_future):
            # Expand dimension --> batch size of 1
            yield (np.expand_dims(data[i-past_days:i], axis=0),
                   np.expand_dims(data[i+days_to_future,1:], axis=0))


def get_data(past_days: int, days_to_future: int,
             split: float=0.80, min_index: int=None, max_index: int=None,
             ) -> Tuple[
                    Tuple[int, Iterator[np.ndarray]],
                    Tuple[int, Iterator[np.ndarray]]]:
    """
    Get two generators, both which loop over their data indefinitely. The first one
    is for training, the second one for validation. Also returns the number of
    unique data samples until the generator starts the next loop.
    :param past_days:
    :param days_to_future:
    :param split: Fraction at which to split the data into training and test set.
    :param min_index: If you don't want to use the whole data (maybe because you also
                      need a test set) you can specify a range with ``min_index`` and
                      ``max_index``. Is ignored when greater than the data length.
    :param max_index: See ``min_index``.
    :return: A tuple of two tuples:
             1. tuple: (number of unique training samples, training data generator)
             2. tuple: (number of unique validation samples, validation data generator)
    """
    # TODO Think about a way to shuffle the data
    assert 0. < split < 1.
    if min_index: assert min_index >= 0
    if max_index: assert min_index < max_index
    # Load and merge the data.
    xm_settle = pd.read_csv("data/8_m_settle.csv", usecols=range(1, 10), dtype=np.float32,
                            parse_dates=[0], header=0, index_col=0, na_values=0)
    vix = pd.read_csv("data/vix.csv", usecols=[0,5], parse_dates=[0], header=0, index_col=0,
                      na_values=["null", 0], dtype = np.float32)
    training = pd.merge(vix, xm_settle, left_index=True, right_index=True)
    # Normalize the data
    mean = training.mean()
    ptp = training.max() - training.min()
    training = (training - mean) / ptp
    # The training data has now the shape (N, 9).
    if min_index and min_index >= len(training):
        logging.warning(f"min_index is greater than length of data {len(training)}. Ignore.")
        min_index = None
    if max_index and max_index >= len(training):
        logging.warning(f"max_index is greater than length of data {len(training)}. Ignore.")
        max_index = None
    # Fill the NaN values and extract a numpy array.
    training = training.fillna(0).values[min_index:max_index]
    split_index = int(split * len(training))
    # Split data into validation set and training set.
    validation = training[split_index:]
    nr_samples_validation = len(validation) - past_days - days_to_future
    assert nr_samples_validation > 0
    training = training[:split_index]
    nr_samples_training = len(training) - past_days - days_to_future
    assert nr_samples_training > 0
    return ((nr_samples_training, data_generator(training, past_days, days_to_future)),
            (nr_samples_validation, data_generator(validation, past_days, days_to_future)))


def train(hidden_layers, past_days, days_to_future, verbose=1):
    repr_string = f"{hidden_layers}_{past_days}_{days_to_future}"
    testset, validationset = get_data(past_days, days_to_future)
    model = get_model(hidden_layers, past_days, days_to_future)
    history = model.fit_generator(testset[1], testset[0], epochs=100, verbose=verbose,
                                  validation_data=validationset[1], validation_steps=validationset[0],
                                  callbacks=[keras.callbacks.CSVLogger(f"training_{repr_string}.log")])
    model.save(f"naive_{repr_string}.hdf5")
    return history


if __name__ == "__main__":
    for i in range(1, 11):
        print(f"Training with {i} hidden layer.")
        train(i, 7, 7, 2)
