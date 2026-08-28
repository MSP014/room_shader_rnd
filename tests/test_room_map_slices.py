from pathlib import Path

from pxr import Usd, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = REPOSITORY_ROOT / "tests" / "test_room_map_slices.usda"
MDL_PATH = REPOSITORY_ROOT / "src" / "mdl" / "room_map.mdl"

SLICE_DEPTHS = (20.0, 40.0, 60.0, 80.0)


def _shader():
    stage = Usd.Stage.Open(str(STAGE_PATH))
    return stage, UsdShade.Shader(
        stage.GetPrimAtPath("/World/Looks/RoomMap/Shader")
    )


def test_depth_slice_stage_binds_the_public_material_and_green_atlas():
    stage, shader = _shader()
    mesh = stage.GetPrimAtPath("/World/Window")
    material, relationship = UsdShade.MaterialBindingAPI(
        mesh
    ).ComputeBoundMaterial()
    source_asset = shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Get()
    atlas_asset = shader.GetInput("room_atlas").Get()

    assert relationship
    assert material.GetPath() == "/World/Looks/RoomMap"
    assert source_asset.path.endswith("src/mdl/room_map.mdl")
    assert (
        shader.GetPrim()
        .GetAttribute("info:mdl:sourceAsset:subIdentifier")
        .Get()
        == "room_map"
    )
    assert atlas_asset.path.endswith(
        "assets/_external/tex/room_map_debug/room_map_debug.1002.png"
    )


def test_depth_slice_stage_exposes_ordered_artist_controls():
    _, shader = _shader()

    assert shader.GetInput("room_depth").Get() == 1.0
    assert tuple(shader.GetInput("window_shift").Get()) == (0.0, 0.0)

    depths = []
    for index, expected_depth in enumerate(SLICE_DEPTHS, start=1):
        assert shader.GetInput(f"enable_slice_{index}").Get() is True
        assert tuple(shader.GetInput(f"slice_{index}_offset").Get()) == (
            0.0,
            0.0,
        )
        assert tuple(shader.GetInput(f"slice_{index}_scale").Get()) == (
            1.0,
            1.0,
        )

        depth = shader.GetInput(f"slice_{index}_depth_percent").Get()
        assert depth == expected_depth
        depths.append(depth)

    assert depths == sorted(depths)


def test_depth_slice_module_defines_cross_atlas_sampling_and_depth_ordering():
    source = MDL_PATH.read_text(encoding="utf-8")

    assert "export material room_map(" in source
    assert "float2 window_shift" in source
    assert "color fallback_colour" in source
    assert "slice_1_depth_percent = 20.0" in source
    assert "slice_4_depth_percent = 80.0" in source
    assert source.count("tex::lookup_float4(") == 5
    assert "float2(0.0, 0.0)" in source
    assert "float2(0.0, 2.0 / 3.0)" in source
    assert "float2(2.0 / 3.0, 2.0 / 3.0)" in source
    assert "float2(2.0 / 3.0, 0.0)" in source
    assert "transmittance_from_nearer_slice" in source
    assert "slice_2_depth <= slice_1_depth" in source
    assert "slice_4_depth <= slice_3_depth" in source
    assert "ray marching" not in source.lower()
