# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Build selection controls with an explicit ORMS active-state contrast."""

from __future__ import annotations

from collections.abc import Callable

from .ui_tooltips import with_wrapped_tooltip

SELECTION_BUTTON_STYLE = {
    "Button": {"background_color": 0xFF454545},
    "Button:hovered": {"background_color": 0xFF505050},
    "Button:pressed": {"background_color": 0xFF252525},
    "Button:selected": {"background_color": 0xFF252525},
}


def selection_button(
    ui: object,
    text: str,
    *,
    selected: bool,
    clicked: Callable[[], None],
    enabled: bool = True,
    tooltip: str | None = None,
) -> object:
    """Create one mutually exclusive choice with visible selected state."""

    button = ui.Button(
        text,
        selected=selected,
        enabled=enabled,
        clicked_fn=clicked,
        style=SELECTION_BUTTON_STYLE,
    )
    return with_wrapped_tooltip(button, tooltip)
