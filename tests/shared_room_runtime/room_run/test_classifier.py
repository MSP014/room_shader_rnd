"""Protect the public pure-classifier orchestration and fallback contract."""

from random import Random

from tools.omniverse.room_run.classifier import (
    ClassifierSettings,
    classify_apertures,
)

from ._support import (
    _group_sizes_in_geometry_order,
    _window,
)


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
