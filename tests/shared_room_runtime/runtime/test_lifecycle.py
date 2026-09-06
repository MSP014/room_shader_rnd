# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect ORMS lifecycle cleanup and restartable Stop semantics."""

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


def test_stop_detaches_runtime_and_enters_restartable_state():
    lifecycle, _classifier, _camera, teardown_calls = _attached_lifecycle()

    assert lifecycle.stop()

    assert teardown_calls == [True]
    assert lifecycle.classifier is None
    assert lifecycle.state is RuntimeState.STOPPED


def test_repeated_stop_does_not_repeat_cleanup():
    lifecycle, _classifier, _camera, teardown_calls = _attached_lifecycle()

    lifecycle.stop()

    assert not lifecycle.stop()
    assert teardown_calls == [True]
    assert lifecycle.state is RuntimeState.STOPPED


def test_stopped_lifecycle_cannot_resume_detached_state():
    lifecycle, classifier, camera, _teardown_calls = _attached_lifecycle()

    lifecycle.stop()

    assert not lifecycle.resume()
    assert classifier.resume_count == 0
    assert camera.resume_count == 0


def test_teardown_after_stop_returns_to_inactive_without_extra_cleanup():
    lifecycle, _classifier, _camera, teardown_calls = _attached_lifecycle()
    lifecycle.stop()

    assert not lifecycle.teardown()

    assert teardown_calls == [True]
    assert lifecycle.state is RuntimeState.INACTIVE
