# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Resolve portable MDL and atlas resources without hard-coded install paths."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from msp.orms.interior_sets.contracts import VariantIdentityManifest

from .materials.atlas_manifest import (
    debug_variant_manifest,
    load_variant_manifest,
)

MATERIAL_SOURCE_ASSET = "room_map.mdl"
MATERIAL_SUBIDENTIFIER = "room_map"
DEBUG_VARIANT_COUNT = 8
PRODUCTION_DIRECTORY_SETTING = (
    "/persistent/exts/msp.orms.runtime/atlases/x{room_size}/directory"
)
DEBUG_ASSET_SETTING = (
    "/persistent/exts/msp.orms.runtime/atlases/debug/x{room_size}/asset"
)

_UDIM_SEED_PATTERN = re.compile(r"(?<!\d)1001(?!\d)")
# This is a texture filename placeholder, never authentication material.
_UDIM_TOKEN = "<UDIM>"  # nosec B105

_DEBUG_FAMILY_NAMES = {
    1: "room_map_debug_x1",
    2: "room_map_debug_x2",
    3: "room_map_debug_x3",
    4: "room_map_debug_x4",
}

_DEMO_STAGE_RELATIVE_PATH = (
    Path("Moskovskiy_av_150") / "usd" / "Moskovskiy_av_150_HDRI.usd"
)
_DEMO_PROFILE_RELATIVE_PATH = (
    Path("Moskovskiy_av_150") / "usd" / "test_150.orms"
)


@dataclass(frozen=True)
class AtlasResource:
    """Describe one complete UDIM family and its valid variant count."""

    room_size: int
    asset_path: Path
    variant_count: int
    source: str
    variant_manifest: VariantIdentityManifest | None = None


@dataclass(frozen=True)
class ResourceLayout:
    """Resolve relocatable runtime and optional demo resources."""

    extension_root: Path
    mdl_root: Path
    debug_atlases: tuple[AtlasResource, ...]
    demo_stage: Path | None = None
    demo_profile: Path | None = None

    @classmethod
    def discover(cls, module_file: str | Path) -> "ResourceLayout":
        """Find resources relative to the installed extension or source checkout."""

        extension_root = Path(module_file).resolve().parents[3]
        mdl_root = extension_root / "data" / "mdl"
        if not _contains_runtime_mdl(mdl_root):
            raise FileNotFoundError(
                "The ORMS extension has no packaged room_map.mdl resources"
            )

        debug_atlases = []
        for room_size, family_name in _DEBUG_FAMILY_NAMES.items():
            packaged_asset = (
                extension_root
                / "data"
                / "atlases"
                / family_name
                / f"{family_name}.<UDIM>.png"
            )
            if _is_complete_udim_family(packaged_asset):
                debug_atlases.append(
                    AtlasResource(
                        room_size,
                        packaged_asset,
                        DEBUG_VARIANT_COUNT,
                        "packaged",
                        debug_variant_manifest(DEBUG_VARIANT_COUNT),
                    )
                )

        demo_stage, demo_profile = _discover_demo_content(extension_root)
        return cls(
            extension_root=extension_root,
            mdl_root=mdl_root,
            debug_atlases=tuple(debug_atlases),
            demo_stage=demo_stage,
            demo_profile=demo_profile,
        )

    def debug_atlas(self, room_size: int) -> AtlasResource | None:
        """Return one complete packaged or development debug family."""

        return next(
            (
                atlas
                for atlas in self.debug_atlases
                if atlas.room_size == room_size
            ),
            None,
        )


@dataclass(frozen=True)
class DebugAtlasDecision:
    """Describe one global debug override and its packaged fallback."""

    room_size: int
    configured_directory: str
    atlas: AtlasResource | None
    validation_error: str | None = None

    @property
    def uses_override(self) -> bool:
        """Return whether the configured directory resolved successfully."""

        return (
            bool(self.configured_directory) and self.validation_error is None
        )


def _contains_runtime_mdl(directory: Path) -> bool:
    return all(
        (directory / filename).is_file()
        for filename in ("room_map.mdl", "room_map_single.mdl")
    )


def _discover_demo_content(
    extension_root: Path,
) -> tuple[Path | None, Path | None]:
    """Find demo content in an installed bundle or its source checkout."""

    candidates = (
        extension_root / "data" / "demo",
        extension_root.parents[1] / "assets" / "_demo",
    )
    for demo_root in candidates:
        stage = demo_root / _DEMO_STAGE_RELATIVE_PATH
        profile = demo_root / _DEMO_PROFILE_RELATIVE_PATH
        if stage.is_file() and profile.is_file():
            return stage, profile
    return None, None


def _is_complete_udim_family(asset_path: Path) -> bool:
    asset_name = asset_path.name
    if "<UDIM>" not in asset_name:
        return False
    return all(
        asset_path.with_name(asset_name.replace("<UDIM>", str(tile))).is_file()
        for tile in range(1001, 1009)
    )


def discover_production_atlas(
    *,
    room_size: int,
    atlas_directory: str | Path,
) -> AtlasResource:
    """Discover one continuous UDIM family inside an external directory."""

    return _discover_directory_atlas(
        room_size=room_size,
        atlas_directory=atlas_directory,
        source="production",
    )


def discover_debug_atlas(
    *,
    room_size: int,
    atlas_directory: str | Path,
) -> AtlasResource:
    """Discover one artist-selected global debug atlas family."""

    atlas = _discover_directory_atlas(
        room_size=room_size,
        atlas_directory=atlas_directory,
        source="debug override",
    )
    manifest = atlas.variant_manifest or debug_variant_manifest(
        atlas.variant_count
    )
    return AtlasResource(
        room_size=atlas.room_size,
        asset_path=atlas.asset_path,
        variant_count=atlas.variant_count,
        source=atlas.source,
        variant_manifest=manifest,
    )


def resolve_debug_atlases(
    resources: ResourceLayout,
    atlas_directories: tuple[str, str, str, str],
) -> tuple[DebugAtlasDecision, ...]:
    """Resolve global debug overrides with source-owned safe fallbacks."""

    if len(atlas_directories) != 4:
        raise ValueError("Debug atlas overrides require x1-x4 directories")
    decisions = []
    for room_size, configured in enumerate(atlas_directories, start=1):
        directory = str(configured).strip()
        if not directory:
            decisions.append(
                DebugAtlasDecision(
                    room_size=room_size,
                    configured_directory="",
                    atlas=resources.debug_atlas(room_size),
                )
            )
            continue
        try:
            atlas = discover_debug_atlas(
                room_size=room_size,
                atlas_directory=directory,
            )
        except (FileNotFoundError, ValueError) as error:
            decisions.append(
                DebugAtlasDecision(
                    room_size=room_size,
                    configured_directory=directory,
                    atlas=resources.debug_atlas(room_size),
                    validation_error=str(error),
                )
            )
        else:
            decisions.append(
                DebugAtlasDecision(
                    room_size=room_size,
                    configured_directory=directory,
                    atlas=atlas,
                )
            )
    return tuple(decisions)


def _discover_directory_atlas(
    *,
    room_size: int,
    atlas_directory: str | Path,
    source: str,
) -> AtlasResource:
    """Discover one continuous external atlas without policy decisions."""

    if room_size not in {1, 2, 3, 4}:
        raise ValueError(f"Unsupported ORMS room size: x{room_size}")
    directory = Path(atlas_directory).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(
            f"ORMS {source} atlas directory does not exist: {directory}"
        )

    asset_patterns = {
        _pattern_from_seed(path)
        for path in directory.iterdir()
        if path.is_file() and _UDIM_SEED_PATTERN.search(path.name)
    }
    if not asset_patterns:
        raise FileNotFoundError(
            f"No ORMS {source} atlas beginning with UDIM 1001 was found "
            f"in: {directory}"
        )
    if len(asset_patterns) > 1:
        names = ", ".join(sorted(path.name for path in asset_patterns))
        raise ValueError(
            f"An ORMS {source} family directory must contain exactly one "
            f"UDIM sequence; found: {names}"
        )

    asset_path = next(iter(asset_patterns))
    tiles = _udim_tiles(asset_path)
    expected_tiles = tuple(range(1001, 1001 + len(tiles)))
    if tiles != expected_tiles:
        raise FileNotFoundError(
            f"The ORMS {source} atlas must be continuous from UDIM 1001; "
            f"found: {', '.join(str(tile) for tile in tiles)}"
        )
    return AtlasResource(
        room_size=room_size,
        asset_path=asset_path,
        variant_count=len(tiles),
        source=source,
        variant_manifest=load_variant_manifest(directory, len(tiles)),
    )


def select_runtime_atlases(
    resources: ResourceLayout,
    setting_values: Mapping[str, object],
) -> tuple[AtlasResource, ...]:
    """Overlay configured production families on packaged debug fallbacks."""

    selected = {atlas.room_size: atlas for atlas in resources.debug_atlases}
    for room_size in (1, 2, 3, 4):
        directory_setting = PRODUCTION_DIRECTORY_SETTING.format(
            room_size=room_size
        )
        atlas_directory = str(
            setting_values.get(directory_setting, "") or ""
        ).strip()
        if not atlas_directory:
            continue
        selected[room_size] = discover_production_atlas(
            room_size=room_size,
            atlas_directory=atlas_directory,
        )
    return tuple(selected[size] for size in sorted(selected))


def _pattern_from_seed(seed_path: Path) -> Path:
    """Replace the unambiguous 1001 token in a seed filename with UDIM."""

    matches = tuple(_UDIM_SEED_PATTERN.finditer(seed_path.name))
    if len(matches) != 1:
        raise ValueError(
            "An ORMS atlas seed filename must contain one standalone 1001 "
            f"token: {seed_path.name}"
        )
    match = matches[0]
    pattern_name = (
        seed_path.name[: match.start()]
        + _UDIM_TOKEN
        + seed_path.name[match.end() :]
    )
    return seed_path.with_name(pattern_name)


def _udim_tiles(asset_path: Path) -> tuple[int, ...]:
    """Return sorted tiles matching one discovered asset pattern."""

    escaped_name = re.escape(asset_path.name)
    tile_pattern = re.compile(
        "^" + escaped_name.replace(re.escape(_UDIM_TOKEN), r"(\d{4})") + "$"
    )
    tiles = []
    for path in asset_path.parent.iterdir():
        if not path.is_file():
            continue
        match = tile_pattern.fullmatch(path.name)
        if match is not None:
            tiles.append(int(match.group(1)))
    return tuple(sorted(tiles))
