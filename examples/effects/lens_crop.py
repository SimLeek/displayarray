from displayarray.effects import crop, lens
from displayarray import display
from examples.videos import test_video

# Move the mouse to center the image, scroll to increase/decrease barrel, ctrl+scroll to increase/decrease zoom

d = (
    display(test_video)
    .add_callback(crop.Crop())
    .add_callback(lens.Barrel().enable_mouse_control())
    .wait_for_init()
)

while d:
    print(d.frames[0].shape)
