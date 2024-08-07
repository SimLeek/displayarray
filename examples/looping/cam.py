from displayarray import display, DirectDisplay
import numpy as np


with display(0, size=(9999,9999)) as displayer:
    while displayer:
        pass
import cv2

# proof opencv is slow
#d= DirectDisplay()
#size=(9999,9999)
#cam = cv2.VideoCapture(0)
#cam.set(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG)
#cam.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
#cam.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
#while not d.window.is_closing:
#    ret, frame = cam.read()
#    if frame is not None:
#        d.imshow('cam', frame)
#    d.update()