from displayarray.effects import lens
from displayarray import display
from examples.videos import test_video

# Move the mouse to center the image, scroll to increase/decrease barrel, ctrl+scroll to increase/decrease zoom

m = lens.Barrel(use_bleed=False)
m.enable_mouse_control()
display(test_video, callbacks=m, blocking=True)
