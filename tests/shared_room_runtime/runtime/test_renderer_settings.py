"""Protect temporary RTX setting ownership and exact restoration."""

import pytest

from tools.omniverse.runtime import renderer_settings as renderer_module


def test_rtx_face_culling_setting_is_owned_and_restored(monkeypatch):
    class FakeSettings:
        def __init__(self):
            self.values = {
                renderer_module._RTX_FACE_CULLING_SETTING: False,
            }

        def get(self, path):
            return self.values[path]

        def set(self, path, value):
            self.values[path] = value

    fake_settings = FakeSettings()
    monkeypatch.setattr(
        renderer_module,
        "log_room_map_warning",
        lambda **_kwargs: None,
    )
    renderer_module._previous_rtx_face_culling = None
    renderer_module._owns_rtx_face_culling_setting = False

    renderer_module._enable_rtx_single_sided_culling(fake_settings)

    assert fake_settings.values[renderer_module._RTX_FACE_CULLING_SETTING]
    assert renderer_module._owns_rtx_face_culling_setting

    renderer_module._restore_rtx_single_sided_culling(fake_settings)

    assert not fake_settings.values[renderer_module._RTX_FACE_CULLING_SETTING]
    assert renderer_module._previous_rtx_face_culling is None
    assert not renderer_module._owns_rtx_face_culling_setting


@pytest.mark.parametrize("previous_value", [None, False, True])
def test_rtx_cutout_opacity_setting_is_owned_and_restored(
    monkeypatch,
    previous_value,
):
    class FakeSettings:
        def __init__(self):
            self.values = {
                renderer_module._RTX_OPACITY_OVERRIDE_SETTING: previous_value,
            }

        def get(self, path):
            return self.values[path]

        def set(self, path, value):
            self.values[path] = value

    fake_settings = FakeSettings()
    monkeypatch.setattr(
        renderer_module,
        "log_room_map_warning",
        lambda **_kwargs: None,
    )
    renderer_module._previous_rtx_opacity_override = None
    renderer_module._owns_rtx_opacity_override_setting = False

    renderer_module._enable_rtx_cutout_opacity(fake_settings)

    assert (
        fake_settings.values[renderer_module._RTX_OPACITY_OVERRIDE_SETTING]
        is True
    )
    assert renderer_module._owns_rtx_opacity_override_setting

    renderer_module._restore_rtx_cutout_opacity(fake_settings)

    assert fake_settings.values[
        renderer_module._RTX_OPACITY_OVERRIDE_SETTING
    ] is bool(previous_value)
    assert renderer_module._previous_rtx_opacity_override is None
    assert not renderer_module._owns_rtx_opacity_override_setting


def test_rtx_material_sync_settings_are_owned_and_restored_exactly(
    monkeypatch,
):
    material_db_path, hydra_path = renderer_module._RTX_MATERIAL_SYNC_SETTINGS

    class FakeSettings:
        def __init__(self):
            self.values = {hydra_path: False}

        def get(self, path):
            return self.values.get(path)

        def set(self, path, value):
            self.values[path] = value

        def destroy_item(self, path):
            self.values.pop(path, None)

    fake_settings = FakeSettings()
    monkeypatch.setattr(
        renderer_module,
        "log_room_map_warning",
        lambda **_kwargs: None,
    )
    renderer_module._previous_rtx_material_sync_values = None
    renderer_module._owns_rtx_material_sync_settings = False

    renderer_module._enable_rtx_material_sync_loads(fake_settings)

    assert fake_settings.values[material_db_path] is True
    assert fake_settings.values[hydra_path] is True
    assert renderer_module._owns_rtx_material_sync_settings

    renderer_module._restore_rtx_material_sync_loads(fake_settings)

    assert material_db_path not in fake_settings.values
    assert fake_settings.values[hydra_path] is False
    assert renderer_module._previous_rtx_material_sync_values is None
    assert not renderer_module._owns_rtx_material_sync_settings
