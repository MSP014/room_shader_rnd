# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Author Set-scoped material families without owning classification."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from pxr import Sdf, Usd, UsdShade

from ..classification.contracts import DerivedApertureMapping
from ..interior_sets.contracts import (
    DEFAULT_INTERIOR_SET_ID,
    InteriorSetCollection,
)
from ..interior_sets.runtime_resources import InteriorSetRuntimeSnapshot
from .authoring import author_family_materials
from .material_controls import material_input_values_from_mapping

MaterialKey = tuple[str, int]


def author_interior_set_materials(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    collection: InteriorSetCollection,
    runtime_resources: InteriorSetRuntimeSnapshot,
    window_paths_by_set: Mapping[str, tuple[str, ...]],
    legacy_default_values: Mapping[str, object] | None = None,
) -> dict[MaterialKey, UsdShade.Material]:
    """Author only active `(set_id, room_size)` material families."""

    materials: dict[MaterialKey, UsdShade.Material] = {}
    for item in collection.sets:
        window_paths = window_paths_by_set.get(item.set_id, ())
        if not window_paths:
            continue
        selected = runtime_resources.by_id(item.set_id)
        stored_values = item.material_mapping()
        values = (
            material_input_values_from_mapping(stored_values)
            if stored_values
            else {}
        )
        if item.set_id == DEFAULT_INTERIOR_SET_ID and legacy_default_values:
            values.update(legacy_default_values)
        authored = author_family_materials(
            stage,
            runtime_layer,
            selected.resources,
            selected.resources.available_room_sizes,
            window_paths,
            values,
            interior_set_id=item.set_id,
            display_name=collection.label_for(item.set_id),
        )
        materials.update(
            {
                (item.set_id, room_size): material
                for room_size, material in authored.items()
            }
        )
    return materials


def window_paths_by_set(
    mappings: Sequence[DerivedApertureMapping],
) -> dict[str, tuple[str, ...]]:
    """Collect selected composed mesh paths for material seed discovery."""

    paths: dict[str, set[str]] = defaultdict(set)
    for mapping in mappings:
        paths[str(mapping.interior_set_id)].add(str(mapping.prim_path))
    return {
        set_id: tuple(sorted(prim_paths))
        for set_id, prim_paths in paths.items()
    }
