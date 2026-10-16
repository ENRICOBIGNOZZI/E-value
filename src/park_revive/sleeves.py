import numpy as np


def sleeve_weights(values):
    centered = values-values.mean(axis=0)
    return centered/np.maximum(np.abs(centered).sum(axis=0), 1e-12)
