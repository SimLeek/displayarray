import cv2
from ..webcam_pub.camctrl import CamCtrl


if False:
    from typing import List

frame_dict = {}

def triangle_seen():
    print("a triangle was seen")
def square_seen():
    print("a square was seen")
def nothing_seen():
    print("nothing was seen")

command_dict = {
    "t": triangle_seen,
    "s": square_seen,
    " ": nothing_seen
}

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
                if callbacks[i % len(callbacks)] is not None:
                    frames = callbacks[i % len(callbacks)](frame_dict[input_vid_global_names[i]])
                else:
                    frames = frame_dict[input_vid_global_names[i]]
                for f in range(len(frames)):
                    cv2.imshow(names[f % len(names)]+" (press q to quit)", frames[f])
                    if cv2.getWindowProperty(names[f % len(names)]+" (press q to quit)", 0) != 0:
                        print("X was pressed")
                        for name in names:
                            cv2.destroyWindow(name)
                        for c in input_cams:
                            CamCtrl.stop_cam(c)


            key_criteria = cv2.waitKey(1) & 0xFF

            if key_criteria == ord("q"):
                for name in names:
                    cv2.destroyWindow(name)
                for c in input_cams:
                    CamCtrl.stop_cam(c)
                return

            if chr(key_criteria) in command_dict:
                command_dict[chr(key_criteria)]()
                CamCtrl.key_stroke(chr(key_criteria))
            elif chr(key_criteria) != "ÿ":
                print(chr(key_criteria))


