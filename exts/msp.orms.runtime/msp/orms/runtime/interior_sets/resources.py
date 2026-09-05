# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Resolve production and debug atlas families independently per Set."""

from __future__ import annotations

from dataclasses import dataclass

from msp.orms.interior_sets.atlas_mode import (
    ATLAS_MODE_DEBUG,
    ATLAS_MODE_PRODUCTION,
    normalise_atlas_mode,
)
from msp.orms.interior_sets.contracts import (
    ROOM_SIZES,
    InteriorSetCollection,
)
from msp.orms.interior_sets.runtime_resources import (
    InteriorSetRuntimeResources,
    InteriorSetRuntimeSnapshot,
)
from msp.orms.scene.resources import (
    RuntimeAtlasFamily,
    RuntimeResources,
)

from ..materials.atlas_manifest import (
    ManifestCoherence,
    validate_manifest_coherence,
)
from ..resources import (
    AtlasResource,
    DebugAtlasDecision,
    ResourceLayout,
    discover_production_atlas,
    resolve_debug_atlases,
)


@dataclass(frozen=True)
class ResolvedAtlasFamily:
    """Describe one Set-local family selection and fallback reason."""

    set_id: str
    room_size: int
    configured_directory: str
    atlas: AtlasResource | None
    fallback_reason: str | None = None
    validation_error: str | None = None


@dataclass(frozen=True)
class InteriorSetResourceSnapshot:
    """Hold all resource decisions for one applied Interior Set."""

    set_id: str
    families: tuple[ResolvedAtlasFamily, ...]
    coherence: ManifestCoherence

    @property
    def available_room_sizes(self) -> frozenset[int]:
        """Return family sizes that resolved to a usable atlas."""

        return frozenset(
            family.room_size
            for family in self.families
            if family.atlas is not None
        )

    def family(self, room_size: int) -> ResolvedAtlasFamily:
        """Return one family without relying on tuple position."""

        for family in self.families:
            if family.room_size == room_size:
                return family
        raise KeyError(f"No x{room_size} resource decision for {self.set_id}")


def resolve_interior_set_resources(
    resources: ResourceLayout,
    collection: InteriorSetCollection,
    atlas_mode: str = ATLAS_MODE_PRODUCTION,
    debug_atlas_directories: tuple[str, str, str, str] = ("", "", "", ""),
) -> tuple[InteriorSetResourceSnapshot, ...]:
    """Apply the global mode before resolving each Set-local family."""

    mode = normalise_atlas_mode(atlas_mode)
    debug_decisions = resolve_debug_atlases(
        resources,
        debug_atlas_directories,
    )
    snapshots = []
    for item in collection.sets:
        families = tuple(
            _resolve_family(
                resources,
                item.set_id,
                room_size,
                directory,
                mode,
                debug_decisions[room_size - 1],
            )
            for room_size, directory in zip(
                ROOM_SIZES,
                item.atlas_directories,
                strict=True,
            )
        )
        manifests = {
            family.room_size: (
                family.atlas.variant_manifest
                if family.atlas is not None
                else None
            )
            for family in families
            if family.atlas is not None
        }
        snapshots.append(
            InteriorSetResourceSnapshot(
                set_id=item.set_id,
                families=families,
                coherence=validate_manifest_coherence(manifests),
            )
        )
    return tuple(snapshots)


def build_runtime_resource_snapshot(
    resources: ResourceLayout,
    collection: InteriorSetCollection,
    atlas_mode: str = ATLAS_MODE_PRODUCTION,
    debug_atlas_directories: tuple[str, str, str, str] = ("", "", "", ""),
    resolved: tuple[InteriorSetResourceSnapshot, ...] | None = None,
) -> InteriorSetRuntimeSnapshot:
    """Adapt filesystem decisions to the installed runtime contract."""

    decisions = resolved or resolve_interior_set_resources(
        resources,
        collection,
        atlas_mode,
        debug_atlas_directories,
    )
    runtime_sets = []
    for snapshot in decisions:
        families = tuple(
            RuntimeAtlasFamily(
                room_size=family.room_size,
                asset_path=family.atlas.asset_path.as_posix(),
                variant_count=family.atlas.variant_count,
                source=family.atlas.source,
            )
            for family in snapshot.families
            if family.atlas is not None
        )
        runtime_sets.append(
            InteriorSetRuntimeResources(
                set_id=snapshot.set_id,
                resources=RuntimeResources(
                    mdl_source_asset=(
                        resources.mdl_root / "room_map.mdl"
                    ).as_posix(),
                    atlas_families=families,
                ),
                variant_coherent=snapshot.coherence.coherent,
                coherence_error=snapshot.coherence.error,
                variant_namespace=snapshot.coherence.namespace,
                variant_ids=snapshot.coherence.variant_ids,
            )
        )
    return InteriorSetRuntimeSnapshot(tuple(runtime_sets))


def _resolve_family(
    resources: ResourceLayout,
    set_id: str,
    room_size: int,
    configured_directory: str,
    atlas_mode: str,
    debug_decision: DebugAtlasDecision,
) -> ResolvedAtlasFamily:
    directory = configured_directory.strip()
    if atlas_mode == ATLAS_MODE_DEBUG:
        return ResolvedAtlasFamily(
            set_id=set_id,
            room_size=room_size,
            configured_directory=directory,
            atlas=debug_decision.atlas,
            fallback_reason="global debug mode",
            validation_error=debug_decision.validation_error,
        )
    if directory:
        try:
            production = discover_production_atlas(
                room_size=room_size,
                atlas_directory=directory,
            )
            return ResolvedAtlasFamily(
                set_id=set_id,
                room_size=room_size,
                configured_directory=directory,
                atlas=production,
            )
        except (FileNotFoundError, ValueError) as error:
            debug = debug_decision.atlas
            return ResolvedAtlasFamily(
                set_id=set_id,
                room_size=room_size,
                configured_directory=directory,
                atlas=debug,
                fallback_reason="invalid production family",
                validation_error=str(error),
            )
    debug = debug_decision.atlas
    return ResolvedAtlasFamily(
        set_id=set_id,
        room_size=room_size,
        configured_directory="",
        atlas=debug,
        fallback_reason=(
            "production family not configured" if debug is not None else None
        ),
    )
