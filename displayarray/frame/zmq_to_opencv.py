"""Allow OpenCV to handle zmq subscriber addresses as input."""

import cv2
import zmq
from tensorcom.tenbin import decode_buffer  # type: ignore


class ZmqCam(object):
    """Add OpenCV camera controls to a numpy array."""

    def __init__(self, img):
        """Create a fake camera for OpenCV based on the initial array."""
        assert isinstance(img, str)
        s = img.split('#')
        self.__ctx = zmq.Context()
        self.__addr = s[0]
        self.__sub = self.__ctx.socket(zmq.SUB)
        if len(s) > 1:
            self.__topic = bytes(s[1], 'ascii')
            self.__sub.setsockopt(zmq.SUBSCRIBE, self.__topic)
        else:
            self.__topic = b""
        self.__sub.connect(self.__addr)

        self.__is_opened = True

    def set(self, *args, **kwargs):
        """Set CAP_PROP_FRAME_WIDTH or CAP_PROP_FRAME_HEIGHT to scale a numpy array to that size."""
        pass

    @staticmethod
    def get(*args, **kwargs):
        """Get OpenCV args. Currently only a fake CAP_PROP_FRAME_COUNT to fix detecting video ends."""
        if args[0] == cv2.CAP_PROP_FRAME_COUNT:
            return float("inf")

    def read(self):
        """Read back the numpy array in standard "did it work", "the array", OpenCV format."""
        r = self.__sub.recv_multipart()
        arrs = [decode_buffer(ri) for ri in r[1:]]
        return True, arrs

    def isOpened(self):  # NOSONAR
        """Hack to tell OpenCV we're opened until we call release."""
        return self.__is_opened

    def release(self):
        """Let OpenCV know we're finished."""
        self.__is_opened = False
