"""Protect ordered stage classification and bounded material-family authoring."""

import pytest
from msp.orms.interior_sets.contracts import (
    DEFAULT_INTERIOR_SET_ID,
    InteriorSetCollection,
    InteriorSetConfig,
    runtime_set_token,
)
from msp.orms.interior_sets.runtime_resources import (
    InteriorSetRuntimeResources,
    InteriorSetRuntimeSnapshot,
)
from msp.orms.scene.resources import (
    RuntimeAtlasFamily,
    RuntimeResources,
)
from msp.orms.shared_room import authoring as authoring_module
from msp.orms.shared_room.authoring import RuntimeLayerOwner
from msp.orms.shared_room.contracts import RuntimeClassifierSettings
from msp.orms.shared_room.pipeline import classify_stage
from pxr import Gf, Sdf, UsdGeom, UsdShade

from ._support import REPOSITORY_ROOT, _window_stage


def test_stage_classification_authors_all_available_material_families():
    stage, mesh = _window_stage((1, 1, 2, 1, 1))
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()

    classification = classify_stage(
        stage,
        runtime_layer,
        RuntimeClassifierSettings(),
        REPOSITORY_ROOT,
    )

    materials = tuple(
        prim
        for prim in stage.GetPrimAtPath("/__ORMSRuntime/Looks").GetChildren()
        if prim.IsA(UsdShade.Material)
    )
    subsets = tuple(
        subset
        for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh)
        if subset.GetElementTypeAttr().Get() == UsdGeom.Tokens.face
    )
    bound_sizes = set()
    for subset in subsets:
        material, relationship = UsdShade.MaterialBindingAPI(
            subset.GetPrim()
        ).ComputeBoundMaterial()
        assert relationship
        bound_sizes.add(int(material.GetPath().name.removeprefix("RoomMapX")))

    assert classification.available_room_sizes == frozenset({1, 2, 3, 4})
    assert len(materials) == 4
    assert all(
        material.GetAttribute("omni:rtx:enableCutoutOpacity").Get() is True
        for material in materials
    )
    assert all(
        UsdShade.Shader(stage.GetPrimAtPath(f"{material.GetPath()}/Shader"))
        .GetInput("enable_opacity")
        .Get()
        is True
        for material in materials
    )
    assert bound_sizes == {1, 2}
    assert sum(len(subset.GetIndicesAttr().Get()) for subset in subsets) == 5
    interior_set_primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(
        "ormsInteriorSetId"
    )
    assert interior_set_primvar.Get() == DEFAULT_INTERIOR_SET_ID
    assert interior_set_primvar.GetTypeName() == Sdf.ValueTypeNames.String
    assert interior_set_primvar.GetInterpolation() == UsdGeom.Tokens.constant

    runtime_material = UsdShade.Material(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX2")
    )
    runtime_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX2/Shader")
    )
    source_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Building/Looks/RoomMap/Shader")
    )
    assert runtime_material.GetPrim().HasAuthoredSpecializes()
    assert tuple(runtime_shader.GetInput("window_aperture_scale").Get()) == (
        1.0,
        1.0,
    )

    source_shader.GetInput("window_aperture_scale").Set(Gf.Vec2f(0.5, 0.75))

    assert tuple(runtime_shader.GetInput("window_aperture_scale").Get()) == (
        0.5,
        0.75,
    )

    owner.detach()

    assert not stage.GetPrimAtPath("/__ORMSRuntime")


def test_central_material_values_are_authored_to_every_family():
    stage, _mesh = _window_stage((1, 1))
    owner = RuntimeLayerOwner(stage)

    classify_stage(
        stage,
        owner.attach(),
        RuntimeClassifierSettings(),
        REPOSITORY_ROOT,
        material_input_values={
            "glass_roughness": 0.37,
            "window_shift": Gf.Vec2f(0.2, -0.1),
        },
    )

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert shader.GetInput("glass_roughness").Get() == pytest.approx(0.37)
        assert tuple(shader.GetInput("window_shift").Get()) == pytest.approx(
            (0.2, -0.1)
        )


def test_runtime_implementation_scope_is_hidden_from_stage_ui(monkeypatch):
    stage, _mesh = _window_stage((1,))
    owner = RuntimeLayerOwner(stage)
    hidden_paths = []
    monkeypatch.setattr(
        authoring_module,
        "hide_in_stage_window",
        lambda prim: hidden_paths.append(str(prim.GetPath())) or True,
    )

    classify_stage(
        stage,
        owner.attach(),
        RuntimeClassifierSettings(),
        REPOSITORY_ROOT,
    )

    assert hidden_paths == ["/__ORMSRuntime"]


def test_stage_classification_reports_ordered_runtime_phases():
    stage, _mesh = _window_stage((1, 1, 2, 1, 1))
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()
    phases = []

    classify_stage(
        stage,
        runtime_layer,
        RuntimeClassifierSettings(),
        REPOSITORY_ROOT,
        phase_callback=lambda phase, details: phases.append(
            (phase, dict(details))
        ),
    )

    assert [phase for phase, _details in phases] == [
        "STAGE_EXTRACTION_COMPLETE",
        "CLASSIFICATION_COMPLETE",
        "RUNTIME_PRIMVARS_AUTHORED",
        "RUNTIME_MATERIALS_AUTHORED",
        "RUNTIME_BINDINGS_AUTHORED",
    ]
    assert phases[0][1]["aperture_count"] == 5
    assert phases[1][1]["mapping_count"] == 5
    assert phases[3][1]["material_count"] == 4
    assert phases[4][1]["subset_count"] == 2
    assert phases[4][1]["direct_mesh_binding_count"] == 0

    owner.detach()


def test_stage_classification_consumes_installation_neutral_resources():
    stage, _mesh = _window_stage((1, 1))
    source_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Building/Looks/RoomMap/Shader")
    )
    source_shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Set(
        Sdf.AssetPath("room_map.mdl")
    )
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()
    resources = RuntimeResources(
        mdl_source_asset="room_map.mdl",
        atlas_families=(
            RuntimeAtlasFamily(
                1,
                "packaged/debug/x1/room_map_debug.<UDIM>.png",
                8,
            ),
            RuntimeAtlasFamily(
                2,
                "licensed/pack/x2/room_map.<UDIM>.png",
                32,
            ),
        ),
    )

    classification = classify_stage(
        stage,
        runtime_layer,
        RuntimeClassifierSettings(),
        resources,
    )

    shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX2/Shader")
    )
    material = UsdShade.Material(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX2")
    )
    assert classification.available_room_sizes == frozenset({1, 2})
    assert material.GetPrim().HasAuthoredSpecializes()
    assert shader.GetInput("room_atlas").Get() == Sdf.AssetPath(
        "licensed/pack/x2/room_map.<UDIM>.png"
    )
    assert shader.GetInput("room_variant_count").Get() == 32
    assert not stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX3")
    assert not stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX4")

    owner.detach()


def test_one_pipeline_authors_independent_set_material_families():
    stage, _mesh = _window_stage((7, 7))
    root_layer = stage.GetRootLayer()
    Sdf.CopySpec(
        root_layer,
        Sdf.Path("/World/Building/Windows"),
        root_layer,
        Sdf.Path("/World/Building/Kitchens_Windows"),
    )
    kitchens_id = "11111111-1111-1111-1111-111111111111"
    default = InteriorSetConfig(
        set_id=DEFAULT_INTERIOR_SET_ID,
        name="Living Rooms",
        material_values=(("glass_roughness", 0.11),),
    )
    kitchens = InteriorSetConfig(
        set_id=kitchens_id,
        name="Kitchens",
        selectors=("*/Kitchens_Windows",),
        material_values=(("glass_roughness", 0.73),),
    )
    collection = InteriorSetCollection((default, kitchens))
    resources = RuntimeResources.from_repository(REPOSITORY_ROOT)
    runtime_snapshot = InteriorSetRuntimeSnapshot(
        tuple(
            InteriorSetRuntimeResources(item.set_id, resources)
            for item in collection.sets
        )
    )
    owner = RuntimeLayerOwner(stage)

    classification = classify_stage(
        stage,
        owner.attach(),
        RuntimeClassifierSettings(),
        resources,
        interior_sets=collection,
        interior_set_resources=runtime_snapshot,
    )

    resolutions = {
        item.prim_path: item for item in classification.selector_resolutions
    }
    assert (
        resolutions["/World/Building/Kitchens_Windows"].set_id == kitchens_id
    )
    assert resolutions["/World/Building/Windows"].used_default
    assert {
        group.interior_set_id for group in classification.result.groups
    } == {
        DEFAULT_INTERIOR_SET_ID,
        kitchens_id,
    }
    diagnostics = classification.interior_set_diagnostics
    assert diagnostics is not None
    assert diagnostics.active_set_count == 2
    assert diagnostics.default_fallback_paths == ("/World/Building/Windows",)
    assert diagnostics.variant_identities
    assert len(diagnostics.generated_material_paths) == 8
    assert dict(diagnostics.aperture_counts) == {
        DEFAULT_INTERIOR_SET_ID: 2,
        kitchens_id: 2,
    }
    roughness_by_set = {}
    for item in collection.sets:
        shader_path = (
            f"/__ORMSRuntime/Looks/{runtime_set_token(item.set_id)}/"
            "RoomMapX2/Shader"
        )
        shader = UsdShade.Shader(stage.GetPrimAtPath(shader_path))
        roughness_by_set[item.set_id] = shader.GetInput(
            "glass_roughness"
        ).Get()
    assert roughness_by_set[DEFAULT_INTERIOR_SET_ID] == pytest.approx(0.11)
    assert roughness_by_set[kitchens_id] == pytest.approx(0.73)
    expected_x1 = Sdf.AssetPath(resources.atlas_family(1).asset_path)
    for item in collection.sets:
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/{runtime_set_token(item.set_id)}/"
                "RoomMapX1/Shader"
            )
        )
        assert shader.GetInput("room_atlas").Get() == expected_x1


def test_explicit_default_only_preserves_legacy_visual_inputs():
    legacy_stage, _legacy_mesh = _window_stage((7, 7))
    explicit_stage, _explicit_mesh = _window_stage((7, 7))
    resources = RuntimeResources.from_repository(REPOSITORY_ROOT)
    default_only = InteriorSetCollection.default_only()
    runtime_snapshot = InteriorSetRuntimeSnapshot(
        (
            InteriorSetRuntimeResources(
                DEFAULT_INTERIOR_SET_ID,
                resources,
            ),
        )
    )
    legacy_owner = RuntimeLayerOwner(legacy_stage)
    explicit_owner = RuntimeLayerOwner(explicit_stage)

    legacy = classify_stage(
        legacy_stage,
        legacy_owner.attach(),
        RuntimeClassifierSettings(),
        resources,
    )
    explicit = classify_stage(
        explicit_stage,
        explicit_owner.attach(),
        RuntimeClassifierSettings(),
        resources,
        interior_sets=default_only,
        interior_set_resources=runtime_snapshot,
    )

    assert explicit.result == legacy.result
    legacy_shader = UsdShade.Shader(
        legacy_stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX2/Shader")
    )
    explicit_shader = UsdShade.Shader(
        explicit_stage.GetPrimAtPath(
            f"/__ORMSRuntime/Looks/{runtime_set_token(DEFAULT_INTERIOR_SET_ID)}/"
            "RoomMapX2/Shader"
        )
    )
    for input_name in (
        "room_atlas",
        "room_variant_count",
        "room_depth",
        "glass_roughness",
    ):
        assert explicit_shader.GetInput(input_name).Get() == (
            legacy_shader.GetInput(input_name).Get()
        )

    explicit_owner.detach()
    legacy_owner.detach()
