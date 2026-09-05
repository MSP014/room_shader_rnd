# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect USD notice filtering around runtime-owned and artist inputs."""

from msp.orms.shared_room.changes import _is_relevant_change
from pxr import Sdf, UsdGeom

from ._support import _window_stage


def test_change_filter_excludes_camera_runtime_and_artist_inputs():
    stage, _mesh = _window_stage((1,))
    UsdGeom.Camera.Define(stage, "/World/Camera")
    geometry_ancestors = frozenset(
        {
            "/World",
            "/World/Building",
            "/World/Building/Windows",
        }
    )
    building_roots = frozenset({"/World/Building"})

    for path in (
        "/World/Camera.xformOp:transform",
        "/World/Building/Looks/RoomMap/Shader.inputs:camera_position_world",
        "/World/Building/Looks/RoomMap/Shader.inputs:window_aperture_scale",
        "/World.primvars:ormsCameraPositionWorld",
        "/__ORMSRuntime/Looks/RoomMapX2/Shader.inputs:room_atlas",
        "/__ORMSRuntime/Looks/RoomMapX2/Shader.outputs:out",
    ):
        assert not _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
            building_roots,
        )

    for path in (
        "/World/Building/Windows.xformOp:translate",
        "/World/Building/Windows.points",
        "/World/Building/Windows.primvars:roomID",
        "/World/Building/Windows.material:binding",
    ):
        assert _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
            building_roots,
        )

    assert _is_relevant_change(
        stage,
        Sdf.Path("/World/Building.xformOp:scale"),
        geometry_ancestors,
        building_roots,
        frozenset({"/World/Building"}),
    )

    for path in (
        "/World/Building.xformOp:translate",
        "/World/Building.xformOp:rotateXYZ",
        "/World/Building.xformOp:orient",
        "/World/Building.xformOp:scale",
    ):
        assert not _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
            building_roots,
        )

    assert not _is_relevant_change(
        stage,
        Sdf.Path("/World/Building/Windows.primvars:ormsRoomSize"),
        geometry_ancestors,
    )
    assert _is_relevant_change(
        stage,
        Sdf.Path("/World/Building"),
        geometry_ancestors,
        resynced=True,
    )
    assert not _is_relevant_change(
        stage,
        Sdf.Path("/World/Building"),
        geometry_ancestors,
        resynced=False,
    )


def test_change_filter_excludes_unrelated_renderer_resyncs():
    stage, _mesh = _window_stage((1,))
    geometry_ancestors = frozenset(
        {
            "/World",
            "/World/Building",
            "/World/Building/Windows",
        }
    )
    building_roots = frozenset({"/World/Building"})

    for path in (
        "/OmniKit_Viewport_LightRig",
        "/Render",
        "/Render/OmniverseKit",
        "/Render/OmniverseKit/HydraTextures",
        (
            "/Render/OmniverseKit/HydraTextures/"
            "omni_kit_widget_viewport_ViewportTexture_0"
        ),
    ):
        assert not _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
            building_roots,
            resynced=True,
        )

    for path in (
        "/Render/Proxy.points",
        "/Render/Proxy.primvars:roomID",
        "/Render/Proxy.material:binding",
        "/Render/Shader.info:mdl:sourceAsset",
    ):
        assert not _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
            building_roots,
            resynced=False,
        )


def test_change_filter_retains_geometry_and_material_dependencies():
    stage, _mesh = _window_stage((1,))
    geometry_ancestors = frozenset(
        {
            "/World",
            "/World/Building",
            "/World/Building/Windows",
        }
    )
    building_roots = frozenset({"/World/Building"})
    material_ancestors = frozenset(
        {
            "/ExternalLooks",
            "/ExternalLooks/RoomMap",
        }
    )
    material_roots = frozenset({"/ExternalLooks/RoomMap"})

    for path in (
        "/World/Building/NewWindows",
        "/ExternalLooks",
        "/ExternalLooks/RoomMap/Shader",
    ):
        assert _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
            building_roots,
            source_material_ancestor_paths=material_ancestors,
            source_material_root_paths=material_roots,
            resynced=True,
        )
