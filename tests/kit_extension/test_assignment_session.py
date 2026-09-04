"""Protect stage-scoped assignment inspection and override lifecycle."""

from msp.orms.runtime.assignment_session import AssignmentSession
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade


def _stage_with_window():
    stage = Usd.Stage.CreateInMemory()
    material = UsdShade.Material.Define(stage, "/World/Looks/Windows_Glass")
    mesh = UsdGeom.Mesh.Define(stage, "/World/windows/living_rooms")
    mesh.CreatePointsAttr(
        [
            Gf.Vec3f(0.0, 0.0, 0.0),
            Gf.Vec3f(1.0, 0.0, 0.0),
            Gf.Vec3f(1.0, 1.0, 0.0),
            Gf.Vec3f(0.0, 1.0, 0.0),
        ]
    )
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    primvars = UsdGeom.PrimvarsAPI(mesh)
    primvars.CreatePrimvar(
        "roomID",
        Sdf.ValueTypeNames.IntArray,
        UsdGeom.Tokens.uniform,
    ).Set([1])
    for name in ("roomP", "tangentu", "tangentv"):
        primvars.CreatePrimvar(
            name,
            Sdf.ValueTypeNames.Float3Array,
            UsdGeom.Tokens.uniform,
        ).Set([Gf.Vec3f(0.0)])
    primvars.CreatePrimvar(
        "roomUV",
        Sdf.ValueTypeNames.Float2Array,
        UsdGeom.Tokens.faceVarying,
    ).Set([Gf.Vec2f(0.0)] * 4)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return stage, mesh


def test_session_retains_pre_binding_inspection_across_rebuilds():
    stage, mesh = _stage_with_window()
    source_before = stage.GetRootLayer().ExportToString()
    session = AssignmentSession(stage)

    session.apply(
        source_asset_path="room_map.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )
    first = session.inspect()
    session.set_override(str(mesh.GetPath()), False)
    session.apply(
        source_asset_path="room_map.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )
    second = session.inspect()

    assert first.editable and first.items[0].assigned
    assert second.items[0].override is False
    assert not second.items[0].assigned
    assert second.items[0].reason == "explicitly_excluded"
    assert stage.GetRootLayer().ExportToString() == source_before

    session.stop()

    assert stage.GetSessionLayer().subLayerPaths == []
    assert stage.GetRootLayer().ExportToString() == source_before
