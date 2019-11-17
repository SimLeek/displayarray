from displayarray.effects import crop, lens
from displayarray import display
from examples.videos import test_video

# Move the mouse to center the image, scroll to increase/decrease barrel, ctrl+scroll to increase/decrease zoom

d = (
    display(test_video)
    .add_callback(lens.BarrelPyTorch().enable_mouse_control(crop_size=(256, 256)))
    .add_callback(crop.Crop(output_size=(256, 256, 3)))
    .wait_for_init()
)

while d:
    if len(d.frames) > 0:
        pass
