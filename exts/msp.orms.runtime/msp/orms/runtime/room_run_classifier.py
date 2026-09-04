"""Preserve the historical room-run classifier import path."""

import sys

from ..classification import classifier as _classifier

# Aliasing the module object preserves monkeypatches and identity-sensitive
# contracts; copying exports here would create a second observable facade state.
sys.modules[__name__] = _classifier
