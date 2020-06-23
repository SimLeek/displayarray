"""Transform functions."""

import numpy as np
import cv2


def transform_about_center(
    arr, scale_multiplier=(1, 1), rotation_degrees=0, translation=(0, 0), skew=(0, 0)
):
    """
    Transform an image about its center.

    :param arr: numpy image to be transformed
    :param scale_multiplier: grow/shrink in x and y
    :param rotation_degrees: degrees to rotate, from 0 to 360
    :param translation: pixels to translate the image
    :param skew: mimics rotation along screen axes. In degrees. 90 degrees should give a line.
    :return: transformed numpy image
    """
    center_scale_xform = np.eye(3)
    center_scale_xform[0, 0] = scale_multiplier[1]
    center_scale_xform[1, 1] = scale_multiplier[0]
    center_scale_xform[0:2, -1] = [arr.shape[1] // 2, arr.shape[0] // 2]

    rotation_xform = np.eye(3)

    theta = np.radians(rotation_degrees)
    c, s = np.cos(theta), np.sin(theta)
    R = np.array(((c, -s), (s, c)))
    rotation_xform[0:2, 0:2] = R
    skew = np.radians(skew)
    skew = np.tan(skew)
    rotation_xform[-1, 0:2] = [skew[1] / arr.shape[1], skew[0] / arr.shape[0]]

    translation_skew_xform = np.eye(3)
    translation_skew_xform[0:2, -1] = [
        (-arr.shape[1] - translation[1]) // 2,
        (-arr.shape[0] - translation[0]) // 2,
    ]

    full_xform = center_scale_xform @ rotation_xform @ translation_skew_xform
    xformd_arr = cv2.warpPerspective(
        arr, full_xform, tuple(reversed(arr.shape[:2])), flags=0
    )
    return xformd_arr
