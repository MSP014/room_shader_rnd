"""Own the dockable Window-menu surface for persistent ORMS controls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tools.omniverse.shared_room.interior_set_diagnostics import (
    InteriorSetDiagnostics,
)
from tools.omniverse.shared_room.material_controls import (
    ensure_material_setting_defaults,
)
from tools.omniverse.shared_room.settings import (
    ensure_classifier_setting_defaults,
)
from tools.omniverse.shared_room.settings_panel import build_settings_panel

from .assignment_panel import build_assignment_panel
from .assignment_session import AssignmentSnapshot
from .interior_set_atlas_panel import build_interior_set_atlas_panel
from .interior_set_controller import InteriorSetController
from .interior_set_directory_picker import InteriorSetDirectoryPicker
from .interior_set_material_panel import build_interior_set_material_panel
from .interior_set_panel_state import InteriorSetPanelState
from .interior_set_profile_workflow import InteriorSetProfileWorkflow
from .lifecycle import RuntimeState
from .lifecycle_controls import LifecycleCallbacks, LifecycleControls
from .material_update_feedback import MaterialUpdateFeedback
from .resources import (
    DEBUG_ASSET_SETTING,
    PRODUCTION_DIRECTORY_SETTING,
)
from .ui_update_scheduler import UiUpdateScheduler

WINDOW_NAME = "ORMS"
MENU_GROUP = "Window"
_CLASSIFIER_DELAY_SECONDS = 0.15
_LIFECYCLE_SECTION_ID = "classifier:runtime_lifecycle"


class OrmsSettingsWindow:
    """Register one lazy, dockable ORMS window and remove it symmetrically."""

    def __init__(self) -> None:
        self._window: Any | None = None
        self._menu_items: list[Any] = []
        self._models: tuple[object, ...] = ()
        self._updates = UiUpdateScheduler()
        self._building = False
        self._classifier_changed: Callable[[], None] | None = None
        self._assignment_changed: Callable[[str, bool | None], None] | None = (
            None
        )
        self._assignment_snapshot: Callable[[], AssignmentSnapshot] | None = (
            None
        )
        self._material_feedback = MaterialUpdateFeedback(self._rebuild_window)
        self._apply_interior_sets: Callable[[], None] | None = None
        self._rename_interior_set: Callable[[str, str], None] | None = None
        self._interior_sets: InteriorSetController | None = None
        self._runtime_diagnostics: (
            Callable[[], InteriorSetDiagnostics | None] | None
        ) = None
        self._lifecycle_controls: LifecycleControls | None = None
        self._lifecycle_state = RuntimeState.INACTIVE
        self._structural_error: str | None = None
        self._directory_picker = InteriorSetDirectoryPicker()
        self._active_tab_index = 0
        self._panel_state = InteriorSetPanelState()
        self._profile_workflow = InteriorSetProfileWorkflow(
            self._panel_state,
            lambda: self._interior_sets,
            self._rebuild_window,
        )

    def start(
        self,
        *,
        classifier_changed: Callable[[], None],
        assignment_changed: Callable[[str, bool | None], None],
        assignment_snapshot: Callable[[], AssignmentSnapshot],
        material_changed: Callable[[str, str, object], int],
        material_reset: Callable[[str, str | None], int],
        apply_interior_sets: Callable[[], None],
        rename_interior_set: Callable[[str, str], None],
        interior_sets: InteriorSetController,
        runtime_diagnostics: Callable[
            [],
            InteriorSetDiagnostics | None,
        ],
        start_runtime: Callable[[], None],
        restart_runtime: Callable[[], None],
        stop_runtime: Callable[[], None],
        restore_asset: Callable[[], None],
    ) -> None:
        """Expose `Window > ORMS` without opening it automatically."""

        import omni.kit.menu.utils
        import omni.ui as ui
        from omni.kit.menu.utils import MenuItemDescription

        if self._menu_items:
            return
        ensure_classifier_setting_defaults()
        ensure_material_setting_defaults()
        self._classifier_changed = classifier_changed
        self._assignment_changed = assignment_changed
        self._assignment_snapshot = assignment_snapshot
        self._material_feedback.start(material_changed, material_reset)
        self._apply_interior_sets = apply_interior_sets
        self._rename_interior_set = rename_interior_set
        self._interior_sets = interior_sets
        self._runtime_diagnostics = runtime_diagnostics
        self._lifecycle_controls = LifecycleControls(
            LifecycleCallbacks(
                start=start_runtime,
                restart=restart_runtime,
                stop=stop_runtime,
                restore=restore_asset,
            ),
            self._lifecycle_state,
            collapsed=self._panel_state.is_section_collapsed(
                _LIFECYCLE_SECTION_ID
            ),
            collapsed_changed=lambda collapsed: (
                self._panel_state.remember_section_collapsed(
                    _LIFECYCLE_SECTION_ID,
                    collapsed,
                )
            ),
        )
        self._menu_items = [
            MenuItemDescription(
                name=WINDOW_NAME,
                ticked=True,
                ticked_fn=self._is_visible,
                onclick_fn=self._toggle,
            )
        ]
        ui.Workspace.set_show_window_fn(WINDOW_NAME, self._show_window)
        omni.kit.menu.utils.add_menu_items(
            self._menu_items,
            name=MENU_GROUP,
        )

    def _is_visible(self) -> bool:
        return bool(self._window and self._window.visible)

    def _toggle(self) -> None:
        import omni.ui as ui

        ui.Workspace.show_window(WINDOW_NAME, not self._is_visible())

    def _show_window(self, visible: bool) -> None:
        if visible and self._window is None:
            self._create_window()
        if self._window is not None:
            self._window.visible = visible

    def _create_window(self) -> None:
        import omni.ui as ui

        self._window = ui.Window(WINDOW_NAME, width=920, height=760)
        self._window.set_visibility_changed_fn(self._visibility_changed)
        self._window.frame.set_build_fn(self._build_window_contents)
        self._window.frame.rebuild()

    def _build_window_contents(self) -> None:
        """Build controls when the owning frame requests its next draw."""

        import omni.ui as ui

        self._building = True
        self._material_feedback.begin_build()
        try:
            with ui.ScrollingFrame():
                if self._interior_sets is None:
                    raise RuntimeError(
                        "Interior Set UI controller is unavailable"
                    )
                self._models = build_settings_panel(
                    atlas_paths={
                        "debug_asset": DEBUG_ASSET_SETTING,
                        "production_directory": (PRODUCTION_DIRECTORY_SETTING),
                    },
                    classifier_changed=self._schedule_classifier_change,
                    material_changed=lambda: None,
                    apply_atlases=self._apply_structural_changes,
                    build_lifecycle_controls=self._lifecycle_controls.build,
                    watch_model=self._watch_model,
                    build_assignment_panel=self._build_assignment_panel,
                    build_material_panel=lambda: (
                        build_interior_set_material_panel(
                            self._interior_sets,
                            self._schedule_material_change,
                            self._schedule_material_reset,
                            self._material_feedback.status,
                            self._material_feedback.remember_label,
                            self._panel_state.is_section_collapsed,
                            self._panel_state.remember_section_collapsed,
                        )
                    ),
                    build_atlas_panel=self._build_atlas_panel,
                    active_tab_index=self._active_tab_index,
                    tab_changed=self._remember_active_tab,
                    debug_atlases_collapsed=(
                        self._panel_state.debug_atlases_collapsed
                    ),
                    debug_atlases_collapsed_changed=(
                        self._remember_debug_atlases_collapsed
                    ),
                    section_collapsed=(self._panel_state.is_section_collapsed),
                    section_collapsed_changed=(
                        self._panel_state.remember_section_collapsed
                    ),
                )
        finally:
            self._building = False

    def _remember_active_tab(self, index: int) -> None:
        self._active_tab_index = index

    def _build_assignment_panel(self) -> tuple[object, ...]:
        """Build the current stage's source-safe assignment controls."""

        snapshot = (
            self._assignment_snapshot()
            if self._assignment_snapshot is not None
            else AssignmentSnapshot()
        )
        return build_assignment_panel(
            snapshot,
            self._schedule_assignment_change,
        )

    def _remember_debug_atlases_collapsed(self, collapsed: bool) -> None:
        """Preserve the packaged-debug section across frame rebuilds."""

        self._panel_state.debug_atlases_collapsed = bool(collapsed)

    def _remember_atlas_mode_collapsed(self, collapsed: bool) -> None:
        """Preserve the global atlas-mode section across frame rebuilds."""

        self._panel_state.atlas_mode_collapsed = bool(collapsed)

    def _build_atlas_panel(self) -> tuple[object, ...]:
        """Build portable profile controls before staged Set controls."""

        if self._interior_sets is None:
            return ()
        models = list(self._profile_workflow.build_panel())
        models.extend(
            build_interior_set_atlas_panel(
                self._interior_sets,
                self._rebuild_window,
                self._apply_structural_changes,
                self._rename_interior_set,
                self._directory_picker.choose,
                (
                    self._runtime_diagnostics()
                    if self._runtime_diagnostics is not None
                    else None
                ),
                error_message=self._structural_error,
                atlas_mode_collapsed=(self._panel_state.atlas_mode_collapsed),
                atlas_mode_collapsed_changed=(
                    self._remember_atlas_mode_collapsed
                ),
                set_collapsed=self._panel_state.is_set_collapsed,
                set_collapsed_changed=(
                    self._panel_state.remember_set_collapsed
                ),
            )
        )
        return tuple(models)

    @staticmethod
    def _subscribe_model(
        model: object,
        changed: Callable[[], None],
    ) -> None:
        add_value_changed = getattr(model, "add_value_changed_fn", None)
        if callable(add_value_changed):
            add_value_changed(lambda _model: changed())
            return
        add_item_changed = getattr(model, "add_item_changed_fn", None)
        if callable(add_item_changed):
            add_item_changed(lambda _model, _item: changed())
            return
        raise TypeError(f"Unsupported ORMS setting model: {type(model)!r}")

    def _watch_model(
        self,
        model: object,
        changed: Callable[[], None],
    ) -> None:
        self._subscribe_model(model, changed)

    def _schedule_classifier_change(self) -> None:
        if self._building or self._classifier_changed is None:
            return
        self._updates.schedule(
            "classifier",
            self._classifier_changed,
            delay_seconds=_CLASSIFIER_DELAY_SECONDS,
        )

    def _schedule_assignment_change(
        self,
        prim_path: str,
        allowed: bool | None,
    ) -> None:
        """Defer one assignment rebuild beyond the current button event."""

        if self._building or self._assignment_changed is None:
            return
        self._updates.schedule(
            "assignment",
            lambda: self._assignment_changed(prim_path, allowed),
            delay_seconds=0.0,
        )

    def _schedule_material_change(
        self,
        set_id: str,
        name: str,
        value: object,
    ) -> None:
        if self._building:
            return
        self._updates.schedule(
            f"material:{set_id}:{name}",
            lambda: self._material_feedback.apply(set_id, name, value),
            delay_seconds=0.0,
        )

    def _schedule_material_reset(
        self,
        set_id: str,
        group: str | None,
    ) -> None:
        """Defer a reset and rebuild fields only after it succeeds."""

        if self._building:
            return
        key = group or "complete"
        self._updates.schedule(
            f"material-reset:{set_id}:{key}",
            lambda: self._material_feedback.reset(set_id, group),
            delay_seconds=0.0,
        )

    def _apply_structural_changes(self) -> None:
        if self._apply_interior_sets is None:
            return
        try:
            self._apply_interior_sets()
            self._structural_error = None
        except Exception as error:
            import carb

            self._structural_error = str(error)
            carb.log_error(f"[ORMS] Apply Interior Sets failed: {error!r}")
        self._rebuild_window()

    def _rebuild_window(self) -> None:
        """Request a safe content rebuild without replacing the window."""

        if self._interior_sets is not None:
            self._panel_state.retain_sets(
                item.set_id for item in self._interior_sets.draft.sets
            )
        if self._window is not None:
            # Frame.rebuild defers replacement to the next drawing cycle.
            # Replacing a Window inside a button callback is invalid OmniUI.
            self._window.frame.rebuild()

    def _visibility_changed(self, visible: bool) -> None:
        import omni.kit.menu.utils

        if (
            not visible
            and not self._building
            and self._interior_sets is not None
            and self._interior_sets.dirty
            and self._window is not None
        ):
            import carb

            carb.log_warn(
                "[ORMS] Apply or revert Interior Set changes before "
                "closing the window"
            )
            self._window.visible = True
            return
        omni.kit.menu.utils.refresh_menu_items(MENU_GROUP)

    def set_lifecycle_state(self, state: RuntimeState) -> None:
        """Present service-owned lifecycle state without initiating a change."""

        self._lifecycle_state = state
        if self._lifecycle_controls is not None:
            self._lifecycle_controls.set_state(state)

    def refresh_interior_sets(self) -> None:
        """Refresh visible Interior Set state after a runtime rebuild."""

        if self._window is not None:
            self._rebuild_window()

    def stop(self) -> None:
        """Remove the menu, callbacks, models, tasks, and window owned here."""

        import omni.kit.menu.utils
        import omni.ui as ui

        self._updates.stop()
        if self._menu_items:
            omni.kit.menu.utils.remove_menu_items(
                self._menu_items,
                name=MENU_GROUP,
            )
        self._menu_items = []
        ui.Workspace.set_show_window_fn(WINDOW_NAME, None)
        self._building = True
        try:
            if self._window is not None:
                self._window.destroy()
        finally:
            self._building = False
        self._window = None
        self._models = ()
        self._classifier_changed = None
        self._assignment_changed = None
        self._assignment_snapshot = None
        self._material_feedback.stop()
        self._apply_interior_sets = None
        self._rename_interior_set = None
        self._interior_sets = None
        self._runtime_diagnostics = None
        self._structural_error = None
        self._active_tab_index = 0
        self._panel_state.reset()
        self._directory_picker.stop()
        self._profile_workflow.stop()
        self._lifecycle_controls = None
