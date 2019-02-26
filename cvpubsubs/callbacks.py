from cvpubsubs.window_sub.winctrl import WinCtrl
import numpy as np

if False:
    from typing import Union


def global_cv_display_callback(frame,  # type: np.ndarray
                               cam_id  # type: Union[int, str]
                               ):
    from cvpubsubs.window_sub import SubscriberWindows
    """Default callback for sending frames to the global frame dictionary.

    :param frame: The video or image frame
    :type frame: np.ndarray
    :param cam_id: The video or image source
    :type cam_id: Union[int, str]
    """
    SubscriberWindows.frame_dict[str(cam_id) + "frame"] = frame


class function_display_callback(object):  # NOSONAR
    def __init__(self, display_function, finish_function=None):
        """Used for running arbitrary functions on pixels.

        >>> import random
        >>> from cvpubsubs.webcam_pub import VideoHandlerThread
        >>> img = np.zeros((300, 300, 3))
        >>> def fun(array, coords, finished):
        ...     r,g,b = random.random()/20.0, random.random()/20.0, random.random()/20.0
        ...     array[coords[0:2]] = (array[coords[0:2]] + [r,g,b])%1.0
        >>> VideoHandlerThread(video_source=img, callbacks=function_display_callback(fun)).display()

        :param display_function: a function to run on the input image.
        :param finish_function: a function to run on the input image when the other function finishes.
        """
        self.looping = True
        self.first_call = True

        def _run_finisher(self, frame, finished, *args, **kwargs):
            if not callable(finish_function):
                WinCtrl.quit()
            else:
                finished = finish_function(frame, Ellipsis, finished, *args, **kwargs)
                if finished:
                    WinCtrl.quit()

        def _display_internal(self, frame, cam_id, *args, **kwargs):
            finished = True
            if self.first_call:
                # return to display initial frame
                self.first_call = False
                return
            if self.looping:
                it = np.nditer(frame, flags=['multi_index'])
                while not it.finished:
                    x, y, c = it.multi_index
                    finished = display_function(frame, (x, y, c), finished, *args, **kwargs)
                    it.iternext()
            if finished:
                self.looping = False
                _run_finisher(self, frame, finished, *args, **kwargs)

        self.inner_function = _display_internal

    def __call__(self, *args, **kwargs):
        return self.inner_function(self, *args, **kwargs)
