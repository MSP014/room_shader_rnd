"""Protect ordered stage classification and bounded material-family authoring."""

from pxr import Gf, UsdGeom, UsdShade

from tools.omniverse.shared_room.authoring import RuntimeLayerOwner
from tools.omniverse.shared_room.contracts import RuntimeClassifierSettings
from tools.omniverse.shared_room.pipeline import classify_stage

from ._support import REPOSITORY_ROOT, _window_stage


def test_stage_classification_reuses_four_family_materials_and_face_subsets():
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
    assert phases[4][1]["subset_count"] == 3

    owner.detach()
