"""Crop any n-dimensional array."""

import numpy as np
from displayarray.input import mouse_loop


class Crop(object):
    """
    A callback class that will return the input array cropped to the output size. N-dimensional.

    >>> crop_it = Crop((2,2,2))
    >>> arr = np.ones((4,4,4))
    >>> crop_it(arr)
    array([[[1., 1.],
            [1., 1.]],
    <BLANKLINE>
           [[1., 1.],
            [1., 1.]]])

    """

    def __init__(self, output_size=(64, 64, 3), center=None):
        """Create the cropper."""
        self._output_size = None
        self._center = None
        self.odd_center = None
        self.mouse_control = None
        self.input_size = None

        self.center = center
        self.output_size = output_size

    @property
    def output_size(self):
        """Get the output size after cropping."""
        return self._output_size

    @output_size.setter
    def output_size(self, set):
        """Set what the output size will be after cropping."""
        self._output_size = set
        if self._output_size is not None:
            self._output_size = np.asarray(set)

    @property
    def center(self):
        """Get center crop position on the input."""
        return self._center

    @center.setter
    def center(self, set):
        """Set center crop position on the input."""
        self._center = set
        if self._center is not None:
            self._center = np.asarray(set)

    def __call__(self, arr):
        """Crop the input array to the specified output size. output is centered on self.center point on input."""
        self.input_size = arr.shape
        if self.center is None:
            self.center = [int(arr.shape[x]) // 2 for x in range(arr.ndim)]
        self.odd_out = np.array(
            [self.output_size[x] % 2 for x in range(len(self.output_size))]
        )
        self.odd_center = np.array(
            [self.center[x] % 2 for x in range(len(self.center))]
        )

        center = self.center.copy()  # stop opencv from thread breaking us
        top_left_get = [
            min(max(0, center[x] - self.output_size[x] // 2), arr.shape[x] - 1)
            for x in range(arr.ndim)
        ]
        bottom_right_get = [
            min(
                max(0, center[x] + self.output_size[x] // 2 + self.odd_out[x]),
                arr.shape[x],
            )
            for x in range(arr.ndim)
        ]

        top_left_put = [
            min(
                max(
                    0,
                    -(bottom_right_get[x] - center[x] - self.output_size[x] // 2)
                    + self.odd_out[x],
                ),
                self.output_size[x],
            )
            for x in range(arr.ndim)
        ]
        bottom_right_put = [
            min(
                max(0, top_left_put[x] + (bottom_right_get[x] - top_left_get[x])),
                self.output_size[x],
            )
            for x in range(arr.ndim)
        ]
        get_slices = [slice(x1, x2) for x1, x2 in zip(top_left_get, bottom_right_get)]
        get_slices = tuple(get_slices)
        put_slices = [slice(x1, x2) for x1, x2 in zip(top_left_put, bottom_right_put)]
        put_slices = tuple(put_slices)
        out_array = np.zeros(self.output_size)
        out_array[put_slices] = arr[get_slices]
        return out_array.astype(arr.dtype)

    def enable_mouse_control(self):
        """Move the mouse to move where the crop is from on the original image."""

        @mouse_loop
        def m_loop(me):
            if self.center is None:
                self.center = [0, 0, 1]
            self.center[:] = [
                int(me.y / self.output_size[0] * self.input_size[0]),
                int(me.x / self.output_size[1] * self.input_size[1]),
                1,
            ]

        self.mouse_control = m_loop
        return self
