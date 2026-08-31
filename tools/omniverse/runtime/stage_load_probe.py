"""Trace the observable Kit stage-loading pipeline in warning-visible logs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from itertools import count
from time import perf_counter
from typing import Any

from .resource_metrics import _resource_snapshot
from .stage_load_state import AssetBatchTracker
from .status_log import log_room_map_warning

_RUN_IDS = count(1)
_HEARTBEAT_SECONDS = 15.0
_PROGRESS_BUCKET_PERCENT = 5


class StageLoadProbe:
    """Observe stage, asset, MDL, streaming, and loading-status boundaries."""

    def __init__(
        self,
        context: Any,
        app: Any,
        stage_event_types: Mapping[str, object],
        *,
        log_warning: Callable[..., None] = log_room_map_warning,
        clock: Callable[[], float] = perf_counter,
        resource_sampler: Callable[[], Mapping[str, object]] = (
            _resource_snapshot
        ),
        event_dispatcher: Any | None = None,
        update_event_name: str | None = None,
    ) -> None:
        self._context = context
        self._app = app
        self._stage_event_types = dict(stage_event_types)
        self._log_warning = log_warning
        self._clock = clock
        self._resource_sampler = resource_sampler
        self._event_dispatcher = event_dispatcher
        self._update_event_name = update_event_name
        self._run_id = self._next_run_id()
        self._started_at = clock()
        self._last_emit_at = self._started_at
        self._performance_window_started_at = self._started_at
        self._last_performance_emit_at = self._started_at
        self._performance_update_count = 0
        self._last_progress_marker: tuple[object, ...] | None = None
        self._last_progress_change_at = self._started_at
        self._last_status_signature: tuple[object, ...] | None = None
        self._loading_status_pending = False
        self._mdl_parameter_count = 0
        self._asset_batches = AssetBatchTracker(clock)
        self._stage_subscriptions: tuple[object, ...] = ()
        self._update_subscription: object | None = None

    @staticmethod
    def _next_run_id() -> str:
        return f"SCENE-{next(_RUN_IDS):04d}"

    def start(self) -> None:
        """Subscribe to stage and update events owned by this probe instance."""

        if self._event_dispatcher is None:
            import carb.eventdispatcher

            self._event_dispatcher = carb.eventdispatcher.get_eventdispatcher()
        if self._update_event_name is None:
            import omni.kit.app

            self._update_event_name = omni.kit.app.GLOBAL_EVENT_UPDATE
        self._stage_subscriptions = tuple(
            self._event_dispatcher.observe_event(
                event_name=self._context.stage_event_name(event_type),
                on_event=self._on_stage_event,
                observer_name=(
                    "orms.stage_load_probe." f"{event_name.lower()}"
                ),
            )
            for event_name, event_type in self._stage_event_types.items()
        )
        self._update_subscription = self._event_dispatcher.observe_event(
            event_name=self._update_event_name,
            on_event=self._on_update,
            observer_name="orms.stage_load_probe.update",
        )
        self._log(
            "PROBE_ARMED",
            {
                "coverage": "from_probe_start_forward",
                "already_elapsed_stage_work_observable": False,
            },
        )
        self._sample_loading_status("probe_start", force=True)

    def stop(self) -> None:
        """Reset every owned event guard without altering Kit loading state."""

        for subscription in self._stage_subscriptions:
            reset = getattr(subscription, "reset", None)
            if callable(reset):
                reset()
        self._stage_subscriptions = ()
        reset = getattr(self._update_subscription, "reset", None)
        if callable(reset):
            reset()
        self._update_subscription = None

    def _stage_identifier(self) -> str:
        stage = self._context.get_stage()
        if stage is None:
            return "<none>"
        return stage.GetRootLayer().identifier

    def _log(self, state: str, details: Mapping[str, object]) -> None:
        payload: dict[str, object] = {
            "diagnostic_code": "ORMS-SCENE-LOAD-TRACE",
            "run_id": self._run_id,
            "elapsed_ms": round(
                (self._clock() - self._started_at) * 1000.0,
                3,
            ),
            "stage_identifier": self._stage_identifier(),
        }
        payload.update(details)
        self._log_warning(
            owner="SCENE LOAD PROBE",
            process="KIT STAGE LOAD TRACE",
            state=state,
            details=payload,
        )
        self._last_emit_at = self._clock()

    def _loading_status(self) -> tuple[str, int, int, bool]:
        message, files_loaded, total_files = (
            self._context.get_stage_loading_status()
        )
        return (
            str(message),
            int(files_loaded),
            int(total_files),
            bool(self._context.get_stage_streaming_status()),
        )

    def _start_asset_batch(self) -> None:
        if self._asset_batches.active:
            self._finish_asset_batch(
                "ASSET_BATCH_LOADING_SUPERSEDED",
                terminal_reason="new_assets_loading_event",
            )
        self._asset_batches.start(self._stage_identifier())

    def _finish_asset_batch(
        self,
        state: str,
        *,
        terminal_reason: str,
    ) -> bool:
        if not self._asset_batches.active:
            return False
        try:
            message, files_loaded, total_files, streaming_busy = (
                self._loading_status()
            )
        except Exception:
            message = ""
            files_loaded = 0
            total_files = 0
            streaming_busy = False
        details = self._asset_batches.finish(
            state,
            terminal_reason=terminal_reason,
            message=message,
            files_loaded=files_loaded,
            total_files=total_files,
            streaming_busy=streaming_busy,
        )
        if details is None:
            return False
        self._log(state, details)
        return True

    def _log_unobserved_asset_batch_terminal(
        self,
        state: str,
        *,
        terminal_reason: str,
        completion_observed: bool,
    ) -> None:
        self._log(
            state,
            {
                "asset_batch_id": "unobserved",
                "asset_batch_duration_ms": "unavailable",
                "duration_observable": False,
                "batch_terminal_reason": terminal_reason,
                "batch_completion_observed": completion_observed,
                "completion_scope": "terminal_event_only",
                "native_material_wait_complete": "unobservable",
                "renderer_idle_observable": False,
            },
        )

    def _sample_loading_status(
        self,
        reason: str,
        *,
        force: bool = False,
    ) -> None:
        try:
            message, files_loaded, total_files, streaming_busy = (
                self._loading_status()
            )
        except Exception as error:
            if force:
                self._log(
                    "STAGE_LOADING_STATUS_UNAVAILABLE",
                    {"sample_reason": reason, "error": repr(error)},
                )
            return

        progress_percent = (
            round(files_loaded * 100.0 / total_files, 3)
            if total_files > 0
            else None
        )
        progress_bucket = (
            int(progress_percent // _PROGRESS_BUCKET_PERCENT)
            * _PROGRESS_BUCKET_PERCENT
            if progress_percent is not None
            else None
        )
        pending = bool(message.strip()) or (
            total_files > 0 and files_loaded < total_files
        )
        signature = (
            message,
            total_files,
            progress_bucket,
            streaming_busy,
            pending,
        )
        now = self._clock()
        progress_marker = (message, files_loaded, total_files)
        if progress_marker != self._last_progress_marker:
            self._last_progress_marker = progress_marker
            self._last_progress_change_at = now
        self._asset_batches.record_status(message, total_files, now)
        heartbeat_due = (
            now - self._last_performance_emit_at >= _HEARTBEAT_SECONDS
        )
        transitioned_to_empty = self._loading_status_pending and not pending
        if not (
            force
            or signature != self._last_status_signature
            or heartbeat_due
            or transitioned_to_empty
        ):
            return

        if transitioned_to_empty:
            state = "STAGE_LOADING_STATUS_EMPTY"
        elif pending:
            state = "STAGE_LOADING_PROGRESS"
        elif heartbeat_due:
            state = "KIT_PERFORMANCE_HEARTBEAT"
        else:
            state = "STAGE_LOADING_STATUS_SNAPSHOT"
        details: dict[str, object] = {
            "sample_reason": reason,
            "loading_message": message or "<empty>",
            "files_loaded": files_loaded,
            "total_files": total_files,
            "progress_percent": (
                progress_percent
                if progress_percent is not None
                else "unavailable"
            ),
            "streaming_busy": streaming_busy,
            "loading_status_pending": pending,
            "loading_status_stalled_for_ms": (
                round(
                    (now - self._last_progress_change_at) * 1000.0,
                    3,
                )
                if pending
                else "not_applicable"
            ),
            "loading_status_idle_for_ms": (
                round(
                    (now - self._last_progress_change_at) * 1000.0,
                    3,
                )
                if not pending
                else "not_applicable"
            ),
            "asset_batch_active": self._asset_batches.active,
            "completion_claim": False,
            "heartbeat": heartbeat_due,
            "renderer_idle_observable": False,
        }
        if heartbeat_due:
            performance_duration = now - self._performance_window_started_at
            average_fps = (
                self._performance_update_count / performance_duration
                if performance_duration > 0.0
                else 0.0
            )
            details.update(
                {
                    "performance_window_seconds": round(
                        performance_duration,
                        3,
                    ),
                    "kit_update_fps": round(average_fps, 3),
                    "kit_update_frame_time_ms": (
                        round(1000.0 / average_fps, 3)
                        if average_fps > 0.0
                        else "unavailable"
                    ),
                    "kit_update_count": self._performance_update_count,
                    "app_ready": bool(self._app.is_app_ready()),
                }
            )
            try:
                details.update(self._resource_sampler())
            except Exception as error:
                details["resource_metrics_error"] = repr(error)
            self._performance_window_started_at = now
            self._last_performance_emit_at = now
            self._performance_update_count = 0
        self._log(state, details)
        self._last_status_signature = signature
        self._loading_status_pending = pending

    def _on_update(self, _event: object) -> None:
        self._performance_update_count += 1
        self._sample_loading_status("kit_update")

    def _reset_for_stage_open(self) -> None:
        self._run_id = self._next_run_id()
        self._started_at = self._clock()
        self._last_emit_at = self._started_at
        self._performance_window_started_at = self._started_at
        self._last_performance_emit_at = self._started_at
        self._performance_update_count = 0
        self._last_progress_marker = None
        self._last_progress_change_at = self._started_at
        self._last_status_signature = None
        self._loading_status_pending = False
        self._mdl_parameter_count = 0
        self._asset_batches.reset_for_stage_open()

    def _on_stage_event(self, event: object) -> None:
        event_type_value = getattr(event, "type", None)
        if event_type_value is None:
            event_name_value = getattr(event, "event_name", "")
            event_type_value = self._context.stage_event_type(event_name_value)
        event_type = int(event_type_value)
        event_name = next(
            (
                name
                for name, value in self._stage_event_types.items()
                if int(value) == event_type
            ),
            "UNKNOWN",
        )
        if event_name == "OPENING":
            self._finish_asset_batch(
                "ASSET_BATCH_LOADING_SUPERSEDED",
                terminal_reason="stage_opening",
            )
            self._reset_for_stage_open()
            self._log("STAGE_OPENING", {})
        elif event_name == "OPENED":
            self._log("STAGE_OPENED", {})
        elif event_name == "ASSETS_LOADING":
            self._start_asset_batch()
            self._log(
                "ASSET_BATCH_LOADING_STARTED",
                {"asset_batch_id": self._asset_batches.batch_id},
            )
        elif event_name == "ASSETS_LOADED":
            finished = self._finish_asset_batch(
                "ASSET_BATCH_LOADING_COMPLETE",
                terminal_reason="assets_loaded_event",
            )
            if not finished:
                self._log_unobserved_asset_batch_terminal(
                    "ASSET_BATCH_LOADING_COMPLETE_UNTIMED",
                    terminal_reason="assets_loaded_without_observed_start",
                    completion_observed=True,
                )
        elif event_name == "ASSETS_LOAD_ABORTED":
            finished = self._finish_asset_batch(
                "ASSET_BATCH_LOADING_ABORTED",
                terminal_reason="assets_load_aborted_event",
            )
            if not finished:
                self._log_unobserved_asset_batch_terminal(
                    "ASSET_BATCH_LOADING_ABORTED_UNTIMED",
                    terminal_reason=(
                        "assets_load_aborted_without_observed_start"
                    ),
                    completion_observed=False,
                )
        elif event_name == "MDL_PARAM_LOADED":
            self._mdl_parameter_count += 1
            self._log(
                "MDL_PARAMETER_LOADED",
                {"mdl_parameter_event_count": self._mdl_parameter_count},
            )
        elif event_name == "HYDRA_GEO_STREAMING_STARTED":
            self._log("GEOMETRY_STREAMING_STARTED", {})
        elif event_name == "HYDRA_GEO_STREAMING_STOPPED":
            self._log("GEOMETRY_STREAMING_STOPPED", {})
        elif event_name == "OPEN_FAILED":
            self._finish_asset_batch(
                "ASSET_BATCH_LOADING_SUPERSEDED",
                terminal_reason="stage_open_failed",
            )
            self._log("STAGE_OPEN_FAILED", {})
        elif event_name == "CLOSING":
            self._finish_asset_batch(
                "ASSET_BATCH_LOADING_SUPERSEDED",
                terminal_reason="stage_closing",
            )
            self._log("STAGE_CLOSING", {})
        elif event_name == "CLOSED":
            self._log("STAGE_CLOSED", {})
        else:
            return
        self._sample_loading_status(f"stage_event:{event_name}", force=True)


_probe: StageLoadProbe | None = None


def _stage_event_types(omni_usd: Any) -> dict[str, object]:
    names = (
        "OPENING",
        "OPENED",
        "OPEN_FAILED",
        "CLOSING",
        "CLOSED",
        "ASSETS_LOADING",
        "ASSETS_LOADED",
        "ASSETS_LOAD_ABORTED",
        "MDL_PARAM_LOADED",
        "HYDRA_GEO_STREAMING_STARTED",
        "HYDRA_GEO_STREAMING_STOPPED",
    )
    return {
        name: getattr(omni_usd.StageEventType, name)
        for name in names
        if getattr(omni_usd.StageEventType, name, None) is not None
    }


def start() -> StageLoadProbe:
    """Start tracing immediately, including an already-running load batch."""

    import omni.kit.app
    import omni.usd

    global _probe
    stop()
    _probe = StageLoadProbe(
        omni.usd.get_context(),
        omni.kit.app.get_app(),
        _stage_event_types(omni.usd),
    )
    _probe.start()
    return _probe


def stop() -> None:
    """Release Kit subscriptions owned by the probe."""

    global _probe
    if _probe is not None:
        _probe.stop()
        _probe = None
