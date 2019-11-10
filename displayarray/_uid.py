"""Generate unique IDs for videos."""

from collections.abc import Hashable


def uid_for_source(video_source):
    """Get a uid for any source so it can be passed through the publisher-subscriber system."""
    if len(str(video_source)) <= 1000:
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
