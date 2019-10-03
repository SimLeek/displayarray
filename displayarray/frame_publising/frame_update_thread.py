import threading
from typing import Union, Tuple, Any, Callable, List, Optional

import numpy as np

from displayarray.callbacks import global_cv_display_callback
from displayarray.uid import uid_for_source
from displayarray.frame_publising import subscriber_dictionary
from displayarray.frame_publising.frame_publishing import pub_cam_thread
from displayarray.subscriber_window import window_commands

FrameCallable = Callable[[np.ndarray], Optional[np.ndarray]]


class VideoHandlerThread(threading.Thread):
    """Thread for publishing frames from a video source."""

    def __init__(
        self,
        video_source: Union[int, str, np.ndarray] = 0,
        callbacks: Optional[Union[List[FrameCallable], FrameCallable]] = None,
        request_size: Tuple[int, int] = (-1, -1),
        high_speed: bool = True,
        fps_limit: float = 240,
    ):
        super(VideoHandlerThread, self).__init__(target=self.loop, args=())
        self.cam_id = uid_for_source(video_source)
        self.video_source = video_source
        if callbacks is None:
            callbacks = []
        if callable(callbacks):
            self.callbacks = [callbacks]
        else:
            self.callbacks = callbacks
        self.request_size = request_size
        self.high_speed = high_speed
        self.fps_limit = fps_limit
        self.exception_raised = None

    def __wait_for_cam_id(self):
        while str(self.cam_id) not in subscriber_dictionary.CV_CAMS_DICT:
            continue

    def __apply_callbacks_to_frame(self, frame):
        if frame is not None:
            frame_c = None
            for c in self.callbacks:
                try:
                    frame_c = c(frame)
                except TypeError as te:
                    raise TypeError(
                        "Callback functions for cvpubsub need to accept two arguments: array and uid"
                    )
                except Exception as e:
                    self.exception_raised = e
                    frame = frame_c = self.exception_raised
                    subscriber_dictionary.stop_cam(self.cam_id)
                    window_commands.quit()
                    raise e
            if frame_c is not None:
                global_cv_display_callback(frame_c, self.cam_id)
            else:
                global_cv_display_callback(frame, self.cam_id)

    def loop(self):
        """Continually get frames from the video publisher, run callbacks on them, and listen to commands."""
        t = pub_cam_thread(
            self.video_source, self.request_size, self.high_speed, self.fps_limit
        )
        self.__wait_for_cam_id()

        sub_cam = subscriber_dictionary.cam_frame_sub(str(self.cam_id))
        sub_owner = subscriber_dictionary.handler_cmd_sub(str(self.cam_id))
        msg_owner = sub_owner.return_on_no_data = ""
        while msg_owner != "quit":
            frame = sub_cam.get(blocking=True, timeout=1.0)  # type: np.ndarray
            self.__apply_callbacks_to_frame(frame)
            msg_owner = sub_owner.get()
        sub_owner.release()
        sub_cam.release()
        subscriber_dictionary.stop_cam(self.cam_id)
        t.join()

    def display(self, callbacks: List[Callable[[np.ndarray], Any]] = None):
        """
        Start default display operation.

        For multiple video sources, please use something outside of this class.

        :param callbacks: List of callbacks to be run on frames before displaying to the screen.
        """
        from displayarray.subscriber_window import SubscriberWindows

        if callbacks is None:
            callbacks = []
        self.start()
        SubscriberWindows(video_sources=[self.cam_id], callbacks=callbacks).loop()
        self.join()
        if self.exception_raised is not None:
            raise self.exception_raised
