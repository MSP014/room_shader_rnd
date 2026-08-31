"""Map accepted straight and corner aperture groups into shared room space."""

from __future__ import annotations

from .contracts import (
    ApertureDescriptor,
    ClassifierSettings,
    DerivedApertureMapping,
    Vector3,
)
from .topology import (
    _EPSILON,
    _add,
    _angle_degrees,
    _canonical_axis,
    _Connection,
    _connection_end,
    _cross,
    _derived_id,
    _dot,
    _length,
    _multiply,
    _normalise,
    _normalised_aperture_intervals,
    _subtract,
)

_CENTRAL_PARALLEL_TOLERANCE_DEGREES = 1.0


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

    # The longer leg becomes the primary facade. A deterministic traversal
    # resolves equal-length ties, so primitive ordering cannot flip the room.
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

    # Fit one physical rectangular box around both facade legs, retaining real
    # aperture spans and gaps for the front-exit mask consumed by MDL.
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

    # Primary windows map across room X; secondary windows map across room depth
    # while sharing the same origin, vertical axis, and room dimensions.
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
                physical_normal=_normalise(
                    _cross(
                        aperture.tangent_u_metres,
                        aperture.tangent_v_metres,
                    )
                ),
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
                physical_normal=_normalise(
                    _cross(
                        aperture.tangent_u_metres,
                        aperture.tangent_v_metres,
                    )
                ),
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
    # A single sharp turn uses the bounded corner contract. Straight and gently
    # faceted runs use one rigid mean basis across every physical aperture.
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

    room_axis_u, room_axis_v, _reference_indices = _shared_room_basis(
        group_apertures,
        up_axis,
    )
    room_normal = _normalise(_cross(room_axis_u, room_axis_v))
    # Project all physical bounds into the shared basis before deriving scale;
    # this prevents differently sized or angled windows from stretching a room.
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
    group_min_normal = min(corner[2] for corner in projected_corners)
    group_max_normal = max(corner[2] for corner in projected_corners)
    room_front_normal_coordinate = group_max_normal
    slice_start_depth = max(
        0.0,
        (room_front_normal_coordinate - group_min_normal) * room_scale[2],
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
            centre[2] - room_front_normal_coordinate,
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
                physical_normal=_normalise(
                    _cross(
                        aperture.tangent_u_metres,
                        aperture.tangent_v_metres,
                    )
                ),
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
    # Fallbacks preserve a usable x1 frame and explicit diagnostic state, but
    # mapping_valid remains false so the shader can expose degraded input.
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
        physical_normal=_normalise(_cross(tangent_u, tangent_v)),
        fallback_state=state,
    )
