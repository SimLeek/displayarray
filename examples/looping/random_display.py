from displayarray import display
import numpy as np

arr = np.random.normal(0.5, 0.1, (100, 100, 3))
arr2 = np.random.normal(0.5, 0.1, (200, 200, 3))
arr3 = np.random.normal(0.5, 0.1, (300, 300, 3))

with display(arr) as displayer:
    while displayer:
        arr[:] += np.random.normal(0.001, 0.0005, (100, 100, 3))
        arr %= 1.0
        displayer.update(arr2, '2')
        displayer.update(arr3, '3')

