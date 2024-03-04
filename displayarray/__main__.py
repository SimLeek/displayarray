"""
DisplayArray.

Display NumPy arrays.

Usage:
  displayarray (-w <webcam-number> | -v <video-filename> | -t <topic-name>[,dtype])... [-m <msg-backend>]
  displayarray -h
  displayarray --version


Options:
  -h, --help                                           Show this help text.
  --version                                            Show version number.
  -w <webcam-number>, --webcam=<webcam-number>         Display video from a webcam.
  -v <video-filename>, --video=<video-filename>        Display frames from a video file.
  -t <topic-name>, --topic=<topic-name>                Display frames from a topic using the chosen message broker.
  -m <msg-backend>, --message-backend <msg-backend>    Choose message broker backend. [Default: ROS]
                                                       Currently supported: ROS, ZeroMQ
  --ros                                                Use ROS as the backend message broker.
  --zeromq                                             Use ZeroMQ as the backend message broker.
"""

from docopt import docopt
import asyncio


def main(argv=None):
    """Process command line arguments."""
    arguments = docopt(__doc__, argv=argv)
    if arguments["--version"]:
        from displayarray import __version__

        print(f"DisplayArray V{__version__}")
        return
    from displayarray import display

    vids = [int(w) for w in arguments["--webcam"]] + arguments["--video"]
    v_disps = None
    if vids:
        v_disps = display(*vids, blocking=False)
        while v_disps:
            pass



if __name__ == "__main__":
    main()
