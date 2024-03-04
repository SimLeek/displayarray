from displayarray import display
import numpy as np

arr = np.random.normal(0.5, 0.1, (100, 200, 3))
arr2 = np.random.normal(0.5, 0.1, (200, 300, 3))
arr3 = np.random.normal(0.5, 0.1, (300, 400, 3))

with display(arr) as displayer:
    while displayer:
        arr[:] += np.random.normal(0.001, 0.0005, (100, 200, 3))
        arr %= 1.0
        arr2[:] += np.random.normal(0.002, 0.0005, (200, 300, 3))
        arr2 %= 1.0
        arr3[:] -= np.random.normal(0.001, 0.0005, (300, 400, 3))
        arr3 %= 1.0


        displayer.update(arr2, '2')
        displayer.update(arr3, '3')

