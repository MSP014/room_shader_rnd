"""Build the compact lifecycle controls shown on the ORMS classifier tab."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .lifecycle import RuntimeState

LIFECYCLE_ACTION_LABELS = (
    ("start", "Start"),
    ("restart", "Restart"),
    ("stop", "Stop"),
    ("restore", "Restore Original Asset"),
)


def enabled_lifecycle_actions(state: RuntimeState) -> frozenset[str]:
    """Return commands that are valid for the visible runtime state."""

    if state is RuntimeState.RUNNING:
        return frozenset({"restart", "stop", "restore"})
    if state is RuntimeState.STOPPED:
        return frozenset({"start", "restart", "restore"})
    if state is RuntimeState.FAILED:
        return frozenset({"start", "restart", "restore"})
    return frozenset({"start"})


@dataclass(frozen=True)
class LifecycleCallbacks:
    """Route lifecycle button clicks without giving UI ownership of runtime."""

    start: Callable[[], None]
    restart: Callable[[], None]
    stop: Callable[[], None]
    restore: Callable[[], None]


class LifecycleControls:
    """Present state-aware buttons while delegating every transition."""

    def __init__(
        self,
        callbacks: LifecycleCallbacks,
        state: RuntimeState = RuntimeState.INACTIVE,
    ) -> None:
        self._callbacks = callbacks
        self._state = state
        self._status_label: Any | None = None
        self._buttons: dict[str, Any] = {}

    def build(self) -> None:
        """Build the lifecycle block inside the current OmniUI parent."""

        import omni.ui as ui

        with ui.CollapsableFrame("Runtime lifecycle", collapsed=False):
            with ui.VStack(spacing=6):
                self._status_label = ui.Label(
                    "",
                    height=22,
                    name="title",
                )
                with ui.HStack(height=30, spacing=4):
                    for key, label in LIFECYCLE_ACTION_LABELS:
                        self._buttons[key] = ui.Button(
                            label,
                            clicked_fn=getattr(self._callbacks, key),
                        )
        self.set_state(self._state)

    def set_state(self, state: RuntimeState) -> None:
        """Refresh the status text and valid actions for one lifecycle state."""

        self._state = state
        if self._status_label is None:
            return
        self._status_label.text = f"Status: {state.value}"
        enabled_actions = enabled_lifecycle_actions(state)
        for key, button in self._buttons.items():
            button.enabled = key in enabled_actions
