# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect installed Kit import/export signatures for `.orms` profiles."""

import sys
from pathlib import Path
from types import ModuleType

from msp.orms.runtime.profiles.picker import (
    InteriorSetProfilePicker,
    export_filename_url,
    exported_profile_path,
    selected_profile_path,
)


def _install_picker_modules(monkeypatch, importer, exporter):
    omni = ModuleType("omni")
    omni.__path__ = []
    kit = ModuleType("omni.kit")
    kit.__path__ = []
    window = ModuleType("omni.kit.window")
    window.__path__ = []
    file_importer = ModuleType("omni.kit.window.file_importer")
    file_importer.get_file_importer = lambda: importer
    file_exporter = ModuleType("omni.kit.window.file_exporter")
    file_exporter.get_file_exporter = lambda: exporter
    monkeypatch.setitem(sys.modules, "omni", omni)
    monkeypatch.setitem(sys.modules, "omni.kit", kit)
    monkeypatch.setitem(sys.modules, "omni.kit.window", window)
    monkeypatch.setitem(
        sys.modules,
        "omni.kit.window.file_importer",
        file_importer,
    )
    monkeypatch.setitem(
        sys.modules,
        "omni.kit.window.file_exporter",
        file_exporter,
    )


def test_profile_path_helpers_enforce_the_custom_suffix():
    assert selected_profile_path("tower.orms", "C:/profiles") == str(
        Path("C:/profiles/tower.orms")
    )
    assert exported_profile_path("tower", "C:/profiles", ".orms") == str(
        Path("C:/profiles/tower.orms")
    )
    assert export_filename_url("C:/profiles/tower.orms") == (
        "C:/profiles/tower"
    )


def test_profile_picker_uses_installed_import_and_export_contracts(
    monkeypatch,
):
    import_calls = []
    export_calls = []

    class Importer:
        def show_window(self, **options):
            import_calls.append(options)

    class Exporter:
        def show_window(self, **options):
            export_calls.append(options)

    _install_picker_modules(monkeypatch, Importer(), Exporter())
    selected = []
    picker = InteriorSetProfilePicker()

    picker.choose_existing("C:/profiles/current.orms", selected.append)
    picker.choose_save_path("C:/profiles/current.orms", selected.append)

    assert import_calls[0]["file_extension"] == ".orms"
    assert import_calls[0]["should_validate"] is True
    assert "click_cancel_handler" not in import_calls[0]
    import_calls[0]["import_handler"](
        "loaded.orms",
        "C:/profiles",
        (),
    )
    assert export_calls[0]["file_extension"] == ".orms"
    assert export_calls[0]["should_validate"] is False
    export_calls[0]["export_handler"](
        filename="saved",
        dirname="C:/profiles",
        extension=".orms",
        selections=(),
    )
    assert selected == [
        str(Path("C:/profiles/loaded.orms")),
        str(Path("C:/profiles/saved.orms")),
    ]
