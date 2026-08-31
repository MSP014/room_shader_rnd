"""Protect USD notice filtering around runtime-owned and artist inputs."""

from pxr import Sdf, UsdGeom

from tools.omniverse.shared_room.changes import _is_relevant_change

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
