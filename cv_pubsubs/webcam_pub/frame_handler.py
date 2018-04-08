import threading

import numpy as np
import pubsub

from cv_pubsubs.listen_default import listen_default
from .pub_cam import pub_cam_thread

if False:
    from typing import Union, Tuple, Any, Callable


def frame_handler_loop(cam_id,  # type: Union[int, str]
                       frame_handler,  # type: Callable[[np.ndarray, int], Any]
                       request_size=(1280, 720),  # type: Tuple[int, int]
                       high_speed=False,  # type: bool
                       fps_limit=240  # type: float
                       ):
    t = pub_cam_thread(cam_id, request_size, high_speed, fps_limit)
    sub_cam = pubsub.subscribe("CVCams." + str(cam_id) + ".Vid")
    sub_owner = pubsub.subscribe("CVCamHandlers." + str(cam_id) + ".Cmd")
    msg_owner = ''
    while msg_owner != 'quit':
        frame = listen_default(sub_cam, timeout=.1)  # type: np.ndarray
        if frame is not None:
            frame = frame[0]
            frame_handler(frame, cam_id)
        msg_owner = listen_default(sub_owner, block=False, empty='')
    pubsub.publish("CVCams." + str(cam_id) + ".Cmd", 'quit')
    t.join()


def frame_handler_thread(cam_id,  # type: Union[int, str]
                         frame_handler,  # type: Callable[[int, np.ndarray], Any]
                         request_size=(1280, 720),  # type: Tuple[int, int]
                         high_speed=False,  # type: bool
                         fps_limit=240  # type: float
                         ):  # type: (...) -> threading.Thread
    t = threading.Thread(target=frame_handler_loop, args=(cam_id, frame_handler, request_size, high_speed, fps_limit))
    t.start()
    return t
