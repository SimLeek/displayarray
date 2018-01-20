import pubsub
if False:
    from typing import Union

class cam_ctrl:

    @staticmethod
    def stop_cam(cam_id  # type: Union[int, str]
                 ):
        pubsub.publish("cvcamhandlers." + str(cam_id) + ".cmd", 'q')