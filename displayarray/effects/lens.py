"""Create lens effects. Currently only 2D+color arrays are supported."""

import numpy as np
from ..input import mouse_loop
import cv2

try:
    import torch
except ImportError:
    torch = None  # type: ignore


class ControllableLens(object):
    """A lens callback that can be controlled by the program or the user."""

    def __init__(self, use_bleed=False, zoom=1, center=None):
        """Create the lens callback."""
        self._center = center
        self._zoom = zoom
        self.use_bleed = use_bleed
        self.bleed = None
        self.mouse_control = None

    def _check_setup_bleed(self, arr):
        if not isinstance(self.bleed, np.ndarray) and self.use_bleed:
            self.bleed = np.zeros_like(arr)

    def run_bleed(self, arr, x, y):
        """Spread color outwards, like food coloring in water."""
        arr[y, ...] = (arr[(y + 1) % len(y), ...] + arr[(y - 1) % len(y), ...]) / 2
        arr[:, x, ...] = (
            arr[:, (x + 1) % len(x), ...] + arr[:, (x - 1) % len(x), ...]
        ) / 2


class Barrel(ControllableLens):
    """A barrel lens distortion callback."""

    def __init__(
        self, use_bleed=False, barrel_power=1, pincushion_power=1, zoom=1, center=None
    ):
        """Create the barrel lens distortion callback."""
        super().__init__(use_bleed, zoom, center)
        self._center = center
        self._zoom = zoom
        self.use_bleed = use_bleed
        self.bleed = None
        self._barrel_power = barrel_power
        self.mouse_control = None
        self.input_size = None

    @property
    def center(self):
        """Guarded get center. Limits to within input."""
        if self.input_size is not None:
            self._center[:] = [
                min(max(0, s), self.input_size[i]) for i, s in enumerate(self._center)
            ]
        return self._center

    @center.setter
    def center(self, setpoint):
        """Guarded set center. Limits to within input."""
        if self.input_size is not None:
            setpoint = [
                min(max(0, s), self.input_size[i]) for i, s in enumerate(setpoint)
            ]
        self._center[:] = setpoint

    @property
    def zoom(self):
        """Guarded zoom. Avoids divide by zero conditions."""
        if self._zoom == 0:
            return 1e-15
        else:
            return self._zoom

    @property
    def barrel_power(self):
        """Guarded barrel power. Avoids divide by zero conditions."""
        if self._barrel_power == 0:
            return 1e-15
        else:
            return self._barrel_power

    @barrel_power.setter
    def barrel_power(self, setpoint):
        """Set the barrel power."""
        self._barrel_power = setpoint

    @zoom.setter  # type: ignore
    def zoom(self, setpoint):
        """Set the zoom power."""
        self._zoom = setpoint

    def enable_mouse_control(self, crop_size=None):
        """
        Enable the default mouse controls.

        Move the mouse to center the image
        scroll to increase/decrease barrel
        ctrl+scroll to increase/decrease zoom
        """

        @mouse_loop
        def m_loop(me):
            if self.input_size is not None:
                if crop_size is not None:
                    self.center = [
                        me.y * self.input_size[0] / crop_size[0],
                        me.x * self.input_size[1] / crop_size[1],
                    ]
                else:
                    self.center = [me.y, me.x]
                if me.event == cv2.EVENT_MOUSEWHEEL:
                    if me.flags & cv2.EVENT_FLAG_CTRLKEY:
                        if me.flags > 0:
                            self.zoom *= 1.1
                        else:
                            self.zoom /= 1.1
                    else:
                        if me.flags > 0:
                            self.barrel_power *= 1.1
                        else:
                            self.barrel_power /= 1.1
                        print(self.barrel_power)

        self.mouse_control = m_loop
        return self

    def __call__(self, arr):
        """Run the lens distortion algorithm on the input."""
        zoom_out = 1.0 / self.zoom
        self._check_setup_bleed(arr)

        self.input_size = arr.shape

        y = np.arange(arr.shape[0])
        x = np.arange(arr.shape[1])
        if self._center is None:
            self._center = [len(y) / 2.0, len(x) / 2.0]
        y2_ = (y - (len(y) / 2.0)) * zoom_out / arr.shape[0]
        x2_ = (x - (len(x) / 2.0)) * zoom_out / arr.shape[1]
        p2 = np.array(np.meshgrid(x2_, y2_))

        cy = self._center[0] / arr.shape[0]
        cx = self._center[1] / arr.shape[1]

        theta = np.arctan2(p2[1], p2[0])

        radius = np.linalg.norm(p2, axis=0, ord=2)

        radius = pow(radius, self.barrel_power)

        x_new = 0.5 * (radius * np.cos(theta) + cx * 2)
        x_new = np.clip(x_new * len(x), 0, len(x) - 1)

        y_new = 0.5 * (radius * np.sin(theta) + cy * 2)
        y_new = np.clip(y_new * len(y), 0, len(y) - 1)

        p = np.array(np.meshgrid(y, x)).astype(np.uint32)

        p_new = np.array((y_new, x_new))
        p_new = p_new.astype(np.uint32)

        if self.use_bleed:
            arr2 = self.bleed.copy()
            self.run_bleed(arr2, x, y)
            arr2[p_new[0], p_new[1], :] = np.swapaxes(arr[p[0], p[1], :], 0, 1)
            self.bleed = arr2
        else:
            arr[p[0], p[1], :] = np.swapaxes(arr[p_new[0], p_new[1], :], 0, 1)

        return arr


class BarrelPyTorch(Barrel):
    """A barrel distortion callback class accelerated by PyTorch."""

    def __call__(self, arr):
        """Run a pytorch accelerated lens distortion algorithm on the input."""
        zoom_out = 1.0 / self.zoom
        self.input_size = arr.shape
        y = torch.arange(arr.shape[1]).type(torch.FloatTensor).cuda()
        x = torch.arange(arr.shape[0]).type(torch.FloatTensor).cuda()
        if self._center is None:
            self._center = [y.shape[0] / 2.0, x.shape[0] / 2.0]

        y2_ = (y - (y.shape[0] / 2.0)) * zoom_out / arr.shape[1]
        x2_ = (x - (x.shape[0] / 2.0)) * zoom_out / arr.shape[0]
        p2 = torch.stack(torch.meshgrid(x2_, y2_))

        cy = self._center[1] / arr.shape[1]
        cx = self._center[0] / arr.shape[0]

        theta = torch.atan2(p2[1], p2[0])

        radius = torch.norm(p2, dim=0)

        radius = torch.pow(radius, self.barrel_power)

        x_new = 0.5 * (radius * torch.cos(theta) + cx * 2)
        x_new = torch.clamp(x_new * x.shape[0], 0, x.shape[0] - 1)

        y_new = 0.5 * (radius * torch.sin(theta) + cy * 2)
        y_new = torch.clamp(y_new * y.shape[0], 0, y.shape[0] - 1)

        p = torch.stack(torch.meshgrid([x, y])).type(torch.IntTensor)

        p_new = torch.stack((x_new, y_new))
        p_new = p_new.type(torch.IntTensor)

        arr[p[0], p[1], :] = arr[p_new[0], p_new[1], :]

        return arr


class Mustache(ControllableLens):
    """A mustache distortion callback."""

    def __init__(
        self, use_bleed=False, barrel_power=1, pincushion_power=1, zoom=1, center=None
    ):
        """Create the mustache distortion callback."""
        super().__init__(use_bleed, zoom, center)
        self.center = center
        self.zoom = zoom
        self.use_bleed = use_bleed
        self.bleed = None
        self.barrel_power = barrel_power
        self.pincushion_power = pincushion_power
        self.mouse_control = None

    def enable_mouse_control(self):
        """
        Enable the default mouse loop to control the mustache distortion.

        ctrl+scroll wheel: zoom in and out
        shift+scroll wheel: adjust pincushion power
        scroll wheel: adjust barrel power
        """

        @mouse_loop
        def m_loop(me):
            self.center[:] = [me.y, me.x]
            if me.event == cv2.EVENT_MOUSEWHEEL:
                if me.flags & cv2.EVENT_FLAG_CTRLKEY:
                    if me.flags > 0:
                        self.zoom *= 1.1
                    else:
                        self.zoom /= 1.1
                elif me.flags & cv2.EVENT_FLAG_SHIFTKEY:
                    if me.flags > 0:
                        self.pincushion_power *= 1.1
                    else:
                        self.pincushion_power /= 1.1
                else:
                    if me.flags > 0:
                        self.barrel_power *= 1.1
                    else:
                        self.barrel_power /= 1.1

        self.mouse_control = m_loop

    def __call__(self, arr):
        """Run the mustache distortion algorithm on the input numpy array."""
        zoom_out = 1.0 / self.zoom
        self._check_setup_bleed(arr)

        y = np.arange(arr.shape[0])
        x = np.arange(arr.shape[1])
        if self.center is None:
            self.center = [len(y) / 2.0, len(x) / 2.0]
        y2_ = (y - self.center[0]) * zoom_out / arr.shape[0]
        x2_ = (x - self.center[1]) * zoom_out / arr.shape[1]
        p2 = np.array(np.meshgrid(x2_, y2_))

        barrel_power = self.barrel_power
        pincushion_power = self.pincushion_power

        theta = np.arctan2(p2[1], p2[0])

        radius = np.linalg.norm(p2, axis=0)
        radius2 = np.linalg.norm(p2, axis=0, ord=4)

        radius = pow(radius, barrel_power)
        radius2 = pow(radius2, pincushion_power)

        x_new = 0.5 * (radius2 * radius * np.cos(theta) + 1)
        x_new = np.clip(x_new * len(x), 0, len(x) - 1)

        y_new = 0.5 * (radius2 * radius * np.sin(theta) + 1)
        y_new = np.clip(y_new * len(y), 0, len(y) - 1)

        p = np.array(np.meshgrid(y, x)).astype(np.uint32)

        p_new = np.array((y_new, x_new)).astype(np.uint32)

        if self.use_bleed:
            arr2 = self.bleed.copy()
            self.run_bleed(arr2, x, y)
            arr2[p_new[0], p_new[1], :] = np.swapaxes(arr[p[0], p[1], :], 0, 1)
            self.bleed = arr2
        else:
            arr2 = np.zeros_like(arr)
            arr2[p_new[0], p_new[1], :] = np.swapaxes(arr[p[0], p[1], :], 0, 1)

        return arr2
