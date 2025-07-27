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
import numpy as np

def main(argv=None):
    """Process command line arguments."""
    arguments = docopt(__doc__, argv=argv)
    if arguments["--version"]:
        from displayarray import __version__

        print(f"DisplayArray V{__version__}")
        return
    from displayarray import DirectRead, DirectDisplay

    vids = [int(w) for w in arguments["--webcam"]] + arguments["--video"]
    v_disps = None
    display = DirectDisplay()
    if vids:
        v_disps = DirectRead(*vids)
        for frame_dict in v_disps:
            for name, frame in frame_dict.items():
                im = frame.astype(np.uint8)
                display.imshow(f'{name}', im)
            display.update()
            if display.window.is_closing:
                break
            continue



if __name__ == "__main__":
    main()
