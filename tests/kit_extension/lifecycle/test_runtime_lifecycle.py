# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect ORMS lifecycle transitions independently from Kit and OmniUI."""

import pytest
from msp.orms.runtime.lifecycle import (
    RuntimeLifecycleController,
    RuntimeState,
)


class _RuntimePart:
    def __init__(self) -> None:
        self.pause_count = 0
        self.resume_count = 0
        self.material_input_paths = None

    def pause(self) -> None:
        self.pause_count += 1

    def resume(self) -> None:
        self.resume_count += 1

    def set_material_input_paths(self, paths) -> None:
        self.material_input_paths = tuple(paths)


def test_stop_and_start_freeze_and_resume_one_owned_session():
    states = []
    teardown_calls = []
    classifier = _RuntimePart()
    camera_bridge = _RuntimePart()
    lifecycle = RuntimeLifecycleController(states.append)
    lifecycle.attach(
        classifier,
        camera_bridge,
        lambda: teardown_calls.append("teardown"),
    )

    assert lifecycle.state is RuntimeState.RUNNING
    assert lifecycle.classifier is classifier
    assert lifecycle.pause() is True
    assert lifecycle.state is RuntimeState.STOPPED
    assert classifier.pause_count == 1
    assert camera_bridge.pause_count == 1
    assert teardown_calls == []

    assert lifecycle.resume() is True
    assert lifecycle.state is RuntimeState.RUNNING
    assert classifier.resume_count == 1
    assert camera_bridge.resume_count == 1
    assert teardown_calls == []
    assert states == [
        RuntimeState.RUNNING,
        RuntimeState.STOPPED,
        RuntimeState.RUNNING,
    ]


def test_restore_tears_down_once_and_returns_to_inactive():
    teardown_calls = []
    lifecycle = RuntimeLifecycleController()
    lifecycle.attach(
        _RuntimePart(),
        _RuntimePart(),
        lambda: teardown_calls.append("teardown"),
    )

    assert lifecycle.teardown() is True
    assert lifecycle.teardown() is False
    assert lifecycle.state is RuntimeState.INACTIVE
    assert lifecycle.classifier is None
    assert teardown_calls == ["teardown"]


def test_running_session_retargets_camera_inputs_without_restart():
    lifecycle = RuntimeLifecycleController()
    camera_bridge = _RuntimePart()
    lifecycle.attach(_RuntimePart(), camera_bridge, lambda: None)

    changed = lifecycle.set_camera_input_paths(("/Looks/New.inputs:camera",))

    assert changed is True
    assert camera_bridge.material_input_paths == ("/Looks/New.inputs:camera",)


def test_failure_removes_partial_session_and_remains_recoverable():
    teardown_calls = []
    lifecycle = RuntimeLifecycleController()
    lifecycle.attach(
        _RuntimePart(),
        _RuntimePart(),
        lambda: teardown_calls.append("teardown"),
    )

    lifecycle.fail()

    assert lifecycle.state is RuntimeState.FAILED
    assert lifecycle.classifier is None
    assert lifecycle.pause() is False
    assert lifecycle.resume() is False
    assert teardown_calls == ["teardown"]


def test_teardown_failure_still_releases_session_ownership():
    lifecycle = RuntimeLifecycleController()

    def fail_teardown() -> None:
        raise RuntimeError("test teardown failure")

    lifecycle.attach(
        _RuntimePart(),
        _RuntimePart(),
        fail_teardown,
    )

    with pytest.raises(RuntimeError, match="test teardown failure"):
        lifecycle.teardown()

    assert lifecycle.state is RuntimeState.INACTIVE
    assert lifecycle.classifier is None
