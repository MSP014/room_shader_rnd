"""Protect folder selection normalisation without requiring Kit UI."""

import os
import sys
from pathlib import Path
from types import ModuleType

from msp.orms.runtime.interior_set_directory_picker import (
    InteriorSetDirectoryPicker,
    directory_url,
    selected_directory,
)


def test_selected_folder_prefers_explicit_browser_selection():
    selected = str(Path("C:/atlases/kitchens"))

    assert selected_directory("", "C:/atlases", (selected,)) == selected


def test_selected_folder_ignores_stale_filename_input():
    expected = str(Path("C:/atlases/kitchens"))

    assert selected_directory("room_maps", expected) == expected


def test_directory_url_does_not_populate_the_filename_input():
    current = str(Path("C:/atlases/kitchens"))

    assert directory_url(current) == os.path.join(current, "")


def test_picker_uses_the_installed_file_importer_signature(monkeypatch):
    calls = []

    class Importer:
        def show_window(self, **options):
            calls.append(options)

    importer = Importer()
    omni = ModuleType("omni")
    omni.__path__ = []
    kit = ModuleType("omni.kit")
    kit.__path__ = []
    window = ModuleType("omni.kit.window")
    window.__path__ = []
    file_importer = ModuleType("omni.kit.window.file_importer")
    file_importer.get_file_importer = lambda: importer
    monkeypatch.setitem(sys.modules, "omni", omni)
    monkeypatch.setitem(sys.modules, "omni.kit", kit)
    monkeypatch.setitem(sys.modules, "omni.kit.window", window)
    monkeypatch.setitem(
        sys.modules,
        "omni.kit.window.file_importer",
        file_importer,
    )
    selected = []
    picker = InteriorSetDirectoryPicker()

    picker.choose("C:/atlases", selected.append)

    assert len(calls) == 1
    assert "click_cancel_handler" not in calls[0]
    assert calls[0]["should_validate"] is False
    assert calls[0]["filename_url"].endswith(os.sep)
    calls[0]["import_handler"]("room_maps", "C:/atlases/kitchens", ())
    assert selected == [str(Path("C:/atlases/kitchens"))]
