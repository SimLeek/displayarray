from displayarray import display
import numpy as np


def black_and_white(arr):
    return (np.sum(arr, axis=-1) / 3).astype(np.uint8)


display(0, callbacks=black_and_white, blocking=True)