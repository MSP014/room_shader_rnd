"""Build deterministic aperture adjacency and partition linear room runs."""

from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from statistics import median
from typing import Iterable

from .contracts import (
    ApertureDescriptor,
    ClassificationSummary,
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
        aperture.interior_set_id,
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


def _intervals_are_compatible(
    left: tuple[float, float],
    right: tuple[float, float],
    settings: ClassifierSettings,
) -> bool:
    """Compare two metre-space vertical spans against the row policy."""

    left_bottom, left_top = left
    right_bottom, right_top = right
    overlap = max(
        0.0,
        min(left_top, right_top) - max(left_bottom, right_bottom),
    )
    minimum_height = max(
        _EPSILON,
        min(left_top - left_bottom, right_top - right_bottom),
    )
    return (
        abs(left_bottom - right_bottom) <= settings.floor_tolerance_metres
        and overlap / minimum_height >= settings.minimum_vertical_overlap
    )


def _height_bands_are_compatible(
    left: ApertureDescriptor,
    right: ApertureDescriptor,
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> bool:
    return _intervals_are_compatible(
        _vertical_interval(left, up_axis),
        _vertical_interval(right, up_axis),
        settings,
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


@dataclass(frozen=True)
class _FacadeKey:
    """Identity of one coplanar orientation segment on one building row."""

    building_root: str
    row_id: int
    direction_bucket: int
    plane_component: int


@dataclass(frozen=True)
class _FacadeSequence:
    """Facade-local aperture ordering established before roomID filtering."""

    key: _FacadeKey
    aperture_indices: tuple[int, ...]
    local_pitch_metres: float | None


def _aperture_normal(aperture: ApertureDescriptor) -> Vector3:
    return _normalise(
        _cross(aperture.tangent_u_metres, aperture.tangent_v_metres)
    )


def _horizontal_vector(vector: Vector3, up_axis: Vector3) -> Vector3:
    vertical = _multiply(up_axis, _dot(vector, up_axis))
    return _normalise(_subtract(vector, vertical))


def _horizontal_coordinates(
    position: Vector3,
    up_axis: Vector3,
) -> tuple[float, float]:
    """Project metre-space positions for axis-aligned Y-up or Z-up stages."""

    if abs(up_axis[1]) > 0.5:
        return position[0], position[2]
    return position[0], position[1]


def _facade_angle_degrees(normal: Vector3, up_axis: Vector3) -> float:
    horizontal = _horizontal_vector(normal, up_axis)
    if abs(up_axis[1]) > 0.5:
        return math.degrees(math.atan2(horizontal[2], horizontal[0]))
    return math.degrees(math.atan2(horizontal[1], horizontal[0]))


def _facade_bucket(
    aperture: ApertureDescriptor,
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> int:
    requested_snap = max(settings.facade_angle_snap_degrees, _EPSILON)
    bucket_count = max(1, int(round(360.0 / requested_snap)))
    # Use an exact subdivision of the circle so arbitrary preference values do
    # not create an asymmetric bucket at the -180/+180 degree seam.
    bucket_width = 360.0 / bucket_count
    angle = _facade_angle_degrees(_aperture_normal(aperture), up_axis) % 360.0
    return int(round(angle / bucket_width)) % bucket_count


def _cluster_rows(
    aperture_indices: tuple[int, ...],
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> tuple[tuple[int, ...], ...]:
    """Cluster building-local floor bands without world-origin quantisation."""

    ordered = sorted(
        aperture_indices,
        key=lambda index: (
            _vertical_interval(apertures[index], up_axis)[0],
            _sort_key(apertures[index], settings.identity_quantisation_metres),
        ),
    )
    rows: list[list[int]] = []
    for index in ordered:
        for row in rows:
            anchor = apertures[row[0]]
            if _height_bands_are_compatible(
                anchor, apertures[index], up_axis, settings
            ):
                row.append(index)
                break
        else:
            rows.append([index])
    return tuple(tuple(row) for row in rows)


def _sequence_local_pitch(
    aperture_indices: tuple[int, ...],
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
) -> float | None:
    spacings = [
        _horizontal_distance(
            apertures[left].centre_metres,
            apertures[right].centre_metres,
            up_axis,
        )
        for left, right in zip(aperture_indices, aperture_indices[1:])
    ]
    # One isolated pair cannot define its own acceptance threshold. It falls
    # back to a scale derived from the two aperture widths instead.
    return float(median(spacings)) if len(spacings) >= 2 else None


def _mean_horizontal_normal(
    aperture_indices: tuple[int, ...],
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
) -> Vector3:
    normals = tuple(
        _horizontal_vector(_aperture_normal(apertures[index]), up_axis)
        for index in aperture_indices
    )
    return _normalise(
        (
            sum(normal[0] for normal in normals),
            sum(normal[1] for normal in normals),
            sum(normal[2] for normal in normals),
        )
    )


def _facade_plane_groups(
    facade_indices: tuple[int, ...],
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> tuple[tuple[int, ...], ...]:
    """Separate parallel facade bodies before local u ordering.

    Identity quantisation is reused as a stable plane-offset tolerance instead
    of introducing a Building-specific distance. A curved or noisy facade may
    split into several components; the mutual-nearest pass reconnects physical
    neighbours across those components.
    """

    representative_normal = _mean_horizontal_normal(
        facade_indices,
        apertures,
        up_axis,
    )
    plane_quantum = max(settings.identity_quantisation_metres, _EPSILON)
    groups: dict[int, list[int]] = {}
    for index in facade_indices:
        plane_offset = _dot(
            apertures[index].centre_metres, representative_normal
        )
        groups.setdefault(_quantise(plane_offset, plane_quantum), []).append(
            index
        )
    return tuple(tuple(indices) for _key, indices in sorted(groups.items()))


def _build_facade_sequence(
    key: _FacadeKey,
    aperture_indices: tuple[int, ...],
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> _FacadeSequence:
    representative_normal = _mean_horizontal_normal(
        aperture_indices,
        apertures,
        up_axis,
    )
    facade_u = _normalise(_cross(up_axis, representative_normal))
    ordered = tuple(
        sorted(
            aperture_indices,
            key=lambda index: (
                _dot(apertures[index].centre_metres, facade_u),
                _sort_key(
                    apertures[index],
                    settings.identity_quantisation_metres,
                ),
            ),
        )
    )
    return _FacadeSequence(
        key=key,
        aperture_indices=ordered,
        local_pitch_metres=_sequence_local_pitch(
            ordered,
            apertures,
            up_axis,
        ),
    )


def _row_facade_sequences(
    building_root: str,
    row_id: int,
    row_indices: tuple[int, ...],
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> tuple[_FacadeSequence, ...]:
    by_direction: dict[int, list[int]] = {}
    for index in row_indices:
        direction_bucket = _facade_bucket(apertures[index], up_axis, settings)
        by_direction.setdefault(direction_bucket, []).append(index)

    sequences = []
    for direction_bucket, direction_indices in sorted(by_direction.items()):
        plane_groups = _facade_plane_groups(
            tuple(direction_indices),
            apertures,
            up_axis,
            settings,
        )
        for plane_component, plane_indices in enumerate(plane_groups):
            key = _FacadeKey(
                building_root=building_root,
                row_id=row_id,
                direction_bucket=direction_bucket,
                plane_component=plane_component,
            )
            sequences.append(
                _build_facade_sequence(
                    key,
                    plane_indices,
                    apertures,
                    up_axis,
                    settings,
                )
            )
    return tuple(sequences)


def _facade_sequences(
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> tuple[_FacadeSequence, ...]:
    """Build deterministic local facade orderings for every building row."""

    by_building: dict[str, list[int]] = {}
    for index, aperture in enumerate(apertures):
        by_building.setdefault(aperture.building_root, []).append(index)

    sequences: list[_FacadeSequence] = []
    for building_root, building_indices in sorted(by_building.items()):
        rows = _cluster_rows(
            tuple(building_indices), apertures, up_axis, settings
        )
        for row_id, row_indices in enumerate(rows):
            sequences.extend(
                _row_facade_sequences(
                    building_root,
                    row_id,
                    row_indices,
                    apertures,
                    up_axis,
                    settings,
                )
            )
    return tuple(sequences)


def _spacing_is_local(
    left: ApertureDescriptor,
    right: ApertureDescriptor,
    connection: _Connection,
    local_pitch_metres: float | None,
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> bool:
    ratio = max(settings.maximum_local_spacing_ratio, _EPSILON)
    if local_pitch_metres is not None:
        centre_spacing = _horizontal_distance(
            left.centre_metres,
            right.centre_metres,
            up_axis,
        )
        return centre_spacing <= local_pitch_metres * ratio
    width_scale = max(
        _length(left.tangent_u_metres),
        _length(right.tangent_u_metres),
        _EPSILON,
    )
    return connection.distance <= width_scale * ratio


def _record_connection(
    left_index: int,
    right_index: int,
    connection: _Connection,
    adjacency: dict[int, set[int]],
    connections: dict[tuple[int, int], _Connection],
) -> None:
    low, high = sorted((left_index, right_index))
    if left_index == low:
        oriented = connection
    else:
        oriented = _Connection(
            connection.right_end,
            connection.left_end,
            connection.distance,
        )
    adjacency[low].add(high)
    adjacency[high].add(low)
    connections[(low, high)] = oriented


def _transition_candidates(
    row_sequences: tuple[_FacadeSequence, ...],
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> tuple[tuple[int, int, _Connection], ...]:
    """Return physical mutual-nearest pairs across facade components.

    Candidates deliberately ignore roomID. The caller applies room identity
    only after every physical window has competed for nearest-neighbour status;
    this prevents equal IDs from jumping over an intervening different room.
    """

    facade_by_aperture = {
        index: sequence.key
        for sequence in row_sequences
        for index in sequence.aperture_indices
    }
    aperture_indices = tuple(sorted(facade_by_aperture))
    normals = {
        index: _aperture_normal(apertures[index]) for index in aperture_indices
    }
    vertical_intervals = {
        index: _vertical_interval(apertures[index], up_axis)
        for index in aperture_indices
    }
    endpoint_positions = {
        (index, end): _horizontal_coordinates(position, up_axis)
        for index in aperture_indices
        for end, position in enumerate(_aperture_edges(apertures[index]))
    }
    maximum_turn = _clamp(settings.maximum_turn_degrees, 0.0, 180.0)
    minimum_normal_dot = math.cos(math.radians(maximum_turn))
    best: dict[tuple[int, int], tuple[float, int, int]] = {}

    def retain_nearest(
        endpoint: tuple[int, int],
        candidate: tuple[float, int, int],
    ) -> None:
        previous = best.get(endpoint)
        if previous is None or candidate < previous:
            best[endpoint] = candidate

    # Height and normal predicates belong to an aperture pair, while only the
    # four endpoint distances vary. Evaluate those shared predicates once.
    for position, left_index in enumerate(aperture_indices):
        for right_index in aperture_indices[position + 1 :]:
            if (
                facade_by_aperture[left_index]
                == facade_by_aperture[right_index]
            ):
                continue
            if not _intervals_are_compatible(
                vertical_intervals[left_index],
                vertical_intervals[right_index],
                settings,
            ):
                continue
            if (
                _dot(normals[left_index], normals[right_index])
                < minimum_normal_dot
            ):
                continue
            for left_end in (0, 1):
                left_position = endpoint_positions[(left_index, left_end)]
                for right_end in (0, 1):
                    right_position = endpoint_positions[
                        (right_index, right_end)
                    ]
                    delta_u = left_position[0] - right_position[0]
                    delta_v = left_position[1] - right_position[1]
                    distance_squared = delta_u * delta_u + delta_v * delta_v
                    retain_nearest(
                        (left_index, left_end),
                        (distance_squared, right_index, right_end),
                    )
                    retain_nearest(
                        (right_index, right_end),
                        (distance_squared, left_index, left_end),
                    )

    result = []
    seen_pairs = set()
    for endpoint, candidate in sorted(best.items()):
        distance_squared, other_index, other_end = candidate
        reciprocal = best.get((other_index, other_end))
        if reciprocal is None or reciprocal[1:] != endpoint:
            continue
        pair = tuple(sorted((endpoint[0], other_index)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        left_index, right_index = pair
        distance = math.sqrt(distance_squared)
        if left_index == endpoint[0]:
            connection = _Connection(endpoint[1], other_end, distance)
        else:
            connection = _Connection(other_end, endpoint[1], distance)
        result.append((left_index, right_index, connection))
    return tuple(result)


def _build_adjacency_graph(
    apertures: tuple[ApertureDescriptor, ...],
    up_axis: Vector3,
    settings: ClassifierSettings,
) -> tuple[
    dict[int, set[int]],
    dict[tuple[int, int], _Connection],
    ClassificationSummary,
]:
    """Build row- and facade-local adjacency before grouping by roomID."""

    adjacency = {index: set() for index in range(len(apertures))}
    connections: dict[tuple[int, int], _Connection] = {}
    sequences = _facade_sequences(apertures, up_axis, settings)
    pitch_by_aperture = {
        index: sequence.local_pitch_metres
        for sequence in sequences
        for index in sequence.aperture_indices
    }
    straight_candidates = 0
    transition_candidates = 0
    accepted_straight = 0
    accepted_transition = 0
    rejected_room_id = 0
    rejected_interior_set = 0
    rejected_spacing = 0

    for sequence in sequences:
        for left_index, right_index in zip(
            sequence.aperture_indices,
            sequence.aperture_indices[1:],
        ):
            straight_candidates += 1
            left = apertures[left_index]
            right = apertures[right_index]
            if left.room_id != right.room_id:
                rejected_room_id += 1
                continue
            if left.interior_set_id != right.interior_set_id:
                rejected_interior_set += 1
                continue
            connection = _connection_between(left, right, up_axis)
            if not _spacing_is_local(
                left,
                right,
                connection,
                sequence.local_pitch_metres,
                up_axis,
                settings,
            ):
                rejected_spacing += 1
                continue
            _record_connection(
                left_index,
                right_index,
                connection,
                adjacency,
                connections,
            )
            accepted_straight += 1

    rows: dict[tuple[str, int], list[_FacadeSequence]] = {}
    for sequence in sequences:
        row_key = (sequence.key.building_root, sequence.key.row_id)
        rows.setdefault(row_key, []).append(sequence)
    for row_sequences in rows.values():
        for left_index, right_index, connection in _transition_candidates(
            tuple(row_sequences), apertures, up_axis, settings
        ):
            transition_candidates += 1
            pair = (left_index, right_index)
            if pair in connections:
                continue
            left = apertures[left_index]
            right = apertures[right_index]
            if left.room_id != right.room_id:
                rejected_room_id += 1
                continue
            if left.interior_set_id != right.interior_set_id:
                rejected_interior_set += 1
                continue
            local_pitches = tuple(
                pitch
                for pitch in (
                    pitch_by_aperture[left_index],
                    pitch_by_aperture[right_index],
                )
                if pitch is not None
            )
            local_pitch = max(local_pitches) if local_pitches else None
            if not _spacing_is_local(
                left,
                right,
                connection,
                local_pitch,
                up_axis,
                settings,
            ):
                rejected_spacing += 1
                continue
            _record_connection(
                left_index,
                right_index,
                connection,
                adjacency,
                connections,
            )
            accepted_transition += 1

    local_pitches = tuple(
        sequence.local_pitch_metres
        for sequence in sequences
        if sequence.local_pitch_metres is not None
    )
    summary = ClassificationSummary(
        building_count=len({aperture.building_root for aperture in apertures}),
        row_count=len(rows),
        facade_count=len(sequences),
        straight_candidate_count=straight_candidates,
        transition_candidate_count=transition_candidates,
        accepted_straight_edge_count=accepted_straight,
        accepted_transition_edge_count=accepted_transition,
        rejected_room_id_edge_count=rejected_room_id,
        rejected_interior_set_edge_count=rejected_interior_set,
        rejected_spacing_edge_count=rejected_spacing,
        local_pitch_min_metres=(min(local_pitches) if local_pitches else None),
        local_pitch_max_metres=(max(local_pitches) if local_pitches else None),
    )
    return adjacency, connections, summary


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
