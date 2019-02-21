# CVPubSubs

A  threaded PubSub OpenCV interfaceREADME.md. Webcam and video feeds to multiple windows is supported.

## Installation

CVPubSubs is distributed on `PyPI <https://pypi.org>`_ as a universal
wheel and is available on Linux/macOS and Windows and supports
Python 2.7/3.5+ and PyPy.

    $ pip install CVPubSubs
    
## Usage

### Video Editing and Publishing

#### Display your webcam
    import cvpubsubs.webcam_pub as w
    
    w.VideoHandlerThread().display()
    
#### Change Display Arguments
    import cvpubsubs.webcam_pub as w
    
    video_thread = w.VideoHandlerThread(video_source=0,
                                        callbacks = w.display_callbacks,
                                        request_size=(800, 600),
                                        high_speed = False,
                                        fps_limit = 8
                                        )

    video_thread.display()
    
#### Run your own functions on the frames
    import cvpubsubs.webcam_pub as w
    
    def redden_frame_print_spam(frame, cam_id):
        frame[:, :, 0] = 0
        frame[:, :, 1] = 0
        print("Spam!")

    w.VideoHandlerThread(callbacks=[redden_frame_print_spam] + w.display_callbacks).display()

#### Display a tensor

    def tensor_from_image(frame, cam_id):
        ten = tensor_from_pytorch_or_tensorflow(frame)
        return ten
    
    t = wp.VideoHandlerThread(video_source=cam, callbacks=[tensor_from_image] + wp.display_callbacks)

    t.display()

#### Display multiple windows from one source
    import cvpubsubs.webcam_pub as w
    from cvpubsubs.window_sub import SubscriberWindows

    def cam_handler(frame, cam_id):
        SubscriberWindows.set_global_frame_dict(cam_id, frame, frame)

    t = w.VideoHandlerThread(0, [cam_handler],
                             request_size=(1280, 720),
                             high_speed=True,
                             fps_limit=240
                             )

    t.start()

    SubscriberWindows(window_names=['cammy', 'cammy2'],
                      video_sources=[str(0)]
                      ).loop()

    t.join()
    
#### Display multiple windows from multiple sources
    iport cvpubsubs.webcam_pub as w
    from cvpubsubs.window_sub import SubscriberWindows

    t1 = w.VideoHandlerThread(0)
    t2 = w.VideoHandlerThread(1)

    t1.start()
    t2.start()

    SubscriberWindows(window_names=['cammy', 'cammy2'],
                      video_sources=[0,1]
                      ).loop()

    t1.join()
    t1.join()

## License

CVPubSubs is distributed under the terms of both

- `MIT License <https://choosealicense.com/licenses/mit>`_
- `Apache License, Version 2.0 <https://choosealicense.com/licenses/apache-2.0>`_

at your option.


