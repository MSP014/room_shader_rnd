"""Expose the source-checkout extension package to standalone pytest."""

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXTENSION_ROOT = REPOSITORY_ROOT / "exts" / "msp.orms.runtime"

extension_text = str(EXTENSION_ROOT)
if extension_text not in sys.path:
    sys.path.insert(0, extension_text)
