from collections import Counter
from pathlib import Path

import pytest
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = REPOSITORY_ROOT / "tests" / "test_room_map_apertures_houdini.usda"
ASSET_DIRECTORY = (
    REPOSITORY_ROOT / "assets" / "_external" / "usd" / "test_grid_wins_diff"
)
HOUDINI_SOURCE_PATH = REPOSITORY_ROOT / "hip" / "room map test 005.hiplc"

WINDOWS_PATH = "/World/HoudiniGrid/geo/windows"
MATERIAL_PATH = "/World/Looks/RoomMapAperturesHoudini"
SHADER_PATH = f"{MATERIAL_PATH}/Shader"

EXPECTED_WINDOW_DIMENSIONS = (
    (0.8, 0.8),
    (0.8, 0.8),
    (0.8, 0.8),
    (0.8, 0.8),
    (0.8, 0.8),
    (0.44, 0.65),
    (0.44, 0.65),
    (0.44, 0.65),
    (0.44, 0.65),
    (0.44, 0.65),
    (0.72, 0.44),
    (0.72, 0.44),
    (0.72, 0.44),
    (0.72, 0.44),
    (0.72, 0.44),
)


def _stage_mesh_and_shader():
    stage = Usd.Stage.Open(str(STAGE_PATH), load=Usd.Stage.LoadAll)
    return (
        stage,
        UsdGeom.Mesh(stage.GetPrimAtPath(WINDOWS_PATH)),
        UsdShade.Shader(stage.GetPrimAtPath(SHADER_PATH)),
    )


def _face_point_indices(mesh):
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    cursor = 0

    for count in counts:
        yield indices[cursor : cursor + count]
        cursor += count


def test_capture_stage_resolves_the_houdini_component():
    stage, mesh, _ = _stage_mesh_and_shader()
    used_layer_names = {
        Path(layer.realPath).name
        for layer in stage.GetUsedLayers()
        if layer.realPath
    }

    assert mesh
    assert {
        "test_grid_wins_diff.usd",
        "payload.usdc",
        "geo.usdc",
        "mtl.usdc",
    }.issubset(used_layer_names)
    assert tuple(mesh.GetFaceVertexCountsAttr().Get()) == (4,) * 15
    assert len(mesh.GetPointsAttr().Get()) == 60
    assert HOUDINI_SOURCE_PATH.is_file()


def test_houdini_export_preserves_three_physical_window_dimensions():
    stage, mesh, _ = _stage_mesh_and_shader()
    primvars = UsdGeom.PrimvarsAPI(mesh)
    room_id = primvars.GetPrimvar("roomID")
    room_position = primvars.GetPrimvar("roomP")
    tangent_u = primvars.GetPrimvar("tangentu")
    tangent_v = primvars.GetPrimvar("tangentv")
    room_uv = primvars.GetPrimvar("roomUV")
    points = mesh.GetPointsAttr().Get()

    assert room_id.GetTypeName() == Sdf.ValueTypeNames.IntArray
    assert room_id.GetInterpolation() == UsdGeom.Tokens.uniform
    assert not room_id.IsIndexed()
    assert Counter(room_id.Get()) == Counter({0: 3, 1: 8, 2: 4})

    for primvar in (room_position, tangent_u, tangent_v):
        assert primvar.GetTypeName() == Sdf.ValueTypeNames.Float3Array
        assert primvar.GetInterpolation() == UsdGeom.Tokens.vertex
        assert not primvar.IsIndexed()
        assert len(primvar.Get()) == 60

    assert room_uv.GetTypeName() == Sdf.ValueTypeNames.TexCoord3fArray
    assert room_uv.GetInterpolation() == UsdGeom.Tokens.faceVarying
    assert not room_uv.IsIndexed()
    assert len(room_uv.Get()) == 60

    room_positions = room_position.Get()
    tangent_u_values = tangent_u.Get()
    tangent_v_values = tangent_v.Get()
    room_uv_values = room_uv.Get()
    cursor = 0

    for face_index, point_indices in enumerate(_face_point_indices(mesh)):
        expected_width, expected_height = EXPECTED_WINDOW_DIMENSIONS[
            face_index
        ]
        face_room_position = {
            tuple(room_positions[index]) for index in point_indices
        }

        assert len(face_room_position) == 1

        for point_index in point_indices:
            axis_u = tangent_u_values[point_index]
            axis_v = tangent_v_values[point_index]

            assert axis_u.GetLength() == pytest.approx(
                expected_width, abs=2e-4
            )
            assert axis_v.GetLength() == pytest.approx(
                expected_height, abs=2e-4
            )
            assert Gf.Dot(axis_u, axis_v) == pytest.approx(0.0, abs=2e-5)

        face_uv = room_uv_values[cursor : cursor + 4]
        actual_corners = {
            (round(float(value[0]), 4), round(float(value[1]), 4))
            for value in face_uv
        }
        assert actual_corners == {
            (0.0, 0.0),
            (0.0, 1.0),
            (1.0, 0.0),
            (1.0, 1.0),
        }

        for local_index, point_index in enumerate(point_indices):
            delta = points[point_index] - room_positions[point_index]
            expected_u = (
                Gf.Dot(delta, tangent_u_values[point_index])
                / Gf.Dot(
                    tangent_u_values[point_index],
                    tangent_u_values[point_index],
                )
                + 0.5
            )
            expected_v = (
                Gf.Dot(delta, tangent_v_values[point_index])
                / Gf.Dot(
                    tangent_v_values[point_index],
                    tangent_v_values[point_index],
                )
                + 0.5
            )
            assert tuple(face_uv[local_index][:2]) == pytest.approx(
                (expected_u, expected_v), abs=2e-4
            )

        cursor += 4

    assert stage


def test_capture_stage_overrides_only_exported_window_material():
    stage, mesh, shader = _stage_mesh_and_shader()
    material, relationship = UsdShade.MaterialBindingAPI(
        mesh
    ).ComputeBoundMaterial()
    source_asset = shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Get()
    atlas_asset = shader.GetInput("room_atlas").Get()

    assert relationship
    assert material.GetPath() == MATERIAL_PATH
    assert source_asset.path.endswith("src/mdl/room_map.mdl")
    assert (
        shader.GetPrim()
        .GetAttribute("info:mdl:sourceAsset:subIdentifier")
        .Get()
        == "room_map"
    )
    assert atlas_asset.path.endswith(
        "assets/_external/tex/room_map_debug/room_map_debug.<UDIM>.png"
    )
    assert shader.GetInput("room_variant_count").Get() == 3
    assert shader.GetInput("variation_seed").Get() == 0
    assert tuple(
        shader.GetInput("window_aperture_scale").Get()
    ) == pytest.approx((1.0, 0.8))
    assert tuple(
        shader.GetInput("window_aperture_offset").Get()
    ) == pytest.approx((0.0, 0.1))
    assert tuple(shader.GetInput("window_shift").Get()) == pytest.approx(
        (0.01, 0.0)
    )
    assert shader.GetInput("room_uniform_scale").Get() == pytest.approx(0.8)

    facade = stage.GetPrimAtPath("/World/HoudiniGrid/geo/test_grid")
    facade_material, facade_relationship = UsdShade.MaterialBindingAPI(
        facade
    ).ComputeBoundMaterial()
    assert facade_relationship
    assert facade_material.GetPath() == "/World/HoudiniGrid/mtl/test_mat"


def test_capture_stage_keeps_all_external_evidence_assets():
    for name in (
        "test_grid_wins_diff.usd",
        "payload.usdc",
        "geo.usdc",
        "mtl.usdc",
    ):
        assert (ASSET_DIRECTORY / name).is_file()
