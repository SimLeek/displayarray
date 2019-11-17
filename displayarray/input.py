"""Decorators for creating input loops that OpenCV handles."""

from displayarray.window import window_commands
import threading
import time

from typing import Callable


class MouseEvent(object):
    """Holds all the OpenCV mouse event information."""

    def __init__(self, event, x, y, flags, param):
        """Create an OpenCV mouse event."""
        self.event = event
        self.x = x
        self.y = y
        self.flags = flags
        self.param = param

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "event:{}\nx,y:{},{}\nflags:{}\nparam:{}\n".format(
            self.event, self.x, self.y, self.flags, self.param
        )


class _mouse_thread(object):  # NOSONAR
    """Run a function on mouse information that is received by the window."""

    def __init__(self, f):
        self.f = f
        self.sub_mouse = window_commands.mouse_pub.make_sub()

    def __call__(self, *args, **kwargs):
        """Call the function this was set up with."""
        self.f(self.sub_mouse, *args, **kwargs)


class _mouse_loop_thread(object):  # NOSONAR
    """Run a function on mouse information that is received by the window, in the main loop."""

    def __init__(self, f, run_when_no_events=False, fps=60):
        self.f = f
        self.sub_mouse = window_commands.mouse_pub.make_sub()
        self.sub_cmd = window_commands.win_cmd_pub.make_sub()
        self.sub_cmd.return_on_no_data = ""
        self.run_when_no_events = run_when_no_events
        self.fps = fps

    def __call__(self, *args, **kwargs):
        """Run the function this was set up with in a loop."""
        msg_cmd = ""
        while msg_cmd != "quit":
            mouse_xyzclick = self.sub_mouse.get(blocking=True)  # type: MouseEvent
            if mouse_xyzclick is not self.sub_mouse.return_on_no_data:
                self.f(mouse_xyzclick, *args, **kwargs)
            elif self.run_when_no_events:
                self.f(None, *args, **kwargs)
            msg_cmd = self.sub_cmd.get()
            time.sleep(1.0 / self.fps)
        window_commands.quit(force_all_read=False)


class mouse_loop(object):  # NOSONAR
    """
    Run a function on mouse information that is received by the window, continuously in a new thread.

    .. code-block:: python

      >>> @mouse_loop
      ... def fun(mouse_event):
      ...   print("x:{}, y:{}".format(mouse_event.x, mouse_event.y))
    """

    def __init__(self, f):
        """Start a new mouse thread for the decorated function."""
        self.t = threading.Thread(
            target=_mouse_loop_thread(f, run_when_no_events=False)
        )
        self.t.start()

    def __call__(self, *args, **kwargs):
        """Return the thread that was started with the function passed in."""
        return self.t


class _key_thread(object):  # NOSONAR
    """Run a function on mouse information that is received by the window."""

    def __init__(self, f):
        self.f = f
        self.sub_key = window_commands.key_pub.make_sub()

    def __call__(self, *args, **kwargs):
        """Call the function this was set up with."""
        self.f(self.sub_key, *args, **kwargs)


class _key_loop_thread(object):  # NOSONAR
    """Run a function on mouse information that is received by the window, in the main loop."""

    def __init__(self, f, run_when_no_events=False, fps=60):
        self.f = f
        self.sub_key = window_commands.key_pub.make_sub()
        self.sub_cmd = window_commands.win_cmd_pub.make_sub()
        self.sub_cmd.return_on_no_data = ""
        self.run_when_no_events = run_when_no_events
        self.fps = fps

    def __call__(self, *args, **kwargs):
        """Run the function this was set up with in a loop."""
        msg_cmd = ""
        while msg_cmd != "quit":
            key_chr = self.sub_key.get()  # type: chr
            if key_chr is not self.sub_key.return_on_no_data:
                self.f(key_chr, *args, **kwargs)
            elif self.run_when_no_events:
                self.f(None, *args, **kwargs)
            msg_cmd = self.sub_cmd.get()
            time.sleep(1.0 / self.fps)
        window_commands.quit(force_all_read=False)


class key_loop(object):  # NOSONAR
    """
    Run a function on mouse information that is received by the window, continuously in a new thread.

    .. code-block:: python

      >>> @key_loop
      ... def fun(key):
      ...   print("key pressed:{}".format(key))
    """

    def __init__(self, f: Callable[[str], None]):
        """Start a new key thread for the decorated function."""
        self.t = threading.Thread(target=_key_loop_thread(f, run_when_no_events=False))
        self.t.start()

    def __call__(self, *args, **kwargs):
        """Return the thread that was started with the function passed in."""
        return self.t
