# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect default Windows Glass assignment and its reversible ownership."""

from pathlib import Path

from msp.orms.scene import assignment as assignment_module
from msp.orms.scene.assignment import (
    AutoAssignmentOwner,
    evaluate_windows_glass,
)
from msp.orms.scene.assignment_overrides import (
    AssignmentOverrideOwner,
)
from msp.orms.scene.traversal import iter_composed_prims
from msp.orms.shared_room import controller as controller_module
from msp.orms.shared_room.authoring import (
    camera_position_primvar_required,
    instance_source_camera_input_paths,
)
from msp.orms.shared_room.contracts import (
    ResolvedStageMetrics,
    RuntimeClassifierSettings,
)
from msp.orms.shared_room.controller import SharedRoomClassifier
from msp.orms.shared_room.stage import (
    extract_stage_apertures,
    stage_has_room_map_source_mesh,
)
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CITY_STAGE_PATH = (
    REPOSITORY_ROOT / "assets" / "_external" / "usd" / "room_map_city.usd"
)
PREBOUND_INSTANCE_STAGE_PATH = (
    REPOSITORY_ROOT
    / "tests"
    / "shared_room_runtime"
    / "test_room_map_shared_rooms_houdini_instances.usda"
)


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


def _mesh_material_paths(stage):
    bindings = {}
    for prim in iter_composed_prims(stage, include_instance_proxies=True):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        material, relationship = UsdShade.MaterialBindingAPI(
            prim
        ).ComputeBoundMaterial()
        bindings[str(prim.GetPath())] = (
            str(material.GetPath()) if relationship and material else None
        )
    return bindings


def _instance_root_paths(stage, proxy_paths):
    roots = {
        str(
            assignment_module._instance_root(
                stage.GetPrimAtPath(proxy_path)
            ).GetPath()
        )
        for proxy_path in proxy_paths
    }
    return tuple(sorted(roots))


def _stage_with_instance_window(
    *,
    include_facade=False,
    include_source_class=True,
):
    asset_stage = Usd.Stage.CreateInMemory()
    asset_root = UsdGeom.Xform.Define(asset_stage, "/Building").GetPrim()
    if include_source_class:
        asset_stage.CreateClassPrim("/__class__/Building")
        asset_root.GetInherits().AddInherit("/__class__/Building")
    material = UsdShade.Material.Define(
        asset_stage,
        "/Building/Looks/Windows_Glass",
    )
    mesh = UsdGeom.Mesh.Define(
        asset_stage,
        "/Building/geo/render/Windows_Glass",
    )
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
    if include_facade:
        facade_material = UsdShade.Material.Define(
            asset_stage,
            "/Building/Looks/Facade",
        )
        facade = UsdGeom.Mesh.Define(
            asset_stage,
            "/Building/geo/render/Facade",
        )
        facade.CreatePointsAttr(
            [
                Gf.Vec3f(0.0, 0.0, 1.0),
                Gf.Vec3f(1.0, 0.0, 1.0),
                Gf.Vec3f(1.0, 1.0, 1.0),
                Gf.Vec3f(0.0, 1.0, 1.0),
            ]
        )
        facade.CreateFaceVertexCountsAttr([4])
        facade.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        UsdShade.MaterialBindingAPI.Apply(facade.GetPrim()).Bind(
            facade_material
        )

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")
    instance = UsdGeom.Xform.Define(stage, "/World/BuildingA").GetPrim()
    instance.GetReferences().AddReference(
        asset_stage.GetRootLayer().identifier,
        "/Building",
    )
    instance.SetInstanceable(True)
    return stage, asset_stage, instance


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

    decisions = evaluate_windows_glass(
        stage,
        candidate_selectors=("Windows_Glass",),
    )

    assert len(decisions) == 1
    assert decisions[0].eligible
    assert decisions[0].prim_path == str(mesh.GetPath())
    assert decisions[0].source_material_path == str(material.GetPath())


def test_configured_mesh_selector_extends_compatibility_discovery():
    legacy_stage, _legacy_mesh, _legacy_material = _stage_with_window(
        material_name="base_lod00_mat",
        mesh_name="Windows_Glass",
    )
    custom_stage, custom_mesh, _custom_material = _stage_with_window(
        material_name="base_lod00_mat",
        mesh_name="Lobby_Panes",
    )

    legacy = evaluate_windows_glass(
        legacy_stage,
        candidate_selectors=("Lobby_*",),
    )
    selected = evaluate_windows_glass(
        custom_stage,
        candidate_selectors=("Lobby_*",),
    )

    assert len(legacy) == 1
    assert legacy[0].eligible
    assert len(selected) == 1
    assert selected[0].prim_path == str(custom_mesh.GetPath())
    assert selected[0].eligible


def test_configured_selector_can_match_a_complete_composed_path():
    stage, mesh, _material = _stage_with_window(
        material_name="base_lod00_mat",
        mesh_name="Lobby_Panes",
    )

    decisions = evaluate_windows_glass(
        stage,
        candidate_selectors=("*/Building/Lobby_Panes",),
    )

    assert len(decisions) == 1
    assert decisions[0].prim_path == str(mesh.GetPath())


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


def test_preserve_binds_only_instance_window_and_restores_source():
    stage, asset_stage, instance = _stage_with_instance_window(
        include_facade=True
    )
    stage_before = stage.GetRootLayer().ExportToString()
    asset_before = asset_stage.GetRootLayer().ExportToString()
    decisions = evaluate_windows_glass(stage)

    assert len(decisions) == 1
    assert decisions[0].prim_path.endswith("/Windows_Glass")
    assert decisions[0].eligible
    assert not decisions[0].override_editable
    source_bindings = _mesh_material_paths(stage)
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)

    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        instance_source_asset_path="room_map_single.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )
    result = owner.apply()

    assert result.assigned_prim_paths == (
        "/World/BuildingA/geo/render/Windows_Glass",
    )
    assert result.preserved_instance_paths == ("/World/BuildingA",)
    assert instance.IsInstance()
    inherited_classes = instance.GetInherits().GetAllDirectInherits()
    assert inherited_classes == [Sdf.Path("/__class__/Building")]
    assert owner.runtime_layer.GetPrimAtPath(instance.GetPath()) is None
    assert not owner.runtime_layer.GetPrimAtPath(
        Sdf.Path("/__ORMSAutoAssignment")
    )
    assert not instance.GetRelationship(
        "material:binding:collection:ormsRoomMapWindows"
    )
    window = stage.GetPrimAtPath("/World/BuildingA/geo/render/Windows_Glass")
    assert window.IsInstanceProxy()
    assert _bound_material_path(window) == (
        "/World/BuildingA/mtl/ORMSRoomMapSingle"
    )
    assert (
        UsdShade.MaterialBindingAPI(window).ComputeBoundMaterial()[1].GetName()
        == "material:binding"
    )
    camera_input_paths = instance_source_camera_input_paths(stage)
    assert camera_input_paths == (
        Sdf.Path(
            "/__class__/Building/mtl/ORMSRoomMapSingle/"
            "Shader.inputs:camera_position_world"
        ),
    )
    assert not camera_position_primvar_required(stage)
    assert not UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World")).GetPrimvar(
        "ormsCameraPositionWorld"
    )
    assert tuple(stage.GetSessionLayer().subLayerPaths) != session_before
    assert owner.layer_identifier in stage.GetSessionLayer().subLayerPaths
    references = instance.GetMetadata("references").GetAppliedItems()
    assert len(references) == 1
    assert references[0].assetPath == asset_stage.GetRootLayer().identifier
    facade = stage.GetPrimAtPath("/World/BuildingA/geo/render/Facade")
    assert facade.IsInstanceProxy()
    assert _bound_material_path(facade).endswith("/Looks/Facade")
    assert stage.GetRootLayer().ExportToString() == stage_before
    assert asset_stage.GetRootLayer().ExportToString() == asset_before

    owner.stop()

    assert instance.IsInstance()
    assert instance.GetInherits().GetAllDirectInherits() == [
        Sdf.Path("/__class__/Building")
    ]
    assert _mesh_material_paths(stage) == source_bindings
    assert not instance_source_camera_input_paths(stage)
    assert owner.layer_identifier not in stage.GetSessionLayer().subLayerPaths
    assert stage.GetRootLayer().ExportToString() == stage_before
    assert asset_stage.GetRootLayer().ExportToString() == asset_before


def test_preserve_without_one_source_class_fails_open():
    stage, asset_stage, instance = _stage_with_instance_window(
        include_facade=True,
        include_source_class=False,
    )
    source_bindings = _mesh_material_paths(stage)
    stage_before = stage.GetRootLayer().ExportToString()
    asset_before = asset_stage.GetRootLayer().ExportToString()
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        instance_source_asset_path="room_map_single.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )

    result = owner.apply()

    assert not result.assigned_prim_paths
    assert result.decisions[0].reason == (
        "native_instance_source_class_unavailable"
    )
    assert not result.decisions[0].eligible
    assert owner.runtime_layer is None
    assert instance.IsInstance()
    assert _mesh_material_paths(stage) == source_bindings
    assert tuple(stage.GetSessionLayer().subLayerPaths) == session_before
    assert stage.GetRootLayer().ExportToString() == stage_before
    assert asset_stage.GetRootLayer().ExportToString() == asset_before


def test_preserve_with_ambiguous_source_classes_fails_open():
    stage, asset_stage, instance = _stage_with_instance_window(
        include_facade=True,
    )
    asset_stage.CreateClassPrim("/__class__/BuildingMixin")
    asset_stage.GetPrimAtPath("/Building").GetInherits().AddInherit(
        "/__class__/BuildingMixin"
    )
    source_bindings = _mesh_material_paths(stage)
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        instance_source_asset_path="room_map_single.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )

    result = owner.apply()

    assert not result.assigned_prim_paths
    assert result.decisions[0].reason == (
        "native_instance_source_class_unavailable"
    )
    assert owner.runtime_layer is None
    assert instance.IsInstance()
    assert len(instance.GetInherits().GetAllDirectInherits()) == 2
    assert _mesh_material_paths(stage) == source_bindings
    assert tuple(stage.GetSessionLayer().subLayerPaths) == session_before


def test_preserve_restart_replaces_only_ephemeral_window_bindings():
    stage, asset_stage, instance = _stage_with_instance_window(
        include_facade=True
    )
    stage_before = stage.GetRootLayer().ExportToString()
    asset_before = asset_stage.GetRootLayer().ExportToString()
    source_bindings = _mesh_material_paths(stage)
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)

    for _restart_index in range(2):
        owner = AutoAssignmentOwner(
            stage,
            source_asset_path="room_map.mdl",
            instance_source_asset_path="room_map_single.mdl",
            atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
            atlas_variant_count=8,
            candidate_selectors=("Windows_Glass",),
        )
        result = owner.apply()

        assert result.assigned_prim_paths == (
            "/World/BuildingA/geo/render/Windows_Glass",
        )
        assert result.preserved_instance_paths == ("/World/BuildingA",)
        assert instance.IsInstance()
        bindings = _mesh_material_paths(stage)
        assert (
            bindings["/World/BuildingA/geo/render/Windows_Glass"]
            == "/World/BuildingA/mtl/ORMSRoomMapSingle"
        )
        assert (
            bindings["/World/BuildingA/geo/render/Facade"]
            == source_bindings["/World/BuildingA/geo/render/Facade"]
        )
        assert tuple(stage.GetSessionLayer().subLayerPaths) != session_before
        assert stage.GetRootLayer().ExportToString() == stage_before
        assert asset_stage.GetRootLayer().ExportToString() == asset_before

        owner.stop()

        assert instance.IsInstance()
        assert _mesh_material_paths(stage) == source_bindings
        assert tuple(stage.GetSessionLayer().subLayerPaths) == session_before
        assert stage.GetRootLayer().ExportToString() == stage_before
        assert asset_stage.GetRootLayer().ExportToString() == asset_before


def test_preserve_instances_with_same_window_shape_share_one_binding_class():
    stage, asset_stage, first = _stage_with_instance_window(
        include_facade=True
    )
    second = UsdGeom.Xform.Define(stage, "/World/BuildingB").GetPrim()
    second.GetReferences().AddReference(
        asset_stage.GetRootLayer().identifier,
        "/Building",
    )
    second.SetInstanceable(True)
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        instance_source_asset_path="room_map_single.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
        candidate_selectors=("Windows_Glass",),
    )

    result = owner.apply()

    assert result.preserved_instance_paths == (
        "/World/BuildingA",
        "/World/BuildingB",
    )
    assert first.IsInstance() and second.IsInstance()
    first_classes = first.GetInherits().GetAllDirectInherits()
    second_classes = second.GetInherits().GetAllDirectInherits()
    assert first_classes == second_classes
    assert first_classes == [Sdf.Path("/__class__/Building")]
    for instance_path in result.preserved_instance_paths:
        window = stage.GetPrimAtPath(
            f"{instance_path}/geo/render/Windows_Glass"
        )
        facade = stage.GetPrimAtPath(f"{instance_path}/geo/render/Facade")
        assert _bound_material_path(window) == (
            f"{instance_path}/mtl/ORMSRoomMapSingle"
        )
        assert _bound_material_path(facade).endswith("/Looks/Facade")

    owner.stop()

    assert first.GetInherits().GetAllDirectInherits() == [
        Sdf.Path("/__class__/Building")
    ]
    assert second.GetInherits().GetAllDirectInherits() == [
        Sdf.Path("/__class__/Building")
    ]


def test_city_preserve_restart_changes_no_instance_materials():
    stage = Usd.Stage.Open(str(CITY_STAGE_PATH))
    assert stage
    root_before = stage.GetRootLayer().ExportToString()
    source_bindings = _mesh_material_paths(stage)
    decisions = evaluate_windows_glass(
        stage,
        candidate_selectors=("Windows_Glass",),
    )
    window_proxy_paths = {
        decision.prim_path
        for decision in decisions
        if decision.eligible and not decision.override_editable
    }
    assert window_proxy_paths
    point_instancer = UsdGeom.PointInstancer(
        stage.GetPrimAtPath("/World/RoomMapDemo/CityBlocks")
    )
    assert point_instancer
    assert point_instancer.GetPrototypesRel().GetTargets() == [
        Sdf.Path("/World/RoomMapDemo/CityBlocks/Prototypes/block")
    ]
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)
    inherits_before = {
        root_path: tuple(
            stage.GetPrimAtPath(root_path).GetInherits().GetAllDirectInherits()
        )
        for root_path in _instance_root_paths(stage, window_proxy_paths)
    }

    for _restart_index in range(2):
        owner = AutoAssignmentOwner(
            stage,
            source_asset_path="room_map.mdl",
            instance_source_asset_path="room_map_single.mdl",
            atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
            atlas_variant_count=8,
            candidate_selectors=("Windows_Glass",),
        )
        result = owner.apply()
        assert set(result.assigned_prim_paths) == window_proxy_paths
        assert result.preserved_instance_paths
        camera_input_paths = instance_source_camera_input_paths(stage)
        assert len(camera_input_paths) == len(result.preserved_instance_paths)
        assert all(
            str(path).endswith(
                "/mtl/ORMSRoomMapSingle/" "Shader.inputs:camera_position_world"
            )
            for path in camera_input_paths
        )
        assert not camera_position_primvar_required(stage)
        assert not UsdGeom.PrimvarsAPI(
            stage.GetPrimAtPath("/World")
        ).GetPrimvar("ormsCameraPositionWorld")
        for instance_path in result.preserved_instance_paths:
            instance = stage.GetPrimAtPath(instance_path)
            assert instance.IsInstance()
            assert (
                tuple(instance.GetInherits().GetAllDirectInherits())
                == inherits_before[instance_path]
            )
            assert not instance.GetRelationship(
                "material:binding:collection:ormsRoomMapWindows"
            )
            assert (
                owner.runtime_layer.GetPrimAtPath(instance.GetPath()) is None
            )
        assert not owner.runtime_layer.GetPrimAtPath(
            Sdf.Path("/__ORMSAutoAssignment")
        )
        bindings = _mesh_material_paths(stage)
        assert {
            path
            for path, material_path in bindings.items()
            if material_path != source_bindings[path]
        } == window_proxy_paths
        for window_path in window_proxy_paths:
            instance_root = assignment_module._instance_root(
                stage.GetPrimAtPath(window_path)
            )
            assert bindings[window_path] == (
                f"{instance_root.GetPath()}/mtl/ORMSRoomMapSingle"
            )
        with Usd.EditContext(stage, owner.runtime_layer):
            for camera_input_path in camera_input_paths:
                stage.GetAttributeAtPath(camera_input_path).Set(
                    Gf.Vec3f(100.0, 200.0, 300.0)
                )
        assert _mesh_material_paths(stage) == bindings
        assert not UsdGeom.PrimvarsAPI(
            stage.GetPrimAtPath("/World")
        ).GetPrimvar("ormsCameraPositionWorld")
        assert tuple(stage.GetSessionLayer().subLayerPaths) != session_before
        assert stage.GetRootLayer().ExportToString() == root_before

        owner.stop()

        assert _mesh_material_paths(stage) == source_bindings
        assert not instance_source_camera_input_paths(stage)
        assert tuple(stage.GetSessionLayer().subLayerPaths) == session_before
        assert stage.GetRootLayer().ExportToString() == root_before


def test_city_existing_source_class_can_override_only_its_window():
    """Prove the Houdini class arc can carry a class-local x1 binding."""

    stage = Usd.Stage.Open(str(CITY_STAGE_PATH))
    assert stage
    instance_path = (
        "/World/RoomMapDemo/CityBlocks/Prototypes/block/" "Moskovskiy_av_136"
    )
    instance = stage.GetPrimAtPath(instance_path)
    assert instance.IsInstance()
    inherited_classes_before = tuple(
        instance.GetInherits().GetAllDirectInherits()
    )
    assert len(inherited_classes_before) == 1
    source_class_path = inherited_classes_before[0]
    source_bindings = _mesh_material_paths(stage)
    root_before = stage.GetRootLayer().ExportToString()
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)
    probe_layer = Sdf.Layer.CreateAnonymous("orms_class_overlay_probe.usda")
    stage.GetSessionLayer().subLayerPaths = [
        probe_layer.identifier,
        *stage.GetSessionLayer().subLayerPaths,
    ]

    try:
        with Usd.EditContext(stage, probe_layer):
            stage.CreateClassPrim(source_class_path)
            material = UsdShade.Material.Define(
                stage,
                source_class_path.AppendPath("mtl/ORMSRoomMapSingle"),
            )
            relative_window_path = Sdf.Path("geo/render/Windows_Glass")
            window_overlay = stage.OverridePrim(
                source_class_path.AppendPath(relative_window_path)
            )
            UsdShade.MaterialBindingAPI.Apply(window_overlay).Bind(material)

        assert instance.IsInstance()
        assert tuple(instance.GetInherits().GetAllDirectInherits()) == (
            inherited_classes_before
        )
        bindings = _mesh_material_paths(stage)
        changed_paths = {
            path
            for path, material_path in bindings.items()
            if material_path != source_bindings[path]
        }
        window_path = f"{instance_path}/geo/render/Windows_Glass"
        assert changed_paths == {window_path}
        assert bindings[window_path] == (
            f"{instance_path}/mtl/ORMSRoomMapSingle"
        )
        assert stage.GetRootLayer().ExportToString() == root_before
    finally:
        stage.GetSessionLayer().subLayerPaths = list(session_before)

    assert instance.IsInstance()
    assert tuple(instance.GetInherits().GetAllDirectInherits()) == (
        inherited_classes_before
    )
    assert _mesh_material_paths(stage) == source_bindings
    assert stage.GetRootLayer().ExportToString() == root_before


def test_city_native_runtime_bridges_only_class_local_camera_inputs(
    monkeypatch,
):
    """Protect the camera-motion boundary that failed in Kit/RTX 1.0.11."""

    monkeypatch.setattr(
        controller_module,
        "_log_diagnostic",
        lambda _diagnostic: None,
    )
    stage = Usd.Stage.Open(str(CITY_STAGE_PATH))
    source_bindings = _mesh_material_paths(stage)
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        instance_source_asset_path="room_map_single.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
        candidate_selectors=("Windows_Glass",),
    )
    result = owner.apply()
    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
    )

    classifier.start()

    camera_input_paths = classifier.camera_input_paths
    assert len(camera_input_paths) == len(result.preserved_instance_paths)
    assert all(path.startswith("/__class__/") for path in camera_input_paths)
    assert all(
        path.endswith("Shader.inputs:camera_position_world")
        for path in camera_input_paths
    )
    assert not any(path.startswith("/World.") for path in camera_input_paths)
    assert not UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World")).GetPrimvar(
        "ormsCameraPositionWorld"
    )
    bindings_before_camera_update = _mesh_material_paths(stage)
    with Usd.EditContext(stage, classifier.runtime_layer):
        for camera_input_path in camera_input_paths:
            stage.GetAttributeAtPath(camera_input_path).Set(
                Gf.Vec3f(100.0, 200.0, 300.0)
            )
    assert _mesh_material_paths(stage) == bindings_before_camera_update

    classifier.stop()
    owner.stop()

    assert _mesh_material_paths(stage) == source_bindings


def test_preserved_instance_material_updates_supported_x1_controls():
    stage, _asset_stage, instance = _stage_with_instance_window()
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        instance_source_asset_path="room_map_single.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
        material_input_values={
            "enable_emission": True,
            "emission_strength": 32000.0,
        },
    )

    result = owner.apply()

    assert instance.IsInstance()
    assert result.assigned_prim_paths == (
        "/World/BuildingA/geo/render/Windows_Glass",
    )
    shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__class__/Building/mtl/ORMSRoomMapSingle/Shader")
    )
    assert shader.GetInput("emission_strength").Get() == 32000.0
    assert not shader.GetInput("enable_opacity")

    updated_count = owner.set_material_input_values(
        {
            "emission_strength": 64000.0,
            "glass_reflectivity": 0.2,
        }
    )

    assert updated_count == 2
    assert shader.GetInput("emission_strength").Get() == 64000.0
    assert abs(shader.GetInput("glass_reflectivity").Get() - 0.2) < 1e-6
    assert instance.IsInstance()
    owner.stop()


def test_prebound_instance_source_is_recognised_without_runtime_assignment():
    stage = Usd.Stage.Open(str(PREBOUND_INSTANCE_STAGE_PATH))
    assert stage
    source_bindings = _mesh_material_paths(stage)
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )

    result = owner.apply()

    assert result.decisions == ()
    assert result.assigned_prim_paths == ()
    assert stage_has_room_map_source_mesh(stage)
    assert camera_position_primvar_required(stage)
    assert _mesh_material_paths(stage) == source_bindings
    assert tuple(stage.GetSessionLayer().subLayerPaths) == session_before
    owner.stop()


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


def test_empty_assignment_does_not_attach_or_author_runtime_state():
    stage, _mesh, _material = _stage_with_window(material_name="Facade_Glass")
    session_before = tuple(stage.GetSessionLayer().subLayerPaths)
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        instance_source_asset_path="room_map_single.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )

    result = owner.apply()

    assert not result.assigned_prim_paths
    assert owner.runtime_layer is None
    assert tuple(stage.GetSessionLayer().subLayerPaths) == session_before
    assert not stage.GetPrimAtPath("/__ORMSAutoAssignment")


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


def test_source_exclusion_remains_visible_and_can_be_overridden_safely():
    stage, mesh, _material = _stage_with_window(
        material_name="Facade_Glass",
        mesh_name="Facade_Panels",
    )
    source_attribute = mesh.GetPrim().CreateAttribute(
        "orms:autoAssign",
        Sdf.ValueTypeNames.Bool,
    )
    source_attribute.Set(False)
    source_before = stage.GetRootLayer().ExportToString()
    owner = AssignmentOverrideOwner(stage)

    excluded = evaluate_windows_glass(stage)
    owner.set_override(str(mesh.GetPath()), True)
    allowed = evaluate_windows_glass(stage)

    assert excluded[0].reason == "explicitly_excluded"
    assert allowed[0].eligible
    assert owner.value_for(str(mesh.GetPath())) is True
    assert stage.GetRootLayer().ExportToString() == source_before

    owner.set_override(str(mesh.GetPath()), None)

    assert evaluate_windows_glass(stage)[0].reason == "explicitly_excluded"
    assert stage.GetRootLayer().ExportToString() == source_before


def test_assignment_override_stop_removes_only_its_session_layer():
    stage, mesh, _material = _stage_with_window()
    source_before = stage.GetRootLayer().ExportToString()
    original_sublayers = tuple(stage.GetSessionLayer().subLayerPaths)
    owner = AssignmentOverrideOwner(stage)

    owner.set_override(str(mesh.GetPath()), False)

    assert evaluate_windows_glass(stage)[0].reason == "explicitly_excluded"
    assert tuple(stage.GetSessionLayer().subLayerPaths) != original_sublayers

    owner.stop()

    assert tuple(stage.GetSessionLayer().subLayerPaths) == original_sublayers
    assert evaluate_windows_glass(stage)[0].eligible
    assert stage.GetRootLayer().ExportToString() == source_before
