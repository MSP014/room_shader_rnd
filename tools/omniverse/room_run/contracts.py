"""Define the stable plain-data contract of shared-room classification."""

from __future__ import annotations

from dataclasses import dataclass

Vector3 = tuple[float, float, float]
Float4 = tuple[float, float, float, float]

CLASSIFIER_CONTRACT_VERSION = "shared_room_runtime_v46"

_EPSILON = 1.0e-8
_DERIVED_ID_LIMIT = 2_147_483_647
_CENTRAL_PARALLEL_TOLERANCE_DEGREES = 1.0


# These tuple-based vector helpers keep the classifier independent from pxr and
# Kit, allowing the geometric contract to be tested in an ordinary Python run.
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
    room_position_world: Vector3 = (0.0, 0.0, 0.0)


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
    physical_normal: Vector3 = (0.0, 0.0, 1.0)
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
