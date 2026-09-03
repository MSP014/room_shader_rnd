"""Protect default Windows Glass assignment and its reversible ownership."""

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

from tools.omniverse.runtime import assignment as assignment_module
from tools.omniverse.runtime.assignment import (
    AutoAssignmentOwner,
    evaluate_windows_glass,
)
from tools.omniverse.shared_room.contracts import ResolvedStageMetrics
from tools.omniverse.shared_room.stage import extract_stage_apertures


def _stage_with_window(
    *,
    material_name="Windows_Glass",
    mesh_name="Windows",
    valid=True,
):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")
    material = UsdShade.Material.Define(stage, f"/World/Looks/{material_name}")
    mesh = UsdGeom.Mesh.Define(stage, f"/World/Building/{mesh_name}")
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
    if valid:
        primvars = UsdGeom.PrimvarsAPI(mesh)
        primvars.CreatePrimvar(
            "roomID", Sdf.ValueTypeNames.IntArray, UsdGeom.Tokens.uniform
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
    return stage, mesh, material


def _bound_material_path(prim):
    material, relationship = UsdShade.MaterialBindingAPI(
        prim
    ).ComputeBoundMaterial()
    assert relationship
    return str(material.GetPath())


def test_valid_windows_glass_is_eligible_and_invalid_contract_is_rejected():
    valid_stage, _valid_mesh, _valid_material = _stage_with_window()
    invalid_stage, _invalid_mesh, _invalid_material = _stage_with_window(
        valid=False
    )

    valid_decision = evaluate_windows_glass(valid_stage)
    invalid_decision = evaluate_windows_glass(invalid_stage)

    assert len(valid_decision) == 1
    assert valid_decision[0].eligible
    assert valid_decision[0].reason == "windows_glass_contract_valid"
    assert len(invalid_decision) == 1
    assert not invalid_decision[0].eligible
    assert invalid_decision[0].reason.startswith("missing_primvars:")


def test_windows_glass_mesh_identity_wins_over_generic_inherited_material():
    stage, mesh, material = _stage_with_window(
        material_name="base_lod00_mat",
        mesh_name="Windows_Glass",
    )

    decisions = evaluate_windows_glass(stage)

    assert len(decisions) == 1
    assert decisions[0].eligible
    assert decisions[0].prim_path == str(mesh.GetPath())
    assert decisions[0].source_material_path == str(material.GetPath())


def test_semantic_mesh_below_windows_container_is_eligible():
    stage, mesh, material = _stage_with_window(
        material_name="base_lod00_mat",
        mesh_name="windows/living_rooms",
    )

    decisions = evaluate_windows_glass(stage)

    assert len(decisions) == 1
    assert decisions[0].eligible
    assert decisions[0].prim_path == str(mesh.GetPath())
    assert decisions[0].source_material_path == str(material.GetPath())


def test_explicit_exclusion_wins_over_default_assignment():
    stage, mesh, _material = _stage_with_window()
    mesh.GetPrim().CreateAttribute(
        "orms:autoAssign", Sdf.ValueTypeNames.Bool
    ).Set(False)

    decision = evaluate_windows_glass(stage)

    assert len(decision) == 1
    assert not decision[0].eligible
    assert decision[0].reason == "explicitly_excluded"


def test_owned_assignment_layer_restores_original_material_on_stop():
    stage, mesh, source_material = _stage_with_window()
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )

    result = owner.apply()

    assert result.assigned_prim_paths == (str(mesh.GetPath()),)
    assert _bound_material_path(mesh.GetPrim()) == (
        "/__ORMSAutoAssignment/Looks/RoomMap"
    )
    assert owner.layer_identifier in stage.GetSessionLayer().subLayerPaths
    extraction = extract_stage_apertures(
        stage,
        ResolvedStageMetrics(up_axis="Y", meters_per_unit=1.0),
    )
    assert len(extraction.apertures) == 1

    owner.stop()

    assert owner.layer_identifier not in stage.GetSessionLayer().subLayerPaths
    assert _bound_material_path(mesh.GetPrim()) == str(
        source_material.GetPath()
    )


def test_auto_assignment_scope_is_hidden_from_stage_ui(monkeypatch):
    stage, _mesh, _source_material = _stage_with_window()
    hidden_paths = []
    monkeypatch.setattr(
        assignment_module,
        "hide_in_stage_window",
        lambda prim: hidden_paths.append(str(prim.GetPath())) or True,
    )
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )

    owner.apply()

    assert hidden_paths == ["/__ORMSAutoAssignment"]


def test_unrelated_material_is_never_considered_for_auto_assignment():
    stage, _mesh, _material = _stage_with_window(material_name="Facade_Glass")

    assert evaluate_windows_glass(stage) == ()


def test_explicit_opt_in_supports_a_semantically_named_mesh():
    stage, mesh, _material = _stage_with_window(
        material_name="Facade_Glass",
        mesh_name="Living_Rooms",
    )
    mesh.GetPrim().CreateAttribute(
        "orms:autoAssign", Sdf.ValueTypeNames.Bool
    ).Set(True)

    decision = evaluate_windows_glass(stage)

    assert len(decision) == 1
    assert decision[0].eligible
