# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Present live Set-scoped material update outcomes beside their controls."""

from __future__ import annotations

from collections.abc import Callable

MaterialChange = Callable[[str, str, object], int]
MaterialReset = Callable[[str, str | None], int]


class MaterialUpdateFeedback:
    """Own transient material status and current OmniUI label references."""

    def __init__(self, rebuild: Callable[[], None]) -> None:
        self._rebuild = rebuild
        self._change: MaterialChange | None = None
        self._reset: MaterialReset | None = None
        self._statuses: dict[str, str] = {}
        self._labels: dict[str, object] = {}

    def start(self, change: MaterialChange, reset: MaterialReset) -> None:
        """Bind service commands for this window lifetime."""

        self._change = change
        self._reset = reset

    def begin_build(self) -> None:
        """Release labels belonging to the preceding UI frame build."""

        self._labels = {}

    def status(self, set_id: str) -> str | None:
        """Return the latest outcome retained for one stable Set identity."""

        return self._statuses.get(set_id)

    def remember_label(self, set_id: str, label: object) -> None:
        """Retain the current label for immediate live feedback."""

        self._labels[set_id] = label

    def apply(self, set_id: str, name: str, value: object) -> None:
        """Run one live change and surface success or failure inline."""

        if self._change is None:
            return
        try:
            updated_count = self._change(set_id, name, value)
        except Exception as error:
            self._set_status(set_id, f"Apply failed: {error}")
            raise
        self._set_status(set_id, _success_message(updated_count))

    def reset(self, set_id: str, group: str | None) -> None:
        """Run one reset, retain its outcome, and rebuild edited fields."""

        if self._reset is None:
            return
        try:
            updated_count = self._reset(set_id, group)
        except Exception as error:
            self._set_status(set_id, f"Reset failed: {error}")
            raise
        label = group or "Complete profile"
        self._statuses[set_id] = (
            f"{label} reset. {_success_message(updated_count)}"
        )
        self._rebuild()

    def stop(self) -> None:
        """Release callbacks, label references, and transient messages."""

        self._change = None
        self._reset = None
        self._statuses = {}
        self._labels = {}

    def _set_status(self, set_id: str, message: str) -> None:
        self._statuses[set_id] = message
        label = self._labels.get(set_id)
        if label is not None:
            label.text = message
            label.visible = True


def _success_message(updated_count: int) -> str:
    if updated_count:
        return f"Applied to {updated_count} runtime materials."
    return "Saved in the Set; no active runtime materials were changed."
