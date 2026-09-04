"""Own ORMS visibility within a host Material Library allow-list."""

from __future__ import annotations

import fnmatch
from collections.abc import Callable

_SHOW_LIST_SETTING = "/exts/omni.kit.material.library/ui_show_list"


class MaterialVisibilityOwner:
    """Add and remove only the ORMS entry required by a restricted host."""

    def __init__(
        self,
        *,
        get_values: Callable[[], object] | None = None,
        set_values: Callable[[list[str]], None] | None = None,
    ) -> None:
        self._get_values = get_values
        self._set_values = set_values
        self._added_entry: str | None = None

    def _load_kit_apis(self) -> None:
        if self._get_values is not None:
            return
        import carb.settings

        settings = carb.settings.get_settings()
        self._get_values = lambda: settings.get(_SHOW_LIST_SETTING)
        self._set_values = lambda values: settings.set(
            _SHOW_LIST_SETTING,
            values,
        )

    def _current_values(self) -> list[str]:
        get_values = self._get_values
        if get_values is None:
            raise RuntimeError(
                "The host did not provide Material Library settings"
            )
        values = get_values()
        if not values:
            return []
        return [str(value) for value in values]

    def start(self, display_name: str) -> None:
        """Expose ORMS only when the host uses a restrictive allow-list."""

        self._load_kit_apis()
        set_values = self._set_values
        if set_values is None:
            raise RuntimeError(
                "The host did not provide Material Library settings"
            )
        values = self._current_values()
        if not values:
            return
        if any(fnmatch.fnmatch(display_name, pattern) for pattern in values):
            return
        set_values([*values, display_name])
        self._added_entry = display_name

    def stop(self) -> None:
        """Remove the exact allow-list entry added by this owner."""

        added_entry, self._added_entry = self._added_entry, None
        if added_entry is None:
            return
        set_values = self._set_values
        if set_values is None:
            raise RuntimeError(
                "The host did not provide Material Library settings"
            )
        values = self._current_values()
        removed = False
        retained = []
        for value in values:
            if value == added_entry and not removed:
                removed = True
                continue
            retained.append(value)
        if removed:
            set_values(retained)
