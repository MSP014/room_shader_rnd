"""Protect the ORMS Window-menu surface and its direct model callbacks."""

from pathlib import Path

from msp.orms.runtime.resources import (
    DEBUG_ASSET_SETTING,
    PRODUCTION_DIRECTORY_SETTING,
)
from msp.orms.runtime.settings_window import MENU_GROUP, WINDOW_NAME

from tools.omniverse.shared_room.settings_panel import SETTINGS_TAB_LABELS


def test_settings_live_in_one_dockable_orms_window():
    assert WINDOW_NAME == "ORMS"
    assert MENU_GROUP == "Window"
    assert SETTINGS_TAB_LABELS == (
        "ORMS Classifier",
        "Material Parameters",
        "Interior Atlases",
    )


def test_debug_and_production_atlases_have_separate_setting_zones():
    assert PRODUCTION_DIRECTORY_SETTING.endswith(
        "/atlases/x{room_size}/directory"
    )
    assert DEBUG_ASSET_SETTING.endswith("/atlases/debug/x{room_size}/asset")


def test_scalar_and_item_models_both_notify_the_runtime():
    from msp.orms.runtime.settings_window import OrmsSettingsWindow

    events = []

    class ScalarModel:
        def add_value_changed_fn(self, callback):
            callback(self)

    class ItemModel:
        def add_item_changed_fn(self, callback):
            callback(self, object())

    OrmsSettingsWindow._subscribe_model(
        ScalarModel(),
        lambda: events.append("scalar"),
    )
    OrmsSettingsWindow._subscribe_model(
        ItemModel(),
        lambda: events.append("item"),
    )

    assert events == ["scalar", "item"]


def test_service_owns_window_lifecycle_outside_stage_lifecycle():
    service_path = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
        / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")

    assert "self._settings_window.start(" in source
    assert "settings_window.stop()" in source
    assert "classifier.set_settings(settings_from_kit())" in source
    assert "self._lifecycle.pause()" in source
    assert "self._lifecycle.resume()" in source
    assert "self._lifecycle.teardown()" in source
    assert "Preferences" not in source


def test_service_skips_runtime_without_a_room_map_source_mesh():
    service_path = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
        / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")

    assert "if not stage_has_room_map_source_mesh(stage):" in source
    assert "Stage activation skipped" in source
