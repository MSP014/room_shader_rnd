"""Build the compact lifecycle controls shown on the ORMS classifier tab."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from msp.orms.shared_room.ui_sections import collapsable_frame
from msp.orms.shared_room.ui_tooltips import with_wrapped_tooltip

from .lifecycle import RuntimeState

LIFECYCLE_ACTION_LABELS = (
    ("start", "Start"),
    ("restart", "Restart"),
    ("stop", "Stop"),
    ("restore", "Restore Original Asset"),
)

LIFECYCLE_ACTION_HELP = {
    "start": "Start activates ORMS or resumes a stopped result.",
    "stop": "Stop freezes the current result and releases live updates.",
    "restart": "Restart removes and rebuilds ORMS from current settings.",
    "restore": (
        "Restore Original Asset removes every ORMS-owned Session Layer "
        "opinion."
    ),
}


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
        *,
        collapsed: bool = False,
        collapsed_changed: Callable[[bool], None] | None = None,
    ) -> None:
        self._callbacks = callbacks
        self._state = state
        self._status_label: Any | None = None
        self._buttons: dict[str, Any] = {}
        self._collapsed = collapsed
        self._collapsed_changed = collapsed_changed

    def _remember_collapsed(self, collapsed: bool) -> None:
        """Retain the choice locally and in the containing panel state."""

        self._collapsed = bool(collapsed)
        if self._collapsed_changed is not None:
            self._collapsed_changed(self._collapsed)

    def build(self) -> None:
        """Build the lifecycle block inside the current OmniUI parent."""

        import omni.ui as ui

        frame = collapsable_frame(
            ui,
            "Runtime lifecycle",
            collapsed=self._collapsed,
            collapsed_changed=self._remember_collapsed,
        )
        with frame:
            with ui.VStack(spacing=6):
                self._status_label = ui.Label(
                    "",
                    height=22,
                    name="title",
                )
                with ui.HStack(height=30, spacing=4):
                    for key, label in LIFECYCLE_ACTION_LABELS:
                        button = ui.Button(
                            label,
                            clicked_fn=getattr(self._callbacks, key),
                        )
                        with_wrapped_tooltip(
                            button,
                            LIFECYCLE_ACTION_HELP[key],
                        )
                        self._buttons[key] = button
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
