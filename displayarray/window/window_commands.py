"""Commands to control the array displaying windows."""

from localpubsub import VariablePub, VariableSub

key_pub = VariablePub()
mouse_pub = VariablePub()
win_cmd_pub = VariablePub()


def quit(force_all_read=True):
    """Quit the main loop displaying all the windows."""
    win_cmd_pub.publish("quit", force_all_read=force_all_read)


def win_cmd_sub() -> VariableSub:
    """Get a subscriber to the main window loop."""
    return win_cmd_pub.make_sub()
