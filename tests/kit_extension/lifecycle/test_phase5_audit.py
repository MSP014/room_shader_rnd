# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect bounded Phase-5 runtime and restore diagnostics."""

from msp.orms.runtime.phase5_audit import (
    Phase5RuntimeAudit,
    runtime_structure_details,
)
from pxr import Sdf, Usd, UsdGeom, UsdShade


def _file_stage(tmp_path):
    path = tmp_path / "scene.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.Xform.Define(stage, "/World")
    stage.GetRootLayer().Save()
    return stage


def _attach_runtime_layer(stage):
    layer = Sdf.Layer.CreateAnonymous("orms_auto_assignment.usda")
    stage.GetSessionLayer().subLayerPaths = [layer.identifier]
    with Usd.EditContext(stage, layer):
        material = UsdShade.Material.Define(
            stage,
            "/__class__/Building/mtl/ORMSRoomMapSingle",
        )
        UsdShade.Shader.Define(
            stage,
            material.GetPath().AppendChild("Shader"),
        )
    return layer


def _ownership(**changes):
    result = {
        "runtime_session_count": 1,
        "classifier_subscription_count": 1,
        "camera_subscription_count": 1,
        "camera_registered_observer_count": 1,
        "camera_update_callback_count": 3,
        "camera_successful_update_count": 2,
        "assignment_session_count": 1,
        "camera_target_count": 1,
    }
    result.update(changes)
    return result


def test_runtime_structure_counts_and_then_releases_owned_overlay(tmp_path):
    stage = _file_stage(tmp_path)
    layer = _attach_runtime_layer(stage)

    active = runtime_structure_details(stage)

    assert active["runtime_layer_count"] == 1
    assert active["runtime_material_spec_count"] == 1
    assert active["runtime_spec_count"] > 0

    stage.GetSessionLayer().subLayerPaths = []
    assert Sdf.Layer.Find(layer.identifier) is layer
    restored = runtime_structure_details(stage)
    assert restored["runtime_layer_count"] == 0
    assert restored["runtime_material_spec_count"] == 0
    assert restored["runtime_spec_count"] == 0


def test_repeated_running_samples_report_stable_structure(tmp_path):
    stage = _file_stage(tmp_path)
    status_records = []
    audit = Phase5RuntimeAudit(
        stage,
        resource_sampler=lambda: {"process_working_set_gib": 2.0},
        log_status=lambda **record: status_records.append(record),
        log_warning=lambda **record: status_records.append(record),
    )
    _attach_runtime_layer(stage)

    audit.sample("STARTED", _ownership())
    audit.sample("RESTARTED", _ownership(classifier_subscription_count=2))

    first, second = status_records[-2:]
    assert first["details"]["structure_matches_first_running_sample"] is True
    assert second["details"]["structure_matches_first_running_sample"] is True
    assert second["details"]["callback_counts_within_expected_bounds"] is True


def test_stop_sample_requires_no_camera_or_classifier_callbacks(tmp_path):
    stage = _file_stage(tmp_path)
    status_records = []
    audit = Phase5RuntimeAudit(
        stage,
        resource_sampler=lambda: {},
        log_status=lambda **record: status_records.append(record),
        log_warning=lambda **record: status_records.append(record),
    )
    _attach_runtime_layer(stage)

    audit.sample(
        "STOPPED",
        _ownership(
            classifier_subscription_count=0,
            camera_subscription_count=0,
        ),
    )

    details = status_records[-1]["details"]
    assert details["runtime_layer_count"] == 1
    assert details["runtime_material_spec_count"] == 1
    assert details["camera_subscription_count"] == 0
    assert details["camera_registered_observer_count"] == 1
    assert details["classifier_subscription_count"] == 0


def test_restore_passes_only_after_every_runtime_owner_is_cleared(tmp_path):
    stage = _file_stage(tmp_path)
    status_records = []
    audit = Phase5RuntimeAudit(
        stage,
        resource_sampler=lambda: {},
        log_status=lambda **record: status_records.append(record),
        log_warning=lambda **record: status_records.append(record),
    )
    _attach_runtime_layer(stage)
    stage.GetSessionLayer().subLayerPaths = []

    audit.finish(
        "RESTORED",
        _ownership(
            runtime_session_count=0,
            classifier_subscription_count=0,
            camera_subscription_count=0,
            camera_registered_observer_count=0,
            assignment_session_count=0,
            camera_target_count=0,
        ),
    )

    record = status_records[-1]
    assert record["state"] == "PASSED"
    assert record["details"]["source_integrity_passed"] is True
    assert record["details"]["runtime_ownership_cleared"] is True


def test_restore_fails_when_one_callback_owner_remains(tmp_path):
    stage = _file_stage(tmp_path)
    warning_records = []
    audit = Phase5RuntimeAudit(
        stage,
        resource_sampler=lambda: {},
        log_status=lambda **_record: None,
        log_warning=lambda **record: warning_records.append(record),
    )

    audit.finish(
        "RESTORED",
        _ownership(
            runtime_session_count=0,
            classifier_subscription_count=0,
            camera_registered_observer_count=0,
            assignment_session_count=0,
            camera_target_count=0,
        ),
    )

    assert warning_records[-1]["state"] == "FAILED"
    assert warning_records[-1]["details"]["runtime_ownership_cleared"] is False
