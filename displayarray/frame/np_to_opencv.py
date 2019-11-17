"""Allow OpenCV to handle numpy arrays as input."""

import numpy as np
import cv2


class NpCam(object):
    """Add OpenCV camera controls to a numpy array."""

    def __init__(self, img):
        """Create a fake camera for OpenCV based on the initial array."""
        assert isinstance(img, np.ndarray)
        self.__img = img
        self.__is_opened = True
        if len(img.shape) > 0:
            self.__height = self.__img.shape[0]
            if len(self.__img.shape) > 1:
                self.__width = self.__img.shape[1]
            else:
                self.__width = self.__height
        else:
            self.__width = self.__height = 1
        self.__ratio = float(self.__width) / self.__height

        self.__wait_for_ratio = False

    def __handler_ratio(self):
        if self.__width <= 0 or not isinstance(self.__width, int):
            self.__width = int(self.__ratio * self.__height)
        elif self.__height <= 0 or not isinstance(self.__height, int):
            self.__height = int(self.__width / self.__ratio)
        if self.__width > 0 and self.__height > 0:
            self.__img = cv2.resize(self.__img, (self.__width, self.__height))

    def set(self, *args, **kwargs):
        """Set CAP_PROP_FRAME_WIDTH or CAP_PROP_FRAME_HEIGHT to scale a numpy array to that size."""
        if args[0] in [cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT]:
            self.__wait_for_ratio = not self.__wait_for_ratio
            if args[0] == cv2.CAP_PROP_FRAME_WIDTH:
                self.__width = args[1]
            else:
                self.__height = args[1]
            if not self.__wait_for_ratio:
                self.__handler_ratio()

    @staticmethod
    def get(*args, **kwargs):
        """Get OpenCV args. Currently only a fake CAP_PROP_FRAME_COUNT to fix detecting video ends."""
        if args[0] == cv2.CAP_PROP_FRAME_COUNT:
            return float("inf")

    def read(self):
        """Read back the numpy array in standard "did it work", "the array", OpenCV format."""
        return True, self.__img

    def isOpened(self):  # NOSONAR
        """Hack to tell OpenCV we're opened until we call release."""
        return self.__is_opened

    def release(self):
        """Let OpenCV know we're finished."""
        self.__is_opened = False
