"""Generate unique IDs for videos."""

from collections.abc import Hashable

import numpy as np

try:
    import torch
    pytorch_available = True
except ImportError:
    pytorch_available = False

try:
    import scipy
    scipy_available = True
except ImportError:
    scipy_available = False


def uid_for_source(video_source):
    """Get a uid for any source so it can be passed through the publisher-subscriber system."""
    if scipy_available and isinstance(video_source, scipy.sparse.csr_matrix):
        uid = str(id(video_source))
    elif pytorch_available and isinstance(video_source, torch.Tensor) and video_source.layout==torch.sparse_csr:
        uid = str(id(video_source))
    elif isinstance(video_source, np.ndarray):
        uid = str(video_source.__array_interface__['data'][0])  # get array data pointer
    elif len(str(video_source)) <= 1000:
        uid = str(video_source)
    elif isinstance(video_source, Hashable):
        try:
            uid = str(hash(video_source))
        except TypeError:
            raise NotImplementedError(
                "Displaying immutables filled with mutables is not allowed yet. "
                "No tuples of arrays."
            )
    else:
        uid = str(hash(str(video_source)))
    return uid
