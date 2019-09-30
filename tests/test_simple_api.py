import unittest as ut

class TestSubWin(ut.TestCase):

    def test_display_numpy(self):
        from cvpubsubs import display
        import numpy as np

        display(np.random.normal(0.5, .1, (500,500,3)))

    def test_display_numpy_callback(self):
        from cvpubsubs import display
        import numpy as np

        arr = np.random.normal(0.5, .1, (500, 500, 3))

        def fix_arr_cv(arr_in):
            arr_in[:] += np.random.normal(0.01, .005, (500, 500, 3))
            arr_in%=1.0

        display(arr, callbacks= fix_arr_cv, blocking=True)

    def test_display_numpy_loop(self):
        from cvpubsubs import display
        import numpy as np

        arr = np.random.normal(0.5, .1, (500, 500, 3))

        displayer, ids = display(arr, blocking = False)

        while True:
            arr[:] += np.random.normal(0.01, .005, (500, 500, 3))
            arr %= 1.0
            displayer.update(arr, ids[0])
        displayer.end()

    def test_display_tensorflow(self):
        from cvpubsubs import display
        import numpy as np
        from tensorflow.keras import layers, models
        import tensorflow as tf

        for gpu in tf.config.experimental.list_physical_devices("GPU"):
            tf.compat.v2.config.experimental.set_memory_growth(gpu, True)
        #tf.keras.backend.set_floatx("float16")

        displayer, ids = display(0, blocking = False)
        displayer.wait_for_init()
        autoencoder = models.Sequential()
        autoencoder.add(
            layers.Conv2D(20, (3, 3), activation="sigmoid", input_shape=displayer.frames[0].shape)
        )
        autoencoder.add(layers.Conv2DTranspose(3, (3, 3), activation="sigmoid"))

        autoencoder.compile(loss="mse", optimizer="adam")

        while True:
            grab = tf.convert_to_tensor(displayer.frame_dict['0frame'][np.newaxis, ...].astype(np.float32)/255.0)
            autoencoder.fit(grab, grab, steps_per_epoch=1, epochs=1)
            output_image = autoencoder.predict(grab, steps=1)
            displayer.update((output_image[0]*255.0).astype(np.uint8), "uid for autoencoder output")
