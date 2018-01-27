import cv2
from .cv_webcam_pub.camctrl import CamCtrl

if False:
    from typing import List

cvWindows = []
frame_dict = {}


# todo: figure out how to get the red x button to work. Try: https://stackoverflow.com/a/37881722/782170
def sub_win_loop(*,
                 names,  # type: List[str]
                 input_vid_global_names,  # type: List[str]
                 callbacks=(None,),
                 input_cams=(0,)
                 ):
    global cvWindows
    global frame_dict

    while True:
        for i in range(len(input_vid_global_names)):
            if input_vid_global_names[i] in frame_dict and frame_dict[input_vid_global_names[i]] is not None:
                if callbacks[i % len(callbacks)] is not None:
                    frames = callbacks[i % len(callbacks)](frame_dict[input_vid_global_names[i]])
                else:
                    frames = frame_dict[input_vid_global_names[i]]
                for f in range(len(frames)):
                    cv2.imshow(names[f % len(names)], frames[f])
            if cv2.waitKey(1) & 0xFF == ord('q'):
                for name in names:
                    cv2.destroyWindow(name)
                for c in input_cams:
                    CamCtrl.stop_cam(c)
                return
