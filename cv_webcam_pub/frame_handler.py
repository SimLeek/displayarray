import pubsub
import numpy as np
import threading
from .listen_default import _listen_default
from .pub_cam import pub_cam_thread

if False:
    from typing import Union, Tuple, Any, Callable

def frame_handler_loop(cam_id,  # type: Union[int, str]
                       frame_handler,  # type: Callable[[int, np.ndarray], Any]
                       request_size=(1280, 720),  # type: Tuple[int, int]
                       fps_limit = 60
                       ):
    t = pub_cam_thread(cam_id, request_size, fps_limit)
    sub_cam = pubsub.subscribe("cvcams." + str(cam_id) + ".vid")
    sub_owner = pubsub.subscribe("cvcamhandlers." + str(cam_id) + ".cmd")
    msg_owner = ''
    while msg_owner != 'q':
        frame = _listen_default(sub_cam, timeout=.1)  # type: np.ndarray
        if frame is not None:
            frame = frame[0]
            frame_handler(frame, cam_id)
        msg_owner = _listen_default(sub_owner, block=False, empty='')
    pubsub.publish("cvcams." + str(cam_id) + ".cmd", 'q')
    t.join()

def frame_handler_thread(cam_id,  # type: Union[int, str]
                            frame_handler,  # type: Callable[[int, np.ndarray], Any]
                            request_size=(1280, 720),  # type: Tuple[int, int]
                         fps_limit = 60
                         ):                        # type: (...) -> threading.Thread
    t = threading.Thread(target=frame_handler_loop, args=(cam_id, frame_handler, request_size, fps_limit))
    t.start()
    return t