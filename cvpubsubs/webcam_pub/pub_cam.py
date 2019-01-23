import threading
import time


import cv2
import numpy as np

from cvpubsubs.webcam_pub.camctrl import CamCtrl
from .np_cam import NpCam

if False:
    from typing import Union, Tuple


def pub_cam_loop(cam_id,  # type: Union[int, str]
                 request_size=(1280, 720),  # type: Tuple[int, int]
                 high_speed=False,  # type: bool
                 fps_limit=240  # type: float
                 ):  # type: (...)->bool
    """Publishes whichever camera you select to CVCams.<cam_id>.Vid
    You can send a quit command 'quit' to CVCams.<cam_id>.Cmd
    Status information, such as failure to open, will be posted to CVCams.<cam_id>.Status


    :param high_speed: Selects mjpeg transferring, which most cameras seem to support, so speed isn't limited
    :param fps_limit: Limits the frames per second.
    :param cam_id: An integer representing which webcam to use, or a string representing a video file.
    :param request_size: A tuple with width, then height, to request the video size.
    :return: True if loop ended normally, False if it failed somehow.
    """

    if isinstance(cam_id, (int, str)):
        name = str(cam_id)
    elif isinstance(cam_id, np.ndarray):
        name = str(hash(str(cam_id)))
    else:
        raise TypeError("Only strings or ints representing cameras, or numpy arrays representing pictures supported.")

    if isinstance(cam_id, (int, str)):
        cam = cv2.VideoCapture(cam_id)
    elif isinstance(cam_id, np.ndarray):
        cam = NpCam(cam_id)  # type: NpCam
    else:
        raise TypeError("Only strings or ints representing cameras, or numpy arrays representing pictures supported.")

    CamCtrl.register_cam(name)

    # cam.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    frame_counter = 0

    sub = CamCtrl.cam_cmd_sub(name)
    sub.return_on_no_data = ''
    msg = ''

    if high_speed:
        cam.set(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG)

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, request_size[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, request_size[1])

    if not cam.isOpened():
        CamCtrl.cv_cams_dict[name].status_pub.publish("failed")
        return False
    now = time.time()
    while msg != 'quit':
        time.sleep(1. / (fps_limit - (time.time() - now)))
        now = time.time()
        (ret, frame) = cam.read()  # type: Tuple[bool, np.ndarray ]
        if ret is False or not isinstance(frame, np.ndarray):
            cam.release()
            CamCtrl.cv_cams_dict[name].status_pub.publish("failed")
            return False
        if cam.get(cv2.CAP_PROP_FRAME_COUNT) > 0:
            frame_counter += 1
            if frame_counter >= cam.get(cv2.CAP_PROP_FRAME_COUNT):
                frame_counter = 0
                cam = cv2.VideoCapture(cam_id)
        CamCtrl.cv_cams_dict[name].frame_pub.publish(frame)
        msg = sub.get()
    sub.release()

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
