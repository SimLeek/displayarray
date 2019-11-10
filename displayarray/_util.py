"""Functions needed to deal with OpenCV."""

import weakref


class WeakMethod(weakref.WeakMethod):
    """Pass any method to OpenCV without it keeping a reference forever."""

    def __call__(self, *args, **kwargs):
        """Call the actual method this object was made with."""
        obj = super().__call__()
        func = self._func_ref()
        if obj is None or func is None:
            return None
        meth = self._meth_type(func, obj)
        meth(*args, **kwargs)
