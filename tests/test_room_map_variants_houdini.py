from collections import Counter, defaultdict
from pathlib import Path

import pytest
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = REPOSITORY_ROOT / "tests" / "test_room_map_variants_houdini.usda"
ASSET_DIRECTORY = (
    REPOSITORY_ROOT / "assets" / "_external" / "usd" / "test_grid_wins"
)
HOUDINI_SOURCE_PATH = REPOSITORY_ROOT / "hip" / "room map test 004.hiplc"

WINDOWS_PATH = "/World/HoudiniGrid/geo/windows"
MATERIAL_PATH = "/World/Looks/RoomMapHoudini"
SHADER_PATH = f"{MATERIAL_PATH}/Shader"


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


def test_capture_stage_resolves_the_complete_houdini_component():
    stage, mesh, _ = _stage_mesh_and_shader()
    used_layer_names = {
        Path(layer.realPath).name
        for layer in stage.GetUsedLayers()
        if layer.realPath
    }

    assert mesh
    assert {
        "test_grid_wins.usd",
        "payload.usdc",
        "geo.usdc",
        "mtl.usdc",
    }.issubset(used_layer_names)
    assert tuple(mesh.GetFaceVertexCountsAttr().Get()) == (4,) * 15
    assert len(mesh.GetPointsAttr().Get()) == 60
    assert HOUDINI_SOURCE_PATH.is_file()


def test_houdini_export_preserves_room_ids_and_per_window_frames():
    stage, mesh, _ = _stage_mesh_and_shader()
    primvars = UsdGeom.PrimvarsAPI(mesh)
    room_id = primvars.GetPrimvar("roomID")
    room_ids = tuple(room_id.Get())

    assert room_id.GetTypeName() == Sdf.ValueTypeNames.IntArray
    assert room_id.GetInterpolation() == UsdGeom.Tokens.uniform
    assert not room_id.IsIndexed()
    assert len(room_ids) == 15
    assert set(room_ids) == {0, 1, 2}
    assert all(count > 1 for count in Counter(room_ids).values())

    face_centres_by_room = defaultdict(set)
    face_indices = tuple(_face_point_indices(mesh))

    for name in ("roomP", "tangentu", "tangentv"):
        primvar = primvars.GetPrimvar(name)
        assert primvar.GetTypeName() == Sdf.ValueTypeNames.Float3Array
        assert primvar.GetInterpolation() == UsdGeom.Tokens.vertex
        assert not primvar.IsIndexed()
        assert len(primvar.Get()) == 60

    room_positions = primvars.GetPrimvar("roomP").Get()
    tangent_u = primvars.GetPrimvar("tangentu").Get()
    tangent_v = primvars.GetPrimvar("tangentv").Get()

    for face_index, point_indices in enumerate(face_indices):
        positions = {tuple(room_positions[index]) for index in point_indices}
        assert len(positions) == 1

        centre = positions.pop()
        face_centres_by_room[room_ids[face_index]].add(centre)

        for point_index in point_indices:
            axis_u = tangent_u[point_index]
            axis_v = tangent_v[point_index]
            axis_u_length = axis_u.GetLength()
            axis_v_length = axis_v.GetLength()
            frame_normal = Gf.Cross(axis_u, axis_v)

            assert axis_u_length > 1e-6
            assert axis_v_length > 1e-6
            assert abs(Gf.Dot(axis_u, axis_v)) <= (
                1e-6 * axis_u_length * axis_v_length
            )
            assert Gf.IsClose(
                frame_normal.GetNormalized(),
                Gf.Vec3f(1.0, 0.0, 0.0),
                1e-6,
            )

    assert sum(len(centres) for centres in face_centres_by_room.values()) == 15
    assert stage


def test_houdini_export_authors_dedicated_room_uv_aligned_to_each_frame():
    stage, mesh, _ = _stage_mesh_and_shader()
    primvars = UsdGeom.PrimvarsAPI(mesh)
    room_uv = primvars.GetPrimvar("roomUV")
    values = room_uv.Get()
    points = mesh.GetPointsAttr().Get()
    room_positions = primvars.GetPrimvar("roomP").Get()
    tangent_u = primvars.GetPrimvar("tangentu").Get()
    tangent_v = primvars.GetPrimvar("tangentv").Get()

    assert room_uv.GetTypeName() == Sdf.ValueTypeNames.TexCoord3fArray
    assert room_uv.GetInterpolation() == UsdGeom.Tokens.faceVarying
    assert not room_uv.IsIndexed()
    assert len(values) == 60

    cursor = 0
    expected_corners = {(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)}

    for point_indices in _face_point_indices(mesh):
        face_values = values[cursor : cursor + 4]
        actual_corners = {
            (round(float(value[0]), 6), round(float(value[1]), 6))
            for value in face_values
        }
        assert len(actual_corners) == 4
        for actual, expected in zip(
            sorted(actual_corners), sorted(expected_corners), strict=True
        ):
            assert actual == pytest.approx(expected, abs=2e-4)

        for local_index, point_index in enumerate(point_indices):
            delta = points[point_index] - room_positions[point_index]
            expected_u = (
                Gf.Dot(delta, tangent_u[point_index])
                / Gf.Dot(tangent_u[point_index], tangent_u[point_index])
                + 0.5
            )
            expected_v = (
                Gf.Dot(delta, tangent_v[point_index])
                / Gf.Dot(tangent_v[point_index], tangent_v[point_index])
                + 0.5
            )
            assert tuple(face_values[local_index][:2]) == pytest.approx(
                (expected_u, expected_v), abs=2e-4
            )

        cursor += 4

    st = primvars.GetPrimvar("st")
    assert st.GetTypeName() == Sdf.ValueTypeNames.TexCoord2fArray
    assert st.GetInterpolation() == UsdGeom.Tokens.faceVarying
    assert len(set(map(tuple, st.Get()))) == 1
    assert stage


def test_capture_stage_overrides_only_the_window_material():
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

    facade = stage.GetPrimAtPath("/World/HoudiniGrid/geo/test_grid")
    facade_material, facade_relationship = UsdShade.MaterialBindingAPI(
        facade
    ).ComputeBoundMaterial()
    assert facade_relationship
    assert facade_material.GetPath() == "/World/HoudiniGrid/mtl/test_mat"


def test_capture_stage_keeps_all_external_evidence_assets():
    for name in ("test_grid_wins.usd", "payload.usdc", "geo.usdc", "mtl.usdc"):
        assert (ASSET_DIRECTORY / name).is_file()
