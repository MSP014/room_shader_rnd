"""Build portable `.orms` scene-profile controls."""

from __future__ import annotations

from collections.abc import Callable

from msp.orms.shared_room.ui_sections import collapsable_frame


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
    )
    with frame:
        with ui.VStack(spacing=4):
            ui.Label(
                "Save the applied Interior Set configuration to a portable "
                "profile, or load one into the staged draft. Loading never "
                "changes the scene until Apply Interior Sets.",
                word_wrap=True,
                height=0,
            )
            with ui.HStack(height=28, spacing=4):
                ui.Button("Save Profile...", clicked_fn=save)
                ui.Button("Load Profile...", clicked_fn=load)
            if status:
                ui.Label(status, word_wrap=True, height=0)
    return ()
