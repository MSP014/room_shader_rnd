"""Build content-sized ORMS sections with retained collapse state."""

from __future__ import annotations

from collections.abc import Callable

from .ui_tooltips import with_wrapped_tooltip


def collapsable_frame(
    ui: object,
    title: str,
    *,
    collapsed: bool = False,
    collapsed_changed: Callable[[bool], None] | None = None,
    tooltip: str | None = None,
) -> object:
    """Create a frame that releases its content height when collapsed."""

    frame = ui.CollapsableFrame(
        title,
        collapsed=collapsed,
        height=0,
    )
    with_wrapped_tooltip(frame, tooltip)
    if collapsed_changed is not None:
        frame.set_collapsed_changed_fn(collapsed_changed)
    return frame
