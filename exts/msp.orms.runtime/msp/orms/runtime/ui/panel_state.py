"""Retain transient ORMS presentation state across UI rebuilds."""

from __future__ import annotations

from collections.abc import Iterable


class InteriorSetPanelState:
    """Track collapsed sections by stable identity, never by visible order."""

    def __init__(self) -> None:
        self.debug_atlases_collapsed = False
        self.profile_collapsed = False
        self.atlas_mode_collapsed = False
        self.profile_path = ""
        self.profile_status: str | None = None
        self._set_collapsed: dict[str, bool] = {}
        self._section_collapsed: dict[str, bool] = {}

    def is_set_collapsed(self, set_id: str) -> bool:
        """Return the remembered state, defaulting new Set blocks to open."""

        return self._set_collapsed.get(set_id, False)

    def remember_set_collapsed(self, set_id: str, collapsed: bool) -> None:
        """Remember one Set block independently from name and priority."""

        self._set_collapsed[set_id] = bool(collapsed)

    def is_section_collapsed(
        self,
        section_id: str,
        default: bool = False,
    ) -> bool:
        """Return state for a classifier or material section."""

        return self._section_collapsed.get(section_id, default)

    def remember_section_collapsed(
        self,
        section_id: str,
        collapsed: bool,
    ) -> None:
        """Remember a non-atlas section by its stable semantic key."""

        self._section_collapsed[section_id] = bool(collapsed)

    def retain_sets(self, set_ids: Iterable[str]) -> None:
        """Discard presentation state for Sets no longer in the draft."""

        retained = set(set_ids)
        self._set_collapsed = {
            set_id: collapsed
            for set_id, collapsed in self._set_collapsed.items()
            if set_id in retained
        }
        self._section_collapsed = {
            section_id: collapsed
            for section_id, collapsed in self._section_collapsed.items()
            if not section_id.startswith("material:set:")
            or section_id.split(":", 3)[2] in retained
        }

    def reset(self) -> None:
        """Restore initial presentation state when the window stops."""

        self.debug_atlases_collapsed = False
        self.profile_collapsed = False
        self.atlas_mode_collapsed = False
        self.profile_path = ""
        self.profile_status = None
        self._set_collapsed.clear()
        self._section_collapsed.clear()
