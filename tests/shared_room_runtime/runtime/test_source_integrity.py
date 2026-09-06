# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the Phase-5 source-stage integrity comparison."""

from pathlib import Path

from msp.orms.scene.source_integrity import (
    capture_stage_source_state,
    source_integrity_details,
)
from pxr import Sdf, Usd, UsdGeom, UsdShade


def _stage_with_instance(tmp_path: Path) -> tuple[Usd.Stage, Path]:
    asset_path = tmp_path / "building.usda"
    asset = Usd.Stage.CreateNew(str(asset_path))
    building = UsdGeom.Xform.Define(asset, "/Building").GetPrim()
    asset.SetDefaultPrim(building)
    material = UsdShade.Material.Define(asset, "/Building/Looks/Facade")
    mesh = UsdGeom.Mesh.Define(asset, "/Building/Windows_Glass")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    asset.GetRootLayer().Save()

    scene_path = tmp_path / "city.usda"
    scene = Usd.Stage.CreateNew(str(scene_path))
    UsdGeom.Xform.Define(scene, "/World")
    instance = UsdGeom.Xform.Define(scene, "/World/BuildingA").GetPrim()
    instance.GetReferences().AddReference(str(asset_path))
    instance.SetInstanceable(True)
    scene.GetRootLayer().Save()
    return Usd.Stage.Open(str(scene_path)), scene_path


def _temporary_runtime_layer(stage: Usd.Stage) -> Sdf.Layer:
    layer = Sdf.Layer.CreateAnonymous("orms_phase5_test.usda")
    stage.GetSessionLayer().subLayerPaths = [
        layer.identifier,
        *stage.GetSessionLayer().subLayerPaths,
    ]
    with Usd.EditContext(stage, layer):
        UsdShade.Material.Define(
            stage,
            "/__class__/Building/mtl/ORMSRoomMapSingle",
        )
    return layer


def test_restored_stage_matches_source_bytes_bindings_and_instance_prototypes(
    tmp_path,
):
    stage, _scene_path = _stage_with_instance(tmp_path)
    baseline = capture_stage_source_state(stage)
    session_sublayers = tuple(stage.GetSessionLayer().subLayerPaths)
    _temporary_runtime_layer(stage)

    stage.GetSessionLayer().subLayerPaths = list(session_sublayers)
    restored = capture_stage_source_state(stage)
    details = source_integrity_details(baseline, restored)

    assert any(
        path == "/World/BuildingA/Windows_Glass"
        for path, _material in baseline.material_state["mesh_bindings"]
    )
    assert details["source_integrity_passed"] is True
    assert details["source_file_count"] == 2
    assert details["same_stage_object"] is True
    assert details["material_bindings_restored"] is True
    assert details["instance_signature_unchanged"] is True
    assert details["usd_prototype_count_unchanged"] is True
    assert details["usd_prototype_structure_unchanged"] is True


def test_changed_source_file_bytes_fail_the_restore_audit(tmp_path):
    stage, scene_path = _stage_with_instance(tmp_path)
    baseline = capture_stage_source_state(stage)

    scene_path.write_text(
        scene_path.read_text(encoding="utf-8") + "\n# external mutation\n",
        encoding="utf-8",
    )
    details = source_integrity_details(
        baseline,
        capture_stage_source_state(stage),
    )

    assert details["source_file_bytes_unchanged"] is False
    assert details["source_integrity_passed"] is False


def test_reopened_stage_fails_same_object_identity_check(tmp_path):
    stage, scene_path = _stage_with_instance(tmp_path)
    baseline = capture_stage_source_state(stage)

    reopened = Usd.Stage.Open(str(scene_path))
    details = source_integrity_details(
        baseline,
        capture_stage_source_state(reopened),
    )

    assert details["same_stage_object"] is False
    assert details["same_root_layer"] is True
    assert details["source_integrity_passed"] is False


def test_deinstancing_is_reported_even_without_saving_the_source_layer(
    tmp_path,
):
    stage, _scene_path = _stage_with_instance(tmp_path)
    baseline = capture_stage_source_state(stage)

    stage.GetPrimAtPath("/World/BuildingA").SetInstanceable(False)
    details = source_integrity_details(
        baseline,
        capture_stage_source_state(stage),
    )

    assert details["instance_signature_unchanged"] is False
    assert details["source_layer_structure_unchanged"] is False
    assert details["source_integrity_passed"] is False


def test_new_sidecar_or_adapter_entry_fails_the_restore_audit(tmp_path):
    stage, _scene_path = _stage_with_instance(tmp_path)
    baseline = capture_stage_source_state(stage)

    (tmp_path / "city.orms.usda").write_text("#usda 1.0\n", encoding="utf-8")
    details = source_integrity_details(
        baseline,
        capture_stage_source_state(stage),
    )

    assert details["new_sidecar_or_adapter_entries"].endswith("city.orms.usda")
    assert details["source_integrity_passed"] is False
