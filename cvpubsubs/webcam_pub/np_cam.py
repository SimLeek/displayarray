import numpy as np
import cv2


class NpCam(object):
    def __init__(self, img):
        assert isinstance(img, np.ndarray)
        self.__img = img
        self.__is_opened = True

        self.__width = self.__img.shape[1]
        self.__height = self.__img.shape[0]
        self.__ratio = float(self.__width) / self.__height

        self.__wait_for_ratio = False

    def set(self, *args, **kwargs):
        if args[0] in [cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT]:
            self.__wait_for_ratio = not self.__wait_for_ratio
            if args[0] == cv2.CAP_PROP_FRAME_WIDTH:
                self.__width = args[1]
            else:
                self.__height = args[1]
            if not self.__wait_for_ratio:
                if self.__width <= 0 or not isinstance(self.__width, int):
                    self.__width = int(self.__ratio * self.__height)
                elif self.__height <= 0 or not isinstance(self.__height, int):
                    self.__height = int(self.__width / self.__ratio)
                if self.__width>0 and self.__height>0:
                    self.__img = cv2.resize(self.__img, (self.__width, self.__height))

    def get(self, *args, **kwargs):
        if args[0] == cv2.CAP_PROP_FRAME_COUNT:
            return float("inf")

    def read(self):
        return (True, self.__img)

    def isOpened(self):
        return self.__is_opened

    def release(self):
        self.__is_opened = False
