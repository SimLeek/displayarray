import threading
import unittest as ut

import cvpubsubs.webcam_pub as w
from cvpubsubs.window_sub import SubscriberWindows
from cvpubsubs.window_sub.winctrl import WinCtrl
from cvpubsubs.input import mouse_loop, key_loop

if False:
    import numpy as np
    from cvpubsubs.window_sub.mouse_event import MouseEvent


class TestSubWin(ut.TestCase):

    def test_mouse_loop(self):
        @mouse_loop
        def print_mouse_thread(mouse_event):
            print(mouse_event)

        w.VideoHandlerThread().display()

    def test_key_loop(self):
        @key_loop
        def print_key_thread(key_chr):
            print("key pressed: " + str(key_chr))

        w.VideoHandlerThread().display()

    def test_sub(self):
        w.VideoHandlerThread().display()

    def test_image(self):
        img = np.random.uniform(0, 1, (300, 300, 3))
        w.VideoHandlerThread(video_source=img).display()

    def test_image_args(self):
        img = np.random.uniform(0, 1, (30, 30, 3))
        w.VideoHandlerThread(video_source=img, request_size=(300, -1)).display()

    def test_sub_with_args(self):
        video_thread = w.VideoHandlerThread(video_source=0,
                                            callbacks=w.display_callbacks,
                                            request_size=(800, 600),
                                            high_speed=False,
                                            fps_limit=8
                                            )

        video_thread.display()

    def test_sub_with_callback(self):
        def redden_frame_print_spam(frame, cam_id):
            frame[:, :, 0] = 0
            frame[:, :, 2] = 0

        w.VideoHandlerThread(callbacks=redden_frame_print_spam).display()

    def test_sub_with_callback_exception(self):
        def redden_frame_print_spam(frame, cam_id):
            frame[:, :, 0] = 0
            frame[:, :, 2] = 1 / 0

        with self.assertRaises(ZeroDivisionError) as e:
            v = w.VideoHandlerThread(callbacks=redden_frame_print_spam)
            v.display()
            self.assertEqual(v.exception_raised, e)

    def test_multi_cams_one_source(self):
        def cam_handler(frame, cam_id):
            SubscriberWindows.set_global_frame_dict(cam_id, frame, frame)

        t = w.VideoHandlerThread(0, [cam_handler],
                                 request_size=(1280, 720),
                                 high_speed=True,
                                 fps_limit=240
                                 )

        t.start()

        SubscriberWindows(window_names=['cammy', 'cammy2'],
                          video_sources=[str(0)]
                          ).loop()

        t.join()

    @ut.skip("I don't have stereo cams... :(")
    def test_multi_cams_multi_source(self):
        t1 = w.VideoHandlerThread(0, request_size=(1920, 1080))
        t2 = w.VideoHandlerThread(1, request_size=(1920, 1080))

        t1.start()
        t2.start()

        SubscriberWindows(window_names=['cammy', 'cammy2'],
                          video_sources=[0, 1]
                          ).loop()

        t1.join()
        t1.join()

    def test_nested_frames(self):
        def nest_frame(frame, cam_id):
            frame = np.asarray([[[[[[frame]]]]], [[[[[frame]]], [[[frame]]]]]])
            return frame

        v = w.VideoHandlerThread(callbacks=[nest_frame] + w.display_callbacks)
        v.start()

        SubscriberWindows(window_names=[str(i) for i in range(3)],
                          video_sources=[str(0)]
                          ).loop()

        v.join()

    def test_nested_frames_exception(self):
        def nest_frame(frame, cam_id):
            frame = np.asarray([[[[[[frame + 1 / 0]]]]], [[[[[frame]]], [[[frame]]]]]])
            return frame

        v = w.VideoHandlerThread(callbacks=[nest_frame] + w.display_callbacks)
        v.start()

        with self.assertRaises(ZeroDivisionError) as e:
            SubscriberWindows(window_names=[str(i) for i in range(3)],
                              video_sources=[str(0)]
                              ).loop()
            self.assertEqual(v.exception_raised, e)

        v.join()

    def test_conway_life(self):
        from cvpubsubs.webcam_pub import VideoHandlerThread
        from cvpubsubs.callbacks import function_display_callback
        import numpy as np
        import cv2
        img = np.zeros((50, 50, 1))
        img[0:5, 0:5, :] = 1

        def conway(array, coords, finished):
            neighbors = np.sum(array[max(coords[0] - 1, 0):min(coords[0] + 2, 50),
                               max(coords[1] - 1, 0):min(coords[1] + 2, 50)])
            neighbors = max(neighbors - np.sum(array[coords[0:2]]), 0.0)
            if array[coords] == 1.0:
                if neighbors < 2 or neighbors > 3:
                    array[coords] = 0.0
                elif 2 <= neighbors <= 3:
                    array[coords] = 1.0
            else:
                if neighbors == 3:
                    array[coords] = 1.0

        @mouse_loop
        def conway_add(mouse_event  # type:MouseEvent
                       ):
            if 0 <= mouse_event.x < 50 and 0 <= mouse_event.y < 50:
                if mouse_event.flags == cv2.EVENT_FLAG_LBUTTON:
                    img[mouse_event.y - 5:mouse_event.y + 10, mouse_event.x - 5:mouse_event.x + 10, :] = 0.0
                elif mouse_event.flags == cv2.EVENT_FLAG_RBUTTON:
                    img[mouse_event.y - 5:mouse_event.y + 10, mouse_event.x - 5:mouse_event.x + 10, :] = 1.0

        VideoHandlerThread(video_source=img, callbacks=function_display_callback(conway)).display()
