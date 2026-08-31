"""Own shared-room runtime subscriptions, state transitions, and teardown."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
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
    _enable_rtx_material_sync_loads,
    _enable_rtx_single_sided_culling,
    _restore_rtx_cutout_opacity,
    _restore_rtx_material_sync_loads,
    _restore_rtx_single_sided_culling,
)
from ..runtime.status_log import log_room_map_warning
from . import preferences as shared_room_preferences
from .authoring import (
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
_RTX_FACE_CULLING_SETTING = "/rtx/hydra/faceCulling/enabled"
_RTX_OPACITY_OVERRIDE_SETTING = "/rtx/material/omniRtxEnableOpacityOverride"
_RTX_MATERIAL_SYNC_SETTINGS = (
    "/rtx/materialDb/syncLoads",
    "/rtx/hydra/materialSyncLoads",
)
_EXPECTED_CLASSIFIER_CONTRACT_VERSION = "shared_room_runtime_v46"

_RTX_CUTOUT_OPT_IN_ATTRIBUTE = "omni:rtx:enableCutoutOpacity"
_RUNTIME_FAMILY_SHADER_PATHS = tuple(
    Sdf.Path(f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader")
    for room_size in range(1, 5)
)
_SHARED_RUNTIME_INPUT_NAMES = frozenset(
    {
        "variation_seed",
        "room_depth",
        "room_uniform_scale",
        "window_shift",
        "window_aperture_scale",
        "window_aperture_offset",
        "enable_slice_1",
        "enable_slice_2",
        "enable_slice_3",
        "enable_slice_4",
        "slice_1_depth_percent",
        "slice_2_depth_percent",
        "slice_3_depth_percent",
        "slice_4_depth_percent",
        "slice_1_offset",
        "slice_2_offset",
        "slice_3_offset",
        "slice_4_offset",
        "slice_1_scale",
        "slice_2_scale",
        "slice_3_scale",
        "slice_4_scale",
        "fallback_colour",
        "emission_strength",
    }
)


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
    source_path: Sdf.Path,
) -> int:
    """Copy one shared control to every authored x1-x4 atlas material."""

    input_name = _runtime_family_input_name(source_path)
    source_attribute = stage.GetAttributeAtPath(source_path)
    if input_name is None or not source_attribute:
        return 0
    source_value = source_attribute.Get()
    source_type = source_attribute.GetTypeName()
    updated_count = 0
    for target_path in _runtime_family_input_paths(input_name):
        if target_path == source_path:
            continue
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
    return updated_count


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


def _has_direct_runtime_input_opinion(attribute: Usd.Attribute) -> bool:
    """Exclude values inherited from the source material specialization."""

    attribute_path = attribute.GetPath()
    return any(
        spec.path == attribute_path for spec in attribute.GetPropertyStack()
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
        repository_root: Path,
        settings: RuntimeClassifierSettings,
        trace_log_warning: Callable[..., None] | None = None,
    ):
        self._stage = stage
        self._repository_root = repository_root
        self._settings = settings
        self._layer_owner = RuntimeLayerOwner(stage)
        self._notice_key: Any | None = None
        self._is_authoring = False
        self._last: StageClassification | None = None
        self._geometry_ancestor_paths: frozenset[str] = frozenset()
        self._building_root_paths: frozenset[str] = frozenset()
        self._building_root_shape_signatures: dict[str, tuple[float, ...]] = {}
        self._pose_frames_by_prim: dict[
            str, tuple[_ObjectSpacePoseFrame, ...]
        ] = {}
        self._trace_log_warning = trace_log_warning
        self._first_frame_subscription: object | None = None

    @property
    def last_classification(self) -> StageClassification | None:
        """Expose the last immutable inspection result, if classification ran."""

        return self._last

    def start(self, trigger: str = "manual_start") -> StageClassification:
        """Classify once, reconcile shared inputs, and subscribe to USD edits."""

        runtime_layer = self._layer_owner.attach()
        self._reclassify(runtime_layer, trigger=trigger)
        self._synchronise_existing_runtime_family_inputs()
        self._notice_key = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            self._stage,
        )
        return self._last  # type: ignore[return-value]

    def _synchronise_existing_runtime_family_inputs(self) -> None:
        """Reconcile saved family overrides before subscribing to new edits."""

        for input_name in sorted(_SHARED_RUNTIME_INPUT_NAMES):
            authored_paths = tuple(
                path
                for path in _runtime_family_input_paths(input_name)
                if (
                    (attribute := self._stage.GetAttributeAtPath(path))
                    and _has_direct_runtime_input_opinion(attribute)
                )
            )
            if not authored_paths:
                continue
            source_path = authored_paths[0]
            source_value = self._stage.GetAttributeAtPath(source_path).Get()
            conflicting_paths = tuple(
                path
                for path in authored_paths[1:]
                if self._stage.GetAttributeAtPath(path).Get() != source_value
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
            updated_count = _synchronise_runtime_family_input(
                self._stage,
                source_path,
            )
            if updated_count and self._trace_log_warning is not None:
                self._trace_log_warning(
                    owner="SHARED ROOM CLASSIFIER",
                    process="RUNTIME MATERIAL INPUT SYNC",
                    state="SYNCHRONISED",
                    details={
                        "trigger": "manual_start",
                        "input": input_name,
                        "source_path": str(source_path),
                        "updated_family_count": updated_count,
                        "family_values": _runtime_family_input_values(
                            self._stage,
                            input_name,
                        ),
                    },
                )

    def _reclassify(
        self,
        runtime_layer: Sdf.Layer | None = None,
        *,
        trigger: str = "usd_change",
        trigger_details: Mapping[str, object] | None = None,
    ) -> None:
        if self._is_authoring:
            return
        self._is_authoring = True
        try:
            # Rebuild the owned layer as one coherent snapshot. The authoring
            # guard prevents these opinions from recursively invalidating it.
            layer = runtime_layer or self._layer_owner.layer
            layer.Clear()
            trace = (
                _RuntimeTrace(
                    trigger=trigger,
                    log_warning=self._trace_log_warning,
                )
                if self._trace_log_warning is not None
                else None
            )
            if trace is not None:
                run_details: dict[str, object] = {
                    "stage_identifier": self._stage.GetRootLayer().identifier,
                    "runtime_layer": layer.identifier,
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
                self._stage,
                layer,
                self._settings,
                self._repository_root,
                phase_callback=trace.mark if trace is not None else None,
            )
            geometry_ancestor_paths = set()
            for (
                prim_path,
                _face_count,
            ) in self._last.extraction.face_counts_by_prim:
                geometry_ancestor_paths.update(
                    str(prefix)
                    for prefix in Sdf.Path(prim_path).GetPrefixes()
                    if prefix.IsPrimPath()
                )
            self._geometry_ancestor_paths = frozenset(geometry_ancestor_paths)
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
                self._trace_material_submission(trace)
        finally:
            self._is_authoring = False

    def _trace_material_submission(self, trace: _RuntimeTrace) -> None:
        """Trace observable renderer boundaries without inventing completion."""

        self._first_frame_subscription = None

        def on_new_frame(_event: object) -> None:
            self._first_frame_subscription = None
            trace.mark(
                "FIRST_FRAME_AFTER_MATERIAL_UPDATE",
                {
                    "observation_signal": _FIRST_FRAME_SIGNAL,
                    "material_loading_complete": False,
                    "group_count": (
                        len(self._last.result.groups) if self._last else 0
                    ),
                },
            )

        trace.mark(
            "MATERIAL_UPDATE_SUBMITTED",
            {
                "first_frame_signal": _FIRST_FRAME_SIGNAL,
                "material_loading_complete": False,
                "material_family_count": len(
                    self._settings.core_settings(
                        self._last.available_room_sizes
                    ).enabled_room_sizes
                    & self._last.available_room_sizes
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
        shared_input_paths = tuple(
            path for path in paths if _runtime_family_input_name(path)
        )
        if shared_input_paths:
            # Artist edits to a shared control propagate across family materials
            # without rerunning geometric classification.
            self._is_authoring = True
            try:
                for path in shared_input_paths:
                    updated_count = _synchronise_runtime_family_input(
                        self._stage,
                        path,
                    )
                    input_name = _runtime_family_input_name(path)
                    if self._trace_log_warning is None:
                        continue
                    self._trace_log_warning(
                        owner="SHARED ROOM CLASSIFIER",
                        process="RUNTIME MATERIAL INPUT SYNC",
                        state="SYNCHRONISED",
                        details={
                            "trigger": "usd_change",
                            "input": input_name,
                            "source_path": str(path),
                            "updated_family_count": updated_count,
                            "family_values": _runtime_family_input_values(
                                self._stage,
                                input_name,
                            ),
                        },
                    )
            finally:
                self._is_authoring = False
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

        self._first_frame_subscription = None
        if self._notice_key is not None:
            self._notice_key.Revoke()
            self._notice_key = None
        self._layer_owner.detach()
        self._last = None
        self._building_root_shape_signatures = {}
        self._pose_frames_by_prim = {}


_classifier: SharedRoomClassifier | None = None
_context_subscription: Any | None = None
_repository_root: Path | None = None
_runtime_settings: RuntimeClassifierSettings | None = None


def _on_classifier_setting_changed() -> None:
    global _runtime_settings
    if _repository_root is None:
        return
    import omni.usd

    _runtime_settings = settings_from_kit()
    _replace_active_classifier(
        omni.usd.get_context().get_stage(),
        trigger="settings_change",
    )


def _replace_active_classifier(
    stage: Usd.Stage | None,
    *,
    trigger: str,
) -> None:
    global _classifier
    if _classifier:
        _classifier.stop()
        _classifier = None
    if stage is None or _repository_root is None or _runtime_settings is None:
        return
    _classifier = SharedRoomClassifier(
        stage,
        _repository_root,
        _runtime_settings,
        trace_log_warning=log_room_map_warning,
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
) -> SharedRoomClassifier:
    """Start on the already-open stage, then subscribe to later stage changes."""

    import carb.eventdispatcher
    import omni.usd

    global _context_subscription, _repository_root, _runtime_settings
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
    if repository_root is None:
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

    # Renderer settings and stage subscriptions are runtime-owned and restored
    # by stop(); source USD and user preferences remain external.
    _repository_root = Path(repository_root).resolve()
    shared_room_preferences.register(_on_classifier_setting_changed)
    _runtime_settings = settings or settings_from_kit()
    _enable_rtx_single_sided_culling()
    try:
        _enable_rtx_cutout_opacity()
        _enable_rtx_material_sync_loads()
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
        _restore_rtx_material_sync_loads()
        _restore_rtx_cutout_opacity()
        _restore_rtx_single_sided_culling()
        raise
    return _classifier  # type: ignore[return-value]


def inspect() -> StageClassification | None:
    """Return the latest R&D result without exposing editable window indices."""

    return _classifier.last_classification if _classifier else None


def stop() -> None:
    """Stop subscriptions and remove only the ORMS-owned runtime sublayer."""

    global _classifier, _context_subscription, _repository_root, _runtime_settings
    if _classifier:
        _classifier.stop()
        _classifier = None
    shared_room_preferences.unregister()
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
    _repository_root = None
    _runtime_settings = None
    _restore_rtx_material_sync_loads()
    _restore_rtx_cutout_opacity()
    _restore_rtx_single_sided_culling()
