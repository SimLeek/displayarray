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
        from PyV4L2Cam.camera import Camera as pyv4lcamera  # type: ignore
        from PyV4L2Cam.controls import ControlIDs as pyv4lcontrolids  # type: ignore
        from PyV4L2Cam import convert_mjpeg, convert_rgb24  # type: ignore
        from PyV4L2Cam.get_camera import get_camera_by_bus_info, get_camera_by_string  # type: ignore

        using_pyv4l2cam = True
except ImportError:
    warnings.warn("Could not import PyV4L2Cam on linux. Camera capture will be slow.")
    warnings.warn(
        "To install, run: pip install git+https://github.com/simleek/PyV4L2Cam.git"
    )

import numpy as np

from displayarray.frame import subscriber_dictionary
from .np_to_opencv import NpCam
from .zmq_to_opencv import ZmqCam
from displayarray._uid import uid_for_source

from typing import Union, Tuple, Optional, Dict, Any, List, Callable

FrameCallable = Callable[[np.ndarray], Optional[np.ndarray]]


def pub_cam_loop_pyv4l2(
    cam_id: Union[int, str, np.ndarray],
    request_size: Tuple[int, int] = (-1, -1),
    mjpg: bool = True,
    fps_limit: float = float("inf"),
):
    """
    Publish whichever camera you select to CVCams.<cam_id>.Vid, using v4l2 instead of opencv.

    You can send a quit command 'quit' to CVCams.<cam_id>.Cmd
    Status information, such as failure to open, will be posted to CVCams.<cam_id>.Status

    :param mjpg: Selects mjpeg transferring, which most cameras seem to support, so speed isn't limited
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
            if "usb" in cam_id:
                cam = get_camera_by_bus_info(cam_id, *request_size)  # type: ignore
            else:
                cam = get_camera_by_string(cam_id, *request_size)  # type: ignore
    else:
        raise TypeError(
            "Only strings or ints representing cameras are supported with v4l2."
        )

    subscriber_dictionary.register_cam(name, cam)

    sub = subscriber_dictionary.cam_cmd_sub(name)
    sub.return_on_no_data = ""
    msg = ""

    if mjpg and cam.pixel_format != "MJPEG":
        warnings.warn("Camera does not support high speed.")

    now = time.time()
    while msg != "quit":
        time.sleep(1.0 / (fps_limit - (time.time() - now)))
        now = time.time()
        frame_bytes = cam.get_frame()  # type: bytes

        if cam.pixel_format == "MJPEG":
            nd_frame = convert_mjpeg(frame_bytes)  # type: ignore
        elif cam.pixel_format == "RGB24":
            nd_frame = convert_rgb24(frame_bytes, cam.width, cam.height)  # type: ignore
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
    mjpg: bool = True,
    fps_limit: float = float("inf"),
    extra: Optional[List[Tuple[int, int]]] = None,
) -> bool:
    """
    Publish whichever camera you select to CVCams.<cam_id>.Vid.

    You can send a quit command 'quit' to CVCams.<cam_id>.Cmd
    Status information, such as failure to open, will be posted to CVCams.<cam_id>.Status

    :param mjpg: Selects mjpeg transferring, which most cameras seem to support, so speed isn't limited
    :param fps_limit: Limits the frames per second.
    :param cam_id: An integer representing which webcam to use, or a string representing a video file.
    :param request_size: A tuple with width, then height, to request the video size.
    :return: True if loop ended normally, False if it failed somehow.
    """
    name = uid_for_source(cam_id)

    cam: Union[NpCam, ZmqCam, cv2.VideoCapture]
    if isinstance(cam_id, (int, str)):
        if isinstance(cam_id, str) and cam_id.startswith('tcp'):
            cam = ZmqCam(cam_id)
        else:
            cam = cv2.VideoCapture(cam_id)
    elif isinstance(cam_id, (np.ndarray)):
        cam = NpCam(cam_id)
    else:
        raise TypeError(
            "Only strings or ints representing cameras, or numpy arrays representing pictures supported."
        )

    subscriber_dictionary.register_cam(name, cam)

    frame_counter = 0

    sub = subscriber_dictionary.cam_cmd_sub(name)
    sub.return_on_no_data = ""
    msg = ""

    if mjpg:
        try:
            cam.set(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG)
        except AttributeError:
            warnings.warn("Please update OpenCV")

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
        if ret is False or not isinstance(frame, (np.ndarray, list)):
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
    mjpg: bool = True,
    fps_limit: float = float("inf"),
    force_backend="",
) -> threading.Thread:
    """Run pub_cam_loop in a new thread. Starts on creation."""

    name = uid_for_source(cam_id)
    if name in uid_dict.keys():
        t = uid_dict[name]
    else:
        if "cv" in force_backend.lower():
            pub_cam_loop = pub_cam_loop_opencv
        elif (
            sys.platform == "linux"
            and using_pyv4l2cam
            and (
                isinstance(cam_id, int)
                or (
                    isinstance(cam_id, str)
                    and any(["/dev/video" in cam_id, "usb" in cam_id])
                )
            )
        ) or "v4l2" in force_backend.lower():
            pub_cam_loop = pub_cam_loop_pyv4l2  # type: ignore
        else:
            pub_cam_loop = pub_cam_loop_opencv

        t = threading.Thread(
            target=pub_cam_loop, args=(cam_id, request_ize, mjpg, fps_limit)
        )
        uid_dict[name] = t
        t.start()
    return t
