import math
from collections import Counter
from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdLux, UsdShade

from tools.omniverse.shared_room_classifier import (
    DERIVED_APERTURE_MASK_OFFSET_U,
    DERIVED_MAP_AXIS_U,
    DERIVED_MAP_AXIS_V,
    DERIVED_MAP_ORIGIN,
    DERIVED_MAPPING_VALID,
    DERIVED_ROOM_AXIS_U,
    DERIVED_ROOM_DEPTH_SIZE,
    DERIVED_ROOM_GROUP_ID,
    DERIVED_ROOM_SCALE,
    DERIVED_ROOM_SIZE,
    DERIVED_SLICE_START_DEPTH,
    INSTANCE_POLICY_SESSION_DEINSTANCE,
    RuntimeClassifierSettings,
    RuntimeLayerOwner,
    classify_stage,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
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


@pytest.mark.parametrize(
    "fixture_path",
    (
        OMNIVERSE_FIXTURE,
        HOUDINI_FIXTURE,
        HOUDINI_INSTANCE_FIXTURE,
        INSTANCE_FIXTURE,
    ),
)
def test_visual_fixtures_use_the_room_map_hdri_environment(fixture_path):
    stage = Usd.Stage.Open(str(fixture_path), load=Usd.Stage.LoadAll)
    dome = UsdLux.DomeLight(stage.GetPrimAtPath("/World/RoomMapEnvironment"))

    assert dome
    assert dome.GetTextureFileAttr().Get().path == HDRI_ASSET_PATH
    assert dome.GetTextureFormatAttr().Get() == "latlong"
    assert dome.GetExposureAttr().Get() == 0.0
    assert dome.GetIntensityAttr().Get() == 1000.0
    dome_prim = dome.GetPrim()
    assert dome_prim.GetAttribute("xformOp:rotateX").Get() == -90.0
    assert dome_prim.GetAttribute("xformOpOrder").Get() == ["xformOp:rotateX"]
    assert HDRI_PATH.is_file()


@pytest.mark.parametrize(
    ("fixture_path", "shader_path"),
    (
        (
            OMNIVERSE_FIXTURE,
            "/World/Building/Looks/RoomMapSource/Shader",
        ),
        (HOUDINI_FIXTURE, "/World/Looks/RoomMapSource/Shader"),
        (
            HOUDINI_INSTANCE_SOURCE,
            "/HoudiniBuilding/Looks/RoomMapSource/Shader",
        ),
    ),
)
def test_source_x1_materials_enable_all_debug_variants(
    fixture_path,
    shader_path,
):
    stage = Usd.Stage.Open(str(fixture_path), load=Usd.Stage.LoadAll)
    shader = UsdShade.Shader(stage.GetPrimAtPath(shader_path))

    assert shader
    assert shader.GetInput("room_variant_count").Get() == 8
    assert shader.GetInput("variation_seed").Get() == 0
    assert (
        shader.GetInput("room_atlas")
        .Get()
        .path.endswith("room_map_debug/room_map_debug.<UDIM>.png")
    )


@pytest.mark.parametrize(
    "fixture_path",
    (HOUDINI_INSTANCE_FIXTURE, INSTANCE_FIXTURE),
)
def test_instance_fixtures_predeclare_camera_primvar_before_runtime(
    fixture_path,
):
    stage = Usd.Stage.Open(str(fixture_path), load=Usd.Stage.LoadAll)
    primvar = UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World")).GetPrimvar(
        "ormsCameraPositionWorld"
    )

    assert primvar
    assert primvar.GetTypeName() == Sdf.ValueTypeNames.Float3
    assert primvar.GetInterpolation() == UsdGeom.Tokens.constant
    assert tuple(primvar.Get()) == (8.0, 3.0, 5.0)

    instance_roots = tuple(
        child
        for child in stage.GetPrimAtPath("/World").GetChildren()
        if child.IsInstance()
    )
    assert len(instance_roots) == 2
    inherited_primvars = tuple(
        UsdGeom.PrimvarsAPI(proxy).FindPrimvarWithInheritance(
            "ormsCameraPositionWorld"
        )
        for instance in instance_roots
        for proxy in Usd.PrimRange(instance, Usd.TraverseInstanceProxies())
        if proxy.IsA(UsdGeom.Mesh)
        and UsdGeom.PrimvarsAPI(proxy).GetPrimvar("roomUV")
    )
    assert inherited_primvars
    assert all(inherited_primvars)
    assert {tuple(inherited.Get()) for inherited in inherited_primvars} == {
        (8.0, 3.0, 5.0)
    }


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


def test_houdini_export_tangent_lengths_encode_aperture_extents():
    stage = Usd.Stage.Open(str(HOUDINI_EXPORT), load=Usd.Stage.LoadAll)
    windows = UsdGeom.Mesh(stage.GetPrimAtPath("/test_bld/geo/windows"))
    primvars = UsdGeom.PrimvarsAPI(windows)
    points = windows.GetPointsAttr().Get()
    face_counts = windows.GetFaceVertexCountsAttr().Get()
    face_indices = windows.GetFaceVertexIndicesAttr().Get()
    room_positions = primvars.GetPrimvar("roomP").ComputeFlattened()
    tangents_u = primvars.GetPrimvar("tangentu").ComputeFlattened()
    tangents_v = primvars.GetPrimvar("tangentv").ComputeFlattened()
    face_offset = 0

    for face_count in face_counts:
        point_indices = face_indices[face_offset : face_offset + face_count]
        vertex_index = point_indices[0]
        room_position = room_positions[vertex_index]
        tangent_u = tangents_u[vertex_index]
        tangent_v = tangents_v[vertex_index]
        axis_u = tangent_u.GetNormalized()
        axis_v = tangent_v.GetNormalized()
        offsets = [points[index] - room_position for index in point_indices]
        aperture_width = max(offset * axis_u for offset in offsets) - min(
            offset * axis_u for offset in offsets
        )
        aperture_height = max(offset * axis_v for offset in offsets) - min(
            offset * axis_v for offset in offsets
        )

        assert tangent_u.GetLength() == pytest.approx(aperture_width)
        assert tangent_v.GetLength() == pytest.approx(aperture_height)
        face_offset += face_count


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


@pytest.mark.parametrize(
    ("fixture_path", "instance_names", "aperture_count", "group_sizes"),
    (
        (
            INSTANCE_FIXTURE,
            {"BuildingA", "BuildingB"},
            94,
            Counter({1: 4, 2: 8, 3: 8, 4: 8}),
        ),
        (
            HOUDINI_INSTANCE_FIXTURE,
            {"HoudiniBuildingA", "HoudiniBuildingB"},
            280,
            Counter({1: 190, 2: 8, 3: 8, 4: 6}),
        ),
    ),
)
def test_real_instance_fixtures_support_both_runtime_policies(
    fixture_path,
    instance_names,
    aperture_count,
    group_sizes,
):
    preserve_stage, preserve_owner, preserve = _classify(fixture_path)

    instances = tuple(
        child
        for child in preserve_stage.GetPrimAtPath("/World").GetChildren()
        if child.GetName() in instance_names
    )
    assert len(instances) == 2
    assert all(prim.IsInstance() for prim in instances)
    assert not preserve.extraction.apertures
    assert Counter(
        diagnostic.state for diagnostic in preserve.extraction.diagnostics
    ) == Counter({"INSTANCE_PRESERVED_X1_FALLBACK": 2})
    for diagnostic in preserve.extraction.diagnostics:
        details = dict(diagnostic.details)
        assert details["source_x1_proxy_count"] > 0
        assert (
            details["room_uv_varying_proxy_count"]
            == details["source_x1_proxy_count"]
        )
        assert (
            details["camera_primvar_inherited_proxy_count"]
            == details["source_x1_proxy_count"]
        )
    assert _family_material_sizes(preserve_stage) == set()
    assert (
        tuple(
            str(prim.GetAttribute("inputs:camera_position_world").GetPath())
            for prim in preserve_stage.Traverse()
            if prim.GetAttribute("inputs:camera_position_world")
        )
        == ()
    )
    for instance in instances:
        meshes = tuple(
            prim
            for prim in Usd.PrimRange(
                instance,
                Usd.TraverseInstanceProxies(),
            )
            if prim.IsA(UsdGeom.Mesh)
        )
        assert meshes
        eligible_meshes = tuple(
            mesh
            for mesh in meshes
            if all(
                UsdGeom.PrimvarsAPI(mesh).GetPrimvar(name)
                for name in (
                    "roomID",
                    "roomP",
                    "tangentu",
                    "tangentv",
                    "roomUV",
                )
            )
            and str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            ).endswith("/Looks/RoomMapSource")
        )
        preserved_meshes = tuple(
            mesh for mesh in meshes if mesh not in eligible_meshes
        )
        assert eligible_meshes
        assert {
            str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            )
            for mesh in eligible_meshes
        } == {f"{instance.GetPath()}/Looks/RoomMapSource"}
        assert all(
            str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            )
            != f"{instance.GetPath()}/Looks/RoomMapSource"
            for mesh in preserved_meshes
        )
        assert not instance.GetRelationship(
            "material:binding:collection:ormsRoomMapWindows"
        )
        if fixture_path == HOUDINI_INSTANCE_FIXTURE:
            assert preserved_meshes
            assert any(
                str(
                    UsdShade.MaterialBindingAPI(mesh)
                    .ComputeBoundMaterial()[0]
                    .GetPath()
                ).endswith("/mtl/test_mat")
                for mesh in preserved_meshes
            )

    preserve_owner.detach()

    assert not any(
        prim.GetRelationship("material:binding:collection:ormsRoomMapWindows")
        for prim in instances
    )

    deinstance_stage, deinstance_owner, deinstance = _classify(
        fixture_path,
        RuntimeClassifierSettings(
            instance_policy=INSTANCE_POLICY_SESSION_DEINSTANCE
        ),
    )
    deinstanced = tuple(
        child
        for child in deinstance_stage.GetPrimAtPath("/World").GetChildren()
        if child.GetName() in instance_names
    )
    assert not any(prim.IsInstance() for prim in deinstanced)
    assert len(deinstance.extraction.apertures) == aperture_count
    assert (
        Counter(group.room_size for group in deinstance.result.groups)
        == group_sizes
    )

    deinstance_owner.detach()

    assert all(prim.IsInstance() for prim in deinstanced)


def test_houdini_instance_fixture_uses_the_exported_component_layers():
    stage = Usd.Stage.Open(
        str(HOUDINI_INSTANCE_FIXTURE),
        load=Usd.Stage.LoadAll,
    )

    used_layer_names = {
        Path(layer.realPath).name
        for layer in stage.GetUsedLayers()
        if layer.realPath
    }
    assert stage.GetRootLayer().customLayerData["orms:fixtureOrigin"] == (
        "Referenced and instanceable Houdini-exported geometry"
    )
    assert {
        HOUDINI_INSTANCE_SOURCE.name,
        "test_bld.usd",
        "payload.usdc",
        "geo.usdc",
        "mtl.usdc",
    }.issubset(used_layer_names)
