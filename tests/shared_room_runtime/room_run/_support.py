# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Build reusable pure-classifier apertures and mapping assertions."""

import math

import pytest
from msp.orms.classification.classifier import ApertureDescriptor


def _window(
    key,
    room_id,
    x,
    *,
    y=0.5,
    z=0.0,
    width=1.0,
    height=1.0,
    building="/World/Building",
    tangent_u=None,
    tangent_v=None,
):
    tangent_u = tangent_u or (width, 0.0, 0.0)
    tangent_v = tangent_v or (0.0, height, 0.0)
    return ApertureDescriptor(
        key=key,
        prim_path="/World/Building/Windows",
        face_index=(
            int(key[1:]) if key.startswith("w") and key[1:].isdigit() else 0
        ),
        building_root=building,
        room_id=room_id,
        centre_metres=(x, y, z),
        tangent_u_metres=tangent_u,
        tangent_v_metres=tangent_v,
    )


def _window_run_from_angles(angles_degrees, *, room_id=70, width=0.8):
    endpoint = (0.0, 0.0)
    apertures = []
    for index, angle_degrees in enumerate(angles_degrees):
        angle = math.radians(angle_degrees)
        tangent_u = (
            math.sin(angle) * width,
            0.0,
            math.cos(angle) * width,
        )
        next_endpoint = (
            endpoint[0] + tangent_u[0],
            endpoint[1] + tangent_u[2],
        )
        apertures.append(
            _window(
                f"w{index}",
                room_id,
                (endpoint[0] + next_endpoint[0]) * 0.5,
                z=(endpoint[1] + next_endpoint[1]) * 0.5,
                width=width,
                tangent_u=tangent_u,
            )
        )
        endpoint = next_endpoint
    return apertures


def _group_sizes_in_geometry_order(result, apertures):
    group_size_by_key = {
        aperture_key: group.room_size
        for group in result.groups
        for aperture_key in group.aperture_keys
    }
    return [group_size_by_key[aperture.key] for aperture in apertures]


def _mapped_position(mapping, u, v):
    return tuple(
        mapping.map_origin[index]
        + mapping.map_axis_u[index] * u
        + mapping.map_axis_v[index] * v
        for index in range(3)
    )


def _corner_box_position(mapping, u, v):
    mapped = _mapped_position(mapping, u, v)
    return (
        mapped[0] * mapping.room_scale[0] + mapping.room_size * 0.5,
        mapped[1] * mapping.room_scale[1] + 0.5,
        mapped[2] * mapping.room_scale[2],
    )


def _normalised_cross(left, right):
    cross = (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
    length = math.sqrt(sum(component**2 for component in cross))
    return tuple(component / length for component in cross)


def _assert_mapped_seams_are_continuous(result, aperture_keys):
    mappings = {mapping.aperture_key: mapping for mapping in result.mappings}
    for left_key, right_key in zip(aperture_keys, aperture_keys[1:]):
        assert _mapped_position(mappings[left_key], 1.0, 0.5) == pytest.approx(
            _mapped_position(mappings[right_key], 0.0, 0.5)
        )


def _expected_slice_start_depth(mappings):
    mapped_depths = []
    for mapping in mappings:
        for u in (0.0, 1.0):
            for v in (0.0, 1.0):
                mapped_depths.append(
                    _mapped_position(mapping, u, v)[2] * mapping.room_scale[2]
                )
    return max(0.0, -min(mapped_depths))


def _mapped_scaled_depth_extent(mappings):
    mapped_depths = []
    for mapping in mappings:
        for u in (0.0, 1.0):
            for v in (0.0, 1.0):
                mapped_depths.append(
                    _mapped_position(mapping, u, v)[2] * mapping.room_scale[2]
                )
    return min(mapped_depths), max(mapped_depths)
