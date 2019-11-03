import sys
import threading
import time

import cv2
import numpy as np

from displayarray import read_updates
from displayarray.frame import subscriber_dictionary
from displayarray.frame.frame_updater import FrameCallable
from .np_to_opencv import NpCam
from displayarray.uid import uid_for_source

from typing import Union, Tuple, Optional, Dict, Any, List, Callable


def pub_cam_loop(
    cam_id: Union[int, str, np.ndarray],
    request_size: Tuple[int, int] = (-1, -1),
    high_speed: bool = True,
    fps_limit: float = 240,
) -> bool:
    """
    Publish whichever camera you select to CVCams.<cam_id>.Vid.

    You can send a quit command 'quit' to CVCams.<cam_id>.Cmd
    Status information, such as failure to open, will be posted to CVCams.<cam_id>.Status

    :param high_speed: Selects mjpeg transferring, which most cameras seem to support, so speed isn't limited
    :param fps_limit: Limits the frames per second.
    :param cam_id: An integer representing which webcam to use, or a string representing a video file.
    :param request_size: A tuple with width, then height, to request the video size.
    :return: True if loop ended normally, False if it failed somehow.
    """
    name = uid_for_source(cam_id)

    if isinstance(cam_id, (int, str)):
        cam: Union[NpCam, cv2.VideoCapture] = cv2.VideoCapture(cam_id)
    elif isinstance(cam_id, np.ndarray):
        cam = NpCam(cam_id)
    else:
        raise TypeError(
            "Only strings or ints representing cameras, or numpy arrays representing pictures supported."
        )

    subscriber_dictionary.register_cam(name)

    # cam.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    frame_counter = 0

    sub = subscriber_dictionary.cam_cmd_sub(name)
    sub.return_on_no_data = ""
    msg = ""

    if high_speed:
        cam.set(cv2.CAP_PROP_FOURCC, cv2.CAP_OPENCV_MJPEG)

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, request_size[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, request_size[1])

    if not cam.isOpened():
        subscriber_dictionary.CV_CAMS_DICT[name].status_pub.publish("failed")
        return False
    now = time.time()
    while msg != "quit":
        time.sleep(1.0 / (fps_limit - (time.time() - now)))
        now = time.time()
        (ret, frame) = cam.read()  # type: Tuple[bool, np.ndarray ]
        if ret is False or not isinstance(frame, np.ndarray):
            cam.release()
            subscriber_dictionary.CV_CAMS_DICT[name].status_pub.publish("failed")
            return False
        if cam.get(cv2.CAP_PROP_FRAME_COUNT) > 0:
            frame_counter += 1
            if frame_counter >= cam.get(cv2.CAP_PROP_FRAME_COUNT):
                frame_counter = 0
                cam = cv2.VideoCapture(cam_id)
        subscriber_dictionary.CV_CAMS_DICT[name].frame_pub.publish(frame)
        msg = sub.get()
    sub.release()

    cam.release()
    return True


def pub_cam_thread(
    cam_id: Union[int, str],
    request_ize: Tuple[int, int] = (-1, -1),
    high_speed: bool = True,
    fps_limit: float = 240,
) -> threading.Thread:
    """Run pub_cam_loop in a new thread. Starts on creation."""
    t = threading.Thread(
        target=pub_cam_loop, args=(cam_id, request_ize, high_speed, fps_limit)
    )
    t.start()
    return t


def publish_updates_zero_mq(
    *vids,
    callbacks: Optional[
        Union[Dict[Any, FrameCallable], List[FrameCallable], FrameCallable]
    ] = None,
    fps_limit=float("inf"),
    size=(-1, -1),
    end_callback: Callable[[], bool] = lambda: False,
    blocking=True,
    publishing_address="tcp://127.0.0.1:5600",
    prepend_topic=""
):
    import zmq

    ctx = zmq.Context()
    s = ctx.socket(zmq.PUB)
    s.bind(publishing_address)

    try:
        for v in read_updates(vids, callbacks, fps_limit, size, end_callback, blocking):
            for vid_name, frame in v.items():
                s.send_multipart([prepend_topic + vid_name, frame])
    except KeyboardInterrupt:
        pass
    finally:
        vid_names = [uid_for_source(name) for name in vids]
        for v in vid_names:
            subscriber_dictionary.stop_cam(v)
        sys.exit()


def publish_updates_ros(
    *vids,
    callbacks: Optional[
        Union[Dict[Any, FrameCallable], List[FrameCallable], FrameCallable]
    ] = None,
    fps_limit=float("inf"),
    size=(-1, -1),
    end_callback: Callable[[], bool] = lambda: False,
    blocking=True,
    node_name="displayarray"
):
    # mostly copied from:
    # https://answers.ros.org/question/289557/custom-message-including-numpy-arrays/?answer=321122#post-id-321122

    import rospy
    from std_msgs.msg import Float32MultiArray, MultiArrayDimension, UInt8MultiArray

    vid_names = [uid_for_source(name) for name in vids]
    rospy.init_node(node_name, anonymous=True)
    pubs = {
        vid_name: rospy.Publisher(vid_name, Float32MultiArray, queue_size=1)
        for vid_name in vid_names
    }
    try:
        for v in read_updates(vids, callbacks, fps_limit, size, end_callback, blocking):
            if rospy.is_shutdown():
                print("ROS is shutdown.")
                break
            for vid_name, frame in v.items():
                if frame.dtype == np.uint8:
                    frame_msg = UInt8MultiArray()
                elif frame.dtype == np.float32:
                    frame_msg = Float32MultiArray()
                else:
                    raise NotImplementedError(
                        "Only uint8 and float32 types supported currently."
                    )
                frame_msg.layout.dim = []
                dims = np.array(frame.shape)
                frame_size = dims.prod() / float(
                    frame.nbytes
                )  # this is my attempt to normalize the strides size depending on .nbytes. not sure this is correct

                for i in range(0, len(dims)):  # should be rather fast.
                    # gets the num. of dims of nparray to construct the message
                    frame_msg.layout.dim.append(MultiArrayDimension())
                    frame_msg.layout.dim[i].size = dims[i]
                    frame_msg.layout.dim[i].stride = dims[i:].prod() / frame_size
                    frame_msg.layout.dim[i].label = "dim_%d" % i

                frame_msg.data = np.frombuffer(frame.tobytes())
                pubs[vid_name].publish(frame_msg)
    except KeyboardInterrupt:
        pass
    finally:
        vid_names = [uid_for_source(name) for name in vids]
        for v in vid_names:
            subscriber_dictionary.stop_cam(v)
        sys.exit()
