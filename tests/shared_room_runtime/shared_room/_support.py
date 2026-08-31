"""Build reusable in-memory OpenUSD stages for shared-room tests."""

from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MDL_PATH = REPOSITORY_ROOT / "src" / "mdl" / "room_map.mdl"


def _window_stage(room_ids=(1, 1, 2, 1, 1)):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    mesh = UsdGeom.Mesh.Define(stage, "/World/Building/Windows")
    points = []
    counts = []
    indices = []
    room_positions = []
    tangent_u = []
    tangent_v = []
    room_uv = []

    for face_index in range(len(room_ids)):
        left = face_index * 1.1
        point_offset = len(points)
        points.extend(
            [
                (left, 0.0, 0.0),
                (left + 1.0, 0.0, 0.0),
                (left + 1.0, 1.0, 0.0),
                (left, 1.0, 0.0),
            ]
        )
        counts.append(4)
        indices.extend(range(point_offset, point_offset + 4))
        room_positions.extend([(left + 0.5, 0.5, 0.0)] * 4)
        tangent_u.extend([(1.0, 0.0, 0.0)] * 4)
        tangent_v.extend([(0.0, 1.0, 0.0)] * 4)
        room_uv.extend(
            [
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 1.0, 0.0),
                (0.0, 1.0, 0.0),
            ]
        )

    mesh.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(indices))
    mesh.CreatePointsAttr(
        Vt.Vec3fArray([Gf.Vec3f(*value) for value in points])
    )
    primvars = UsdGeom.PrimvarsAPI(mesh)
    primvars.CreatePrimvar(
        "roomID", Sdf.ValueTypeNames.IntArray, UsdGeom.Tokens.uniform
    ).Set(Vt.IntArray(room_ids))
    for name, values in (
        ("roomP", room_positions),
        ("tangentu", tangent_u),
        ("tangentv", tangent_v),
    ):
        primvars.CreatePrimvar(
            name,
            Sdf.ValueTypeNames.Float3Array,
            UsdGeom.Tokens.vertex,
        ).Set(Vt.Vec3fArray([Gf.Vec3f(*value) for value in values]))
    primvars.CreatePrimvar(
        "roomUV",
        Sdf.ValueTypeNames.TexCoord3fArray,
        UsdGeom.Tokens.faceVarying,
    ).Set(Vt.Vec3fArray([Gf.Vec3f(*value) for value in room_uv]))
    material = UsdShade.Material.Define(stage, "/World/Building/Looks/RoomMap")
    shader = UsdShade.Shader.Define(
        stage, "/World/Building/Looks/RoomMap/Shader"
    )
    shader.GetPrim().CreateAttribute(
        "info:implementationSource",
        Sdf.ValueTypeNames.Token,
        custom=False,
    ).Set("sourceAsset")
    shader.GetPrim().CreateAttribute(
        "info:mdl:sourceAsset",
        Sdf.ValueTypeNames.Asset,
        custom=False,
    ).Set(Sdf.AssetPath("../src/mdl/room_map.mdl"))
    shader.GetPrim().CreateAttribute(
        "info:mdl:sourceAsset:subIdentifier",
        Sdf.ValueTypeNames.Token,
        custom=False,
    ).Set("room_map")
    shader.CreateInput("camera_position_world", Sdf.ValueTypeNames.Float3).Set(
        Gf.Vec3f(0.0)
    )
    shader.CreateInput("window_aperture_scale", Sdf.ValueTypeNames.Float2).Set(
        Gf.Vec2f(1.0)
    )
    shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput("mdl").ConnectToSource(shader_output)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return stage, mesh


def _instance_stage():
    asset_stage, _ = _window_stage((6, 6))
    source_shader = UsdShade.Shader(
        asset_stage.GetPrimAtPath("/World/Building/Looks/RoomMap/Shader")
    )
    source_shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Set(
        Sdf.AssetPath("../src/mdl/room_map_single.mdl")
    )
    source_shader.GetPrim().GetAttribute(
        "info:mdl:sourceAsset:subIdentifier"
    ).Set("room_map_single")
    facade = UsdGeom.Mesh.Define(asset_stage, "/World/Building/Facade")
    facade_material = UsdShade.Material.Define(
        asset_stage,
        "/World/Building/Looks/Facade",
    )
    UsdShade.MaterialBindingAPI.Apply(facade.GetPrim()).Bind(facade_material)
    asset_layer = asset_stage.GetRootLayer()
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    instances = []
    for name, offset in (("BuildingA", 0.0), ("BuildingB", 5.0)):
        prim = stage.DefinePrim(f"/World/{name}", "Xform")
        prim.GetReferences().AddReference(
            asset_layer.identifier,
            "/World/Building",
        )
        prim.SetInstanceable(True)
        UsdGeom.Xformable(prim).AddTranslateOp().Set(
            Gf.Vec3d(offset, 0.0, 0.0)
        )
        instances.append(prim)
    return stage, asset_stage, tuple(instances)
