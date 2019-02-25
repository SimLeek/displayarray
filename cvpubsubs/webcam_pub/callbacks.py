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

        :param display_function:
        :param finish_function:
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


class pytorch_function_display_callback(object):  # NOSONAR
    def __init__(self, display_function, finish_function=None):
        """Used for running arbitrary functions on pixels.

        >>> import random
        >>> import torch
        >>> from cvpubsubs.webcam_pub import VideoHandlerThread
        >>> img = np.zeros((300, 300, 3))
        >>> def fun(array, coords, finished):
        ...     rgb = torch.empty(array.shape).uniform_(0,1).type(torch.DoubleTensor).to(array.device)/150.0
        ...     array[coords] = (array[coords+np.ones_like(coords)] + rgb[coords])%1.0
        >>> VideoHandlerThread(video_source=img, callbacks=pytorch_function_display_callback(fun)).display()

        thanks: https://medium.com/@awildtaber/building-a-rendering-engine-in-tensorflow-262438b2e062

        :param display_function:
        :param finish_function:
        """

        import torch
        from torch.autograd import Variable

        self.looping = True
        self.first_call = True

        def _run_finisher(self, frame, finished, *args, **kwargs):
            if not callable(finish_function):
                WinCtrl.quit()
            else:
                finished = finish_function(frame, Ellipsis, finished, *args, **kwargs)
                if finished:
                    WinCtrl.quit()

        def _setup(self, frame, cam_id, *args, **kwargs):

            if "device" in kwargs:
                self.device = torch.device(kwargs["device"])
            else:
                if torch.cuda.is_available():
                    self.device = torch.device("cuda")
                else:
                    self.device = torch.device("cpu")

            self.min_bounds = [0 for _ in frame.shape]
            self.max_bounds = list(frame.shape)
            grid_slices = [slice(self.min_bounds[d], self.max_bounds[d]) for d in range(len(frame.shape))]
            self.space_grid = np.mgrid[grid_slices]
            x_tens = torch.LongTensor(self.space_grid[0, ...]).to(self.device)
            y_tens = torch.LongTensor(self.space_grid[1, ...]).to(self.device)
            c_tens = torch.LongTensor(self.space_grid[2, ...]).to(self.device)
            self.x = Variable(x_tens, requires_grad=False)
            self.y = Variable(y_tens, requires_grad=False)
            self.c = Variable(c_tens, requires_grad=False)

        def _display_internal(self, frame, cam_id, *args, **kwargs):
            finished = True
            if self.first_call:
                # return to display initial frame
                _setup(self, frame, finished, *args, **kwargs)
                self.first_call = False
                return
            if self.looping:
                tor_frame = torch.from_numpy(frame).to(self.device)
                finished = display_function(tor_frame, (self.x, self.y, self.c), finished, *args, **kwargs)
                frame[...] = tor_frame.cpu().numpy()[...]
            if finished:
                self.looping = False
                _run_finisher(self, frame, finished, *args, **kwargs)

        self.inner_function = _display_internal

    def __call__(self, *args, **kwargs):
        return self.inner_function(self, *args, **kwargs)
