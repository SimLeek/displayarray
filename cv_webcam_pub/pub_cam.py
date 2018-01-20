import pubsub
import cv2
import numpy as np
import time
import threading
from .listen_default import _listen_default

if False:
    from typing import Union, Tuple

def pub_cam_loop(cam_id,  # type: Union[int, str]
                      request_size=(1280, 720),  # type: Tuple[int, int]
                      fps_limit = 60
                      ):  # type: (...)->bool
    """


    :param cam_id:
    :param request_size:
    :return:
    """
    sub = pubsub.subscribe("cvcams." + str(cam_id) + ".cmd")
    msg = ''
    cam = cv2.VideoCapture(cam_id)
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
        msg = _listen_default(sub, block=False, empty='')

        pass
    cam.release()
    return True

def pub_cam_thread(cam_id,                  # type: Union[int, str]
                           request_ize=(1280, 720)  # type: Tuple[int, int]
                           ):
    # type: (...) -> threading.Thread
    t = threading.Thread(target=pub_cam_loop, args=(cam_id, request_ize))
    t.start()
    return t

