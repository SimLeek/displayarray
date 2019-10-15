import displayarray.frame.subscriber_dictionary as subd
from localpubsub import VariablePub, VariableSub
import mock


def test_cam_handler():
    my_pub = VariablePub()
    my_sub = VariableSub(my_pub)
    camh = subd.CamHandler("my name", my_sub)

    assert camh.name == "my name"
    assert camh.cmd is None
    assert camh.sub == my_sub
    assert isinstance(camh.pub, VariablePub)
    assert isinstance(camh.cmd_pub, VariablePub)


def test_cam():
    cam = subd.Cam("my name")

    assert cam.name == "my name"
    assert cam.cmd is None
    assert isinstance(cam.frame_pub, VariablePub)
    assert isinstance(cam.cmd_pub, VariablePub)
    assert isinstance(cam.status_pub, VariablePub)


def test_register_cam():
    subd.register_cam("test name")
    assert isinstance(subd.CV_CAMS_DICT["test name"], subd.Cam)
    assert subd.CV_CAMS_DICT["test name"].name == "test name"
    assert isinstance(subd.CV_CAM_HANDLERS_DICT["test name"], subd.CamHandler)
    assert subd.CV_CAM_HANDLERS_DICT["test name"].name == "test name"


def test_stop_cam():
    subd.register_cam("test name 2")
    cam_publish = subd.CV_CAMS_DICT["test name 2"].cmd_pub.publish = mock.MagicMock()
    cam_handler_publish = subd.CV_CAM_HANDLERS_DICT["test name 2"].cmd_pub.publish = mock.MagicMock()

    subd.stop_cam("test name 2")

    cam_publish.assert_called_once_with("quit", blocking=True)
    cam_handler_publish.assert_called_once_with("quit", blocking=True)


def test_cam_cmd_sub():
    subd.register_cam("test name 2")

    sub = subd.cam_cmd_sub("test name 2", blocking=False)

    assert isinstance(sub, VariableSub)
    assert sub.pub == subd.CV_CAMS_DICT["test name 2"].cmd_pub


def test_cam_frame_sub():
    subd.register_cam("test name 2")

    sub = subd.cam_frame_sub("test name 2", blocking=False)

    assert isinstance(sub, VariableSub)
    assert sub.pub == subd.CV_CAMS_DICT["test name 2"].frame_pub


def test_handler_cmd_sub():
    subd.register_cam("test name 2")

    sub = subd.handler_cmd_sub("test name 2", blocking=False)

    assert isinstance(sub, VariableSub)
    assert sub.pub == subd.CV_CAM_HANDLERS_DICT["test name 2"].cmd_pub
