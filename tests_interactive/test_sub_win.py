import unittest as ut
from cv_pubsubs import window_sub as win
from cv_pubsubs import webcam_pub as cam

class TestSubWin(ut.TestCase):

    def test_sub(self):
        def cam_handler(frame, cam_id):
            win.frame_dict[str(cam_id) + "Frame"] = (frame, frame)

        t = cam.frame_handler_thread(0, cam_handler,
                                   request_size=(1280, 720),
                                   high_speed=True,
                                   fps_limit=240
                                   )

        win.sub_win_loop(names=['cammy', 'cammy2'],
                     input_vid_global_names=[str(0) + "Frame"])

        cam.CamCtrl.stop_cam(0)

        t.join()
