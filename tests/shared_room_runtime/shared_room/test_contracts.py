"""Protect shared-room runtime settings and immutable result contracts."""

from dataclasses import FrozenInstanceError

import pytest

from tools.omniverse.shared_room.contracts import RuntimeClassifierSettings


def test_runtime_settings_are_frozen_and_always_retain_x1_fallback():
    settings = RuntimeClassifierSettings(
        enabled_room_sizes=frozenset({3, 4}),
    )

    core = settings.core_settings(frozenset({1, 2, 3, 4}))

    assert core.enabled_room_sizes == frozenset({1, 3, 4})
    with pytest.raises(FrozenInstanceError):
        settings.partition_seed = 7
