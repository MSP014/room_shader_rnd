"""Serialise Interior Set snapshots into two persistent settings slots."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from msp.orms.interior_sets.atlas_mode import normalise_atlas_mode
from msp.orms.interior_sets.contracts import (
    ROOM_SIZES,
    InteriorSetCollection,
    InteriorSetConfig,
)
from msp.orms.interior_sets.selectors import validate_selector
from msp.orms.shared_room.material_controls import MATERIAL_CONTROLS

INTERIOR_SET_SETTINGS_ROOT = "/persistent/exts/msp.orms.runtime/interior_sets"
SCHEMA_PATH = f"{INTERIOR_SET_SETTINGS_ROOT}/schema_version"
ACTIVE_SLOT_PATH = f"{INTERIOR_SET_SETTINGS_ROOT}/active_slot"
SLOTS = ("a", "b")


def material_defaults() -> dict[str, object]:
    """Return one independent copy of the complete material profile."""

    return {control.name: control.default for control in MATERIAL_CONTROLS}


def normalise_collection(
    collection: InteriorSetCollection,
) -> InteriorSetCollection:
    """Validate one complete candidate before persistent mutation."""

    defaults = material_defaults()
    normalised_sets = []
    for item in collection.sets:
        selectors = []
        for mask in item.selectors:
            normalised = validate_selector(mask)
            if normalised and normalised not in selectors:
                selectors.append(normalised)
        material_values = defaults.copy()
        material_values.update(item.material_mapping())
        normalised_sets.append(
            replace(
                item,
                selectors=tuple(selectors),
                atlas_directories=tuple(
                    str(path).strip() for path in item.atlas_directories
                ),
                material_values=tuple(material_values.items()),
            )
        )
    return InteriorSetCollection(tuple(normalised_sets))


def slot_root(slot: str) -> str:
    """Return one validated inactive or active snapshot path."""

    if slot not in SLOTS:
        raise ValueError(f"Invalid Interior Set settings slot: {slot!r}")
    return f"{INTERIOR_SET_SETTINGS_ROOT}/slots/{slot}"


def set_root(slot: str, set_id: str) -> str:
    """Return the stable persistent subtree for one Set in one slot."""

    return f"{slot_root(slot)}/sets/{set_id}"


class InteriorSetSnapshotStore:
    """Read and write complete snapshots without switching ownership."""

    def __init__(self, settings: Any):
        self.settings = settings

    def write(
        self,
        slot: str,
        collection: InteriorSetCollection,
        atlas_mode: str,
        debug_atlas_directories: tuple[str, str, str, str] = (
            "",
            "",
            "",
            "",
        ),
    ) -> None:
        """Replace one inactive slot with a complete candidate snapshot."""

        root = slot_root(slot)
        destroy_item = getattr(self.settings, "destroy_item", None)
        if callable(destroy_item):
            destroy_item(root)
        self.settings.set(
            f"{root}/order",
            json.dumps([item.set_id for item in collection.sets]),
        )
        self.settings.set(
            f"{root}/atlas_mode",
            normalise_atlas_mode(atlas_mode),
        )
        if len(debug_atlas_directories) != len(ROOM_SIZES):
            raise ValueError("Debug atlas overrides require x1-x4 directories")
        for room_size, directory in zip(
            ROOM_SIZES,
            debug_atlas_directories,
            strict=True,
        ):
            self.settings.set(
                f"{root}/debug_atlases/x{room_size}/directory",
                str(directory).strip(),
            )
        for item in collection.sets:
            item_root = set_root(slot, item.set_id)
            self.settings.set(f"{item_root}/name", item.name)
            self.settings.set(
                f"{item_root}/selectors",
                json.dumps(item.selectors),
            )
            for room_size in ROOM_SIZES:
                self.settings.set(
                    f"{item_root}/atlases/x{room_size}/directory",
                    item.atlas_directory(room_size),
                )
            for name, value in item.material_values:
                self.set_typed(
                    f"{item_root}/material/{name}",
                    value,
                )

    def load(self, slot: str) -> InteriorSetCollection:
        """Rebuild one immutable collection from an indicated slot."""

        root = slot_root(slot)
        raw_order = self.settings.get(f"{root}/order")
        try:
            order = tuple(json.loads(str(raw_order)))
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Interior Set snapshot has malformed priority order"
            ) from error
        defaults = material_defaults()
        loaded = tuple(
            self._load_set(slot, str(set_id), defaults) for set_id in order
        )
        return normalise_collection(InteriorSetCollection(loaded))

    def load_atlas_mode(self, slot: str) -> str:
        """Load the global resource policy from one complete snapshot."""

        return normalise_atlas_mode(
            self.settings.get(f"{slot_root(slot)}/atlas_mode")
        )

    def load_debug_atlas_directories(
        self,
        slot: str,
    ) -> tuple[str, str, str, str]:
        """Load optional global debug overrides from one snapshot."""

        root = slot_root(slot)
        return tuple(
            str(
                self.settings.get(
                    f"{root}/debug_atlases/x{room_size}/directory"
                )
                or ""
            ).strip()
            for room_size in ROOM_SIZES
        )

    def set_atlas_mode(self, slot: str, atlas_mode: str) -> None:
        """Complete legacy snapshot migration before advancing its schema."""

        self.settings.set(
            f"{slot_root(slot)}/atlas_mode",
            normalise_atlas_mode(atlas_mode),
        )

    def _load_set(
        self,
        slot: str,
        set_id: str,
        defaults: dict[str, object],
    ) -> InteriorSetConfig:
        item_root = set_root(slot, set_id)
        raw_selectors = self.settings.get(f"{item_root}/selectors")
        try:
            selectors = tuple(json.loads(str(raw_selectors or "[]")))
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Interior Set {set_id} has malformed selectors"
            ) from error
        material_values = []
        for name, default in defaults.items():
            value = self.settings.get(f"{item_root}/material/{name}")
            if value is not None and isinstance(default, tuple):
                value = tuple(value)
            material_values.append((name, default if value is None else value))
        return InteriorSetConfig(
            set_id=set_id,
            name=str(self.settings.get(f"{item_root}/name") or ""),
            selectors=selectors,
            atlas_directories=tuple(
                str(
                    self.settings.get(f"{item_root}/atlases/x{size}/directory")
                    or ""
                )
                for size in ROOM_SIZES
            ),
            material_values=tuple(material_values),
        )

    def set_name(self, slot: str, set_id: str, name: str) -> None:
        """Update live presentation data in the active snapshot."""

        self.settings.set(f"{set_root(slot, set_id)}/name", name)

    def set_material(
        self,
        slot: str,
        set_id: str,
        name: str,
        value: object,
    ) -> None:
        """Update one live material value in the active snapshot."""

        self.set_typed(
            f"{set_root(slot, set_id)}/material/{name}",
            value,
        )

    def set_typed(self, path: str, value: object) -> None:
        """Preserve vector settings as typed floating-point arrays."""

        if isinstance(value, (tuple, list)):
            self.settings.set_float_array(
                path,
                [float(component) for component in value],
            )
            return
        self.settings.set(path, value)
