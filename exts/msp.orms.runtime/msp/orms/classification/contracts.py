# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Define the stable plain-data contract of shared-room classification."""

from __future__ import annotations

from dataclasses import dataclass

from ..interior_sets.contracts import DEFAULT_INTERIOR_SET_ID

Vector3 = tuple[float, float, float]
Float4 = tuple[float, float, float, float]

CLASSIFIER_CONTRACT_VERSION = "shared_room_runtime_v48"

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
    interior_set_id: str = DEFAULT_INTERIOR_SET_ID


@dataclass(frozen=True)
class ClassifierSettings:
    """Pure geometry policy expressed in metres, ratios, and degrees.

    Floor tolerance and vertical overlap establish one row. Facade snap
    establishes orientation buckets before local ordering. The spacing ratio
    compares centre spacing with a facade-local pitch, or with aperture width
    when a local pitch cannot be inferred. Maximum turn limits graph edges;
    the lower corner threshold selects the bounded corner mapping inside an
    already accepted linear component.
    """

    enabled_room_sizes: frozenset[int] = frozenset({1, 2, 3, 4})
    available_room_sizes: frozenset[int] = frozenset({1, 2, 3, 4})
    available_room_sizes_by_set: tuple[tuple[str, frozenset[int]], ...] = ()
    incoherent_interior_set_ids: frozenset[str] = frozenset()
    partition_seed: int = 0
    floor_tolerance_metres: float = 0.25
    minimum_vertical_overlap: float = 0.5
    facade_angle_snap_degrees: float = 5.0
    maximum_local_spacing_ratio: float = 2.0
    maximum_turn_degrees: float = 100.0
    corner_turn_threshold_degrees: float = 60.0
    identity_quantisation_metres: float = 0.001

    def available_sizes_for(self, set_id: str) -> frozenset[int]:
        """Return Set-local resources or the legacy global availability."""

        for candidate_id, room_sizes in self.available_room_sizes_by_set:
            if candidate_id == set_id:
                return room_sizes
        return self.available_room_sizes

    def usable_sizes_for(self, set_id: str) -> frozenset[int]:
        """Apply global artist toggles to one Set's resource inventory."""

        return frozenset(
            set(self.enabled_room_sizes)
            & set(self.available_sizes_for(set_id))
            & {1, 2, 3, 4}
        )

    def cross_family_is_coherent(self, set_id: str) -> bool:
        """Return whether one Set may form a multi-family corner room."""

        return set_id not in self.incoherent_interior_set_ids


@dataclass(frozen=True)
class ClassificationSummary:
    """Deterministic topology counters exposed to runtime diagnostics."""

    spacing_model: str = "facade_median_centre_spacing_with_width_fallback"
    building_count: int = 0
    row_count: int = 0
    facade_count: int = 0
    straight_candidate_count: int = 0
    transition_candidate_count: int = 0
    accepted_straight_edge_count: int = 0
    accepted_transition_edge_count: int = 0
    rejected_room_id_edge_count: int = 0
    rejected_interior_set_edge_count: int = 0
    rejected_spacing_edge_count: int = 0
    local_pitch_min_metres: float | None = None
    local_pitch_max_metres: float | None = None
    group_size_counts: tuple[tuple[int, int], ...] = ()


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
    interior_set_id: str = DEFAULT_INTERIOR_SET_ID


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
    interior_set_id: str = DEFAULT_INTERIOR_SET_ID


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
    summary: ClassificationSummary = ClassificationSummary()
