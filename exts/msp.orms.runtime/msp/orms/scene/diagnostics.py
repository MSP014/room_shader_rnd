# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Summarise classified corner boxes without coupling diagnostics to loading."""

from __future__ import annotations

from typing import Any


def corner_box_summaries(classification: Any | None) -> tuple[str, ...]:
    """Return stable reader-facing summaries for classified corner rooms."""

    if classification is None:
        return ()

    mappings_by_group = {}
    for mapping in classification.result.mappings:
        mappings_by_group.setdefault(mapping.group_id, []).append(mapping)

    summaries = []
    for group in classification.result.groups:
        if len(group.aperture_keys) <= group.room_size:
            continue
        mappings = mappings_by_group.get(group.derived_id, ())
        if not mappings:
            continue
        axes = sorted(
            {
                tuple(round(value, 4) for value in mapping.room_axis_u)
                for mapping in mappings
            }
        )
        atlas_sizes = sorted({mapping.atlas_size for mapping in mappings})
        reference_mapping = mappings[0]
        room_width_metres = (
            reference_mapping.room_size / reference_mapping.room_scale[0]
        )
        raw_aperture_intervals = tuple(
            (minimum, maximum)
            for minimum, maximum in zip(
                reference_mapping.primary_aperture_min_u,
                reference_mapping.primary_aperture_max_u,
            )
            if minimum >= 0.0 and maximum >= minimum
        )
        aperture_intervals = tuple(
            (round(minimum, 4), round(maximum, 4))
            for minimum, maximum in raw_aperture_intervals
        )
        aperture_spans_metres = tuple(
            (
                round(minimum * room_width_metres, 4),
                round(maximum * room_width_metres, 4),
            )
            for minimum, maximum in raw_aperture_intervals
        )
        side_depth_spans_metres = tuple(
            (
                round(
                    min(
                        mapping.map_origin[2],
                        mapping.map_origin[2] + mapping.map_axis_u[2],
                    ),
                    4,
                ),
                round(
                    max(
                        mapping.map_origin[2],
                        mapping.map_origin[2] + mapping.map_axis_u[2],
                    ),
                    4,
                ),
            )
            for mapping in mappings
            if abs(mapping.map_axis_u[2]) > 1.0e-6
        )
        front_gaps_metres = tuple(
            round(min(abs(minimum), abs(maximum)), 4)
            for minimum, maximum in side_depth_spans_metres
        )
        side_u_offsets_metres = tuple(
            round(mapping.aperture_mask_offset_u, 4)
            for mapping in mappings
            if abs(mapping.map_axis_u[2]) > 1.0e-6
        )
        summaries.append(
            f"roomID={group.room_id}:box=x{group.room_size}"
            f"x{group.room_depth_size},axes={axes},atlases={atlas_sizes},"
            "primary_plane_room_z=0.0,"
            f"primary_intervals={aperture_intervals},"
            f"primary_spans_from_group_min_m={aperture_spans_metres},"
            f"side_depth_spans_m={side_depth_spans_metres},"
            f"front_gaps_m={front_gaps_metres},"
            f"side_u_offsets_m={side_u_offsets_metres}"
        )
    return tuple(summaries)
