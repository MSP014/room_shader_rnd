"""Protect composed-stage metrics, resource discovery, and aperture extraction."""

import pytest
from pxr import Usd, UsdGeom

from tools.omniverse.shared_room.contracts import (
    METRICS_MODE_LOCAL_OVERRIDE,
    RuntimeClassifierSettings,
)
from tools.omniverse.shared_room.stage import (
    discover_atlas_family_availability,
    extract_stage_apertures,
    resolve_stage_metrics,
)

from ._support import REPOSITORY_ROOT, _window_stage


def test_auto_metrics_use_authored_stage_values_without_mutation():
    stage, _ = _window_stage()
    root_before = stage.GetRootLayer().ExportToString()

    metrics = resolve_stage_metrics(stage, RuntimeClassifierSettings())

    assert metrics.up_axis == "Y"
    assert metrics.meters_per_unit == pytest.approx(1.0)
    assert not metrics.diagnostics
    assert stage.GetRootLayer().ExportToString() == root_before


def test_missing_metrics_and_conflicting_local_override_are_diagnostic_only():
    missing_stage = Usd.Stage.CreateInMemory()
    missing_before = missing_stage.GetRootLayer().ExportToString()
    missing = resolve_stage_metrics(missing_stage, RuntimeClassifierSettings())

    stage, _ = _window_stage()
    override = resolve_stage_metrics(
        stage,
        RuntimeClassifierSettings(
            metrics_mode=METRICS_MODE_LOCAL_OVERRIDE,
            local_up_axis="Z",
            local_meters_per_unit=0.01,
        ),
    )

    assert (missing.up_axis, missing.meters_per_unit) == ("Y", 1.0)
    assert missing.diagnostics[0].state == "MISSING_OR_INVALID_STAGE_METRICS"
    assert missing_stage.GetRootLayer().ExportToString() == missing_before
    assert (override.up_axis, override.meters_per_unit) == ("Z", 0.01)
    assert override.diagnostics[0].state == "LOCAL_STAGE_METRICS_OVERRIDE"


def test_extraction_converts_stage_units_to_metres():
    stage, _ = _window_stage((1,))
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    metrics = resolve_stage_metrics(stage, RuntimeClassifierSettings())

    extraction = extract_stage_apertures(stage, metrics)
    aperture = extraction.apertures[0]

    assert aperture.centre_metres == pytest.approx((0.005, 0.005, 0.0))
    assert aperture.tangent_u_metres == pytest.approx((0.01, 0.0, 0.0))
    assert aperture.tangent_v_metres == pytest.approx((0.0, 0.01, 0.0))


def test_all_four_repository_atlas_families_are_complete():
    assert discover_atlas_family_availability(REPOSITORY_ROOT) == frozenset(
        {1, 2, 3, 4}
    )
