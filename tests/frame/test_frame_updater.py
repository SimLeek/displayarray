import displayarray.frame.frame_updater as fup
import numpy as np
import mock
import pytest
import itertools
from displayarray.effects.select_channels import SelectChannels


def test_init_defaults():
    ud = fup.FrameUpdater()

    assert ud.video_source == 0
    assert ud.cam_id == "0"
    assert ud.callbacks == []
    assert ud.request_size == (-1, -1)
    assert ud.high_speed == True
    assert ud.fps_limit == 240


def test_init():
    cb = lambda x: np.zeros((1, 1))
    ud = fup.FrameUpdater("test", cb, (2, 2), False, 30)

    assert ud.video_source == "test"
    assert ud.cam_id == "test"
    assert ud.callbacks == [cb]
    assert ud.request_size == (2, 2)
    assert ud.high_speed == False
    assert ud.fps_limit == 30


def test_loop():
    with mock.patch(
        "displayarray.frame.frame_updater.pub_cam_thread"
    ) as mock_pubcam_thread, mock.patch(
        "displayarray.frame.frame_updater.subscriber_dictionary.CV_CAMS_DICT"
    ) as mock_cam_dict, mock.patch(
        "displayarray.frame.frame_updater.subscriber_dictionary.cam_frame_sub"
    ) as mock_frame_sub, mock.patch(
        "displayarray.frame.frame_updater.subscriber_dictionary.handler_cmd_sub"
    ) as handler_cmd_sub, mock.patch(
        "displayarray.frame.frame_updater.global_cv_display_callback"
    ) as mock_global_cb:
        mock_cbs = [mock.MagicMock(), mock.MagicMock()]
        ud = fup.FrameUpdater(0, callbacks=mock_cbs)

        pub_t = mock_pubcam_thread.return_value = mock.MagicMock()
        mock_cam_dict.__contains__.side_effect = itertools.cycle([False, False, True])
        sub_cam = mock_frame_sub.return_value = mock.MagicMock()
        frame = sub_cam.get.return_value = mock.MagicMock()
        transformed_frame = mock.MagicMock()
        mock_cbs[0].return_value = transformed_frame
        mock_cbs[1].return_value = transformed_frame
        transformed_frame.shape = [1, 2, 3]
        mock_sub_owner = handler_cmd_sub.return_value = mock.MagicMock()
        mock_sub_owner.get.side_effect = ["", "", "", "quit"]

        ud.loop()

        mock_pubcam_thread.assert_called_once_with(0, (-1, -1), True, 240)
        mock_frame_sub.assert_called_once_with("0")
        handler_cmd_sub.assert_called_once_with("0")
        sub_cam.get.assert_has_calls([mock.call(blocking=True, timeout=1.0)] * 3)
        mock_cbs[0].assert_has_calls([mock.call(frame)] * 4)
        mock_cbs[1].assert_has_calls([mock.call(transformed_frame)] * 4)
        mock_global_cb.assert_has_calls([mock.call(transformed_frame, "0")] * 4)
        mock_sub_owner.release.assert_called_once()
        sub_cam.release.assert_called_once()
        pub_t.join.assert_called_once()


def test_callback_exception():
    def redden_frame_print_spam(frame):
        frame[:, :, 0] = 0
        frame[:, :, 2] = 1 / 0

    with pytest.raises(ZeroDivisionError) as e:
        v = fup.FrameUpdater(np.zeros((1, 1, 3)), callbacks=redden_frame_print_spam)
        v.loop()
    assert e.errisinstance(ZeroDivisionError)


def test_display():
    with mock.patch(
        "displayarray.window.SubscriberWindows", new_callable=mock.MagicMock
    ) as mock_sub_win:
        f = fup.FrameUpdater()
        with mock.patch.object(f, "start"), mock.patch.object(f, "join"):
            mock_sub_win_instance = mock_sub_win.return_value = mock.MagicMock()

            f.display()

            mock_sub_win.assert_called_once_with(video_sources=["0"], callbacks=[])
            mock_sub_win_instance.loop.assert_called_once()
            f.start.assert_called_once()
            f.join.assert_called_once()


def test_display_exception():
    with mock.patch(
        "displayarray.window.SubscriberWindows", new_callable=mock.MagicMock
    ) as mock_sub_win:

        def redden_frame_print_spam(frame):
            frame[:, :, 0] = 0
            frame[:, :, 2] = 1 / 0

        with pytest.raises(ZeroDivisionError) as e:
            v = fup.FrameUpdater(np.zeros((1, 1, 3)), callbacks=redden_frame_print_spam)
            v.display()
        assert e.errisinstance(ZeroDivisionError)


from displayarray.window.window_commands import win_cmd_pub


def test_display_many_channels():
    with mock.patch(
        "displayarray.frame.frame_updater.pub_cam_thread"
    ), mock.patch.object(
        fup.subscriber_dictionary, "CV_CAMS_DICT"
    ) as mock_cam_dict, mock.patch.object(
        fup.subscriber_dictionary, "cam_frame_sub"
    ) as mock_sub_cam, mock.patch(
        "displayarray.frame.frame_updater.subscriber_dictionary.handler_cmd_sub"
    ) as handler_cmd_sub:
        mock_cam_dict.__contains__.side_effect = itertools.cycle([False, False, True])
        mock_sub_owner = handler_cmd_sub.return_value = mock.MagicMock()
        mock_sub_owner.get.side_effect = ["", "", "", "quit"]

        arr = np.ones((20, 20, 20))
        sub = mock.MagicMock()
        sub.get.return_value = arr
        mock_sub_cam.return_value = sub

        f = fup.FrameUpdater(arr)

        f.loop()

        assert isinstance(f.callbacks[0], SelectChannels)
        win_cmd_pub.publish("quit")
