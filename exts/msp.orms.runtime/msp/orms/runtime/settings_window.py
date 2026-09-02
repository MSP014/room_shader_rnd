"""Own the dockable Window-menu surface for persistent ORMS controls."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from tools.omniverse.shared_room.material_controls import (
    ensure_material_setting_defaults,
)
from tools.omniverse.shared_room.settings import (
    ensure_classifier_setting_defaults,
)
from tools.omniverse.shared_room.settings_panel import build_settings_panel

from .lifecycle import RuntimeState
from .lifecycle_controls import LifecycleCallbacks, LifecycleControls
from .resources import (
    DEBUG_ASSET_SETTING,
    PRODUCTION_DIRECTORY_SETTING,
)

WINDOW_NAME = "ORMS"
MENU_GROUP = "Window"
_CLASSIFIER_DELAY_SECONDS = 0.15


class OrmsSettingsWindow:
    """Register one lazy, dockable ORMS window and remove it symmetrically."""

    def __init__(self) -> None:
        self._window: Any | None = None
        self._menu_items: list[Any] = []
        self._models: tuple[object, ...] = ()
        self._tasks: dict[str, Any] = {}
        self._building = False
        self._classifier_changed: Callable[[], None] | None = None
        self._material_changed: Callable[[], None] | None = None
        self._apply_atlases: Callable[[], None] | None = None
        self._lifecycle_controls: LifecycleControls | None = None
        self._lifecycle_state = RuntimeState.INACTIVE

    def start(
        self,
        *,
        classifier_changed: Callable[[], None],
        material_changed: Callable[[], None],
        apply_atlases: Callable[[], None],
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
        self._material_changed = material_changed
        self._apply_atlases = apply_atlases
        self._lifecycle_controls = LifecycleControls(
            LifecycleCallbacks(
                start=start_runtime,
                restart=restart_runtime,
                stop=stop_runtime,
                restore=restore_asset,
            ),
            self._lifecycle_state,
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

        self._window = ui.Window(WINDOW_NAME, width=820, height=680)
        self._window.set_visibility_changed_fn(self._visibility_changed)
        self._building = True
        try:
            with self._window.frame:
                with ui.ScrollingFrame():
                    self._models = build_settings_panel(
                        atlas_paths={
                            "debug_asset": DEBUG_ASSET_SETTING,
                            "production_directory": (
                                PRODUCTION_DIRECTORY_SETTING
                            ),
                        },
                        classifier_changed=(self._schedule_classifier_change),
                        material_changed=self._schedule_material_change,
                        apply_atlases=self._apply_atlases,
                        build_lifecycle_controls=(
                            self._lifecycle_controls.build
                        ),
                        watch_model=self._watch_model,
                    )
        finally:
            self._building = False

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
        self._schedule_change(
            "classifier",
            self._classifier_changed,
            delay_seconds=_CLASSIFIER_DELAY_SECONDS,
        )

    def _schedule_material_change(self) -> None:
        self._schedule_change(
            "material",
            self._material_changed,
            delay_seconds=0.0,
        )

    def _schedule_change(
        self,
        key: str,
        callback: Callable[[], None] | None,
        *,
        delay_seconds: float,
    ) -> None:
        if self._building or callback is None:
            return
        pending = self._tasks.pop(key, None)
        if pending is not None:
            pending.cancel()

        async def invoke() -> None:
            import carb
            import omni.kit.app

            try:
                if delay_seconds:
                    await asyncio.sleep(delay_seconds)
                else:
                    await omni.kit.app.get_app().next_update_async()
                callback()
            except asyncio.CancelledError:
                return
            except Exception as error:
                carb.log_error(
                    f"[ORMS] {key} setting update failed: {error!r}"
                )
            finally:
                current = self._tasks.get(key)
                if current is asyncio.current_task():
                    self._tasks.pop(key, None)

        self._tasks[key] = asyncio.ensure_future(invoke())

    @staticmethod
    def _visibility_changed(_visible: bool) -> None:
        import omni.kit.menu.utils

        omni.kit.menu.utils.refresh_menu_items(MENU_GROUP)

    def set_lifecycle_state(self, state: RuntimeState) -> None:
        """Present service-owned lifecycle state without initiating a change."""

        self._lifecycle_state = state
        if self._lifecycle_controls is not None:
            self._lifecycle_controls.set_state(state)

    def stop(self) -> None:
        """Remove the menu, callbacks, models, tasks, and window owned here."""

        import omni.kit.menu.utils
        import omni.ui as ui

        for task in self._tasks.values():
            task.cancel()
        self._tasks = {}
        if self._menu_items:
            omni.kit.menu.utils.remove_menu_items(
                self._menu_items,
                name=MENU_GROUP,
            )
        self._menu_items = []
        ui.Workspace.set_show_window_fn(WINDOW_NAME, None)
        if self._window is not None:
            self._window.destroy()
        self._window = None
        self._models = ()
        self._classifier_changed = None
        self._material_changed = None
        self._apply_atlases = None
        self._lifecycle_controls = None
