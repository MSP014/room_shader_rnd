# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Verify every retained fixture resolves a complete hydrated UDIM family."""

from pathlib import Path

import pytest
from pxr import Usd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIRECTORY = REPOSITORY_ROOT / "tests"
TEXTURE_DIRECTORY = (
    REPOSITORY_ROOT / "exts" / "msp.orms.runtime" / "data" / "atlases"
)

DEBUG_TEXTURE_FAMILIES = (
    ("room_map_debug_x1", 1001),
    ("room_map_debug_x2", 1001),
    ("room_map_debug_x3", 1001),
    ("room_map_debug_x4", 1001),
)
TILES_PER_FAMILY = 8
ROOM_MAP_STAGE_PATHS = tuple(
    sorted(TESTS_DIRECTORY.glob("test_room_map_*.usda"))
)


def _expected_family_paths(family_name, first_tile):
    family_directory = TEXTURE_DIRECTORY / family_name
    return {
        (family_directory / f"{family_name}.{tile_number:04d}.png").resolve()
        for tile_number in range(first_tile, first_tile + TILES_PER_FAMILY)
    }


EXPECTED_TEXTURE_PATHS = frozenset(
    path
    for family_name, first_tile in DEBUG_TEXTURE_FAMILIES
    for path in _expected_family_paths(family_name, first_tile)
)


def _authored_atlas_paths(stage_path):
    stage = Usd.Stage.Open(str(stage_path), load=Usd.Stage.LoadAll)

    assert stage, f"Could not open Room Map test stage: {stage_path.name}"

    atlas_paths = []
    prim_ranges = [stage.Traverse()]
    prim_ranges.extend(
        Usd.PrimRange(prototype) for prototype in stage.GetPrototypes()
    )
    for prim_range in prim_ranges:
        for prim in prim_range:
            atlas_attribute = prim.GetAttribute("inputs:room_atlas")
            if (
                not atlas_attribute
                or not atlas_attribute.HasAuthoredValueOpinion()
            ):
                continue

            atlas_asset = atlas_attribute.Get()
            if atlas_asset and atlas_asset.path:
                atlas_paths.append(atlas_asset.path)

    return atlas_paths


def _referenced_texture_paths(stage_path, authored_path):
    pattern_path = (stage_path.parent / authored_path).resolve()
    pattern_name = pattern_path.name

    if "<UDIM>" not in pattern_name:
        return {pattern_path}

    return {
        path.resolve()
        for path in pattern_path.parent.glob(
            pattern_name.replace("<UDIM>", "*")
        )
    }


@pytest.mark.parametrize(
    ("family_name", "first_tile"),
    DEBUG_TEXTURE_FAMILIES,
    ids=[family_name for family_name, _first_tile in DEBUG_TEXTURE_FAMILIES],
)
def test_debug_texture_family_contains_every_required_tile(
    family_name, first_tile
):
    expected_paths = _expected_family_paths(family_name, first_tile)
    missing_paths = sorted(
        path for path in expected_paths if not path.is_file()
    )

    assert (
        not missing_paths
    ), f"Missing {family_name} debug texture files: " + ", ".join(
        path.name for path in missing_paths
    )


def test_every_room_map_stage_references_hydrated_debug_textures():
    assert ROOM_MAP_STAGE_PATHS

    for stage_path in ROOM_MAP_STAGE_PATHS:
        authored_paths = _authored_atlas_paths(stage_path)

        assert (
            authored_paths
        ), f"Room Map test stage has no authored room_atlas: {stage_path.name}"

        for authored_path in authored_paths:
            referenced_paths = _referenced_texture_paths(
                stage_path, authored_path
            )
            unexpected_paths = referenced_paths - EXPECTED_TEXTURE_PATHS

            assert referenced_paths, (
                f"Room Map atlas resolves to no files in {stage_path.name}: "
                f"{authored_path}"
            )
            assert not unexpected_paths, (
                "Room Map stage references unmanaged texture files in "
                f"{stage_path.name}: "
                + ", ".join(str(path) for path in sorted(unexpected_paths))
            )
            assert all(path.is_file() for path in referenced_paths)
