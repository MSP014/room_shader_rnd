# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect demo onboarding without replacing established ORMS settings."""

import asyncio

import pytest
from msp.orms.interior_sets.atlas_mode import ATLAS_MODE_PRODUCTION
from msp.orms.interior_sets.contracts import InteriorSetCollection
from msp.orms.runtime.demo_scene import open_demo_scene
from msp.orms.runtime.profiles.scene_profile import (
    InteriorSetSceneProfile,
    save_scene_profile,
)

from . import _support  # noqa: F401


class _Controller:
    def __init__(self, factory: bool):
        self.is_factory_configuration = factory
        self.staged = []

    def stage_profile(self, collection, atlas_mode):
        self.staged.append((collection, atlas_mode))


def _profile_path(tmp_path):
    return save_scene_profile(
        str(tmp_path / "demo.orms"),
        InteriorSetSceneProfile(
            InteriorSetCollection.default_only(),
            ATLAS_MODE_PRODUCTION,
        ),
    )


def test_demo_profile_applies_only_over_untouched_factory_settings(tmp_path):
    stage_path = tmp_path / "demo.usd"
    stage_path.touch()
    controller = _Controller(factory=True)
    applied = []

    async def open_stage(path):
        assert path == stage_path.as_posix()
        return True, ""

    status = asyncio.run(
        open_demo_scene(
            stage_path,
            _profile_path(tmp_path),
            controller,
            lambda: applied.append(True),
            open_stage,
            auto_apply_profile=True,
        )
    )

    assert len(controller.staged) == 1
    assert controller.staged[0][1] == ATLAS_MODE_PRODUCTION
    assert applied == [True]
    assert "profile was applied" in status


def test_demo_open_preserves_existing_configuration(tmp_path):
    controller = _Controller(factory=False)

    async def open_stage(_path):
        return True, ""

    status = asyncio.run(
        open_demo_scene(
            tmp_path / "demo.usd",
            _profile_path(tmp_path),
            controller,
            lambda: pytest.fail("existing settings must not be applied over"),
            open_stage,
            auto_apply_profile=True,
        )
    )

    assert controller.staged == []
    assert "preserved" in status


def test_demo_open_reports_kit_failure(tmp_path):
    async def fail_open(_path):
        return False, "invalid stage"

    with pytest.raises(RuntimeError, match="invalid stage"):
        asyncio.run(
            open_demo_scene(
                tmp_path / "demo.usd",
                _profile_path(tmp_path),
                _Controller(factory=True),
                lambda: None,
                fail_open,
                auto_apply_profile=True,
            )
        )
