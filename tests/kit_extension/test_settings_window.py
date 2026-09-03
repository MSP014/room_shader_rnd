"""Protect the ORMS Window-menu surface and its direct model callbacks."""

from pathlib import Path

from msp.orms.runtime.interior_set_panel_state import InteriorSetPanelState
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


def test_structural_apply_retargets_camera_bridge_after_rebuild():
    from msp.orms.runtime.service import OrmsRuntimeService

    events = []

    class Classifier:
        camera_input_paths = ("/Looks/New/Shader.inputs:camera",)

        def apply_interior_sets(self, collection, resources):
            events.append(("rebuild", collection, resources))

    class Lifecycle:
        classifier = Classifier()

        def set_camera_input_paths(self, paths):
            events.append(("camera", tuple(paths)))

    service = OrmsRuntimeService.__new__(OrmsRuntimeService)
    service._lifecycle = Lifecycle()

    service._apply_interior_sets_to_runtime("sets", "resources")

    assert events == [
        ("rebuild", "sets", "resources"),
        ("camera", ("/Looks/New/Shader.inputs:camera",)),
    ]


def test_interior_set_ui_is_split_into_staged_and_live_modules():
    runtime_root = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
    )
    window_source = (runtime_root / "settings_window.py").read_text(
        encoding="utf-8"
    )
    atlas_source = (runtime_root / "interior_set_atlas_panel.py").read_text(
        encoding="utf-8"
    )
    material_source = (
        runtime_root / "interior_set_material_panel.py"
    ).read_text(encoding="utf-8")

    assert "build_interior_set_atlas_panel" in window_source
    assert "build_interior_set_material_panel" in window_source
    assert '"Apply Interior Sets"' in atlas_source
    assert '"Revert unapplied changes"' in atlas_source
    assert '"+ Add Interior Set"' in atlas_source
    assert '"Duplicate"' in atlas_source
    assert '"Browse..."' in atlas_source
    assert "Default is evaluated last" in atlas_source
    assert '"Debug (force packaged)"' in atlas_source
    assert '"Production + debug fallback"' in atlas_source
    assert "InteriorSetProfileWorkflow" in window_source
    assert "MATERIAL_CONTROLS" in material_source
    assert "material_changed(" in material_source


def test_content_rebuild_preserves_window_and_selected_tab():
    from msp.orms.runtime.settings_window import OrmsSettingsWindow

    class Frame:
        def __init__(self):
            self.rebuild_count = 0

        def rebuild(self):
            self.rebuild_count += 1

    class Window:
        def __init__(self):
            self.frame = Frame()

    settings_window = OrmsSettingsWindow()
    window = Window()
    settings_window._window = window
    settings_window._active_tab_index = 2
    settings_window._remember_debug_atlases_collapsed(True)

    settings_window._rebuild_window()

    assert settings_window._window is window
    assert settings_window._active_tab_index == 2
    assert settings_window._panel_state.debug_atlases_collapsed is True
    assert window.frame.rebuild_count == 1


def test_interior_set_collapsed_state_follows_uuid_through_reorder():
    state = InteriorSetPanelState()
    default_id = "00000000-0000-0000-0000-000000000000"
    living_id = "11111111-1111-1111-1111-111111111111"
    cabinets_id = "22222222-2222-2222-2222-222222222222"

    state.remember_set_collapsed(default_id, True)
    state.remember_set_collapsed(living_id, True)
    state.remember_set_collapsed(cabinets_id, False)
    state.retain_sets((default_id, cabinets_id, living_id))

    assert state.is_set_collapsed(default_id) is True
    assert state.is_set_collapsed(living_id) is True
    assert state.is_set_collapsed(cabinets_id) is False

    state.retain_sets((default_id, cabinets_id))

    assert state.is_set_collapsed(living_id) is False


def test_classifier_and_material_collapse_state_survives_rebuilds():
    state = InteriorSetPanelState()
    living_id = "11111111-1111-1111-1111-111111111111"
    removed_id = "22222222-2222-2222-2222-222222222222"
    classifier_key = "classifier:room_families"
    set_key = f"material:set:{living_id}"
    group_key = f"{set_key}:group:glass"
    removed_key = f"material:set:{removed_id}"

    state.remember_section_collapsed(classifier_key, True)
    state.remember_section_collapsed(set_key, True)
    state.remember_section_collapsed(group_key, True)
    state.remember_section_collapsed(removed_key, True)
    state.retain_sets((living_id,))

    assert state.is_section_collapsed(classifier_key) is True
    assert state.is_section_collapsed(set_key) is True
    assert state.is_section_collapsed(group_key) is True
    assert state.is_section_collapsed(removed_key) is False


def test_extension_declares_standard_directory_picker_dependency():
    config_path = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "config"
        / "extension.toml"
    )

    assert '"omni.kit.window.file_importer" = {}' in (
        config_path.read_text(encoding="utf-8")
    )
    assert '"omni.kit.window.file_exporter" = {}' in (
        config_path.read_text(encoding="utf-8")
    )
