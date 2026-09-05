# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Own ORMS runtime pause, resume, failure, and teardown transitions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any


class RuntimeState(Enum):
    """Describe the artist-visible lifecycle state of the active stage."""

    INACTIVE = "Inactive"
    RUNNING = "Running"
    STOPPED = "Stopped"
    FAILED = "Failed"


@dataclass(frozen=True)
class _RuntimeSession:
    classifier: Any
    camera_bridge: Any
    teardown: Callable[[], None]


class RuntimeLifecycleController:
    """Pause live updates independently from removing ORMS-owned USD state."""

    def __init__(
        self,
        state_changed: Callable[[RuntimeState], None] | None = None,
    ) -> None:
        self._state = RuntimeState.INACTIVE
        self._session: _RuntimeSession | None = None
        self._state_changed = state_changed

    @property
    def state(self) -> RuntimeState:
        """Return the current artist-visible lifecycle state."""

        return self._state

    @property
    def classifier(self) -> Any | None:
        """Expose the active classifier to service-owned setting commands."""

        return self._session.classifier if self._session is not None else None

    def attach(
        self,
        classifier: Any,
        camera_bridge: Any,
        teardown: Callable[[], None],
    ) -> None:
        """Own one newly started runtime session and mark it running."""

        self.teardown()
        self._session = _RuntimeSession(
            classifier,
            camera_bridge,
            teardown,
        )
        self._set_state(RuntimeState.RUNNING)

    def pause(self) -> bool:
        """Freeze live USD and camera updates without detaching their layer."""

        if self._session is None or self._state is not RuntimeState.RUNNING:
            return False
        self._session.camera_bridge.pause()
        self._session.classifier.pause()
        self._set_state(RuntimeState.STOPPED)
        return True

    def resume(self) -> bool:
        """Resume a frozen session without reclassifying its current result."""

        if self._session is None or self._state is not RuntimeState.STOPPED:
            return False
        self._session.classifier.resume()
        self._session.camera_bridge.resume()
        self._set_state(RuntimeState.RUNNING)
        return True

    def set_camera_input_paths(self, paths: Sequence[str]) -> bool:
        """Retarget the live camera bridge after material-family changes."""

        if self._session is None or self._state is not RuntimeState.RUNNING:
            return False
        self._session.camera_bridge.set_material_input_paths(paths)
        return True

    def teardown(self) -> bool:
        """Remove runtime callbacks and USD state through its teardown owner."""

        session, self._session = self._session, None
        try:
            if session is not None:
                session.teardown()
        finally:
            self._set_state(RuntimeState.INACTIVE)
        return session is not None

    def fail(self) -> None:
        """Tear down partial runtime ownership and expose recoverable failure."""

        session, self._session = self._session, None
        try:
            if session is not None:
                session.teardown()
        finally:
            self._set_state(RuntimeState.FAILED)

    def _set_state(self, state: RuntimeState) -> None:
        if state is self._state:
            return
        self._state = state
        if self._state_changed is not None:
            self._state_changed(state)
