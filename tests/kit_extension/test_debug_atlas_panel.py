"""Protect staged global debug-atlas controls and artist feedback."""

import inspect

from msp.orms.runtime.debug_atlas_panel import (
    _DEBUG_HELP,
    _status,
    build_debug_atlas_panel,
)
from msp.orms.runtime.resources import AtlasResource, DebugAtlasDecision


def test_debug_atlas_panel_exposes_browse_clear_and_apply_guidance():
    source = inspect.getsource(build_debug_atlas_panel)

    assert '"Browse..."' in source
    assert '"Clear"' in source
    assert "stage_debug_atlas_directory" in source
    assert "clear_debug_atlas_directory" in source
    assert "Apply Interior Sets" in _DEBUG_HELP
    assert "if decision.validation_error:" in source


def test_debug_atlas_status_distinguishes_default_override_and_fallback(
    tmp_path,
):
    packaged = AtlasResource(1, tmp_path / "packaged.png", 8, "packaged")
    custom = AtlasResource(1, tmp_path / "custom.png", 4, "debug override")

    assert _status(DebugAtlasDecision(1, "", packaged)) == (
        "Packaged default: 8 variants."
    )
    assert _status(DebugAtlasDecision(1, "custom", custom)) == (
        "Custom override: 4 variants."
    )
    assert "packaged fallback" in _status(
        DebugAtlasDecision(1, "missing", packaged, "directory is missing")
    )
