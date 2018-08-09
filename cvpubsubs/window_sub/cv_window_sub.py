import warnings

import cv2
import pubsub

from .winctrl import WinCtrl
from ..listen_default import listen_default
from ..webcam_pub.camctrl import CamCtrl

if False:
    from typing import List


class SubscriberWindows(object):
    frame_dict = {}

    esc_key_codes = [27]  # ESC key on most keyboards

    def __init__(self,
                 window_names,  # type: List[str]
                 input_vid_global_names,  # type: List[str]
                 callbacks=(None,),
                 input_cams=(0,)
                 ):
        self.window_names = window_names
        self.input_vid_global_names = input_vid_global_names
        self.callbacks = callbacks
        self.input_cams = input_cams

    def handle_keys(self,
                    key_input,  # type: int
                    ):
        if key_input in self.esc_key_codes:
            for name in self.window_names:
                cv2.destroyWindow(name + " (press ESC to quit)")
            for c in self.input_cams:
                CamCtrl.stop_cam(c)
            WinCtrl.quit()
        elif key_input not in [-1, 0]:
            try:
                WinCtrl.key_stroke(chr(key_input))
            except ValueError:
                warnings.warn(
                    RuntimeWarning("Unknown key code: [{}]. Please report to cv_pubsubs issue page.".format(key_input))
                )

    def update_window_frames(self):
        for i in range(len(self.input_vid_global_names)):
            if self.input_vid_global_names[i] in self.frame_dict and self.frame_dict[
                self.input_vid_global_names[i]] is not None:
                if self.callbacks[i % len(self.callbacks)] is not None:
                    frames = self.callbacks[i % len(self.callbacks)](self.frame_dict[self.input_vid_global_names[i]])
                else:
                    frames = self.frame_dict[self.input_vid_global_names[i]]
                for f in range(len(frames)):
                    cv2.imshow(self.window_names[f % len(self.window_names)] + " (press ESC to quit)", frames[f])

    # todo: figure out how to get the red x button to work. Try: https://stackoverflow.com/a/37881722/782170
    def loop(self):
        sub_cmd = pubsub.subscribe("CVWinCmd")
        msg_cmd = ''
        while msg_cmd != 'quit':
            self.update_window_frames()
            self.handle_keys(cv2.waitKey(1))
            msg_cmd = listen_default(sub_cmd, block=False, empty='')
        pubsub.publish("CVWinCmd", 'quit')
