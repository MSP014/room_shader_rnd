# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect reversible Session Layer authoring, instances, and pose primvars."""

import pytest
from msp.orms.classification.classifier import classify_apertures
from msp.orms.shared_room import authoring as authoring_module
from msp.orms.shared_room.authoring import (
    RuntimeLayerOwner,
    author_derived_primvars,
    seed_camera_position_primvar,
)
from msp.orms.shared_room.contracts import (
    CAMERA_POSITION_PRIMVAR_NAME,
    DERIVED_APERTURE_MASK_OFFSET_U,
    DERIVED_MAP_AXIS_U,
    DERIVED_MAP_POSITION,
    DERIVED_MAPPING_VALID,
    DERIVED_PHYSICAL_NORMAL,
    DERIVED_PRIMARY_APERTURE_MAX_U_012,
    DERIVED_PRIMARY_APERTURE_MIN_U_012,
    DERIVED_PRIMARY_APERTURE_U_3,
    DERIVED_ROOM_AXIS_U,
    DERIVED_ROOM_AXIS_V,
    DERIVED_ROOM_DEPTH_SIZE,
    DERIVED_ROOM_GROUP_ID,
    DERIVED_ROOM_PARAMETERS,
    DERIVED_ROOM_POSITION,
    DERIVED_ROOM_SIZE,
    DERIVED_SLICE_START_DEPTH,
    INSTANCE_POLICY_SESSION_DEINSTANCE,
    RuntimeClassifierSettings,
)
from msp.orms.shared_room.pipeline import classify_stage
from msp.orms.shared_room.stage import (
    extract_stage_apertures,
    resolve_stage_metrics,
)
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, Vt

from ._support import (
    REPOSITORY_ROOT,
    _instance_stage,
    _window_stage,
)


def test_finished_runtime_layer_is_published_as_one_live_stage_change():
    stage, mesh = _window_stage((1,))
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        mesh.GetPrim().CreateAttribute(
            "user:keep", Sdf.ValueTypeNames.String
        ).Set("unrelated session edit")
    owner = RuntimeLayerOwner(stage)
    authoring_stage, draft_layer = owner.prepare_replacement()
    with Usd.EditContext(authoring_stage, draft_layer):
        draft_prim = UsdGeom.Scope.Define(
            authoring_stage,
            "/__ORMSRuntime",
        ).GetPrim()
        draft_prim.CreateAttribute("test:first", Sdf.ValueTypeNames.Int).Set(1)

    assert not stage.GetPrimAtPath("/__ORMSRuntime")
    assert (
        authoring_stage.GetPrimAtPath("/World/Building/Windows")
        .GetAttribute("user:keep")
        .Get()
        == "unrelated session edit"
    )

    notices = []
    notice_key = Tf.Notice.Register(
        Usd.Notice.ObjectsChanged,
        lambda notice, _sender: notices.append(notice),
        stage,
    )
    owner.publish(draft_layer)
    notice_key.Revoke()

    assert len(notices) == 1
    assert (
        stage.GetPrimAtPath("/__ORMSRuntime").GetAttribute("test:first").Get()
        == 1
    )

    replacement_stage, replacement_layer = owner.prepare_replacement()
    assert not replacement_stage.GetPrimAtPath("/__ORMSRuntime")
    with Usd.EditContext(replacement_stage, replacement_layer):
        replacement_prim = UsdGeom.Scope.Define(
            replacement_stage,
            "/__ORMSRuntime",
        ).GetPrim()
        replacement_prim.CreateAttribute(
            "test:second", Sdf.ValueTypeNames.Int
        ).Set(2)
    owner.publish(replacement_layer)

    runtime_prim = stage.GetPrimAtPath("/__ORMSRuntime")
    assert not runtime_prim.GetAttribute("test:first")
    assert runtime_prim.GetAttribute("test:second").Get() == 2
    assert (
        mesh.GetPrim().GetAttribute("user:keep").Get()
        == "unrelated session edit"
    )


def test_seeded_camera_primvar_survives_runtime_primvar_authoring():
    stage, _mesh = _window_stage((1,))
    owner = RuntimeLayerOwner(stage)
    runtime_layer = owner.attach()
    expected = (4.0, 5.0, 6.0)

    path = seed_camera_position_primvar(stage, expected)
    authored_path = authoring_module.author_camera_position_primvar(
        stage,
        runtime_layer,
    )
    primvar = UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World")).GetPrimvar(
        CAMERA_POSITION_PRIMVAR_NAME
    )

    assert path == authored_path
    assert tuple(primvar.Get()) == expected


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
    physical_normals = primvars.GetPrimvar(DERIVED_PHYSICAL_NORMAL)
    assert physical_normals.GetTypeName() == Sdf.ValueTypeNames.Float3Array
    assert physical_normals.GetInterpolation() == UsdGeom.Tokens.uniform
    assert all(
        tuple(normal) == pytest.approx((0.0, 0.0, 1.0))
        for normal in physical_normals.Get()
    )
    primary_minimums = primvars.GetPrimvar(DERIVED_PRIMARY_APERTURE_MIN_U_012)
    primary_maximums = primvars.GetPrimvar(DERIVED_PRIMARY_APERTURE_MAX_U_012)
    primary_fourth = primvars.GetPrimvar(DERIVED_PRIMARY_APERTURE_U_3)
    assert primary_minimums.GetTypeName() == Sdf.ValueTypeNames.Float3Array
    assert primary_maximums.GetTypeName() == Sdf.ValueTypeNames.Float3Array
    assert primary_fourth.GetTypeName() == Sdf.ValueTypeNames.Float3Array
    assert primary_minimums.GetInterpolation() == UsdGeom.Tokens.uniform
    assert primary_maximums.GetInterpolation() == UsdGeom.Tokens.uniform
    assert primary_fourth.GetInterpolation() == UsdGeom.Tokens.uniform
    expected_minimums = (
        (0.0, 1.1 / 2.1, -1.0),
        (0.0, 1.1 / 2.1, -1.0),
        (0.0, -1.0, -1.0),
        (0.0, 1.1 / 2.1, -1.0),
        (0.0, 1.1 / 2.1, -1.0),
    )
    expected_maximums = (
        (1.0 / 2.1, 1.0, -1.0),
        (1.0 / 2.1, 1.0, -1.0),
        (1.0, -1.0, -1.0),
        (1.0 / 2.1, 1.0, -1.0),
        (1.0 / 2.1, 1.0, -1.0),
    )
    expected_fourth = ((-1.0, -1.0, 0.0),) * 5
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
    for authored, expected in zip(
        primary_fourth.Get(),
        expected_fourth,
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


def test_runtime_frame_is_authored_in_world_space():
    stage, mesh = _window_stage((1, 1))
    building = UsdGeom.Xformable(stage.GetPrimAtPath("/World/Building"))
    building.AddRotateYOp().Set(37.0)
    building.AddScaleOp().Set(Gf.Vec3d(2.0, 1.5, 0.75))
    settings = RuntimeClassifierSettings()
    metrics = resolve_stage_metrics(stage, settings)
    extraction = extract_stage_apertures(stage, metrics)
    result = classify_apertures(
        extraction.apertures,
        settings.core_settings(frozenset({1, 2, 3, 4})),
        up_axis=metrics.up_axis,
    )
    owner = RuntimeLayerOwner(stage)

    author_derived_primvars(stage, owner.attach(), extraction, result)

    primvars = UsdGeom.PrimvarsAPI(mesh)
    mappings_by_face = {
        mapping.face_index: mapping for mapping in result.mappings
    }
    apertures_by_face = {
        aperture.face_index: aperture for aperture in extraction.apertures
    }
    authored_axis_u = primvars.GetPrimvar(DERIVED_ROOM_AXIS_U).Get()
    authored_axis_v = primvars.GetPrimvar(DERIVED_ROOM_AXIS_V).Get()
    authored_normals = primvars.GetPrimvar(DERIVED_PHYSICAL_NORMAL).Get()
    authored_positions = primvars.GetPrimvar(DERIVED_ROOM_POSITION).Get()
    for face_index, mapping in mappings_by_face.items():
        assert tuple(authored_axis_u[face_index]) == pytest.approx(
            mapping.room_axis_u
        )
        assert tuple(authored_axis_v[face_index]) == pytest.approx(
            mapping.room_axis_v
        )
        assert tuple(authored_normals[face_index]) == pytest.approx(
            mapping.physical_normal
        )
        assert tuple(authored_positions[face_index]) == pytest.approx(
            apertures_by_face[face_index].room_position_world
        )

    owner.detach()


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
    assert {
        dict(diagnostic.details)["fallback_render_path"]
        for diagnostic in classification.extraction.diagnostics
    } == {"source_authored_x1_binding"}
    assert {
        dict(diagnostic.details)["camera_primvar_inherited_proxy_count"]
        for diagnostic in classification.extraction.diagnostics
    } == {1}
    assert {
        dict(diagnostic.details)["room_uv_varying_proxy_count"]
        for diagnostic in classification.extraction.diagnostics
    } == {1}
    assert not stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX1")
    camera_primvar = UsdGeom.PrimvarsAPI(
        stage.GetPrimAtPath("/World")
    ).GetPrimvar("ormsCameraPositionWorld")
    assert camera_primvar
    assert tuple(camera_primvar.Get()) == (0.0, 0.0, 0.0)
    for instance in instances:
        meshes = tuple(
            prim
            for prim in Usd.PrimRange(
                instance,
                Usd.TraverseInstanceProxies(),
            )
            if prim.IsA(UsdGeom.Mesh)
        )
        assert meshes
        eligible_meshes = tuple(
            mesh
            for mesh in meshes
            if all(
                UsdGeom.PrimvarsAPI(mesh).GetPrimvar(name)
                for name in (
                    "roomID",
                    "roomP",
                    "tangentu",
                    "tangentv",
                    "roomUV",
                )
            )
        )
        ineligible_meshes = tuple(
            mesh for mesh in meshes if mesh not in eligible_meshes
        )
        assert eligible_meshes
        assert all(
            UsdGeom.PrimvarsAPI(mesh)
            .FindPrimvarWithInheritance("ormsCameraPositionWorld")
            .IsDefined()
            for mesh in eligible_meshes
        )
        assert ineligible_meshes
        assert {
            str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            )
            for mesh in eligible_meshes
        } == {f"{instance.GetPath()}/Looks/RoomMap"}
        assert {
            str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            )
            for mesh in ineligible_meshes
        } == {f"{instance.GetPath()}/Looks/Facade"}
        assert not instance.GetRelationship(
            "material:binding:collection:ormsRoomMapWindows"
        )

    owner.detach()

    assert all(prim.IsInstance() for prim in instances)
    assert not any(
        prim.GetRelationship("material:binding:collection:ormsRoomMapWindows")
        for prim in instances
    )


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
