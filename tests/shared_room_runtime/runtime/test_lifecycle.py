# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect ORMS lifecycle freeze, resume, and cleanup semantics."""

from msp.orms.runtime.lifecycle import (
    RuntimeLifecycleController,
    RuntimeState,
)


class _RuntimePart:
    def __init__(self) -> None:
        self.pause_count = 0
        self.resume_count = 0

    def pause(self) -> None:
        self.pause_count += 1

    def resume(self) -> None:
        self.resume_count += 1


def _attached_lifecycle():
    lifecycle = RuntimeLifecycleController()
    classifier = _RuntimePart()
    camera = _RuntimePart()
    teardown_calls = []
    lifecycle.attach(classifier, camera, lambda: teardown_calls.append(True))
    return lifecycle, classifier, camera, teardown_calls


def test_stop_freezes_runtime_without_detaching_owned_state():
    lifecycle, classifier, camera, teardown_calls = _attached_lifecycle()

    assert lifecycle.stop()

    assert teardown_calls == []
    assert lifecycle.classifier is classifier
    assert classifier.pause_count == 1
    assert camera.pause_count == 1
    assert lifecycle.state is RuntimeState.STOPPED


def test_repeated_stop_does_not_repeat_pause_callbacks():
    lifecycle, classifier, camera, teardown_calls = _attached_lifecycle()

    lifecycle.stop()

    assert not lifecycle.stop()
    assert teardown_calls == []
    assert classifier.pause_count == 1
    assert camera.pause_count == 1
    assert lifecycle.state is RuntimeState.STOPPED


def test_start_resumes_the_same_frozen_runtime_session():
    lifecycle, classifier, camera, teardown_calls = _attached_lifecycle()

    lifecycle.stop()

    assert lifecycle.resume()
    assert lifecycle.classifier is classifier
    assert lifecycle.state is RuntimeState.RUNNING
    assert classifier.resume_count == 1
    assert camera.resume_count == 1
    assert teardown_calls == []


def test_restore_after_stop_tears_down_the_frozen_session_once():
    lifecycle, classifier, camera, teardown_calls = _attached_lifecycle()
    lifecycle.stop()

    assert lifecycle.teardown()
    assert not lifecycle.teardown()

    assert teardown_calls == [True]
    assert classifier.pause_count == 1
    assert camera.pause_count == 1
    assert lifecycle.state is RuntimeState.INACTIVE


def test_stop_is_a_noop_without_an_active_runtime_session():
    lifecycle = RuntimeLifecycleController()

    assert not lifecycle.stop()
    assert lifecycle.state is RuntimeState.INACTIVE
