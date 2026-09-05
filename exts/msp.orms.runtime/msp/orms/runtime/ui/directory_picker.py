# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Own the standard Kit folder picker used by Interior Set atlas fields."""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence


def selected_directory(
    filename: str,
    dirname: str,
    selections: Sequence[str] = (),
) -> str:
    """Return one normalised local directory from importer callback values."""

    del filename
    if selections:
        return os.path.normpath(str(selections[-1]))
    return os.path.normpath(dirname) if dirname else ""


def directory_url(directory: str) -> str | None:
    """Keep Kit from treating the final folder component as a filename."""

    return os.path.join(directory, "") if directory else None


class InteriorSetDirectoryPicker:
    """Present one singleton folder picker without owning persistent state."""

    def __init__(self) -> None:
        self._open = False

    def choose(
        self,
        current_directory: str,
        changed: Callable[[str], None],
    ) -> None:
        """Open the picker and return the accepted folder to local draft UI."""

        from omni.kit.window.file_importer import get_file_importer

        importer = get_file_importer()
        if importer is None:
            raise RuntimeError("The Kit directory picker is unavailable")

        def accepted(
            filename: str,
            dirname: str,
            selections: Sequence[str] = (),
        ) -> None:
            self._open = False
            changed(selected_directory(filename, dirname, selections))

        self._open = True
        importer.show_window(
            title="Select ORMS atlas folder",
            show_only_collections=["my-computer"],
            show_only_folders=True,
            import_button_label="Select folder",
            import_handler=accepted,
            filename_url=directory_url(current_directory),
            hide_window_on_import=True,
            # Kit validates dirname + filename as a file even when its browser
            # is restricted to folders. The accepted callback is authoritative.
            should_validate=False,
            focus_filename_input=False,
            allow_multi_files_selection=False,
        )

    def stop(self) -> None:
        """Close only a picker opened by this ORMS window."""

        if not self._open:
            return
        from omni.kit.window.file_importer import get_file_importer

        importer = get_file_importer()
        if importer is not None:
            importer.hide_window()
        self._open = False
