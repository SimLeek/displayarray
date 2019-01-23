import threading
import logging

from localpubsub import VariablePub, VariableSub


class WinCtrl(object):
    key_pub = VariablePub()
    win_cmd_pub = VariablePub()

    @staticmethod
    def quit(force_all_read=True):
        WinCtrl.win_cmd_pub.publish('quit', force_all_read=force_all_read)

    @staticmethod
    def win_cmd_sub(): # type: ()->VariableSub
        return WinCtrl.win_cmd_pub.make_sub()  # type: VariableSub
