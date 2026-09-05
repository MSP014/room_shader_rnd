# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect immutable defaults in the room-run plain-data contracts."""

from dataclasses import FrozenInstanceError

import pytest
from msp.orms.classification.contracts import (
    ApertureDescriptor,
    ClassifierSettings,
)


def test_classifier_contracts_are_frozen_and_use_metric_defaults():
    aperture = ApertureDescriptor(
        key="window",
        prim_path="/World/Building/Windows",
        face_index=0,
        building_root="/World/Building",
        room_id=1,
        centre_metres=(0.0, 0.0, 0.0),
        tangent_u_metres=(1.0, 0.0, 0.0),
        tangent_v_metres=(0.0, 1.0, 0.0),
    )
    settings = ClassifierSettings()

    assert settings.available_room_sizes == frozenset({1, 2, 3, 4})
    assert settings.identity_quantisation_metres == pytest.approx(0.001)
    with pytest.raises(FrozenInstanceError):
        aperture.room_id = 2
