import numpy as np
from ..input import mouse_loop
import cv2


class ControllableLens(object):
    def __init__(self, use_bleed=False, zoom=1, center=None):
        self.center = center
        self.zoom = zoom
        self.use_bleed = use_bleed
        self.bleed = None
        self.mouse_control = None

    def check_setup_bleed(self, arr):
        if not isinstance(self.bleed, np.ndarray) and self.use_bleed:
            self.bleed = np.zeros_like(arr)

    def run_bleed(self, arr, x, y):
        arr[y, ...] = (arr[(y + 1) % len(y), ...] + arr[(y - 1) % len(y), ...]) / 2
        arr[:, x, ...] = (
            arr[:, (x + 1) % len(x), ...] + arr[:, (x - 1) % len(x), ...]
        ) / 2


class Barrel(ControllableLens):
    def __init__(
        self, use_bleed=False, barrel_power=1, pincushion_power=1, zoom=1, center=None
    ):
        super().__init__(use_bleed, zoom, center)
        self.center = center
        self.zoom = zoom
        self.use_bleed = use_bleed
        self.bleed = None
        self.barrel_power = barrel_power
        self.mouse_control = None

    def enable_mouse_control(self):
        """
        Move the mouse to center the image, scroll to increase/decrease barrel, ctrl+scroll to increase/decrease zoom
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
                else:
                    if me.flags > 0:
                        self.barrel_power *= 1.1
                    else:
                        self.barrel_power /= 1.1

        self.mouse_control = m_loop
        return self

    def __call__(self, arr):
        zoom_out = 1.0 / self.zoom
        self.check_setup_bleed(arr)

        y = np.arange(arr.shape[0])
        x = np.arange(arr.shape[1])
        if self.center is None:
            self.center = [len(y) / 2.0, len(x) / 2.0]
        y2_ = (y - (len(y) / 2.0)) * zoom_out / arr.shape[0]
        x2_ = (x - (len(x) / 2.0)) * zoom_out / arr.shape[1]
        p2 = np.array(np.meshgrid(x2_, y2_))

        cy = self.center[0] / arr.shape[0]
        cx = self.center[1] / arr.shape[1]

        barrel_power = self.barrel_power

        theta = np.arctan2(p2[1], p2[0])

        radius = np.linalg.norm(p2, axis=0, ord=2)

        radius = pow(radius, barrel_power)

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


class Mustache(ControllableLens):
    def __init__(
        self, use_bleed=False, barrel_power=1, pincushion_power=1, zoom=1, center=None
    ):
        super().__init__(use_bleed, zoom, center)
        self.center = center
        self.zoom = zoom
        self.use_bleed = use_bleed
        self.bleed = None
        self.barrel_power = barrel_power
        self.pincushion_power = pincushion_power
        self.mouse_control = None

    def enable_mouse_control(self):
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
        zoom_out = 1.0 / self.zoom
        self.check_setup_bleed(arr)

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
