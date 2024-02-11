from displayarray import display
import numpy as np

arr = np.random.normal(0.5, 0.1, (100, 100, 5))

with display(0, size=(-1,-1)) as displayer:
    while displayer:
        pass
