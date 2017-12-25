import numpy as np
import cv2

#todo: add dshow, v4l

if False:  # don't include if actually running
    from typing import List, Tuple


def make_camlist():  # type: () -> List[cv2.VideoCapture]
    cam_list = []  # type: List[cv2.VideoCapture]

    while len(cam_list) == 0 or cam_list[-1].isOpened():
        cam_list.append(cv2.VideoCapture(len(cam_list)))

    return cam_list

def capture_cams(cam_list  # type: List[cv2.VideoCapture]
                 ):  # type: (...) -> List[np.ndarray]
    frame_list = []
    for c in range(len(cam_list)):
        (ret, frame) = cam_list[c].read()  # type: Tuple[bool, np.ndarray ]
        if ret is False or not isinstance(frame, np.ndarray):
            cam_list[c].release()
            cam_list.pop(c)
            continue
        frame_list.append(frame)
    #        for i in range(100):
    #                    try:
    #                        print(i, cam_list[c].get(i))
    #                    except:
    #                        break
    #        exit()
    return frame_list


def show_cams(cam_list  # type: List[cv2.VideoCapture]
              ):  # type: (...) -> None
    while True:
        frame_list = capture_cams(cam_list)
        for f in range(len(frame_list)):
            print(frame_list[f].shape)
            cv2.imshow('frame' + str(f), frame_list[f])
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


def end_cams(cam_list  # type: List[cv2.VideoCapture]
             ):  # type: (...) -> None
    for cam in cam_list:
        cam.release()

