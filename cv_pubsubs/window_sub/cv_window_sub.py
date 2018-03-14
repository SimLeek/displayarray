import cv2
from ..webcam_pub.camctrl import CamCtrl

if False:
    from typing import List

frame_dict = {}


def destruct_windows(window_names, input_cams):
    for name in window_names:
        cv2.destroyWindow(name)
    for c in input_cams:
        CamCtrl.stop_cam(c)

def set_frames_from_callbacks(input_vid_global_names, callbacks, frame):
    global frame_dict

    if callbacks[frame % len(callbacks)] is not None:
        frames = callbacks[frame % len(callbacks)](frame_dict[input_vid_global_names[frame]])
    else:
        frames = frame_dict[input_vid_global_names[frame]]
    return frames

# todo: figure out how to get the red x button to work. Try: https://stackoverflow.com/a/37881722/782170
def sub_win_loop(
                 names,  # type: List[str]
                 input_vid_global_names,  # type: List[str]
                 callbacks=(None,),
                 input_cams=(0,)
                 ):
    global frame_dict

    while True:
        for i in range(len(input_vid_global_names)):
            if input_vid_global_names[i] in frame_dict and frame_dict[input_vid_global_names[i]] is not None:
                frames = set_frames_from_callbacks(input_vid_global_names, callbacks, i)
                for f in range(len(frames)):
                    cv2.imshow(names[f % len(names)], frames[f])
            if cv2.waitKey(1) & 0xFF == ord('q'):
                destruct_windows(names, input_cams)
                return
