from displayarray.frame.frame_publishing import pub_cam_loop, pub_cam_thread
import displayarray
import mock
import pytest
import cv2
from displayarray.frame.np_to_opencv import NpCam
import numpy as np
import displayarray.frame.subscriber_dictionary as subd
import displayarray.frame.frame_publishing as fpub


def test_pub_cam_loop_exit():
    not_a_camera = mock.MagicMock()
    with pytest.raises(TypeError):
        pub_cam_loop(not_a_camera)


def test_pub_cam_int():
    img = np.zeros((30, 40))
    with mock.patch.object(cv2, "VideoCapture", new_callable=mock.MagicMock) as mock_cv_capture:
        cap = NpCam(img)
        mock_cv_capture.return_value = cap
        reg_cam = displayarray.frame.frame_publishing.subscriber_dictionary.register_cam = mock.MagicMock()
        cam_cmd_sub = displayarray.frame.frame_publishing.subscriber_dictionary.cam_cmd_sub = mock.MagicMock()
        mock_sub = cam_cmd_sub.return_value = mock.MagicMock()
        mock_sub.get = mock.MagicMock()
        mock_sub.get.side_effect = ["", "", "", "quit"]
        mock_sub.release = mock.MagicMock()
        cap.set = mock.MagicMock()
        cap.get = mock.MagicMock()
        cap.get.return_value = 2
        cap.release = mock.MagicMock()

        cam_0 = subd.CV_CAMS_DICT['0'] = subd.Cam('0')
        cam_pub = cam_0.frame_pub.publish = mock.MagicMock()

        pub_cam_loop(0, high_speed=False)

        cam_pub.assert_has_calls(
            [mock.call(img)] * 4
        )

        reg_cam.assert_called_once_with('0')
        cam_cmd_sub.assert_called_once_with('0')

        cap.set.assert_has_calls(
            [mock.call(cv2.CAP_PROP_FRAME_WIDTH, 1280),
             mock.call(cv2.CAP_PROP_FRAME_HEIGHT, 720)]
        )
        cap.get.assert_has_calls(
            [mock.call(cv2.CAP_PROP_FRAME_COUNT)] * 8
        )
        mock_sub.get.assert_has_calls([mock.call(), mock.call(), mock.call(), mock.call()])
        mock_sub.release.assert_called_once()
        cap.release.assert_called_once()


def test_pub_cam_fail():
    img = np.zeros((30, 40))
    with mock.patch.object(cv2, "VideoCapture", new_callable=mock.MagicMock) as mock_cv_capture:
        cap = NpCam(img)
        mock_cv_capture.side_effect = [cap]

        cap.isOpened = mock.MagicMock()
        cap.isOpened.return_value = False
        subd.register_cam = mock.MagicMock()
        subd.CV_CAMS_DICT['0'] = subd.Cam('0')

        mock_fail_pub = \
            subd.CV_CAMS_DICT['0'].status_pub.publish = \
            mock.MagicMock()

        pub_cam_loop(0, high_speed=False)

        mock_fail_pub.assert_called_once_with("failed")


def test_pub_cam_high_speed():
    img = np.zeros((30, 40))
    with mock.patch.object(cv2, "VideoCapture", new_callable=mock.MagicMock) as mock_cv_capture:
        cap = NpCam(img)
        mock_cv_capture.side_effect = [cap]

        cap.isOpened = mock.MagicMock()
        cap.isOpened.return_value = False
        cap.set = mock.MagicMock()

        pub_cam_loop(0, request_size=(640, 480), high_speed=True)

        cap.set.assert_has_calls(
            [mock.call(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG),
             mock.call(cv2.CAP_PROP_FRAME_WIDTH, 640),
             mock.call(cv2.CAP_PROP_FRAME_HEIGHT, 480)]
        )


def test_pub_cam_numpy():
    with mock.patch("displayarray.frame.frame_publishing.uid_for_source", new_callable=mock.MagicMock) as mock_uidfs:
        img = np.zeros((30, 40))
        NpCam.read = mock.MagicMock()
        NpCam.read.side_effect = [(True, img), (True, img), (True, img), (False, None)]
        subd.register_cam = mock.MagicMock()
        mock_uidfs.return_value = '0'
        cam_0 = subd.CV_CAMS_DICT['0'] = subd.Cam('0')
        cam_pub = cam_0.frame_pub.publish = mock.MagicMock()

        pub_cam_loop(img)
        cam_pub.assert_has_calls(
            [mock.call(img)] * 3
        )


def test_pub_cam_thread():
    with mock.patch("displayarray.frame.frame_publishing.threading.Thread", new_callable=mock.MagicMock) as mock_thread:
        thread_instance = mock_thread.return_value = mock.MagicMock()

        pub_cam_thread(5)

        mock_thread.assert_called_once_with(target=fpub.pub_cam_loop, args=(5, (1280, 720), True, 240))
        thread_instance.start.assert_called_once()
