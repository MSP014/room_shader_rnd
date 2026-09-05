# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect source-material snapshots used for runtime visual diagnosis."""

from pathlib import Path

from msp.orms.shared_room.material_diagnostics import (
    capture_material_state,
    material_state_log_details,
)
from pxr import Usd

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BUILDING_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "building_150_runtime"
    / "test_room_map_building_150.usda"
)


def test_building_snapshot_records_source_material_network_and_bindings():
    stage = Usd.Stage.Open(str(BUILDING_FIXTURE))

    snapshot = capture_material_state(stage)
    details = material_state_log_details(snapshot, snapshot)

    assert len(snapshot["mesh_bindings"]) == 33
    assert snapshot["mesh_binding_counts"] == (
        ("/World/Building150/mtl/base_lod00_mat", 28),
        ("/World/Looks/RoomMapSource", 5),
    )
    assert "outputs:mtlx:surface" in details["source_material_outputs"]
    assert "ND_tiledimage_color3" in details["source_texture_inputs"]
    assert "texcoord=" in details["source_texture_inputs"]
    production_atlas = (
        REPOSITORY_ROOT
        / "assets"
        / "_external"
        / "tex"
        / "room_maps"
        / "room_map.1001.png"
    )
    expected_unresolved = (
        "<none>"
        if production_atlas.is_file()
        else "/World/Looks/RoomMapSource/Shader.room_atlas"
    )
    assert details["unresolved_texture_inputs"] == expected_unresolved
    assert details["source_usd_state_unchanged"] is True
    assert details["rendered_material_state_observable"] is False
