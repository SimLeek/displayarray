from cvpubsubs.window_sub.winctrl import WinCtrl
import threading

if False:
    from typing import Callable
    from cvpubsubs.window_sub.mouse_event import MouseEvent


class mouse_thread(object):  # NOSONAR

    def __init__(self, f):
        self.f = f
        self.sub_mouse = WinCtrl.mouse_pub.make_sub()

    def __call__(self, *args, **kwargs):
        self.f(self.sub_mouse, *args, **kwargs)


class mouse_loop_thread(object):  # NOSONAR

    def __init__(self, f, run_when_no_events=False):
        self.f = f
        self.sub_mouse = WinCtrl.mouse_pub.make_sub()
        self.sub_cmd = WinCtrl.win_cmd_pub.make_sub()
        self.sub_cmd.return_on_no_data = ''
        self.run_when_no_events = run_when_no_events

    def __call__(self, *args, **kwargs):
        msg_cmd = ''
        while msg_cmd != 'quit':
            mouse_xyzclick = self.sub_mouse.get()  # type: MouseEvent
            if mouse_xyzclick is not self.sub_mouse.return_on_no_data:
                self.f(mouse_xyzclick, *args, **kwargs)
            elif self.run_when_no_events:
                self.f(None, *args, **kwargs)
            msg_cmd = self.sub_cmd.get()
        WinCtrl.quit(force_all_read=False)


class mouse_loop(object):  # NOSONAR

    def __init__(self, f, run_when_no_events=False):
        self.t = threading.Thread(target=mouse_loop_thread(f, run_when_no_events))
        self.t.start()

    def __call__(self, *args, **kwargs):
        return self.t


class key_thread(object):  # NOSONAR

    def __init__(self, f):
        self.f = f
        self.sub_key = WinCtrl.key_pub.make_sub()

    def __call__(self, *args, **kwargs):
        self.f(self.sub_key, *args, **kwargs)


class key_loop_thread(object):  # NOSONAR

    def __init__(self, f, run_when_no_events=False):
        self.f = f
        self.sub_key = WinCtrl.key_pub.make_sub()
        self.sub_cmd = WinCtrl.win_cmd_pub.make_sub()
        self.sub_cmd.return_on_no_data = ''
        self.run_when_no_events = run_when_no_events

    def __call__(self, *args, **kwargs):
        msg_cmd = ''
        while msg_cmd != 'quit':
            key_chr = self.sub_key.get()  # type: chr
            if key_chr is not self.sub_key.return_on_no_data:
                self.f(key_chr, *args, **kwargs)
            elif self.run_when_no_events:
                self.f(None, *args, **kwargs)
            msg_cmd = self.sub_cmd.get()
        WinCtrl.quit(force_all_read=False)


class key_loop(object):  # NOSONAR

    def __init__(self,
                 f,  # type: Callable[[chr],None]
                 run_when_no_events=False):
        self.t = threading.Thread(target=key_loop_thread(f, run_when_no_events))
        self.t.start()

    def __call__(self, *args, **kwargs):
        return self.t
