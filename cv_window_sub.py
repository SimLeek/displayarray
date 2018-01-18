import cv2, pubsub

if False:
    from typing import List

cvWindows = []
frameDict={}
import time
def cv_win_sub(*,
               names,  # type: List[str]
               inputVidGlobalNames,  # type: List[str]
               callbacks=(None,)
               ):
    global cvWindows

    global frameDict
    firstRun=True
    timeMod = None
    while True:
        t = int(time.time()) * 1000
        if firstRun:
            timeMod = t % 1000
            firstRun = False
        #global camImg
        for i in range(len(inputVidGlobalNames)):
            if inputVidGlobalNames[i] in frameDict and frameDict[inputVidGlobalNames[i]] is not None:
                if callbacks[i%len(callbacks)] is not None:
                    frames = callbacks[i%len(callbacks)](frameDict[inputVidGlobalNames[i]])
                else:
                    frames = frameDict[inputVidGlobalNames[i]]
                for i in range(len(frames)):
                    if t % 1000 == timeMod:
                        if names[i%len(names)]+str(i) not in cvWindows:
                            cvWindows.append(names[i%len(names)]+str(i))
                            cv2.namedWindow(names[i%len(names)]+str(i))
                    cv2.imshow(names[i%len(names)]+str(i), frames[i])
            if cv2.waitKey(1)& 0xFF==ord('q'):
                for name in cvWindows:
                    cv2.destroyWindow(name)
                for n in names:
                    pubsub.publish("cvcamhandlers." + str(n) + ".cmd", "q")

                return


camImg = None
if __name__ == '__main__':
    import importlib
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    cv_webcam_pub = importlib.import_module('cv_webcam_pub')

    def camHandler(frame, camId):
        frameDict[str(camId)+"Frame"]= frame

    t = cv_webcam_pub.init_cv_cam_pub_handler(0, camHandler)

    cv_win_sub(names=['cammy', 'cammy2'], inputVidGlobalNames=[str(0)+"Frame"])

    pubsub.publish("cvcamhandlers.0.cmd", 'q')
    t.join()