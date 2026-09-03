"""Persist complete Interior Set snapshots behind one active-slot pointer."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from tools.omniverse.interior_sets.atlas_mode import (
    ATLAS_MODE_DEBUG,
    ATLAS_MODE_PRODUCTION,
    normalise_atlas_mode,
)
from tools.omniverse.interior_sets.contracts import (
    INTERIOR_SET_SCHEMA_VERSION,
    ROOM_SIZES,
    InteriorSetCollection,
    InteriorSetConfig,
)

from .interior_set_storage import (
    ACTIVE_SLOT_PATH,
    INTERIOR_SET_SETTINGS_ROOT,
    SCHEMA_PATH,
    SLOTS,
    InteriorSetSnapshotStore,
    material_defaults,
    normalise_collection,
)
from .resources import PRODUCTION_DIRECTORY_SETTING

__all__ = (
    "INTERIOR_SET_SETTINGS_ROOT",
    "InteriorSetSettingsRepository",
)


@dataclass(frozen=True)
class InteriorSetCommit:
    """Record the pointer change required for runtime rollback."""

    previous_slot: str | None
    active_slot: str
    collection: InteriorSetCollection
    atlas_mode: str


@dataclass(frozen=True)
class MigrationResult:
    """Report whether legacy global values populated Default."""

    collection: InteriorSetCollection
    atlas_mode: str
    migrated: bool
    resumed_interrupted_migration: bool = False


def _legacy_material_path(name: str) -> str:
    return f"/persistent/exts/orms/material/{name}"


def _inferred_atlas_mode(collection: InteriorSetCollection) -> str:
    """Preserve legacy production use while defaulting new setups to debug."""

    has_production = any(
        directory.strip()
        for item in collection.sets
        for directory in item.atlas_directories
    )
    return ATLAS_MODE_PRODUCTION if has_production else ATLAS_MODE_DEBUG


class InteriorSetSettingsRepository:
    """Load and atomically switch two persistent configuration slots."""

    def __init__(self, settings: Any):
        self._settings = settings
        self._store = InteriorSetSnapshotStore(settings)

    @classmethod
    def from_kit(cls) -> "InteriorSetSettingsRepository":
        """Bind the repository to the process-wide Kit settings service."""

        import carb.settings

        return cls(carb.settings.get_settings())

    def ensure_migrated(self) -> MigrationResult:
        """Create Default from legacy globals exactly once."""

        version = self._settings.get(SCHEMA_PATH)
        if version not in {None, 1, INTERIOR_SET_SCHEMA_VERSION}:
            raise ValueError(
                "Unsupported Interior Set settings schema: " f"{version!r}"
            )
        active_slot = self._settings.get(ACTIVE_SLOT_PATH)
        if active_slot in SLOTS:
            collection = self._store.load(str(active_slot))
            resumed = version is None
            migrated = version == 1
            if version != INTERIOR_SET_SCHEMA_VERSION:
                atlas_mode = _inferred_atlas_mode(collection)
                self._store.set_atlas_mode(str(active_slot), atlas_mode)
                self._settings.set(
                    SCHEMA_PATH,
                    INTERIOR_SET_SCHEMA_VERSION,
                )
            else:
                atlas_mode = self._store.load_atlas_mode(str(active_slot))
            return MigrationResult(
                collection=collection,
                atlas_mode=atlas_mode,
                migrated=migrated,
                resumed_interrupted_migration=resumed,
            )
        if version == INTERIOR_SET_SCHEMA_VERSION:
            raise ValueError(
                "Interior Set schema exists without an active snapshot"
            )

        material_values = []
        for name, default in material_defaults().items():
            legacy_value = self._settings.get(_legacy_material_path(name))
            material_values.append(
                (name, default if legacy_value is None else legacy_value)
            )
        atlas_directories = tuple(
            str(
                self._settings.get(
                    PRODUCTION_DIRECTORY_SETTING.format(room_size=size)
                )
                or ""
            )
            for size in ROOM_SIZES
        )
        collection = InteriorSetCollection(
            (
                InteriorSetConfig(
                    set_id=(
                        InteriorSetCollection.default_only().default.set_id
                    ),
                    atlas_directories=atlas_directories,
                    material_values=tuple(material_values),
                ),
            )
        )
        atlas_mode = _inferred_atlas_mode(collection)
        commit = self.commit(collection, atlas_mode)
        self._settings.set(SCHEMA_PATH, INTERIOR_SET_SCHEMA_VERSION)
        return MigrationResult(
            commit.collection,
            commit.atlas_mode,
            migrated=True,
        )

    def load(self) -> InteriorSetCollection:
        """Load the last complete applied snapshot."""

        version = self._settings.get(SCHEMA_PATH)
        if version != INTERIOR_SET_SCHEMA_VERSION:
            return self.ensure_migrated().collection
        active_slot = self._settings.get(ACTIVE_SLOT_PATH)
        if active_slot not in SLOTS:
            raise ValueError("Interior Set settings have no active snapshot")
        return self._store.load(str(active_slot))

    def load_atlas_mode(self) -> str:
        """Load the global applied atlas mode from the active snapshot."""

        version = self._settings.get(SCHEMA_PATH)
        if version != INTERIOR_SET_SCHEMA_VERSION:
            return self.ensure_migrated().atlas_mode
        active_slot = self._settings.get(ACTIVE_SLOT_PATH)
        if active_slot not in SLOTS:
            raise ValueError("Interior Set settings have no active snapshot")
        return self._store.load_atlas_mode(str(active_slot))

    def commit(
        self,
        candidate: InteriorSetCollection,
        atlas_mode: str | None = None,
    ) -> InteriorSetCommit:
        """Write one inactive snapshot before changing the active pointer."""

        collection = normalise_collection(candidate)
        previous = self._settings.get(ACTIVE_SLOT_PATH)
        previous_slot = str(previous) if previous in SLOTS else None
        if atlas_mode is None:
            atlas_mode = (
                self._store.load_atlas_mode(previous_slot)
                if previous_slot is not None
                and self._settings.get(SCHEMA_PATH)
                == INTERIOR_SET_SCHEMA_VERSION
                else _inferred_atlas_mode(collection)
            )
        mode = normalise_atlas_mode(atlas_mode)
        active_slot = "b" if previous_slot == "a" else "a"
        self._store.write(active_slot, collection, mode)
        self._settings.set(ACTIVE_SLOT_PATH, active_slot)
        return InteriorSetCommit(
            previous_slot=previous_slot,
            active_slot=active_slot,
            collection=collection,
            atlas_mode=mode,
        )

    def rollback(self, commit: InteriorSetCommit) -> None:
        """Restore the preceding pointer after a failed runtime rebuild."""

        current = self._settings.get(ACTIVE_SLOT_PATH)
        if current != commit.active_slot:
            raise RuntimeError(
                "Cannot roll back a superseded Interior Set commit"
            )
        if commit.previous_slot is None:
            raise RuntimeError(
                "The initial Interior Set migration has no prior snapshot"
            )
        self._settings.set(ACTIVE_SLOT_PATH, commit.previous_slot)

    def rename(self, set_id: str, name: str) -> InteriorSetCollection:
        """Persist live presentation data without changing runtime identity."""

        collection = self.load()
        updated = collection.by_id(set_id).renamed(name)
        active_slot = str(self._settings.get(ACTIVE_SLOT_PATH))
        self._store.set_name(active_slot, set_id, name)
        return collection.replace(updated)

    def update_material(
        self,
        set_id: str,
        name: str,
        value: object,
    ) -> InteriorSetCollection:
        """Persist one live material value in the applied Set only."""

        return self.update_materials(set_id, {name: value})

    def update_materials(
        self,
        set_id: str,
        values: Mapping[str, object],
    ) -> InteriorSetCollection:
        """Persist several live values through one applied snapshot load."""

        defaults = material_defaults()
        unknown = tuple(name for name in values if name not in defaults)
        if unknown:
            raise KeyError(f"Unknown ORMS material controls: {unknown}")
        collection = self.load()
        item = collection.by_id(set_id)
        material_values = item.material_mapping()
        material_values.update(values)
        updated = replace(
            item,
            material_values=tuple(material_values.items()),
        )
        active_slot = str(self._settings.get(ACTIVE_SLOT_PATH))
        for name, value in values.items():
            self._store.set_material(active_slot, set_id, name, value)
        return collection.replace(updated)
