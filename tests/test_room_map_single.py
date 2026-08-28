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
    assert "camera_position_world - room_position" in source
    assert "state::texture_coordinate(0)" in source
    assert "tex::lookup_float4(" in source
    assert "-room_depth" in source
    assert "slice" not in source.lower()
