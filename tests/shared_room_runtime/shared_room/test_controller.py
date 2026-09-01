"""Protect runtime tracing, USD change routing, pose refresh, and teardown."""

import pytest
from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt

from tools.omniverse.shared_room import controller as classifier_module
from tools.omniverse.shared_room.controller import (
    DERIVED_PHYSICAL_NORMAL,
    DERIVED_ROOM_AXIS_U,
    DERIVED_ROOM_AXIS_V,
    DERIVED_ROOM_POSITION,
    RuntimeClassifierSettings,
    SharedRoomClassifier,
)

from ._support import REPOSITORY_ROOT, _window_stage


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
        "RUNTIME_LAYER_PUBLISHED",
        "SOURCE_USD_STATE_AFTER_AUTHORING",
        "MATERIAL_UPDATE_SUBMITTED",
        "MATERIAL_LOADING_COMPLETION_UNOBSERVABLE",
    ]
    assert len(callbacks) == 1
    assert classifier._first_frame_subscription is subscription
    material_record = next(
        record
        for record in records
        if record["state"] == "SOURCE_USD_STATE_AFTER_AUTHORING"
    )
    assert material_record["details"]["source_usd_state_unchanged"] is True
    assert (
        material_record["details"]["rendered_material_state_observable"]
        is False
    )
    publication_record = next(
        record
        for record in records
        if record["state"] == "RUNTIME_LAYER_PUBLISHED"
    )
    publication_details = publication_record["details"]
    assert publication_details["publication_mode"] == (
        "isolated_stage_atomic_layer_transfer"
    )
    assert publication_details["authoring_notice_count"] == 1
    assert (
        publication_details["source_material_dependency_notice_path_count"]
        == 0
    )
    assert (
        publication_details["runtime_authored_source_material_path_count"] == 0
    )
    run_ids = {record["details"]["run_id"] for record in records}
    assert len(run_ids) == 1
    assert all(
        record["details"]["diagnostic_code"] == "ORMS-RUNTIME-TRACE"
        for record in records
    )

    callbacks[0](object())

    assert records[-1]["state"] == "FIRST_FRAME_AFTER_MATERIAL_UPDATE"
    assert records[-1]["details"]["observation_signal"] == (
        "StageRenderingEventType.NEW_FRAME"
    )
    assert records[-1]["details"]["material_loading_complete"] is False
    assert records[-1]["details"]["source_usd_state_unchanged"] is True
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


def test_camera_and_building_pose_do_not_reclassify_but_geometry_does(
    monkeypatch,
):
    stage, mesh = _window_stage((1, 1))
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera_translate = camera.AddTranslateOp()
    camera_translate.Set(Gf.Vec3d(0.0, 0.0, 5.0))
    building = UsdGeom.Xform.Define(stage, "/World/Building")
    building_scale = building.AddScaleOp()
    building_scale.Set(Gf.Vec3d(1.0))
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
    camera_input = stage.GetAttributeAtPath(classifier.camera_input_paths[0])
    camera_input.Set(Gf.Vec3f(1.0, 2.0, 3.0))
    source_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Building/Looks/RoomMap/Shader")
    )
    source_shader.GetInput("window_aperture_scale").Set(Gf.Vec2f(0.5, 0.75))
    building_translate = building.AddTranslateOp()
    building_rotate = building.AddRotateYOp()
    building_translate.Set(Gf.Vec3d(100.0, 0.0, -25.0))
    building_rotate.Set(42.0)

    assert classification_calls == 1

    class BundledPoseNotice:
        @staticmethod
        def GetResyncedPaths():
            return tuple(
                Sdf.Path(f"/World/Building.{name}")
                for name in (
                    "xformOp:translate",
                    "xformOp:rotateY",
                    "xformOp:scale",
                    "xformOpOrder",
                )
            )

        @staticmethod
        def GetChangedInfoOnlyPaths():
            return ()

    classifier._on_objects_changed(BundledPoseNotice(), stage)

    assert classification_calls == 1
    local_to_world = UsdGeom.XformCache().GetLocalToWorldTransform(
        mesh.GetPrim()
    )
    primvars = UsdGeom.PrimvarsAPI(mesh)
    expected_position = local_to_world.Transform(Gf.Vec3d(0.5, 0.5, 0.0))
    expected_axis_u = local_to_world.TransformDir(
        Gf.Vec3d(1.0, 0.0, 0.0)
    ).GetNormalized()
    expected_axis_v = local_to_world.TransformDir(
        Gf.Vec3d(0.0, 1.0, 0.0)
    ).GetNormalized()
    expected_normal = (
        local_to_world.GetInverse()
        .GetTranspose()
        .TransformDir(Gf.Vec3d(0.0, 0.0, 1.0))
        .GetNormalized()
    )
    assert tuple(primvars.GetPrimvar(DERIVED_ROOM_POSITION).Get()[0]) == (
        pytest.approx(tuple(expected_position))
    )
    assert tuple(primvars.GetPrimvar(DERIVED_ROOM_AXIS_U).Get()[0]) == (
        pytest.approx(tuple(expected_axis_u))
    )
    assert tuple(primvars.GetPrimvar(DERIVED_ROOM_AXIS_V).Get()[0]) == (
        pytest.approx(tuple(expected_axis_v))
    )
    assert tuple(primvars.GetPrimvar(DERIVED_PHYSICAL_NORMAL).Get()[0]) == (
        pytest.approx(tuple(expected_normal))
    )

    building_scale.Set(Gf.Vec3d(1.1, 1.0, 1.0))

    assert classification_calls == 2

    moved_points = Vt.Vec3fArray(mesh.GetPointsAttr().Get())
    moved_points[0] += Gf.Vec3f(0.1, 0.0, 0.0)
    mesh.GetPointsAttr().Set(moved_points)

    assert classification_calls == 3

    classifier.stop()


def test_runtime_artist_controls_are_shared_across_atlas_families():
    stage, _mesh = _window_stage((1, 1))
    records = []
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
        trace_log_warning=lambda **record: records.append(record),
    )

    classifier.start()
    records.clear()

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

    sync_records = tuple(
        record
        for record in records
        if record["process"] == "RUNTIME MATERIAL INPUT SYNC"
    )
    assert sync_records[-1]["state"] == "SYNCHRONISED"
    transition = sync_records[-1]["details"]
    assert tuple(transition["previous_value"]) == pytest.approx((0.75, 0.5))
    assert tuple(transition["new_value"]) == pytest.approx((0.6, 0.4))

    records.clear()
    x3_shader.GetInput("glass_roughness").Set(0.25)

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert shader.GetInput("glass_roughness").Get() == pytest.approx(0.25)

    glass_sync_records = tuple(
        record
        for record in records
        if record["process"] == "RUNTIME MATERIAL INPUT SYNC"
    )
    glass_transition = glass_sync_records[-1]["details"]
    assert glass_sync_records[-1]["state"] == "SYNCHRONISED"
    assert glass_transition["input"] == "glass_roughness"
    assert glass_transition["previous_value"] == pytest.approx(0.1)
    assert glass_transition["new_value"] == pytest.approx(0.25)

    records.clear()
    x3_shader.GetInput("glass_reflectivity").Set(0.75)

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert shader.GetInput("glass_reflectivity").Get() == pytest.approx(
            0.75
        )

    reflectivity_records = tuple(
        record
        for record in records
        if record["process"] == "RUNTIME MATERIAL INPUT SYNC"
    )
    reflectivity_transition = reflectivity_records[-1]["details"]
    assert reflectivity_records[-1]["state"] == "SYNCHRONISED"
    assert reflectivity_transition["input"] == "glass_reflectivity"
    assert reflectivity_transition["previous_value"] == pytest.approx(0.04)
    assert reflectivity_transition["new_value"] == pytest.approx(0.75)

    records.clear()
    x3_shader.GetInput("enable_emission").Set(True)

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert shader.GetInput("enable_emission").Get() is True

    emission_records = tuple(
        record
        for record in records
        if record["process"] == "RUNTIME MATERIAL INPUT SYNC"
    )
    emission_transition = emission_records[-1]["details"]
    assert emission_records[-1]["state"] == "SYNCHRONISED"
    assert emission_transition["input"] == "enable_emission"
    assert emission_transition["previous_value"] is False
    assert emission_transition["new_value"] is True

    records.clear()
    x3_shader.GetInput("emission_slice_3").Set(False)

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert shader.GetInput("emission_slice_3").Get() is False

    slice_emission_records = tuple(
        record
        for record in records
        if record["process"] == "RUNTIME MATERIAL INPUT SYNC"
    )
    slice_emission_transition = slice_emission_records[-1]["details"]
    assert slice_emission_records[-1]["state"] == "SYNCHRONISED"
    assert slice_emission_transition["input"] == "emission_slice_3"
    assert slice_emission_transition["previous_value"] is True
    assert slice_emission_transition["new_value"] is False

    x1_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX1/Shader")
    )
    x1_atlas_before = x1_shader.GetInput("room_atlas").Get()
    x3_shader.GetInput("room_atlas").Set(Sdf.AssetPath("custom_x3.png"))

    assert x1_shader.GetInput("room_atlas").Get() == x1_atlas_before

    classifier.stop()


def test_runtime_artist_input_logs_coalesce_one_editing_gesture():
    stage, _mesh = _window_stage((1, 1))
    records = []
    scheduled_calls = []

    class ScheduledCall:
        def __init__(self, callback):
            self.callback = callback
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    def schedule(delay_seconds, callback):
        assert delay_seconds == pytest.approx(0.2)
        scheduled_call = ScheduledCall(callback)
        scheduled_calls.append(scheduled_call)
        return scheduled_call

    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
        trace_log_warning=lambda **record: records.append(record),
        runtime_input_log_scheduler=schedule,
    )
    classifier.start()
    records.clear()

    x1_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX1/Shader")
    )
    for value in (0.2, 0.3, 0.4):
        x1_shader.GetInput("glass_roughness").Set(value)

    for room_size in range(1, 5):
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert shader.GetInput("glass_roughness").Get() == pytest.approx(0.4)

    deferred_records = tuple(
        record for record in records if record["state"] == "DEFERRED"
    )
    assert len(deferred_records) == 1
    assert deferred_records[0]["details"]["reason"] == (
        "source_value_unavailable"
    )
    assert not any(record["state"] == "SYNCHRONISED" for record in records)
    assert len(scheduled_calls) == 3
    assert all(call.cancelled for call in scheduled_calls[:-1])
    assert not scheduled_calls[-1].cancelled

    scheduled_calls[-1].callback()

    synchronised_records = tuple(
        record for record in records if record["state"] == "SYNCHRONISED"
    )
    assert len(synchronised_records) == 1
    transition = synchronised_records[0]["details"]
    assert transition["input"] == "glass_roughness"
    assert transition["previous_value"] == pytest.approx(0.1)
    assert transition["new_value"] == pytest.approx(0.4)
    assert transition["coalesced_change_count"] == 3
    assert transition["coalescing_window_ms"] == 200

    records.clear()
    scheduled_calls.clear()
    x1_shader.GetInput("glass_roughness").Set(0.5)

    classifier.stop()

    assert scheduled_calls[-1].cancelled
    synchronised_records = tuple(
        record for record in records if record["state"] == "SYNCHRONISED"
    )
    assert len(synchronised_records) == 1
    transition = synchronised_records[0]["details"]
    assert transition["previous_value"] == pytest.approx(0.4)
    assert transition["new_value"] == pytest.approx(0.5)


def test_transient_missing_artist_value_is_deferred():
    stage, _mesh = _window_stage((1, 1))
    records = []
    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
        trace_log_warning=lambda **record: records.append(record),
    )
    classifier.start()
    source_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Building/Looks/RoomMap/Shader")
    )
    source_shader.GetPrim().RemoveProperty("inputs:window_aperture_scale")
    x2_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX2/Shader")
    )
    x2_shader.CreateInput(
        "window_aperture_scale",
        Sdf.ValueTypeNames.Float2,
    ).Set(Gf.Vec2f(0.75, 0.5))
    records.clear()

    transient_path = Sdf.Path(
        "/__ORMSRuntime/Looks/RoomMapX1/Shader" ".inputs:window_aperture_scale"
    )
    stage.OverridePrim(transient_path.GetPrimPath()).CreateAttribute(
        transient_path.name,
        Sdf.ValueTypeNames.Float2,
        custom=False,
    )

    assert tuple(x2_shader.GetInput("window_aperture_scale").Get()) == (
        0.75,
        0.5,
    )
    sync_records = tuple(
        record
        for record in records
        if record["process"] == "RUNTIME MATERIAL INPUT SYNC"
    )
    assert sync_records[-1]["state"] == "DEFERRED"
    assert sync_records[-1]["details"]["reason"] == (
        "source_value_unavailable"
    )
    assert tuple(sync_records[-1]["details"]["previous_value"]) == (
        0.75,
        0.5,
    )
    assert sync_records[-1]["details"]["new_value"] is None
    assert not any(
        record["state"] == "SYNCHRONISED" for record in sync_records
    )

    classifier.stop()
