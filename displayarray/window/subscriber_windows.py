import warnings
from threading import Thread
from typing import List, Union, Callable, Any, Dict, Iterable, Optional

import cv2
import numpy as np
from localpubsub import NoData

from displayarray.callbacks import global_cv_display_callback
from displayarray.uid import uid_for_source
from displayarray.frame import subscriber_dictionary
from displayarray.frame.frame_updater import FrameCallable
from displayarray.frame.frame_updater import FrameUpdater
from displayarray.input import MouseEvent
from displayarray.window import window_commands
from ..util import WeakMethod
from ..effects.select_channels import SelectChannels


class SubscriberWindows(object):
    """Windows that subscribe to updates to cameras, videos, and arrays."""

    FRAME_DICT: Dict[str, np.ndarray] = {}
    ESC_KEY_CODES = [27]  # ESC key on most keyboards

    def __init__(
            self,
            window_names: Iterable[str] = ("displayarray",),
            video_sources: Iterable[Union[str, int]] = (0,),
            callbacks: Optional[List[Callable[[np.ndarray], Any]]] = None,
    ):
        self.source_names: List[Union[str, int]] = []
        self.close_threads: Optional[List[Thread]] = None
        self.frames: List[np.ndarray] = []
        self.input_vid_global_names: List[str] = []
        self.window_names: List[str] = []
        self.input_cams: List[str] = []
        self.exited = False

        if callbacks is None:
            callbacks = []
        for name in video_sources:
            self.add_source(name)
        self.callbacks = callbacks
        for name in window_names:
            self.add_window(name)

        self.update()

    def __bool__(self):
        self.update()
        return not self.exited

    def block(self):
        self.loop()
        for ct in self.close_threads:
            ct.join()

    def add_source(self, name):
        """Add another source for this class to display."""
        uid = uid_for_source(name)
        self.source_names.append(uid)
        self.input_vid_global_names.append(uid + "frame")
        self.input_cams.append(name)
        return self

    def add_window(self, name):
        """Add another window for this class to display sources with. The name will be the title."""
        self.window_names.append(name)
        cv2.namedWindow(name + " (press ESC to quit)")
        m = WeakMethod(self.handle_mouse)
        cv2.setMouseCallback(name + " (press ESC to quit)", m)
        return self

    def del_window(self, name):
        cv2.setMouseCallback(name + " (press ESC to quit)", lambda *args: None)

    def add_callback(self, callback):
        """Add a callback for this class to apply to videos."""
        self.callbacks.append(callback)
        return self

    def __stop_all_cams(self):
        for c in self.source_names:
            subscriber_dictionary.stop_cam(c)

    def handle_keys(
            self, key_input  # type: int
    ):
        """Capture key input for the escape function and passing to key control subscriber threads."""
        if key_input in self.ESC_KEY_CODES:
            for name in self.window_names:
                cv2.destroyWindow(name + " (press ESC to quit)")
            self.exited = True
            window_commands.quit()
            self.__stop_all_cams()
            return "quit"
        elif key_input not in [-1, 0]:
            try:
                window_commands.key_pub.publish(chr(key_input))
            except ValueError:
                warnings.warn(
                    RuntimeWarning(
                        "Unknown key code: [{}]. Please report to cv_pubsubs issue page.".format(
                            key_input
                        )
                    )
                )

    def handle_mouse(self, event, x, y, flags, param):
        """Capture mouse input for mouse control subscriber threads."""
        mousey = MouseEvent(event, x, y, flags, param)
        window_commands.mouse_pub.publish(mousey)

    def _display_frames(self, frames, win_num, ids=None):
        if isinstance(frames, Exception):
            raise frames
        for f in range(len(frames)):
            # detect nested:
            if (
                    isinstance(frames[f], (list, tuple))
                    or frames[f].dtype.num == 17
                    or len(frames[f].shape) > 3
            ):
                win_num = self._display_frames(frames[f], win_num, ids)
            else:
                cv2.imshow(
                    self.window_names[win_num % len(self.window_names)]
                    + " (press ESC to quit)",
                    frames[f],
                )
                win_num += 1
        return win_num

    def update_window_frames(self):
        """Update the windows with the newest data for all frames."""
        win_num = 0
        for i in range(len(self.input_vid_global_names)):
            if self.input_vid_global_names[i] in self.FRAME_DICT and not isinstance(
                    self.FRAME_DICT[self.input_vid_global_names[i]], NoData
            ):
                self.frames = self.FRAME_DICT[self.input_vid_global_names[i]]
                if isinstance(self.frames, np.ndarray) and len(self.frames.shape) <= 3:
                    self.frames = [self.frames]
                if len(self.callbacks) > 0:
                    for c in self.callbacks:
                        for f in range(len(self.frames)):
                            frame = c(self.frames[f])
                            if frame is not None:
                                self.frames[f] = frame
                for f in range(len(self.frames)):
                    if self.frames[f].shape[-1] not in [1, 3] and len(self.frames[f].shape) != 2:
                        print(f"Too many channels in output. (Got {self.frames[f].shape[-1]} instead of 1 or 3.) "
                              f"Frame selection callback added.")
                        print("Ctrl+scroll to change first channel.\n"
                              "Shift+scroll to change second channel.\n"
                              "Alt+scroll to change third channel.")
                        sel = SelectChannels()
                        sel.enable_mouse_control()
                        sel.mouse_print_channels = True
                        self.callbacks.append(sel)
                        for fr in range(len(self.frames)):
                            self.frames[fr] = self.callbacks[-1](self.frames[fr])
                        break
                win_num = self._display_frames(self.frames, win_num)

    def update(self, arr=None, id=None):
        """Update window frames once. Optionally add a new input and input id."""
        if arr is not None and id is not None:
            global_cv_display_callback(arr, id)
            if id not in self.input_cams:
                self.add_source(id)
                self.add_window(id)
        sub_cmd = window_commands.win_cmd_sub()
        self.update_window_frames()
        msg_cmd = sub_cmd.get()
        key = self.handle_keys(cv2.waitKey(1))
        return msg_cmd, key

    def wait_for_init(self):
        """Update window frames in a loop until they're actually updated. Useful for waiting for cameras to init."""
        msg_cmd = ""
        key = ""
        while msg_cmd != "quit" and key != "quit" and len(self.frames) == 0:
            msg_cmd, key = self.update()
        return self

    def end(self):
        """Close all threads. Should be used with non-blocking mode."""
        window_commands.quit(force_all_read=False)
        self.__stop_all_cams()
        if self.close_threads is not None:
            for t in self.close_threads:
                t.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def __del__(self):
        self.end()

    def __delete__(self, instance):
        del self.handle_mouse
        self.end()

    def loop(self):
        """Continually update window frame. OpenCV only allows this in the main thread."""
        sub_cmd = window_commands.win_cmd_sub()
        msg_cmd = ""
        key = ""
        while msg_cmd != "quit" and key != "quit":
            msg_cmd, key = self.update()
        sub_cmd.release()
        window_commands.quit(force_all_read=False)
        self.__stop_all_cams()


def _get_video_callback_dict_threads(
        *vids, callbacks: Optional[Dict[Any, FrameCallable]] = None,
        fps=240, size=(-1, -1)
):
    assert callbacks is not None
    vid_threads = []
    for v in vids:
        v_name = uid_for_source(v)
        v_callbacks: List[Callable[[np.ndarray], Any]] = []
        if v_name in callbacks:
            v_callbacks.append(callbacks[v_name])
        if v in callbacks:
            v_callbacks.append(callbacks[v])
        vid_threads.append(FrameUpdater(v, callbacks=v_callbacks, fps_limit=fps, request_size=size))
    return vid_threads


def _get_video_threads(
        *vids,
        callbacks: Optional[
            Union[Dict[Any, FrameCallable], List[FrameCallable], FrameCallable]
        ] = None,
        fps=240, size=(-1, -1)
):
    vid_threads: List[Thread] = []
    if isinstance(callbacks, Dict):
        vid_threads = _get_video_callback_dict_threads(*vids, callbacks=callbacks, fps=fps, size=size)
    elif isinstance(callbacks, List):
        for v in vids:
            vid_threads.append(FrameUpdater(v, callbacks=callbacks, fps_limit=fps, request_size=size))
    elif callable(callbacks):
        for v in vids:
            vid_threads.append(FrameUpdater(v, callbacks=[callbacks], fps_limit=fps, request_size=size))
    else:
        for v in vids:
            if v is not None:
                vid_threads.append(FrameUpdater(v, fps_limit=fps, request_size=size))
    return vid_threads


def display(
        *vids,
        callbacks: Optional[
            Union[Dict[Any, FrameCallable], List[FrameCallable], FrameCallable]
        ] = None,
        window_names=None,
        blocking=False,
        fps_limit=240,
        size=(-1, -1)
):
    """
    Display all the arrays, cameras, and videos passed in.

    callbacks can be a dictionary linking functions to videos, or a list of function or functions operating on the video
     data before displaying.
    Window names end up becoming the title of the windows
    """
    vid_threads = _get_video_threads(*vids, callbacks=callbacks, fps=fps_limit, size=size)
    for v in vid_threads:
        v.start()
    if window_names is None:
        window_names = ["window {}".format(i) for i in range(len(vids))]
    if blocking:
        SubscriberWindows(window_names=window_names, video_sources=vids).loop()
        for vt in vid_threads:
            vt.join()
    else:
        s = SubscriberWindows(window_names=window_names, video_sources=vids)
        s.close_threads = vid_threads
        return s


def breakpoint_display(*args, **kwargs):
    return display(*args, **kwargs, blocking=True)
