import threading

import numpy as np
import pubsub

from cvpubsubs.listen_default import listen_default
from .pub_cam import pub_cam_thread

if False:
    from typing import Union, Tuple, Any, Callable, List

from cvpubsubs.window_sub import SubscriberWindows


def global_cv_display_callback(frame,  # type: np.ndarray
                               cam_id  # type: Union[int, str]
                               ):
    """Default callback for sending frames to the global frame dictionary.

    :param frame: The video or image frame
    :type frame: np.ndarray
    :param cam_id: The video or image source
    :type cam_id: Union[int, str]
    """
    SubscriberWindows.frame_dict[str(cam_id) + "frame"] = (frame,)

display_callbacks = [global_cv_display_callback]

class VideoHandlerThread(threading.Thread):
    "Thread for publishing frames from a video source."

    def __init__(self, video_source=0,  # type: Union[int, str]
                 callbacks=(global_cv_display_callback,),  # type: List[Callable[[np.ndarray, int], Any]]
                 request_size=(1280, 720),  # type: Tuple[int, int]
                 high_speed=True,  # type: bool
                 fps_limit=240  # type: float
                 ):
        """Sets up the main thread loop.

        :param video_source: The video or image source. Integers typically access webcams, while strings access files.
        :type video_source: Union[int, str]
        :param callbacks: A list of operations to be performed on every frame, including publishing.
        :type callbacks: List[Callable[[np.ndarray, int], Any]]
        :param request_size: Requested video size. Actual size may vary, since this is requesting from the hardware.
        :type request_size: Tuple[int, int]
        :param high_speed: If true, use compression to increase speed.
        :type high_speed: bool
        :param fps_limit: Limits frames per second.
        :type fps_limit: float
        """
        super(VideoHandlerThread, self).__init__(target=self.loop, args=())
        self.cam_id = video_source
        self.callbacks = callbacks
        self.request_size = request_size
        self.high_speed = high_speed
        self.fps_limit = fps_limit

    def loop(self):
        """Continually gets frames from the video publisher, runs callbacks on them, and listens to commands."""
        t = pub_cam_thread(self.cam_id, self.request_size, self.high_speed, self.fps_limit)
        sub_cam = pubsub.subscribe("CVCams." + str(self.cam_id) + ".Vid")
        sub_owner = pubsub.subscribe("CVCamHandlers." + str(self.cam_id) + ".Cmd")
        msg_owner = ''
        while msg_owner != 'quit':
            frame = listen_default(sub_cam, timeout=.1)  # type: np.ndarray
            if frame is not None:
                frame = frame[0]
                for c in self.callbacks:
                    c(frame, self.cam_id)
            msg_owner = listen_default(sub_owner, block=False, empty='')
        pubsub.publish("CVCams." + str(self.cam_id) + ".Cmd", 'quit')
        t.join()

    def display(self,
                callbacks=()  # type: List[Callable[[List[np.ndarray]], Any]]
                ):
        """Default display operation. For multiple video sources, please use something outside of this class.

        :param callbacks: List of callbacks to be run on frames before displaying to the screen.
        :type callbacks: List[Callable[[List[np.ndarray]], Any]]
        """
        self.start()
        SubscriberWindows(video_sources=[self.cam_id], callbacks=callbacks).loop()
        self.join()
