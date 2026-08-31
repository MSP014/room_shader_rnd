"""Build deterministic aperture adjacency and partition linear room runs."""

from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from typing import Iterable

from .contracts import (
    ApertureDescriptor,
    ClassifierSettings,
    Float4,
    Vector3,
)

_EPSILON = 1.0e-8
_DERIVED_ID_LIMIT = 2_147_483_647


def _add(left: Vector3, right: Vector3) -> Vector3:
    return tuple(a + b for a, b in zip(left, right))  # type: ignore[return-value]


def _subtract(left: Vector3, right: Vector3) -> Vector3:
    return tuple(a - b for a, b in zip(left, right))  # type: ignore[return-value]


def _multiply(vector: Vector3, scalar: float) -> Vector3:
    return tuple(value * scalar for value in vector)  # type: ignore[return-value]


def _dot(left: Vector3, right: Vector3) -> float:
    return sum(a * b for a, b in zip(left, right))


def _normalised_aperture_intervals(
    apertures: tuple[ApertureDescriptor, ...],
    room_axis_u: Vector3,
    group_min_u: float,
    group_width: float,
) -> tuple[Float4, Float4]:
    """Pack up to four real aperture spans into the logical room width."""

    intervals = []
    for aperture in apertures:
        centre_u = _dot(aperture.centre_metres, room_axis_u)
        half_width_u = 0.5 * _dot(
            aperture.tangent_u_metres,
            room_axis_u,
        )
        endpoint_a = centre_u - half_width_u
        endpoint_b = centre_u + half_width_u
        minimum = (min(endpoint_a, endpoint_b) - group_min_u) / group_width
        maximum = (max(endpoint_a, endpoint_b) - group_min_u) / group_width
        intervals.append(
            (
                min(max(minimum, 0.0), 1.0),
                min(max(maximum, 0.0), 1.0),
            )
        )
    intervals.sort()
    intervals = intervals[:4]
    while len(intervals) < 4:
        intervals.append((-1.0, -1.0))
    return (
        tuple(interval[0] for interval in intervals),  # type: ignore[return-value]
        tuple(interval[1] for interval in intervals),  # type: ignore[return-value]
    )


def _cross(left: Vector3, right: Vector3) -> Vector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _length(vector: Vector3) -> float:
    return math.sqrt(_dot(vector, vector))


def _normalise(vector: Vector3) -> Vector3:
    length = _length(vector)
    if length <= _EPSILON:
        return (0.0, 0.0, 0.0)
    return _multiply(vector, 1.0 / length)


def _distance(left: Vector3, right: Vector3) -> float:
    return _length(_subtract(left, right))


def _horizontal_distance(
    left: Vector3,
    right: Vector3,
    up_axis: Vector3,
) -> float:
    difference = _subtract(left, right)
    vertical = _multiply(up_axis, _dot(difference, up_axis))
    return _length(_subtract(difference, vertical))


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _angle_degrees(left: Vector3, right: Vector3) -> float:
    cosine = _clamp(_dot(_normalise(left), _normalise(right)), -1.0, 1.0)
    return math.degrees(math.acos(cosine))


def _up_vector(up_axis: str) -> Vector3:
    if up_axis == "Y":
        return (0.0, 1.0, 0.0)
    if up_axis == "Z":
        return (0.0, 0.0, 1.0)
    raise ValueError(f"Unsupported up axis: {up_axis}")


def _frame_is_valid(aperture: ApertureDescriptor) -> bool:
    tangent_u = aperture.tangent_u_metres
    tangent_v = aperture.tangent_v_metres
    return (
        _length(tangent_u) > _EPSILON
        and _length(tangent_v) > _EPSILON
        and _length(_cross(tangent_u, tangent_v)) > _EPSILON
    )


def _canonical_axis(vector: Vector3) -> Vector3:
    axis = _normalise(vector)
    for component in axis:
        if abs(component) <= _EPSILON:
            continue
        return axis if component > 0.0 else _multiply(axis, -1.0)
    return axis


def _quantise(value: float, quantum: float) -> int:
    safe_quantum = max(quantum, _EPSILON)
    return int(round(value / safe_quantum))


def _geometry_identity(
    aperture: ApertureDescriptor,
    quantum: float,
) -> tuple[object, ...]:
    # Geometry, rather than traversal order or process state, defines every
    # stable run and group identifier produced by the classifier.
    return (
        aperture.building_root,
        aperture.room_id,
        *(_quantise(value, quantum) for value in aperture.centre_metres),
        _quantise(_length(aperture.tangent_u_metres), quantum),
        _quantise(_length(aperture.tangent_v_metres), quantum),
        *(
            _quantise(value, quantum)
            for value in _canonical_axis(aperture.tangent_u_metres)
        ),
        *(
            _quantise(value, quantum)
            for value in _canonical_axis(aperture.tangent_v_metres)
        ),
    )


def _sort_key(
    aperture: ApertureDescriptor,
    quantum: float,
) -> tuple[object, ...]:
    return _geometry_identity(aperture, quantum) + (aperture.key,)


def _stable_digest(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()


def _stable_integer(text: str) -> int:
    return int.from_bytes(_stable_digest(text)[:8], "big")


def _derived_id(stable_key: str) -> int:
    return _stable_integer(stable_key) % _DERIVED_ID_LIMIT


def _aperture_edges(aperture: ApertureDescriptor) -> tuple[Vector3, Vector3]:
    half_tangent = _multiply(aperture.tangent_u_metres, 0.5)
    return (
        _subtract(aperture.centre_metres, half_tangent),
        _add(aperture.centre_metres, half_tangent),
    )


def _vertical_interval(
    aperture: ApertureDescriptor,
    up_axis: Vector3,
) -> tuple[float, float]:
    centre = _dot(aperture.centre_metres, up_axis)
    vertical_extent = abs(_dot(aperture.tangent_v_metres, up_axis))
    half_extent = 0.5 * vertical_extent
    return centre - half_extent, centre + half_extent


def _height_bands_are_compatible(
    left: ApertureDescriptor,
    right: ApertureDescriptor,
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> bool:
    left_bottom, left_top = _vertical_interval(left, up_axis)
    right_bottom, right_top = _vertical_interval(right, up_axis)
    overlap = max(
        0.0, min(left_top, right_top) - max(left_bottom, right_bottom)
    )
    minimum_height = max(
        _EPSILON,
        min(left_top - left_bottom, right_top - right_bottom),
    )
    overlap_ratio = overlap / minimum_height
    return (
        abs(left_bottom - right_bottom) <= settings.floor_tolerance_metres
        and overlap_ratio >= settings.minimum_vertical_overlap
    )


@dataclass(frozen=True)
class _Connection:
    left_end: int
    right_end: int
    distance: float


def _connection_between(
    left: ApertureDescriptor,
    right: ApertureDescriptor,
    up_axis: Vector3,
) -> _Connection:
    candidates = []
    for left_end, left_position in enumerate(_aperture_edges(left)):
        for right_end, right_position in enumerate(_aperture_edges(right)):
            candidates.append(
                (
                    _horizontal_distance(
                        left_position, right_position, up_axis
                    ),
                    left_end,
                    right_end,
                )
            )
    distance, left_end, right_end = min(candidates)
    return _Connection(left_end, right_end, distance)


def _are_adjacent(
    left: ApertureDescriptor,
    right: ApertureDescriptor,
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> tuple[bool, _Connection]:
    # Adjacency requires compatible height, facade turn, and physical edge gap;
    # roomID and building-root isolation are applied by the caller's buckets.
    connection = _connection_between(left, right, up_axis)
    left_normal = _cross(left.tangent_u_metres, left.tangent_v_metres)
    right_normal = _cross(right.tangent_u_metres, right.tangent_v_metres)
    return (
        _height_bands_are_compatible(left, right, up_axis, settings)
        and _angle_degrees(left_normal, right_normal)
        <= settings.maximum_turn_degrees
        and connection.distance <= settings.edge_gap_tolerance_metres,
        connection,
    )


def _connected_components(adjacency: dict[int, set[int]]) -> list[list[int]]:
    remaining = set(adjacency)
    components = []
    while remaining:
        start = min(remaining)
        queue = deque([start])
        component = []
        remaining.remove(start)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbour in sorted(adjacency[current]):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
        components.append(component)
    return components


def _connection_end(
    current: int,
    neighbour: int,
    connections: dict[tuple[int, int], _Connection],
) -> int:
    low, high = sorted((current, neighbour))
    connection = connections[(low, high)]
    return connection.left_end if current == low else connection.right_end


def _order_linear_component(
    component: list[int],
    adjacency: dict[int, set[int]],
    connections: dict[tuple[int, int], _Connection],
    apertures: tuple[ApertureDescriptor, ...],
    settings: ClassifierSettings,
) -> tuple[list[int] | None, str | None]:
    # Only a simple path has an unambiguous geometric traversal. Branched,
    # cyclic, or same-edge connections deliberately fall back to x1 mappings.
    if len(component) == 1:
        return component, None
    if any(len(adjacency[index]) > 2 for index in component):
        return None, "BRANCHED_GRAPH"

    endpoints = [index for index in component if len(adjacency[index]) == 1]
    if len(endpoints) != 2:
        return None, "NON_LINEAR_GRAPH"

    start = min(
        endpoints,
        key=lambda index: _sort_key(
            apertures[index], settings.identity_quantisation_metres
        ),
    )
    ordered = []
    previous = None
    current = start
    while current is not None:
        ordered.append(current)
        candidates = adjacency[current] - (
            {previous} if previous is not None else set()
        )
        following = min(candidates) if candidates else None
        previous, current = current, following

    if len(ordered) != len(component):
        return None, "NON_LINEAR_GRAPH"

    for position in range(1, len(ordered) - 1):
        current = ordered[position]
        incoming_end = _connection_end(
            current, ordered[position - 1], connections
        )
        outgoing_end = _connection_end(
            current, ordered[position + 1], connections
        )
        if incoming_end == outgoing_end:
            return None, "AMBIGUOUS_PROXIMITY"
    return ordered, None


def _run_stable_key(
    run: Iterable[ApertureDescriptor],
    settings: ClassifierSettings,
) -> str:
    ordered_identities = sorted(
        _geometry_identity(aperture, settings.identity_quantisation_metres)
        for aperture in run
    )
    return repr(ordered_identities)


def partition_room_run(
    run_length: int,
    usable_room_sizes: Iterable[int],
    partition_seed: int,
    stable_run_identity: str,
) -> tuple[int, ...]:
    """Partition a run into deterministic contiguous x1 through x4 groups."""

    if run_length < 0:
        raise ValueError("run_length cannot be negative")
    if run_length == 0:
        return ()

    usable = tuple(
        sorted(
            {int(size) for size in usable_room_sizes if 1 <= int(size) <= 4}
        )
    )
    if 1 not in usable:
        raise ValueError("x1 must be usable before a run can be partitioned")
    if run_length <= 4 and run_length in usable:
        return (run_length,)

    # Hash each consumed offset independently so the same geometry, settings,
    # and seed reproduce the same contiguous partition after a stage reload.
    result = []
    consumed = 0
    while consumed < run_length:
        remaining = run_length - consumed
        candidates = tuple(size for size in usable if size <= remaining)
        choice_key = (
            f"{stable_run_identity}|seed={partition_seed}|"
            f"offset={consumed}|remaining={remaining}"
        )
        choice = candidates[_stable_integer(choice_key) % len(candidates)]
        result.append(choice)
        consumed += choice
    return tuple(result)
