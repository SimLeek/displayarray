"""Publish frames so any function within this program can find them."""

import asyncio
import sys
import threading
import time
import warnings
from typing import Union, Tuple, Optional, List, Iterator, Dict

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
    # while this is still good for raspberry pi, OpenCV tends to be faster for normal computers.
    if sys.platform == "linux":
        warnings.warn("Could not import PyV4L2Cam on linux. Camera capture will be slow.")
        warnings.warn(
            "To install, run: pip install git+https://github.com/simleek/PyV4L2Cam.git"
        )

import numpy as np

from displayarray.frame import subscriber_dictionary
from .np_to_opencv import NpCam
from .zmq_to_opencv import ZmqCam
from displayarray._uid import uid_for_source

try:
    import torch
    pytorch_available = True
except ImportError:
    pytorch_available = False

try:
    import scipy
    scipy_available = True
except ImportError:
    scipy_available = False

from typing import Union, Tuple, Optional, Dict, Any, List, Callable

FrameCallable = Callable[[np.ndarray], Optional[np.ndarray]]

# todo: if we need more accurate framerates, we'll just have to use a PID, Adam, or other optimizer
#  spinwait is accurate, but uses too much compute and slows down other operations
#  sleep doesn't use compute, but is inaccurate
#  using an optimizer would allow automatically changing the 1.0/fps in sleep to 0.9 ot 1.1 to make sleep more accurate
def spinwait_us(delay):
    #  thx: https://stackoverflow.com/a/74247651/782170
    target = time.perf_counter_ns() + delay * 1000
    while time.perf_counter_ns() < target:
        time.sleep(0)

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
        #spinwait_us(1000000 / (fps_limit - (time.time() - now)))
        time.sleep(1.0/(fps_limit - (time.time() - now)))
        now = time.time()
        frame_bytes = cam.get_frame()  # type: bytes

        if cam.dest_pixel_format == "MJPEG":
            nd_frame = convert_mjpeg(frame_bytes)  # type: ignore
        elif cam.dest_pixel_format == "RGB24":
            nd_frame = convert_rgb24(frame_bytes, cam.width, cam.height)  # type: ignore
        else:
            raise NotImplementedError(f"{cam.pixel_format} format not supported.")

        if nd_frame is not None:
            try:
                subscriber_dictionary.CV_CAMS_DICT[name].frame_pub.publish(nd_frame)
            except KeyError:  # not sure why this happens, but I know I want it to exit correctly in this case
                cam.close()
                break
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
    elif ((isinstance(cam_id, (np.ndarray)) or
          (scipy_available and isinstance(cam_id, scipy.sparse.csr_matrix))) or
          (pytorch_available and isinstance(cam_id, torch.Tensor) and cam_id.layout==torch.sparse_csr)):
        cam = NpCam(cam_id)
    else:
        raise TypeError(
            "Only strings or ints representing cameras, or numpy arrays representing pictures supported."
        )

    if fps_limit == float("inf"):
        fps_limit = cam.get(cv2.CAP_PROP_FPS)
        if fps_limit is None:
            fps_limit = float("inf")

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
    count = cam.get(cv2.CAP_PROP_FRAME_COUNT)

    if not cam.isOpened():
        subscriber_dictionary.CV_CAMS_DICT[name].status_pub.publish("failed")
        return False
    now = time.time()
    while msg != "quit":
        (ret, frame) = cam.read()  # type: Tuple[bool, np.ndarray ]
        if ret is False or frame is None:
            cam.release()
            if count>0:  # sometimes mp4s just fail
                frame_counter = 0
                cam = cv2.VideoCapture(cam_id)
            else:
                subscriber_dictionary.CV_CAMS_DICT[name].status_pub.publish("failed")
                return False
        if count > 0:
            frame_counter += 1
            if frame_counter >= count-1:
                frame_counter = 0
                cam.release()
                cam = cv2.VideoCapture(cam_id)
        time2 = time.time()
        time.sleep(1.0 / (fps_limit - (time2 - now)))
        #spinwait_us(1000000 / (fps_limit - (time2 - now)))
        now = time.time()
        try:
            subscriber_dictionary.CV_CAMS_DICT[name].frame_pub.publish(frame)
        except KeyError:  # we got deleted. Time to exit.
            cam.release()
            return False
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
    t = None
    if name in uid_dict.keys():
        t = uid_dict[name]
    if t is None or not t.is_alive():  # Enables reopening cameras
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

class PubCamCV:
    """Iterator class to yield a dictionary of frames from one or more video sources without threading."""
    def __init__(
        self,
        cam_id: Union[int, str, np.ndarray, List[Union[int, str, np.ndarray]]],
        request_size: Union[Tuple[int, int], List[Tuple[int, int]]] = (-1, -1),
        mjpg: bool = True,
        fps_limit: float = None,
        extra: Optional[List[Tuple[int, int]]] = None
    ):
        self.mjpg = mjpg
        self.fps_limit = fps_limit
        self.extra = extra
        self.last_frame_time = time.time()

        # Convert single cam_id to list for uniform handling
        self.cam_ids = [cam_id] if not isinstance(cam_id, list) else cam_id
        # Convert single request_size to list for all cameras
        if isinstance(request_size, tuple):
            self.request_sizes = [request_size] * len(self.cam_ids)
        else:
            self.request_sizes = request_size
            if len(self.request_sizes) != len(self.cam_ids):
                raise ValueError("Number of request_sizes must match number of cam_ids")

        # Initialize cameras
        self.cams = []
        self.frame_counters = []
        self.frame_counts = []
        for cam_id, req_size in zip(self.cam_ids, self.request_sizes):
            cam, frame_count = self._init_camera(cam_id, req_size)
            self.cams.append(cam)
            self.frame_counters.append(0)
            self.frame_counts.append(frame_count)

        # Set FPS limit (use minimum FPS from all cameras if inf)
        if self.fps_limit == None:
            fps_values = [cam.get(cv2.CAP_PROP_FPS) or float("inf") for cam in self.cams]
            self.fps_limit = min(fps_values)
        self.frame_interval = 1.0 / self.fps_limit if self.fps_limit != float("inf") else 0

    def _init_camera(self, cam_id: Union[int, str, np.ndarray], request_size: Tuple[int, int]) -> Tuple[Union[cv2.VideoCapture, NpCam, ZmqCam], float]:
        """Initialize a single camera or video source."""
        if isinstance(cam_id, (int, str)):
            if isinstance(cam_id, str) and cam_id.startswith('tcp'):
                cam = ZmqCam(cam_id)
            else:
                cam = cv2.VideoCapture(cam_id)
        elif ((isinstance(cam_id, np.ndarray)) or
              (scipy_available and isinstance(cam_id, scipy.sparse.csr_matrix)) or
              (pytorch_available and isinstance(cam_id, torch.Tensor) and cam_id.layout == torch.sparse_csr)):
            cam = NpCam(cam_id)
        else:
            raise TypeError(
                "Only strings or ints representing cameras, or numpy arrays representing pictures supported."
            )

        # Configure camera
        if self.mjpg and isinstance(cam, cv2.VideoCapture):
            try:
                cam.set(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG)
            except AttributeError:
                warnings.warn("Please update OpenCV")
        if isinstance(cam, cv2.VideoCapture):
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, request_size[0])
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, request_size[1])
        frame_count = cam.get(cv2.CAP_PROP_FRAME_COUNT)

        if not cam.isOpened():
            raise RuntimeError(f"Failed to open camera or video source: {cam_id}")

        return cam, frame_count

    def __iter__(self) -> Iterator[Dict[Union[int, str, np.ndarray], Optional[np.ndarray]]]:
        """Yield a dictionary mapping cam_id to frames from all video sources with FPS limiting."""
        while True:
            start_time = time.time()
            frame_dict = {}
            any_valid = False

            for i, (cam, cam_id, frame_count, req_size) in enumerate(zip(self.cams, self.cam_ids, self.frame_counts, self.request_sizes)):
                ret, frame = cam.read()
                if not ret or frame is None:
                    if frame_count > 0:  # Loop video
                        self.frame_counters[i] = 0
                        cam.release()
                        cam, frame_count = self._init_camera(cam_id, req_size)
                        self.cams[i] = cam
                        self.frame_counts[i] = frame_count
                        ret, frame = cam.read()
                    else:
                        frame_dict[cam_id] = None
                        continue
                if ret and frame is not None:
                    any_valid = True
                    frame_dict[cam_id] = frame
                else:
                    frame_dict[cam_id] = None

                if frame_count > 0:
                    self.frame_counters[i] += 1
                    if self.frame_counters[i] >= frame_count - 1:
                        self.frame_counters[i] = 0
                        cam.release()
                        cam, frame_count = self._init_camera(cam_id, req_size)
                        self.cams[i] = cam
                        self.frame_counts[i] = frame_count

            if not any_valid:
                break

            # Yield the dictionary of frames
            yield frame_dict

            # FPS limiting
            elapsed = time.time() - start_time
            sleep_time = max(0, self.frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def __del__(self):
        """Clean up all camera resources."""
        for cam in self.cams:
            cam.release()