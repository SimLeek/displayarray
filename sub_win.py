import cv2
from .cv_webcam_pub.cam_ctrl import cam_ctrl

if False:
    from typing import List

cvWindows = []
frameDict = {}


# todo: figure out how to get the red x button to work. Try: https://stackoverflow.com/a/37881722/782170
def sub_win_loop(*,
                 names,  # type: List[str]
                 input_vid_global_names,  # type: List[str]
                 callbacks=(None,),
                 input_cams=(0,)
                 ):
    global cvWindows
    global frameDict

    while True:
        for i in range(len(input_vid_global_names)):
            if input_vid_global_names[i] in frameDict and frameDict[input_vid_global_names[i]] is not None:
                if callbacks[i % len(callbacks)] is not None:
                    frames = callbacks[i % len(callbacks)](frameDict[input_vid_global_names[i]])
                else:
                    frames = frameDict[input_vid_global_names[i]]
                for f in range(len(frames)):
                    cv2.imshow(names[f % len(names)], frames[f])
            if cv2.waitKey(1) & 0xFF == ord('q'):
                for name in names:
                    cv2.destroyWindow(name)
                for c in input_cams:
                    cam_ctrl.stop_cam(c)
                return
