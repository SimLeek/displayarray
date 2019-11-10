from displayarray import display
import math as m
from examples.videos import test_video


def forest_color(arr):
    forest_color.i += 1
    arr[..., 0] = (
        m.sin(forest_color.i * (2 * m.pi) * 0.4 / 360) * 255 + arr[..., 0]
    ) % 255
    arr[..., 1] = (
        m.sin((forest_color.i * (2 * m.pi) * 0.5 + 45) / 360) * 255 + arr[..., 1]
    ) % 255
    arr[..., 2] = (
        m.cos(forest_color.i * (2 * m.pi) * 0.3 / 360) * 255 + arr[..., 2]
    ) % 255


forest_color.i = 0

display(test_video, callbacks=forest_color, blocking=True, fps_limit=120)
