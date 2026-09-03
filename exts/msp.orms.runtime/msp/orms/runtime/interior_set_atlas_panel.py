"""Build staged Interior Set selectors, atlases, order, and Apply controls."""

from __future__ import annotations

from collections.abc import Callable

from tools.omniverse.interior_sets.atlas_mode import (
    ATLAS_MODE_DEBUG,
    ATLAS_MODE_PRODUCTION,
)
from tools.omniverse.shared_room.interior_set_diagnostics import (
    InteriorSetDiagnostics,
)
from tools.omniverse.shared_room.ui_buttons import selection_button
from tools.omniverse.shared_room.ui_sections import collapsable_frame

from .interior_set_alerts import selector_conflict_alerts
from .interior_set_controller import InteriorSetController
from .interior_set_fields import string_field


def _resource_status(controller: InteriorSetController, set_id: str) -> str:
    snapshot = next(
        item
        for item in controller.resource_decisions()
        if item.set_id == set_id
    )
    family_statuses = []
    for family in snapshot.families:
        source = family.atlas.source if family.atlas is not None else "missing"
        detail = family.validation_error or family.fallback_reason
        family_statuses.append(
            f"x{family.room_size}: {source}"
            + (f" fallback ({detail})" if detail else "")
        )
    families = ", ".join(family_statuses)
    coherence = (
        "coherent"
        if snapshot.coherence.coherent
        else snapshot.coherence.error or "incoherent"
    )
    return f"{families}. Variant identity: {coherence}."


def _select_atlas_mode(
    controller: InteriorSetController,
    atlas_mode: str,
    rebuild: Callable[[], None],
) -> None:
    """Stage one global resource policy and refresh only local UI."""

    controller.stage_atlas_mode(atlas_mode)
    rebuild()


def _collapsable_frame(
    ui: object,
    title: str,
    *,
    collapsed: bool,
    collapsed_changed: Callable[[bool], None] | None,
) -> object:
    """Create a zero-height collapsible frame with retained state."""

    return collapsable_frame(
        ui,
        title,
        collapsed=collapsed,
        collapsed_changed=collapsed_changed,
    )


def _build_structural_actions(
    ui: object,
    controller: InteriorSetController,
    rebuild: Callable[[], None],
    apply: Callable[[], None],
) -> None:
    """Keep the staged transaction actions above the repeatable Set list."""

    with ui.HStack(height=30, spacing=4):
        ui.Button(
            "+ Add Interior Set",
            clicked_fn=lambda: (controller.add(), rebuild()),
        )
        ui.Button("Apply Interior Sets", clicked_fn=apply)
        ui.Button(
            "Revert unapplied changes",
            enabled=controller.dirty,
            clicked_fn=lambda: (controller.revert(), rebuild()),
        )


def build_interior_set_atlas_panel(
    controller: InteriorSetController,
    rebuild: Callable[[], None],
    apply: Callable[[], None],
    rename: Callable[[str, str], None],
    choose_directory: Callable[
        [str, Callable[[str], None]],
        None,
    ],
    runtime_diagnostics: InteriorSetDiagnostics | None,
    error_message: str | None = None,
    atlas_mode_collapsed: bool = False,
    atlas_mode_collapsed_changed: Callable[[bool], None] | None = None,
    set_collapsed: Callable[[str], bool] | None = None,
    set_collapsed_changed: Callable[[str, bool], None] | None = None,
) -> tuple[object, ...]:
    """Build structural fields that never mutate applied state directly."""

    import omni.ui as ui

    models = []
    state = (
        "Unapplied structural changes"
        if controller.dirty
        else "Interior Sets are applied"
    )
    ui.Label(
        f"{state}. Applied revision {controller.applied_revision}; "
        f"draft revision {controller.draft_revision}. "
        f"Last action: {controller.last_apply_status}.",
        word_wrap=True,
        height=0,
    )
    if error_message:
        ui.Label(
            f"Apply failed: {error_message}",
            word_wrap=True,
            height=0,
        )
    for alert in selector_conflict_alerts(controller, runtime_diagnostics):
        ui.Label(
            alert,
            word_wrap=True,
            height=0,
            name="warning",
        )
    atlas_mode_frame = _collapsable_frame(
        ui,
        "Atlas mode",
        collapsed=atlas_mode_collapsed,
        collapsed_changed=atlas_mode_collapsed_changed,
    )
    with atlas_mode_frame:
        with ui.VStack(spacing=4):
            ui.Label(
                "Debug forces packaged x1-x4 atlases for every Interior Set. "
                "Production uses each Set's configured family and falls back "
                "to the matching packaged debug family when it is absent.",
                word_wrap=True,
                height=0,
            )
            with ui.HStack(height=28, spacing=4):
                selection_button(
                    ui,
                    "Debug (force packaged)",
                    selected=(controller.draft_atlas_mode == ATLAS_MODE_DEBUG),
                    clicked=lambda: _select_atlas_mode(
                        controller,
                        ATLAS_MODE_DEBUG,
                        rebuild,
                    ),
                )
                selection_button(
                    ui,
                    "Production + debug fallback",
                    selected=(
                        controller.draft_atlas_mode == ATLAS_MODE_PRODUCTION
                    ),
                    clicked=lambda: _select_atlas_mode(
                        controller,
                        ATLAS_MODE_PRODUCTION,
                        rebuild,
                    ),
                )
    _build_structural_actions(ui, controller, rebuild, apply)
    for item in controller.draft.sets:
        title = controller.draft.label_for(item.set_id)
        if item.is_default:
            title += " (Default fallback)"
        frame = _collapsable_frame(
            ui,
            title,
            collapsed=(
                set_collapsed(item.set_id)
                if set_collapsed is not None
                else False
            ),
            collapsed_changed=(
                (
                    lambda collapsed, set_id=item.set_id: (
                        set_collapsed_changed(set_id, collapsed)
                    )
                )
                if set_collapsed_changed is not None
                else None
            ),
        )
        with frame:
            with ui.VStack(spacing=4):
                with ui.HStack(height=24):
                    ui.Label("Name", width=ui.Percent(30), name="title")
                    models.extend(
                        string_field(
                            item.name,
                            lambda value, set_id=item.set_id: rename(
                                set_id,
                                value,
                            ),
                        )
                    )
                if item.is_default:
                    ui.Label(
                        "Default is evaluated last and receives every "
                        "compatible ORMS window not matched by a specific "
                        "Interior Set.",
                        word_wrap=True,
                        height=0,
                    )
                else:
                    ui.Label("Target paths / masks", name="title")
                    models.extend(
                        string_field(
                            "\n".join(item.selectors),
                            lambda value, set_id=item.set_id: (
                                controller.stage_selectors(
                                    set_id,
                                    tuple(value.splitlines()),
                                )
                            ),
                            multiline=True,
                        )
                    )
                directories = list(item.atlas_directories)
                for room_size in range(1, 5):
                    with ui.HStack(height=24):
                        ui.Label(
                            f"x{room_size} production folder",
                            width=ui.Percent(30),
                            name="title",
                        )

                        def changed(
                            value: str,
                            *,
                            set_id: str = item.set_id,
                            index: int = room_size - 1,
                            current: list[str] = directories,
                        ) -> None:
                            current[index] = value
                            controller.stage_atlas_directories(
                                set_id,
                                tuple(current),
                            )

                        models.extend(
                            string_field(directories[room_size - 1], changed)
                        )
                        ui.Button(
                            "Browse...",
                            width=90,
                            clicked_fn=(
                                lambda current=directories[
                                    room_size - 1
                                ], update=changed: choose_directory(
                                    current,
                                    lambda value: (update(value), rebuild()),
                                )
                            ),
                        )
                ui.Label(
                    _resource_status(controller, item.set_id),
                    word_wrap=True,
                    height=0,
                )
                with ui.HStack(height=28, spacing=4):
                    ui.Button(
                        "Duplicate",
                        clicked_fn=lambda set_id=item.set_id: (
                            controller.duplicate(set_id),
                            rebuild(),
                        ),
                    )
                    if not item.is_default:
                        ui.Button(
                            "Move Up",
                            clicked_fn=lambda set_id=item.set_id: (
                                controller.move(set_id, -1),
                                rebuild(),
                            ),
                        )
                        ui.Button(
                            "Move Down",
                            clicked_fn=lambda set_id=item.set_id: (
                                controller.move(set_id, 1),
                                rebuild(),
                            ),
                        )
                        ui.Button(
                            "Remove",
                            clicked_fn=lambda set_id=item.set_id: (
                                controller.remove(set_id),
                                rebuild(),
                            ),
                        )
    return tuple(models)
