# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect user-facing labels at the Kit-to-runtime settings boundary."""

import pytest
from msp.orms.shared_room.contracts import (
    INSTANCE_POLICY_PRESERVE,
    METRICS_MODE_LOCAL_OVERRIDE,
)
from msp.orms.shared_room.settings import settings_from_mapping


def test_removed_deinstance_preference_is_normalised_to_preserve():
    settings = settings_from_mapping(
        {
            "instance_policy": "Session de-instance",
            "metrics_mode": "Local override",
            "local_up_axis": "Z",
            "local_meters_per_unit": 0.01,
            "facade_angle_snap_degrees": 7.5,
            "maximum_local_spacing_ratio": 1.75,
            "corner_turn_threshold_degrees": 72.0,
        }
    )

    assert settings.instance_policy == INSTANCE_POLICY_PRESERVE
    assert settings.metrics_mode == METRICS_MODE_LOCAL_OVERRIDE
    assert settings.local_up_axis == "Z"
    assert settings.local_meters_per_unit == pytest.approx(0.01)
    assert settings.facade_angle_snap_degrees == pytest.approx(7.5)
    assert settings.maximum_local_spacing_ratio == pytest.approx(1.75)
    assert settings.corner_turn_threshold_degrees == pytest.approx(72.0)
    assert not hasattr(settings, "edge_gap_tolerance_metres")
