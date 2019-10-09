from displayarray.effects import crop, lens
from displayarray import display
from examples.videos import test_video

# Move the mouse to move where the crop is from on the original image

display(test_video) \
    .add_callback(crop.Crop()) \
    .add_callback(lens.Barrel().enable_mouse_control()) \
    .block()
