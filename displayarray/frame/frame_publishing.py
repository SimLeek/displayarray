"""Publish frames so any function within this program can find them."""

import asyncio
import sys
import threading
import time
import warnings

import cv2

using_pyv4l2cam = False
try:
    if sys.platform == "linux":
        from PyV4L2Cam.camera import Camera as pyv4lcamera
        from PyV4L2Cam.controls import ControlIDs as pyv4lcontrolids

        using_pyv4l2cam = True
except ImportError:
    warnings.warn("Could not import PyV4L2Cam on linux. Camera capture will be slow.")
    warnings.warn(
        "To install, run: pip install git+https://github.com/simleek/PyV4L2Cam.git"
    )

import numpy as np

from displayarray.frame import subscriber_dictionary
from .np_to_opencv import NpCam
from displayarray._uid import uid_for_source

from typing import Union, Tuple, Optional, Dict, Any, List, Callable

FrameCallable = Callable[[np.ndarray], Optional[np.ndarray]]


def _v4l2_convert_mjpeg(mjpeg: bytes) -> Optional[np.ndarray]:
    # Thanks: https://stackoverflow.com/a/21844162
    a = mjpeg.find(b"\xff\xd8")
    b = mjpeg.find(b"\xff\xd9")

    if a == -1 or b == -1:
        return None
    else:
        jpg = mjpeg[a : b + 2]
        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        return frame


def _v4l2_convert_rgb24(rgb24: bytes, width: int, height: int) -> Optional[np.ndarray]:
    nparr = np.frombuffer(rgb24, np.uint8)
    np_frame = nparr.reshape((height, width, 3))
    return np_frame


def pub_cam_loop_pyv4l2(
    cam_id: Union[int, str, np.ndarray],
    request_size: Tuple[int, int] = (-1, -1),
    high_speed: bool = True,
    fps_limit: float = float("inf"),
):
    """
    Publish whichever camera you select to CVCams.<cam_id>.Vid, using v4l2 instead of opencv.

    You can send a quit command 'quit' to CVCams.<cam_id>.Cmd
    Status information, such as failure to open, will be posted to CVCams.<cam_id>.Status

    :param high_speed: Selects mjpeg transferring, which most cameras seem to support, so speed isn't limited
    :param fps_limit: Limits the frames per second.
    :param cam_id: An integer representing which webcam to use, or a string representing a video file.
    :param request_size: A tuple with width, then height, to request the video size.
    :return: True if loop ended normally, False if it failed somehow.
    """
    name = uid_for_source(cam_id)

    if isinstance(cam_id, (int, str)):
        if isinstance(cam_id, int):
            cam: pyv4lcamera = pyv4lcamera(  # type: ignore
                f"/dev/video{cam_id}", *request_size
            )
        else:
            cam = pyv4lcamera(cam_id, *request_size)  # type: ignore
    else:
        raise TypeError(
            "Only strings or ints representing cameras are supported with v4l2."
        )

    subscriber_dictionary.register_cam(name)

    sub = subscriber_dictionary.cam_cmd_sub(name)
    sub.return_on_no_data = ""
    msg = ""

    if high_speed and cam.pixel_format != "MJPEG":
        warnings.warn("Camera does not support high speed.")

    now = time.time()
    while msg != "quit":
        time.sleep(1.0 / (fps_limit - (time.time() - now)))
        now = time.time()
        frame_bytes = cam.get_frame()  # type: bytes

        if cam.pixel_format == "MJPEG":
            nd_frame = _v4l2_convert_mjpeg(frame_bytes)
        elif cam.pixel_format == "RGB24":
            nd_frame = _v4l2_convert_rgb24(frame_bytes, cam.width, cam.height)
        else:
            raise NotImplementedError(f"{cam.pixel_format} format not supported.")

        if nd_frame is not None:
            subscriber_dictionary.CV_CAMS_DICT[name].frame_pub.publish(nd_frame)
        else:
            cam.close()
            subscriber_dictionary.CV_CAMS_DICT[name].status_pub.publish("failed")
            return False

        msg = sub.get()
    sub.release()

    cam.close()
    return True


def pub_cam_loop_opencv(
    cam_id: Union[int, str, np.ndarray],
    request_size: Tuple[int, int] = (-1, -1),
    high_speed: bool = True,
    fps_limit: float = float("inf"),
    extra: Optional[List[Tuple[int, int]]] = None,
) -> bool:
    """
    Publish whichever camera you select to CVCams.<cam_id>.Vid.

    You can send a quit command 'quit' to CVCams.<cam_id>.Cmd
    Status information, such as failure to open, will be posted to CVCams.<cam_id>.Status

    :param high_speed: Selects mjpeg transferring, which most cameras seem to support, so speed isn't limited
    :param fps_limit: Limits the frames per second.
    :param cam_id: An integer representing which webcam to use, or a string representing a video file.
    :param request_size: A tuple with width, then height, to request the video size.
    :return: True if loop ended normally, False if it failed somehow.
    """
    name = uid_for_source(cam_id)

    if isinstance(cam_id, (int, str)):
        cam: Union[NpCam, cv2.VideoCapture] = cv2.VideoCapture(cam_id)
    elif isinstance(cam_id, np.ndarray):
        cam = NpCam(cam_id)
    else:
        raise TypeError(
            "Only strings or ints representing cameras, or numpy arrays representing pictures supported."
        )

    subscriber_dictionary.register_cam(name)

    frame_counter = 0

    sub = subscriber_dictionary.cam_cmd_sub(name)
    sub.return_on_no_data = ""
    msg = ""

    if high_speed:
        cam.set(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG)

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, request_size[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, request_size[1])

    if not cam.isOpened():
        subscriber_dictionary.CV_CAMS_DICT[name].status_pub.publish("failed")
        return False
    now = time.time()
    while msg != "quit":
        time.sleep(1.0 / (fps_limit - (time.time() - now)))
        now = time.time()
        (ret, frame) = cam.read()  # type: Tuple[bool, np.ndarray ]
        if ret is False or not isinstance(frame, np.ndarray):
            cam.release()
            subscriber_dictionary.CV_CAMS_DICT[name].status_pub.publish("failed")
            return False
        if cam.get(cv2.CAP_PROP_FRAME_COUNT) > 0:
            frame_counter += 1
            if frame_counter >= cam.get(cv2.CAP_PROP_FRAME_COUNT):
                frame_counter = 0
                cam = cv2.VideoCapture(cam_id)
        subscriber_dictionary.CV_CAMS_DICT[name].frame_pub.publish(frame)
        msg = sub.get()
    sub.release()

    cam.release()
    return True


uid_dict: Dict[str, threading.Thread] = {}


def pub_cam_thread(
    cam_id: Union[int, str],
    request_ize: Tuple[int, int] = (-1, -1),
    high_speed: bool = True,
    fps_limit: float = float("inf"),
) -> threading.Thread:
    """Run pub_cam_loop in a new thread. Starts on creation."""

    name = uid_for_source(cam_id)
    if name in uid_dict.keys():
        t = uid_dict[name]
    else:
        if (
            sys.platform == "linux"
            and using_pyv4l2cam
            and (
                isinstance(cam_id, int)
                or (isinstance(cam_id, str) and "/dev/video" in cam_id)
            )
        ):
            pub_cam_loop = pub_cam_loop_pyv4l2
        else:
            pub_cam_loop = pub_cam_loop_opencv

        t = threading.Thread(
            target=pub_cam_loop, args=(cam_id, request_ize, high_speed, fps_limit)
        )
        uid_dict[name] = t
        t.start()
    return t


async def publish_updates_zero_mq(
    *vids,
    callbacks: Optional[
        Union[Dict[Any, FrameCallable], List[FrameCallable], FrameCallable]
    ] = None,
    fps_limit=float("inf"),
    size=(-1, -1),
    end_callback: Callable[[], bool] = lambda: False,
    blocking=False,
    publishing_address="tcp://127.0.0.1:5600",
    prepend_topic="",
    flags=0,
    copy=True,
    track=False,
):
    """Publish frames to ZeroMQ when they're updated."""
    import zmq
    from displayarray import read_updates

    ctx = zmq.Context()
    s = ctx.socket(zmq.PUB)
    s.bind(publishing_address)

    if not blocking:
        flags |= zmq.NOBLOCK

    try:
        for v in read_updates(vids, callbacks, fps_limit, size, end_callback, blocking):
            if v:
                for vid_name, frame in v.items():
                    md = dict(
                        dtype=str(frame.dtype),
                        shape=frame.shape,
                        name=prepend_topic + vid_name,
                    )
                    s.send_json(md, flags | zmq.SNDMORE)
                    s.send(frame, flags, copy=copy, track=track)
            if fps_limit:
                await asyncio.sleep(1.0 / fps_limit)
            else:
                await asyncio.sleep(0)
    except KeyboardInterrupt:
        pass
    finally:
        vid_names = [uid_for_source(name) for name in vids]
        for v in vid_names:
            subscriber_dictionary.stop_cam(v)


async def publish_updates_ros(
    *vids,
    callbacks: Optional[
        Union[Dict[Any, FrameCallable], List[FrameCallable], FrameCallable]
    ] = None,
    fps_limit=float("inf"),
    size=(-1, -1),
    end_callback: Callable[[], bool] = lambda: False,
    blocking=False,
    node_name="displayarray",
    publisher_name="npy",
    rate_hz=None,
    dtype=None,
):
    """Publish frames to ROS when they're updated."""
    import rospy
    from rospy.numpy_msg import numpy_msg
    import std_msgs.msg
    from displayarray import read_updates

    def get_msg_type(dtype):
        if dtype is None:
            msg_type = {
                np.float32: std_msgs.msg.Float32(),
                np.float64: std_msgs.msg.Float64(),
                np.bool: std_msgs.msg.Bool(),
                np.char: std_msgs.msg.Char(),
                np.int16: std_msgs.msg.Int16(),
                np.int32: std_msgs.msg.Int32(),
                np.int64: std_msgs.msg.Int64(),
                np.str: std_msgs.msg.String(),
                np.uint16: std_msgs.msg.UInt16(),
                np.uint32: std_msgs.msg.UInt32(),
                np.uint64: std_msgs.msg.UInt64(),
                np.uint8: std_msgs.msg.UInt8(),
            }[dtype]
        else:
            msg_type = (
                dtype  # allow users to use their own custom messages in numpy arrays
            )
        return msg_type

    publishers: Dict[str, rospy.Publisher] = {}
    rospy.init_node(node_name, anonymous=True)
    try:
        for v in read_updates(vids, callbacks, fps_limit, size, end_callback, blocking):
            if v:
                if rospy.is_shutdown():
                    break
                for vid_name, frame in v.items():
                    if vid_name not in publishers:
                        dty = frame.dtype if dtype is None else dtype
                        publishers[vid_name] = rospy.Publisher(
                            publisher_name + vid_name,
                            numpy_msg(get_msg_type(dty)),
                            queue_size=10,
                        )
                    publishers[vid_name].publish(frame)
            if rate_hz:
                await asyncio.sleep(1.0 / rate_hz)
            else:
                await asyncio.sleep(0)
    except KeyboardInterrupt:
        pass
    finally:
        vid_names = [uid_for_source(name) for name in vids]
        for v in vid_names:
            subscriber_dictionary.stop_cam(v)
    if rospy.core.is_shutdown():
        raise rospy.exceptions.ROSInterruptException("rospy shutdown")
