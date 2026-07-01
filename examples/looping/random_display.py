from displayarray import display
import numpy as np

arr = np.random.normal(0.5, 0.1, (149, 199))
arr2 = np.random.normal(0.5, 0.1, (212, 282))
arr3 = np.random.normal(0.5, 0.1, (1000, 800))

arr4 = np.random.normal(0.5, 0.1, (105, 140))
arr5 = np.random.normal(0.5, 0.1, (74, 98))
arr6 = np.random.normal(0.5, 0.1, (52, 69))

with display(arr) as displayer:
    while displayer:
        arr[:] += np.random.normal(0.001, 0.0005, (149, 199))
        arr %= 1.0
        arr2[:] += np.random.normal(0.002, 0.0005, (212, 282))
        arr2 %= 1.0
        arr3[:] -= np.random.normal(0.001, 0.0005, (1000, 800))
        arr3 %= 1.0

        arr4[:] += np.random.normal(0.001, 0.0005, (105, 140))
        arr4 %= 1.0
        arr5[:] += np.random.normal(0.002, 0.0005, (74, 98))
        arr5 %= 1.0
        arr6[:] -= np.random.normal(0.001, 0.0005, (52, 69))
        arr6 %= 1.0


        displayer.update([arr2, arr3, arr4, arr5, arr6], ['2', '3', '4', '5', '6'])
        # or, for one frame: displayer.update(arr2, '2')
