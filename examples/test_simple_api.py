import unittest as ut


class TestSubWin(ut.TestCase):
    def test_display_numpy(self):
        from displayarray import display
        import numpy as np

        display(np.random.normal(0.5, 0.1, (500, 500, 3)))

    def test_display_numpy_callback(self):
        from displayarray import display
        import numpy as np

        arr = np.random.normal(0.5, 0.1, (500, 500, 3))

        def fix_arr_cv(arr_in):
            arr_in[:] += np.random.normal(0.01, 0.005, (500, 500, 3))
            arr_in %= 1.0

        display(arr, callbacks=fix_arr_cv, blocking=True)

    def test_display_numpy_loop(self):
        from displayarray import display
        import numpy as np

        arr = np.random.normal(0.5, 0.1, (100, 100, 3))

        with display(arr) as displayer:
            while displayer:
                arr[:] += np.random.normal(0.001, 0.0005, (100, 100, 3))
                arr %= 1.0

    def test_display_camera(self):
        from displayarray import display
        import numpy as np

        def black_and_white(arr):
            return (np.sum(arr, axis=-1) / 3).astype(np.uint8)

        display(0, callbacks=black_and_white, blocking=True)

    def test_display_video(self):
        from displayarray import display
        import math as m

        def forest_color(arr):
            forest_color.i += 1
            arr[..., 0] = (m.sin(forest_color.i * (2 * m.pi) * .4 / 360) * 255 + arr[..., 0]) % 255
            arr[..., 1] = (m.sin((forest_color.i * (2 * m.pi) * .5 + 45) / 360) * 255 + arr[..., 1]) % 255
            arr[..., 2] = (m.cos(forest_color.i * (2 * m.pi) * .3 / 360) * 255 + arr[..., 2]) % 255

        forest_color.i = 0

        display("fractal test.mp4", callbacks=forest_color, blocking=True, fps_limit=120)

    def test_display_tensorflow(self):
        from displayarray import display
        import numpy as np
        from tensorflow.keras import layers, models
        import tensorflow as tf

        for gpu in tf.config.experimental.list_physical_devices("GPU"):
            tf.compat.v2.config.experimental.set_memory_growth(gpu, True)

        displayer = display("fractal test.mp4")
        displayer.wait_for_init()
        autoencoder = models.Sequential()
        autoencoder.add(
            layers.Conv2D(
                20, (3, 3), activation="sigmoid", input_shape=displayer.frames[0].shape
            )
        )
        autoencoder.add(
            layers.Conv2D(
                20, (3, 3), activation="sigmoid", input_shape=displayer.frames[0].shape
            )
        )
        autoencoder.add(layers.Conv2DTranspose(3, (3, 3), activation="sigmoid"))
        autoencoder.add(layers.Conv2DTranspose(3, (3, 3), activation="sigmoid"))

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

    def test_lens_construction(self):
        from displayarray import display
        import numpy as np

        center = (75, 450)
        zoom = .5
        zoom_out = 1.0 / zoom

        arr = np.random.uniform(0, 1, (300, 600, 3))
        display(arr, blocking=True)

        y = np.arange(arr.shape[0])
        x = np.arange(arr.shape[1])
        y_ = (y - center[0]) * zoom_out / arr.shape[0]
        x_ = (x - center[1]) * zoom_out / arr.shape[1]
        p = np.array(np.meshgrid(x_, y_))
        display(p[0] + .5, blocking=True)
        display(p[1] + .5, blocking=True)

        barrel_power = 1.5

        theta = np.arctan2(p[1], p[0])
        display((theta + (np.pi / 2.0)) / (np.pi / 2.0), blocking=True)

        radius = np.linalg.norm(p, axis=0)
        print(radius.shape)
        display(radius, blocking=True)

        radius = pow(radius, barrel_power)
        display(radius, blocking=True)

        print(len(x))
        x_new = 0.5 * (radius * np.cos(theta) + 1)
        display(x_new, blocking=True)
        x_new = np.clip(x_new * len(x), 0, len(x) - 1)
        display(x_new / float(len(x)), blocking=True)

        y_new = 0.5 * (radius * np.sin(theta) + 1)
        display(y_new, blocking=True)
        y_new = np.clip(y_new * len(y), 0, len(y) - 1)

        p = np.array(np.meshgrid(y, x)).astype(np.uint32)

        p_new = np.array((y_new, x_new)).astype(np.uint32)

        arr[p[0], p[1], :] = np.swapaxes(arr[p_new[0], p_new[1], :], 0, 1)
        display(arr, blocking=True)

    def test_display_lens(self):
        from displayarray import display
        from displayarray.input import mouse_loop
        import numpy as np
        import cv2
        import skimage.measure
        import skimage.transform

        def lens(arr):
            center = lens.center
            zoom = lens.zoom
            zoom_out = 1.0 / zoom[0]
            if not isinstance(lens.bleed[0], np.ndarray):
                lens.bleed[0] = np.zeros_like(arr)

            y = np.arange(arr.shape[0])
            x = np.arange(arr.shape[1])
            y_ = (y - arr.shape[0] / 2.0) * zoom_out / arr.shape[0]
            x_ = (x - arr.shape[1] / 2.0) * zoom_out / arr.shape[1]
            p = np.array(np.meshgrid(x_, y_))

            y2_ = (y - center[0]) * zoom_out / arr.shape[0]
            x2_ = (x - center[1]) * zoom_out / arr.shape[1]
            p2 = np.array(np.meshgrid(x2_, y2_))

            barrel_power = lens.power[0]

            theta = np.arctan2(p2[1], p2[0])

            radius = np.linalg.norm(p2, axis=0)

            radius = pow(radius, barrel_power)

            x_new = 0.5 * (radius * np.cos(theta) + 1)
            x_new = np.clip(x_new * len(x), 0, len(x) - 1)

            y_new = 0.5 * (radius * np.sin(theta) + 1)
            y_new = np.clip(y_new * len(y), 0, len(y) - 1)

            p = np.array(np.meshgrid(y, x)).astype(np.uint32)

            p_new = np.array((y_new, x_new)).astype(np.uint32)

            # arr[p[0], p[1], :] = np.swapaxes(arr[p_new[0], p_new[1], :], 0, 1)
            arr2 = lens.bleed[0].copy()
            arr2[y,...] = (arr2[y,...] + arr2[(y+1)%len(y), ...])/2
            arr2[y, ...] = (arr2[y, ...] + arr2[(y - 1) % len(y), ...]) / 2
            arr2[:,x, ...] = (arr2[:,x, ...] + arr2[:, (x + 1) % len(x), ...]) / 2
            arr2[:,x, ...] = (arr2[:,x, ...] + arr2[:, (x - 1) % len(x), ...]) / 2
            #arr2 = np.zeros_like(arr)
            arr2[p_new[0], p_new[1], :] = np.swapaxes(arr[p[0], p[1], :], 0, 1)
            #lens.bleed[0][p_new[0], p_new[1], :] = np.swapaxes(arr[p[0], p[1], :], 0, 1)
            #avg = skimage.measure.block_reduce(arr2, (2,2, 1), np.min)
            #avg2 = skimage.transform.resize(avg, (arr2.shape))
            lens.bleed[0]=arr2
            #lens.bleed

            return arr2

        lens.center = [250, 250]
        lens.zoom = [.5]
        lens.power = [1.0]
        lens.bleed = [None]

        @mouse_loop
        def m_loop(me):
            m_loop.center[:] = [me.y, me.x]
            if me.event == cv2.EVENT_MOUSEWHEEL:
                if me.flags & cv2.EVENT_FLAG_CTRLKEY:
                    if me.flags > 0:
                        m_loop.zoom[0] *= 1.1
                    else:
                        m_loop.zoom[0] /= 1.1
                else:
                    if me.flags > 0:
                        m_loop.power[0] *= 1.1
                    else:
                        m_loop.power[0] /= 1.1

        m_loop.center = lens.center
        m_loop.zoom = lens.zoom
        m_loop.power = lens.power

        display("fractal test.mp4", callbacks=lens, blocking=True)
