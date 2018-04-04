import pubsub

if False:
    from typing import Union


class CamCtrl:

    @staticmethod
    def stop_cam(cam_id  # type: Union[int, str]
                 ):
        pubsub.publish("cvcamhandlers." + str(cam_id) + ".cmd", 'q')

    @staticmethod
    def reset_vid(cam_id  # type: Union[int, str]
                  ):
        pubsub.publish("cvcamhandlers." + str(cam_id) + ".cmd", 'r')

    @staticmethod
    def key_stroke(key_entered):
        pubsub.publish("cvKeyStroke.", key_entered)

