"""Build selection controls with an explicit ORMS active-state contrast."""

from __future__ import annotations

from collections.abc import Callable

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
) -> object:
    """Create one mutually exclusive choice with visible selected state."""

    return ui.Button(
        text,
        selected=selected,
        clicked_fn=clicked,
        style=SELECTION_BUTTON_STYLE,
    )
