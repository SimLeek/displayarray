import cv_pubsubs.cv_webcam_pub as w
import unittest as ut


class TestFrameHandler(ut.TestCase):
    i = 0

    def test_handler(self):

        def test_frame_handler(frame, cam_id):
            if self.i == 200:
                w.cam_ctrl.stop_cam(cam_id)
            if self.i % 100 == 0:
                print(frame.shape)
            self.i += 1

        w.frame_handler_thread(0, test_frame_handler)
