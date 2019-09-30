import numpy as np
from collections import Hashable


def uid_for_source(video_source):
    if len(str(video_source)) <= 1000:
        uid = str(video_source)
    elif isinstance(video_source, Hashable):
        uid = str(hash(video_source))
    else:
        uid = str(hash(str(video_source)))
    return uid
