from displayarray import display
import numpy as np

arr = np.random.normal(0.5, 0.1, (500, 500, 3))


def fix_arr_cv(arr_in):
    arr_in[:] += np.random.normal(0.01, 0.005, (500, 500, 3))
    arr_in %= 1.0


display(arr, callbacks=fix_arr_cv, blocking=True)