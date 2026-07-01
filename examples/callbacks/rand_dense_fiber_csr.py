import time
import numpy as np
from scipy.sparse import csr_matrix
from displayarray import display

PI2 = 2 * np.pi
TINY_INC = 2 * np.pi / 50000

gen = np.random.Generator(np.random.PCG64(int(time.time() * 1000000000)))
arr = gen.uniform(0, PI2, (1080, 1920, 3))


def fix_arr_cv(_):
    global arr
    arr[:] += gen.uniform(0, TINY_INC, (1080, 1920, 3))
    arr[:] %= PI2

    # Calculate the new values and find the non-zero indices
    arr_in_new = (np.sin(arr) ** 10000000) * 255
    arr_in_new = arr_in_new.astype(np.uint8)

    non_zero_mask = np.any(arr_in_new > 0, axis=2)
    row_indices, col_indices = np.nonzero(non_zero_mask)

    mode_3_fibers = []
    for i in range(len(row_indices)):
        pixel_values = arr_in_new[row_indices[i], col_indices[i], :]

        mode_3_fibers.append(pixel_values)

    # todo: create a sparse matrix class in SILi that can handle this
    arr_in_sparse = csr_matrix(
        (mode_3_fibers, (row_indices, col_indices)),
        shape=(1080, 1920), dtype=object
    )

    # Return the new CSR array
    return arr_in_sparse


# Initial call to display with arr2_sparse
arr2_sparse = fix_arr_cv(None)
display(arr2_sparse, window_names=['1'], callbacks=fix_arr_cv, blocking=True)
