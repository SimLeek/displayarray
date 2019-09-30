import warnings

import cv2
import numpy as np

from .winctrl import WinCtrl
from cvpubsubs.webcam_pub.camctrl import CamCtrl
from cvpubsubs.webcam_pub.frame_handler import VideoHandlerThread
from localpubsub import NoData
from cvpubsubs.window_sub.mouse_event import MouseEvent
from cvpubsubs.serialize import uid_for_source

from typing import List, Union, Callable, Any, Dict
import numpy as np
from cvpubsubs.callbacks import global_cv_display_callback


class SubscriberWindows(object):
    frame_dict = {}

    esc_key_codes = [27]  # ESC key on most keyboards

    def __init__(self,
                 window_names=('cvpubsubs',),  # type: List[str]
                 video_sources=(0,),  # type: List[Union[str,int]]
                 callbacks=(None,),  # type: List[Callable[[List[np.ndarray]], Any]]
                 ):
        self.source_names = []
        self.close_threads = None
        self.frames = []
        self.input_vid_global_names = []
        self.window_names = []
        self.input_cams = []

        for name in video_sources:
            self.add_source(name)
        self.callbacks = callbacks
        for name in window_names:
            self.add_window(name)

    def add_source(self, name):
        uid = uid_for_source(name)
        self.source_names.append(uid)
        self.input_vid_global_names.append(uid + "frame")
        self.input_cams.append(name)

    def add_window(self, name):
        self.window_names.append(name)
        cv2.namedWindow(name + " (press ESC to quit)")
        cv2.setMouseCallback(name + " (press ESC to quit)", self.handle_mouse)

    def add_callback(self, callback):
        self.callbacks.append(callback)

    @staticmethod
    def set_global_frame_dict(name, *args):
        if len(str(name)) <= 1000:
            SubscriberWindows.frame_dict[str(name) + "frame"] = list(args)
        elif isinstance(name, np.ndarray):
            SubscriberWindows.frame_dict[str(hash(str(name))) + "frame"] = list(args)
        else:
            raise ValueError("Input window name too long.")

    def __stop_all_cams(self):
        for c in self.source_names:
            CamCtrl.stop_cam(c)

    def handle_keys(self,
                    key_input,  # type: int
                    ):
        if key_input in self.esc_key_codes:
            for name in self.window_names:
                cv2.destroyWindow(name + " (press ESC to quit)")
            WinCtrl.quit()
            self.__stop_all_cams()
            return 'quit'
        elif key_input not in [-1, 0]:
            try:
                WinCtrl.key_pub.publish(chr(key_input))
            except ValueError:
                warnings.warn(
                    RuntimeWarning("Unknown key code: [{}]. Please report to cv_pubsubs issue page.".format(key_input))
                )

    def handle_mouse(self, event, x, y, flags, param):
        mousey = MouseEvent(event, x, y, flags, param)
        WinCtrl.mouse_pub.publish(mousey)

    def _display_frames(self, frames, win_num, ids=None):
        if isinstance(frames, Exception):
            raise frames
        for f in range(len(frames)):
            # detect nested:
            if isinstance(frames[f], (list, tuple)) or frames[f].dtype.num == 17 or len(frames[f].shape) > 3:
                win_num = self._display_frames(frames[f], win_num, ids)
            else:
                cv2.imshow(self.window_names[win_num % len(self.window_names)] + " (press ESC to quit)", frames[f])
                win_num += 1
        return win_num

    def update_window_frames(self):
        win_num = 0
        for i in range(len(self.input_vid_global_names)):
            if self.input_vid_global_names[i] in self.frame_dict and \
                    not isinstance(self.frame_dict[self.input_vid_global_names[i]], NoData):
                if len(self.callbacks) > 0 and self.callbacks[i % len(self.callbacks)] is not None:
                    self.frames = self.callbacks[i % len(self.callbacks)](
                        self.frame_dict[self.input_vid_global_names[i]])
                else:
                    self.frames = self.frame_dict[self.input_vid_global_names[i]]
                if isinstance(self.frames, np.ndarray) and len(self.frames.shape) <= 3:
                    self.frames = [self.frames]
                win_num = self._display_frames(self.frames, win_num)

    def update(self, arr=None, id=None):
        if arr is not None and id is not None:
            global_cv_display_callback(arr, id)
            if id not in self.input_cams:
                self.add_source(id)
                self.add_window(id)
        sub_cmd = WinCtrl.win_cmd_sub()
        self.update_window_frames()
        msg_cmd = sub_cmd.get()
        key = self.handle_keys(cv2.waitKey(1))
        return msg_cmd, key

    def wait_for_init(self):
        msg_cmd=""
        key = ""
        while msg_cmd != 'quit' and key != 'quit' and len(self.frames)==0:
            msg_cmd, key = self.update()

    def end(self):
        if self.close_threads is not None:
            for t in self.close_threads:
                t.join()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    # todo: figure out how to get the red x button to work. Try: https://stackoverflow.com/a/37881722/782170
    def loop(self):
        sub_cmd = WinCtrl.win_cmd_sub()
        msg_cmd = ''
        key = ''
        while msg_cmd != 'quit' and key != 'quit':
            msg_cmd, key = self.update()
        sub_cmd.release()
        WinCtrl.quit(force_all_read=False)
        self.__stop_all_cams()


from cvpubsubs.callbacks import global_cv_display_callback

from threading import Thread


def display(*vids,
            callbacks: Union[Dict[Any, Callable], List[Callable], Callable, None] = None,
            window_names=[],
            blocking=False):
    vid_threads = []
    if isinstance(callbacks, Dict):
        for v in vids:
            v_name = uid_for_source(v)
            v_callbacks = []
            if v_name in callbacks:
                v_callbacks.extend(callbacks[v_name])
            if v in callbacks:
                v_callbacks.extend(callbacks[v])
            vid_threads.append(VideoHandlerThread(v, callbacks=v_callbacks))
    elif isinstance(callbacks, List):
        for v in vids:
            vid_threads.append(VideoHandlerThread(v, callbacks=callbacks))
    elif isinstance(callbacks, Callable):
        for v in vids:
            vid_threads.append(VideoHandlerThread(v, callbacks=[callbacks]))
    else:
        for v in vids:
            vid_threads.append(VideoHandlerThread(v))
    for v in vid_threads:
        v.start()
    if len(window_names) == 0:
        window_names = ["window {}".format(i) for i in range(len(vids))]
    if blocking:
        SubscriberWindows(window_names=window_names,
                          video_sources=vids
                          ).loop()
        for v in vid_threads:
            v.join()
    else:
        s = SubscriberWindows(window_names=window_names,
                              video_sources=vids
                              )
        s.close_threads = vid_threads
        v_names = []
        for v in vids:
            v_name = uid_for_source(v)
            v_names.append(v_name)
        return s, v_names
