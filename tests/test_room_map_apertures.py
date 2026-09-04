"""Validate physical aperture controls independently from virtual-room scale."""

from pathlib import Path

import pytest
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = REPOSITORY_ROOT / "tests" / "test_room_map_apertures.usda"
MDL_PATH = (
    REPOSITORY_ROOT
    / "exts"
    / "msp.orms.runtime"
    / "data"
    / "mdl"
    / "room_map.mdl"
)

WINDOW_DIMENSIONS = {
    "WindowSquareDefault": (1.0, 1.0),
    "WindowLandscapeDefault": (2.0, 1.0),
    "WindowPortraitDefault": (1.0, 2.0),
    "WindowScaleX": (1.0, 1.0),
    "WindowScaleY": (1.0, 1.0),
    "WindowOffset": (1.0, 1.0),
}

MATERIAL_INPUTS = {
    "RoomMapDefault": ((1.0, 1.0), (0.0, 0.0), 2.0),
    "RoomMapScaleX": ((1.0, 1.0), (0.0, 0.0), 2.0),
    "RoomMapScaleY": ((1.0, 1.0), (0.0, 0.0), 2.0),
    "RoomMapOffset": ((1.0, 1.0), (0.0, 0.0), 2.0),
}


def _aperture_corners(
    width,
    height,
    room_uniform_scale,
    scale=(1.0, 1.0),
    offset=(0.0, 0.0),
):
    extent = (width * max(scale[0], 1e-4), height * max(scale[1], 1e-4))
    room_extent = max(room_uniform_scale, 1e-4)

    return (
        (
            0.5 * room_extent - 0.5 * extent[0] + offset[0] * room_extent,
            0.5 * room_extent - 0.5 * extent[1] + offset[1] * room_extent,
        ),
        (
            0.5 * room_extent + 0.5 * extent[0] + offset[0] * room_extent,
            0.5 * room_extent + 0.5 * extent[1] + offset[1] * room_extent,
        ),
    )


def _stage():
    return Usd.Stage.Open(str(STAGE_PATH))


def test_aperture_stage_has_required_physical_window_proportions():
    stage = _stage()

    for mesh_name, expected_dimensions in WINDOW_DIMENSIONS.items():
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(f"/World/{mesh_name}"))
        primvars = UsdGeom.PrimvarsAPI(mesh)
        tangent_u = primvars.GetPrimvar("tangentu")
        tangent_v = primvars.GetPrimvar("tangentv")
        room_uv = primvars.GetPrimvar("roomUV")

        assert mesh
        assert tuple(mesh.GetFaceVertexCountsAttr().Get()) == (4,)
        assert tangent_u.GetTypeName() == Sdf.ValueTypeNames.Float3Array
        assert tangent_v.GetTypeName() == Sdf.ValueTypeNames.Float3Array
        assert tangent_u.GetInterpolation() == UsdGeom.Tokens.vertex
        assert tangent_v.GetInterpolation() == UsdGeom.Tokens.vertex
        assert room_uv.GetTypeName() == Sdf.ValueTypeNames.TexCoord3fArray
        assert room_uv.GetInterpolation() == UsdGeom.Tokens.faceVarying

        expected_width, expected_height = expected_dimensions
        for axis_u, axis_v in zip(
            tangent_u.Get(), tangent_v.Get(), strict=True
        ):
            assert axis_u.GetLength() == pytest.approx(expected_width)
            assert axis_v.GetLength() == pytest.approx(expected_height)
            assert Gf.Dot(axis_u, axis_v) == pytest.approx(0.0)

        actual_uv_corners = {
            (round(float(value[0]), 6), round(float(value[1]), 6))
            for value in room_uv.Get()
        }
        assert actual_uv_corners == {
            (0.0, 0.0),
            (0.0, 1.0),
            (1.0, 0.0),
            (1.0, 1.0),
        }


def test_aperture_stage_exposes_independent_scale_and_offset_controls():
    stage = _stage()

    for material_name, expected_inputs in MATERIAL_INPUTS.items():
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(f"/World/Looks/{material_name}/Shader")
        )
        expected_scale, expected_offset, expected_room_scale = expected_inputs

        assert tuple(shader.GetInput("window_aperture_scale").Get()) == (
            pytest.approx(expected_scale)
        )
        assert tuple(shader.GetInput("window_aperture_offset").Get()) == (
            pytest.approx(expected_offset)
        )
        assert tuple(shader.GetInput("window_shift").Get()) == pytest.approx(
            (0.0, 0.0)
        )
        assert shader.GetInput("room_uniform_scale").Get() == pytest.approx(
            expected_room_scale
        )


def test_aperture_module_keeps_virtual_room_aspect_independent_from_geometry():
    source = MDL_PATH.read_text(encoding="utf-8")

    assert "float2 window_aperture_scale = float2(1.0)" in source
    assert "float2 window_aperture_offset = float2(0.0)" in source
    assert "float room_uniform_scale = 1.0" in source
    assert "float safe_room_extent = positive_extent(" in source
    assert "positive_extent(room_uniform_scale)" in source
    assert "float3 shared_aperture_position(" in source
    assert '"ormsRoomMapPosition"' in source
    assert (
        "float3 scaled_position = physical_position * room_scale * room_extent"
        in source
    )
    assert "bool depth_aligned_portal = math::abs(portal_mode) > 1.5" in source
    assert (
        "float front_position_x = scaled_position.x * aperture_scale.x"
        in source
    )
    assert "float side_position_z =" in source
    assert (
        "(scaled_position.z + 0.5 * mapped_room_depth) * aperture_scale.x"
        in source
    )
    assert (
        "side_axis_direction * horizontal_control * mapped_room_depth"
        in source
    )
    assert "scaled_position.x + 0.5 * room_width" in source
    assert "float3 derived_room_scale" in source
    assert "ray_vector_room * safe_room_scale" in source
    assert "float3 shared_ray_origin = shared_aperture_position(" in source
    assert "float3 ray_origin = shared_ray_origin" in source
    assert "scaled_position.z" in source
    assert "surface_position_room - camera_position_room" in source
    assert "aperture_is_in_unit_room" not in source
    assert "saturate(\n            (window_coordinate.x" not in source
    assert "point_is_in_room_extent(" in source
    assert "physical_aperture_coordinate" not in source
    assert "float2 aperture_coordinate(" not in source
    assert "tex::lookup_float4(" in source
    assert source.count("tex::lookup_float4(") == 5


def test_default_aperture_uses_one_shared_room_extent():
    expected_corners = {
        (1.0, 1.0): ((0.5, 0.5), (1.5, 1.5)),
        (2.0, 1.0): ((0.0, 0.5), (2.0, 1.5)),
        (1.0, 2.0): ((0.5, 0.0), (1.5, 2.0)),
    }

    for dimensions, expected in expected_corners.items():
        actual = _aperture_corners(*dimensions, room_uniform_scale=2.0)
        assert actual[0] == pytest.approx(expected[0])
        assert actual[1] == pytest.approx(expected[1])

    offset_corners = _aperture_corners(
        1.0, 1.0, room_uniform_scale=2.0, offset=(0.2, -0.2)
    )
    assert offset_corners[0] == pytest.approx((0.9, 0.1))
    assert offset_corners[1] == pytest.approx((1.9, 1.1))

    scale_x_corners = _aperture_corners(
        1.0, 1.0, room_uniform_scale=2.0, scale=(0.5, 1.0)
    )
    assert scale_x_corners[0] == pytest.approx((0.75, 0.5))
    assert scale_x_corners[1] == pytest.approx((1.25, 1.5))

    scale_y_corners = _aperture_corners(
        1.0, 1.0, room_uniform_scale=2.0, scale=(1.0, 0.5)
    )
    assert scale_y_corners[0] == pytest.approx((0.5, 0.75))
    assert scale_y_corners[1] == pytest.approx((1.5, 1.25))
