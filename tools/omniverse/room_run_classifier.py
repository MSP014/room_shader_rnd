"""Deterministically classify flat Room Map apertures into linear room runs.

This module contains no Kit or OpenUSD runtime dependency.  The R&D runtime
adapter extracts aperture descriptors from a composed stage, delegates the
geometric decision to this module, and authors the returned direct mapping as
ephemeral ORMS primvars.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable

Vector3 = tuple[float, float, float]
Float4 = tuple[float, float, float, float]

CLASSIFIER_CONTRACT_VERSION = "krm93_exact_corner_mask_origin_v15"

_EPSILON = 1.0e-8
_DERIVED_ID_LIMIT = 2_147_483_647
_CENTRAL_PARALLEL_TOLERANCE_DEGREES = 1.0


@dataclass(frozen=True)
class ApertureDescriptor:
    """Geometry and identity required to classify one flat aperture."""

    key: str
    prim_path: str
    face_index: int
    building_root: str
    room_id: int
    centre_metres: Vector3
    tangent_u_metres: Vector3
    tangent_v_metres: Vector3


@dataclass(frozen=True)
class ClassifierSettings:
    """Pure classifier settings expressed in metres and degrees."""

    enabled_room_sizes: frozenset[int] = frozenset({1, 2, 3, 4})
    available_room_sizes: frozenset[int] = frozenset({1, 2, 3, 4})
    partition_seed: int = 0
    edge_gap_tolerance_metres: float = 0.65
    floor_tolerance_metres: float = 0.25
    minimum_vertical_overlap: float = 0.5
    maximum_turn_degrees: float = 100.0
    corner_turn_threshold_degrees: float = 60.0
    identity_quantisation_metres: float = 0.001


@dataclass(frozen=True)
class RoomGroup:
    """One bounded room selected from an ordered aperture run.

    For a corner, ``room_size`` and ``room_depth_size`` describe its canonical
    max-by-min footprint.  The derived mappings then swap those dimensions per
    facade leg: a 4x1 corner exposes an x4/depth-1 portal on its long facade
    and an x1/depth-4 portal on its short facade.
    """

    stable_key: str
    derived_id: int
    room_id: int
    building_root: str
    aperture_keys: tuple[str, ...]
    room_size: int
    room_depth_size: int = 1


@dataclass(frozen=True)
class DerivedApertureMapping:
    """Physical local-roomUV embedding into one fixed logical room frame."""

    aperture_key: str
    prim_path: str
    face_index: int
    group_key: str
    group_id: int
    room_size: int
    room_depth_size: int
    atlas_size: int
    room_axis_u: Vector3
    room_axis_v: Vector3
    room_scale: Vector3
    map_origin: Vector3
    map_axis_u: Vector3
    map_axis_v: Vector3
    mapping_valid: bool
    primary_aperture_min_u: Float4 = (0.0, -1.0, -1.0, -1.0)
    primary_aperture_max_u: Float4 = (1.0, -1.0, -1.0, -1.0)
    aperture_mask_offset_u: float = 0.0
    slice_start_depth: float = 0.0
    fallback_state: str | None = None


@dataclass(frozen=True)
class ClassifierDiagnostic:
    """A structured degraded or fallback state for the runtime logger."""

    state: str
    prim_path: str
    details: tuple[tuple[str, object], ...]


@dataclass(frozen=True)
class ClassificationResult:
    """Complete deterministic output of one classifier pass."""

    mappings: tuple[DerivedApertureMapping, ...]
    groups: tuple[RoomGroup, ...]
    diagnostics: tuple[ClassifierDiagnostic, ...]


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


def _shared_room_basis(
    group_apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
) -> tuple[Vector3, Vector3, tuple[int, ...]]:
    """Return one rigid room basis shared by every aperture in a group.

    An odd group follows its central aperture.  An even group follows its two
    central apertures when they are parallel within the export tolerance;
    otherwise it uses the aligned mean normal of the whole run.  Rebuilding
    the orthonormal frame from that normal keeps the virtual back and side
    walls rigid while the physical aperture planes turn around a bay facade.
    """

    aligned_axes_v = tuple(
        _multiply(
            _normalise(aperture.tangent_v_metres),
            1 if _dot(aperture.tangent_v_metres, up_axis) >= 0.0 else -1,
        )
        for aperture in group_apertures
    )
    aligned_normals = tuple(
        _normalise(_cross(_normalise(aperture.tangent_u_metres), axis_v))
        for aperture, axis_v in zip(group_apertures, aligned_axes_v)
    )

    group_size = len(group_apertures)
    if group_size % 2 == 1:
        selected = (group_size // 2,)
    else:
        central = (group_size // 2 - 1, group_size // 2)
        selected = (
            central
            if _angle_degrees(
                aligned_normals[central[0]],
                aligned_normals[central[1]],
            )
            <= _CENTRAL_PARALLEL_TOLERANCE_DEGREES
            else tuple(range(group_size))
        )

    normal_sum = (0.0, 0.0, 0.0)
    vertical_sum = (0.0, 0.0, 0.0)
    for index in selected:
        normal_sum = _add(normal_sum, aligned_normals[index])
        vertical_sum = _add(vertical_sum, aligned_axes_v[index])

    shared_normal = _normalise(normal_sum)
    shared_vertical_seed = _normalise(vertical_sum)
    if _length(shared_normal) <= _EPSILON:
        shared_normal = aligned_normals[group_size // 2]
    if _length(shared_vertical_seed) <= _EPSILON:
        shared_vertical_seed = up_axis

    shared_axis_u = _normalise(_cross(shared_vertical_seed, shared_normal))
    if _length(shared_axis_u) <= _EPSILON:
        shared_axis_u = _normalise(
            group_apertures[group_size // 2].tangent_u_metres
        )
    shared_axis_v = _normalise(_cross(shared_normal, shared_axis_u))
    return shared_axis_u, shared_axis_v, selected


def _basis_coordinates(
    vector: Vector3,
    axis_u: Vector3,
    axis_v: Vector3,
    normal: Vector3,
) -> Vector3:
    return (
        _dot(vector, axis_u),
        _dot(vector, axis_v),
        _dot(vector, normal),
    )


def _corner_turn_positions(
    group_apertures: tuple[ApertureDescriptor, ...],
    threshold_degrees: float,
) -> tuple[int, ...]:
    """Return split indices immediately after every sharp facade turn."""

    normals = tuple(
        _cross(
            aperture.tangent_u_metres,
            aperture.tangent_v_metres,
        )
        for aperture in group_apertures
    )
    return tuple(
        index
        for index, (left, right) in enumerate(
            zip(normals, normals[1:]),
            start=1,
        )
        if _angle_degrees(left, right) >= threshold_degrees
    )


def _corner_group_mappings(
    group_apertures: tuple[ApertureDescriptor, ...],
    group_indices: tuple[int, ...],
    connections: dict[tuple[int, int], _Connection],
    up_axis: Vector3,
    group_key: str,
    split_index: int,
) -> tuple[DerivedApertureMapping, ...]:
    """Embed both corner legs on two boundaries of one fixed room box.

    The longer leg defines the stable world-space width axis; ties use the
    first deterministic traversal leg.  The perpendicular leg lies on the
    connected side boundary and spans the common depth.  Atlas family choice
    remains per leg, but it never changes the room basis.
    """

    first_indices = group_indices[:split_index]
    second_indices = group_indices[split_index:]

    aperture_by_index = {
        index: aperture
        for index, aperture in zip(group_indices, group_apertures)
    }
    primary_is_first = len(first_indices) >= len(second_indices)
    primary_indices = first_indices if primary_is_first else second_indices
    secondary_indices = second_indices if primary_is_first else first_indices
    primary_apertures = tuple(
        aperture_by_index[index] for index in primary_indices
    )
    secondary_apertures = tuple(
        aperture_by_index[index] for index in secondary_indices
    )
    room_axis_u, room_axis_v, _reference_indices = _shared_room_basis(
        primary_apertures,
        up_axis,
    )
    room_normal = _normalise(_cross(room_axis_u, room_axis_v))
    room_interior_axis = _multiply(room_normal, -1.0)
    primary_centre = _multiply(
        tuple(
            sum(
                aperture.centre_metres[component]
                for aperture in primary_apertures
            )
            for component in range(3)
        ),
        1.0 / len(primary_apertures),
    )
    secondary_centre = _multiply(
        tuple(
            sum(
                aperture.centre_metres[component]
                for aperture in secondary_apertures
            )
            for component in range(3)
        ),
        1.0 / len(secondary_apertures),
    )
    if (
        _dot(
            _subtract(secondary_centre, primary_centre),
            room_interior_axis,
        )
        < 0.0
    ):
        room_axis_u = _multiply(room_axis_u, -1.0)
        room_normal = _normalise(_cross(room_axis_u, room_axis_v))
        room_interior_axis = _multiply(room_normal, -1.0)

    primary_u_endpoints = tuple(
        _dot(aperture.centre_metres, room_axis_u)
        + sign * 0.5 * _dot(aperture.tangent_u_metres, room_axis_u)
        for aperture in primary_apertures
        for sign in (-1.0, 1.0)
    )
    group_min_u = min(primary_u_endpoints)
    group_max_u = max(primary_u_endpoints)
    group_centre_u = (group_min_u + group_max_u) * 0.5
    group_width = max(group_max_u - group_min_u, _EPSILON)
    primary_aperture_min_u, primary_aperture_max_u = (
        _normalised_aperture_intervals(
            primary_apertures,
            room_axis_u,
            group_min_u,
            group_width,
        )
    )

    all_v_endpoints = tuple(
        _dot(aperture.centre_metres, room_axis_v)
        + sign * 0.5 * _dot(aperture.tangent_v_metres, room_axis_v)
        for aperture in group_apertures
        for sign in (-1.0, 1.0)
    )
    group_min_v = min(all_v_endpoints)
    group_max_v = max(all_v_endpoints)
    group_centre_v = (group_min_v + group_max_v) * 0.5
    group_height = max(group_max_v - group_min_v, _EPSILON)

    primary_plane_coordinate = sum(
        _dot(aperture.centre_metres, room_interior_axis)
        for aperture in primary_apertures
    ) / len(primary_apertures)
    secondary_depth_endpoints = tuple(
        _dot(aperture.centre_metres, room_interior_axis)
        + sign * 0.5 * _dot(aperture.tangent_u_metres, room_interior_axis)
        - primary_plane_coordinate
        for aperture in secondary_apertures
        for sign in (-1.0, 1.0)
    )
    group_max_depth = max(secondary_depth_endpoints)
    group_depth = max(group_max_depth, _EPSILON)

    primary_corner_index = (
        primary_indices[-1] if primary_is_first else primary_indices[0]
    )
    secondary_corner_index = (
        secondary_indices[0] if primary_is_first else secondary_indices[-1]
    )
    primary_corner = aperture_by_index[primary_corner_index]
    connected_end = _connection_end(
        primary_corner_index,
        secondary_corner_index,
        connections,
    )
    connected_u = _dot(primary_corner.centre_metres, room_axis_u) + (
        float(connected_end) - 0.5
    ) * _dot(primary_corner.tangent_u_metres, room_axis_u)
    side_coordinate = (
        -0.5 * group_width
        if connected_u < group_centre_u
        else 0.5 * group_width
    )
    physical_side_coordinate = (
        sum(
            _dot(aperture.centre_metres, room_axis_u)
            for aperture in secondary_apertures
        )
        / len(secondary_apertures)
        - group_centre_u
    )
    aperture_mask_offset_u = physical_side_coordinate - side_coordinate

    room_size = len(primary_indices)
    room_depth_size = len(secondary_indices)
    room_scale = (
        room_size / group_width,
        1.0 / group_height,
        room_depth_size / group_depth,
    )
    group_id = _derived_id(group_key)

    mappings = []
    for aperture_index in primary_indices:
        aperture = aperture_by_index[aperture_index]
        axis_u = _dot(aperture.tangent_u_metres, room_axis_u)
        axis_v = _dot(aperture.tangent_v_metres, room_axis_v)
        mappings.append(
            DerivedApertureMapping(
                aperture_key=aperture.key,
                prim_path=aperture.prim_path,
                face_index=aperture.face_index,
                group_key=group_key,
                group_id=group_id,
                room_size=room_size,
                room_depth_size=room_depth_size,
                atlas_size=len(primary_indices),
                room_axis_u=room_axis_u,
                room_axis_v=room_axis_v,
                room_scale=room_scale,
                map_origin=(
                    _dot(aperture.centre_metres, room_axis_u)
                    - 0.5 * axis_u
                    - group_centre_u,
                    _dot(aperture.centre_metres, room_axis_v)
                    - 0.5 * axis_v
                    - group_centre_v,
                    0.0,
                ),
                map_axis_u=(axis_u, 0.0, 0.0),
                map_axis_v=(0.0, axis_v, 0.0),
                mapping_valid=True,
                primary_aperture_min_u=primary_aperture_min_u,
                primary_aperture_max_u=primary_aperture_max_u,
            )
        )

    for aperture_index in secondary_indices:
        aperture = aperture_by_index[aperture_index]
        depth_origin = (
            _dot(
                _subtract(
                    aperture.centre_metres,
                    _multiply(aperture.tangent_u_metres, 0.5),
                ),
                room_interior_axis,
            )
            - primary_plane_coordinate
        )
        depth_axis = _dot(
            aperture.tangent_u_metres,
            room_interior_axis,
        )
        axis_v = _dot(aperture.tangent_v_metres, room_axis_v)
        mappings.append(
            DerivedApertureMapping(
                aperture_key=aperture.key,
                prim_path=aperture.prim_path,
                face_index=aperture.face_index,
                group_key=group_key,
                group_id=group_id,
                room_size=room_size,
                room_depth_size=room_depth_size,
                atlas_size=len(secondary_indices),
                room_axis_u=room_axis_u,
                room_axis_v=room_axis_v,
                room_scale=room_scale,
                map_origin=(
                    side_coordinate,
                    _dot(aperture.centre_metres, room_axis_v)
                    - 0.5 * axis_v
                    - group_centre_v,
                    -depth_origin,
                ),
                map_axis_u=(0.0, 0.0, -depth_axis),
                map_axis_v=(0.0, axis_v, 0.0),
                mapping_valid=True,
                primary_aperture_min_u=primary_aperture_min_u,
                primary_aperture_max_u=primary_aperture_max_u,
                aperture_mask_offset_u=aperture_mask_offset_u,
            )
        )
    return tuple(mappings)


def _group_mappings(
    group_apertures: tuple[ApertureDescriptor, ...],
    group_indices: tuple[int, ...],
    connections: dict[tuple[int, int], _Connection],
    up_axis: Vector3,
    group_key: str,
    room_size: int,
    room_depth_size: int,
    settings: ClassifierSettings,
) -> tuple[DerivedApertureMapping, ...]:
    corner_turns = _corner_turn_positions(
        group_apertures, settings.corner_turn_threshold_degrees
    )
    if len(corner_turns) == 1:
        return _corner_group_mappings(
            group_apertures,
            group_indices,
            connections,
            up_axis,
            group_key,
            corner_turns[0],
        )

    room_axis_u, room_axis_v, reference_indices = _shared_room_basis(
        group_apertures,
        up_axis,
    )
    room_normal = _normalise(_cross(room_axis_u, room_axis_v))
    projected_centres = tuple(
        _basis_coordinates(
            aperture.centre_metres,
            room_axis_u,
            room_axis_v,
            room_normal,
        )
        for aperture in group_apertures
    )
    projected_axes_u = tuple(
        _basis_coordinates(
            aperture.tangent_u_metres,
            room_axis_u,
            room_axis_v,
            room_normal,
        )
        for aperture in group_apertures
    )
    projected_axes_v = tuple(
        _basis_coordinates(
            aperture.tangent_v_metres,
            room_axis_u,
            room_axis_v,
            room_normal,
        )
        for aperture in group_apertures
    )
    projected_corners = tuple(
        _add(
            centre,
            _add(
                _multiply(axis_u, sign_u * 0.5),
                _multiply(axis_v, sign_v * 0.5),
            ),
        )
        for centre, axis_u, axis_v in zip(
            projected_centres,
            projected_axes_u,
            projected_axes_v,
        )
        for sign_u in (-1.0, 1.0)
        for sign_v in (-1.0, 1.0)
    )
    group_min_u = min(corner[0] for corner in projected_corners)
    group_max_u = max(corner[0] for corner in projected_corners)
    group_min_v = min(corner[1] for corner in projected_corners)
    group_max_v = max(corner[1] for corner in projected_corners)
    group_centre_u = (group_min_u + group_max_u) * 0.5
    group_centre_v = (group_min_v + group_max_v) * 0.5
    group_width = max(group_max_u - group_min_u, _EPSILON)
    group_height = max(group_max_v - group_min_v, _EPSILON)
    primary_aperture_min_u, primary_aperture_max_u = (
        _normalised_aperture_intervals(
            group_apertures,
            room_axis_u,
            group_min_u,
            group_width,
        )
    )
    room_scale = (
        room_size / group_width,
        1.0 / group_height,
        1.0 / group_height,
    )
    reference_normal_coordinate = sum(
        projected_centres[index][2] for index in reference_indices
    ) / len(reference_indices)
    group_min_normal = min(corner[2] for corner in projected_corners)
    slice_start_depth = max(
        0.0,
        (reference_normal_coordinate - group_min_normal) * room_scale[2],
    )
    if slice_start_depth <= _EPSILON:
        slice_start_depth = 0.0
    group_id = _derived_id(group_key)

    mappings = []
    for aperture, centre, axis_u, axis_v in zip(
        group_apertures,
        projected_centres,
        projected_axes_u,
        projected_axes_v,
    ):
        relative_centre = (
            centre[0] - group_centre_u,
            centre[1] - group_centre_v,
            centre[2] - reference_normal_coordinate,
        )
        map_origin = _subtract(
            _subtract(relative_centre, _multiply(axis_u, 0.5)),
            _multiply(axis_v, 0.5),
        )

        mappings.append(
            DerivedApertureMapping(
                aperture_key=aperture.key,
                prim_path=aperture.prim_path,
                face_index=aperture.face_index,
                group_key=group_key,
                group_id=group_id,
                room_size=room_size,
                room_depth_size=room_depth_size,
                atlas_size=room_size,
                room_axis_u=room_axis_u,
                room_axis_v=room_axis_v,
                room_scale=room_scale,
                map_origin=map_origin,
                map_axis_u=axis_u,
                map_axis_v=axis_v,
                mapping_valid=True,
                primary_aperture_min_u=primary_aperture_min_u,
                primary_aperture_max_u=primary_aperture_max_u,
                slice_start_depth=slice_start_depth,
            )
        )
    return tuple(mappings)


def _fallback_mapping(
    aperture: ApertureDescriptor,
    state: str,
) -> DerivedApertureMapping:
    tangent_u = _canonical_axis(aperture.tangent_u_metres)
    tangent_v = _canonical_axis(aperture.tangent_v_metres)
    if _length(tangent_u) <= _EPSILON:
        tangent_u = (1.0, 0.0, 0.0)
    if _length(tangent_v) <= _EPSILON:
        tangent_v = (0.0, 1.0, 0.0)
    group_key = (
        f"fallback|{aperture.building_root}|{aperture.room_id}|{aperture.key}"
    )
    return DerivedApertureMapping(
        aperture_key=aperture.key,
        prim_path=aperture.prim_path,
        face_index=aperture.face_index,
        group_key=group_key,
        group_id=_derived_id(group_key),
        room_size=1,
        room_depth_size=1,
        atlas_size=1,
        room_axis_u=tangent_u,
        room_axis_v=tangent_v,
        room_scale=(1.0, 1.0, 1.0),
        map_origin=(0.0, 0.0, 0.0),
        map_axis_u=(1.0, 0.0, 0.0),
        map_axis_v=(0.0, 1.0, 0.0),
        mapping_valid=False,
        fallback_state=state,
    )


def classify_apertures(
    apertures: Iterable[ApertureDescriptor],
    settings: ClassifierSettings = ClassifierSettings(),
    *,
    up_axis: str = "Y",
) -> ClassificationResult:
    """Classify apertures without relying on input or USD primitive order."""

    up = _up_vector(up_axis)
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

    usable_sizes = (
        set(settings.enabled_room_sizes)
        & set(settings.available_room_sizes)
        & {1, 2, 3, 4}
    )
    if 1 not in usable_sizes:
        for aperture in valid_apertures:
            mappings.append(_fallback_mapping(aperture, "MISSING_X1_ATLAS"))
            diagnostics.append(
                ClassifierDiagnostic(
                    state="MISSING_X1_ATLAS",
                    prim_path=aperture.prim_path,
                    details=(("aperture", aperture.key),),
                )
            )
        return ClassificationResult(
            mappings=tuple(
                sorted(mappings, key=lambda item: item.aperture_key)
            ),
            groups=(),
            diagnostics=tuple(diagnostics),
        )

    buckets: dict[tuple[str, int], list[ApertureDescriptor]] = defaultdict(
        list
    )
    for aperture in valid_apertures:
        buckets[(aperture.building_root, aperture.room_id)].append(aperture)

    for (building_root, room_id), bucket in sorted(buckets.items()):
        bucket_tuple = tuple(
            sorted(
                bucket,
                key=lambda aperture: _sort_key(
                    aperture, settings.identity_quantisation_metres
                ),
            )
        )
        adjacency = {index: set() for index in range(len(bucket_tuple))}
        connections = {}
        for left_index, left in enumerate(bucket_tuple):
            for right_index in range(left_index + 1, len(bucket_tuple)):
                right = bucket_tuple[right_index]
                adjacent, connection = _are_adjacent(
                    left,
                    right,
                    up,
                    settings,
                )
                if not adjacent:
                    continue
                adjacency[left_index].add(right_index)
                adjacency[right_index].add(left_index)
                connections[(left_index, right_index)] = connection

        for component in _connected_components(adjacency):
            ordered_indices, fallback_state = _order_linear_component(
                component,
                adjacency,
                connections,
                bucket_tuple,
                settings,
            )
            if ordered_indices is None:
                for index in component:
                    aperture = bucket_tuple[index]
                    mappings.append(
                        _fallback_mapping(
                            aperture, fallback_state or "INVALID_GRAPH"
                        )
                    )
                diagnostics.append(
                    ClassifierDiagnostic(
                        state=fallback_state or "INVALID_GRAPH",
                        prim_path=bucket_tuple[component[0]].prim_path,
                        details=(
                            ("building_root", building_root),
                            ("room_id", room_id),
                            ("aperture_count", len(component)),
                        ),
                    )
                )
                continue

            run = tuple(bucket_tuple[index] for index in ordered_indices)
            run_key = _run_stable_key(run, settings)
            corner_turns = _corner_turn_positions(
                run,
                settings.corner_turn_threshold_degrees,
            )
            if len(corner_turns) > 1:
                for index in ordered_indices:
                    mappings.append(
                        _fallback_mapping(
                            bucket_tuple[index], "MULTI_CORNER_LAYOUT"
                        )
                    )
                diagnostics.append(
                    ClassifierDiagnostic(
                        state="MULTI_CORNER_LAYOUT",
                        prim_path=run[0].prim_path,
                        details=(
                            ("building_root", building_root),
                            ("room_id", room_id),
                            ("aperture_count", len(run)),
                            ("corner_count", len(corner_turns)),
                        ),
                    )
                )
                continue

            group_specs = []
            if corner_turns:
                split_index = corner_turns[0]
                leg_sizes = (split_index, len(run) - split_index)
                corner_room_size = max(leg_sizes)
                if max(leg_sizes) <= 4 and set(leg_sizes) <= usable_sizes:
                    group_specs.append(
                        (
                            run,
                            tuple(ordered_indices),
                            corner_room_size,
                            min(leg_sizes),
                        )
                    )
                else:
                    for leg_number, (leg_start, leg_end) in enumerate(
                        ((0, split_index), (split_index, len(run)))
                    ):
                        leg = run[leg_start:leg_end]
                        leg_indices = tuple(ordered_indices[leg_start:leg_end])
                        partitions = partition_room_run(
                            len(leg),
                            usable_sizes,
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
                    usable_sizes,
                    settings.partition_seed,
                    run_key,
                )
                offset = 0
                for group_size in partitions:
                    group_specs.append(
                        (
                            run[offset : offset + group_size],
                            tuple(
                                ordered_indices[offset : offset + group_size]
                            ),
                            group_size,
                            1,
                        )
                    )
                    offset += group_size

            for group_number, (
                group_apertures,
                group_indices,
                group_size,
                group_depth_size,
            ) in enumerate(group_specs):
                group_key = (
                    f"{run_key}|group={group_number}|width={group_size}|"
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
    )
