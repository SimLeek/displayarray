from displayarray import display
import numpy as np

arr = np.random.normal(0.5, 0.1, (100, 100, 5))

with display(arr) as displayer:
    while displayer:
        arr[:] += np.random.normal(0.001, 0.0005, (100, 100, 5))
        arr %= 1.0
