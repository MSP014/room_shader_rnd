# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Open bundled ORMS demo content without replacing established settings."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from .interior_sets.controller import InteriorSetController
from .profiles.scene_profile import load_scene_profile

OpenStageAsync = Callable[[str], Awaitable[object]]


def _stage_open_result(result: object) -> tuple[bool, str]:
    if isinstance(result, tuple):
        success = bool(result[0]) if result else False
        message = str(result[1]) if len(result) > 1 else ""
        return success, message
    return bool(result), ""


async def open_demo_scene(
    stage_path: Path,
    profile_path: Path,
    controller: InteriorSetController,
    apply_interior_sets: Callable[[], None],
    open_stage_async: OpenStageAsync,
    *,
    auto_apply_profile: bool,
) -> str:
    """Open the demo and apply its profile only over untouched defaults."""

    result = await open_stage_async(stage_path.as_posix())
    success, message = _stage_open_result(result)
    if not success:
        detail = message or "Kit did not provide an error message"
        raise RuntimeError(f"Cannot open the ORMS demo scene: {detail}")

    if auto_apply_profile and controller.is_factory_configuration:
        profile = load_scene_profile(str(profile_path))
        controller.stage_profile(profile.collection, profile.atlas_mode)
        apply_interior_sets()
        return "Demo scene opened and its atlas profile was applied."
    return "Demo scene opened. Existing ORMS configuration was preserved."
