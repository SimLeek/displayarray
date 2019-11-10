displayarray
============

A library for displaying arrays as video in Python.

Display arrays while updating them
----------------------------------

.. figure:: https://i.imgur.com/UEt6iR6.gif
   :alt: 

::

    from displayarray import display
    import numpy as np

    arr = np.random.normal(0.5, 0.1, (100, 100, 3))

    with display(arr) as d:
        while d:
            arr[:] += np.random.normal(0.001, 0.0005, (100, 100, 3))
            arr %= 1.0

Run functions on 60fps webcam or video input
--------------------------------------------

|image0|

(Video Source: https://www.youtube.com/watch?v=WgXQ59rg0GM)

::

    from displayarray import display
    import math as m

    def forest_color(arr):
        forest_color.i += 1
        arr[..., 0] = (m.sin(forest_color.i*(2*m.pi)*4/360)*255 + arr[..., 0]) % 255
        arr[..., 1] = (m.sin((forest_color.i * (2 * m.pi) * 5 + 45) / 360) * 255 + arr[..., 1]) % 255
        arr[..., 2] = (m.cos(forest_color.i*(2*m.pi)*3/360)*255 + arr[..., 2]) % 255

    forest_color.i = 0

    display("fractal test.mp4", callbacks=forest_color, blocking=True, fps_limit=120)

Display tensors as they're running through TensorFlow or PyTorch
----------------------------------------------------------------

.. figure:: https://i.imgur.com/TejCpIP.png
   :alt: 

::

    # see test_display_tensorflow in test_simple_apy for full code.

    ...

    autoencoder.compile(loss="mse", optimizer="adam")

    while displayer:
        grab = tf.convert_to_tensor(
            displayer.FRAME_DICT["fractal test.mp4frame"][np.newaxis, ...].astype(np.float32)
            / 255.0
        )
        grab_noise = tf.convert_to_tensor(
            (((displayer.FRAME_DICT["fractal test.mp4frame"][np.newaxis, ...].astype(
                np.float32) + np.random.uniform(0, 255, grab.shape)) / 2) % 255)
            / 255.0
        )
        displayer.update((grab_noise.numpy()[0] * 255.0).astype(np.uint8), "uid for grab noise")
        autoencoder.fit(grab_noise, grab, steps_per_epoch=1, epochs=1)
        output_image = autoencoder.predict(grab, steps=1)
        displayer.update((output_image[0] * 255.0).astype(np.uint8), "uid for autoencoder output")

Handle input events
-------------------

Mouse events captured whenever the mouse moves over the window:

::

    event:0
    x,y:133,387
    flags:0
    param:None

Code:

::

    from displayarray.input import mouse_loop
    from displayarray import display

    @mouse_loop
    def print_mouse_thread(mouse_event):
        print(mouse_event)

    display("fractal test.mp4", blocking=True)

Installation
------------

displayarray is distributed on `PyPI <https://pypi.org>`__ as a
universal wheel in Python 3.6+ and PyPy.

::

    $ pip install displayarray

Usage
-----

API has been generated `here <https://simleek.github.io/displayarray/index.html>`_.

See tests and examples for example usage.

License
-------

displayarray is distributed under the terms of both

-  `MIT License <https://choosealicense.com/licenses/mit>`__
-  `Apache License, Version
   2.0 <https://choosealicense.com/licenses/apache-2.0>`__

at your option.

.. |image0| image:: https://thumbs.gfycat.com/AbsoluteEarnestEelelephant-size_restricted.gif
   :target: https://gfycat.com/absoluteearnesteelelephant
