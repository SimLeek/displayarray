import cv2
from .cv_webcam_pub.cam_ctrl import cam_ctrl

if False:
    from typing import List

cvWindows = []
frameDict = {}


def sub_win_loop(*,
                 names,  # type: List[str]
                 input_vid_global_names,  # type: List[str]
                 callbacks=(None,)
                 ):
    global cvWindows
    global frameDict

    first_run = True
    while True:
        for i in range(len(input_vid_global_names)):
            if input_vid_global_names[i] in frameDict and frameDict[input_vid_global_names[i]] is not None:
                if callbacks[i % len(callbacks)] is not None:
                    frames = callbacks[i % len(callbacks)](frameDict[input_vid_global_names[i]])
                else:
                    frames = frameDict[input_vid_global_names[i]]
                for f in range(len(frames)):
                    if first_run:
                        if names[f % len(names)] not in cvWindows:
                            cvWindows.append(names[f % len(names)])
                            cv2.namedWindow(names[f % len(names)])
                    cv2.imshow(names[f % len(names)], frames[f])
            if cv2.waitKey(1) & 0xFF == ord('q'):
                for name in cvWindows:
                    cv2.destroyWindow(name)
                for n in names:
                    cam_ctrl.stop_cam(n)

                return
        first_run = False
