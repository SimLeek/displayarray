import cvpubsubs.webcam_pub as w
import unittest as ut


class TestFrameHandler(ut.TestCase):
    i = 0

    def test_handler(self):

        def test_frame_handler(frame, cam_id):
            if self.i == 200:
                w.CamCtrl.stop_cam(cam_id)
            if self.i % 100 == 0:
                print(frame.shape)
            self.i += 1

        w.VideoHandlerThread(0, [test_frame_handler],
                               request_size=(1280, 720),
                               high_speed=True,
                               fps_limit=240)
