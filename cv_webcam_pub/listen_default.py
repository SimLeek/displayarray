if False:
    from typing import Any, Optional, queue

def _listen_default(sub,           # type: queue
                    block=True,    # type: bool
                    timeout=None,  # type: Optional[float]
                    empty=None     # type: Any
                    ):             # type: (...)->Any
    try:
        msg = (sub.listen(block=block, timeout=timeout))
        try:
            msg = next(msg)['data']
        except StopIteration:
            msg = empty
    except queue.Empty:
        msg = empty
    return msg