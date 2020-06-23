import displayarray.window.subscriber_windows as sub_win
from threading import Thread
import mock
import cv2
import numpy as np
from displayarray.effects.select_channels import SelectChannels
import pytest


def test_init_defaults():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow") as window_mock:
        sw = sub_win.SubscriberWindows()

        assert sw.source_names == ["0"]
        assert sw.input_vid_global_names == ["0"]
        assert sw.window_names == ["displayarray"]
        assert sw.input_cams == [0]
        assert sw.exited == False

        window_mock.assert_called_once_with("displayarray (press ESC to quit)")


def test_init():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow") as window_mock:
        cb = mock.MagicMock()
        sw = sub_win.SubscriberWindows(["test name"], [1], cb)

        assert sw.source_names == ["1"]
        assert sw.input_vid_global_names == ["1"]
        assert sw.window_names == ["test name"]
        assert sw.input_cams == [1]
        assert sw.exited == False

        window_mock.assert_called_once_with("test name (press ESC to quit)")


def test_bool():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        sub_win.SubscriberWindows, "update"
    ) as mock_update:
        sw = sub_win.SubscriberWindows()

        mock_update.assert_called_once()
        mock_update.reset_mock()

        assert bool(sw) == True

        mock_update.assert_called_once()
        mock_update.reset_mock()

        sw.exited = True

        assert bool(sw) == False


def test_block():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        sub_win.SubscriberWindows, "update"
    ), mock.patch.object(sub_win.SubscriberWindows, "loop") as mock_loop:
        sw = sub_win.SubscriberWindows()
        sw.close_threads.append(mock.MagicMock())

        sw.block()

        mock_loop.assert_called_once()
        sw.close_threads[0].join.assert_called_once()


def test_add_source():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"):
        sw = sub_win.SubscriberWindows().add_source(2)

        assert sw.source_names == ["0", "2"]
        assert sw.input_vid_global_names == ["0", "2"]
        assert sw.input_cams == [0, 2]


def test_add_window():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow") as mock_named_window, mock.patch.object(
        cv2, "setMouseCallback"
    ) as mock_set_mouse, mock.patch(
        "displayarray.window.subscriber_windows.WeakMethod", new_callable=mock.MagicMock
    ) as mock_weak:
        weak_method = mock_weak.return_value = mock.MagicMock()

        sw = sub_win.SubscriberWindows().add_window("second window")

        mock_weak.assert_has_calls(
            [mock.call(sw.handle_mouse), mock.call(sw.handle_mouse)]
        )
        assert sw.window_names == ["displayarray", "second window"]
        mock_named_window.assert_has_calls(
            [
                mock.call("displayarray (press ESC to quit)"),
                mock.call("second window (press ESC to quit)"),
            ]
        )
        mock_set_mouse.assert_has_calls(
            [
                mock.call("displayarray (press ESC to quit)", weak_method),
                mock.call("second window (press ESC to quit)", weak_method),
            ]
        )


def test_add_callback():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"):
        mock_cb = mock.MagicMock()

        sw = sub_win.SubscriberWindows().add_callback(mock_cb)

        assert sw.callbacks[0] == mock_cb


def test_handle_keys():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch(
        "displayarray.window.subscriber_windows.window_commands"
    ) as mock_win_cmd, mock.patch(
        "displayarray.window.subscriber_windows.subscriber_dictionary.stop_cam"
    ) as mock_stop, mock.patch(
        "displayarray.window.subscriber_windows.warnings"
    ) as mock_warnings, mock.patch(
        "displayarray.window.subscriber_windows.RuntimeWarning"
    ) as mock_runtime, mock.patch.object(
        cv2, "destroyWindow"
    ) as mock_destroy:
        mock_runtime.return_value = mock_runtime

        # test ordinary
        sw = sub_win.SubscriberWindows()

        sw.handle_keys(ord("h"))

        mock_win_cmd.key_pub.publish.assert_called_once_with("h")

        # test bad key
        def bad_key(k):
            raise ValueError("Bad Key")

        mock_win_cmd.key_pub.publish = bad_key

        sw.handle_keys(ord("b"))

        mock_runtime.assert_called_once_with(
            f"Unknown key code: [{ord('b')}]. Please report to the displayarray issue page."
        )
        mock_warnings.warn.assert_called_once_with(mock_runtime)

        # test exit key
        assert sw.ESC_KEY_CODES == [27]
        ret = sw.handle_keys(27)

        mock_destroy.assert_called_once_with("displayarray (press ESC to quit)")
        assert sw.exited is True
        mock_win_cmd.quit.assert_called()
        mock_stop.assert_called_with("0")
        assert ret == "quit"


def test_handle_mouse():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch(
        "displayarray.window.subscriber_windows.window_commands"
    ) as mock_win_cmd, mock.patch(
        "displayarray.window.subscriber_windows.MouseEvent"
    ) as mock_mouse_event:
        mock_mousey = mock_mouse_event.return_value = mock.MagicMock()

        sw = sub_win.SubscriberWindows()

        sw.handle_mouse(1, 2, 3, 4, 5)
        mock_mouse_event.assert_called_once_with(1, 2, 3, 4, 5)
        mock_win_cmd.mouse_pub.publish.assert_called_once_with(mock_mousey)


def test_update_frames():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        cv2, "imshow"
    ) as mock_imshow:
        sw = sub_win.SubscriberWindows()

        frame = np.ones((100, 100))
        sw.FRAME_DICT["0"] = frame

        sw.update_frames()

        assert sw.frames == {"0": [frame]}
        mock_imshow.assert_called_once_with("displayarray (press ESC to quit)", frame)


def test_update_frames_callback():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        cv2, "imshow"
    ) as mock_imshow:
        cb = mock.MagicMock()
        cb2 = mock.MagicMock()
        frame = np.ones((100, 100))
        frame2 = np.ones((102, 102))
        frame3 = np.ones((103, 103))
        cb.return_value = frame2
        cb2.return_value = frame3

        sw = sub_win.SubscriberWindows(
            window_names=["0", "1"], video_sources=[0, 1], callbacks=[cb, cb2]
        )

        sw.FRAME_DICT["0"] = frame
        sw.FRAME_DICT["1"] = frame

        sw.update_frames()

        assert sw.frames == {"0": [frame3], "1": [frame3]}
        assert np.all(cb.mock_calls[0].args[0] == frame)
        assert np.all(cb2.mock_calls[0].args[0] == frame2)
        mock_imshow.assert_has_calls(
            [
                mock.call("0 (press ESC to quit)", frame3),
                mock.call("1 (press ESC to quit)", frame3),
            ]
        )


def test_update_frames_too_many_channels():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        cv2, "imshow"
    ) as mock_imshow, mock.patch(
        "displayarray.window.subscriber_windows.print"
    ) as mock_print:
        sw = sub_win.SubscriberWindows()

        frame = np.ones((100, 100, 100))
        sw.FRAME_DICT["0"] = frame

        sw.update_frames()

        mock_print.assert_has_calls(
            [
                mock.call(
                    "Too many channels in output. (Got 100 instead of 1 or 3.) Frame selection callback added."
                ),
                mock.call(
                    "Ctrl+scroll to change first channel.\n"
                    "Shift+scroll to change second channel.\n"
                    "Alt+scroll to change third channel."
                ),
            ]
        )

        assert isinstance(sw.callbacks[-1], SelectChannels)
        assert sw.callbacks[-1].mouse_control is not None
        assert sw.callbacks[-1].mouse_print_channels is True
        assert sw.frames["0"][0].shape[-1] == 3


def test_update_frames_nested():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        cv2, "imshow"
    ) as mock_imshow, mock.patch("displayarray.window.subscriber_windows.print"):
        sw = sub_win.SubscriberWindows()

        frame = np.ones((20, 100, 100, 100))
        sw.FRAME_DICT["0"] = frame

        sw.update_frames()

        assert np.all(sw.frames["0"][0] == np.ones((20, 100, 100, 3)))
        assert len(sw.frames) == 1
        assert mock_imshow.mock_calls[0].args[0] == "displayarray (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[0].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[1].args[0] == "0 -  1 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[1].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[2].args[0] == "0 -  2 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[2].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[3].args[0] == "0 -  3 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[3].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[4].args[0] == "0 -  4 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[4].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[5].args[0] == "0 -  5 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[5].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[6].args[0] == "0 -  6 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[6].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[7].args[0] == "0 -  7 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[7].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[8].args[0] == "0 -  8 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[8].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[9].args[0] == "0 -  9 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[9].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[10].args[0] == "0 -  10 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[10].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[11].args[0] == "0 -  11 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[11].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[12].args[0] == "0 -  12 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[12].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[13].args[0] == "0 -  13 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[13].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[14].args[0] == "0 -  14 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[14].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[15].args[0] == "0 -  15 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[15].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[16].args[0] == "0 -  16 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[16].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[17].args[0] == "0 -  17 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[17].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[18].args[0] == "0 -  18 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[18].args[1] == np.ones((100, 100, 3)))
        assert mock_imshow.mock_calls[19].args[0] == "0 -  19 (press ESC to quit)"
        assert np.all(mock_imshow.mock_calls[19].args[1] == np.ones((100, 100, 3)))


def test_update_frames_exception():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        cv2, "imshow"
    ) as mock_imshow:
        sw = sub_win.SubscriberWindows()

        frame = RuntimeError("Sent from FrameUpdater")
        sw.FRAME_DICT["0"] = frame

        with pytest.raises(RuntimeError) as e:
            sw.update_frames()
        assert e.value == frame


def test_update():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        sub_win.SubscriberWindows, "update_frames"
    ) as mock_update_win_frames, mock.patch(
        "displayarray.window.subscriber_windows.window_commands"
    ) as mock_win_cmd, mock.patch.object(
        sub_win.SubscriberWindows, "handle_keys"
    ) as mock_handle_keys, mock.patch.object(
        cv2, "waitKey"
    ) as key:
        sub_cmd = mock_win_cmd.win_cmd_sub.return_value = mock.MagicMock()
        key.return_value = 2
        mock_cmd = sub_cmd.get.return_value = mock.MagicMock()
        mock_key = mock_handle_keys.return_value = mock.MagicMock()

        sw = sub_win.SubscriberWindows()

        cmd, key = sw.update()

        assert mock_win_cmd.win_cmd_sub.call_count == 2
        assert mock_update_win_frames.call_count == 2
        assert sub_cmd.get.call_count == 2
        assert cmd == mock_cmd
        assert key == mock_key


def test_update_with_array():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        sub_win.SubscriberWindows, "update_frames"
    ) as mock_update_win_frames, mock.patch(
        "displayarray.window.subscriber_windows.window_commands"
    ) as mock_win_cmd, mock.patch.object(
        sub_win.SubscriberWindows, "handle_keys"
    ) as mock_handle_keys, mock.patch.object(
        sub_win.SubscriberWindows, "add_source"
    ) as add_source, mock.patch.object(
        sub_win.SubscriberWindows, "add_window"
    ) as add_window, mock.patch(
        "displayarray.window.subscriber_windows.global_cv_display_callback"
    ) as mock_cb, mock.patch.object(
        cv2, "waitKey"
    ) as key:
        sw = sub_win.SubscriberWindows()

        sw.update(arr=1, id=2)

        mock_cb.assert_called_once_with(1, 2)
        add_source.assert_has_calls([mock.call(0), mock.call(2)])
        add_window.assert_has_calls([mock.call("displayarray"), mock.call(2)])


def test_wait_for_init():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        sub_win.SubscriberWindows, "update"
    ) as update:
        sw = sub_win.SubscriberWindows()

        def mock_update():
            sw.frames = mock_update.frames[mock_update.i]
            mock_update.i += 1
            return "", ""

        mock_update.frames = [[], [], [], [1]]
        mock_update.i = 0

        update.side_effect = mock_update

        sw.wait_for_init()

        assert mock_update.i == 4


def test_end():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch(
        "displayarray.window.subscriber_windows.window_commands"
    ) as mock_win_cmd, mock.patch(
        "displayarray.window.subscriber_windows.subscriber_dictionary.stop_cam"
    ) as mock_stop:
        sw = sub_win.SubscriberWindows()

        sw.close_threads = [mock.MagicMock(), mock.MagicMock()]

        sw.end()

        mock_win_cmd.quit.assert_called_with(force_all_read=False)
        mock_stop.assert_called_with("0")
        sw.close_threads[0].join.assert_called_once()
        sw.close_threads[1].join.assert_called_once()


def test_enter_exit():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        sub_win.SubscriberWindows, "end"
    ) as end:
        with sub_win.SubscriberWindows() as sw:
            assert isinstance(sw, sub_win.SubscriberWindows)

        end.assert_called()


def test_del():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch.object(
        sub_win.SubscriberWindows, "end"
    ) as end:
        sw = sub_win.SubscriberWindows()

        del sw

        end.assert_called_once()


def test_loop():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch.object(cv2, "namedWindow"), mock.patch(
        "displayarray.window.subscriber_windows.window_commands"
    ) as mock_win_cmd, mock.patch(
        "displayarray.window.subscriber_windows.subscriber_dictionary.stop_cam"
    ) as mock_stop, mock.patch.object(
        sub_win.SubscriberWindows, "update"
    ) as update:
        sub_cmd = mock_win_cmd.win_cmd_sub.return_value = mock.MagicMock()

        sw = sub_win.SubscriberWindows()

        def mock_update():
            mock_update.i += 1
            return "", mock_update.keys[mock_update.i]

        mock_update.keys = ["", "", "", "quit"]
        mock_update.i = 0

        update.side_effect = mock_update

        sw.loop()

        assert mock_update.i == 3
        sub_cmd.release.assert_called_once()
        mock_win_cmd.quit.assert_called_with(force_all_read=False)
        mock_stop.assert_called_with("0")


def test_display():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch(
        "displayarray.window.subscriber_windows.FrameUpdater"
    ) as fup, mock.patch(
        "displayarray.window.subscriber_windows.SubscriberWindows"
    ) as sws:
        fup_inst = fup.return_value = mock.MagicMock()
        sws_inst = sws.return_value = mock.MagicMock()

        d = sub_win.display(0, 1, size=(50, 50))

        fup.assert_has_calls(
            [
                mock.call(
                    0, force_backend="", fps_limit=float("inf"), request_size=(50, 50)
                ),
                mock.call(
                    1, force_backend="", fps_limit=float("inf"), request_size=(50, 50)
                ),
            ]
        )
        assert fup_inst.start.call_count == 2
        sws.assert_called_once_with(
            window_names=["window 0", "window 1"], video_sources=(0, 1), silent=False
        )
        assert sws_inst.close_threads == [fup_inst, fup_inst]
        assert d == sws_inst


def test_display_blocking():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch(
        "displayarray.window.subscriber_windows.FrameUpdater"
    ) as fup, mock.patch(
        "displayarray.window.subscriber_windows.SubscriberWindows"
    ) as sws:
        fup_inst = fup.return_value = mock.MagicMock()
        sws_inst = sws.return_value = mock.MagicMock()

        sub_win.display(0, 1, blocking=True)

        assert fup_inst.start.call_count == 2
        sws.assert_called_once_with(
            window_names=["window 0", "window 1"], video_sources=(0, 1), silent=False
        )
        sws_inst.loop.assert_called_once()
        assert fup_inst.join.call_count == 2


def test_display_callbacks():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch(
        "displayarray.window.subscriber_windows.FrameUpdater"
    ) as fup, mock.patch(
        "displayarray.window.subscriber_windows.SubscriberWindows"
    ) as sws:
        cb = mock.MagicMock()

        sub_win.display(0, 1, callbacks=cb)

        fup.assert_has_calls(
            [
                mock.call(
                    0,
                    callbacks=[cb],
                    force_backend="",
                    fps_limit=float("inf"),
                    request_size=(-1, -1),
                ),
                mock.call(
                    1,
                    callbacks=[cb],
                    force_backend="",
                    fps_limit=float("inf"),
                    request_size=(-1, -1),
                ),
            ]
        )

        fup.reset_mock()

        cb2 = mock.MagicMock()

        sub_win.display(0, 1, callbacks=[cb, cb2], fps_limit=60)

        fup.assert_has_calls(
            [
                mock.call(
                    0,
                    callbacks=[cb, cb2],
                    force_backend="",
                    fps_limit=60,
                    request_size=(-1, -1),
                ),
                mock.call(
                    1,
                    callbacks=[cb, cb2],
                    force_backend="",
                    fps_limit=60,
                    request_size=(-1, -1),
                ),
            ]
        )


def test_display_callbacks_dict():
    sub_win.SubscriberWindows.FRAME_DICT = {}
    with mock.patch(
        "displayarray.window.subscriber_windows.FrameUpdater"
    ) as fup, mock.patch(
        "displayarray.window.subscriber_windows.SubscriberWindows"
    ) as sws:
        cb1 = mock.MagicMock()
        cb2 = mock.MagicMock()
        cb3 = mock.MagicMock()

        sub_win.display(0, 1, 2, callbacks={0: cb1, 1: [cb1, cb2], "2": [cb3]})

        fup.assert_has_calls(
            [
                mock.call(
                    0,
                    callbacks=[cb1],
                    force_backend="",
                    fps_limit=float("inf"),
                    request_size=(-1, -1),
                ),
                mock.call(
                    1,
                    callbacks=[cb1, cb2],
                    force_backend="",
                    fps_limit=float("inf"),
                    request_size=(-1, -1),
                ),
                mock.call(
                    2,
                    callbacks=[cb3],
                    force_backend="",
                    fps_limit=float("inf"),
                    request_size=(-1, -1),
                ),
            ]
        )
