"""Trace the observable Kit stage-loading pipeline in warning-visible logs."""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable, Mapping
from itertools import count
from time import perf_counter
from typing import Any

try:
    from .status_log import log_room_map_warning
except ImportError:
    from status_log import log_room_map_warning


_RUN_IDS = count(1)
_HEARTBEAT_SECONDS = 15.0
_PROGRESS_BUCKET_PERCENT = 5


def _windows_memory_snapshot() -> dict[str, object]:
    """Return process and host memory counters without a third-party module."""

    if sys.platform != "win32":
        return {"host_memory_metrics": "unsupported_platform"}

    class _ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    class _MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    gib = float(1024**3)
    details: dict[str, object] = {}
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = ctypes.c_void_p
        get_process_memory_info = psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_ProcessMemoryCountersEx),
            ctypes.c_ulong,
        ]
        get_process_memory_info.restype = ctypes.c_int

        counters = _ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(counters)
        success = get_process_memory_info(
            get_current_process(),
            ctypes.byref(counters),
            counters.cb,
        )
        if success:
            details.update(
                {
                    "process_working_set_gib": round(
                        counters.WorkingSetSize / gib,
                        3,
                    ),
                    "process_private_commit_gib": round(
                        counters.PrivateUsage / gib,
                        3,
                    ),
                }
            )
        else:
            details["process_memory_error"] = (
                "GetProcessMemoryInfo failed: "
                f"winerror={ctypes.get_last_error()}"
            )
    except Exception as error:
        details["process_memory_error"] = repr(error)

    try:
        if "kernel32" not in locals():
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        global_memory_status = kernel32.GlobalMemoryStatusEx
        global_memory_status.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
        global_memory_status.restype = ctypes.c_int
        memory = _MemoryStatusEx()
        memory.dwLength = ctypes.sizeof(memory)
        if global_memory_status(ctypes.byref(memory)):
            details.update(
                {
                    "system_available_memory_gib": round(
                        memory.ullAvailPhys / gib,
                        3,
                    ),
                    "system_memory_load_percent": int(memory.dwMemoryLoad),
                }
            )
        else:
            details["system_memory_error"] = (
                "GlobalMemoryStatusEx failed: "
                f"winerror={ctypes.get_last_error()}"
            )
    except Exception as error:
        details["system_memory_error"] = repr(error)
    return details


def _hydra_memory_snapshot() -> dict[str, object]:
    """Read public Hydra device counters when that extension is available."""

    try:
        import omni.hydra.engine.stats as engine_stats

        devices = engine_stats.get_device_info(0)
        if not devices:
            return {"gpu_memory_metrics": "no_device"}
        device = devices[0]
        memory_fields = {
            str(name): value
            for name, value in device.items()
            if "memory" in str(name).lower() or "budget" in str(name).lower()
        }
        details: dict[str, object] = {
            "gpu_device": device.get("description", "unavailable"),
            "gpu_memory_fields": memory_fields or "unavailable",
        }
        total_fields = {
            str(item.get("category", "unknown")): item.get("size")
            for item in engine_stats.get_mem_stats()
            if "total" in str(item.get("category", "")).lower()
        }
        details["hydra_total_memory_fields"] = total_fields or "unavailable"
        return details
    except Exception as error:
        return {"gpu_memory_metrics": f"unavailable: {error!r}"}


def _resource_snapshot() -> dict[str, object]:
    details = _windows_memory_snapshot()
    details.update(_hydra_memory_snapshot())
    return details


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
        self._asset_batch_id = 0
        self._asset_batch_active = False
        self._asset_batch_started_at: float | None = None
        self._asset_batch_stage_identifier: str | None = None
        self._batch_max_total_files = 0
        self._batch_current_message = ""
        self._batch_current_message_started_at: float | None = None
        self._batch_longest_message = "<none>"
        self._batch_longest_message_ms = 0.0
        self._stage_subscriptions: tuple[object, ...] = ()
        self._update_subscription: object | None = None

    @staticmethod
    def _next_run_id() -> str:
        return f"SCENE-{next(_RUN_IDS):04d}"

    def start(self) -> None:
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

    def _close_batch_message_interval(self, now: float) -> None:
        if self._batch_current_message_started_at is None:
            return
        duration_ms = (now - self._batch_current_message_started_at) * 1000.0
        if duration_ms > self._batch_longest_message_ms:
            self._batch_longest_message = (
                self._batch_current_message or "<empty>"
            )
            self._batch_longest_message_ms = duration_ms
        self._batch_current_message_started_at = None

    def _record_batch_status(
        self,
        message: str,
        total_files: int,
        now: float,
    ) -> None:
        if not self._asset_batch_active:
            return
        self._batch_max_total_files = max(
            self._batch_max_total_files,
            total_files,
        )
        if message == self._batch_current_message:
            return
        self._close_batch_message_interval(now)
        self._batch_current_message = message
        if message:
            self._batch_current_message_started_at = now

    def _start_asset_batch(self) -> None:
        if self._asset_batch_active:
            self._finish_asset_batch(
                "ASSET_BATCH_LOADING_SUPERSEDED",
                terminal_reason="new_assets_loading_event",
            )
        self._asset_batch_id += 1
        self._asset_batch_active = True
        self._asset_batch_started_at = self._clock()
        self._asset_batch_stage_identifier = self._stage_identifier()
        self._batch_max_total_files = 0
        self._batch_current_message = ""
        self._batch_current_message_started_at = None
        self._batch_longest_message = "<none>"
        self._batch_longest_message_ms = 0.0

    def _finish_asset_batch(
        self,
        state: str,
        *,
        terminal_reason: str,
    ) -> bool:
        if not self._asset_batch_active:
            return False
        now = self._clock()
        self._close_batch_message_interval(now)
        try:
            message, files_loaded, total_files, streaming_busy = (
                self._loading_status()
            )
        except Exception:
            message = ""
            files_loaded = 0
            total_files = 0
            streaming_busy = False
        self._batch_max_total_files = max(
            self._batch_max_total_files,
            total_files,
        )
        duration_ms = (
            round((now - self._asset_batch_started_at) * 1000.0, 3)
            if self._asset_batch_started_at is not None
            else "unavailable"
        )
        self._log(
            state,
            {
                "asset_batch_id": self._asset_batch_id,
                "asset_batch_stage_identifier": (
                    self._asset_batch_stage_identifier or "<none>"
                ),
                "asset_batch_duration_ms": duration_ms,
                "max_total_files": self._batch_max_total_files,
                "longest_loading_message": self._batch_longest_message,
                "longest_loading_message_ms": round(
                    self._batch_longest_message_ms,
                    3,
                ),
                "final_loading_message": message or "<empty>",
                "final_files_loaded": files_loaded,
                "final_total_files": total_files,
                "final_streaming_busy": streaming_busy,
                "completion_scope": "current_async_asset_batch",
                "batch_terminal_reason": terminal_reason,
                "batch_completion_observed": (
                    state == "ASSET_BATCH_LOADING_COMPLETE"
                ),
                "native_material_wait_complete": "unobservable",
                "renderer_idle_observable": False,
            },
        )
        self._asset_batch_active = False
        self._asset_batch_started_at = None
        self._asset_batch_stage_identifier = None
        self._batch_current_message_started_at = None
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
        self._record_batch_status(message, total_files, now)
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
            "asset_batch_active": self._asset_batch_active,
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
        self._asset_batch_id = 0
        self._asset_batch_started_at = None
        self._asset_batch_stage_identifier = None
        self._batch_current_message_started_at = None

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
                {"asset_batch_id": self._asset_batch_id},
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
