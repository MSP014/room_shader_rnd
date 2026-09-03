"""Protect the public pure-classifier orchestration and fallback contract."""

from dataclasses import replace
from random import Random

from tools.omniverse.room_run.classifier import (
    ClassifierSettings,
    classify_apertures,
)

from ._support import (
    _group_sizes_in_geometry_order,
    _window,
)

KITCHENS_SET_ID = "11111111-1111-1111-1111-111111111111"


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


def test_different_interior_sets_cannot_share_one_room():
    living_room = _window("w0", 1, 0.0)
    kitchen = replace(
        _window("w1", 1, 1.1),
        interior_set_id=KITCHENS_SET_ID,
    )

    result = classify_apertures((living_room, kitchen))

    assert [group.room_size for group in result.groups] == [1, 1]
    assert {group.interior_set_id for group in result.groups} == {
        living_room.interior_set_id,
        KITCHENS_SET_ID,
    }
    assert result.summary.rejected_interior_set_edge_count == 1


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


def test_facade_local_spacing_is_scale_independent():
    compact = [_window(f"w{index}", 11, index * 3.0) for index in range(3)]
    large = [
        _window(
            f"large_{index}",
            12,
            index * 30.0,
            width=10.0,
            height=10.0,
        )
        for index in range(3)
    ]

    compact_result = classify_apertures(compact)
    large_result = classify_apertures(large)

    assert [group.room_size for group in compact_result.groups] == [3]
    assert [group.room_size for group in large_result.groups] == [3]
    assert compact_result.summary.rejected_spacing_edge_count == 0
    assert large_result.summary.rejected_spacing_edge_count == 0


def test_different_facade_spacings_are_classified_independently():
    front = [_window(f"w{index}", 21, index * 3.0) for index in range(3)]
    back = [
        _window(
            f"back_{index}",
            22,
            index * 1.1,
            z=10.0,
            tangent_u=(-1.0, 0.0, 0.0),
        )
        for index in range(3)
    ]

    result = classify_apertures(front + back)

    assert sorted(group.room_size for group in result.groups) == [3, 3]
    assert result.summary.facade_count == 2


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


def test_unavailable_or_disabled_families_degrade_to_supported_groups():
    apertures = [_window(f"w{index}", 3, index * 1.1) for index in range(12)]
    settings = ClassifierSettings(
        enabled_room_sizes=frozenset({1, 2, 3}),
        available_room_sizes=frozenset({1, 2, 4}),
        partition_seed=17,
    )

    result = classify_apertures(apertures, settings)

    assert {group.room_size for group in result.groups} <= {1, 2}
    assert sum(group.room_size for group in result.groups) == 12


def test_atlas_availability_is_resolved_independently_per_set():
    living = [_window(f"w{index}", 3, index * 1.1) for index in range(2)]
    kitchens = [
        replace(
            _window(f"k{index}", 4, 5.0 + index * 1.1),
            interior_set_id=KITCHENS_SET_ID,
        )
        for index in range(2)
    ]
    settings = ClassifierSettings(
        available_room_sizes_by_set=(
            (living[0].interior_set_id, frozenset({1, 2})),
            (KITCHENS_SET_ID, frozenset({1})),
        )
    )

    result = classify_apertures(living + kitchens, settings)

    sizes_by_set = {
        set_id: sorted(
            group.room_size
            for group in result.groups
            if group.interior_set_id == set_id
        )
        for set_id in (living[0].interior_set_id, KITCHENS_SET_ID)
    }
    assert sizes_by_set[living[0].interior_set_id] == [2]
    assert sizes_by_set[KITCHENS_SET_ID] == [1, 1]


def test_disabled_x4_family_degrades_existing_x4_group_to_x1():
    apertures = [_window(f"w{index}", 3, index * 1.1) for index in range(4)]

    enabled = classify_apertures(apertures, ClassifierSettings())
    disabled = classify_apertures(
        apertures,
        ClassifierSettings(
            enabled_room_sizes=frozenset({1, 2, 3}),
        ),
    )

    assert [group.room_size for group in enabled.groups] == [4]
    assert [group.room_size for group in disabled.groups] == [1, 1, 1, 1]
    assert {mapping.room_size for mapping in disabled.mappings} == {1}


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
