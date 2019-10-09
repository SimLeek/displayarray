from displayarray import display
import numpy as np
from tensorflow.keras import layers, models
import tensorflow as tf
from examples.videos import test_video_2

for gpu in tf.config.experimental.list_physical_devices("GPU"):
    tf.compat.v2.config.experimental.set_memory_growth(gpu, True)

displayer = display(test_video_2)
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
    displayer.update()
    grab = tf.convert_to_tensor(
        next(iter(displayer.FRAME_DICT.values()))[np.newaxis, ...].astype(np.float32) / 255.0
    )
    grab_noise = tf.convert_to_tensor(
        ((next(iter(displayer.FRAME_DICT.values()))[np.newaxis, ...].astype(
            np.float32) + np.random.uniform(0, 255, grab.shape)) / 2)
        / 255.0
    )
    displayer.update((grab_noise.numpy()[0] * 255.0).astype(np.uint8), "uid for grab noise")
    autoencoder.fit(grab_noise, grab, steps_per_epoch=1, epochs=1)
    output_image = autoencoder.predict(grab, steps=1)
    displayer.update((output_image[0] * 255.0).astype(np.uint8), "uid for autoencoder output")
