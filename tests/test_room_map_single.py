"""Protect the single-window five-face analytic parallax baseline."""

from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = REPOSITORY_ROOT / "tests" / "test_room_map_single.usda"
MDL_PATH = REPOSITORY_ROOT / "src" / "mdl" / "room_map_single.mdl"

EXPECTED_FRAME_PRIMVARS = {
    "roomP": UsdGeom.Tokens.vertex,
    "tangentu": UsdGeom.Tokens.vertex,
    "tangentv": UsdGeom.Tokens.vertex,
}


def test_single_room_stage_defines_a_unit_window_and_room_frame():
    stage = Usd.Stage.Open(str(STAGE_PATH))
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/World/Window"))
    primvars_api = UsdGeom.PrimvarsAPI(mesh)

    assert mesh
    assert [tuple(point) for point in mesh.GetPointsAttr().Get()] == [
        (0.0, 0.0, -1.0),
        (0.0, 1.0, -1.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0),
    ]

    st = primvars_api.GetPrimvar("st")
    assert st.GetInterpolation() == UsdGeom.Tokens.faceVarying
    assert [tuple(value) for value in st.Get()] == [
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (0.0, 0.0),
    ]

    room_uv = primvars_api.GetPrimvar("roomUV")
    assert room_uv.GetInterpolation() == UsdGeom.Tokens.faceVarying
    assert [tuple(value) for value in room_uv.Get()] == [
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0),
    ]

    for name, interpolation in EXPECTED_FRAME_PRIMVARS.items():
        primvar = primvars_api.GetPrimvar(name)

        assert primvar.IsDefined()
        assert primvar.GetTypeName() == Sdf.ValueTypeNames.Float3Array
        assert primvar.GetInterpolation() == interpolation
        assert len(primvar.Get()) == 4


def test_single_room_stage_binds_the_mdl_material_and_debug_atlas():
    stage = Usd.Stage.Open(str(STAGE_PATH))
    mesh = stage.GetPrimAtPath("/World/Window")
    material, relationship = UsdShade.MaterialBindingAPI(
        mesh
    ).ComputeBoundMaterial()
    shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Looks/RoomMapSingle/Shader")
    )
    source_asset = shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Get()
    atlas_asset = shader.GetInput("room_atlas").Get()

    assert relationship
    assert material.GetPath() == "/World/Looks/RoomMapSingle"
    assert source_asset.path.endswith("src/mdl/room_map_single.mdl")
    assert (
        shader.GetPrim()
        .GetAttribute("info:mdl:sourceAsset:subIdentifier")
        .Get()
        == "room_map_single"
    )
    assert atlas_asset.path.endswith(
        "assets/_external/tex/room_map_debug/room_map_debug.1001.png"
    )
    assert tuple(shader.GetInput("camera_position_world").Get()) == (
        2.0,
        0.5,
        -0.5,
    )
    assert shader.GetInput("room_depth").Get() == 1.0


def test_single_room_module_uses_the_frame_camera_and_five_face_atlas_contract():
    source = MDL_PATH.read_text(encoding="utf-8")

    assert 'data_lookup_float3(\n        "roomP"' in source
    assert 'data_lookup_float3(\n        "tangentu"' in source
    assert 'data_lookup_float3(\n        "tangentv"' in source
    assert "state::coordinate_object" in source
    assert source.count("state::transform_vector(") == 2
    assert (
        'data_lookup_float3(\n            "ormsCameraPositionWorld"' in source
    )
    assert 'data_lookup_float3(\n        "roomUV"' in source
    assert 'data_lookup_int(\n        "roomID"' in source
    assert "uniform int room_variant_count = 1" in source
    assert "uniform int variation_seed = 0" in source
    assert "int variant_index = select_room_variant(" in source
    assert "udim_atlas_coordinate(atlas_coordinate, variant_index)" in source
    assert "float glass_roughness = 0.1" in source
    assert "float glass_reflectivity = 0.04" in source
    assert "color glass_tint = color(1.0)" in source
    assert "float glass_transmission = 1.0" in source
    assert "bool enable_emission = false" in source
    assert "float emission_threshold = 0.8" in source
    assert "float emission_softness = 0.1" in source
    assert "float room_emission_mask(" in source
    assert "float3(source_colour)" in source
    assert "math::smoothstep(" in source
    assert (
        "tinted_room_colour * safe_glass_transmission * luminous_room_mask"
        in source
    )
    assert "bsdf room_behind_glass = df::custom_curve_layer(" in source
    assert "normal_reflectivity: safe_glass_reflectivity" in source
    assert "scattering: room_behind_glass" in source
    assert "mode: df::scatter_reflect" in source
    assert "mode: df::scatter_reflect_transmit" not in source
    assert "bridged_camera_position_world - room_position" in source
    assert "float tangent_u_extent = math::length(tangent_u_raw);" in source
    assert "float tangent_v_extent = math::length(tangent_v_raw);" in source
    assert (
        "math::dot(camera_from_room, tangent_u) / safe_tangent_u_extent"
        in source
    )
    assert (
        "math::dot(camera_from_room, tangent_v) / safe_tangent_v_extent"
        in source
    )
    assert (
        "math::dot(surface_from_room, tangent_u) / safe_tangent_u_extent"
        in source
    )
    assert (
        "math::dot(surface_from_room, tangent_v) / safe_tangent_v_extent"
        in source
    )
    assert "state::direction()" not in source
    assert "state::texture_coordinate(0)" in source
    assert "tex::lookup_float4(" in source
    assert "-room_depth" in source
    assert "slice" not in source.lower()
