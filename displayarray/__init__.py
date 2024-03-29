"""
Display any array, webcam, or video file.

display is a function that displays these in their own windows.
"""

__version__ = "2.0.0"

from .window.subscriber_windows import display, breakpoint_display, read_updates, publish_updates
from . import effects
