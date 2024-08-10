import time

from displayarray import display
import numpy as np

PI2 = 2 * np.pi
TINY_INC = 2*np.pi/50000

gen = np.random.Generator(np.random.PCG64(int(time.time()*1000000)))
arr = gen.uniform(0, PI2,(1080, 1920))
arr2 = np.zeros_like(arr, dtype=np.uint8)

def fix_arr_cv(arr_in):
    global arr
    arr[:] += gen.uniform(0, TINY_INC,(1080, 1920))
    arr[:] %= PI2
    arr_in[:] = (np.sin(arr)**1000000)*255



display( arr2, window_names=['1'], callbacks=fix_arr_cv, blocking=True)
