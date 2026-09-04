"""Define Kit-independent Interior Set configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .atlas_mode import ATLAS_MODE_DEBUG, normalise_atlas_mode
from .identity import (
    DEFAULT_INTERIOR_SET_ID,
    INTERIOR_SET_SCHEMA_VERSION,
    ROOM_SIZES,
    canonical_set_id,
    new_set_id,
    runtime_set_token,
)
from .manifest import (
    VARIANT_MANIFEST_VERSION,
    VariantIdentityManifest,
    semantic_variant_id,
    semantic_variant_index,
)

__all__ = (
    "DEFAULT_INTERIOR_SET_ID",
    "INTERIOR_SET_SCHEMA_VERSION",
    "ROOM_SIZES",
    "VARIANT_MANIFEST_VERSION",
    "InteriorSetCollection",
    "InteriorSetConfig",
    "InteriorSetTransaction",
    "VariantIdentityManifest",
    "runtime_set_token",
    "semantic_variant_id",
    "semantic_variant_index",
)


@dataclass(frozen=True)
class InteriorSetConfig:
    """Hold one immutable-identity artist configuration."""

    set_id: str
    name: str = ""
    selectors: tuple[str, ...] = ()
    atlas_directories: tuple[str, str, str, str] = ("", "", "", "")
    material_values: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        canonical_set_id(self.set_id)
        if len(self.atlas_directories) != len(ROOM_SIZES):
            raise ValueError("Interior Sets require x1-x4 atlas directories")
        material_names = tuple(name for name, _value in self.material_values)
        if len(set(material_names)) != len(material_names):
            raise ValueError("Interior Set material names must be unique")

    @property
    def is_default(self) -> bool:
        """Return whether this is the reserved fallback Set."""

        return self.set_id == DEFAULT_INTERIOR_SET_ID

    def atlas_directory(self, room_size: int) -> str:
        """Return the configured production directory for one family."""

        if room_size not in ROOM_SIZES:
            raise ValueError(f"Unsupported ORMS room size: x{room_size}")
        return self.atlas_directories[room_size - 1]

    def material_mapping(self) -> dict[str, object]:
        """Return an editable copy of the stored material profile."""

        return dict(self.material_values)

    def renamed(self, name: str) -> "InteriorSetConfig":
        """Change presentation without replacing the stable identity."""

        return replace(self, name=str(name))


@dataclass(frozen=True)
class InteriorSetCollection:
    """Hold Default first and specific Sets in selector-priority order."""

    sets: tuple[InteriorSetConfig, ...]

    def __post_init__(self) -> None:
        if not self.sets:
            raise ValueError("At least one Interior Set is required")
        identifiers = tuple(item.set_id for item in self.sets)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Interior Set identities must be unique")
        if identifiers.count(DEFAULT_INTERIOR_SET_ID) != 1:
            raise ValueError("Exactly one Default Interior Set is required")
        if identifiers[0] != DEFAULT_INTERIOR_SET_ID:
            raise ValueError("The Default Interior Set must remain first")

    @classmethod
    def default_only(
        cls,
        material_values: tuple[tuple[str, object], ...] = (),
    ) -> "InteriorSetCollection":
        """Create the stable fallback configuration used by migration."""

        return cls(
            (
                InteriorSetConfig(
                    set_id=DEFAULT_INTERIOR_SET_ID,
                    material_values=material_values,
                ),
            )
        )

    @property
    def default(self) -> InteriorSetConfig:
        """Return the mandatory fallback Set."""

        return self.sets[0]

    @property
    def specific(self) -> tuple[InteriorSetConfig, ...]:
        """Return specific Sets in deterministic selector priority."""

        return self.sets[1:]

    def by_id(self, set_id: str) -> InteriorSetConfig:
        """Return one Set without accepting display names as identity."""

        canonical = canonical_set_id(set_id)
        for item in self.sets:
            if item.set_id == canonical:
                return item
        raise KeyError(f"Unknown Interior Set: {set_id}")

    def label_for(self, set_id: str) -> str:
        """Return the display name or its order-derived fallback label."""

        item = self.by_id(set_id)
        if item.name.strip():
            return item.name.strip()
        return f"ORMS {self.sets.index(item) + 1}"

    def add(
        self,
        *,
        set_id: str | None = None,
    ) -> "InteriorSetCollection":
        """Append a blank structural Set inheriting Default materials."""

        created = InteriorSetConfig(
            set_id=set_id or new_set_id(),
            material_values=self.default.material_values,
        )
        return InteriorSetCollection((*self.sets, created))

    def duplicate(
        self,
        source_id: str,
        *,
        set_id: str | None = None,
    ) -> "InteriorSetCollection":
        """Copy editable configuration directly after its source."""

        source = self.by_id(source_id)
        duplicate = replace(source, set_id=set_id or new_set_id())
        source_index = self.sets.index(source)
        copied = (
            self.sets[: source_index + 1]
            + (duplicate,)
            + self.sets[source_index + 1 :]
        )
        return InteriorSetCollection(copied)

    def replace(self, updated: InteriorSetConfig) -> "InteriorSetCollection":
        """Replace editable values while retaining collection order."""

        current = self.by_id(updated.set_id)
        index = self.sets.index(current)
        values = self.sets[:index] + (updated,) + self.sets[index + 1 :]
        return InteriorSetCollection(values)

    def remove(self, set_id: str) -> "InteriorSetCollection":
        """Remove one specific Set and reject removal of Default."""

        item = self.by_id(set_id)
        if item.is_default:
            raise ValueError("The Default Interior Set cannot be removed")
        return InteriorSetCollection(
            tuple(candidate for candidate in self.sets if candidate != item)
        )

    def move(self, set_id: str, offset: int) -> "InteriorSetCollection":
        """Move one specific Set by one priority position."""

        if offset not in {-1, 1}:
            raise ValueError("Interior Sets move by one position at a time")
        item = self.by_id(set_id)
        if item.is_default:
            raise ValueError("The Default Interior Set cannot be reordered")
        source_index = self.sets.index(item)
        target_index = min(
            max(source_index + offset, 1),
            len(self.sets) - 1,
        )
        if source_index == target_index:
            return self
        reordered = list(self.sets)
        reordered.insert(target_index, reordered.pop(source_index))
        return InteriorSetCollection(tuple(reordered))


@dataclass
class InteriorSetTransaction:
    """Separate mutable UI intent from the last applied configuration."""

    applied: InteriorSetCollection
    draft: InteriorSetCollection
    applied_revision: int = 0
    draft_revision: int = 0
    applied_atlas_mode: str = ATLAS_MODE_DEBUG
    draft_atlas_mode: str = ATLAS_MODE_DEBUG
    applied_debug_atlas_directories: tuple[str, str, str, str] = (
        "",
        "",
        "",
        "",
    )
    draft_debug_atlas_directories: tuple[str, str, str, str] = (
        "",
        "",
        "",
        "",
    )

    @classmethod
    def from_applied(
        cls,
        applied: InteriorSetCollection,
        atlas_mode: str = ATLAS_MODE_DEBUG,
        debug_atlas_directories: tuple[str, str, str, str] = (
            "",
            "",
            "",
            "",
        ),
    ) -> "InteriorSetTransaction":
        """Begin with an unchanged local draft."""

        mode = normalise_atlas_mode(atlas_mode)
        return cls(
            applied=applied,
            draft=applied,
            applied_atlas_mode=mode,
            draft_atlas_mode=mode,
            applied_debug_atlas_directories=debug_atlas_directories,
            draft_debug_atlas_directories=debug_atlas_directories,
        )

    @property
    def dirty(self) -> bool:
        """Return whether structural edits remain unapplied."""

        return (
            self.draft != self.applied
            or self.draft_atlas_mode != self.applied_atlas_mode
            or self.draft_debug_atlas_directories
            != self.applied_debug_atlas_directories
        )

    def stage(self, candidate: InteriorSetCollection) -> None:
        """Replace only the local candidate configuration."""

        if candidate == self.draft:
            return
        self.draft = candidate
        self.draft_revision += 1

    def stage_atlas_mode(self, atlas_mode: str) -> None:
        """Replace only the local global resource-selection policy."""

        mode = normalise_atlas_mode(atlas_mode)
        if mode == self.draft_atlas_mode:
            return
        self.draft_atlas_mode = mode
        self.draft_revision += 1

    def stage_debug_atlas_directories(
        self,
        directories: tuple[str, str, str, str],
    ) -> None:
        """Replace only the staged global debug-family overrides."""

        if len(directories) != len(ROOM_SIZES):
            raise ValueError("Debug atlas overrides require x1-x4 directories")
        if directories == self.draft_debug_atlas_directories:
            return
        self.draft_debug_atlas_directories = directories
        self.draft_revision += 1

    def stage_snapshot(
        self,
        candidate: InteriorSetCollection,
        atlas_mode: str,
        debug_atlas_directories: tuple[str, str, str, str] | None = None,
    ) -> None:
        """Stage one complete profile as a single structural revision."""

        mode = normalise_atlas_mode(atlas_mode)
        directories = (
            self.draft_debug_atlas_directories
            if debug_atlas_directories is None
            else debug_atlas_directories
        )
        if len(directories) != len(ROOM_SIZES):
            raise ValueError("Debug atlas overrides require x1-x4 directories")
        if (
            candidate == self.draft
            and mode == self.draft_atlas_mode
            and directories == self.draft_debug_atlas_directories
        ):
            return
        self.draft = candidate
        self.draft_atlas_mode = mode
        self.draft_debug_atlas_directories = directories
        self.draft_revision += 1

    def accept(self) -> InteriorSetCollection:
        """Promote the complete validated draft after a successful Apply."""

        self.applied = self.draft
        self.applied_atlas_mode = self.draft_atlas_mode
        self.applied_debug_atlas_directories = (
            self.draft_debug_atlas_directories
        )
        self.applied_revision = self.draft_revision
        return self.applied

    def revert(self) -> InteriorSetCollection:
        """Discard local structural edits without touching runtime state."""

        self.draft = self.applied
        self.draft_atlas_mode = self.applied_atlas_mode
        self.draft_debug_atlas_directories = (
            self.applied_debug_atlas_directories
        )
        self.draft_revision = self.applied_revision
        return self.draft
