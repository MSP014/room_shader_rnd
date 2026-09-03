"""Protect straight, bay, and corner mappings into shared room space."""

import math

import pytest

from tools.omniverse.interior_sets.manifest import (
    VariantIdentityManifest,
    semantic_variant_id,
)
from tools.omniverse.room_run.classifier import (
    ClassifierSettings,
    classify_apertures,
)

from ._support import (
    _assert_mapped_seams_are_continuous,
    _corner_box_position,
    _expected_slice_start_depth,
    _mapped_position,
    _mapped_scaled_depth_extent,
    _normalised_cross,
    _window,
    _window_run_from_angles,
)


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


def test_x4_x1_corner_uses_one_semantic_variant_identity():
    room_id = 17
    variation_seed = 3
    apertures = _window_run_from_angles(
        (0.0, 0.0, 0.0, 0.0, 90.0),
        room_id=room_id,
    )
    result = classify_apertures(
        apertures,
        ClassifierSettings(partition_seed=variation_seed),
    )
    x1_manifest = VariantIdentityManifest(
        namespace="kitchens.v1",
        variant_ids=("k-0", "k-1", "k-2", "k-3"),
    )
    x4_manifest = VariantIdentityManifest(
        namespace="kitchens.v1",
        variant_ids=("k-0", "k-1", "k-2", "k-3"),
    )

    assert len(result.groups) == 1
    assert {mapping.atlas_size for mapping in result.mappings} == {1, 4}
    assert semantic_variant_id(
        x1_manifest,
        room_id,
        variation_seed,
    ) == semantic_variant_id(
        x4_manifest,
        room_id,
        variation_seed,
    )


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


def test_incoherent_corner_families_cannot_share_one_room():
    apertures = _window_run_from_angles(
        (0.0, 90.0, 90.0, 90.0, 90.0),
        room_id=452,
    )
    set_id = apertures[0].interior_set_id

    result = classify_apertures(
        apertures,
        ClassifierSettings(
            incoherent_interior_set_ids=frozenset({set_id}),
        ),
    )

    assert all(group.room_depth_size == 1 for group in result.groups)
    assert sum(len(group.aperture_keys) for group in result.groups) == 5
    assert "INCOHERENT_ATLAS_FAMILIES" in {
        diagnostic.state for diagnostic in result.diagnostics
    }


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
