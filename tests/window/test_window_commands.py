import displayarray.window.window_commands as win_com
from localpubsub import VariablePub, VariableSub
import mock


def test_pubs():
    assert isinstance(win_com.key_pub, VariablePub)
    assert isinstance(win_com.mouse_pub, VariablePub)
    assert isinstance(win_com.win_cmd_pub, VariablePub)


def test_quit():
    with mock.patch.object(win_com.win_cmd_pub, "publish") as mock_pub:
        win_com.quit()
        mock_pub.assert_called_once_with("quit", force_all_read=True)
        mock_pub.reset_mock()
        win_com.quit(False)
        mock_pub.assert_called_once_with("quit", force_all_read=False)


def test_win_cmd_sub():
    with mock.patch.object(win_com.win_cmd_pub, "make_sub") as mock_make:
        win_com.win_cmd_sub()
        mock_make.assert_called_once()
