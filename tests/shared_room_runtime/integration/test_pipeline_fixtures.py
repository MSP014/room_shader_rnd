"""Protect end-to-end classification on retained Omniverse and Houdini stages."""

import math
from collections import Counter
from pathlib import Path

import pytest
from pxr import Usd, UsdGeom, UsdShade

from tools.omniverse.shared_room.controller import (
    DERIVED_APERTURE_MASK_OFFSET_U,
    DERIVED_MAP_AXIS_U,
    DERIVED_MAP_ORIGIN,
    DERIVED_MAPPING_VALID,
    DERIVED_ROOM_AXIS_U,
    DERIVED_ROOM_DEPTH_SIZE,
    DERIVED_ROOM_GROUP_ID,
    DERIVED_ROOM_SIZE,
    DERIVED_SLICE_START_DEPTH,
    RuntimeClassifierSettings,
    RuntimeLayerOwner,
    classify_stage,
)

from ._fixture_support import (
    HOUDINI_EXPORT,
    HOUDINI_FIXTURE,
    HOUDINI_SOURCE,
    HOUDINI_WINDOWS,
    OMNIVERSE_CASES,
    OMNIVERSE_FIXTURE,
    REPOSITORY_ROOT,
    _classify,
    _family_material_sizes,
    _mesh_bounds,
    _physical_aperture_gaps,
    _scaled_depth_extent,
    _scaled_horizontal_extent,
)


def test_omniverse_fixture_uses_unique_debug_textures_and_coherent_layout():
    stage = Usd.Stage.Open(str(OMNIVERSE_FIXTURE), load=Usd.Stage.LoadAll)
    source_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Building/Looks/RoomMapSource/Shader")
    )

    source_asset = (
        source_shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Get()
    )
    source_sub_identifier = (
        source_shader.GetPrim()
        .GetAttribute("info:mdl:sourceAsset:subIdentifier")
        .Get()
    )
    assert source_asset.path.endswith("src/mdl/room_map_single.mdl")
    assert source_sub_identifier == "room_map_single"
    selected_textures = set()
    for (
        prim_name,
        atlas_sizes,
        _room_size,
        _room_depth_size,
        expected_room_id,
        expected_variant,
    ) in OMNIVERSE_CASES:
        prim = stage.GetPrimAtPath(f"/World/Building/{prim_name}")
        room_ids = UsdGeom.PrimvarsAPI(prim).GetPrimvar("roomID").Get()
        assert set(room_ids) == {expected_room_id}
        variant = (expected_room_id * 1664525) % 8
        assert variant == expected_variant
        for room_size in atlas_sizes:
            family = (
                "room_map_debug"
                if room_size == 1
                else f"room_map_debug_x{room_size}"
            )
            texture = (
                REPOSITORY_ROOT
                / "assets"
                / "_external"
                / "tex"
                / family
                / f"{family}.{1001 + variant}.png"
            )
            assert texture.is_file()
            selected_textures.add(texture)
    assert len(selected_textures) == sum(
        len(atlas_sizes)
        for _name, atlas_sizes, _size, _depth, _id, _variant in OMNIVERSE_CASES
    )

    bay_x3_bounds = _mesh_bounds(
        stage.GetPrimAtPath("/World/Building/RoomX3Bay30")
    )
    bay_x4_bounds = _mesh_bounds(
        stage.GetPrimAtPath("/World/Building/RoomX4Bay45")
    )
    arc_bounds = _mesh_bounds(
        stage.GetPrimAtPath("/World/Building/RoomX4Arc8")
    )
    assert arc_bounds[1][0] > max(bay_x3_bounds[1][1], bay_x4_bounds[1][1])
    lower_row_centre_z = (bay_x3_bounds[2][0] + bay_x4_bounds[2][1]) * 0.5
    arc_centre_z = sum(arc_bounds[2]) * 0.5
    assert arc_centre_z == pytest.approx(lower_row_centre_z, abs=0.25)


def test_omniverse_fixture_classifies_flat_corner_and_bay_rooms():
    stage = Usd.Stage.Open(str(OMNIVERSE_FIXTURE), load=Usd.Stage.LoadAll)
    root_before = stage.GetRootLayer().ExportToString()
    owner = RuntimeLayerOwner(stage)
    classification = classify_stage(
        stage,
        owner.attach(),
        RuntimeClassifierSettings(),
        REPOSITORY_ROOT,
    )

    assert stage.GetRootLayer().customLayerData["orms:fixtureOrigin"] == (
        "Omniverse-authored isolated geometry"
    )
    assert classification.metrics.up_axis == "Y"
    assert classification.metrics.meters_per_unit == 1.0
    assert len(classification.extraction.apertures) == 47
    assert not classification.extraction.diagnostics
    assert not classification.result.diagnostics
    assert Counter(
        group.room_size for group in classification.result.groups
    ) == (Counter({1: 2, 2: 4, 3: 4, 4: 4}))
    assert Counter(
        group.room_depth_size for group in classification.result.groups
    ) == Counter({1: 13, 2: 1})
    assert _family_material_sizes(stage) == {1, 2, 3, 4}

    for (
        prim_name,
        _atlas_sizes,
        room_size,
        room_depth_size,
        _room_id,
        _variant,
    ) in OMNIVERSE_CASES:
        mesh = UsdGeom.Mesh(
            stage.GetPrimAtPath(f"/World/Building/{prim_name}")
        )
        primvars = UsdGeom.PrimvarsAPI(mesh)
        assert set(primvars.GetPrimvar(DERIVED_ROOM_SIZE).Get()) == {room_size}
        assert set(primvars.GetPrimvar(DERIVED_ROOM_DEPTH_SIZE).Get()) == {
            room_depth_size
        }
        assert set(primvars.GetPrimvar(DERIVED_MAPPING_VALID).Get()) == {1}
        assert mesh.GetDoubleSidedAttr().HasAuthoredValueOpinion()
        assert mesh.GetDoubleSidedAttr().Get() is False
        assert mesh.GetOrientationAttr().HasAuthoredValueOpinion()
        assert mesh.GetOrientationAttr().Get() == UsdGeom.Tokens.leftHanded

    for prim_name in ("RoomX3Bay30", "RoomX4Bay45", "RoomX4Arc8"):
        prim = stage.GetPrimAtPath(f"/World/Building/{prim_name}")
        slice_start_depths = tuple(
            UsdGeom.PrimvarsAPI(prim)
            .GetPrimvar(DERIVED_SLICE_START_DEPTH)
            .Get()
        )
        expected_slice_start = max(0.0, -_scaled_depth_extent(prim)[0])
        assert expected_slice_start > 0.0
        assert slice_start_depths == pytest.approx(
            (expected_slice_start,) * len(slice_start_depths)
        )

    for prim_name in ("RoomX1", "RoomX2", "Corner2x2", "Corner4x1"):
        primvars = UsdGeom.PrimvarsAPI(
            stage.GetPrimAtPath(f"/World/Building/{prim_name}")
        )
        assert set(primvars.GetPrimvar(DERIVED_SLICE_START_DEPTH).Get()) == {
            0.0
        }

    corner_primvars = UsdGeom.PrimvarsAPI(
        stage.GetPrimAtPath("/World/Building/Corner2x2")
    )
    corner_axes = corner_primvars.GetPrimvar(DERIVED_ROOM_AXIS_U).Get()
    assert len(corner_axes) == 4
    assert {
        tuple(abs(round(component, 6)) for component in axis)
        for axis in corner_axes
    } == {(0.0, 0.0, 1.0)}
    corner_map_axes = corner_primvars.GetPrimvar(DERIVED_MAP_AXIS_U).Get()
    assert {
        tuple(abs(round(component, 6)) for component in axis)
        for axis in corner_map_axes
    } == {(0.8, 0.0, 0.0), (0.0, 0.0, 0.8)}
    assert _scaled_horizontal_extent(
        stage.GetPrimAtPath("/World/Building/Corner2x2")
    ) == pytest.approx((-1.0, 1.0))
    assert _scaled_depth_extent(
        stage.GetPrimAtPath("/World/Building/Corner2x2")
    ) == pytest.approx((-2.0, 0.0))

    corner_4x1 = UsdGeom.PrimvarsAPI(
        stage.GetPrimAtPath("/World/Building/Corner4x1")
    )
    assert tuple(corner_4x1.GetPrimvar(DERIVED_ROOM_SIZE).Get()) == (
        4,
        4,
        4,
        4,
        4,
    )
    assert tuple(corner_4x1.GetPrimvar(DERIVED_ROOM_DEPTH_SIZE).Get()) == (
        1,
        1,
        1,
        1,
        1,
    )
    assert (
        len(
            {
                tuple(round(component, 6) for component in axis)
                for axis in corner_4x1.GetPrimvar(DERIVED_ROOM_AXIS_U).Get()
            }
        )
        == 1
    )
    assert len(set(corner_4x1.GetPrimvar(DERIVED_ROOM_GROUP_ID).Get())) == 1
    assert _scaled_horizontal_extent(
        stage.GetPrimAtPath("/World/Building/Corner4x1")
    ) == pytest.approx((-2.0, 2.0))
    assert _scaled_depth_extent(
        stage.GetPrimAtPath("/World/Building/Corner4x1")
    ) == pytest.approx((-1.0, 0.0))

    corner_1x4 = UsdGeom.PrimvarsAPI(
        stage.GetPrimAtPath("/World/Building/Corner1x4")
    )
    corner_1x4_origins = corner_1x4.GetPrimvar(DERIVED_MAP_ORIGIN).Get()
    corner_1x4_axes = corner_1x4.GetPrimvar(DERIVED_MAP_AXIS_U).Get()
    corner_1x4_mask_offsets = corner_1x4.GetPrimvar(
        DERIVED_APERTURE_MASK_OFFSET_U
    ).Get()
    assert corner_1x4_origins[0][2] == pytest.approx(-1.0)
    assert corner_1x4_axes[0][2] == pytest.approx(0.8)
    assert (corner_1x4_origins[0][2] + corner_1x4_axes[0][2]) == pytest.approx(
        -0.2
    )
    assert tuple(corner_1x4_mask_offsets) == pytest.approx(
        (-0.1, 0.0, 0.0, 0.0, 0.0)
    )

    corner_4x1_origins = corner_4x1.GetPrimvar(DERIVED_MAP_ORIGIN).Get()
    corner_4x1_axes = corner_4x1.GetPrimvar(DERIVED_MAP_AXIS_U).Get()
    corner_4x1_mask_offsets = corner_4x1.GetPrimvar(
        DERIVED_APERTURE_MASK_OFFSET_U
    ).Get()
    assert corner_4x1_origins[4][2] == pytest.approx(-0.1)
    assert corner_4x1_axes[4][2] == pytest.approx(-0.8)
    assert (corner_4x1_origins[4][2] + corner_4x1_axes[4][2]) == pytest.approx(
        -0.9
    )
    assert tuple(corner_4x1_mask_offsets) == pytest.approx(
        (0.0, 0.0, 0.0, 0.0, 0.2)
    )
    corner_4x1_mesh = UsdGeom.Mesh(
        stage.GetPrimAtPath("/World/Building/Corner4x1")
    )
    bound_face_counts = {}
    for subset in UsdGeom.Subset.GetAllGeomSubsets(corner_4x1_mesh):
        material, relationship = UsdShade.MaterialBindingAPI(
            subset.GetPrim()
        ).ComputeBoundMaterial()
        assert relationship
        room_size = int(material.GetPath().name.removeprefix("RoomMapX"))
        bound_face_counts[room_size] = len(subset.GetIndicesAttr().Get())
    assert bound_face_counts == {1: 1, 4: 4}

    bay_x3_axes = (
        UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World/Building/RoomX3Bay30"))
        .GetPrimvar(DERIVED_ROOM_AXIS_U)
        .Get()
    )
    assert {
        tuple(abs(round(component, 6)) for component in axis)
        for axis in bay_x3_axes
    } == {(0.0, 0.0, 1.0)}
    bay_x3_map_axes = (
        UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World/Building/RoomX3Bay30"))
        .GetPrimvar(DERIVED_MAP_AXIS_U)
        .Get()
    )
    assert tuple(round(axis[2], 6) for axis in bay_x3_map_axes) == (
        0.4,
        0.0,
        -0.4,
    )
    bay_x3_prim = stage.GetPrimAtPath("/World/Building/RoomX3Bay30")
    assert _scaled_horizontal_extent(bay_x3_prim) == pytest.approx((-1.5, 1.5))
    assert _physical_aperture_gaps(bay_x3_prim) == pytest.approx(
        (0.2, 0.2), abs=1.0e-5
    )

    bay_x4_axes = (
        UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World/Building/RoomX4Bay45"))
        .GetPrimvar(DERIVED_ROOM_AXIS_U)
        .Get()
    )
    assert {
        tuple(abs(round(component, 6)) for component in axis)
        for axis in bay_x4_axes
    } == {(0.0, 0.0, 1.0)}
    bay_x4_prim = stage.GetPrimAtPath("/World/Building/RoomX4Bay45")
    assert _scaled_horizontal_extent(bay_x4_prim) == pytest.approx((-2.0, 2.0))
    assert _physical_aperture_gaps(bay_x4_prim) == pytest.approx(
        (0.2, 0.2, 0.2), abs=1.0e-5
    )

    arc_prim = stage.GetPrimAtPath("/World/Building/RoomX4Arc8")
    arc_depth_extent = _scaled_depth_extent(arc_prim)
    arc_slice_start_depth = (
        UsdGeom.PrimvarsAPI(arc_prim)
        .GetPrimvar(DERIVED_SLICE_START_DEPTH)
        .Get()[0]
    )
    assert arc_depth_extent[1] == pytest.approx(0.0)
    assert arc_depth_extent[0] == pytest.approx(-arc_slice_start_depth)
    arc_axis_u = (
        UsdGeom.PrimvarsAPI(arc_prim).GetPrimvar(DERIVED_ROOM_AXIS_U).Get()
    )
    assert {
        tuple(abs(round(component, 6)) for component in axis)
        for axis in arc_axis_u
    } == {(0.0, 0.0, 1.0)}
    source_axes = (
        UsdGeom.PrimvarsAPI(arc_prim).GetPrimvar("tangentu").Get()[::4]
    )
    arc_map_axes = (
        UsdGeom.PrimvarsAPI(arc_prim).GetPrimvar(DERIVED_MAP_AXIS_U).Get()
    )
    assert all(abs(axis[2]) > 0.05 for axis in arc_map_axes)
    assert _scaled_horizontal_extent(arc_prim) == pytest.approx((-2.0, 2.0))
    assert _physical_aperture_gaps(arc_prim) == pytest.approx(
        (0.2, 0.2, 0.2), abs=1.0e-5
    )
    for left, right in zip(source_axes, source_axes[1:]):
        cosine = sum(a * b for a, b in zip(left, right)) / (
            left.GetLength() * right.GetLength()
        )
        assert math.degrees(math.acos(cosine)) == pytest.approx(
            8.0, abs=1.0e-4
        )

    owner.detach()

    assert owner.layer.identifier not in stage.GetSessionLayer().subLayerPaths
    for prim_name, *_rest in OMNIVERSE_CASES:
        mesh = UsdGeom.Mesh(
            stage.GetPrimAtPath(f"/World/Building/{prim_name}")
        )
        assert not mesh.GetDoubleSidedAttr().HasAuthoredValueOpinion()
        assert not mesh.GetOrientationAttr().HasAuthoredValueOpinion()
    assert stage.GetRootLayer().ExportToString() == root_before


def test_houdini_fixture_preserves_export_and_classifies_all_families():
    stage = Usd.Stage.Open(str(HOUDINI_FIXTURE), load=Usd.Stage.LoadAll)
    root_before = stage.GetRootLayer().ExportToString()
    windows = UsdGeom.Mesh(stage.GetPrimAtPath(HOUDINI_WINDOWS))
    primvars = UsdGeom.PrimvarsAPI(windows)
    source_room_ids = tuple(primvars.GetPrimvar("roomID").Get())
    bound_material, binding_relationship = UsdShade.MaterialBindingAPI(
        windows
    ).ComputeBoundMaterial()
    owner = RuntimeLayerOwner(stage)
    classification = classify_stage(
        stage,
        owner.attach(),
        RuntimeClassifierSettings(),
        REPOSITORY_ROOT,
    )

    used_layer_names = {
        Path(layer.realPath).name
        for layer in stage.GetUsedLayers()
        if layer.realPath
    }
    assert stage.GetRootLayer().customLayerData["orms:fixtureOrigin"] == (
        "Omniverse capture layer over Houdini-exported test_bld component "
        "asset"
    )
    assert stage.GetRootLayer().customLayerData["orms:houdiniExport"] == (
        "assets/_external/usd/test_bld/test_bld.usd"
    )
    assert HOUDINI_SOURCE.is_file()
    assert HOUDINI_EXPORT.is_file()
    assert {
        "test_bld.usd",
        "payload.usdc",
        "geo.usdc",
        "mtl.usdc",
    }.issubset(used_layer_names)
    assert len(source_room_ids) == 140
    assert Counter(source_room_ids) >= Counter(
        {
            11: 3,
            12: 3,
            21: 4,
            22: 4,
            31: 9,
            41: 6,
            42: 6,
            221: 4,
            222: 4,
            331: 3,
            332: 3,
            441: 4,
        }
    )
    assert primvars.GetPrimvar("roomID").GetInterpolation() == "uniform"
    for name in ("roomP", "tangentu", "tangentv"):
        assert primvars.GetPrimvar(name).GetInterpolation() == "vertex"
    assert primvars.GetPrimvar("roomUV").GetInterpolation() == "faceVarying"
    assert binding_relationship
    assert bound_material.GetPath() == "/World/Looks/RoomMapSource"
    assert len(classification.extraction.apertures) == 140
    assert not classification.extraction.diagnostics
    assert not classification.result.diagnostics
    assert Counter(
        group.room_size for group in classification.result.groups
    ) == Counter({1: 95, 2: 4, 3: 4, 4: 3})
    assert Counter(primvars.GetPrimvar(DERIVED_ROOM_SIZE).Get()) == Counter(
        {1: 97, 2: 14, 3: 14, 4: 15}
    )
    slice_start_depths = tuple(
        primvars.GetPrimvar(DERIVED_SLICE_START_DEPTH).Get()
    )
    assert 0.0 in slice_start_depths
    assert max(slice_start_depths) > 0.5
    assert _family_material_sizes(stage) == {1, 2, 3, 4}

    owner.detach()

    assert not primvars.GetPrimvar(DERIVED_ROOM_SIZE)
    assert stage.GetRootLayer().ExportToString() == root_before


def test_disabled_atlas_families_repartition_fixture_without_source_edits():
    stage, owner, classification = _classify(
        HOUDINI_FIXTURE,
        RuntimeClassifierSettings(enabled_room_sizes=frozenset({1, 2})),
    )

    assert len(classification.result.mappings) == 140
    assert {group.room_size for group in classification.result.groups} <= {
        1,
        2,
    }
    assert _family_material_sizes(stage) == {1, 2}

    owner.detach()
