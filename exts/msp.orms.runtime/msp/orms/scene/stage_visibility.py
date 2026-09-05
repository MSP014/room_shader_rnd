# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Keep extension-owned USD implementation prims out of the normal Stage UI."""

from __future__ import annotations

from pxr import Tf, Usd

HIDE_IN_STAGE_WINDOW_METADATA = "hide_in_stage_window"


def hide_in_stage_window(prim: Usd.Prim) -> bool:
    """Apply Kit's Stage-window-only hiding hint without changing visibility."""

    try:
        return bool(prim.SetMetadata(HIDE_IN_STAGE_WINDOW_METADATA, True))
    except Tf.ErrorException:
        # Stock OpenUSD builds do not register this Kit-specific metadata key.
        # Rendering and USD composition remain valid outside Kit.
        return False
