import numpy as np
from displayarray import display


def mandel(
    height=240, width=320, itermax=255, y_min=-1.8, y_max=0.6, x_min=-1.6, x_max=1.6
):
    """
    Generate a view of the mandlebrot fractal

    source: https://thesamovar.wordpress.com/2009/03/22/fast-fractals-with-python-and-numpy/

    .. code-block:: python

      >>> img = mandel()
      >>> center = (0, -1.78)
      >>> length = 3.2
      >>> d = display(img)
      >>> while d:
      ...   length*=.9
      ...   y_min = center[1]-length/2.0
      ...   y_max = center[1]+length/2.0
      ...   x_min = center[0]-length/2.0
      ...   x_max = center[0]+length/2.0
      ...   img[...] = mandel(y_min=y_min, y_max=y_max, x_min=x_min, x_max=x_max)
    """

    ix, iy = np.mgrid[0:height, 0:width]
    x = np.linspace(y_min, y_max, height)[ix]
    y = np.linspace(x_min, x_max, width)[iy]
    c = x + complex(0, 1) * y
    del x, y
    img = np.zeros_like(c, dtype=int)
    c.shape = iy.shape = ix.shape = height * width
    z = np.copy(c)
    for i in range(itermax):
        if not len(z):
            break
        z = z * z
        z = z + c
        rem = abs(z) > 4.0
        img[ix[rem], iy[rem]] = i + 1
        rem = ~rem
        z = z[rem]
        ix, iy = ix[rem], iy[rem]
        c = c[rem]
    return img / 255.0


if __name__ == "__main__":
    img = mandel()
    center = (0, -0.6)
    length = 3.2
    d = display(img)
    while d:
        length *= 0.9
        y_min = center[1] - length / 2.0
        y_max = center[1] + length / 2.0
        x_min = center[0] - length / 2.0
        x_max = center[0] + length / 2.0
        img[...] = mandel(y_min=y_min, y_max=y_max, x_min=x_min, x_max=x_max)
