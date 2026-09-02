"""Own shared-room runtime subscriptions, state transitions, and teardown."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import count
from pathlib import Path
from time import perf_counter
from typing import Any

from pxr import Sdf, Tf, Usd, UsdShade

from ..room_run import classifier as _room_run_classifier
from ..room_run.classifier import (
    ApertureDescriptor,
    ClassificationResult,
    ClassifierDiagnostic,
    ClassifierSettings,
    DerivedApertureMapping,
    classify_apertures,
)
from ..runtime.renderer_settings import (
    _enable_rtx_cutout_opacity,
    _restore_rtx_cutout_opacity,
)
from ..runtime.resources import RuntimeResources, coerce_runtime_resources
from ..runtime.status_log import log_room_map_warning
from .authoring import (
    _ROOM_MAP_INPUT_TYPES,
    _SHARED_ARTIST_INPUT_NAMES,
    RuntimeLayerOwner,
    _build_object_space_pose_frames,
    _ObjectSpacePoseFrame,
    _refresh_pose_primvars,
    apply_instance_policy,
    author_camera_position_primvar,
    author_derived_primvars,
    author_family_bindings,
    author_family_materials,
    camera_position_primvar_exists,
    camera_position_primvar_required,
    seed_camera_position_primvar,
)
from .changes import (
    _building_root_shape_signatures,
    _building_root_transform_change_roots,
    _is_relevant_change,
    _pose_change_roots,
    _shape_signatures_match,
)
from .contracts import (
    CAMERA_POSITION_PRIMVAR_NAME,
    CAMERA_POSITION_PRIMVAR_PATH,
    DERIVED_APERTURE_MASK_OFFSET_U,
    DERIVED_MAP_AXIS_U,
    DERIVED_MAP_AXIS_V,
    DERIVED_MAP_ORIGIN,
    DERIVED_MAP_POSITION,
    DERIVED_MAPPING_VALID,
    DERIVED_PHYSICAL_NORMAL,
    DERIVED_PRIMARY_APERTURE_MAX_U_012,
    DERIVED_PRIMARY_APERTURE_MIN_U_012,
    DERIVED_PRIMARY_APERTURE_U_3,
    DERIVED_PRIMVAR_NAMES,
    DERIVED_ROOM_AXIS_U,
    DERIVED_ROOM_AXIS_V,
    DERIVED_ROOM_DEPTH_SIZE,
    DERIVED_ROOM_GROUP_ID,
    DERIVED_ROOM_PARAMETERS,
    DERIVED_ROOM_POSITION,
    DERIVED_ROOM_SCALE,
    DERIVED_ROOM_SIZE,
    DERIVED_SLICE_START_DEPTH,
    INSTANCE_POLICY_PRESERVE,
    INSTANCE_POLICY_SESSION_DEINSTANCE,
    KIT_SETTINGS_ROOT,
    METRICS_MODE_AUTO,
    METRICS_MODE_LOCAL_OVERRIDE,
    RUNTIME_OWNED_PRIMVAR_NAMES,
    ClassificationPhaseCallback,
    ResolvedStageMetrics,
    RuntimeClassifierSettings,
    StageClassification,
    StageExtraction,
)
from .material_controls import material_input_values_from_kit
from .material_diagnostics import (
    MaterialStateSnapshot,
    capture_material_state,
    material_state_log_details,
)
from .pipeline import classify_stage
from .settings import settings_from_kit, settings_from_mapping
from .stage import (
    discover_atlas_family_availability,
    extract_stage_apertures,
    resolve_stage_metrics,
)

__all__ = [
    "CAMERA_POSITION_PRIMVAR_NAME",
    "CAMERA_POSITION_PRIMVAR_PATH",
    "DERIVED_APERTURE_MASK_OFFSET_U",
    "DERIVED_MAPPING_VALID",
    "DERIVED_MAP_AXIS_U",
    "DERIVED_MAP_AXIS_V",
    "DERIVED_MAP_ORIGIN",
    "DERIVED_MAP_POSITION",
    "DERIVED_PHYSICAL_NORMAL",
    "DERIVED_PRIMARY_APERTURE_MAX_U_012",
    "DERIVED_PRIMARY_APERTURE_MIN_U_012",
    "DERIVED_PRIMARY_APERTURE_U_3",
    "DERIVED_PRIMVAR_NAMES",
    "DERIVED_ROOM_AXIS_U",
    "DERIVED_ROOM_AXIS_V",
    "DERIVED_ROOM_DEPTH_SIZE",
    "DERIVED_ROOM_GROUP_ID",
    "DERIVED_ROOM_PARAMETERS",
    "DERIVED_ROOM_POSITION",
    "DERIVED_ROOM_SCALE",
    "DERIVED_ROOM_SIZE",
    "DERIVED_SLICE_START_DEPTH",
    "INSTANCE_POLICY_PRESERVE",
    "INSTANCE_POLICY_SESSION_DEINSTANCE",
    "KIT_SETTINGS_ROOT",
    "METRICS_MODE_AUTO",
    "METRICS_MODE_LOCAL_OVERRIDE",
    "RUNTIME_OWNED_PRIMVAR_NAMES",
    "ApertureDescriptor",
    "ClassificationPhaseCallback",
    "ClassificationResult",
    "ClassifierDiagnostic",
    "ClassifierSettings",
    "DerivedApertureMapping",
    "ResolvedStageMetrics",
    "RuntimeClassifierSettings",
    "RuntimeLayerOwner",
    "SharedRoomClassifier",
    "StageClassification",
    "StageExtraction",
    "apply_instance_policy",
    "author_camera_position_primvar",
    "author_derived_primvars",
    "author_family_bindings",
    "author_family_materials",
    "camera_position_primvar_required",
    "camera_position_primvar_exists",
    "classify_apertures",
    "classify_stage",
    "discover_atlas_family_availability",
    "extract_stage_apertures",
    "inspect",
    "resolve_stage_metrics",
    "seed_camera_position_primvar",
    "settings_from_kit",
    "settings_from_mapping",
    "start",
    "stop",
]

_TRACE_DIAGNOSTIC_CODE = "ORMS-RUNTIME-TRACE"
_TRACE_RUN_IDS = count(1)
_TRACE_PATH_LIMIT = 16
_FIRST_FRAME_SIGNAL = "StageRenderingEventType.NEW_FRAME"
_EXPECTED_CLASSIFIER_CONTRACT_VERSION = "shared_room_runtime_v47"
_UNAVAILABLE_TRANSITION_VALUE = "<unavailable>"
_RUNTIME_INPUT_LOG_DEBOUNCE_SECONDS = 0.2

_RTX_CUTOUT_OPT_IN_ATTRIBUTE = "omni:rtx:enableCutoutOpacity"
_RUNTIME_FAMILY_SHADER_PATHS = tuple(
    Sdf.Path(f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader")
    for room_size in range(1, 5)
)
_SHARED_RUNTIME_INPUT_NAMES = _SHARED_ARTIST_INPUT_NAMES


@dataclass(frozen=True)
class _RuntimeInputSyncResult:
    """Describe whether one shared input has an effective family value."""

    synchronised: bool
    updated_family_count: int
    reason: str
    effective_value: object | None


@dataclass
class _PendingRuntimeInputLog:
    """Retain one editing gesture while material previews update live."""

    trigger: str
    input_name: str
    source_path: Sdf.Path
    previous_value: object
    sync_result: _RuntimeInputSyncResult
    change_count: int = 1
    scheduled_call: object | None = None


def _schedule_runtime_input_log(
    delay_seconds: float,
    callback: Callable[[], None],
) -> object | None:
    """Schedule on Kit's asyncio loop, with a synchronous fallback."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        callback()
        return None
    return loop.call_later(delay_seconds, callback)


def _runtime_family_input_name(path: Sdf.Path) -> str | None:
    """Return a shared artist input edited on one runtime atlas family."""

    if not path.IsPropertyPath() or path.GetPrimPath() not in (
        _RUNTIME_FAMILY_SHADER_PATHS
    ):
        return None
    property_name = str(path).rsplit(".", 1)[-1]
    if not property_name.startswith("inputs:"):
        return None
    input_name = property_name.removeprefix("inputs:")
    return input_name if input_name in _SHARED_RUNTIME_INPUT_NAMES else None


def _runtime_family_input_paths(input_name: str) -> tuple[Sdf.Path, ...]:
    return tuple(
        shader_path.AppendProperty(f"inputs:{input_name}")
        for shader_path in _RUNTIME_FAMILY_SHADER_PATHS
    )


def _synchronise_runtime_family_input(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    source_path: Sdf.Path,
) -> _RuntimeInputSyncResult:
    """Copy one shared control to every authored x1-x4 atlas material."""

    input_name = _runtime_family_input_name(source_path)
    source_attribute = stage.GetAttributeAtPath(source_path)
    if input_name is None or not source_attribute:
        return _RuntimeInputSyncResult(
            False,
            0,
            "source_input_missing",
            None,
        )
    saved_source = _saved_runtime_input_spec(
        source_attribute,
        runtime_layer,
    )
    source_value = (
        saved_source.default
        if saved_source is not None
        else source_attribute.Get()
    )
    if source_value is None:
        return _RuntimeInputSyncResult(
            False,
            0,
            "source_value_unavailable",
            None,
        )
    source_type = (
        saved_source.typeName
        if saved_source is not None
        else source_attribute.GetTypeName()
    )
    if source_type != _ROOM_MAP_INPUT_TYPES[input_name]:
        return _RuntimeInputSyncResult(
            False,
            0,
            "source_type_mismatch",
            source_value,
        )
    active_paths = tuple(
        path
        for path in _runtime_family_input_paths(input_name)
        if stage.GetPrimAtPath(path.GetPrimPath())
    )
    if not active_paths:
        return _RuntimeInputSyncResult(
            False,
            0,
            "no_active_families",
            source_value,
        )
    updated_count = 0
    with Usd.EditContext(stage, runtime_layer):
        for target_path in active_paths:
            target_attribute = stage.GetAttributeAtPath(target_path)
            if not target_attribute:
                target_prim = stage.GetPrimAtPath(target_path.GetPrimPath())
                if not target_prim:
                    continue
                target_attribute = (
                    UsdShade.Shader(target_prim)
                    .CreateInput(
                        input_name,
                        source_type,
                    )
                    .GetAttr()
                )
            if target_attribute.Get() != source_value:
                target_attribute.Set(source_value)
                updated_count += 1
    all_values_match = all(
        (attribute := stage.GetAttributeAtPath(path))
        and attribute.Get() is not None
        and attribute.Get() == source_value
        for path in active_paths
    )
    return _RuntimeInputSyncResult(
        all_values_match,
        updated_count,
        (
            "all_active_family_values_match"
            if all_values_match
            else "active_family_value_unavailable"
        ),
        source_value,
    )


def _runtime_family_input_values(
    stage: Usd.Stage,
    input_name: str,
) -> str:
    values = []
    for room_size, path in enumerate(
        _runtime_family_input_paths(input_name),
        start=1,
    ):
        attribute = stage.GetAttributeAtPath(path)
        values.append(
            f"x{room_size}={attribute.Get() if attribute else 'MISSING'}"
        )
    return ",".join(values)


def _common_runtime_family_input_value(
    stage: Usd.Stage,
    input_name: str,
) -> object | None:
    """Return one non-None value only when every active family agrees."""

    values = tuple(
        attribute.Get()
        for path in _runtime_family_input_paths(input_name)
        if (attribute := stage.GetAttributeAtPath(path))
    )
    if not values or values[0] is None:
        return None
    return values[0] if all(value == values[0] for value in values) else None


def _has_saved_runtime_input_opinion(
    attribute: Usd.Attribute,
    runtime_layer: Sdf.Layer,
) -> bool:
    """Find a saved override outside the classifier-owned runtime layer."""

    attribute_path = attribute.GetPath()
    return any(
        spec.path == attribute_path and spec.layer != runtime_layer
        for spec in attribute.GetPropertyStack()
    )


def _saved_runtime_input_spec(
    attribute: Usd.Attribute,
    runtime_layer: Sdf.Layer,
) -> Sdf.AttributeSpec | None:
    """Return the strongest saved value hidden by runtime defaults."""

    attribute_path = attribute.GetPath()
    return next(
        (
            spec
            for spec in attribute.GetPropertyStack()
            if spec.path == attribute_path and spec.layer != runtime_layer
        ),
        None,
    )


class _RuntimeTrace:
    """Emit one correlated, warning-visible timing record per runtime phase."""

    def __init__(
        self,
        *,
        trigger: str,
        log_warning: Callable[..., None],
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self.run_id = f"ORMS-RUN-{next(_TRACE_RUN_IDS):04d}"
        self.trigger = trigger
        self._log_warning = log_warning
        self._clock = clock
        self._started_at = clock()
        self._last_phase_at = self._started_at

    def mark(
        self,
        phase: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        """Record one phase without hiding it behind the Console info filter."""

        now = self._clock()
        payload: dict[str, object] = {
            "diagnostic_code": _TRACE_DIAGNOSTIC_CODE,
            "run_id": self.run_id,
            "trigger": self.trigger,
            "phase_ms": round((now - self._last_phase_at) * 1000.0, 3),
            "elapsed_ms": round((now - self._started_at) * 1000.0, 3),
        }
        if details:
            payload.update(details)
        self._log_warning(
            owner="SHARED ROOM CLASSIFIER",
            process="RUNTIME PHASE TRACE",
            state=phase,
            details=payload,
        )
        self._last_phase_at = self._clock()


def _subscribe_to_next_rendered_frame(
    callback: Callable[[object], None],
) -> object:
    """Observe the next frame without treating it as material completion."""

    import carb.eventdispatcher
    import omni.usd

    context = omni.usd.get_context()
    event_name = context.stage_rendering_event_name(
        omni.usd.StageRenderingEventType.NEW_FRAME
    )
    return carb.eventdispatcher.get_eventdispatcher().observe_event(
        event_name=event_name,
        on_event=callback,
        observer_name="orms.shared_room_classifier.renderer_ready",
    )


def _trace_path_details(
    *,
    resynced_paths: Sequence[Sdf.Path],
    changed_info_paths: Sequence[Sdf.Path],
    relevant_paths: Sequence[Sdf.Path],
) -> dict[str, object]:
    """Bound USD notice detail volume while retaining the triggering paths."""

    def serialise(paths: Sequence[Sdf.Path]) -> str:
        retained = tuple(str(path) for path in paths[:_TRACE_PATH_LIMIT])
        return ", ".join(retained) if retained else "<none>"

    return {
        "resynced_path_count": len(resynced_paths),
        "resynced_paths": serialise(resynced_paths),
        "changed_info_path_count": len(changed_info_paths),
        "changed_info_paths": serialise(changed_info_paths),
        "relevant_path_count": len(relevant_paths),
        "relevant_paths": serialise(relevant_paths),
        "path_limit": _TRACE_PATH_LIMIT,
        "paths_truncated": (
            len(resynced_paths) > _TRACE_PATH_LIMIT
            or len(changed_info_paths) > _TRACE_PATH_LIMIT
            or len(relevant_paths) > _TRACE_PATH_LIMIT
        ),
    }


def _authoring_notice_details(
    notice_count: int,
    resynced_paths: set[str],
    changed_info_paths: set[str],
) -> dict[str, object]:
    """Bound the USD notices emitted while the runtime layer is authored."""

    def serialise(paths: set[str]) -> str:
        retained = tuple(sorted(paths))[:_TRACE_PATH_LIMIT]
        return ", ".join(retained) if retained else "<none>"

    source_material_dependency_paths = {
        path
        for path in resynced_paths | changed_info_paths
        if "/mtl/" in path
        or ("/Looks/" in path and not path.startswith("/__ORMSRuntime/"))
    }

    return {
        "authoring_notice_count": notice_count,
        "authoring_resynced_path_count": len(resynced_paths),
        "authoring_resynced_paths": serialise(resynced_paths),
        "authoring_changed_info_path_count": len(changed_info_paths),
        "authoring_changed_info_paths": serialise(changed_info_paths),
        "source_material_dependency_notice_path_count": len(
            source_material_dependency_paths
        ),
        "source_material_dependency_notice_paths": serialise(
            source_material_dependency_paths
        ),
        "authoring_notice_path_limit": _TRACE_PATH_LIMIT,
        "authoring_notice_paths_truncated": (
            len(resynced_paths) > _TRACE_PATH_LIMIT
            or len(changed_info_paths) > _TRACE_PATH_LIMIT
        ),
    }


def _runtime_layer_scope_details(
    layer: Sdf.Layer,
    selected_prim_paths: Sequence[str],
) -> dict[str, object]:
    """Report authored specs separately from propagated USD dependency paths."""

    prim_specs = []
    pending = list(layer.rootPrims)
    while pending:
        prim_spec = pending.pop()
        prim_specs.append(prim_spec)
        pending.extend(prim_spec.nameChildren.values())

    authored_paths = tuple(sorted(str(spec.path) for spec in prim_specs))
    selected_paths = tuple(Sdf.Path(path) for path in selected_prim_paths)
    runtime_root = Sdf.Path("/__ORMSRuntime")

    def is_allowed(path_text: str) -> bool:
        path = Sdf.Path(path_text)
        if path.HasPrefix(runtime_root):
            return True
        return any(
            path.HasPrefix(selected) or selected.HasPrefix(path)
            for selected in selected_paths
        )

    source_material_paths = tuple(
        path
        for path in authored_paths
        if "/mtl/" in path
        or ("/Looks/" in path and not path.startswith("/__ORMSRuntime/"))
    )
    unexpected_paths = tuple(
        path for path in authored_paths if not is_allowed(path)
    )

    def serialise_layer_paths(paths: Sequence[str]) -> str:
        retained = paths[:_TRACE_PATH_LIMIT]
        return ", ".join(retained) if retained else "<none>"

    return {
        "runtime_authored_prim_path_count": len(authored_paths),
        "runtime_authored_prim_paths": serialise_layer_paths(authored_paths),
        "runtime_authored_source_material_path_count": len(
            source_material_paths
        ),
        "runtime_authored_source_material_paths": serialise_layer_paths(
            source_material_paths
        ),
        "unexpected_runtime_authored_path_count": len(unexpected_paths),
        "unexpected_runtime_authored_paths": serialise_layer_paths(
            unexpected_paths
        ),
        "runtime_layer_scope_valid": not unexpected_paths,
    }


def _log_diagnostic(diagnostic: ClassifierDiagnostic) -> None:
    log_room_map_warning(
        owner="SHARED ROOM CLASSIFIER",
        process="RUNTIME CLASSIFICATION",
        state=diagnostic.state,
        details={
            "prim_path": diagnostic.prim_path,
            **dict(diagnostic.details),
        },
    )


class SharedRoomClassifier:
    """Manually started shared-room classifier for an already-open stage."""

    def __init__(
        self,
        stage: Usd.Stage,
        resources_or_repository_root: RuntimeResources | Path,
        settings: RuntimeClassifierSettings,
        trace_log_warning: Callable[..., None] | None = None,
        runtime_input_log_scheduler: Callable[
            [float, Callable[[], None]], object | None
        ] = _schedule_runtime_input_log,
        material_input_values: Mapping[str, object] | None = None,
    ):
        self._stage = stage
        self._resources = coerce_runtime_resources(
            resources_or_repository_root
        )
        self._settings = settings
        self._material_input_values = dict(material_input_values or {})
        self._layer_owner = RuntimeLayerOwner(stage)
        self._notice_key: Any | None = None
        self._is_authoring = False
        self._last: StageClassification | None = None
        self._geometry_ancestor_paths: frozenset[str] = frozenset()
        self._source_prim_root_paths: frozenset[str] = frozenset()
        self._source_material_ancestor_paths: frozenset[str] = frozenset()
        self._source_material_root_paths: frozenset[str] = frozenset()
        self._building_root_paths: frozenset[str] = frozenset()
        self._building_root_shape_signatures: dict[str, tuple[float, ...]] = {}
        self._pose_frames_by_prim: dict[
            str, tuple[_ObjectSpacePoseFrame, ...]
        ] = {}
        self._synchronised_runtime_input_values: dict[str, object] = {}
        self._trace_log_warning = trace_log_warning
        self._runtime_input_log_scheduler = runtime_input_log_scheduler
        self._pending_runtime_input_logs: dict[
            tuple[str, str], _PendingRuntimeInputLog
        ] = {}
        self._first_frame_subscription: object | None = None

    @property
    def last_classification(self) -> StageClassification | None:
        """Expose the last immutable inspection result, if classification ran."""

        return self._last

    @property
    def camera_input_paths(self) -> tuple[str, ...]:
        """Return camera inputs owned by classified window materials only."""

        if self._last is None:
            return ()
        paths = set()
        for attribute_path in _runtime_family_input_paths(
            "camera_position_world"
        ):
            attribute = self._stage.GetAttributeAtPath(attribute_path)
            if attribute:
                paths.add(str(attribute.GetPath()))
        for (
            prim_path,
            _face_count,
        ) in self._last.extraction.face_counts_by_prim:
            prim = self._stage.GetPrimAtPath(prim_path)
            material, relationship = UsdShade.MaterialBindingAPI(
                prim
            ).ComputeBoundMaterial()
            if not relationship or not material:
                continue
            for candidate in Usd.PrimRange(material.GetPrim()):
                attribute = candidate.GetAttribute(
                    "inputs:camera_position_world"
                )
                if attribute:
                    paths.add(str(attribute.GetPath()))
        return tuple(sorted(paths))

    def set_material_input_values(
        self,
        values: Mapping[str, object],
    ) -> int:
        """Apply one central control set to every active atlas family."""

        self._material_input_values = {
            name: value
            for name, value in values.items()
            if name in _SHARED_RUNTIME_INPUT_NAMES
        }
        if self._last is None:
            return 0
        updated_count = 0
        self._is_authoring = True
        try:
            with Usd.EditContext(self._stage, self._layer_owner.layer):
                for name, value in self._material_input_values.items():
                    for path in _runtime_family_input_paths(name):
                        attribute = self._stage.GetAttributeAtPath(path)
                        if attribute and attribute.Get() != value:
                            attribute.Set(value)
                            updated_count += 1
        finally:
            self._is_authoring = False
        self._remember_runtime_family_input_values()
        return updated_count

    def set_settings(
        self,
        settings: RuntimeClassifierSettings,
    ) -> StageClassification | None:
        """Reclassify once when the central classifier settings change."""

        if settings == self._settings:
            return self._last
        self._settings = settings
        self._reclassify(trigger="settings_change")
        self._remember_runtime_family_input_values()
        return self._last

    def start(self, trigger: str = "manual_start") -> StageClassification:
        """Classify once, reconcile shared inputs, and subscribe to USD edits."""

        self._reclassify(trigger=trigger)
        self._synchronise_existing_runtime_family_inputs()
        self._remember_runtime_family_input_values()
        self.resume()
        return self._last  # type: ignore[return-value]

    def pause(self) -> None:
        """Freeze the published runtime layer while releasing live updates."""

        self._flush_pending_runtime_input_logs()
        first_frame_subscription, self._first_frame_subscription = (
            self._first_frame_subscription,
            None,
        )
        reset = getattr(first_frame_subscription, "reset", None)
        if callable(reset):
            reset()
        if self._notice_key is not None:
            self._notice_key.Revoke()
            self._notice_key = None

    def resume(self) -> None:
        """Resume USD change handling without rebuilding the frozen layer."""

        if self._last is None:
            raise RuntimeError(
                "Cannot resume ORMS before initial classification"
            )
        if self._notice_key is None:
            self._notice_key = Tf.Notice.Register(
                Usd.Notice.ObjectsChanged,
                self._on_objects_changed,
                self._stage,
            )

    def _remember_runtime_family_input_values(self) -> None:
        """Snapshot the last complete shared state for later transition logs."""

        values = {}
        for input_name in sorted(_SHARED_RUNTIME_INPUT_NAMES):
            value = _common_runtime_family_input_value(
                self._stage,
                input_name,
            )
            if value is not None:
                values[input_name] = value
        self._synchronised_runtime_input_values = values

    def _runtime_input_transition_details(
        self,
        *,
        trigger: str,
        input_name: str,
        source_path: Sdf.Path,
        sync_result: _RuntimeInputSyncResult,
        previous_value: object,
    ) -> dict[str, object]:
        """Describe one attempted shared-value transition without inference."""

        return {
            "trigger": trigger,
            "input": input_name,
            "source_path": str(source_path),
            "previous_value": previous_value,
            "new_value": sync_result.effective_value,
            "reason": sync_result.reason,
            "updated_family_count": sync_result.updated_family_count,
            "family_values": _runtime_family_input_values(
                self._stage,
                input_name,
            ),
        }

    @staticmethod
    def _cancel_scheduled_call(scheduled_call: object | None) -> None:
        """Cancel a pending callback without depending on its concrete type."""

        cancel = getattr(scheduled_call, "cancel", None)
        if callable(cancel):
            cancel()

    def _flush_pending_runtime_input_log(
        self,
        key: tuple[str, str],
    ) -> None:
        """Emit one completed record for a coalesced editing gesture."""

        pending = self._pending_runtime_input_logs.pop(key, None)
        if pending is None:
            return
        self._cancel_scheduled_call(pending.scheduled_call)
        if self._trace_log_warning is None:
            return
        details = self._runtime_input_transition_details(
            trigger=pending.trigger,
            input_name=pending.input_name,
            source_path=pending.source_path,
            sync_result=pending.sync_result,
            previous_value=pending.previous_value,
        )
        details.update(
            {
                "coalesced_change_count": pending.change_count,
                "coalescing_window_ms": int(
                    _RUNTIME_INPUT_LOG_DEBOUNCE_SECONDS * 1000
                ),
            }
        )
        self._trace_log_warning(
            owner="SHARED ROOM CLASSIFIER",
            process="RUNTIME MATERIAL INPUT SYNC",
            state="SYNCHRONISED",
            details=details,
        )

    def _queue_runtime_input_log(
        self,
        *,
        trigger: str,
        input_name: str,
        source_path: Sdf.Path,
        sync_result: _RuntimeInputSyncResult,
        previous_value: object,
    ) -> None:
        """Coalesce successful notices without delaying material authoring."""

        key = (str(source_path), input_name)
        pending = self._pending_runtime_input_logs.get(key)
        if pending is None:
            pending = _PendingRuntimeInputLog(
                trigger=trigger,
                input_name=input_name,
                source_path=source_path,
                previous_value=previous_value,
                sync_result=sync_result,
            )
            self._pending_runtime_input_logs[key] = pending
        else:
            self._cancel_scheduled_call(pending.scheduled_call)
            pending.sync_result = sync_result
            pending.change_count += 1
        pending.scheduled_call = self._runtime_input_log_scheduler(
            _RUNTIME_INPUT_LOG_DEBOUNCE_SECONDS,
            lambda: self._flush_pending_runtime_input_log(key),
        )

    def _flush_pending_runtime_input_logs(self) -> None:
        """Flush completed edits before runtime teardown."""

        for key in tuple(self._pending_runtime_input_logs):
            self._flush_pending_runtime_input_log(key)

    def _synchronise_existing_runtime_family_inputs(self) -> None:
        """Reconcile saved family overrides before subscribing to new edits."""

        for input_name in sorted(_SHARED_RUNTIME_INPUT_NAMES):
            authored_paths = tuple(
                path
                for path in _runtime_family_input_paths(input_name)
                if (
                    (attribute := self._stage.GetAttributeAtPath(path))
                    and _has_saved_runtime_input_opinion(
                        attribute,
                        self._layer_owner.layer,
                    )
                )
            )
            if not authored_paths:
                continue
            source_path = authored_paths[0]
            source_spec = _saved_runtime_input_spec(
                self._stage.GetAttributeAtPath(source_path),
                self._layer_owner.layer,
            )
            source_value = source_spec.default
            conflicting_paths = tuple(
                path
                for path in authored_paths[1:]
                if _saved_runtime_input_spec(
                    self._stage.GetAttributeAtPath(path),
                    self._layer_owner.layer,
                ).default
                != source_value
            )
            if conflicting_paths:
                log_room_map_warning(
                    owner="SHARED ROOM CLASSIFIER",
                    process="RUNTIME MATERIAL INPUT SYNC",
                    state="CONFLICT",
                    details={
                        "input": input_name,
                        "family_paths": ",".join(
                            str(path) for path in authored_paths
                        ),
                        "message": (
                            "Saved atlas-family overrides disagree; edit one "
                            "runtime family input to choose the shared value."
                        ),
                    },
                )
                continue
            sync_result = _synchronise_runtime_family_input(
                self._stage,
                self._layer_owner.layer,
                source_path,
            )
            previous_value = self._synchronised_runtime_input_values.get(
                input_name,
                _UNAVAILABLE_TRANSITION_VALUE,
            )
            if (
                not sync_result.synchronised
                and self._trace_log_warning is not None
            ):
                self._trace_log_warning(
                    owner="SHARED ROOM CLASSIFIER",
                    process="RUNTIME MATERIAL INPUT SYNC",
                    state="DEFERRED",
                    details=self._runtime_input_transition_details(
                        trigger="manual_start",
                        input_name=input_name,
                        source_path=source_path,
                        sync_result=sync_result,
                        previous_value=previous_value,
                    ),
                )
                continue
            if (
                sync_result.synchronised
                and sync_result.effective_value is not None
            ):
                self._synchronised_runtime_input_values[input_name] = (
                    sync_result.effective_value
                )
            if (
                sync_result.updated_family_count
                and self._trace_log_warning is not None
            ):
                self._trace_log_warning(
                    owner="SHARED ROOM CLASSIFIER",
                    process="RUNTIME MATERIAL INPUT SYNC",
                    state="SYNCHRONISED",
                    details=self._runtime_input_transition_details(
                        trigger="manual_start",
                        input_name=input_name,
                        source_path=source_path,
                        sync_result=sync_result,
                        previous_value=previous_value,
                    ),
                )

    def _reclassify(
        self,
        *,
        trigger: str = "usd_change",
        trigger_details: Mapping[str, object] | None = None,
    ) -> None:
        if self._is_authoring:
            return
        self._flush_pending_runtime_input_logs()
        self._is_authoring = True
        notice_key: Any | None = None
        try:
            # Build the complete replacement away from the live render stage.
            # Only the finished Sdf layer is published into live composition.
            authoring_stage, draft_layer = (
                self._layer_owner.prepare_replacement()
            )
            trace = (
                _RuntimeTrace(
                    trigger=trigger,
                    log_warning=self._trace_log_warning,
                )
                if self._trace_log_warning is not None
                else None
            )
            baseline_material_state = (
                capture_material_state(self._stage)
                if trace is not None
                else None
            )
            authoring_notice_count = 0
            authoring_resynced_paths: set[str] = set()
            authoring_changed_info_paths: set[str] = set()

            def capture_authoring_notice(
                notice: Usd.Notice.ObjectsChanged,
                _sender: Usd.Stage,
            ) -> None:
                nonlocal authoring_notice_count
                authoring_notice_count += 1
                authoring_resynced_paths.update(
                    str(path) for path in notice.GetResyncedPaths()
                )
                authoring_changed_info_paths.update(
                    str(path) for path in notice.GetChangedInfoOnlyPaths()
                )

            if trace is not None:
                notice_key = Tf.Notice.Register(
                    Usd.Notice.ObjectsChanged,
                    capture_authoring_notice,
                    self._stage,
                )
            if trace is not None:
                run_details: dict[str, object] = {
                    "stage_identifier": self._stage.GetRootLayer().identifier,
                    "runtime_layer": self._layer_owner.layer.identifier,
                    "draft_layer": draft_layer.identifier,
                    "publication_mode": (
                        "isolated_stage_atomic_layer_transfer"
                    ),
                    "classifier_contract": (
                        _EXPECTED_CLASSIFIER_CONTRACT_VERSION
                    ),
                }
                if trigger_details:
                    run_details.update(trigger_details)
                trace.mark(
                    "RUNTIME_RUN_BEGIN",
                    run_details,
                )
            self._last = classify_stage(
                authoring_stage,
                draft_layer,
                self._settings,
                self._resources,
                phase_callback=trace.mark if trace is not None else None,
                material_input_values=self._material_input_values,
            )
            published_layer = self._layer_owner.publish(draft_layer)
            self._last = replace(
                self._last,
                runtime_layer_identifier=published_layer.identifier,
            )
            if trace is not None:
                selected_prim_paths = tuple(
                    prim_path
                    for prim_path, _face_count in (
                        self._last.extraction.face_counts_by_prim
                    )
                )
                trace.mark(
                    "RUNTIME_LAYER_PUBLISHED",
                    {
                        "publication_mode": (
                            "isolated_stage_atomic_layer_transfer"
                        ),
                        "draft_layer": draft_layer.identifier,
                        "runtime_layer": published_layer.identifier,
                        **_authoring_notice_details(
                            authoring_notice_count,
                            authoring_resynced_paths,
                            authoring_changed_info_paths,
                        ),
                        **_runtime_layer_scope_details(
                            published_layer,
                            selected_prim_paths,
                        ),
                    },
                )
            geometry_ancestor_paths = set()
            for prim_path in self._last.extraction.source_prim_paths:
                geometry_ancestor_paths.update(
                    str(prefix)
                    for prefix in Sdf.Path(prim_path).GetPrefixes()
                    if prefix.IsPrimPath()
                )
            self._geometry_ancestor_paths = frozenset(geometry_ancestor_paths)
            self._source_prim_root_paths = frozenset(
                self._last.extraction.source_prim_paths
            )
            source_material_ancestor_paths = set()
            for material_path in self._last.extraction.source_material_paths:
                source_material_ancestor_paths.update(
                    str(prefix)
                    for prefix in Sdf.Path(material_path).GetPrefixes()
                    if prefix.IsPrimPath()
                )
            self._source_material_ancestor_paths = frozenset(
                source_material_ancestor_paths
            )
            self._source_material_root_paths = frozenset(
                self._last.extraction.source_material_paths
            )
            self._building_root_paths = frozenset(
                aperture.building_root
                for aperture in self._last.extraction.apertures
            )
            self._building_root_shape_signatures = (
                _building_root_shape_signatures(
                    self._stage,
                    self._building_root_paths,
                )
            )
            self._pose_frames_by_prim = _build_object_space_pose_frames(
                self._stage,
                self._last,
            )
            diagnostics = (
                self._last.metrics.diagnostics
                + self._last.extraction.diagnostics
                + self._last.result.diagnostics
            )
            for diagnostic in diagnostics:
                _log_diagnostic(diagnostic)
            if trace is not None:
                material_state_after_authoring = capture_material_state(
                    self._stage,
                    tuple(baseline_material_state["source_material_paths"]),
                )
                allowed_binding_paths = tuple(
                    prim_path
                    for prim_path, _face_count in (
                        self._last.extraction.face_counts_by_prim
                    )
                )
                trace.mark(
                    "SOURCE_USD_STATE_AFTER_AUTHORING",
                    {
                        **material_state_log_details(
                            material_state_after_authoring,
                            baseline_material_state,
                            allowed_binding_paths,
                        ),
                        **_authoring_notice_details(
                            authoring_notice_count,
                            authoring_resynced_paths,
                            authoring_changed_info_paths,
                        ),
                    },
                )
                self._trace_material_submission(
                    trace,
                    baseline_material_state,
                )
        finally:
            if notice_key is not None:
                notice_key.Revoke()
            self._is_authoring = False

    def _trace_material_submission(
        self,
        trace: _RuntimeTrace,
        baseline_material_state: MaterialStateSnapshot,
    ) -> None:
        """Trace observable renderer boundaries without inventing completion."""

        self._first_frame_subscription = None

        def on_new_frame(_event: object) -> None:
            self._first_frame_subscription = None
            source_material_paths = tuple(
                baseline_material_state["source_material_paths"]
            )
            first_frame_material_state = capture_material_state(
                self._stage,
                source_material_paths,
            )
            allowed_binding_paths = tuple(
                prim_path
                for prim_path, _face_count in (
                    self._last.extraction.face_counts_by_prim
                    if self._last is not None
                    else ()
                )
            )
            trace.mark(
                "FIRST_FRAME_AFTER_MATERIAL_UPDATE",
                {
                    "observation_signal": _FIRST_FRAME_SIGNAL,
                    "material_loading_complete": False,
                    "group_count": (
                        len(self._last.result.groups) if self._last else 0
                    ),
                    **material_state_log_details(
                        first_frame_material_state,
                        baseline_material_state,
                        allowed_binding_paths,
                    ),
                },
            )

        trace.mark(
            "MATERIAL_UPDATE_SUBMITTED",
            {
                "first_frame_signal": _FIRST_FRAME_SIGNAL,
                "material_loading_complete": False,
                "material_family_count": (
                    len(self._last.available_room_sizes)
                    if self._last.result.mappings
                    else 0
                ),
            },
        )
        trace.mark(
            "MATERIAL_LOADING_COMPLETION_UNOBSERVABLE",
            {
                "reason": (
                    "native_status_bar_waits_on_IRenderer_waitIdle_without_"
                    "a_public_Python_completion_event"
                ),
                "status_bar_activity": "Loading material...",
                "first_frame_is_completion": False,
            },
        )
        try:
            self._first_frame_subscription = _subscribe_to_next_rendered_frame(
                on_new_frame
            )
        except Exception as error:
            trace.mark(
                "FIRST_FRAME_OBSERVATION_UNAVAILABLE",
                {
                    "observation_signal": _FIRST_FRAME_SIGNAL,
                    "error": repr(error),
                },
            )

    def _synchronise_changed_runtime_inputs(
        self,
        paths: Sequence[Sdf.Path],
    ) -> None:
        """Propagate shared material edits without reclassifying geometry."""

        shared_input_paths = tuple(
            path for path in paths if _runtime_family_input_name(path)
        )
        if not shared_input_paths:
            return
        self._is_authoring = True
        try:
            for path in shared_input_paths:
                input_name = _runtime_family_input_name(path)
                if input_name is None:
                    continue
                previous_value = self._synchronised_runtime_input_values.get(
                    input_name,
                    _UNAVAILABLE_TRANSITION_VALUE,
                )
                sync_result = _synchronise_runtime_family_input(
                    self._stage,
                    self._layer_owner.layer,
                    path,
                )
                if (
                    sync_result.synchronised
                    and sync_result.effective_value is not None
                ):
                    self._synchronised_runtime_input_values[input_name] = (
                        sync_result.effective_value
                    )
                if self._trace_log_warning is None:
                    continue
                if (
                    sync_result.synchronised
                    and sync_result.updated_family_count == 0
                    and previous_value == sync_result.effective_value
                ):
                    continue
                pending_key = (str(path), input_name)
                if sync_result.synchronised:
                    self._queue_runtime_input_log(
                        trigger="usd_change",
                        input_name=input_name,
                        source_path=path,
                        sync_result=sync_result,
                        previous_value=previous_value,
                    )
                    continue
                self._flush_pending_runtime_input_log(pending_key)
                self._trace_log_warning(
                    owner="SHARED ROOM CLASSIFIER",
                    process="RUNTIME MATERIAL INPUT SYNC",
                    state="DEFERRED",
                    details=self._runtime_input_transition_details(
                        trigger="usd_change",
                        input_name=input_name,
                        source_path=path,
                        sync_result=sync_result,
                        previous_value=previous_value,
                    ),
                )
        finally:
            self._is_authoring = False

    def _on_objects_changed(
        self,
        notice: Usd.Notice.ObjectsChanged,
        _sender: Usd.Stage,
    ) -> None:
        if self._is_authoring:
            return
        resynced_paths = tuple(notice.GetResyncedPaths())
        changed_info_paths = tuple(notice.GetChangedInfoOnlyPaths())
        paths = resynced_paths + changed_info_paths
        self._synchronise_changed_runtime_inputs(paths)
        # Rigid building motion refreshes pose primvars only. Shape or topology
        # changes invalidate adjacency and require complete reclassification.
        transform_roots = _building_root_transform_change_roots(
            paths,
            self._building_root_paths,
        )
        current_shape_signatures = _building_root_shape_signatures(
            self._stage,
            transform_roots,
        )
        changed_shape_roots = frozenset(
            root
            for root, signature in current_shape_signatures.items()
            if not _shape_signatures_match(
                self._building_root_shape_signatures.get(root),
                signature,
            )
        )
        relevant_paths = tuple(
            path
            for path in resynced_paths
            if _is_relevant_change(
                self._stage,
                path,
                self._geometry_ancestor_paths,
                self._building_root_paths,
                changed_shape_roots,
                source_prim_root_paths=self._source_prim_root_paths,
                source_material_ancestor_paths=(
                    self._source_material_ancestor_paths
                ),
                source_material_root_paths=self._source_material_root_paths,
                resynced=True,
            )
        ) + tuple(
            path
            for path in changed_info_paths
            if _is_relevant_change(
                self._stage,
                path,
                self._geometry_ancestor_paths,
                self._building_root_paths,
                changed_shape_roots,
                source_prim_root_paths=self._source_prim_root_paths,
                source_material_ancestor_paths=(
                    self._source_material_ancestor_paths
                ),
                source_material_root_paths=self._source_material_root_paths,
                resynced=False,
            )
        )
        if relevant_paths:
            self._reclassify(
                trigger="usd_change",
                trigger_details=_trace_path_details(
                    resynced_paths=resynced_paths,
                    changed_info_paths=changed_info_paths,
                    relevant_paths=relevant_paths,
                ),
            )
        else:
            pose_roots = _pose_change_roots(
                paths,
                self._building_root_paths,
            )
            if pose_roots:
                self._is_authoring = True
                try:
                    _refresh_pose_primvars(
                        self._stage,
                        self._layer_owner.layer,
                        self._pose_frames_by_prim,
                        pose_roots,
                    )
                finally:
                    self._is_authoring = False
            self._building_root_shape_signatures.update(
                current_shape_signatures
            )

    def stop(self) -> None:
        """Release subscriptions and detach only this classifier's USD layer."""

        self.pause()
        self._layer_owner.detach()
        self._last = None
        self._geometry_ancestor_paths = frozenset()
        self._source_prim_root_paths = frozenset()
        self._source_material_ancestor_paths = frozenset()
        self._source_material_root_paths = frozenset()
        self._building_root_paths = frozenset()
        self._building_root_shape_signatures = {}
        self._pose_frames_by_prim = {}
        self._synchronised_runtime_input_values = {}


_classifier: SharedRoomClassifier | None = None
_context_subscription: Any | None = None
_runtime_resources: RuntimeResources | None = None
_runtime_settings: RuntimeClassifierSettings | None = None
_runtime_material_input_values: dict[str, object] = {}


def _replace_active_classifier(
    stage: Usd.Stage | None,
    *,
    trigger: str,
) -> None:
    global _classifier
    if _classifier:
        _classifier.stop()
        _classifier = None
    if (
        stage is None
        or _runtime_resources is None
        or _runtime_settings is None
    ):
        return
    _classifier = SharedRoomClassifier(
        stage,
        _runtime_resources,
        _runtime_settings,
        trace_log_warning=log_room_map_warning,
        material_input_values=_runtime_material_input_values,
    )
    _classifier.start(trigger=trigger)


def _on_stage_event(event: object) -> None:
    import omni.usd

    event_name = getattr(event, "event_name", "")
    if not event_name:
        return
    event_type = int(omni.usd.stage_event_type(event_name))
    opened = getattr(omni.usd.StageEventType, "OPENED", None)
    closing_types = {
        int(value)
        for value in (
            getattr(omni.usd.StageEventType, "CLOSING", None),
            getattr(omni.usd.StageEventType, "CLOSED", None),
        )
        if value is not None
    }
    if opened is not None and event_type == int(opened):
        _replace_active_classifier(
            omni.usd.get_context().get_stage(),
            trigger="stage_open",
        )
    elif event_type in closing_types:
        _replace_active_classifier(None, trigger="stage_close")


def start(
    repository_root: str | Path | None = None,
    settings: RuntimeClassifierSettings | None = None,
    resources: RuntimeResources | None = None,
) -> SharedRoomClassifier:
    """Start on the already-open stage, then subscribe to later stage changes."""

    import carb.eventdispatcher
    import omni.usd

    global _context_subscription, _runtime_material_input_values
    global _runtime_resources, _runtime_settings
    # A fresh start restores every singleton-owned resource from a previous run,
    # making repeated Script Editor execution deterministic and leak-free.
    stop()
    loaded_contract = getattr(
        _room_run_classifier,
        "CLASSIFIER_CONTRACT_VERSION",
        "missing",
    )
    if loaded_contract != _EXPECTED_CLASSIFIER_CONTRACT_VERSION:
        details = {
            "loaded_contract": loaded_contract,
            "expected_contract": _EXPECTED_CLASSIFIER_CONTRACT_VERSION,
            "action": (
                "reload room_run_classifier before shared_room_classifier"
            ),
        }
        log_room_map_warning(
            owner="ORMS",
            process="runtime_classifier",
            state="CLASSIFIER_MODULE_STALE",
            details=details,
        )
        raise RuntimeError(
            "Stale room_run_classifier module; reload it before "
            "shared_room_classifier"
        )
    context = omni.usd.get_context()
    stage = context.get_stage()
    if stage is None:
        raise RuntimeError(
            "Open a USD stage before starting the ORMS classifier"
        )
    if repository_root is None and resources is None:
        root_real_path = stage.GetRootLayer().realPath
        if not root_real_path:
            raise RuntimeError(
                "Pass repository_root when the stage root is anonymous"
            )
        repository_root = Path(root_real_path).resolve().parent
        while repository_root.name != "_Room_Map_Shader_RnD":
            if repository_root.parent == repository_root:
                raise RuntimeError("Could not derive the ORMS repository root")
            repository_root = repository_root.parent

    # The cutout gate is effective only on ORMS materials that carry the
    # explicit opt-in attribute. Scene-wide face culling remains external:
    # acquiring it here would change unrelated single-sided building meshes.
    if resources is not None:
        _runtime_resources = resources
    else:
        if repository_root is None:
            raise RuntimeError(
                "ORMS runtime resources or a repository root are required"
            )
        _runtime_resources = RuntimeResources.from_repository(repository_root)
    _runtime_settings = settings or settings_from_kit()
    _runtime_material_input_values = material_input_values_from_kit()
    try:
        source_material_state = capture_material_state(stage)
        log_room_map_warning(
            owner="SHARED ROOM CLASSIFIER",
            process="RUNTIME SOURCE USD STATE",
            state="BEFORE_RENDERER_SETTINGS",
            details=material_state_log_details(source_material_state),
        )
        _enable_rtx_cutout_opacity()
        source_material_state_after_cutout = capture_material_state(stage)
        log_room_map_warning(
            owner="SHARED ROOM CLASSIFIER",
            process="RUNTIME SOURCE USD STATE",
            state="AFTER_CUTOUT_GATE",
            details=material_state_log_details(
                source_material_state_after_cutout,
                source_material_state,
            ),
        )
        _replace_active_classifier(stage, trigger="manual_start")
        dispatcher = carb.eventdispatcher.get_eventdispatcher()
        _context_subscription = tuple(
            dispatcher.observe_event(
                event_name=context.stage_event_name(event_type),
                on_event=_on_stage_event,
                observer_name=(
                    "orms.shared_room_classifier." f"{event_name.lower()}"
                ),
            )
            for event_name, event_type in (
                ("OPENED", omni.usd.StageEventType.OPENED),
                ("CLOSING", omni.usd.StageEventType.CLOSING),
                ("CLOSED", omni.usd.StageEventType.CLOSED),
            )
        )
    except Exception:
        _restore_rtx_cutout_opacity()
        raise
    return _classifier  # type: ignore[return-value]


def inspect() -> StageClassification | None:
    """Return the latest R&D result without exposing editable window indices."""

    return _classifier.last_classification if _classifier else None


def stop() -> None:
    """Stop subscriptions and remove only the ORMS-owned runtime sublayer."""

    global _classifier, _context_subscription, _runtime_material_input_values
    global _runtime_resources, _runtime_settings
    if _classifier:
        _classifier.stop()
        _classifier = None
    subscriptions = (
        _context_subscription
        if isinstance(_context_subscription, tuple)
        else (_context_subscription,)
    )
    for subscription in subscriptions:
        reset = getattr(subscription, "reset", None)
        if callable(reset):
            reset()
    _context_subscription = None
    _runtime_resources = None
    _runtime_settings = None
    _runtime_material_input_values = {}
    _restore_rtx_cutout_opacity()
