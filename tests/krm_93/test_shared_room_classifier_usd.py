from pathlib import Path

import pytest
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

from tools.omniverse import reload_room_map_runtime
from tools.omniverse import room_run_classifier as core_classifier_module
from tools.omniverse import shared_room_classifier as classifier_module
from tools.omniverse.room_run_classifier import classify_apertures
from tools.omniverse.shared_room_classifier import (
    DERIVED_APERTURE_MASK_OFFSET_U,
    DERIVED_MAP_AXIS_U,
    DERIVED_MAP_POSITION,
    DERIVED_MAPPING_VALID,
    DERIVED_PRIMARY_APERTURE_MAX_U,
    DERIVED_PRIMARY_APERTURE_MIN_U,
    DERIVED_ROOM_DEPTH_SIZE,
    DERIVED_ROOM_GROUP_ID,
    DERIVED_ROOM_PARAMETERS,
    DERIVED_ROOM_SIZE,
    DERIVED_SLICE_START_DEPTH,
    INSTANCE_POLICY_SESSION_DEINSTANCE,
    METRICS_MODE_LOCAL_OVERRIDE,
    RuntimeClassifierSettings,
    RuntimeLayerOwner,
    SharedRoomClassifier,
    _is_relevant_change,
    author_derived_primvars,
    classify_stage,
    discover_atlas_family_availability,
    extract_stage_apertures,
    resolve_stage_metrics,
    settings_from_mapping,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MDL_PATH = REPOSITORY_ROOT / "src" / "mdl" / "room_map.mdl"


def test_runtime_contract_versions_are_synchronised():
    versions = {
        core_classifier_module.CLASSIFIER_CONTRACT_VERSION,
        classifier_module._EXPECTED_CLASSIFIER_CONTRACT_VERSION,
        reload_room_map_runtime._CONTRACT_VERSION,
    }
    assert versions == {"krm93_exact_corner_mask_origin_v15"}


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


def test_auto_metrics_use_authored_stage_values_without_mutation():
    stage, _ = _window_stage()
    root_before = stage.GetRootLayer().ExportToString()

    metrics = resolve_stage_metrics(stage, RuntimeClassifierSettings())

    assert metrics.up_axis == "Y"
    assert metrics.meters_per_unit == pytest.approx(1.0)
    assert not metrics.diagnostics
    assert stage.GetRootLayer().ExportToString() == root_before


def test_missing_metrics_and_conflicting_local_override_are_diagnostic_only():
    missing_stage = Usd.Stage.CreateInMemory()
    missing_before = missing_stage.GetRootLayer().ExportToString()
    missing = resolve_stage_metrics(missing_stage, RuntimeClassifierSettings())

    stage, _ = _window_stage()
    override = resolve_stage_metrics(
        stage,
        RuntimeClassifierSettings(
            metrics_mode=METRICS_MODE_LOCAL_OVERRIDE,
            local_up_axis="Z",
            local_meters_per_unit=0.01,
        ),
    )

    assert (missing.up_axis, missing.meters_per_unit) == ("Y", 1.0)
    assert missing.diagnostics[0].state == "MISSING_OR_INVALID_STAGE_METRICS"
    assert missing_stage.GetRootLayer().ExportToString() == missing_before
    assert (override.up_axis, override.meters_per_unit) == ("Z", 0.01)
    assert override.diagnostics[0].state == "LOCAL_STAGE_METRICS_OVERRIDE"


def test_session_sublayer_owns_only_derived_primvars_and_is_reversible():
    stage, mesh = _window_stage()
    root_before = stage.GetRootLayer().ExportToString()
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        mesh.GetPrim().CreateAttribute(
            "user:keep", Sdf.ValueTypeNames.String
        ).Set("unrelated session edit")

    settings = RuntimeClassifierSettings()
    metrics = resolve_stage_metrics(stage, settings)
    extraction = extract_stage_apertures(stage, metrics)
    result = classify_apertures(
        extraction.apertures,
        settings.core_settings(frozenset({1, 2, 3, 4})),
        up_axis=metrics.up_axis,
    )
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()

    culling_diagnostics = author_derived_primvars(
        stage,
        runtime_layer,
        extraction,
        result,
    )

    primvars = UsdGeom.PrimvarsAPI(mesh)
    assert tuple(primvars.GetPrimvar(DERIVED_ROOM_SIZE).Get()) == (
        2,
        2,
        1,
        2,
        2,
    )
    assert (
        tuple(primvars.GetPrimvar(DERIVED_ROOM_DEPTH_SIZE).Get()) == (1,) * 5
    )
    assert tuple(primvars.GetPrimvar(DERIVED_MAPPING_VALID).Get()) == (1,) * 5
    group_ids = tuple(primvars.GetPrimvar(DERIVED_ROOM_GROUP_ID).Get())
    assert group_ids[0] == group_ids[1]
    assert group_ids[3] == group_ids[4]
    assert group_ids[0] != group_ids[3]
    assert len(primvars.GetPrimvar(DERIVED_MAP_AXIS_U).Get()) == 5
    primary_minimums = primvars.GetPrimvar(DERIVED_PRIMARY_APERTURE_MIN_U)
    primary_maximums = primvars.GetPrimvar(DERIVED_PRIMARY_APERTURE_MAX_U)
    assert primary_minimums.GetTypeName() == Sdf.ValueTypeNames.Float4Array
    assert primary_maximums.GetTypeName() == Sdf.ValueTypeNames.Float4Array
    assert primary_minimums.GetInterpolation() == UsdGeom.Tokens.uniform
    assert primary_maximums.GetInterpolation() == UsdGeom.Tokens.uniform
    expected_minimums = (
        (0.0, 1.1 / 2.1, -1.0, -1.0),
        (0.0, 1.1 / 2.1, -1.0, -1.0),
        (0.0, -1.0, -1.0, -1.0),
        (0.0, 1.1 / 2.1, -1.0, -1.0),
        (0.0, 1.1 / 2.1, -1.0, -1.0),
    )
    expected_maximums = (
        (1.0 / 2.1, 1.0, -1.0, -1.0),
        (1.0 / 2.1, 1.0, -1.0, -1.0),
        (1.0, -1.0, -1.0, -1.0),
        (1.0 / 2.1, 1.0, -1.0, -1.0),
        (1.0 / 2.1, 1.0, -1.0, -1.0),
    )
    for authored, expected in zip(
        primary_minimums.Get(),
        expected_minimums,
        strict=True,
    ):
        assert tuple(authored) == pytest.approx(expected)
    for authored, expected in zip(
        primary_maximums.Get(),
        expected_maximums,
        strict=True,
    ):
        assert tuple(authored) == pytest.approx(expected)
    slice_start_primvar = primvars.GetPrimvar(DERIVED_SLICE_START_DEPTH)
    assert slice_start_primvar.GetTypeName() == Sdf.ValueTypeNames.FloatArray
    assert slice_start_primvar.GetInterpolation() == UsdGeom.Tokens.uniform
    assert tuple(slice_start_primvar.Get()) == (0.0,) * 5
    mask_offset_primvar = primvars.GetPrimvar(DERIVED_APERTURE_MASK_OFFSET_U)
    assert mask_offset_primvar.GetTypeName() == Sdf.ValueTypeNames.FloatArray
    assert mask_offset_primvar.GetInterpolation() == UsdGeom.Tokens.uniform
    assert tuple(mask_offset_primvar.Get()) == (0.0,) * 5
    room_parameters = primvars.GetPrimvar(DERIVED_ROOM_PARAMETERS)
    assert room_parameters.GetTypeName() == Sdf.ValueTypeNames.Float3Array
    assert room_parameters.GetInterpolation() == UsdGeom.Tokens.uniform
    assert tuple(tuple(value) for value in room_parameters.Get()) == (
        (21.0, 0.0, 1.0),
        (21.0, 0.0, 1.0),
        (11.0, 0.0, 1.0),
        (21.0, 0.0, 1.0),
        (21.0, 0.0, 1.0),
    )
    map_position = primvars.GetPrimvar(DERIVED_MAP_POSITION)
    assert map_position.GetTypeName() == Sdf.ValueTypeNames.Float3Array
    assert map_position.GetInterpolation() == UsdGeom.Tokens.faceVarying
    authored_positions = tuple(tuple(value) for value in map_position.Get())
    mappings_by_face = {
        mapping.face_index: mapping for mapping in result.mappings
    }
    source_room_uv = tuple(
        tuple(value)
        for value in primvars.GetPrimvar("roomUV").ComputeFlattened()
    )
    expected_positions = []
    for face_index in range(5):
        mapping = mappings_by_face[face_index]
        for room_uv in source_room_uv[face_index * 4 : face_index * 4 + 4]:
            expected_positions.append(
                tuple(
                    mapping.map_origin[axis]
                    + mapping.map_axis_u[axis] * room_uv[0]
                    + mapping.map_axis_v[axis] * room_uv[1]
                    for axis in range(3)
                )
            )
    for authored, expected in zip(
        authored_positions,
        expected_positions,
        strict=True,
    ):
        assert authored == pytest.approx(expected)
    assert not culling_diagnostics
    assert mesh.GetDoubleSidedAttr().HasAuthoredValueOpinion()
    assert mesh.GetDoubleSidedAttr().Get() is False
    assert mesh.GetOrientationAttr().HasAuthoredValueOpinion()
    assert mesh.GetOrientationAttr().Get() == UsdGeom.Tokens.rightHanded
    assert runtime_layer.identifier in stage.GetSessionLayer().subLayerPaths
    assert stage.GetRootLayer().ExportToString() == root_before

    owner.detach()

    assert (
        runtime_layer.identifier not in stage.GetSessionLayer().subLayerPaths
    )
    assert not UsdGeom.PrimvarsAPI(mesh).GetPrimvar(DERIVED_ROOM_SIZE)
    assert not mesh.GetDoubleSidedAttr().HasAuthoredValueOpinion()
    assert not mesh.GetOrientationAttr().HasAuthoredValueOpinion()
    assert (
        mesh.GetPrim().GetAttribute("user:keep").Get()
        == "unrelated session edit"
    )
    assert stage.GetRootLayer().ExportToString() == root_before


def test_mixed_mesh_winding_skips_runtime_backface_culling():
    stage, mesh = _window_stage((1, 1))
    indices = list(mesh.GetFaceVertexIndicesAttr().Get())
    indices[4:8] = reversed(indices[4:8])
    mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(indices))
    settings = RuntimeClassifierSettings()
    metrics = resolve_stage_metrics(stage, settings)
    extraction = extract_stage_apertures(stage, metrics)
    result = classify_apertures(
        extraction.apertures,
        settings.core_settings(frozenset({1, 2, 3, 4})),
        up_axis=metrics.up_axis,
    )
    owner = RuntimeLayerOwner(stage)

    diagnostics = author_derived_primvars(
        stage,
        owner.attach(),
        extraction,
        result,
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].state == "ROOM_MAP_BACKFACE_CULLING_SKIPPED"
    assert dict(diagnostics[0].details)["reason"] == "mixed_face_winding"
    assert not mesh.GetDoubleSidedAttr().HasAuthoredValueOpinion()
    assert not mesh.GetOrientationAttr().HasAuthoredValueOpinion()


def test_rtx_face_culling_setting_is_owned_and_restored(monkeypatch):
    class FakeSettings:
        def __init__(self):
            self.values = {
                classifier_module._RTX_FACE_CULLING_SETTING: False,
            }

        def get(self, path):
            return self.values[path]

        def set(self, path, value):
            self.values[path] = value

    fake_settings = FakeSettings()
    monkeypatch.setattr(
        classifier_module,
        "log_room_map_warning",
        lambda **_kwargs: None,
    )
    classifier_module._previous_rtx_face_culling = None
    classifier_module._owns_rtx_face_culling_setting = False

    classifier_module._enable_rtx_single_sided_culling(fake_settings)

    assert fake_settings.values[classifier_module._RTX_FACE_CULLING_SETTING]
    assert classifier_module._owns_rtx_face_culling_setting

    classifier_module._restore_rtx_single_sided_culling(fake_settings)

    assert not fake_settings.values[
        classifier_module._RTX_FACE_CULLING_SETTING
    ]
    assert classifier_module._previous_rtx_face_culling is None
    assert not classifier_module._owns_rtx_face_culling_setting


def test_extraction_converts_stage_units_to_metres():
    stage, _ = _window_stage((1,))
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    metrics = resolve_stage_metrics(stage, RuntimeClassifierSettings())

    extraction = extract_stage_apertures(stage, metrics)
    aperture = extraction.apertures[0]

    assert aperture.centre_metres == pytest.approx((0.005, 0.005, 0.0))
    assert aperture.tangent_u_metres == pytest.approx((0.01, 0.0, 0.0))
    assert aperture.tangent_v_metres == pytest.approx((0.0, 0.01, 0.0))


def test_all_four_repository_atlas_families_are_complete():
    assert discover_atlas_family_availability(REPOSITORY_ROOT) == frozenset(
        {1, 2, 3, 4}
    )


def test_preferences_labels_resolve_to_runtime_policy_tokens():
    settings = settings_from_mapping(
        {
            "instance_policy": "Session de-instance",
            "metrics_mode": "Local override",
            "local_up_axis": "Z",
            "local_meters_per_unit": 0.01,
            "corner_turn_threshold_degrees": 72.0,
        }
    )

    assert settings.instance_policy == INSTANCE_POLICY_SESSION_DEINSTANCE
    assert settings.metrics_mode == METRICS_MODE_LOCAL_OVERRIDE
    assert settings.local_up_axis == "Z"
    assert settings.local_meters_per_unit == pytest.approx(0.01)
    assert settings.corner_turn_threshold_degrees == pytest.approx(72.0)


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


def test_runtime_trace_does_not_claim_material_completion(
    monkeypatch,
):
    stage, mesh = _window_stage((1, 1, 2, 1, 1))
    callbacks = []
    records = []
    subscription = object()

    def subscribe(callback):
        callbacks.append(callback)
        return subscription

    monkeypatch.setattr(
        classifier_module,
        "_subscribe_to_next_rendered_frame",
        subscribe,
    )
    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
        trace_log_warning=lambda **record: records.append(record),
    )

    classifier.start()

    states = [record["state"] for record in records]
    assert states == [
        "RUNTIME_RUN_BEGIN",
        "STAGE_EXTRACTION_COMPLETE",
        "CLASSIFICATION_COMPLETE",
        "RUNTIME_PRIMVARS_AUTHORED",
        "RUNTIME_MATERIALS_AUTHORED",
        "RUNTIME_BINDINGS_AUTHORED",
        "MATERIAL_UPDATE_SUBMITTED",
        "MATERIAL_LOADING_COMPLETION_UNOBSERVABLE",
    ]
    assert len(callbacks) == 1
    assert classifier._first_frame_subscription is subscription
    run_ids = {record["details"]["run_id"] for record in records}
    assert len(run_ids) == 1
    assert all(
        record["details"]["diagnostic_code"] == "ORMS-KRM93-TRACE"
        for record in records
    )

    callbacks[0](object())

    assert records[-1]["state"] == "FIRST_FRAME_AFTER_MATERIAL_UPDATE"
    assert records[-1]["details"]["observation_signal"] == (
        "StageRenderingEventType.NEW_FRAME"
    )
    assert records[-1]["details"]["material_loading_complete"] is False
    assert records[-1]["details"]["run_id"] in run_ids
    assert classifier._first_frame_subscription is None

    moved_points = Vt.Vec3fArray(mesh.GetPointsAttr().Get())
    moved_points[0] += Gf.Vec3f(0.1, 0.0, 0.0)
    mesh.GetPointsAttr().Set(moved_points)

    usd_change_begin = next(
        record
        for record in records
        if record["state"] == "RUNTIME_RUN_BEGIN"
        and record["details"]["trigger"] == "usd_change"
    )
    change_details = usd_change_begin["details"]
    assert change_details["resynced_path_count"] == 0
    assert change_details["resynced_paths"] == "<none>"
    assert change_details["changed_info_path_count"] == 1
    assert change_details["changed_info_paths"] == (
        "/World/Building/Windows.points"
    )
    assert change_details["relevant_path_count"] == 1
    assert change_details["relevant_paths"] == (
        "/World/Building/Windows.points"
    )
    assert change_details["paths_truncated"] is False

    classifier.stop()


def test_change_filter_excludes_camera_runtime_and_artist_inputs():
    stage, _mesh = _window_stage((1,))
    UsdGeom.Camera.Define(stage, "/World/Camera")
    geometry_ancestors = frozenset(
        {
            "/World",
            "/World/Building",
            "/World/Building/Windows",
        }
    )

    for path in (
        "/World/Camera.xformOp:transform",
        "/World/Building/Looks/RoomMap/Shader.inputs:camera_position_world",
        "/World/Building/Looks/RoomMap/Shader.inputs:window_aperture_scale",
        "/__ORMSRuntime/Looks/RoomMapX2/Shader.inputs:room_atlas",
        "/__ORMSRuntime/Looks/RoomMapX2/Shader.outputs:out",
    ):
        assert not _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
        )

    for path in (
        "/World/Building.xformOp:translate",
        "/World/Building/Windows.points",
        "/World/Building/Windows.primvars:roomID",
        "/World/Building/Windows.material:binding",
    ):
        assert _is_relevant_change(
            stage,
            Sdf.Path(path),
            geometry_ancestors,
        )

    assert not _is_relevant_change(
        stage,
        Sdf.Path("/World/Building/Windows.primvars:ormsRoomSize"),
        geometry_ancestors,
    )
    assert _is_relevant_change(
        stage,
        Sdf.Path("/World/Building"),
        geometry_ancestors,
        resynced=True,
    )
    assert not _is_relevant_change(
        stage,
        Sdf.Path("/World/Building"),
        geometry_ancestors,
        resynced=False,
    )


def test_info_only_input_ancestors_do_not_reclassify(
    monkeypatch,
):
    stage, _mesh = _window_stage((1, 1))
    original_classify_stage = classifier_module.classify_stage
    classification_calls = 0

    def tracked_classify_stage(*args, **kwargs):
        nonlocal classification_calls
        classification_calls += 1
        return original_classify_stage(*args, **kwargs)

    class InputNotice:
        @staticmethod
        def GetResyncedPaths():
            return (
                Sdf.Path(
                    "/World/Building/Looks/RoomMap/Shader"
                    ".inputs:camera_position_world"
                ),
            )

        @staticmethod
        def GetChangedInfoOnlyPaths():
            return (
                Sdf.Path("/World"),
                Sdf.Path("/World/Building"),
                Sdf.Path("/World/Building/Looks"),
            )

    monkeypatch.setattr(
        classifier_module,
        "classify_stage",
        tracked_classify_stage,
    )
    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
    )
    classifier.start()

    classifier._on_objects_changed(InputNotice(), stage)

    assert classification_calls == 1

    classifier.stop()


def test_camera_motion_does_not_reclassify_but_geometry_motion_does(
    monkeypatch,
):
    stage, mesh = _window_stage((1, 1))
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera_translate = camera.AddTranslateOp()
    camera_translate.Set(Gf.Vec3d(0.0, 0.0, 5.0))
    original_classify_stage = classifier_module.classify_stage
    classification_calls = 0

    def tracked_classify_stage(*args, **kwargs):
        nonlocal classification_calls
        classification_calls += 1
        return original_classify_stage(*args, **kwargs)

    monkeypatch.setattr(
        classifier_module,
        "classify_stage",
        tracked_classify_stage,
    )
    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
    )
    classifier.start()

    assert classification_calls == 1

    camera_translate.Set(Gf.Vec3d(1.0, 0.0, 5.0))
    source_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Building/Looks/RoomMap/Shader")
    )
    source_shader.GetInput("window_aperture_scale").Set(Gf.Vec2f(0.5, 0.75))

    assert classification_calls == 1

    moved_points = Vt.Vec3fArray(mesh.GetPointsAttr().Get())
    moved_points[0] += Gf.Vec3f(0.1, 0.0, 0.0)
    mesh.GetPointsAttr().Set(moved_points)

    assert classification_calls == 2

    classifier.stop()


def test_runtime_artist_controls_are_shared_across_atlas_families():
    stage, _mesh = _window_stage((1, 1))
    source_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Building/Looks/RoomMap/Shader")
    )
    source_shader.GetPrim().RemoveProperty("inputs:window_aperture_scale")
    saved_scale_path = Sdf.Path(
        "/__ORMSRuntime/Looks/RoomMapX2/Shader.inputs:window_aperture_scale"
    )
    saved_shader = stage.OverridePrim(saved_scale_path.GetPrimPath())
    saved_shader.CreateAttribute(
        saved_scale_path.name,
        Sdf.ValueTypeNames.Float2,
        custom=False,
    ).Set(Gf.Vec2f(0.75, 0.5))
    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
    )

    classifier.start()

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert tuple(shader.GetInput("window_aperture_scale").Get()) == (
            0.75,
            0.5,
        )

    x3_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX3/Shader")
    )
    x3_shader.GetInput("window_aperture_scale").Set(Gf.Vec2f(0.6, 0.4))

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert tuple(shader.GetInput("window_aperture_scale").Get()) == (
            pytest.approx((0.6, 0.4))
        )

    x1_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX1/Shader")
    )
    x1_atlas_before = x1_shader.GetInput("room_atlas").Get()
    x3_shader.GetInput("room_atlas").Set(Sdf.AssetPath("custom_x3.png"))

    assert x1_shader.GetInput("room_atlas").Get() == x1_atlas_before

    classifier.stop()


def _instance_stage():
    asset_stage, _ = _window_stage((6, 6))
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


def test_preserve_keeps_instances_and_reports_x1_fallback():
    stage, _asset_stage, instances = _instance_stage()
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()

    classification = classify_stage(
        stage,
        runtime_layer,
        RuntimeClassifierSettings(),
        REPOSITORY_ROOT,
    )

    assert all(prim.IsInstance() for prim in instances)
    assert not classification.extraction.apertures
    assert {
        diagnostic.state
        for diagnostic in classification.extraction.diagnostics
    } == {"INSTANCE_PRESERVED_X1_FALLBACK"}

    owner.detach()

    assert all(prim.IsInstance() for prim in instances)


def test_session_deinstance_is_ephemeral_and_classifies_each_reference():
    stage, _asset_stage, instances = _instance_stage()
    root_before = stage.GetRootLayer().ExportToString()
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()
    settings = RuntimeClassifierSettings(
        instance_policy=INSTANCE_POLICY_SESSION_DEINSTANCE
    )

    classification = classify_stage(
        stage,
        runtime_layer,
        settings,
        REPOSITORY_ROOT,
    )

    assert not any(prim.IsInstance() for prim in instances)
    assert len(classification.extraction.apertures) == 4
    assert [group.room_size for group in classification.result.groups] == [
        2,
        2,
    ]
    assert {
        diagnostic.state
        for diagnostic in classification.extraction.diagnostics
    } == {"SESSION_DEINSTANCE_ACTIVE"}
    assert stage.GetRootLayer().ExportToString() == root_before

    owner.detach()

    assert all(prim.IsInstance() for prim in instances)
    assert stage.GetRootLayer().ExportToString() == root_before


def test_mdl_consumes_direct_shared_mapping_with_the_existing_lookup_budget():
    source = MDL_PATH.read_text(encoding="utf-8")

    for primvar_name in (
        "ormsRoomParameters",
        "ormsRoomAxisU",
        "ormsRoomAxisV",
        "ormsRoomScale",
        "ormsRoomMapPosition",
    ):
        assert f'"{primvar_name}"' in source

    assert "float3 shared_aperture_position(" in source
    assert '"ormsRoomScale"' in source
    assert "ray_vector_room * safe_room_scale" in source
    assert (
        "float3 scaled_position = physical_position * room_scale * room_extent"
        in source
    )
    assert "bool depth_aligned_portal =" in source
    assert (
        "float front_position_x = scaled_position.x * aperture_scale.x"
        in source
    )
    assert "float side_position_z =" in source
    assert "? float3(" in source
    assert "scaled_position.x + 0.5 * room_width" in source
    assert (
        "safe_room_width = safe_room_extent * float(active_room_size)"
        in source
    )
    assert "float(active_room_depth_size)" in source
    assert "float3 ray_origin = shared_ray_origin;" in source
    assert "scaled_position.z" in source
    assert "math::max(derived_slice_start_depth, 0.0)" in source
    assert "float slice_start_depth = bay_extension_depth" in source
    assert (
        "safe_room_depth = base_room_depth + bay_extension_depth" not in source
    )
    assert "float slice_depth_span = base_room_depth" in source
    assert "float throat_projection_distance = has_bay_extension" in source
    assert "bool throat_entry_is_valid = has_bay_extension" in source
    assert "safe_room_front_depth + safe_room_depth" in source
    assert "float full_depth_coordinate = saturate(" in source
    assert "float ceiling_distance = positive_plane_distance(" in source
    assert "candidate_ceiling_distance" not in source
    assert "left_hit_is_in_full_depth" not in source
    assert "float3 trace_room_cross(" in source
    assert (
        "float3 hit_point = ray_origin + hit_distance * ray_direction"
        in source
    )
    assert "float3 room_trace = trace_room_cross(" in source
    assert "float room_hit_distance = room_trace.z" in source
    assert "slice_depth_span * saturate(slice_1_depth_percent" in source
    assert "bool slice_depth_range_is_valid" in source
    assert "float2 aperture_uv = aperture_coordinate(" not in source
    assert source.count("tex::lookup_float4(") == 5


def test_mdl_uses_binary_physical_and_corner_front_exit_cutouts():
    source = MDL_PATH.read_text(encoding="utf-8")

    assert "bool point_is_in_room_depth(" not in source
    assert "bool back_hit_is_in_room_extent =" not in source
    assert "candidate_back_distance" not in source
    assert "physical_aperture_tangent_u_world" not in source
    assert "float physical_aperture_cutout_opacity(" in source
    assert "state::geometry_normal()" in source
    assert "state::transform_normal(" in source
    assert "float3 physical_aperture_normal_world" in source
    assert "bool facing_input_is_valid" in source
    assert "!facing_input_is_valid || facing_cosine" in source
    assert "? 1.0\n    : 0.0;" in source
    assert "float physical_surface_cutout_opacity =" in source
    assert "bool front_exit_ray_is_valid = depth_aligned_portal" in source
    assert "float3 aperture_mask_scaled_position =" in source
    assert '"ormsApertureMaskOffsetU"' in source
    assert "float3(aperture_mask_offset_u, 0.0, 0.0)" in source
    assert "float3 aperture_mask_ray_origin = float3(" in source
    assert "aperture_mask_scaled_position.z" in source
    assert "aperture_mask_ray_origin.z" in source
    assert "aperture_mask_ray_origin + front_exit_distance" in source
    assert "float front_exit_distance =" in source
    assert "bool front_exit_is_open =" in source
    assert "front_exit_distance < room_hit_distance" not in source
    assert source.count("data_lookup_float4(") == 2
    assert '"ormsPrimaryApertureMinU"' in source
    assert '"ormsPrimaryApertureMaxU"' in source
    assert "int primary_aperture_count = math::max(" not in source
    assert "bool coordinate_is_in_primary_aperture_intervals(" in source
    assert "float mullion_half_width = 0.035" not in source
    assert (
        "bool front_exit_hits_primary_aperture = front_exit_is_open" in source
    )
    assert source.count("coordinate_is_in_primary_aperture_intervals(") == 2
    assert source.count("<= room_hit_distance") == 4
    assert "visible_room_limit_distance" not in source
    assert "float virtual_front_cutout_opacity =" in source
    assert "bool front_exit_has_slice_surface" not in source
    assert (
        "float room_cutout_opacity = physical_surface_cutout_opacity" in source
    )
    assert "* virtual_front_cutout_opacity" in source
    assert (
        "color composited_room_colour = front_exit_hits_primary_aperture"
        in source
    )
    assert "thin_walled: true" not in source
    assert "mode: df::scatter_transmit" not in source
    assert "scattering: df::diffuse_reflection_bsdf(" in source
    assert "intensity: composited_room_colour * emission_strength" in source
    assert "geometry: material_geometry(" in source
    assert "cutout_opacity: room_cutout_opacity" in source
    assert source.count("tex::lookup_float4(") == 5
