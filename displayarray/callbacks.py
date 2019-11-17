"""Standard callbacks to use on incoming frames."""

from displayarray.window import window_commands
import numpy as np

from typing import Union


def global_cv_display_callback(frame: np.ndarray, cam_id: Union[int, str]):
    """
    Send frames to the global frame dictionary.

    :param frame: The video or image frame
    :type frame: np.ndarray
    :param cam_id: The video or image source
    :type cam_id: Union[int, str]
    """
    from displayarray.window import SubscriberWindows

    SubscriberWindows.FRAME_DICT[str(cam_id)] = frame


class function_display_callback(object):  # NOSONAR
    """
    Used for running arbitrary functions on pixels.

    .. code-block:: python

      >>> import random
      >>> from displayarray.frame import FrameUpdater
      >>> img = np.zeros((300, 300, 3))
      >>> def fun(array, coords, finished):
      ...     r,g,b = random.random()/20.0, random.random()/20.0, random.random()/20.0
      ...     array[coords[0:2]] = (array[coords[0:2]] + [r,g,b])%1.0
      >>> FrameUpdater(video_source=img, callbacks=function_display_callback(fun)).display()

    :param display_function: a function to run on the input image.
    :param finish_function: a function to run on the input image when the other function finishes.
    """

    def __init__(self, display_function, finish_function=None):
        """Run display_function on frames."""
        self.looping = True
        self.first_call = True

        def _run_finisher(self, frame, finished, *args, **kwargs):
            if not callable(finish_function):
                window_commands.quit()
            else:
                finished = finish_function(frame, Ellipsis, finished, *args, **kwargs)
                if finished:
                    window_commands.quit()

        def _display_internal(self, frame, *args, **kwargs):
            finished = True
            if self.first_call:
                # return to display initial frame
                self.first_call = False
                return
            if self.looping:
                it = np.nditer(frame, flags=["multi_index"])
                while not it.finished:
                    x, y, c = it.multi_index
                    finished = display_function(
                        frame, (x, y, c), finished, *args, **kwargs
                    )
                    it.iternext()
            if finished:
                self.looping = False
                _run_finisher(self, frame, finished, *args, **kwargs)

        self.inner_function = _display_internal

    def __call__(self, *args, **kwargs):
        """Call the function "function_display_callback" was set up with."""
        return self.inner_function(self, *args, **kwargs)
