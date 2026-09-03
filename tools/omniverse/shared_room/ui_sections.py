"""Build content-sized ORMS sections with retained collapse state."""

from __future__ import annotations

from collections.abc import Callable


def collapsable_frame(
    ui: object,
    title: str,
    *,
    collapsed: bool = False,
    collapsed_changed: Callable[[bool], None] | None = None,
) -> object:
    """Create a frame that releases its content height when collapsed."""

    frame = ui.CollapsableFrame(
        title,
        collapsed=collapsed,
        height=0,
    )
    if collapsed_changed is not None:
        frame.set_collapsed_changed_fn(collapsed_changed)
    return frame
