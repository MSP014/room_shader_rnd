# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Share retained fixture paths and geometric inspection helpers."""

from pathlib import Path

from msp.orms.shared_room.controller import (
    DERIVED_MAP_AXIS_U,
    DERIVED_MAP_AXIS_V,
    DERIVED_MAP_ORIGIN,
    DERIVED_ROOM_SCALE,
    RuntimeClassifierSettings,
    RuntimeLayerOwner,
    classify_stage,
)
from pxr import Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OMNIVERSE_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "shared_room_runtime"
    / "test_room_map_shared_rooms_omniverse.usda"
)
HOUDINI_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "shared_room_runtime"
    / "test_room_map_shared_rooms_houdini.usda"
)
HOUDINI_INSTANCE_SOURCE = (
    REPOSITORY_ROOT
    / "tests"
    / "shared_room_runtime"
    / "test_room_map_shared_rooms_houdini_instance_source.usda"
)
HOUDINI_INSTANCE_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "shared_room_runtime"
    / "test_room_map_shared_rooms_houdini_instances.usda"
)
INSTANCE_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "shared_room_runtime"
    / "test_room_map_shared_rooms_instances.usda"
)
HOUDINI_SOURCE = REPOSITORY_ROOT / "hip" / "room map test 005.hiplc"
HOUDINI_EXPORT = (
    REPOSITORY_ROOT
    / "assets"
    / "_external"
    / "usd"
    / "test_bld"
    / "test_bld.usd"
)
HOUDINI_WINDOWS = "/World/HoudiniBuilding/geo/windows"
HDRI_PATH = (
    REPOSITORY_ROOT
    / "assets"
    / "_external"
    / "hdri"
    / "kloofendal_48d_partly_cloudy_puresky_4k.exr"
)
HDRI_ASSET_PATH = (
    "../../assets/_external/hdri/"
    "kloofendal_48d_partly_cloudy_puresky_4k.exr"
)

OMNIVERSE_CASES = (
    ("RoomX1", (1,), 1, 1, 800, 0),
    ("RoomX2", (2,), 2, 1, 805, 1),
    ("RoomX3DifferentWidths", (3,), 3, 1, 802, 2),
    ("Corner2x2", (2,), 2, 2, 807, 3),
    ("RoomX3Bay30", (3,), 3, 1, 804, 4),
    ("RoomX4Bay45", (4,), 4, 1, 801, 5),
    ("RoomX4Arc8", (4,), 4, 1, 806, 6),
    ("Corner1x1", (1,), 1, 1, 813, 1),
    ("Corner1x2", (1, 2), 2, 1, 818, 2),
    ("Corner2x1", (1, 2), 2, 1, 822, 6),
    ("Corner1x3", (1, 3), 3, 1, 823, 3),
    ("Corner3x1", (1, 3), 3, 1, 825, 5),
    ("Corner1x4", (1, 4), 4, 1, 835, 7),
    ("Corner4x1", (1, 4), 4, 1, 836, 4),
)


def _classify(path, settings=RuntimeClassifierSettings()):
    stage = Usd.Stage.Open(str(path), load=Usd.Stage.LoadAll)
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()
    classification = classify_stage(
        stage,
        runtime_layer,
        settings,
        REPOSITORY_ROOT,
    )
    return stage, owner, classification


def _family_material_sizes(stage):
    looks = stage.GetPrimAtPath("/__ORMSRuntime/Looks")
    if not looks:
        return set()
    return {
        int(prim.GetName().removeprefix("RoomMapX"))
        for prim in looks.GetChildren()
        if prim.IsA(UsdShade.Material)
    }


def _scaled_horizontal_extent(prim):
    primvars = UsdGeom.PrimvarsAPI(prim)
    origins = primvars.GetPrimvar(DERIVED_MAP_ORIGIN).Get()
    axes_u = primvars.GetPrimvar(DERIVED_MAP_AXIS_U).Get()
    axes_v = primvars.GetPrimvar(DERIVED_MAP_AXIS_V).Get()
    scales = primvars.GetPrimvar(DERIVED_ROOM_SCALE).Get()
    positions = []
    for origin, axis_u, axis_v, scale in zip(origins, axes_u, axes_v, scales):
        for u in (0.0, 1.0):
            for v in (0.0, 1.0):
                positions.append(
                    (origin[0] + axis_u[0] * u + axis_v[0] * v) * scale[0]
                )
    return min(positions), max(positions)


def _scaled_depth_extent(prim):
    primvars = UsdGeom.PrimvarsAPI(prim)
    origins = primvars.GetPrimvar(DERIVED_MAP_ORIGIN).Get()
    axes_u = primvars.GetPrimvar(DERIVED_MAP_AXIS_U).Get()
    axes_v = primvars.GetPrimvar(DERIVED_MAP_AXIS_V).Get()
    scales = primvars.GetPrimvar(DERIVED_ROOM_SCALE).Get()
    positions = []
    for origin, axis_u, axis_v, scale in zip(origins, axes_u, axes_v, scales):
        for u in (0.0, 1.0):
            for v in (0.0, 1.0):
                positions.append(
                    (origin[2] + axis_u[2] * u + axis_v[2] * v) * scale[2]
                )
    return min(positions), max(positions)


def _physical_aperture_gaps(prim):
    primvars = UsdGeom.PrimvarsAPI(prim)
    centres = primvars.GetPrimvar("roomP").Get()[::4]
    axes_u = primvars.GetPrimvar("tangentu").Get()[::4]
    gaps = []
    for index in range(len(centres) - 1):
        left_end = centres[index] + axes_u[index] * 0.5
        right_start = centres[index + 1] - axes_u[index + 1] * 0.5
        gaps.append((right_start - left_end).GetLength())
    return tuple(gaps)


def _mesh_bounds(prim):
    points = UsdGeom.Mesh(prim).GetPointsAttr().Get()
    return tuple(
        (
            min(point[axis] for point in points),
            max(point[axis] for point in points),
        )
        for axis in range(3)
    )
