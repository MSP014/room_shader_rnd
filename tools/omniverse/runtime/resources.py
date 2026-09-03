"""Describe the MDL and atlas resources consumed by the ORMS classifier."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_DEBUG_VARIANT_COUNT = 8
ROOM_MAP_MDL_FILENAME = "room_map.mdl"
ROOM_MAP_SINGLE_MDL_FILENAME = "room_map_single.mdl"
_DEBUG_FAMILY_NAMES = {
    1: "room_map_debug",
    2: "room_map_debug_x2",
    3: "room_map_debug_x3",
    4: "room_map_debug_x4",
}


@dataclass(frozen=True)
class RuntimeAtlasFamily:
    """Pair one x1-x4 family with its UDIM asset and valid variants."""

    room_size: int
    asset_path: str
    variant_count: int
    source: str = "runtime"

    def __post_init__(self) -> None:
        if self.room_size not in {1, 2, 3, 4}:
            raise ValueError(f"Unsupported ORMS room size: x{self.room_size}")
        if not self.asset_path:
            raise ValueError("An ORMS atlas asset path cannot be empty")
        if self.variant_count < 1:
            raise ValueError("An ORMS atlas variant count must be positive")


@dataclass(frozen=True)
class RuntimeResources:
    """Keep runtime material and texture lookup independent from installation."""

    mdl_source_asset: str
    atlas_families: tuple[RuntimeAtlasFamily, ...]

    def __post_init__(self) -> None:
        if not self.mdl_source_asset:
            raise ValueError("The ORMS MDL source asset cannot be empty")
        room_sizes = tuple(family.room_size for family in self.atlas_families)
        if len(room_sizes) != len(set(room_sizes)):
            raise ValueError("Each ORMS atlas room size must be unique")

    @property
    def available_room_sizes(self) -> frozenset[int]:
        """Return atlas families that have passed resource validation."""

        return frozenset(family.room_size for family in self.atlas_families)

    def atlas_family(self, room_size: int) -> RuntimeAtlasFamily:
        """Return one validated family or fail with an actionable message."""

        family = next(
            (
                candidate
                for candidate in self.atlas_families
                if candidate.room_size == room_size
            ),
            None,
        )
        if family is None:
            raise KeyError(
                f"No ORMS atlas resource is available for x{room_size}"
            )
        return family

    @classmethod
    def from_repository(
        cls, repository_root: str | Path
    ) -> "RuntimeResources":
        """Adapt the retained checkout layout to the portable resource contract."""

        root = Path(repository_root).resolve()
        texture_root = root / "assets" / "_external" / "tex"
        families = []
        for room_size, family_name in _DEBUG_FAMILY_NAMES.items():
            asset_path = (
                texture_root / family_name / f"{family_name}.<UDIM>.png"
            )
            if _is_complete_udim_family(asset_path):
                families.append(
                    RuntimeAtlasFamily(
                        room_size=room_size,
                        asset_path=asset_path.as_posix(),
                        variant_count=_DEBUG_VARIANT_COUNT,
                    )
                )
        return cls(
            mdl_source_asset=(
                root / "src" / "mdl" / "room_map.mdl"
            ).as_posix(),
            atlas_families=tuple(families),
        )


def coerce_runtime_resources(
    value: RuntimeResources | str | Path | object,
) -> RuntimeResources:
    """Adapt paths and resource records that survived an exact-source reload."""

    if isinstance(value, RuntimeResources):
        return value
    mdl_source_asset = getattr(value, "mdl_source_asset", None)
    atlas_families = getattr(value, "atlas_families", None)
    if mdl_source_asset is not None and atlas_families is not None:
        return RuntimeResources(
            mdl_source_asset=str(mdl_source_asset),
            atlas_families=tuple(
                RuntimeAtlasFamily(
                    room_size=int(family.room_size),
                    asset_path=str(family.asset_path),
                    variant_count=int(family.variant_count),
                    source=str(getattr(family, "source", "runtime")),
                )
                for family in atlas_families
            ),
        )
    return RuntimeResources.from_repository(value)  # type: ignore[arg-type]


def mdl_source_asset_name(value: object) -> str:
    """Return a normalised filename from relative or absolute MDL asset paths."""

    return str(value or "").replace("\\", "/").rsplit("/", 1)[-1].lower()


def is_room_map_source_asset(value: object) -> bool:
    """Recognise both ORMS materials independently from their install root."""

    return mdl_source_asset_name(value) in {
        ROOM_MAP_MDL_FILENAME,
        ROOM_MAP_SINGLE_MDL_FILENAME,
    }


def _is_complete_udim_family(asset_path: Path) -> bool:
    asset_name = asset_path.name
    if "<UDIM>" not in asset_name:
        return False
    return all(
        asset_path.with_name(asset_name.replace("<UDIM>", str(tile))).is_file()
        for tile in range(1001, 1009)
    )
