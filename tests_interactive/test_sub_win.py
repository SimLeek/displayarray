import unittest as ut
import cv_pubsubs.cv_webcam_pub as w
from cv_pubsubs.sub_win import frameDict, sub_win_loop

class TestSubWin(ut.TestCase):

    def test_sub(self):
        def camHandler(frame, camId):
            frameDict[str(camId) + "Frame"] = (frame,frame)

        t = w.frame_handler_thread(0, camHandler)

        sub_win_loop(names=['cammy', 'cammy2'], input_vid_global_names=[str(0)+"Frame"])

        w.cam_ctrl.stop_cam(0)

        t.join()
