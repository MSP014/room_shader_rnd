"""Protect deterministic roomID variation in the isolated Omniverse fixture."""

from collections import Counter
from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = REPOSITORY_ROOT / "tests" / "test_room_map_variants.usda"
MDL_ROOT = REPOSITORY_ROOT / "exts" / "msp.orms.runtime" / "data" / "mdl"
MDL_PATH = MDL_ROOT / "room_map.mdl"
SINGLE_MDL_PATH = MDL_ROOT / "room_map_single.mdl"

ROOM_IDS = (0, 1, 2, 2, 0, 1)


def _stage_and_shader():
    stage = Usd.Stage.Open(str(STAGE_PATH))
    return stage, UsdShade.Shader(
        stage.GetPrimAtPath("/World/Looks/RoomMapVariants/Shader")
    )


def _variant_index(room_id, variation_seed, variant_count):
    safe_variant_count = max(variant_count, 1)
    mixed_id = room_id * 1664525 + variation_seed * 1013904223
    return mixed_id % safe_variant_count


def _udim_tile_offset(variant_index):
    safe_variant_index = max(variant_index, 0)
    return safe_variant_index % 10, safe_variant_index // 10


def test_variant_stage_has_disconnected_windows_with_repeated_room_ids():
    stage, _ = _stage_and_shader()
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/World/Windows"))
    room_id = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("roomID")

    assert mesh
    assert tuple(mesh.GetFaceVertexCountsAttr().Get()) == (4,) * 6
    assert len(mesh.GetPointsAttr().Get()) == 24
    assert room_id
    assert room_id.GetTypeName() == Sdf.ValueTypeNames.IntArray
    assert room_id.GetInterpolation() == UsdGeom.Tokens.uniform
    assert tuple(room_id.Get()) == ROOM_IDS
    assert Counter(room_id.Get()) == Counter({0: 2, 1: 2, 2: 2})


def test_variant_stage_preserves_room_frame_and_uv_contracts():
    stage, _ = _stage_and_shader()
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/World/Windows"))
    primvars = UsdGeom.PrimvarsAPI(mesh)

    for name in ("roomP", "tangentu", "tangentv"):
        primvar = primvars.GetPrimvar(name)
        assert primvar.GetTypeName() == Sdf.ValueTypeNames.Float3Array
        assert primvar.GetInterpolation() == UsdGeom.Tokens.vertex
        assert len(primvar.Get()) == 24

    st = primvars.GetPrimvar("st")
    assert st.GetTypeName() == Sdf.ValueTypeNames.TexCoord2fArray
    assert st.GetInterpolation() == UsdGeom.Tokens.faceVarying
    assert len(st.Get()) == 24


def test_variant_stage_binds_one_material_and_a_udim_atlas():
    stage, shader = _stage_and_shader()
    mesh = stage.GetPrimAtPath("/World/Windows")
    material, relationship = UsdShade.MaterialBindingAPI(
        mesh
    ).ComputeBoundMaterial()
    source_asset = shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Get()
    atlas_asset = shader.GetInput("room_atlas").Get()

    assert relationship
    assert material.GetPath() == "/World/Looks/RoomMapVariants"
    assert source_asset.path.endswith(
        "exts/msp.orms.runtime/data/mdl/room_map.mdl"
    )
    assert (
        shader.GetPrim()
        .GetAttribute("info:mdl:sourceAsset:subIdentifier")
        .Get()
        == "room_map"
    )
    assert atlas_asset.path.endswith(
        "exts/msp.orms.runtime/data/atlases/room_map_debug_x1/"
        "room_map_debug_x1.<UDIM>.png"
    )
    assert shader.GetInput("room_variant_count").Get() == 3
    assert shader.GetInput("variation_seed").Get() == 0


def test_variant_selection_is_deterministic_and_seedable():
    seed_zero = tuple(_variant_index(room_id, 0, 3) for room_id in ROOM_IDS)
    seed_one = tuple(_variant_index(room_id, 1, 3) for room_id in ROOM_IDS)

    assert seed_zero == (0, 2, 1, 1, 0, 2)
    assert seed_one == (1, 0, 2, 2, 1, 0)
    assert seed_zero[0] == seed_zero[4]
    assert seed_zero[1] == seed_zero[5]
    assert seed_zero[2] == seed_zero[3]
    assert seed_zero != seed_one
    assert _variant_index(42, 7, 0) == 0


def test_mdl_maps_variants_across_canonical_udim_rows():
    assert _udim_tile_offset(0) == (0, 0)
    assert _udim_tile_offset(9) == (9, 0)
    assert _udim_tile_offset(10) == (0, 1)
    assert _udim_tile_offset(55) == (5, 5)

    for mdl_path in (MDL_PATH, SINGLE_MDL_PATH):
        source = mdl_path.read_text(encoding="utf-8")
        assert "int tile_u = safe_variant_index % 10;" in source
        assert "int tile_v = safe_variant_index / 10;" in source
        assert (
            "atlas_coordinate + float2(float(tile_u), float(tile_v))" in source
        )


def test_mdl_uses_room_id_for_all_five_existing_atlas_lookups():
    source = MDL_PATH.read_text(encoding="utf-8")

    assert (
        'data_lookup_float3(\n            "ormsRoomMapPosition",\n'
        "            float3(0.0)\n        )"
    ) in source
    assert 'data_lookup_int(\n        "roomID",\n        0\n    )' in source
    assert "uniform int room_variant_count = 1" in source
    assert "uniform int variation_seed = 0" in source
    assert "int select_room_variant(" in source
    assert "room_id * 1664525 + variation_seed * 1013904223" in source
    assert "int safe_variant_count = room_variant_count > 0" in source
    assert source.count("tex::lookup_float4(") == 5
    assert source.count("udim_atlas_coordinate(") == 6
