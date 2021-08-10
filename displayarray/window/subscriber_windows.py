"""OpenCV windows that will display the arrays."""

import warnings
from threading import Thread
from typing import List, Union, Callable, Any, Dict, Iterable, Optional

import cv2
import numpy as np
from localpubsub import NoData

from displayarray.callbacks import global_cv_display_callback
from displayarray._uid import uid_for_source
from displayarray.frame import subscriber_dictionary
from displayarray.frame.frame_updater import FrameCallable
from displayarray.frame.frame_updater import FrameUpdater
from displayarray.frame.subscriber_dictionary import CV_CAMS_DICT
from displayarray.input import MouseEvent
from displayarray.window import window_commands
from displayarray._util import WeakMethod
from displayarray.effects.select_channels import SelectChannels

try:
    import sys

    if sys.platform == "linux":
        from PyV4L2Cam.get_camera import get_bus_info_from_camera  # type: ignore
    else:
        get_bus_info_from_camera = None
except:
    get_bus_info_from_camera = None

try:
    import zmq
    from tensorcom.tenbin import encode_buffer  # type: ignore
except:
    warnings.warn("Could not import ZMQ and tensorcom. Cannot send messages between programs.")


class SubscriberWindows(object):
    """Windows that subscribe to updates to cameras, videos, and arrays."""

    FRAME_DICT: Dict[str, np.ndarray] = {}
    ESC_KEY_CODES = [27]  # ESC key on most keyboards

    def __init__(
        self,
        window_names: Iterable[str] = ("displayarray",),
        video_sources: Iterable[Union[str, int]] = (0,),
        callbacks: Optional[List[Callable[[np.ndarray], Any]]] = None,
        silent: bool = False,
    ):
        """Create the array displaying window."""
        self.source_names: List[Union[str, int]] = []
        self.close_threads: Optional[List[Thread]] = []
        self.frames: Dict[Union[str, int], np.ndarray] = {}
        self.input_vid_global_names: List[str] = []
        self.window_names: List[str] = []
        self.input_cams: List[str] = []
        self.exited = False
        self.silent = silent
        self.ctx = None
        self.sock_list: List[zmq.Socket] = []
        self.top_list: List[bytes] = []

        if callbacks is None:
            callbacks = []
        for name in video_sources:
            self.add_source(name)
        self.callbacks = callbacks
        if not self.silent:
            for name in window_names:
                self.add_window(name)

        self.update()

    def __bool__(self):
        self.update()
        return not self.exited

    def __iter__(self):
        while not self.exited:
            self.update()
            yield self.frames

    def block(self):
        """Update the window continuously while blocking the outer program."""
        self.loop()
        for ct in self.close_threads:
            ct.join()

    def add_source(self, name):
        """Add another source for this class to display."""
        uid = uid_for_source(name)
        self.source_names.append(uid)
        self.input_vid_global_names.append(uid)
        self.input_cams.append(name)
        return self

    def add_window(self, name):
        """Add another window for this class to display sources with. The name will be the title."""
        self.window_names.append(name)
        cv2.namedWindow(name + " (press ESC to quit)")
        m = WeakMethod(self.handle_mouse)
        cv2.setMouseCallback(name + " (press ESC to quit)", m)
        return self

    def add_callback(self, callback):
        """Add a callback for this class to apply to videos."""
        self.callbacks.append(callback)
        return self

    def __stop_all_cams(self):
        for c in self.source_names:
            subscriber_dictionary.stop_cam(c)

    def handle_keys(self, key_input: int):
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
                        f"Unknown key code: [{key_input}]. Please report to the displayarray issue page."
                    )
                )

    def handle_mouse(self, event, x, y, flags, param):
        """Capture mouse input for mouse control subscriber threads."""
        mousey = MouseEvent(event, x, y, flags, param)
        window_commands.mouse_pub.publish(mousey)

    def display_frames(self, frames, win_num=0, prepend_name=""):
        """Display a list of frames on multiple windows."""
        if isinstance(frames, Exception):
            raise frames
        if isinstance(frames, dict):
            for f_name, f in frames.items():
                for i in range(len(f)):
                    # detect nested:
                    if (
                        isinstance(f[i], (list, tuple))
                        or f[i].dtype.num == 17
                        or (
                            len(f[i].shape) != 2
                            and (len(f[i].shape) != 3 or f[i].shape[-1] != 3)
                        )
                    ):
                        win_num = self.display_frames(
                            f[i], win_num, prepend_name=f"{f_name} - "
                        )
                    else:
                        if len(self.window_names) <= win_num:
                            self.add_window(f"{prepend_name}{win_num}")
                        cv2.imshow(
                            self.window_names[win_num] + " (press ESC to quit)", f[i]
                        )
                        win_num += 1
        else:
            for f in range(len(frames)):
                # detect nested:
                if (
                    isinstance(frames[f], (list, tuple))
                    or frames[f].dtype.num == 17
                    or (
                        len(frames[f].shape) != 2
                        and (len(frames[f].shape) != 3 or frames[f].shape[-1] != 3)
                    )
                ):
                    win_num = self.display_frames(frames[f], win_num, prepend_name)
                else:
                    if len(self.window_names) <= win_num:
                        self.add_window(f"{prepend_name} {win_num}")
                    cv2.imshow(
                        self.window_names[win_num] + " (press ESC to quit)", frames[f]
                    )
                    win_num += 1
        return win_num

    def __check_too_many_channels(self):
        for f_name, f in self.frames.items():
            for i in range(len(f)):
                if isinstance(f[i], Exception):
                    raise f[i]
                if (
                    isinstance(f[i], np.ndarray)
                    and f[i].shape[-1] not in [1, 3]
                    and len(f[i].shape) != 2
                ):
                    print(
                        f"Too many channels in output. (Got {f[i].shape[-1]} instead of 1 or 3.) "
                        f"Frame selection callback added."
                    )
                    print(
                        "Ctrl+scroll to change first channel.\n"
                        "Shift+scroll to change second channel.\n"
                        "Alt+scroll to change third channel."
                    )
                    sel = SelectChannels()
                    sel.enable_mouse_control()
                    sel.mouse_print_channels = True
                    self.callbacks.append(sel)
                    for fr in range(len(f)):
                        f[fr] = self.callbacks[-1](f[fr])
                    break

    def update_frames(self):
        """Update the windows with the newest data for all frames."""
        self.frames = {}

        for i in range(len(self.input_vid_global_names)):
            if self.input_vid_global_names[i] in self.FRAME_DICT and not isinstance(
                self.FRAME_DICT[self.input_vid_global_names[i]], NoData
            ):
                if self.input_vid_global_names[i] not in self.frames.keys():
                    self.frames[self.input_vid_global_names[i]] = []
                self.frames[self.input_vid_global_names[i]].append(
                    self.FRAME_DICT[self.input_vid_global_names[i]]
                )
                if len(self.callbacks) > 0:
                    for c in self.callbacks:
                        frame = c(self.frames[self.input_vid_global_names[i]][-1])
                        if frame is not None:
                            self.frames[self.input_vid_global_names[i]][-1] = frame
                if not self.silent:
                    self.__check_too_many_channels()
        if not self.silent:
            self.display_frames(self.frames)

    def update(self, arr: Union[List[np.ndarray], np.ndarray] = None, id: Union[List[str],str, List[int], int, None] = None):
        """Update window frames once. Optionally add a new input and input id."""
        if isinstance(arr, list):
            assert isinstance(id, list)
            return self._update_multiple(arr, id)
        elif arr is not None and id is not None:
            assert not isinstance(id, list)
            global_cv_display_callback(arr, id)
            if id not in self.input_cams:
                self.add_source(id)
                if not self.silent:
                    self.add_window(id)
        sub_cmd = window_commands.win_cmd_sub()
        self.update_frames()
        msg_cmd = sub_cmd.get()
        key = self.handle_keys(cv2.waitKey(1))
        if self.sock_list:
            for s, t in zip(self.sock_list, self.top_list):
                f = list(self.frames.values())
                if f:
                    s.send_multipart([t] + [encode_buffer(fr) for fr in f])
        return msg_cmd, key

    def _update_multiple(self, arr: Union[List[np.ndarray], np.ndarray] = None, id: Union[List[str], List[int]] = None):
        if arr is not None and id is not None:
            for arr_i, id_i in zip(arr, id):
                global_cv_display_callback(arr_i, id_i)  # type: ignore
                if id_i not in self.input_cams:
                    self.add_source(id_i)
                    if not self.silent:
                        self.add_window(id_i)

        sub_cmd = window_commands.win_cmd_sub()
        self.update_frames()
        msg_cmd = sub_cmd.get()
        key = self.handle_keys(cv2.waitKey(1))
        if self.sock_list:
            for s, t in zip(self.sock_list, self.top_list):
                f = list(self.frames.values())
                if f:
                    s.send_multipart([t] + [encode_buffer(fr) for fr in f])

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
        for t in self.close_threads:
            t.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def __del__(self):
        self.end()

    def __delete__(self, instance):
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

    def publish_to(self, address, topic=b""):
        """Publish the current video to the specified address and topic over a zmq publisher."""
        if self.ctx==None:
            self.ctx = zmq.Context()
        self.sock_list.append(self.ctx.socket(zmq.PUB))
        self.sock_list[-1].bind(address)
        self.top_list.append(topic)

    @property
    def cams(self):
        """Get the camera instances. Can be used for OpenCV or V4L2 functions, depending on backend."""
        return [CV_CAMS_DICT[v].cam_instance for v in self.input_vid_global_names]

    @property
    def busses(self):
        """Get the busses the cameras are plugged into. Can be used as UIDs. Requires V4L2 backend."""
        if get_bus_info_from_camera is not None:
            return [get_bus_info_from_camera(c) for c in self.cams]
        else:
            raise RuntimeError("Getting bus info not supported on this system")


def _get_video_callback_dict_threads(
    *vids,
    callbacks: Optional[Dict[Any, Union[FrameCallable, List[FrameCallable]]]] = None,
    fps=float("inf"),
    size=(-1, -1),
    force_backend="",
):
    assert callbacks is not None
    vid_threads = []
    for v in vids:
        v_name = uid_for_source(v)
        v_callbacks: List[Callable[[np.ndarray], Any]] = []
        if v_name in callbacks:
            if isinstance(callbacks[v_name], List):
                v_callbacks.extend(callbacks[v_name])  # type: ignore
            elif callable(callbacks[v_name]):
                v_callbacks.append(callbacks[v_name])  # type: ignore
        if v in callbacks:
            if isinstance(callbacks[v], List):
                v_callbacks.extend(callbacks[v])  # type: ignore
            elif callable(callbacks[v]):
                v_callbacks.append(callbacks[v])  # type: ignore
        vid_threads.append(
            FrameUpdater(
                v,
                callbacks=v_callbacks,
                fps_limit=fps,
                request_size=size,
                force_backend=force_backend,
            )
        )
    return vid_threads


def _get_video_threads(
    *vids,
    callbacks: Optional[
        Union[
            Dict[Any, Union[FrameCallable, List[FrameCallable]]],
            List[FrameCallable],
            FrameCallable,
        ]
    ] = None,
    fps=float("inf"),
    size=(-1, -1),
    force_backend="",
    mjpg=True
):
    vid_threads: List[Thread] = []
    if isinstance(callbacks, Dict):
        vid_threads = _get_video_callback_dict_threads(
            *vids, callbacks=callbacks, fps=fps, size=size
        )
    elif isinstance(callbacks, List):
        for v in vids:
            vid_threads.append(
                FrameUpdater(
                    v,
                    callbacks=callbacks,
                    fps_limit=fps,
                    request_size=size,
                    force_backend=force_backend,
                    mjpg=mjpg
                )
            )
    elif callable(callbacks):
        for v in vids:
            vid_threads.append(
                FrameUpdater(
                    v,
                    callbacks=[callbacks],
                    fps_limit=fps,
                    request_size=size,
                    force_backend=force_backend,
                    mjpg=mjpg
                )
            )
    else:
        for v in vids:
            if v is not None:
                vid_threads.append(
                    FrameUpdater(
                        v, fps_limit=fps, request_size=size, force_backend=force_backend, mjpg=mjpg
                    )
                )
    return vid_threads


def display(
    *vids,
    callbacks: Optional[
        Union[
            Dict[Any, Union[FrameCallable, List[FrameCallable]]],
            List[FrameCallable],
            FrameCallable,
        ]
    ] = None,
    window_names=None,
    blocking=False,
    fps_limit=float("inf"),
    size=(-1, -1),
    silent=False,
    force_backend="",
    mjpg=True
):
    """
    Display all the arrays, cameras, and videos passed in.

    callbacks can be a dictionary linking functions to videos, or a list of function or functions operating on the video
     data before displaying.
    Window names end up becoming the title of the windows
    """
    vid_threads = _get_video_threads(
        *vids,
        callbacks=callbacks,
        fps=fps_limit,
        size=size,
        force_backend=force_backend,
        mjpg=mjpg
    )
    for v in vid_threads:
        v.start()
    if window_names is None:
        window_names = ["window {}".format(i) for i in range(len(vids))]
    if blocking:
        SubscriberWindows(
            window_names=window_names, video_sources=vids, silent=silent
        ).loop()
        for vt in vid_threads:
            vt.join()
    else:
        s = SubscriberWindows(
            window_names=window_names, video_sources=vids, silent=silent
        )
        s.close_threads = vid_threads
        return s


def breakpoint_display(*args, **kwargs):
    """Display all the arrays, cameras, and videos passed in. Stops code execution until the window is closed."""
    return display(*args, **kwargs, blocking=True)


def read_updates(*args, **kwargs):
    """Read back all frame updates and yield a list of frames. List is empty if no frames were read."""
    return display(*args, **kwargs, silent=True)


def publish_updates(*args, address="tcp://127.0.0.1:7880", topic=b"", **kwargs):
    """Publish all the updates to the given address and topic."""
    if 'blocking' in kwargs and kwargs['blocking']:
        block = True
        kwargs['blocking'] = False
    else:
        block = False

    r = read_updates(*args, **kwargs)
    r.publish_to(address, topic)

    if block:
        r.loop()
        for vt in r.close_threads:
            vt.join()
    return r
