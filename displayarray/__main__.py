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
    from displayarray.frame.frame_updater import read_updates_ros, read_updates_zero_mq

    topics = arguments["--topic"]
    topics_split = [t.split(",") for t in topics]
    d = display()

    async def msg_recv():
        nonlocal d
        while d:
            if arguments["--message-backend"] == "ROS":
                async for v_name, frame in read_updates_ros(
                    [t for t, d in topics_split], [d for t, d in topics_split]
                ):
                    d.update(arr=frame, id=v_name)
            if arguments["--message-backend"] == "ZeroMQ":
                async for v_name, frame in read_updates_zero_mq(
                    *[bytes(t, encoding="ascii") for t in topics]
                ):
                    d.update(arr=frame, id=v_name)

    async def update_vids():
        while v_disps:
            if v_disps:
                v_disps.update()
                await asyncio.sleep(0)

    async def runner():
        await asyncio.wait([msg_recv(), update_vids()])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner())
    loop.close()


if __name__ == "__main__":
    main()
