from threading import Lock
from localpubsub import VariablePub, VariableSub

if False:
    from typing import Union, Dict


class CamHandler(object):
    def __init__(self, name, sub):
        self.name = name
        self.cmd = None
        self.sub = sub  # type: VariableSub
        self.pub = VariablePub()
        self.cmd_pub = VariablePub()


class Cam(object):
    def __init__(self, name):
        self.name = name
        self.cmd = None
        self.frame_pub = VariablePub()
        self.cmd_pub = VariablePub()
        self.status_pub = VariablePub()


class CamCtrl(object):
    cv_cam_handlers_dict = {}  # type: Dict[str, CamHandler]
    cv_cams_dict = {}  # type: Dict[str, Cam]

    @staticmethod
    def register_cam(cam_id):
        cam = Cam(str(cam_id))
        CamCtrl.cv_cams_dict[str(cam_id)] = cam
        CamCtrl.cv_cam_handlers_dict[str(cam_id)] = CamHandler(str(cam_id), cam.frame_pub.make_sub())

    @staticmethod
    def stop_cam(cam_id  # type: Union[int, str]
                 ):
        CamCtrl.cv_cams_dict[str(cam_id)].cmd_pub.publish('quit', blocking=True)
        CamCtrl.cv_cam_handlers_dict[str(cam_id)].cmd_pub.publish('quit', blocking=True)

    @staticmethod
    def cam_cmd_sub(cam_id, blocking=True):
        if blocking:
            while cam_id not in CamCtrl.cv_cams_dict:
                continue
        return CamCtrl.cv_cams_dict[str(cam_id)].cmd_pub.make_sub()

    @staticmethod
    def cam_frame_sub(cam_id, blocking=True):
        if blocking:
            while cam_id not in CamCtrl.cv_cams_dict:
                continue
        return CamCtrl.cv_cams_dict[str(cam_id)].frame_pub.make_sub()

    @staticmethod
    def cam_status_sub(cam_id, blocking=True):
        if blocking:
            while cam_id not in CamCtrl.cv_cams_dict:
                continue
        return CamCtrl.cv_cams_dict[str(cam_id)].status_pub.make_sub()

    @staticmethod
    def handler_cmd_sub(cam_id, blocking=True):
        if blocking:
            while cam_id not in CamCtrl.cv_cam_handlers_dict:
                continue
        return CamCtrl.cv_cam_handlers_dict[str(cam_id)].cmd_pub.make_sub()