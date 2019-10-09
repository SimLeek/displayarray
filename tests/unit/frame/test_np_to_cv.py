import displayarray.frame.np_to_opencv as npcv
import numpy as np
import pytest
import cv2


def test_init():
    npcv.NpCam(np.zeros((10, 10)))

    with pytest.raises(AssertionError):
        npcv.NpCam("Not a numpy array")


def test_open():
    cam = npcv.NpCam(np.zeros((10, 10)))
    assert cam.isOpened() is True
    cam.release()
    assert cam.isOpened() is False


def test_read():
    cam = npcv.NpCam(np.zeros((10, 10)))
    succeeded, img = cam.read()
    assert succeeded is True
    assert img.shape == np.zeros((10, 10)).shape


def test_set():
    cam = npcv.NpCam(np.zeros((10, 10)))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 20)
    succeeded, img = cam.read()
    assert succeeded is True
    assert img.shape == np.zeros((10, 10)).shape
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 30)
    succeeded, img = cam.read()
    assert succeeded is True
    assert img.shape == np.zeros((30, 20)).shape


def test_get():
    cam = npcv.NpCam(np.zeros((10, 10)))
    assert cam.get(cv2.CAP_PROP_FRAME_COUNT) == float("inf")
