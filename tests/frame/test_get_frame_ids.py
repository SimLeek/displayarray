import displayarray.frame.get_frame_ids as gfi
import mock
import cv2


def test_get_cam_ids():
    with mock.patch.object(cv2, "VideoCapture", new_callable=mock.MagicMock) as mock_cv_capture:
        cap = mock.MagicMock()
        cap.isOpened.return_value = True
        cap_end = mock.MagicMock()
        cap_end.isOpened.return_value = False
        mock_cv_capture.side_effect = [cap, cap, cap, cap_end]
        ids = gfi.get_cam_ids()
        assert ids == [0, 1, 2]
