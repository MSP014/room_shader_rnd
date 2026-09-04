"""Own local import/export dialogs for portable `.orms` profiles."""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence

from .scene_profile import PROFILE_SUFFIX

_PROFILE_TYPES = [(PROFILE_SUFFIX, "ORMS scene profile")]


def selected_profile_path(
    filename: str,
    dirname: str,
    selections: Sequence[str] = (),
) -> str:
    """Resolve one import callback to a local file path."""

    if selections:
        return os.path.normpath(str(selections[-1]))
    return os.path.normpath(os.path.join(dirname, filename))


def exported_profile_path(
    filename: str,
    dirname: str,
    extension: str,
) -> str:
    """Resolve one exporter callback and enforce the `.orms` suffix."""

    suffix = extension or PROFILE_SUFFIX
    name = filename
    if not name.lower().endswith(suffix.lower()):
        name += suffix
    return os.path.normpath(os.path.join(dirname, name))


def export_filename_url(current_path: str) -> str | None:
    """Exclude the extension as required by Kit's exporter contract."""

    if not current_path:
        return None
    root, extension = os.path.splitext(current_path)
    return root if extension.lower() == PROFILE_SUFFIX else current_path


class InteriorSetProfilePicker:
    """Present compatible singleton dialogs without owning profile state."""

    def __init__(self) -> None:
        self._import_open = False
        self._export_open = False

    def choose_existing(
        self,
        current_path: str,
        changed: Callable[[str], None],
    ) -> None:
        """Select one existing `.orms` file and return its path."""

        from omni.kit.window.file_importer import get_file_importer

        importer = get_file_importer()
        if importer is None:
            raise RuntimeError("The Kit file importer is unavailable")

        def accepted(
            filename: str,
            dirname: str,
            selections: Sequence[str] = (),
        ) -> None:
            self._import_open = False
            changed(selected_profile_path(filename, dirname, selections))

        self._import_open = True
        importer.show_window(
            title="Select ORMS scene profile",
            show_only_collections=["my-computer"],
            show_only_folders=False,
            file_extension_types=_PROFILE_TYPES,
            file_extension=PROFILE_SUFFIX,
            import_button_label="Select profile",
            import_handler=accepted,
            filename_url=current_path or None,
            hide_window_on_import=True,
            should_validate=True,
            focus_filename_input=True,
            allow_multi_files_selection=False,
        )

    def choose_save_path(
        self,
        current_path: str,
        changed: Callable[[str], None],
    ) -> None:
        """Select a `.orms` destination and return its path."""

        from omni.kit.window.file_exporter import get_file_exporter

        exporter = get_file_exporter()
        if exporter is None:
            raise RuntimeError("The Kit file exporter is unavailable")

        def accepted(
            filename: str,
            dirname: str,
            extension: str = "",
            selections: Sequence[str] = (),
        ) -> None:
            del selections
            self._export_open = False
            changed(exported_profile_path(filename, dirname, extension))

        self._export_open = True
        exporter.show_window(
            title="Save ORMS scene profile as",
            show_only_collections=["my-computer"],
            show_only_folders=False,
            file_extension_types=_PROFILE_TYPES,
            file_extension=PROFILE_SUFFIX,
            export_button_label="Save Profile",
            export_handler=accepted,
            filename_url=export_filename_url(current_path),
            should_validate=False,
            enable_filename_input=True,
            focus_filename_input=True,
        )

    def stop(self) -> None:
        """Close only profile dialogs opened by this owner."""

        if self._import_open:
            from omni.kit.window.file_importer import get_file_importer

            importer = get_file_importer()
            if importer is not None:
                importer.hide_window()
        if self._export_open:
            from omni.kit.window.file_exporter import get_file_exporter

            exporter = get_file_exporter()
            if exporter is not None:
                exporter.hide_window()
        self._import_open = False
        self._export_open = False
