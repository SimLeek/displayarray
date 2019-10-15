import threading
from typing import Union, Tuple, Any, Callable, List, Optional

import numpy as np

from displayarray.callbacks import global_cv_display_callback
from displayarray.uid import uid_for_source
from displayarray.frame import subscriber_dictionary
from displayarray.frame.frame_publishing import pub_cam_thread
from displayarray.window import window_commands
from ..effects.select_channels import SelectChannels

FrameCallable = Callable[[np.ndarray], Optional[np.ndarray]]


class FrameUpdater(threading.Thread):
    """Thread for updating frames from a video source."""

    def __init__(
            self,
            video_source: Union[int, str, np.ndarray] = 0,
            callbacks: Optional[Union[List[FrameCallable], FrameCallable]] = None,
            request_size: Tuple[int, int] = (-1, -1),
            high_speed: bool = True,
            fps_limit: float = 240,
    ):
        super(FrameUpdater, self).__init__(target=self.loop, args=())
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
            try:
                for c in self.callbacks:
                    frame_c = c(frame)
                    if frame_c is not None:
                        frame = frame_c
                if frame.shape[-1] not in [1, 3] and len(frame.shape) != 2:
                    print(f"Too many channels in output. (Got {frame.shape[-1]} instead of 1 or 3.) "
                          f"Frame selection callback added.")
                    print("Ctrl+scroll to change first channel.\n"
                          "Shift+scroll to change second channel.\n"
                          "Alt+scroll to change third channel.")
                    sel = SelectChannels()
                    sel.enable_mouse_control()
                    sel.mouse_print_channels = True
                    self.callbacks.append(sel)
                    frame = self.callbacks[-1](frame)
            except Exception as e:
                self.exception_raised = e
                frame = self.exception_raised
                subscriber_dictionary.stop_cam(self.cam_id)
                window_commands.quit()
                raise e
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
        from displayarray.window import SubscriberWindows

        if callbacks is None:
            callbacks = []
        self.start()
        SubscriberWindows(video_sources=[self.cam_id], callbacks=callbacks).loop()
        self.join()
        if self.exception_raised is not None:
            raise self.exception_raised
