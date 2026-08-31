import math
from random import Random

import pytest

from tools.omniverse.room_run_classifier import (
    ApertureDescriptor,
    ClassifierSettings,
    classify_apertures,
    partition_room_run,
)


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


def test_equal_room_id_forms_only_geometrically_contiguous_runs():
    apertures = [
        _window("w0", 1, 0.0),
        _window("w1", 1, 1.1),
        _window("w2", 2, 2.2),
        _window("w3", 1, 3.3),
        _window("w4", 1, 4.4),
    ]

    result = classify_apertures(apertures)

    assert [group.room_size for group in result.groups] == [2, 2, 1]
    assert {mapping.slice_start_depth for mapping in result.mappings} == {0.0}
    assert _group_sizes_in_geometry_order(result, apertures) == [2, 2, 1, 2, 2]
    assert not result.diagnostics


def test_floor_sequences_are_classified_independently():
    floor_1_ids = (1, 2, 3, 4, 4)
    floor_2_ids = (1, 1, 2, 3, 4)
    floor_1 = [
        _window(f"w{index}", room_id, index * 1.1, y=0.5)
        for index, room_id in enumerate(floor_1_ids)
    ]
    floor_2 = [
        _window(f"w{index + 5}", room_id, index * 1.1, y=3.5)
        for index, room_id in enumerate(floor_2_ids)
    ]

    result = classify_apertures(floor_1 + floor_2)

    assert _group_sizes_in_geometry_order(result, floor_1) == [1, 1, 1, 2, 2]
    assert _group_sizes_in_geometry_order(result, floor_2) == [2, 2, 1, 1, 1]


def test_long_run_partition_is_repeatable_and_primitive_order_independent():
    apertures = [_window(f"w{index}", 9, index * 1.1) for index in range(17)]
    shuffled = list(apertures)
    Random(732).shuffle(shuffled)
    settings = ClassifierSettings(partition_seed=42)

    first = classify_apertures(apertures, settings)
    second = classify_apertures(shuffled, settings)

    assert first == second
    assert sum(group.room_size for group in first.groups) == 17
    assert all(1 <= group.room_size <= 4 for group in first.groups)


def test_unavailable_or_disabled_families_are_excluded_from_partitioning():
    apertures = [_window(f"w{index}", 3, index * 1.1) for index in range(12)]
    settings = ClassifierSettings(
        enabled_room_sizes=frozenset({1, 2, 3}),
        available_room_sizes=frozenset({1, 2, 4}),
        partition_seed=17,
    )

    result = classify_apertures(apertures, settings)

    assert {group.room_size for group in result.groups} <= {1, 2}
    assert sum(group.room_size for group in result.groups) == 12


def test_partition_uses_exact_family_for_runs_up_to_four_when_available():
    for run_length in range(1, 5):
        assert partition_room_run(run_length, {1, 2, 3, 4}, 123, "run") == (
            run_length,
        )


def test_partition_requires_the_x1_fallback():
    with pytest.raises(ValueError, match="x1 must be usable"):
        partition_room_run(5, {2, 3, 4}, 0, "run")


def test_ninety_degree_corner_uses_one_fixed_square_room_basis():
    first = _window(
        "corner_a",
        4,
        0.0,
        z=0.5,
        tangent_u=(0.0, 0.0, 1.0),
    )
    second = _window(
        "corner_b",
        4,
        -0.5,
        z=1.0,
        tangent_u=(-1.0, 0.0, 0.0),
    )

    result = classify_apertures([second, first])

    assert len(result.groups) == 1
    assert result.groups[0].room_size == 1
    assert result.groups[0].room_depth_size == 1
    assert len(result.groups[0].aperture_keys) == 2
    assert (
        len(
            {
                tuple(abs(round(value, 6)) for value in mapping.room_axis_u)
                for mapping in result.mappings
            }
        )
        == 1
    )
    assert {mapping.room_scale for mapping in result.mappings} == {
        (1.0, 1.0, 1.0)
    }
    assert {mapping.room_depth_size for mapping in result.mappings} == {1}
    assert {mapping.atlas_size for mapping in result.mappings} == {1}
    assert {mapping.slice_start_depth for mapping in result.mappings} == {0.0}
    assert {
        tuple(abs(round(value, 6)) for value in mapping.map_axis_u)
        for mapping in result.mappings
    } == {(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)}
    assert not result.diagnostics


@pytest.mark.parametrize(
    ("first_leg_size", "second_leg_size"),
    (
        (1, 1),
        (1, 2),
        (2, 1),
        (1, 3),
        (3, 1),
        (2, 2),
        (1, 4),
        (4, 1),
        (2, 3),
        (3, 2),
        (2, 4),
        (4, 2),
        (3, 3),
        (3, 4),
        (4, 3),
        (4, 4),
    ),
)
def test_single_corner_supports_every_bounded_one_to_four_footprint(
    first_leg_size,
    second_leg_size,
):
    apertures = _window_run_from_angles(
        (0.0,) * first_leg_size + (90.0,) * second_leg_size,
        room_id=400 + first_leg_size * 10 + second_leg_size,
    )

    result = classify_apertures(reversed(apertures))

    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.room_size == max(first_leg_size, second_leg_size)
    assert group.room_depth_size == min(first_leg_size, second_leg_size)
    assert len(group.aperture_keys) == first_leg_size + second_leg_size
    assert {mapping.group_id for mapping in result.mappings} == {
        group.derived_id
    }
    mappings = {mapping.aperture_key: mapping for mapping in result.mappings}
    assert {mapping.room_size for mapping in result.mappings} == {
        max(first_leg_size, second_leg_size)
    }
    assert {mapping.room_depth_size for mapping in result.mappings} == {
        min(first_leg_size, second_leg_size)
    }
    for index in range(first_leg_size):
        assert mappings[f"w{index}"].atlas_size == first_leg_size
    for index in range(first_leg_size, first_leg_size + second_leg_size):
        assert mappings[f"w{index}"].atlas_size == second_leg_size
    first_axes = {
        mappings[f"w{index}"].room_axis_u for index in range(first_leg_size)
    }
    second_axes = {
        mappings[f"w{index}"].room_axis_u
        for index in range(first_leg_size, first_leg_size + second_leg_size)
    }
    assert len(first_axes) == 1
    assert len(second_axes) == 1
    assert first_axes == second_axes
    assert len({mapping.room_axis_v for mapping in result.mappings}) == 1
    positions_by_key = {
        key: tuple(_corner_box_position(mapping, u, 0.5) for u in (0.0, 1.0))
        for key, mapping in mappings.items()
    }
    primary_keys = (
        tuple(f"w{index}" for index in range(first_leg_size))
        if first_leg_size >= second_leg_size
        else tuple(
            f"w{index}"
            for index in range(
                first_leg_size,
                first_leg_size + second_leg_size,
            )
        )
    )
    secondary_keys = tuple(set(mappings) - set(primary_keys))
    assert all(
        point[2] == pytest.approx(0.0)
        for key in primary_keys
        for point in positions_by_key[key]
    )
    secondary_x = {
        round(point[0], 6)
        for key in secondary_keys
        for point in positions_by_key[key]
    }
    assert secondary_x in (
        {0.0},
        {float(max(first_leg_size, second_leg_size))},
    )
    all_positions = tuple(
        point for positions in positions_by_key.values() for point in positions
    )
    assert min(point[0] for point in all_positions) == pytest.approx(0.0)
    assert max(point[0] for point in all_positions) == pytest.approx(
        max(first_leg_size, second_leg_size)
    )
    assert min(point[2] for point in all_positions) == pytest.approx(
        -min(first_leg_size, second_leg_size)
    )
    assert max(point[2] for point in all_positions) == pytest.approx(0.0)
    assert {mapping.slice_start_depth for mapping in result.mappings} == {0.0}
    assert not result.diagnostics


def test_corner_mapping_keeps_a_distinct_portal_normal_for_each_facade_leg():
    apertures = _window_run_from_angles((0.0, 0.0, 90.0, 90.0), room_id=422)

    result = classify_apertures(apertures)

    mappings = {mapping.aperture_key: mapping for mapping in result.mappings}
    first_leg_normals = {
        tuple(
            round(component, 6)
            for component in _normalised_cross(
                mappings[key].map_axis_u,
                mappings[key].map_axis_v,
            )
        )
        for key in ("w0", "w1")
    }
    second_leg_normals = {
        tuple(
            round(component, 6)
            for component in _normalised_cross(
                mappings[key].map_axis_u,
                mappings[key].map_axis_v,
            )
        )
        for key in ("w2", "w3")
    }
    assert len(first_leg_normals) == 1
    assert len(second_leg_normals) == 1
    first_normal = next(iter(first_leg_normals))
    second_normal = next(iter(second_leg_normals))
    assert sum(
        first * second for first, second in zip(first_normal, second_normal)
    ) == pytest.approx(0.0)


def test_corner_packs_exact_primary_aperture_spans_with_real_gaps():
    primary_specs = (
        (0.0, 0.6),
        (0.75, 0.9),
        (1.9, 0.7),
        (2.7, 1.0),
    )
    apertures = [
        _window(
            f"w{index}",
            441,
            0.0,
            z=start + width * 0.5,
            width=width,
            tangent_u=(0.0, 0.0, width),
        )
        for index, (start, width) in enumerate(primary_specs)
    ]
    apertures.append(
        _window(
            "w4",
            441,
            0.4,
            z=3.7,
            width=0.8,
            tangent_u=(0.8, 0.0, 0.0),
        )
    )

    result = classify_apertures(reversed(apertures))

    expected_minimums = tuple(start / 3.7 for start, _width in primary_specs)
    expected_maximums = tuple(
        (start + width) / 3.7 for start, width in primary_specs
    )
    assert len(result.groups) == 1
    assert (result.groups[0].room_size, result.groups[0].room_depth_size) == (
        4,
        1,
    )
    for mapping in result.mappings:
        assert mapping.primary_aperture_min_u == pytest.approx(
            expected_minimums
        )
        assert mapping.primary_aperture_max_u == pytest.approx(
            expected_maximums
        )


def test_disabled_corner_family_partitions_each_straight_leg_separately():
    apertures = _window_run_from_angles(
        (0.0, 90.0, 90.0, 90.0, 90.0),
        room_id=451,
    )
    result = classify_apertures(
        apertures,
        ClassifierSettings(
            enabled_room_sizes=frozenset({1, 2}),
            available_room_sizes=frozenset({1, 2, 3, 4}),
            partition_seed=19,
        ),
    )

    assert {group.room_size for group in result.groups} <= {1, 2}
    assert {group.room_depth_size for group in result.groups} == {1}
    assert sum(len(group.aperture_keys) for group in result.groups) == 5
    assert next(
        group for group in result.groups if "w0" in group.aperture_keys
    ).aperture_keys == ("w0",)


def test_multiple_sharp_turns_use_explicit_x1_fallback():
    apertures = _window_run_from_angles(
        (0.0, 90.0, 0.0),
        room_id=460,
        width=2.0,
    )

    result = classify_apertures(apertures)

    assert not result.groups
    assert {mapping.room_size for mapping in result.mappings} == {1}
    assert {mapping.fallback_state for mapping in result.mappings} == {
        "MULTI_CORNER_LAYOUT"
    }
    assert {diagnostic.state for diagnostic in result.diagnostics} == {
        "MULTI_CORNER_LAYOUT"
    }


def test_corner_threshold_can_reclassify_the_same_turn_as_a_bay():
    apertures = _window_run_from_angles((0.0, 90.0), room_id=74)

    result = classify_apertures(
        apertures,
        ClassifierSettings(corner_turn_threshold_degrees=95.0),
    )

    assert len({mapping.room_axis_u for mapping in result.mappings}) == 1
    assert tuple(
        abs(value) for value in result.mappings[0].room_axis_u
    ) == pytest.approx((math.sqrt(0.5), 0.0, math.sqrt(0.5)))


def test_odd_bay_group_uses_central_aperture_for_one_shared_room_basis():
    apertures = _window_run_from_angles((-50.0, 0.0, 25.0), room_id=71)

    result = classify_apertures(apertures)

    assert [group.room_size for group in result.groups] == [3]
    for mapping in result.mappings:
        assert tuple(abs(value) for value in mapping.room_axis_u) == (
            pytest.approx((0.0, 0.0, 1.0))
        )
        assert mapping.room_axis_v == pytest.approx((0.0, 1.0, 0.0))
    _assert_mapped_seams_are_continuous(result, ("w0", "w1", "w2"))
    mappings = {mapping.aperture_key: mapping for mapping in result.mappings}
    expected_slice_start = _expected_slice_start_depth(result.mappings)
    assert expected_slice_start > 0.0
    for mapping in result.mappings:
        assert mapping.slice_start_depth == pytest.approx(expected_slice_start)
    assert mappings["w0"].map_axis_u[2] != pytest.approx(0.0)
    assert mappings["w1"].map_axis_u[2] == pytest.approx(0.0)
    assert mappings["w2"].map_axis_u[2] != pytest.approx(0.0)


def test_even_bay_group_uses_parallel_central_pair_for_shared_room_basis():
    apertures = _window_run_from_angles((-55.0, 0.0, 0.0, 30.0), room_id=72)

    result = classify_apertures(apertures)

    assert [group.room_size for group in result.groups] == [4]
    for mapping in result.mappings:
        assert tuple(abs(value) for value in mapping.room_axis_u) == (
            pytest.approx((0.0, 0.0, 1.0))
        )
        assert mapping.room_axis_v == pytest.approx((0.0, 1.0, 0.0))
        assert mapping.slice_start_depth == pytest.approx(
            _expected_slice_start_depth(result.mappings)
        )
    assert result.mappings[0].slice_start_depth > 0.0
    _assert_mapped_seams_are_continuous(result, ("w0", "w1", "w2", "w3"))


def test_even_arc_without_parallel_windows_uses_mean_shared_room_basis():
    angles = (-12.0, -4.0, 4.0, 12.0)
    apertures = _window_run_from_angles(angles, room_id=73)

    result = classify_apertures(apertures)

    assert [group.room_size for group in result.groups] == [4]
    for left, right in zip(apertures, apertures[1:]):
        left_axis = left.tangent_u_metres
        right_axis = right.tangent_u_metres
        left_width = math.sqrt(sum(component**2 for component in left_axis))
        right_width = math.sqrt(sum(component**2 for component in right_axis))
        cosine = sum(a * b for a, b in zip(left_axis, right_axis)) / (
            left_width * right_width
        )
        assert math.degrees(math.acos(cosine)) == pytest.approx(8.0)
        assert left_width == pytest.approx(0.8)
    for mapping in result.mappings:
        assert mapping.room_axis_u == pytest.approx((0.0, 0.0, 1.0))
        assert mapping.room_axis_v == pytest.approx((0.0, 1.0, 0.0))
        assert mapping.slice_start_depth == pytest.approx(
            _expected_slice_start_depth(result.mappings)
        )
    assert result.mappings[0].slice_start_depth > 0.0
    _assert_mapped_seams_are_continuous(result, ("w0", "w1", "w2", "w3"))
    minimum_depth, maximum_depth = _mapped_scaled_depth_extent(result.mappings)
    assert maximum_depth == pytest.approx(0.0)
    assert minimum_depth == pytest.approx(
        -result.mappings[0].slice_start_depth
    )


def test_disconnected_equal_room_ids_and_building_roots_do_not_merge():
    apertures = [
        _window("a", 7, 0.0, building="/World/A"),
        _window("b", 7, 1.1, building="/World/B"),
        _window("c", 7, 10.0, building="/World/A"),
    ]

    result = classify_apertures(apertures)

    assert len(result.groups) == 3
    assert {group.room_size for group in result.groups} == {1}


def test_different_aperture_dimensions_preserve_physical_widths_and_gap():
    narrow = _window("narrow", 5, 0.0, width=1.0, height=1.0)
    wide = _window("wide", 5, 1.6, width=2.0, height=1.5)
    result = classify_apertures([wide, narrow])
    mappings = {mapping.aperture_key: mapping for mapping in result.mappings}

    assert result.groups[0].room_size == 2
    assert abs(mappings["narrow"].map_axis_u[0]) == pytest.approx(1.0)
    assert abs(mappings["wide"].map_axis_u[0]) == pytest.approx(2.0)
    assert abs(mappings["narrow"].map_axis_v[1]) == pytest.approx(1.0)
    assert abs(mappings["wide"].map_axis_v[1]) == pytest.approx(1.5)
    narrow_extent = sorted(
        (
            _mapped_position(mappings["narrow"], 0.0, 0.5)[0],
            _mapped_position(mappings["narrow"], 1.0, 0.5)[0],
        )
    )
    wide_extent = sorted(
        (
            _mapped_position(mappings["wide"], 0.0, 0.5)[0],
            _mapped_position(mappings["wide"], 1.0, 0.5)[0],
        )
    )
    assert wide_extent[0] - narrow_extent[1] == pytest.approx(0.1)


def test_branched_graph_falls_back_to_independent_x1_mappings():
    centre = _window("centre", 8, 0.0)
    left = _window("left", 8, -1.1)
    right = _window("right", 8, 1.1)
    corner = _window(
        "corner",
        8,
        0.5,
        z=0.5,
        tangent_u=(0.0, 0.0, 1.0),
    )

    result = classify_apertures([centre, left, right, corner])

    assert not result.groups
    assert {mapping.room_size for mapping in result.mappings} == {1}
    assert not any(mapping.mapping_valid for mapping in result.mappings)
    assert {diagnostic.state for diagnostic in result.diagnostics} == {
        "BRANCHED_GRAPH"
    }


def test_degenerate_frame_and_missing_x1_atlas_are_explicit_fallbacks():
    invalid = _window("invalid", 1, 0.0, tangent_u=(0.0, 0.0, 0.0))
    valid = _window("valid", 2, 2.0)
    settings = ClassifierSettings(available_room_sizes=frozenset({2, 3, 4}))

    result = classify_apertures([invalid, valid], settings)

    states = {
        mapping.aperture_key: mapping.fallback_state
        for mapping in result.mappings
    }
    assert states == {
        "invalid": "DEGENERATE_ROOM_FRAME",
        "valid": "MISSING_X1_ATLAS",
    }
    assert {diagnostic.state for diagnostic in result.diagnostics} == {
        "DEGENERATE_ROOM_FRAME",
        "MISSING_X1_ATLAS",
    }
