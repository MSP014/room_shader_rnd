"""Resolve portable MDL and atlas resources without hard-coded install paths."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

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
    1: "room_map_debug",
    2: "room_map_debug_x2",
    3: "room_map_debug_x3",
    4: "room_map_debug_x4",
}


@dataclass(frozen=True)
class AtlasResource:
    """Describe one complete UDIM family and its valid variant count."""

    room_size: int
    asset_path: Path
    variant_count: int
    source: str


@dataclass(frozen=True)
class ResourceLayout:
    """Resolve packaged resources first and checkout resources for development."""

    extension_root: Path
    mdl_root: Path
    runtime_root: Path
    debug_atlases: tuple[AtlasResource, ...]

    @classmethod
    def discover(cls, module_file: str | Path) -> "ResourceLayout":
        """Find resources relative to the installed extension or source checkout."""

        extension_root = Path(module_file).resolve().parents[3]
        checkout_root = extension_root.parents[1]
        packaged_runtime_root = extension_root / "data" / "runtime"
        runtime_root = (
            packaged_runtime_root
            if (packaged_runtime_root / "tools" / "omniverse").is_dir()
            else checkout_root
        )
        if not (runtime_root / "tools" / "omniverse").is_dir():
            raise FileNotFoundError(
                "The ORMS extension has no packaged Python runtime"
            )

        packaged_mdl_root = extension_root / "data" / "mdl"
        checkout_mdl_root = checkout_root / "src" / "mdl"
        mdl_root = (
            packaged_mdl_root
            if _contains_runtime_mdl(packaged_mdl_root)
            else checkout_mdl_root
        )
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
                / "debug"
                / f"x{room_size}"
                / f"{family_name}.<UDIM>.png"
            )
            checkout_asset = (
                checkout_root
                / "assets"
                / "_external"
                / "tex"
                / family_name
                / f"{family_name}.<UDIM>.png"
            )
            asset_path = (
                packaged_asset
                if _is_complete_udim_family(packaged_asset)
                else checkout_asset
            )
            if _is_complete_udim_family(asset_path):
                debug_atlases.append(
                    AtlasResource(
                        room_size,
                        asset_path,
                        DEBUG_VARIANT_COUNT,
                        (
                            "packaged"
                            if asset_path == packaged_asset
                            else "checkout"
                        ),
                    )
                )

        return cls(
            extension_root=extension_root,
            mdl_root=mdl_root,
            runtime_root=runtime_root,
            debug_atlases=tuple(debug_atlases),
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


def _contains_runtime_mdl(directory: Path) -> bool:
    return all(
        (directory / filename).is_file()
        for filename in ("room_map.mdl", "room_map_single.mdl")
    )


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

    if room_size not in {1, 2, 3, 4}:
        raise ValueError(f"Unsupported ORMS room size: x{room_size}")
    directory = Path(atlas_directory).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(
            f"ORMS production atlas directory does not exist: {directory}"
        )

    asset_patterns = {
        _pattern_from_seed(path)
        for path in directory.iterdir()
        if path.is_file() and _UDIM_SEED_PATTERN.search(path.name)
    }
    if not asset_patterns:
        raise FileNotFoundError(
            "No ORMS production atlas beginning with UDIM 1001 was found "
            f"in: {directory}"
        )
    if len(asset_patterns) > 1:
        names = ", ".join(sorted(path.name for path in asset_patterns))
        raise ValueError(
            "An ORMS production family directory must contain exactly one "
            f"UDIM sequence; found: {names}"
        )

    asset_path = next(iter(asset_patterns))
    tiles = _udim_tiles(asset_path)
    expected_tiles = tuple(range(1001, 1001 + len(tiles)))
    if tiles != expected_tiles:
        raise FileNotFoundError(
            "The ORMS production atlas must be continuous from UDIM 1001; "
            f"found: {', '.join(str(tile) for tile in tiles)}"
        )
    return AtlasResource(
        room_size=room_size,
        asset_path=asset_path,
        variant_count=len(tiles),
        source="production",
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
