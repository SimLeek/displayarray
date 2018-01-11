import pubsub
import queue
import cv2
import numpy as np
import threading

if False:  # don't include if actually running
    from typing import List, Union, Tuple, Any, Callable


def get_open_cv_cam_ids():  # type: () -> List[cv2.VideoCapture]
    cam_list = []  # type: List[int]

    while True:
        cam = cv2.VideoCapture(len(cam_list))
        if not cam.isOpened():
            break
        cam_list.append(len(cam_list))

    return cam_list

def pub_cv_cam_thread(camId # type: Union[int, str]
                      ):
    sub = pubsub.subscribe("cvcams."+str(camId)+".cmd")
    msg = ''
    cam = cv2.VideoCapture(camId)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cam.isOpened():
        pubsub.publish("cvcams." + str(camId) + ".status", "failed")
        return False
    while (  msg != 'q'):
        (ret, frame) = cam.read()  # type: Tuple[bool, np.ndarray ]
        if ret is False or not isinstance(frame, np.ndarray):
            cam.release()
            pubsub.publish("cvcams." + str(camId) + ".status", "failed")
            return False
        pubsub.publish("cvcams."+str(camId)+".vid", (frame,))
        msg = listenFixed(sub, block=False, empty='')

        pass
    cam.release()
    return True

def listenFixed(sub, block=True, timeout=None, empty=None):
    try:
        msg = (sub.listen(block=block, timeout=timeout))
        try:
            msg = next(msg)['data']
        except StopIteration:
            msg = empty
    except queue.Empty:
        msg = empty
    return msg


def init_cv_cam_pub_thread(camId # type: Union[int, str]
                      ):
    # type: (...) -> threading.Thread
    t = threading.Thread(target=pub_cv_cam_thread, args = (camId,))
    t.start()
    return t

def cv_cam_pub_handler(camId, # type: Union[int, str]
                       frameHandler # type: Callable[[int, np.ndarray], Any]
                       ):
    t = init_cv_cam_pub_thread(camId)
    subCam = pubsub.subscribe("cvcams."+str(camId)+".vid")
    subOwner = pubsub.subscribe("cvcamhandlers."+str(camId)+".cmd")
    msgOwner = ''
    while msgOwner != 'q':
        frame = listenFixed(subCam, timeout=.1)  # type: np.ndarray
        if frame is not None:
            frame = frame[0]
            frameHandler(frame, camId)
        msgOwner = listenFixed(subOwner, block=False, empty='')
    pubsub.publish("cvcams.0.cmd", 'q')
    t.join()

def init_cv_cam_pub_handler(camId, # type: Union[int, str]
                            frameHandler # type: Callable[[int, np.ndarray], Any]
                      ):
    # type: (...) -> threading.Thread
    t = threading.Thread(target=cv_cam_pub_handler, args = (camId, frameHandler))
    t.start()
    return t

if __name__ == '__main__': # todo: add to tests
    i = 0
    def testFrameHandler(frame, camId):
        global i
        if i == 200:
            pubsub.publish("cvcamhandlers."+str(camId)+".cmd", 'q')
        if i % 100 == 0:
            print(frame.shape)
        i += 1

    cv_cam_pub_handler(0, testFrameHandler)

