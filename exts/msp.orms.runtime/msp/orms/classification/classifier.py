"""Classify aperture runs through deterministic topology and mapping rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Iterable

from .contracts import (
    CLASSIFIER_CONTRACT_VERSION,
    ApertureDescriptor,
    ClassificationResult,
    ClassificationSummary,
    ClassifierDiagnostic,
    ClassifierSettings,
    DerivedApertureMapping,
    Float4,
    RoomGroup,
    Vector3,
)
from .mapping import (
    _corner_turn_positions,
    _fallback_mapping,
    _group_mappings,
)
from .topology import (
    _build_adjacency_graph,
    _connected_components,
    _derived_id,
    _frame_is_valid,
    _order_linear_component,
    _run_stable_key,
    _sort_key,
    _up_vector,
    partition_room_run,
)

__all__ = [
    "CLASSIFIER_CONTRACT_VERSION",
    "ApertureDescriptor",
    "ClassificationResult",
    "ClassificationSummary",
    "ClassifierDiagnostic",
    "ClassifierSettings",
    "DerivedApertureMapping",
    "Float4",
    "RoomGroup",
    "Vector3",
    "classify_apertures",
    "partition_room_run",
]


def classify_apertures(
    apertures: Iterable[ApertureDescriptor],
    settings: ClassifierSettings = ClassifierSettings(),
    *,
    up_axis: str = "Y",
) -> ClassificationResult:
    """Classify apertures without relying on input or USD primitive order."""

    up = _up_vector(up_axis)
    # Canonical ordering is established before validation so every later graph,
    # fallback, group identifier, and diagnostic is reproducible.
    ordered_apertures = tuple(
        sorted(
            apertures,
            key=lambda aperture: _sort_key(
                aperture, settings.identity_quantisation_metres
            ),
        )
    )
    keys = [aperture.key for aperture in ordered_apertures]
    if len(keys) != len(set(keys)):
        raise ValueError("Every aperture key must be unique")

    # Degenerate source frames cannot participate in proximity analysis; retain
    # them as explicit x1 fallbacks instead of silently dropping geometry.
    mappings = []
    groups = []
    diagnostics = []
    valid_apertures = []
    for aperture in ordered_apertures:
        if _frame_is_valid(aperture):
            valid_apertures.append(aperture)
            continue
        mappings.append(_fallback_mapping(aperture, "DEGENERATE_ROOM_FRAME"))
        diagnostics.append(
            ClassifierDiagnostic(
                state="DEGENERATE_ROOM_FRAME",
                prim_path=aperture.prim_path,
                details=(("aperture", aperture.key),),
            )
        )

    # x1 is the universal safe path. Geometry is first grouped independently
    # of artist family toggles; a disabled or unavailable x2-x4 family is then
    # degraded to stable x1 groups instead of repartitioning neighbouring
    # windows into a different multi-window layout.
    classification_sizes = {1, 2, 3, 4}
    classifiable_apertures = []
    for aperture in valid_apertures:
        if 1 not in settings.usable_sizes_for(aperture.interior_set_id):
            mappings.append(_fallback_mapping(aperture, "MISSING_X1_ATLAS"))
            diagnostics.append(
                ClassifierDiagnostic(
                    state="MISSING_X1_ATLAS",
                    prim_path=aperture.prim_path,
                    details=(("aperture", aperture.key),),
                )
            )
            continue
        classifiable_apertures.append(aperture)
    if not classifiable_apertures:
        return ClassificationResult(
            mappings=tuple(
                sorted(mappings, key=lambda item: item.aperture_key)
            ),
            groups=(),
            diagnostics=tuple(diagnostics),
        )

    # Establish rows and facade-local indices across every window before
    # roomID filtering. Equal IDs therefore cannot skip an intervening window.
    valid_tuple = tuple(classifiable_apertures)
    adjacency, connections, summary = _build_adjacency_graph(
        valid_tuple,
        up,
        settings,
    )

    # Each connected component must linearise cleanly before it can share a
    # virtual room. Ambiguous topology degrades locally, never speculatively.
    for component in _connected_components(adjacency):
        first = valid_tuple[component[0]]
        building_root = first.building_root
        room_id = first.room_id
        interior_set_id = first.interior_set_id
        usable_sizes = settings.usable_sizes_for(interior_set_id)
        ordered_indices, fallback_state = _order_linear_component(
            component,
            adjacency,
            connections,
            valid_tuple,
            settings,
        )
        if ordered_indices is None:
            for index in component:
                aperture = valid_tuple[index]
                mappings.append(
                    _fallback_mapping(
                        aperture, fallback_state or "INVALID_GRAPH"
                    )
                )
            diagnostics.append(
                ClassifierDiagnostic(
                    state=fallback_state or "INVALID_GRAPH",
                    prim_path=valid_tuple[component[0]].prim_path,
                    details=(
                        ("building_root", building_root),
                        ("interior_set_id", interior_set_id),
                        ("room_id", room_id),
                        ("aperture_count", len(component)),
                    ),
                )
            )
            continue

        run = tuple(valid_tuple[index] for index in ordered_indices)
        run_key = _run_stable_key(run, settings)
        corner_turns = _corner_turn_positions(
            run,
            settings.corner_turn_threshold_degrees,
        )
        if len(corner_turns) > 1:
            for index in ordered_indices:
                mappings.append(
                    _fallback_mapping(
                        valid_tuple[index], "MULTI_CORNER_LAYOUT"
                    )
                )
            diagnostics.append(
                ClassifierDiagnostic(
                    state="MULTI_CORNER_LAYOUT",
                    prim_path=run[0].prim_path,
                    details=(
                        ("building_root", building_root),
                        ("interior_set_id", interior_set_id),
                        ("room_id", room_id),
                        ("aperture_count", len(run)),
                        ("corner_count", len(corner_turns)),
                    ),
                )
            )
            continue

        # One bounded corner may retain both legs in a single room box;
        # unsupported leg sizes partition independently as straight runs.
        group_specs = []
        if corner_turns:
            split_index = corner_turns[0]
            leg_sizes = (split_index, len(run) - split_index)
            corner_room_size = max(leg_sizes)
            coherent_corner = settings.cross_family_is_coherent(
                interior_set_id
            )
            if max(leg_sizes) <= 4 and coherent_corner:
                group_specs.append(
                    (
                        run,
                        tuple(ordered_indices),
                        corner_room_size,
                        min(leg_sizes),
                    )
                )
            else:
                if max(leg_sizes) <= 4:
                    diagnostics.append(
                        ClassifierDiagnostic(
                            state="INCOHERENT_ATLAS_FAMILIES",
                            prim_path=run[0].prim_path,
                            details=(
                                ("building_root", building_root),
                                ("interior_set_id", interior_set_id),
                                ("room_id", room_id),
                            ),
                        )
                    )
                for leg_number, (leg_start, leg_end) in enumerate(
                    ((0, split_index), (split_index, len(run)))
                ):
                    leg = run[leg_start:leg_end]
                    leg_indices = tuple(ordered_indices[leg_start:leg_end])
                    partitions = partition_room_run(
                        len(leg),
                        classification_sizes,
                        settings.partition_seed,
                        f"{run_key}|leg={leg_number}",
                    )
                    offset = 0
                    for group_size in partitions:
                        group_specs.append(
                            (
                                leg[offset : offset + group_size],
                                leg_indices[offset : offset + group_size],
                                group_size,
                                1,
                            )
                        )
                        offset += group_size
        else:
            partitions = partition_room_run(
                len(run),
                classification_sizes,
                settings.partition_seed,
                run_key,
            )
            offset = 0
            for group_size in partitions:
                group_specs.append(
                    (
                        run[offset : offset + group_size],
                        tuple(ordered_indices[offset : offset + group_size]),
                        group_size,
                        1,
                    )
                )
                offset += group_size

        resolved_group_specs = []
        for group_spec in group_specs:
            (
                group_apertures,
                group_indices,
                group_size,
                _group_depth_size,
            ) = group_spec
            if group_size in usable_sizes:
                resolved_group_specs.append(group_spec)
                continue
            resolved_group_specs.extend(
                ((aperture,), (index,), 1, 1)
                for aperture, index in zip(
                    group_apertures,
                    group_indices,
                    strict=True,
                )
            )

        # Convert every accepted group directly into the affine mapping that
        # MDL consumes, keeping scene analysis out of fragment evaluation.
        for group_number, (
            group_apertures,
            group_indices,
            group_size,
            group_depth_size,
        ) in enumerate(resolved_group_specs):
            group_key = (
                f"{run_key}|set={interior_set_id}|group={group_number}|"
                f"width={group_size}|"
                f"depth={group_depth_size}|apertures={len(group_apertures)}"
            )
            group_id = _derived_id(group_key)
            groups.append(
                RoomGroup(
                    stable_key=group_key,
                    derived_id=group_id,
                    room_id=room_id,
                    building_root=building_root,
                    aperture_keys=tuple(
                        aperture.key for aperture in group_apertures
                    ),
                    room_size=group_size,
                    room_depth_size=group_depth_size,
                    interior_set_id=interior_set_id,
                )
            )
            mappings.extend(
                _group_mappings(
                    group_apertures,
                    group_indices,
                    connections,
                    up,
                    group_key,
                    group_size,
                    group_depth_size,
                    settings,
                )
            )

    interior_set_by_aperture = {
        aperture.key: aperture.interior_set_id
        for aperture in ordered_apertures
    }
    mappings = [
        replace(
            mapping,
            interior_set_id=interior_set_by_aperture[mapping.aperture_key],
        )
        for mapping in mappings
    ]

    summary = replace(
        summary,
        group_size_counts=tuple(
            sorted(Counter(group.room_size for group in groups).items())
        ),
    )
    return ClassificationResult(
        mappings=tuple(sorted(mappings, key=lambda item: item.aperture_key)),
        groups=tuple(sorted(groups, key=lambda item: item.stable_key)),
        diagnostics=tuple(
            sorted(
                diagnostics,
                key=lambda item: (
                    item.prim_path,
                    item.state,
                    repr(item.details),
                ),
            )
        ),
        summary=summary,
    )
