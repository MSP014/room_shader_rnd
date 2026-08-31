"""Protect runtime tracing, USD change routing, pose refresh, and teardown."""

import pytest
from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt

from tools.omniverse.shared_room import controller as classifier_module
from tools.omniverse.shared_room.controller import (
    CAMERA_POSITION_PRIMVAR_NAME,
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
        "MATERIAL_UPDATE_SUBMITTED",
        "MATERIAL_LOADING_COMPLETION_UNOBSERVABLE",
    ]
    assert len(callbacks) == 1
    assert classifier._first_frame_subscription is subscription
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
    camera_position_primvar = UsdGeom.PrimvarsAPI(
        stage.GetPrimAtPath("/World")
    ).GetPrimvar(CAMERA_POSITION_PRIMVAR_NAME)
    camera_position_primvar.Set(Gf.Vec3f(1.0, 2.0, 3.0))
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
