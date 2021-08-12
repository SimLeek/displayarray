from displayarray.frame.frame_publishing import pub_cam_loop_opencv, pub_cam_thread
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
        pub_cam_loop_opencv(not_a_camera)


def test_pub_cam_int():
    img = np.zeros((30, 40))
    with mock.patch.object(
        cv2, "VideoCapture", new_callable=mock.MagicMock
    ) as mock_cv_capture, mock.patch.object(NpCam, "set"), mock.patch.object(
        NpCam, "get"
    ) as mock_get, mock.patch.object(
        NpCam, "release"
    ), mock.patch.object(
        displayarray.frame.frame_publishing.subscriber_dictionary, "register_cam"
    ) as reg_cam, mock.patch.object(
        displayarray.frame.frame_publishing.subscriber_dictionary, "cam_cmd_sub"
    ) as cam_cmd_sub:
        cap = NpCam(img)
        mock_cv_capture.return_value = cap
        mock_sub = cam_cmd_sub.return_value = mock.MagicMock()
        mock_sub.get = mock.MagicMock()
        mock_sub.get.side_effect = ["", "", "", "quit"]
        mock_sub.release = mock.MagicMock()
        mock_get.return_value = 2

        cam_0 = subd.CV_CAMS_DICT["0"] = subd.Cam("0")
        with mock.patch.object(cam_0.frame_pub, "publish") as cam_pub:
            pub_cam_loop_opencv(0, mjpg=False)

            cam_pub.assert_has_calls([mock.call(img)] * 4)

            reg_cam.assert_called_once_with("0", cap)
            cam_cmd_sub.assert_called_once_with("0")

            cap.set.assert_has_calls(
                [
                    mock.call(cv2.CAP_PROP_FRAME_WIDTH, -1),
                    mock.call(cv2.CAP_PROP_FRAME_HEIGHT, -1),
                ]
            )
            cap.get.assert_has_calls([mock.call(cv2.CAP_PROP_FRAME_COUNT)] * 8)
            mock_sub.get.assert_has_calls(
                [mock.call(), mock.call(), mock.call(), mock.call()]
            )
            mock_sub.release.assert_called_once()
            cap.release.assert_called_once()

        subd.CV_CAMS_DICT = {}


def test_pub_cam_fail():
    img = np.zeros((30, 40))
    with mock.patch.object(
        cv2, "VideoCapture", new_callable=mock.MagicMock
    ) as mock_cv_capture, mock.patch.object(
        NpCam, "isOpened"
    ) as mock_is_open, mock.patch.object(
        subd, "register_cam"
    ) as mock_reg:
        cap = NpCam(img)
        mock_cv_capture.side_effect = [cap]

        mock_is_open.return_value = False
        subd.CV_CAMS_DICT["0"] = subd.Cam("0")

        with mock.patch.object(
            subd.CV_CAMS_DICT["0"].status_pub, "publish"
        ) as mock_fail_pub:
            pub_cam_loop_opencv(0, mjpg=False)

            mock_fail_pub.assert_called_once_with("failed")

        subd.CV_CAMS_DICT = {}


def test_pub_cam_high_speed():
    img = np.zeros((30, 40))
    with mock.patch.object(
        cv2, "VideoCapture", new_callable=mock.MagicMock
    ) as mock_cv_capture, mock.patch.object(
        NpCam, "isOpened"
    ) as mock_is_open, mock.patch.object(
        NpCam, "set"
    ) as mock_cam_set:
        cap = NpCam(img)
        mock_cv_capture.side_effect = [cap]

        mock_is_open.return_value = False

        pub_cam_loop_opencv(0, request_size=(640, 480), mjpg=True)

        mock_cam_set.assert_has_calls(
            [
                mock.call(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG),
                mock.call(cv2.CAP_PROP_FRAME_WIDTH, 640),
                mock.call(cv2.CAP_PROP_FRAME_HEIGHT, 480),
            ]
        )


def test_pub_cam_numpy():
    with mock.patch(
        "displayarray.frame.frame_publishing.uid_for_source",
        new_callable=mock.MagicMock,
    ) as mock_uidfs, mock.patch.object(
        NpCam, "read"
    ) as mock_np_read, mock.patch.object(
        subd, "register_cam"
    ):
        img = np.zeros((30, 40))
        mock_np_read.side_effect = [
            (True, img),
            (True, img),
            (True, img),
            (False, None),
        ]
        mock_uidfs.return_value = "0"
        cam_0 = subd.CV_CAMS_DICT["0"] = subd.Cam("0")
        with mock.patch.object(cam_0.frame_pub, "publish") as cam_pub:
            pub_cam_loop_opencv(img)
            cam_pub.assert_has_calls([mock.call(img)] * 3)
        subd.CV_CAMS_DICT = {}


def test_pub_cam_thread():
    with mock.patch(
        "displayarray.frame.frame_publishing.threading.Thread",
        new_callable=mock.MagicMock,
    ) as mock_thread:
        thread_instance = mock_thread.return_value = mock.MagicMock()

        pub_cam_thread(5)

        mock_thread.assert_called_once_with(
            target=fpub.pub_cam_loop_opencv, args=(5, (-1, -1), True, float("inf"))
        )
        thread_instance.start.assert_called_once()
