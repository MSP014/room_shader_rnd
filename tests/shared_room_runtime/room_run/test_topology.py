"""Protect deterministic aperture topology, graph isolation, and partitioning."""

import math

import pytest

from tools.omniverse.room_run.classifier import (
    ClassifierSettings,
    classify_apertures,
    partition_room_run,
)
from tools.omniverse.room_run.topology import _facade_bucket, _up_vector

from ._support import _window


def test_partition_uses_exact_family_for_runs_up_to_four_when_available():
    for run_length in range(1, 5):
        assert partition_room_run(run_length, {1, 2, 3, 4}, 123, "run") == (
            run_length,
        )


def test_partition_requires_the_x1_fallback():
    with pytest.raises(ValueError, match="x1 must be usable"):
        partition_room_run(5, {2, 3, 4}, 0, "run")


def test_disconnected_equal_room_ids_and_building_roots_do_not_merge():
    apertures = [
        _window("a", 7, 0.0, building="/World/A"),
        _window("b", 7, 1.1, building="/World/B"),
        _window("c", 7, 10.0, building="/World/A"),
    ]

    result = classify_apertures(apertures)

    assert len(result.groups) == 3
    assert {group.room_size for group in result.groups} == {1}


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


def test_arbitrary_facade_snap_wraps_equivalent_seam_normals():
    settings = ClassifierSettings(facade_angle_snap_degrees=7.0)
    apertures = [
        _window(
            f"seam_{index}",
            1,
            float(index),
            tangent_u=(
                math.sin(math.radians(angle)),
                0.0,
                -math.cos(math.radians(angle)),
            ),
        )
        for index, angle in enumerate((180.0, -180.0))
    ]

    buckets = {
        _facade_bucket(aperture, _up_vector("Y"), settings)
        for aperture in apertures
    }

    assert len(buckets) == 1
