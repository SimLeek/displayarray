"""Get camera IDs."""

import cv2

from typing import List


def get_cam_ids() -> List[int]:
    """Get all cameras that OpenCV can currently detect."""
    cam_list: List[int] = []

    while True:
        cam = cv2.VideoCapture(len(cam_list))
        if not cam.isOpened():
            break
        cam_list.append(len(cam_list))

    return cam_list
