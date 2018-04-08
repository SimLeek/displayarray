import threading
import unittest as ut

import pubsub

import cv_pubsubs.webcam_pub as w
from cv_pubsubs.listen_default import listen_default
from cv_pubsubs.window_sub import SubscriberWindows


def print_keys_thread():
    sub_key = pubsub.subscribe("CVKeyStroke")
    sub_cmd = pubsub.subscribe("CVWinCmd")
    msg_cmd = ''
    while msg_cmd != 'quit':
        key_chr = listen_default(sub_key, timeout=.1)  # type: np.ndarray
        if key_chr is not None:
            print("key pressed: " + str(key_chr))
        msg_cmd = listen_default(sub_cmd, block=False, empty='')
    pubsub.publish("CVWinCmd", 'quit')


def start_print_keys_thread():  # type: (...) -> threading.Thread
    t = threading.Thread(target=print_keys_thread, args=())
    t.start()
    return t


class TestSubWin(ut.TestCase):

    def test_sub(self):
        def cam_handler(frame, cam_id):
            SubscriberWindows.frame_dict[str(cam_id) + "Frame"] = (frame, frame)

        t = w.frame_handler_thread(0, cam_handler,
                                   request_size=(1280, 720),
                                   high_speed=True,
                                   fps_limit=240
                                   )

        SubscriberWindows(window_names=['cammy', 'cammy2'],
                          input_vid_global_names=[str(0) + "Frame"]
                          ).loop()

        w.CamCtrl.stop_cam(0)

        t.join()

    def test_key_sub(self):
        def cam_handler(frame, cam_id):
            SubscriberWindows.frame_dict[str(cam_id) + "Frame"] = (frame, frame)

        t = w.frame_handler_thread(0, cam_handler,
                                   request_size=(1280, 720),
                                   high_speed=True,
                                   fps_limit=240
                                   )

        kt = start_print_keys_thread()

        SubscriberWindows(window_names=['cammy', 'cammy2'],
                          input_vid_global_names=[str(0) + "Frame"]
                          ).loop()

        w.CamCtrl.stop_cam(0)

        t.join()
        kt.join()
