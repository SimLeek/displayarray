from displayarray import display
import numpy as np

arr = np.random.randint(0, 10, (1000, 900), dtype=np.uint8)
arr2 = np.random.randint(240, 255, (400, 500, 3), dtype=np.uint8)
arr3 = np.random.randint(127, 137, (250, 150, 3), dtype=np.uint8)
arr4 = np.random.randint(45, 55, (128, 28, 3), dtype=np.uint8)
arr5 = np.random.randint(190, 200, (32, 64, 3), dtype=np.uint8)


def fix_arr_cv(arr_in):
    arr_in[:] += np.random.randint(0, 2, arr_in.shape, dtype=np.uint8)
    arr_in %= 255


display(*[arr, arr2, arr3, arr4, arr5], callbacks=fix_arr_cv, blocking=True)
