# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the one-to-many ORMS-window-to-material control contract."""

from msp.orms.shared_room.authoring import _SHARED_ARTIST_INPUT_NAMES
from msp.orms.shared_room.material_controls import (
    MATERIAL_CONTROLS,
    material_input_values_from_mapping,
    material_setting_path,
)
from pxr import Gf


def test_preferences_cover_every_shared_artist_input_once():
    names = tuple(control.name for control in MATERIAL_CONTROLS)

    assert len(names) == len(set(names))
    assert set(names) == set(_SHARED_ARTIST_INPUT_NAMES)
    assert material_setting_path("glass_roughness") == (
        "/persistent/exts/orms/material/glass_roughness"
    )


def test_persistent_vectors_are_coerced_to_usd_shader_types():
    values = material_input_values_from_mapping(
        {
            "window_shift": (0.25, -0.5),
            "glass_tint": (0.1, 0.2, 0.3),
        }
    )

    assert values["window_shift"] == Gf.Vec2f(0.25, -0.5)
    assert values["glass_tint"] == Gf.Vec3f(0.1, 0.2, 0.3)
    assert values["room_depth"] == 1.0
