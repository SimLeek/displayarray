from displayarray.effects import crop
from displayarray import display
import numpy as np

# Scroll the mouse wheel and press ctrl, alt, or shift to select which channels are displayed as red, green, or blue.
arr = np.ones((250, 250, 250))
for x in range(250):
    arr[..., x] = x / 250.0
display(arr).block()
