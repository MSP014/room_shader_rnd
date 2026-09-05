# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect host-memory and renderer contract snapshots independently."""

import sys
from types import SimpleNamespace

from msp.orms.scene.resource_metrics import (
    _renderer_snapshot,
    _windows_memory_snapshot,
)
from pxr import Sdf, Usd, UsdShade


def test_windows_memory_snapshot_reports_process_and_host_memory():
    snapshot = _windows_memory_snapshot()
    if sys.platform != "win32":
        assert snapshot == {"host_memory_metrics": "unsupported_platform"}
        return

    assert snapshot["process_working_set_gib"] > 0.0
    assert snapshot["process_private_commit_gib"] > 0.0
    assert snapshot["system_available_memory_gib"] > 0.0
    assert 0 <= snapshot["system_memory_load_percent"] <= 100


def test_renderer_snapshot_reports_path_tracing_cutout_opt_in():
    stage = Usd.Stage.CreateInMemory()
    UsdShade.Material.Define(stage, "/__ORMSRuntime/Looks/RoomMapX1")
    x2 = UsdShade.Material.Define(
        stage,
        "/__ORMSRuntime/Looks/RoomMapX2",
    )
    for material in (
        UsdShade.Material(
            stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX1")
        ),
        x2,
    ):
        material.GetPrim().CreateAttribute(
            "omni:rtx:enableCutoutOpacity",
            Sdf.ValueTypeNames.Bool,
            custom=False,
        ).Set(True)
        shader = UsdShade.Shader.Define(
            stage,
            material.GetPath().AppendChild("Shader"),
        )
        shader.CreateInput("enable_opacity", Sdf.ValueTypeNames.Bool).Set(True)

    values = {
        "/rtx/rendermode": "PathTracing",
        "/rtx/pathtracing/fractionalCutoutOpacity": True,
        "/rtx/material/omniRtxEnableOpacityOverride": True,
    }
    snapshot = _renderer_snapshot(
        settings=SimpleNamespace(get=values.get),
        stage=stage,
    )

    assert snapshot["renderer_mode"] == "PathTracing"
    assert snapshot["fractional_cutout_opacity"] is True
    assert snapshot["opacity_override"] is True
    assert snapshot["runtime_material_count"] == 2
    assert snapshot["cutout_contract_applicable_material_count"] == 2
    assert snapshot["cutout_opt_in_material_count"] == 2
    assert snapshot["cutout_opt_in_complete"] is True
    assert snapshot["mdl_enable_opacity_material_count"] == 2
    assert snapshot["mdl_enable_opacity_complete"] is True
    assert snapshot["mdl_enable_opacity_values"] == {
        "/__ORMSRuntime/Looks/RoomMapX1": True,
        "/__ORMSRuntime/Looks/RoomMapX2": True,
    }


def test_renderer_snapshot_treats_single_room_fallback_as_non_cutout():
    stage = Usd.Stage.CreateInMemory()
    material = UsdShade.Material.Define(
        stage,
        "/__ORMSRuntime/Looks/RoomMapX1",
    )
    UsdShade.Shader.Define(
        stage,
        material.GetPath().AppendChild("Shader"),
    )

    snapshot = _renderer_snapshot(
        settings=SimpleNamespace(get=lambda _path: None),
        stage=stage,
    )

    assert snapshot["runtime_material_count"] == 1
    assert snapshot["cutout_contract_applicable_material_count"] == 0
    assert snapshot["cutout_opt_in_complete"] is True
    assert snapshot["mdl_enable_opacity_complete"] is True
    assert snapshot["cutout_opt_in_values"] == {
        "/__ORMSRuntime/Looks/RoomMapX1": "not_applicable"
    }
    assert snapshot["mdl_enable_opacity_values"] == {
        "/__ORMSRuntime/Looks/RoomMapX1": "not_applicable"
    }


def test_renderer_snapshot_counts_per_interior_set_materials():
    stage = Usd.Stage.CreateInMemory()
    for set_token in ("Set_default", "Set_kitchens"):
        for room_size in (1, 2, 3, 4):
            material = UsdShade.Material.Define(
                stage,
                (f"/__ORMSRuntime/Looks/{set_token}/" f"RoomMapX{room_size}"),
            )
            UsdShade.Shader.Define(
                stage,
                material.GetPath().AppendChild("Shader"),
            )

    snapshot = _renderer_snapshot(
        settings=SimpleNamespace(get=lambda _path: None),
        stage=stage,
    )

    assert snapshot.get("runtime_material_count") == 8, snapshot
