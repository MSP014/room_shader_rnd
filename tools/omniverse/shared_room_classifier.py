"""Preserve the historical shared-room controller import path."""

import sys

from .shared_room import controller as _controller

# The controller owns singleton subscriptions.  A module alias ensures legacy
# imports observe the same lifecycle state as the canonical package path.
sys.modules[__name__] = _controller
