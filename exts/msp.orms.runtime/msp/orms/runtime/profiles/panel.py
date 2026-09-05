# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Build portable `.orms` scene-profile controls."""

from __future__ import annotations

from collections.abc import Callable

from msp.orms.shared_room.ui_sections import collapsable_frame
from msp.orms.shared_room.ui_tooltips import with_wrapped_tooltip

_PROFILE_HELP = (
    "Save the applied Interior Set configuration to a portable profile, or "
    "load one into the staged draft. Loading never changes the scene until "
    "Apply Interior Sets."
)


def build_interior_set_profile_panel(
    save: Callable[[], None],
    load: Callable[[], None],
    status: str | None,
    collapsed: bool = False,
    collapsed_changed: Callable[[bool], None] | None = None,
) -> tuple[object, ...]:
    """Build local profile I/O without applying loaded scene state."""

    import omni.ui as ui

    frame = collapsable_frame(
        ui,
        "Scene ORMS profile (.orms)",
        collapsed=collapsed,
        collapsed_changed=collapsed_changed,
        tooltip=_PROFILE_HELP,
    )
    with frame:
        with ui.VStack(spacing=4):
            with ui.HStack(height=28, spacing=4):
                save_button = ui.Button(
                    "Save Profile...",
                    clicked_fn=save,
                )
                with_wrapped_tooltip(
                    save_button,
                    "Save the currently applied configuration.",
                )
                load_button = ui.Button(
                    "Load Profile...",
                    clicked_fn=load,
                )
                with_wrapped_tooltip(
                    load_button,
                    "Load a profile into the draft; Apply Interior Sets is "
                    "still required.",
                )
            if status:
                ui.Label(status, word_wrap=True, height=0)
    return ()
