"""Protect the Kit stage-event adapter, progress sampling, and teardown."""

from __future__ import annotations

from enum import IntEnum
from types import SimpleNamespace

from tools.omniverse.runtime.stage_load_probe import StageLoadProbe


class _Guard:
    def __init__(self) -> None:
        self.was_reset = False

    def reset(self) -> None:
        self.was_reset = True


class _Dispatcher:
    def __init__(self) -> None:
        self.callbacks = {}
        self.guards = []

    def observe_event(self, *, event_name, on_event, observer_name):
        guard = _Guard()
        self.callbacks.setdefault(event_name, []).append(on_event)
        self.guards.append((observer_name, guard))
        return guard

    def emit(self, event_name):
        event = SimpleNamespace(event_name=event_name)
        for callback in self.callbacks.get(event_name, ()):
            callback(event)


class _Context:
    def __init__(self) -> None:
        self.status = ("Loading material...", 83, 100)
        self.streaming = False
        self.stage = SimpleNamespace(
            GetRootLayer=lambda: SimpleNamespace(identifier="fixture.usda")
        )

    def stage_event_name(self, event_type):
        return f"stage:{int(event_type)}"

    def stage_event_type(self, event_name):
        return int(str(event_name).rsplit(":", 1)[-1])

    def get_stage_loading_status(self):
        return self.status

    def get_stage_streaming_status(self):
        return self.streaming

    def get_stage(self):
        return self.stage


class _App:
    def is_app_ready(self):
        return True


class _StageEventType(IntEnum):
    OPENED = 2


class _StrictContext(_Context):
    def stage_event_name(self, event_type):
        if not isinstance(event_type, _StageEventType):
            raise TypeError("stage_event_name requires StageEventType")
        return super().stage_event_name(event_type)


def _probe(context, app, stage_event_types, **kwargs):
    dispatcher = _Dispatcher()
    return (
        StageLoadProbe(
            context,
            app,
            stage_event_types,
            event_dispatcher=dispatcher,
            update_event_name="kit:update",
            **kwargs,
        ),
        dispatcher,
    )


def test_probe_records_progress_and_transition_to_idle():
    context = _Context()
    app = _App()
    records = []
    now = [10.0]
    probe, dispatcher = _probe(
        context,
        app,
        {"ASSETS_LOADED": 8},
        log_status=lambda **record: records.append(record),
        clock=lambda: now[0],
    )

    probe.start()

    assert [record["state"] for record in records] == [
        "PROBE_ARMED",
        "STAGE_LOADING_PROGRESS",
    ]
    assert records[-1]["details"]["files_loaded"] == 83
    assert records[-1]["details"]["progress_percent"] == 83.0

    context.status = ("Loading material...", 98, 100)
    now[0] = 12.0
    dispatcher.emit("kit:update")
    assert records[-1]["state"] == "STAGE_LOADING_PROGRESS"
    assert records[-1]["details"]["files_loaded"] == 98

    dispatcher.emit(context.stage_event_name(8))
    assert records[-2]["state"] == ("ASSET_BATCH_LOADING_COMPLETE_UNTIMED")
    assert records[-2]["details"]["asset_batch_duration_ms"] == ("unavailable")
    assert records[-2]["details"]["duration_observable"] is False
    assert records[-2]["details"]["batch_completion_observed"] is True
    assert records[-1]["state"] == "STAGE_LOADING_PROGRESS"

    context.status = ("", 0, 0)
    now[0] = 13.0
    dispatcher.emit("kit:update")
    assert records[-1]["state"] == "STAGE_LOADING_STATUS_EMPTY"
    assert records[-1]["details"]["loading_status_pending"] is False
    assert (
        records[-1]["details"]["loading_status_stalled_for_ms"]
        == "not_applicable"
    )
    assert records[-1]["details"]["loading_status_idle_for_ms"] == 0.0
    assert records[-1]["details"]["completion_claim"] is False
    assert records[-1]["details"]["renderer_idle_observable"] is False


def test_probe_emits_performance_heartbeat_after_fifteen_seconds():
    context = _Context()
    app = _App()
    records = []
    now = [20.0]
    probe, dispatcher = _probe(
        context,
        app,
        {},
        log_status=lambda **record: records.append(record),
        clock=lambda: now[0],
        resource_sampler=lambda: {
            "process_working_set_gib": 7.5,
            "gpu_memory_fields": {"used": 4.5},
        },
    )
    probe.start()
    initial_count = len(records)

    now[0] = 34.9
    dispatcher.emit("kit:update")
    assert len(records) == initial_count

    now[0] = 35.0
    dispatcher.emit("kit:update")
    assert records[-1]["state"] == "STAGE_LOADING_PROGRESS"
    assert records[-1]["details"]["heartbeat"] is True
    assert records[-1]["details"]["performance_window_seconds"] == 15.0
    assert records[-1]["details"]["kit_update_fps"] == 0.133
    assert records[-1]["details"]["process_working_set_gib"] == 7.5
    assert records[-1]["details"]["gpu_memory_fields"] == {"used": 4.5}


def test_probe_summarises_asset_batch_without_claiming_renderer_completion():
    context = _Context()
    app = _App()
    records = []
    now = [30.0]
    probe, dispatcher = _probe(
        context,
        app,
        {"OPENING": 1, "ASSETS_LOADING": 7, "ASSETS_LOADED": 8},
        log_status=lambda **record: records.append(record),
        clock=lambda: now[0],
    )
    probe.start()

    dispatcher.emit(context.stage_event_name(7))
    now[0] = 31.0
    dispatcher.emit(context.stage_event_name(1))
    dispatcher.emit(context.stage_event_name(7))
    context.status = ("/World/Looks/RoomMapSource/Shader", 15, 18)
    now[0] = 32.0
    dispatcher.emit("kit:update")
    now[0] = 40.0
    dispatcher.emit(context.stage_event_name(8))

    superseded = next(
        record
        for record in records
        if record["state"] == "ASSET_BATCH_LOADING_SUPERSEDED"
    )
    assert superseded["details"]["asset_batch_duration_ms"] == 1000.0
    assert superseded["details"]["batch_terminal_reason"] == "stage_opening"
    assert superseded["details"]["batch_completion_observed"] is False

    summary = next(
        record
        for record in records
        if record["state"] == "ASSET_BATCH_LOADING_COMPLETE"
    )
    details = summary["details"]
    assert details["asset_batch_id"] == 1
    assert details["asset_batch_duration_ms"] == 9000.0
    assert details["max_total_files"] == 100
    assert details["longest_loading_message"] == (
        "/World/Looks/RoomMapSource/Shader"
    )
    assert details["longest_loading_message_ms"] == 8000.0
    assert details["completion_scope"] == "current_async_asset_batch"
    assert details["batch_terminal_reason"] == "assets_loaded_event"
    assert details["batch_completion_observed"] is True
    assert details["native_material_wait_complete"] == "unobservable"


def test_probe_releases_events_2_guards_on_stop():
    context = _Context()
    probe, dispatcher = _probe(
        context,
        _App(),
        {"OPENED": 2},
        log_status=lambda **_record: None,
    )

    probe.start()
    guards = [guard for _name, guard in dispatcher.guards]
    probe.stop()

    assert guards
    assert all(guard.was_reset for guard in guards)


def test_probe_passes_stage_event_enum_to_events_2_name_adapter():
    probe, dispatcher = _probe(
        _StrictContext(),
        _App(),
        {"OPENED": _StageEventType.OPENED},
        log_status=lambda **_record: None,
    )

    probe.start()

    assert "stage:2" in dispatcher.callbacks


def test_probe_reserves_warning_severity_for_actionable_failures():
    context = _Context()
    statuses = []
    warnings = []
    probe, dispatcher = _probe(
        context,
        _App(),
        {"OPEN_FAILED": 3},
        log_status=lambda **record: statuses.append(record),
        log_warning=lambda **record: warnings.append(record),
    )
    probe.start()

    dispatcher.emit(context.stage_event_name(3))

    assert warnings[-1]["state"] == "STAGE_OPEN_FAILED"
    assert all(record["state"] != "STAGE_OPEN_FAILED" for record in statuses)
