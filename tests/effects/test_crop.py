import displayarray.effects.crop as crop
import numpy as np
from displayarray.input import mouse_loop
import mock


def test_init_defaults():
    c = crop.Crop()

    assert np.all(c.output_size == (64, 64, 3))
    assert all(c.center == [32, 32, 1])
    assert c.odd_center is None
    assert c.input_size is None


def test_init():
    c = crop.Crop((32, 32, 3), (16, 16, 1))

    c(np.ndarray((64, 64, 3)))

    assert np.all(c.output_size == (32, 32, 3))
    assert np.all(c.center == (16, 16, 1))
    assert np.all(c.odd_center == [0, 0, 1])
    assert c.input_size == (64, 64, 3)


def test_1d_crop():
    c = crop.Crop((4,))

    cropped = c(np.ones((8,)))

    assert np.all(cropped == np.ones((4,)))


def test_1d_edges():
    c = crop.Crop((4,), (0,))

    cropped = c(np.ones((8,)))

    assert np.all(cropped == np.concatenate((np.ones((2,)), np.zeros((2,)))))
    c.center[...] = [8]
    cropped = c(np.ones((8,)))

    assert np.all(cropped == np.concatenate((np.zeros((2,)), np.ones((2,)))))


def test_2d_crop():
    c = crop.Crop((4, 5))

    cropped = c(np.ones((8, 8)))

    assert np.all(cropped == np.ones((4, 5)))


def test_2d_edges():
    c = crop.Crop((4, 5), (0, 4))

    cropped = c(np.ones((8, 8)))

    assert np.all(
        cropped
        == np.array(
            [[1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
        )
    )
    c.center = [4, 0]
    cropped = c(np.ones((8, 8)))

    assert np.all(
        cropped
        == np.array(
            [[1, 1, 1, 0, 0], [1, 1, 1, 0, 0], [1, 1, 1, 0, 0], [1, 1, 1, 0, 0]]
        )
    )

    c.center = [8, 8]
    cropped = c(np.ones((8, 8)))

    assert np.all(
        cropped
        == np.array(
            [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 1, 1], [0, 0, 0, 1, 1]]
        )
    )

    c.center = [4, 8]
    cropped = c(np.ones((8, 8)))

    assert np.all(
        cropped
        == np.array(
            [[0, 0, 0, 1, 1], [0, 0, 0, 1, 1], [0, 0, 0, 1, 1], [0, 0, 0, 1, 1]]
        )
    )


def test_enable_mouse_control():
    with mock.patch.object(crop, "mouse_loop") as m_loop:
        decorate = m_loop.return_value = mock.MagicMock()
        c = crop.Crop()
        assert c.mouse_control == None

        c.enable_mouse_control()
        m_loop.assert_called_once()

        assert c.mouse_control == decorate
