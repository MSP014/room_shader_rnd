"""Protect the Kit Stage-window metadata seam for internal ORMS prims."""

from tools.omniverse.runtime.stage_visibility import (
    HIDE_IN_STAGE_WINDOW_METADATA,
    hide_in_stage_window,
)


class _RecordingPrim:
    def __init__(self):
        self.metadata = {}

    def SetMetadata(self, key, value):
        self.metadata[key] = value
        return True


def test_internal_prim_uses_the_native_stage_window_visibility_metadata():
    prim = _RecordingPrim()

    assert hide_in_stage_window(prim)
    assert prim.metadata == {HIDE_IN_STAGE_WINDOW_METADATA: True}
