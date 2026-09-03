"""Coordinate portable `.orms` profile UI, validation, and local I/O."""

from __future__ import annotations

from collections.abc import Callable

from .interior_set_controller import InteriorSetController
from .interior_set_panel_state import InteriorSetPanelState
from .interior_set_profile_panel import build_interior_set_profile_panel
from .interior_set_profile_picker import InteriorSetProfilePicker
from .interior_set_scene_profile import (
    InteriorSetSceneProfile,
    load_scene_profile,
    save_scene_profile,
)


class InteriorSetProfileWorkflow:
    """Keep profile side effects outside the main settings-window owner."""

    def __init__(
        self,
        state: InteriorSetPanelState,
        controller: Callable[[], InteriorSetController | None],
        rebuild: Callable[[], None],
    ) -> None:
        self._state = state
        self._controller = controller
        self._rebuild = rebuild
        self._picker = InteriorSetProfilePicker()

    def build_panel(self) -> tuple[object, ...]:
        """Build profile controls from the retained transient UI state."""

        return build_interior_set_profile_panel(
            self.save,
            self.load,
            self._state.profile_status,
            collapsed=self._state.profile_collapsed,
            collapsed_changed=self.remember_collapsed,
        )

    def remember_collapsed(self, collapsed: bool) -> None:
        """Preserve the profile section across frame rebuilds."""

        self._state.profile_collapsed = bool(collapsed)

    def load(self) -> None:
        """Open a file dialog and stage the selected valid profile."""

        self._picker.choose_existing(
            self._state.profile_path,
            self._load_at,
        )

    def save(self) -> None:
        """Open a file dialog and save the applied snapshot immediately."""

        self._picker.choose_save_path(
            self._state.profile_path,
            self._save_at,
        )

    def stop(self) -> None:
        """Release import and export dialogs owned by this workflow."""

        self._picker.stop()

    def _load_at(self, path: str) -> None:
        controller = self._controller()
        if controller is None:
            return
        self._state.profile_path = path
        try:
            profile = load_scene_profile(path)
            controller.stage_profile(profile.collection, profile.atlas_mode)
            self._state.profile_status = (
                "Profile loaded to draft; Apply Interior Sets is required."
            )
        except Exception as error:
            self._report_error("load", error)
        self._rebuild()

    def _save_at(self, path: str) -> None:
        controller = self._controller()
        if controller is None:
            return
        excluded_draft = controller.dirty
        try:
            saved = save_scene_profile(
                path,
                InteriorSetSceneProfile(
                    collection=controller.applied,
                    atlas_mode=controller.applied_atlas_mode,
                ),
            )
            self._state.profile_path = str(saved)
            self._state.profile_status = "Applied profile saved." + (
                " Unapplied draft changes were not included."
                if excluded_draft
                else ""
            )
        except Exception as error:
            self._report_error("save", error)
        self._rebuild()

    def _report_error(self, action: str, error: Exception) -> None:
        import carb

        self._state.profile_status = f"Profile {action} failed: {error}"
        carb.log_error(f"[ORMS] Scene profile {action} failed: {error!r}")
