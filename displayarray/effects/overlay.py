"""Overlay functions."""


def overlay_transparent(background, overlay, x=None, y=None):
    """
    Overlay a transparent image on top of a background image.

    :param background: background rgb image to overlay on top of
    :param overlay: rgba image to overlay on top of the background
    :param x: leftmost part to overlay at on the background
    :param y: topmost part to overlay at on the background
    """
    # https://stackoverflow.com/a/54058766/782170
    assert overlay.shape[2] == 4, "Overlay must be BGRA"

    background_width = background.shape[1]
    background_height = background.shape[0]

    if (x is not None and x >= background_width) or (
        y is not None and y >= background_height
    ):
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x is None:
        x = int(background_width / 2 - w / 2)
    if y is None:
        y = int(background_height / 2 - h / 2)

    if x < 0:
        w += x
        overlay = overlay[:, -x:]

    if y < 0:
        w += y
        overlay = overlay[:, -y:]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]

    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h]

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y : y + h, x : x + w] = (1.0 - mask) * background[
        y : y + h, x : x + w
    ] + mask * overlay_image

    return background
