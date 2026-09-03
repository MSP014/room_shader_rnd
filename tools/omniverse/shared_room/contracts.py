"""Define shared-room OpenUSD runtime settings and authored-data contracts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pxr import Sdf

from ..interior_sets.selectors import SelectorResolution
from ..room_run.contracts import (
    ApertureDescriptor,
    ClassificationResult,
    ClassifierDiagnostic,
    ClassifierSettings,
)

if TYPE_CHECKING:
    from .interior_set_diagnostics import InteriorSetDiagnostics

DERIVED_ROOM_SIZE = "ormsRoomSize"
DERIVED_ROOM_DEPTH_SIZE = "ormsRoomDepthSize"
DERIVED_ROOM_GROUP_ID = "ormsRoomGroupId"
DERIVED_INTERIOR_SET_ID = "ormsInteriorSetId"
DERIVED_MAPPING_VALID = "ormsMappingValid"
DERIVED_ROOM_AXIS_U = "ormsRoomAxisU"
DERIVED_ROOM_AXIS_V = "ormsRoomAxisV"
DERIVED_ROOM_POSITION = "ormsRoomPositionWorld"
DERIVED_ROOM_SCALE = "ormsRoomScale"
DERIVED_MAP_ORIGIN = "ormsRoomMapOrigin"
DERIVED_MAP_AXIS_U = "ormsRoomMapAxisU"
DERIVED_MAP_AXIS_V = "ormsRoomMapAxisV"
DERIVED_PHYSICAL_NORMAL = "ormsPhysicalNormal"
DERIVED_SLICE_START_DEPTH = "ormsSliceStartDepth"
DERIVED_ROOM_PARAMETERS = "ormsRoomParameters"
DERIVED_MAP_POSITION = "ormsRoomMapPosition"
DERIVED_PRIMARY_APERTURE_MIN_U_012 = "ormsPrimaryApertureMinU012"
DERIVED_PRIMARY_APERTURE_MAX_U_012 = "ormsPrimaryApertureMaxU012"
DERIVED_PRIMARY_APERTURE_U_3 = "ormsPrimaryApertureU3"
DERIVED_APERTURE_MASK_OFFSET_U = "ormsApertureMaskOffsetU"

DERIVED_PRIMVAR_NAMES = frozenset(
    {
        DERIVED_ROOM_SIZE,
        DERIVED_ROOM_DEPTH_SIZE,
        DERIVED_ROOM_GROUP_ID,
        DERIVED_INTERIOR_SET_ID,
        DERIVED_MAPPING_VALID,
        DERIVED_ROOM_AXIS_U,
        DERIVED_ROOM_AXIS_V,
        DERIVED_ROOM_POSITION,
        DERIVED_ROOM_SCALE,
        DERIVED_MAP_ORIGIN,
        DERIVED_MAP_AXIS_U,
        DERIVED_MAP_AXIS_V,
        DERIVED_PHYSICAL_NORMAL,
        DERIVED_SLICE_START_DEPTH,
        DERIVED_ROOM_PARAMETERS,
        DERIVED_MAP_POSITION,
        DERIVED_PRIMARY_APERTURE_MIN_U_012,
        DERIVED_PRIMARY_APERTURE_MAX_U_012,
        DERIVED_PRIMARY_APERTURE_U_3,
        DERIVED_APERTURE_MASK_OFFSET_U,
    }
)

KIT_SETTINGS_ROOT = "/persistent/exts/orms/classifier"
INSTANCE_POLICY_PRESERVE = "preserve"
INSTANCE_POLICY_SESSION_DEINSTANCE = "session_deinstance"
METRICS_MODE_AUTO = "auto"
METRICS_MODE_LOCAL_OVERRIDE = "local_override"

_REQUIRED_SOURCE_PRIMVARS = (
    "roomID",
    "roomP",
    "tangentu",
    "tangentv",
    "roomUV",
)
CAMERA_POSITION_PRIMVAR_NAME = "ormsCameraPositionWorld"
CAMERA_POSITION_PRIMVAR_PATH = Sdf.Path(
    f"/World.primvars:{CAMERA_POSITION_PRIMVAR_NAME}"
)
RUNTIME_OWNED_PRIMVAR_NAMES = DERIVED_PRIMVAR_NAMES | {
    CAMERA_POSITION_PRIMVAR_NAME
}

_RTX_CUTOUT_OPT_IN_ATTRIBUTE = "omni:rtx:enableCutoutOpacity"

ClassificationPhaseCallback = Callable[
    [str, Mapping[str, object]],
    None,
]


@dataclass(frozen=True)
class RuntimeClassifierSettings:
    """Settings consumed by the manually started shared-room classifier."""

    enabled_room_sizes: frozenset[int] = frozenset({1, 2, 3, 4})
    partition_seed: int = 0
    instance_policy: str = INSTANCE_POLICY_PRESERVE
    metrics_mode: str = METRICS_MODE_AUTO
    local_up_axis: str = "Y"
    local_meters_per_unit: float = 1.0
    floor_tolerance_metres: float = 0.25
    minimum_vertical_overlap: float = 0.5
    facade_angle_snap_degrees: float = 5.0
    maximum_local_spacing_ratio: float = 2.0
    maximum_turn_degrees: float = 100.0
    corner_turn_threshold_degrees: float = 60.0

    def core_settings(
        self,
        available_room_sizes: frozenset[int],
        *,
        available_room_sizes_by_set: (
            Mapping[str, frozenset[int]] | None
        ) = None,
        incoherent_interior_set_ids: frozenset[str] = frozenset(),
    ) -> ClassifierSettings:
        """Project runtime and resource policy into pure geometric settings."""

        enabled_sizes = set(self.enabled_room_sizes)
        enabled_sizes.add(1)
        return ClassifierSettings(
            enabled_room_sizes=frozenset(enabled_sizes),
            available_room_sizes=available_room_sizes,
            available_room_sizes_by_set=tuple(
                sorted((available_room_sizes_by_set or {}).items())
            ),
            incoherent_interior_set_ids=incoherent_interior_set_ids,
            partition_seed=self.partition_seed,
            floor_tolerance_metres=self.floor_tolerance_metres,
            minimum_vertical_overlap=self.minimum_vertical_overlap,
            facade_angle_snap_degrees=self.facade_angle_snap_degrees,
            maximum_local_spacing_ratio=self.maximum_local_spacing_ratio,
            maximum_turn_degrees=self.maximum_turn_degrees,
            corner_turn_threshold_degrees=(self.corner_turn_threshold_degrees),
        )


@dataclass(frozen=True)
class ResolvedStageMetrics:
    """Stage interpretation used only by ORMS classification."""

    up_axis: str
    meters_per_unit: float
    diagnostics: tuple[ClassifierDiagnostic, ...] = ()


@dataclass(frozen=True)
class StageExtraction:
    """Face-level apertures and mesh sizes extracted from one composed stage."""

    apertures: tuple[ApertureDescriptor, ...]
    source_prim_paths: tuple[str, ...]
    source_material_paths: tuple[str, ...]
    face_counts_by_prim: tuple[tuple[str, int], ...]
    diagnostics: tuple[ClassifierDiagnostic, ...]


@dataclass(frozen=True)
class StageClassification:
    """Inspection result retained by the manual R&D runtime."""

    metrics: ResolvedStageMetrics
    available_room_sizes: frozenset[int]
    extraction: StageExtraction
    result: ClassificationResult
    runtime_layer_identifier: str
    selector_resolutions: tuple[SelectorResolution, ...] = ()
    interior_set_diagnostics: "InteriorSetDiagnostics | None" = None


def _diagnostic(
    state: str,
    prim_path: str,
    **details: object,
) -> ClassifierDiagnostic:
    return ClassifierDiagnostic(
        state=state,
        prim_path=prim_path,
        details=tuple(sorted(details.items())),
    )
