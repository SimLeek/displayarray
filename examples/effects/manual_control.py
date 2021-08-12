from displayarray.effects import crop, lens
from displayarray import display
from examples.videos import test_video
import math as m

# Move the mouse to center the image, scroll to increase/decrease barrel, ctrl+scroll to increase/decrease zoom

pre_crop_callback = crop.Crop(output_size=(480, 640, 3)).enable_mouse_control()
lens_callback = lens.BarrelPyTorch()
post_crop_callback = crop.Crop(output_size=(256, 256, 3)).enable_mouse_control()

d = (
    display(0, size=(99999, 99999))
    .add_callback(pre_crop_callback)
    .add_callback(lens_callback)
    .add_callback(post_crop_callback)
    .wait_for_init()
)

i = 0
while d:
    if len(d.frames) > 0:
        i += 1
        frame = next(iter(d.frames.values()))
        center_sin = [(m.sin(m.pi * (i / 70.0))), (m.cos(m.pi * (i / 120.0)))]
        pre_crop_callback.center = [
            center_sin[0] * 720 / 2 + 720 / 2,
            center_sin[1] * 1280 / 2 + 1280 / 2,
        ]
        lens_callback.center = [
            center_sin[0] * 480 / 2 + 480 / 2,
            center_sin[1] * 640 / 2 + 640 / 2,
        ]
        post_crop_callback.center = [480 / 2, 640 / 2]
        lens_callback.zoom = m.sin(m.pi * ((i + 25) / 50.0)) + 1.01
        lens_callback.barrel_power = m.sin((m.pi * (i + 33) / 25)) + 1.5
