from displayarray import display
import numpy as np


def black_and_white(arr):
    return (np.sum(arr, axis=-1) / 3).astype(np.uint8)


import time

t0 = t1 = time.time()
for up in display(0, size=(1, 1), callbacks=black_and_white):
    if up:
        t1 = time.time()
        print(1.0 / (t1 - t0))
        t0 = t1
