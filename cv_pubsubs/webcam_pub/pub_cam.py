import pubsub
import cv2
import numpy as np
import time
import threading
from .listen_default import listen_default

if False:
    from typing import Union, Tuple


def pub_cam_loop(cam_id,  # type: Union[int, str]
                 request_size=(1280, 720),  # type: Tuple[int, int]
                 high_speed=False,  # type: bool
                 fps_limit=240  # type: float
                 ):  # type: (...)->bool
    """Publishes whichever camera you select to cvcams.<cam_id>.vid
    You can send a quit command 'q' to cvcams.<cam_id>.cmd
    Status information, such as failure to open, will be posted to cvcams.<cam_id>.status


    :param high_speed: Selects mjpeg transferring, which most cameras seem to support, so speed isn't limited
    :param fps_limit: Limits the frames per second.
    :param cam_id: An integer representing which webcam to use, or a string representing a video file.
    :param request_size: A tuple with width, then height, to request the video size.
    :return: True if loop ended normally, False if it failed somehow.
    """
    sub = pubsub.subscribe("cvcams." + str(cam_id) + ".cmd")
    msg = ''
    cam = cv2.VideoCapture(cam_id)
    # cam.set(cv2.CAP_PROP_CONVERT_RGB, 0)

    if high_speed:
        cam.set(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG)

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, request_size[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, request_size[1])

    if not cam.isOpened():
        pubsub.publish("cvcams." + str(cam_id) + ".status", "failed")
        return False
    now = time.time()
    while msg != 'q':
        time.sleep(1. / (fps_limit - (time.time() - now)))
        now = time.time()
        (ret, frame) = cam.read()  # type: Tuple[bool, np.ndarray ]
        if ret is False or not isinstance(frame, np.ndarray):
            cam.release()
            pubsub.publish("cvcams." + str(cam_id) + ".status", "failed")
            return False
        pubsub.publish("cvcams." + str(cam_id) + ".vid", (frame,))
        msg = listen_default(sub, block=False, empty='')

    cam.release()
    return True


def pub_cam_thread(cam_id,  # type: Union[int, str]
                   request_ize=(1280, 720),  # type: Tuple[int, int]
                   high_speed=False,  # type: bool
                   fps_limit=240  # type: float
                   ):
    # type: (...) -> threading.Thread
    t = threading.Thread(target=pub_cam_loop, args=(cam_id, request_ize, high_speed, fps_limit))
    t.start()
    return t
