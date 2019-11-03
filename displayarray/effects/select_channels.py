import numpy as np
from ..input import mouse_loop
import cv2


class SelectChannels(object):
    def __init__(self, selected_channels=None):
        if selected_channels is None:
            selected_channels = [0, 0, 0]
        self.selected_channels = selected_channels
        self.mouse_control = None
        self.mouse_print_channels = False
        self.num_input_channels = None

    def __call__(self, arr):
        self.num_input_channels = arr.shape[-1]
        out_arr = [
            arr[..., min(max(0, x), arr.shape[-1] - 1)] for x in self.selected_channels
        ]
        out_arr = np.stack(out_arr, axis=-1)
        return out_arr

    def enable_mouse_control(self):
        @mouse_loop
        def m_loop(me):
            if me.event == cv2.EVENT_MOUSEWHEEL:
                if me.flags & cv2.EVENT_FLAG_CTRLKEY:
                    if me.flags > 0:
                        self.selected_channels[0] += 1
                        self.selected_channels[0] = min(
                            self.selected_channels[0], self.num_input_channels - 1
                        )
                    else:
                        self.selected_channels[0] -= 1
                        self.selected_channels[0] = max(self.selected_channels[0], 0)
                    if self.mouse_print_channels:
                        print(f"Channel 0 now maps to {self.selected_channels[0]}.")
                elif me.flags & cv2.EVENT_FLAG_SHIFTKEY:
                    if me.flags > 0:
                        self.selected_channels[1] += 1
                        self.selected_channels[1] = min(
                            self.selected_channels[1], self.num_input_channels - 1
                        )
                    else:
                        self.selected_channels[1] -= 1
                        self.selected_channels[1] = max(self.selected_channels[1], 0)
                    if self.mouse_print_channels:
                        print(f"Channel 1 now maps to {self.selected_channels[1]}.")
                elif me.flags & cv2.EVENT_FLAG_ALTKEY:
                    if me.flags > 0:
                        self.selected_channels[2] += 1
                        self.selected_channels[2] = min(
                            self.selected_channels[2], self.num_input_channels - 1
                        )
                    else:
                        self.selected_channels[2] -= 1
                        self.selected_channels[2] = max(self.selected_channels[2], 0)
                    if self.mouse_print_channels:
                        print(f"Channel 2 now maps to {self.selected_channels[2]}.")

        self.mouse_control = m_loop
