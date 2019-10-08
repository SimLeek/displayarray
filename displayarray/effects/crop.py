import numpy as np
from ..input import mouse_loop
import cv2


class Crop(object):
    def __init__(self, output_size=(64, 64, 3), center=None):
        self.output_size = output_size
        self.center = center
        if center:
            self.odd = (center[0] % 2, center[1] % 2)
        self.input_size = None

    def __call__(self, arr):
        if self.center is None:
            self.input_size = arr.shape
            self.center = [int(arr.shape[x]) // 2 for x in range(arr.ndim)]
            self.odd = [self.center[x] % 2 for x in range(arr.ndim)]
        center = self.center.copy()  # stop opencv from thread breaking us
        top_left_get = [min(max(0, center[x] - self.output_size[x] // 2), arr.shape[x] - 1) for x in range(arr.ndim)]
        bottom_right_get = [min(max(0, center[x] + self.output_size[x] // 2 + self.odd[x]), arr.shape[x])
                            for x in range(arr.ndim)]

        top_left_put = [min(max(0, -(bottom_right_get[x] - center[x] - self.output_size[x] // 2)), self.output_size[x])
                        for x in range(arr.ndim)]
        bottom_right_put = [
            min(max(0, -(top_left_get[x] - center[x] - self.output_size[x] // 2 - self.odd[x])), self.output_size[x])
            for x in range(arr.ndim)]
        get_slices = [slice(x1, x2) for x1, x2 in zip(top_left_get, bottom_right_get)]
        get_slices = tuple(get_slices)
        put_slices = [slice(x1, x2) for x1, x2 in zip(top_left_put, bottom_right_put)]
        put_slices = tuple(put_slices)
        out_array = np.zeros(self.output_size)
        out_array[put_slices] = arr[get_slices]
        return out_array.astype(arr.dtype)

    def enable_mouse_control(self):
        @mouse_loop
        def m_loop(me):
            if self.center is None:
                self.center = [0, 0, 1]
            self.center[:] = [int(me.y / self.output_size[0] * self.input_size[0]),
                              int(me.x / self.output_size[1] * self.input_size[1]),
                              1]

        self.mouse_control = m_loop
