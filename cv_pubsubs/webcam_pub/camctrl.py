import pubsub
if False:
    from typing import Union


class CamCtrl:

    @staticmethod
    def stop_cam(cam_id  # type: Union[int, str]
                 ):
        pubsub.publish("cvcamhandlers." + str(cam_id) + ".cmd", 'q')
