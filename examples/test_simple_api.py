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
            arr[..., 0] = (m.sin(forest_color.i * (2 * m.pi) * 4 / 360) * 255 + arr[..., 0]) % 255
            arr[..., 1] = (m.sin((forest_color.i * (2 * m.pi) * 5 + 45) / 360) * 255 + arr[..., 1]) % 255
            arr[..., 2] = (m.cos(forest_color.i * (2 * m.pi) * 3 / 360) * 255 + arr[..., 2]) % 255

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
