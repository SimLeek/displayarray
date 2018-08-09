import cv2

if False:
    from typing import List


def get_cam_ids():  # type: () -> List[int]
    cam_list = []

    while True:
        cam = cv2.VideoCapture(len(cam_list))
        if not cam.isOpened():
            break
        cam_list.append(len(cam_list))

    return cam_list
