"""Publisher-subscriber commands to and from the camera."""

from localpubsub import VariablePub, VariableSub

from typing import Union, Dict


class CamHandler(object):
    """A camera handler instance that will send commands to and receive data from a camera."""

    def __init__(self, name, sub):
        """Create the cam handler."""
        self.name = name
        self.cmd = None
        self.sub: VariableSub = sub
        self.pub = VariablePub()
        self.cmd_pub = VariablePub()


class Cam(object):
    """A camera publisher instance that will send frames, status, and commands out."""

    def __init__(self, name, cam_instance=None):
        """Create the cam."""
        self.name = name
        self.cmd = None
        self.frame_pub = VariablePub()
        self.cmd_pub = VariablePub()
        self.status_pub = VariablePub()
        self.cam_instance = cam_instance


CV_CAM_HANDLERS_DICT: Dict[str, CamHandler] = {}
CV_CAMS_DICT: Dict[str, Cam] = {}


def register_cam(cam_id, cam_instance=None):
    """Register camera "cam_id" to a global list so it can be picked up."""
    cam = Cam(str(cam_id), cam_instance)
    CV_CAMS_DICT[str(cam_id)] = cam
    CV_CAM_HANDLERS_DICT[str(cam_id)] = CamHandler(
        str(cam_id), cam.frame_pub.make_sub()
    )


def stop_cam(cam_id: Union[int, str]):
    """Tell camera "cam_id" to end it's main loop."""
    if str(cam_id) in CV_CAMS_DICT:
        CV_CAMS_DICT[str(cam_id)].cmd_pub.publish("quit", blocking=True)
    if str(cam_id) in CV_CAM_HANDLERS_DICT:
        CV_CAM_HANDLERS_DICT[str(cam_id)].cmd_pub.publish("quit", blocking=True)


def cam_cmd_sub(cam_id, blocking=True):
    """Get a command subscriber for registered camera "cam_id"."""
    if blocking:
        while cam_id not in CV_CAMS_DICT:
            continue
    return CV_CAMS_DICT[str(cam_id)].cmd_pub.make_sub()


def cam_frame_sub(cam_id, blocking=True):
    """Get a frame subscriber for registered camera "cam_id"."""
    if blocking:
        while cam_id not in CV_CAMS_DICT:
            continue
    return CV_CAMS_DICT[str(cam_id)].frame_pub.make_sub()


def cam_status_sub(cam_id, blocking=True):
    """Get a status subscriber for registered camera "cam_id"."""
    if blocking:
        while cam_id not in CV_CAMS_DICT:
            continue
    return CV_CAMS_DICT[str(cam_id)].status_pub.make_sub()


def handler_cmd_sub(cam_id, blocking=True):
    """Get a command subscriber for registered camera "cam_id" handler."""
    if blocking:
        while cam_id not in CV_CAM_HANDLERS_DICT:
            continue
    return CV_CAM_HANDLERS_DICT[str(cam_id)].cmd_pub.make_sub()
