# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Summarise Interior Set assignment, grouping, and runtime resources."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..classification.contracts import ClassificationResult
from ..interior_sets.contracts import InteriorSetCollection
from ..interior_sets.runtime_resources import InteriorSetRuntimeSnapshot
from ..interior_sets.selectors import SelectorResolution
from .contracts import StageExtraction


@dataclass(frozen=True)
class SelectorConflict:
    """Describe one composed path matched by several specific Sets."""

    prim_path: str
    winning_set_id: str
    matching_set_ids: tuple[str, ...]


@dataclass(frozen=True)
class InteriorSetDiagnostics:
    """Expose stable counters and decisions from one runtime pass."""

    active_set_count: int
    aperture_counts: tuple[tuple[str, int], ...]
    room_size_counts: tuple[tuple[str, int, int], ...]
    selector_match_counts: tuple[tuple[str, str, int], ...]
    default_fallback_paths: tuple[str, ...]
    conflicts: tuple[SelectorConflict, ...]
    atlas_families: tuple[tuple[str, int, str, str, int], ...]
    coherence: tuple[tuple[str, bool, str | None], ...]
    variant_identities: tuple[
        tuple[str, str | None, tuple[str, ...]], ...
    ] = ()
    generated_material_paths: tuple[str, ...] = ()


def build_interior_set_diagnostics(
    collection: InteriorSetCollection,
    extraction: StageExtraction,
    result: ClassificationResult,
    resolutions: tuple[SelectorResolution, ...],
    resources: InteriorSetRuntimeSnapshot,
) -> InteriorSetDiagnostics:
    """Build one deterministic inspection snapshot without authoring USD."""

    aperture_counts = Counter(
        aperture.interior_set_id for aperture in extraction.apertures
    )
    room_counts = Counter(
        (group.interior_set_id, group.room_size) for group in result.groups
    )
    selector_counts = Counter(
        (resolution.set_id, resolution.winning_mask)
        for resolution in resolutions
        if resolution.winning_mask is not None
    )
    conflicts = tuple(
        SelectorConflict(
            prim_path=resolution.prim_path,
            winning_set_id=resolution.set_id,
            matching_set_ids=tuple(
                match.set_id for match in resolution.specific_matches
            ),
        )
        for resolution in resolutions
        if resolution.has_conflict
    )
    atlas_families = tuple(
        (
            item.set_id,
            family.room_size,
            family.source,
            family.asset_path,
            family.variant_count,
        )
        for item in resources.sets
        for family in item.resources.atlas_families
    )
    return InteriorSetDiagnostics(
        active_set_count=len(collection.sets),
        aperture_counts=tuple(sorted(aperture_counts.items())),
        room_size_counts=tuple(
            (set_id, room_size, count)
            for (set_id, room_size), count in sorted(room_counts.items())
        ),
        selector_match_counts=tuple(
            (set_id, str(mask), count)
            for (set_id, mask), count in sorted(selector_counts.items())
        ),
        default_fallback_paths=tuple(
            item.prim_path for item in resolutions if item.used_default
        ),
        conflicts=conflicts,
        atlas_families=atlas_families,
        coherence=tuple(
            (
                item.set_id,
                item.variant_coherent,
                item.coherence_error,
            )
            for item in resources.sets
        ),
        variant_identities=tuple(
            (
                item.set_id,
                item.variant_namespace,
                item.variant_ids,
            )
            for item in resources.sets
        ),
    )
