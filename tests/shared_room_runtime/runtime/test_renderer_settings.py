# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect temporary RTX setting ownership and exact restoration."""

import pytest
from msp.orms.scene import renderer_settings as renderer_module


@pytest.mark.parametrize("previous_value", [None, False, True])
def test_rtx_cutout_opacity_setting_is_owned_and_restored(
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


def test_rtx_cutout_opacity_routine_trace_can_be_muted():
    class FakeSettings:
        def __init__(self):
            self.values = {
                renderer_module._RTX_OPACITY_OVERRIDE_SETTING: False,
            }

        def get(self, path):
            return self.values[path]

        def set(self, path, value):
            self.values[path] = value

    fake_settings = FakeSettings()
    renderer_module._previous_rtx_opacity_override = None
    renderer_module._owns_rtx_opacity_override_setting = False

    renderer_module._enable_rtx_cutout_opacity(
        fake_settings,
        log_warning=None,
    )
    renderer_module._restore_rtx_cutout_opacity(
        fake_settings,
        log_warning=None,
    )

    assert not renderer_module._owns_rtx_opacity_override_setting
