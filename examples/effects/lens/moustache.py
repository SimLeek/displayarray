from displayarray.effects import lens
from displayarray import display
from examples.videos import test_video

m = lens.Mustache()
m.enable_mouse_control()
display(test_video, callbacks=m, blocking=True)
