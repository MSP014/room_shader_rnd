# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Build artist-facing automatic-assignment inspection and override controls."""

from __future__ import annotations

from collections.abc import Callable

from msp.orms.shared_room.ui_buttons import selection_button

from .session import AssignmentItem, AssignmentSnapshot

AssignmentChanged = Callable[[str, bool | None], None]

_SOURCE_RULE_HELP = (
    "Use the asset's own orms:autoAssign value without a Session Layer "
    "override."
)
_ALLOW_HELP = "Author a temporary orms:autoAssign=true Session Layer override."
_EXCLUDE_HELP = (
    "Author a temporary orms:autoAssign=false override and reveal the source "
    "material binding."
)


def _state_text(item: AssignmentItem) -> str:
    if item.assigned:
        return "Assigned by ORMS"
    if item.reason == "explicitly_excluded":
        return "Excluded; source binding is visible"
    if item.eligible:
        return "Eligible; assignment is not currently active"
    return f"Not assignable: {item.reason}"


def build_assignment_panel(
    snapshot: AssignmentSnapshot,
    changed: AssignmentChanged,
) -> tuple[object, ...]:
    """Show recognised meshes and reversible Session-layer choices."""

    import omni.ui as ui

    if not snapshot.items:
        ui.Label(
            "No recognised window meshes are available in the active stage.",
            word_wrap=True,
            height=0,
        )
        return ()

    for item in snapshot.items:
        with ui.VStack(spacing=3, height=0):
            ui.Label(item.prim_path, word_wrap=True, height=0, name="title")
            ui.Label(
                f"{_state_text(item)}. Source: {item.source_material_path}",
                word_wrap=True,
                height=0,
            )
            with ui.HStack(height=28, spacing=4):
                selection_button(
                    ui,
                    "Use source rule",
                    selected=item.override is None,
                    enabled=snapshot.editable,
                    clicked=lambda path=item.prim_path: changed(path, None),
                    tooltip=_SOURCE_RULE_HELP,
                )
                selection_button(
                    ui,
                    "Allow ORMS",
                    selected=item.override is True,
                    enabled=snapshot.editable,
                    clicked=lambda path=item.prim_path: changed(path, True),
                    tooltip=_ALLOW_HELP,
                )
                selection_button(
                    ui,
                    "Exclude / restore source",
                    selected=item.override is False,
                    enabled=snapshot.editable,
                    clicked=lambda path=item.prim_path: changed(path, False),
                    tooltip=_EXCLUDE_HELP,
                )
    if not snapshot.editable:
        ui.Label(
            "Start ORMS before changing mesh assignment overrides.",
            word_wrap=True,
            height=0,
        )
    return ()
