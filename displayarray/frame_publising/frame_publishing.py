import threading
import time

import cv2
import numpy as np

from displayarray.frame_publising import subscriber_dictionary
from .np_to_opencv import NpCam
from displayarray.uid import uid_for_source

from typing import Union, Tuple


def pub_cam_loop(
    cam_id: Union[int, str],
    request_size: Tuple[int, int] = (1280, 720),
    high_speed: bool = False,
    fps_limit: float = 240,
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

    # cam.set(cv2.CAP_PROP_CONVERT_RGB, 0)
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


def pub_cam_thread(
    cam_id: Union[int, str],
    request_ize: Tuple[int, int] = (1280, 720),
    high_speed: bool = False,
    fps_limit: float = 240,
) -> threading.Thread:
    """Run pub_cam_loop in a new thread."""
    t = threading.Thread(
        target=pub_cam_loop, args=(cam_id, request_ize, high_speed, fps_limit)
    )
    t.start()
    return t
