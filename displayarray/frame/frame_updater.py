"""Get and handle updated frames."""

import threading
import asyncio
from typing import Union, Tuple, Any, Callable, List, Optional, Dict

import numpy as np

from displayarray.callbacks import global_cv_display_callback
from displayarray._uid import uid_for_source
from displayarray.frame import subscriber_dictionary
from displayarray.frame.frame_publishing import pub_cam_thread
from displayarray.window import window_commands
from displayarray.effects.select_channels import SelectChannels
from localpubsub import NoData

FrameCallable = Callable[[np.ndarray], Optional[np.ndarray]]


class FrameUpdater(threading.Thread):
    """Thread for updating frames from a video source."""

    def __init__(
        self,
        video_source: Union[int, str, np.ndarray] = 0,
        callbacks: Optional[Union[List[FrameCallable], FrameCallable]] = None,
        request_size: Tuple[int, int] = (-1, -1),
        mjpg: bool = True,
        fps_limit: float = float("inf"),
        force_backend="",
    ):
        """Create the frame updater thread."""
        super(FrameUpdater, self).__init__(target=self.loop, args=())
        self.cam_id = uid_for_source(video_source)
        self.video_source = video_source
        if callbacks is None:
            callbacks = []
        if callable(callbacks):
            self.callbacks = [callbacks]
        else:
            self.callbacks = callbacks
        self.request_size = request_size
        self.mjpg = mjpg
        self.fps_limit = fps_limit
        self.exception_raised = None
        self.force_backend = force_backend

    def __wait_for_cam_id(self):
        while str(self.cam_id) not in subscriber_dictionary.CV_CAMS_DICT:
            continue

    def __apply_callbacks_to_frame(self, frame):
        if frame is not None and not isinstance(frame, NoData):
            try:
                for c in self.callbacks:
                    frame_c = c(frame)
                    if frame_c is not None:
                        frame = frame_c
                if (
                    isinstance(frame, np.ndarray)
                    and frame.shape[-1] not in [1, 3]
                    and len(frame.shape) != 2
                ):
                    print(
                        f"Too many channels in output. (Got {frame.shape[-1]} instead of 1 or 3.) "
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
                    frame = self.callbacks[-1](frame)
            except Exception as e:
                self.exception_raised = e
                frame = self.exception_raised
                subscriber_dictionary.stop_cam(self.cam_id)
                window_commands.quit()
                raise e
            global_cv_display_callback(frame, self.cam_id)

    def loop(self):
        """Continually get frames from the video publisher, run callbacks on them, and listen to commands."""
        t = pub_cam_thread(
            self.video_source,
            self.request_size,
            self.mjpg,
            self.fps_limit,
            self.force_backend,
        )
        self.__wait_for_cam_id()

        sub_cam = subscriber_dictionary.cam_frame_sub(str(self.cam_id))
        sub_owner = subscriber_dictionary.handler_cmd_sub(str(self.cam_id))
        msg_owner = sub_owner.return_on_no_data = ""
        try:
            while msg_owner != "quit":
                frame = sub_cam.get(blocking=True, timeout=1.0)  # type: np.ndarray
                self.__apply_callbacks_to_frame(frame)
                msg_owner = sub_owner.get()
        except Exception as e:
            raise e
        finally:
            sub_owner.release()
            sub_cam.release()
            subscriber_dictionary.stop_cam(self.cam_id)
            t.join()

    def display(self, callbacks: List[Callable[[np.ndarray], Any]] = None):
        """
        Start default display operation.

        For multiple video sources, please use something outside of this class.

        :param callbacks: List of callbacks to be run on frames before displaying to the screen.
        """
        from displayarray.window import SubscriberWindows

        if callbacks is None:
            callbacks = []
        self.start()
        SubscriberWindows(video_sources=[self.cam_id], callbacks=callbacks).loop()
        self.join()
        if self.exception_raised is not None:
            raise self.exception_raised


'''async def read_updates(
    *vids,
    callbacks: Optional[
        Union[
            Dict[Any, Union[FrameCallable, List[FrameCallable]]],
            List[FrameCallable],
            FrameCallable,
        ]
    ] = None,
    fps_limit=float("inf"),
    size=(-1, -1),
    end_callback: Callable[[], bool] = lambda: False,
    blocking=True,
):
    """
    Read back all updates from the requested videos.

    Examp#le usage:

    .. co#de-block:: python

      >>#> from examples.videos import test_video
      >>#> f = 0
      >>#> for f, r in enumerate(read_updates(test_video, end_callback=lambda :f==2)):
      ..#.   print(f"Frame:{f}. Array:{r}")

    """
    from displayarray.window import SubscriberWindows
    from displayarray.window.subscriber_windows import _get_video_threads

    vid_names = [uid_for_source(name) for name in vids]
    vid_threads = _get_video_threads(
        *vids, callbacks=callbacks, fps=fps_limit, size=size
    )
    for v in vid_threads:
        v.start()

    while not end_callback():
        vid_update_dict = {}
        dict_was_updated = False
        for i in range(len(vid_names)):
            if vid_names[i] in SubscriberWindows.FRAME_DICT and not isinstance(
                SubscriberWindows.FRAME_DICT[vid_names[i]], NoData
            ):
                vid_update_dict[vid_names[i]] = SubscriberWindows.FRAME_DICT[
                    vid_names[i]
                ]
                if (
                    isinstance(vid_update_dict[vid_names[i]], np.ndarray)
                    and len(vid_update_dict[vid_names[i]].shape) <= 3
                ):
                    vid_update_dict[vid_names[i]] = [vid_update_dict[vid_names[i]]]
                dict_was_updated = True
        if dict_was_updated or not blocking:
            yield vid_update_dict
        await asyncio.sleep(0)
    for v in vid_names:
        subscriber_dictionary.stop_cam(v)
    for v in vid_threads:
        v.join()'''


async def read_updates_zero_mq(
    *topic_names,
    address: str = "tcp://127.0.0.1:5600",
    flags: int = 0,
    copy: bool = True,
    track: bool = False,
    blocking: bool = False,
    end_callback: Callable[[Any], bool] = lambda x: False,
):
    """Read updated frames from ZeroMQ."""
    import zmq

    ctx = zmq.Context()
    s = ctx.socket(zmq.SUB)
    s.connect(address)
    if not blocking:
        flags |= zmq.NOBLOCK

    for topic in topic_names:
        s.setsockopt(zmq.SUBSCRIBE, topic)
    cb_val = False
    while not cb_val:
        try:
            md = s.recv_json(flags=flags)
            msg = s.recv(flags=flags, copy=copy, track=track)
            buf = memoryview(msg)
            arr = np.frombuffer(buf, dtype=md["dtype"])
            arr.reshape(md["shape"])
            name = md["name"]
            cb_val = end_callback(md)
            yield name, arr
        except zmq.ZMQError as e:
            if isinstance(e, zmq.Again):
                pass  # no messages to receive
            else:
                raise e
        finally:
            await asyncio.sleep(0)


async def read_updates_ros(
    *topic_names,
    dtypes=None,
    listener_node_name=None,
    poll_rate_hz=None,
    end_callback: Callable[[Any], bool] = lambda x: False,
):
    """Read updated frames from ROS."""
    import rospy
    from rospy.numpy_msg import numpy_msg
    from rospy.client import _WFM
    import std_msgs.msg
    import random
    import string

    if dtypes is None:
        raise ValueError(
            "ROS cannot automatically determine the types of incoming numpy arrays. Please specify.\n"
            "Options are: \n"
            "\tfloat32, float64, bool, char, int16, "
            "\tint32, int64, str, uint16, uint32, uint64, uint8"
        )

    if listener_node_name is None:
        # https://stackoverflow.com/a/2257449
        listener_node_name = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        )

    rospy.init_node(listener_node_name)

    msg_types = [
        {
            np.float32: std_msgs.msg.Float32(),
            np.float64: std_msgs.msg.Float64(),
            np.bool: std_msgs.msg.Bool(),  # type: ignore
            np.char: std_msgs.msg.Char(),
            np.int16: std_msgs.msg.Int16(),
            np.int32: std_msgs.msg.Int32(),
            np.int64: std_msgs.msg.Int64(),
            np.str: std_msgs.msg.String(),  # type: ignore
            np.uint16: std_msgs.msg.UInt16(),
            np.uint32: std_msgs.msg.UInt32(),
            np.uint64: std_msgs.msg.UInt64(),
            np.uint8: std_msgs.msg.UInt8(),
            "float32": std_msgs.msg.Float32(),
            "float64": std_msgs.msg.Float64(),
            "bool": std_msgs.msg.Bool(),
            "char": std_msgs.msg.Char(),
            "int16": std_msgs.msg.Int16(),
            "int32": std_msgs.msg.Int32(),
            "int64": std_msgs.msg.Int64(),
            "str": std_msgs.msg.String(),
            "uint16": std_msgs.msg.UInt16(),
            "uint32": std_msgs.msg.UInt32(),
            "uint64": std_msgs.msg.UInt64(),
            "uint8": std_msgs.msg.UInt8(),
        }.get(
            dtype, dtype
        )  # allow users to use their own custom messages in numpy arrays
        for dtype in dtypes
    ]
    s = None
    cb_val = False
    try:
        wfms = {t: _WFM() for t in topic_names}
        s = {
            t: rospy.Subscriber(t, numpy_msg(msg_types[i]), wfms[t].cb)
            for i, t in enumerate(topic_names)
        }
        while not cb_val:
            while not rospy.core.is_shutdown():
                if poll_rate_hz:
                    await asyncio.sleep(1.0 / poll_rate_hz)
                else:
                    await asyncio.sleep(0)
                for t, w in wfms.items():
                    if w.msg is not None:
                        yield t, w.msg
                        cb_val = end_callback(w.msg)
                        w.msg = None
    except KeyboardInterrupt:
        pass
    finally:
        if s is not None:
            for _, sub in s.items():
                sub.unregister()
    if rospy.core.is_shutdown():
        raise rospy.exceptions.ROSInterruptException("rospy shutdown")
