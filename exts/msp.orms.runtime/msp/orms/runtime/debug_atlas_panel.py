"""Build staged global debug-atlas controls for the Interior Atlases tab."""

from __future__ import annotations

from collections.abc import Callable

from msp.orms.shared_room.ui_sections import collapsable_frame
from msp.orms.shared_room.ui_tooltips import with_wrapped_tooltip

from .interior_set_controller import InteriorSetController
from .interior_set_fields import string_field
from .resources import DebugAtlasDecision

_DEBUG_HELP = (
    "Packaged x1-x4 families are the defaults. A custom folder replaces one "
    "global debug family in Debug mode and Production fallback. Clear restores "
    "the packaged default. Changes remain staged until Apply Interior Sets."
)


def _status(decision: DebugAtlasDecision) -> str:
    atlas = decision.atlas
    if decision.validation_error:
        fallback = "packaged fallback" if atlas is not None else "no fallback"
        return (
            f"Invalid custom folder; {fallback}: {decision.validation_error}"
        )
    if atlas is None:
        return "Packaged debug atlas is missing."
    source = (
        "Custom override" if decision.uses_override else "Packaged default"
    )
    return f"{source}: {atlas.variant_count} variants."


def build_debug_atlas_panel(
    controller: InteriorSetController,
    rebuild: Callable[[], None],
    choose_directory: Callable[[str, Callable[[str], None]], None],
    *,
    collapsed: bool = False,
    collapsed_changed: Callable[[bool], None] | None = None,
) -> tuple[object, ...]:
    """Build x1-x4 overrides that join the explicit Apply transaction."""

    import omni.ui as ui

    models = []
    decisions = controller.debug_atlas_decisions()
    frame = collapsable_frame(
        ui,
        "Debug atlas families (global)",
        collapsed=collapsed,
        collapsed_changed=collapsed_changed,
        tooltip=_DEBUG_HELP,
    )
    with frame:
        with ui.VStack(spacing=4):
            for room_size, decision in enumerate(decisions, start=1):
                configured = controller.draft_debug_atlas_directories[
                    room_size - 1
                ]
                displayed = controller.debug_atlas_display_directory(room_size)
                family_help = f"{_DEBUG_HELP}\n{_status(decision)}"

                def changed(value: str, *, size: int = room_size) -> None:
                    controller.stage_debug_atlas_directory(size, value)

                with ui.HStack(height=24):
                    label = ui.Label(
                        f"x{room_size} debug folder",
                        width=ui.Percent(30),
                        name="title",
                    )
                    with_wrapped_tooltip(label, family_help)
                    models.extend(
                        string_field(
                            displayed,
                            changed,
                            tooltip=family_help,
                        )
                    )
                    browse_button = ui.Button(
                        "Browse...",
                        width=82,
                        clicked_fn=(
                            lambda current=displayed, update=changed: (
                                choose_directory(
                                    current,
                                    lambda value: (update(value), rebuild()),
                                )
                            )
                        ),
                    )
                    with_wrapped_tooltip(browse_button, family_help)
                    clear_button = ui.Button(
                        "Clear",
                        width=54,
                        enabled=bool(configured),
                        clicked_fn=(
                            lambda size=room_size: (
                                controller.clear_debug_atlas_directory(size),
                                rebuild(),
                            )
                        ),
                    )
                    with_wrapped_tooltip(
                        clear_button,
                        "Clear the custom folder and restore the packaged "
                        f"x{room_size} default.",
                    )
                if decision.validation_error:
                    ui.Label(
                        f"x{room_size}: {_status(decision)}",
                        word_wrap=True,
                        height=0,
                        name="warning",
                    )
    return tuple(models)
