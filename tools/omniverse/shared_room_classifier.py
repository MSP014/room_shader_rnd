"""OpenUSD adapter and manual R&D lifecycle for shared Room Map rooms.

The module can be imported by ordinary pytest without Kit.  ``start()`` and
``stop()`` import Omniverse modules lazily for use from Composer's Script
Editor.  All classifier-authored opinions live in one anonymous sublayer of the
stage Session Layer and are removed without clearing unrelated session edits.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from time import perf_counter
from typing import Any

from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, Vt

try:
    from . import room_run_classifier as _room_run_classifier
    from . import shared_room_preferences
    from .room_run_classifier import (
        ApertureDescriptor,
        ClassificationResult,
        ClassifierDiagnostic,
        ClassifierSettings,
        DerivedApertureMapping,
        classify_apertures,
    )
    from .status_log import log_room_map_warning
except ImportError:
    import room_run_classifier as _room_run_classifier
    import shared_room_preferences
    from room_run_classifier import (
        ApertureDescriptor,
        ClassificationResult,
        ClassifierDiagnostic,
        ClassifierSettings,
        DerivedApertureMapping,
        classify_apertures,
    )
    from status_log import log_room_map_warning

DERIVED_ROOM_SIZE = "ormsRoomSize"
DERIVED_ROOM_DEPTH_SIZE = "ormsRoomDepthSize"
DERIVED_ROOM_GROUP_ID = "ormsRoomGroupId"
DERIVED_MAPPING_VALID = "ormsMappingValid"
DERIVED_ROOM_AXIS_U = "ormsRoomAxisU"
DERIVED_ROOM_AXIS_V = "ormsRoomAxisV"
DERIVED_ROOM_SCALE = "ormsRoomScale"
DERIVED_MAP_ORIGIN = "ormsRoomMapOrigin"
DERIVED_MAP_AXIS_U = "ormsRoomMapAxisU"
DERIVED_MAP_AXIS_V = "ormsRoomMapAxisV"
DERIVED_SLICE_START_DEPTH = "ormsSliceStartDepth"
DERIVED_ROOM_PARAMETERS = "ormsRoomParameters"
DERIVED_MAP_POSITION = "ormsRoomMapPosition"

DERIVED_PRIMVAR_NAMES = frozenset(
    {
        DERIVED_ROOM_SIZE,
        DERIVED_ROOM_DEPTH_SIZE,
        DERIVED_ROOM_GROUP_ID,
        DERIVED_MAPPING_VALID,
        DERIVED_ROOM_AXIS_U,
        DERIVED_ROOM_AXIS_V,
        DERIVED_ROOM_SCALE,
        DERIVED_MAP_ORIGIN,
        DERIVED_MAP_AXIS_U,
        DERIVED_MAP_AXIS_V,
        DERIVED_SLICE_START_DEPTH,
        DERIVED_ROOM_PARAMETERS,
        DERIVED_MAP_POSITION,
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

_TRACE_DIAGNOSTIC_CODE = "ORMS-KRM93-TRACE"
_TRACE_RUN_IDS = count(1)
_TRACE_PATH_LIMIT = 16
_FIRST_FRAME_SIGNAL = "StageRenderingEventType.NEW_FRAME"
_RTX_FACE_CULLING_SETTING = "/rtx/hydra/faceCulling/enabled"
_EXPECTED_CLASSIFIER_CONTRACT_VERSION = "krm93_packed_mapping_v12"
_RUNTIME_FAMILY_SHADER_PATHS = tuple(
    Sdf.Path(f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader")
    for room_size in range(1, 5)
)
_SHARED_RUNTIME_INPUT_NAMES = frozenset(
    {
        "variation_seed",
        "room_depth",
        "room_uniform_scale",
        "window_shift",
        "window_aperture_scale",
        "window_aperture_offset",
        "enable_slice_1",
        "enable_slice_2",
        "enable_slice_3",
        "enable_slice_4",
        "slice_1_depth_percent",
        "slice_2_depth_percent",
        "slice_3_depth_percent",
        "slice_4_depth_percent",
        "slice_1_offset",
        "slice_2_offset",
        "slice_3_offset",
        "slice_4_offset",
        "slice_1_scale",
        "slice_2_scale",
        "slice_3_scale",
        "slice_4_scale",
        "fallback_colour",
        "emission_strength",
    }
)

ClassificationPhaseCallback = Callable[
    [str, Mapping[str, object]],
    None,
]


def _runtime_family_input_name(path: Sdf.Path) -> str | None:
    """Return a shared artist input edited on one runtime atlas family."""

    if not path.IsPropertyPath() or path.GetPrimPath() not in (
        _RUNTIME_FAMILY_SHADER_PATHS
    ):
        return None
    property_name = str(path).rsplit(".", 1)[-1]
    if not property_name.startswith("inputs:"):
        return None
    input_name = property_name.removeprefix("inputs:")
    return input_name if input_name in _SHARED_RUNTIME_INPUT_NAMES else None


def _runtime_family_input_paths(input_name: str) -> tuple[Sdf.Path, ...]:
    return tuple(
        shader_path.AppendProperty(f"inputs:{input_name}")
        for shader_path in _RUNTIME_FAMILY_SHADER_PATHS
    )


def _synchronise_runtime_family_input(
    stage: Usd.Stage,
    source_path: Sdf.Path,
) -> int:
    """Copy one shared control to every authored x1-x4 atlas material."""

    input_name = _runtime_family_input_name(source_path)
    source_attribute = stage.GetAttributeAtPath(source_path)
    if input_name is None or not source_attribute:
        return 0
    source_value = source_attribute.Get()
    source_type = source_attribute.GetTypeName()
    updated_count = 0
    for target_path in _runtime_family_input_paths(input_name):
        if target_path == source_path:
            continue
        target_attribute = stage.GetAttributeAtPath(target_path)
        if not target_attribute:
            target_prim = stage.GetPrimAtPath(target_path.GetPrimPath())
            if not target_prim:
                continue
            target_attribute = (
                UsdShade.Shader(target_prim)
                .CreateInput(
                    input_name,
                    source_type,
                )
                .GetAttr()
            )
        if target_attribute.Get() != source_value:
            target_attribute.Set(source_value)
            updated_count += 1
    return updated_count


def _runtime_family_input_values(
    stage: Usd.Stage,
    input_name: str,
) -> str:
    values = []
    for room_size, path in enumerate(
        _runtime_family_input_paths(input_name),
        start=1,
    ):
        attribute = stage.GetAttributeAtPath(path)
        values.append(
            f"x{room_size}={attribute.Get() if attribute else 'MISSING'}"
        )
    return ",".join(values)


def _has_direct_runtime_input_opinion(attribute: Usd.Attribute) -> bool:
    """Exclude values inherited from the source material specialization."""

    attribute_path = attribute.GetPath()
    return any(
        spec.path == attribute_path for spec in attribute.GetPropertyStack()
    )


class _RuntimeTrace:
    """Emit one correlated, warning-visible timing record per runtime phase."""

    def __init__(
        self,
        *,
        trigger: str,
        log_warning: Callable[..., None],
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self.run_id = f"KRM93-{next(_TRACE_RUN_IDS):04d}"
        self.trigger = trigger
        self._log_warning = log_warning
        self._clock = clock
        self._started_at = clock()
        self._last_phase_at = self._started_at

    def mark(
        self,
        phase: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        """Record one phase without hiding it behind the Console info filter."""

        now = self._clock()
        payload: dict[str, object] = {
            "diagnostic_code": _TRACE_DIAGNOSTIC_CODE,
            "run_id": self.run_id,
            "trigger": self.trigger,
            "phase_ms": round((now - self._last_phase_at) * 1000.0, 3),
            "elapsed_ms": round((now - self._started_at) * 1000.0, 3),
        }
        if details:
            payload.update(details)
        self._log_warning(
            owner="KRM-93 CLASSIFIER",
            process="RUNTIME PHASE TRACE",
            state=phase,
            details=payload,
        )
        self._last_phase_at = self._clock()


def _subscribe_to_next_rendered_frame(
    callback: Callable[[object], None],
) -> object:
    """Observe the next frame without treating it as material completion."""

    import carb.eventdispatcher
    import omni.usd

    context = omni.usd.get_context()
    event_name = context.stage_rendering_event_name(
        omni.usd.StageRenderingEventType.NEW_FRAME
    )
    return carb.eventdispatcher.get_eventdispatcher().observe_event(
        event_name=event_name,
        on_event=callback,
        observer_name="orms.shared_room_classifier.renderer_ready",
    )


def _trace_path_details(
    *,
    resynced_paths: Sequence[Sdf.Path],
    changed_info_paths: Sequence[Sdf.Path],
    relevant_paths: Sequence[Sdf.Path],
) -> dict[str, object]:
    """Bound USD notice detail volume while retaining the triggering paths."""

    def serialise(paths: Sequence[Sdf.Path]) -> str:
        retained = tuple(str(path) for path in paths[:_TRACE_PATH_LIMIT])
        return ", ".join(retained) if retained else "<none>"

    return {
        "resynced_path_count": len(resynced_paths),
        "resynced_paths": serialise(resynced_paths),
        "changed_info_path_count": len(changed_info_paths),
        "changed_info_paths": serialise(changed_info_paths),
        "relevant_path_count": len(relevant_paths),
        "relevant_paths": serialise(relevant_paths),
        "path_limit": _TRACE_PATH_LIMIT,
        "paths_truncated": (
            len(resynced_paths) > _TRACE_PATH_LIMIT
            or len(changed_info_paths) > _TRACE_PATH_LIMIT
            or len(relevant_paths) > _TRACE_PATH_LIMIT
        ),
    }


@dataclass(frozen=True)
class RuntimeClassifierSettings:
    """Settings consumed by the manually started KRM-93 R&D module."""

    enabled_room_sizes: frozenset[int] = frozenset({1, 2, 3, 4})
    partition_seed: int = 0
    instance_policy: str = INSTANCE_POLICY_PRESERVE
    metrics_mode: str = METRICS_MODE_AUTO
    local_up_axis: str = "Y"
    local_meters_per_unit: float = 1.0
    edge_gap_tolerance_metres: float = 0.65
    floor_tolerance_metres: float = 0.25
    minimum_vertical_overlap: float = 0.5
    maximum_turn_degrees: float = 100.0
    corner_turn_threshold_degrees: float = 60.0

    def core_settings(
        self,
        available_room_sizes: frozenset[int],
    ) -> ClassifierSettings:
        enabled_sizes = set(self.enabled_room_sizes)
        enabled_sizes.add(1)
        return ClassifierSettings(
            enabled_room_sizes=frozenset(enabled_sizes),
            available_room_sizes=available_room_sizes,
            partition_seed=self.partition_seed,
            edge_gap_tolerance_metres=self.edge_gap_tolerance_metres,
            floor_tolerance_metres=self.floor_tolerance_metres,
            minimum_vertical_overlap=self.minimum_vertical_overlap,
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


def _valid_up_axis(value: object) -> str | None:
    text = str(value).upper() if value is not None else ""
    return text if text in {"Y", "Z"} else None


def resolve_stage_metrics(
    stage: Usd.Stage,
    settings: RuntimeClassifierSettings,
) -> ResolvedStageMetrics:
    """Resolve Auto or local metrics without authoring stage metadata."""

    if settings.metrics_mode == METRICS_MODE_LOCAL_OVERRIDE:
        up_axis = _valid_up_axis(settings.local_up_axis)
        meters_per_unit = float(settings.local_meters_per_unit)
        if up_axis is None or meters_per_unit <= 0.0:
            return ResolvedStageMetrics(
                up_axis="Y",
                meters_per_unit=1.0,
                diagnostics=(
                    _diagnostic(
                        "INVALID_LOCAL_STAGE_METRICS",
                        "/",
                        local_up_axis=settings.local_up_axis,
                        local_meters_per_unit=settings.local_meters_per_unit,
                    ),
                ),
            )

        diagnostics = []
        authored_up = (
            stage.GetMetadata(UsdGeom.Tokens.upAxis)
            if stage.HasAuthoredMetadata(UsdGeom.Tokens.upAxis)
            else None
        )
        authored_metres = (
            stage.GetMetadata(UsdGeom.Tokens.metersPerUnit)
            if stage.HasAuthoredMetadata(UsdGeom.Tokens.metersPerUnit)
            else None
        )
        if (
            authored_up is not None
            and authored_metres is not None
            and (
                _valid_up_axis(authored_up) != up_axis
                or abs(float(authored_metres) - meters_per_unit) > 1.0e-9
            )
        ):
            diagnostics.append(
                _diagnostic(
                    "LOCAL_STAGE_METRICS_OVERRIDE",
                    "/",
                    authored_up_axis=authored_up,
                    authored_meters_per_unit=authored_metres,
                    local_up_axis=up_axis,
                    local_meters_per_unit=meters_per_unit,
                )
            )
        return ResolvedStageMetrics(
            up_axis=up_axis,
            meters_per_unit=meters_per_unit,
            diagnostics=tuple(diagnostics),
        )

    if settings.metrics_mode != METRICS_MODE_AUTO:
        return ResolvedStageMetrics(
            up_axis="Y",
            meters_per_unit=1.0,
            diagnostics=(
                _diagnostic(
                    "INVALID_STAGE_METRICS_MODE",
                    "/",
                    metrics_mode=settings.metrics_mode,
                ),
            ),
        )

    authored_up = (
        stage.GetMetadata(UsdGeom.Tokens.upAxis)
        if stage.HasAuthoredMetadata(UsdGeom.Tokens.upAxis)
        else None
    )
    authored_metres = (
        stage.GetMetadata(UsdGeom.Tokens.metersPerUnit)
        if stage.HasAuthoredMetadata(UsdGeom.Tokens.metersPerUnit)
        else None
    )
    up_axis = _valid_up_axis(authored_up)
    try:
        meters_per_unit = float(authored_metres)
    except (TypeError, ValueError):
        meters_per_unit = 0.0
    if up_axis is None or meters_per_unit <= 0.0:
        return ResolvedStageMetrics(
            up_axis="Y",
            meters_per_unit=1.0,
            diagnostics=(
                _diagnostic(
                    "MISSING_OR_INVALID_STAGE_METRICS",
                    "/",
                    authored_up_axis=authored_up,
                    authored_meters_per_unit=authored_metres,
                    fallback_up_axis="Y",
                    fallback_meters_per_unit=1.0,
                ),
            ),
        )
    return ResolvedStageMetrics(up_axis, meters_per_unit)


def discover_atlas_family_availability(
    repository_root: Path,
) -> frozenset[int]:
    """Return x1 through x4 only when all eight UDIM tiles resolve locally."""

    family_names = {
        1: "room_map_debug",
        2: "room_map_debug_x2",
        3: "room_map_debug_x3",
        4: "room_map_debug_x4",
    }
    texture_root = repository_root / "assets" / "_external" / "tex"
    available = []
    for size, family_name in family_names.items():
        family_directory = texture_root / family_name
        if all(
            (
                family_directory / f"{family_name}.{tile_number:04d}.png"
            ).is_file()
            for tile_number in range(1001, 1009)
        ):
            available.append(size)
    return frozenset(available)


def _face_vertex_indices(mesh: UsdGeom.Mesh) -> tuple[tuple[int, ...], ...]:
    counts = mesh.GetFaceVertexCountsAttr().Get() or ()
    indices = mesh.GetFaceVertexIndicesAttr().Get() or ()
    faces = []
    cursor = 0
    for vertex_count in counts:
        faces.append(tuple(indices[cursor : cursor + vertex_count]))
        cursor += vertex_count
    return tuple(faces)


def _primvar_value_for_face(
    primvar: UsdGeom.Primvar,
    face_index: int,
    point_indices: tuple[int, ...],
    face_vertex_offset: int,
) -> object | None:
    values = primvar.ComputeFlattened()
    if values is None or len(values) == 0:
        return None
    interpolation = primvar.GetInterpolation()
    if interpolation == UsdGeom.Tokens.constant:
        return values[0]
    if interpolation == UsdGeom.Tokens.uniform:
        return values[face_index]
    if interpolation in {UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying}:
        return values[point_indices[0]]
    if interpolation == UsdGeom.Tokens.faceVarying:
        return values[face_vertex_offset]
    return None


def _room_map_mesh_orientation(
    mesh: UsdGeom.Mesh,
    mapped_face_indices: Sequence[int],
) -> tuple[str | None, ClassifierDiagnostic | None]:
    """Align USD front faces with the authored ORMS tangent frame."""

    prim_path = str(mesh.GetPath())
    faces = _face_vertex_indices(mesh)
    mapped_faces = frozenset(int(index) for index in mapped_face_indices)
    if mapped_faces != frozenset(range(len(faces))):
        return None, _diagnostic(
            "ROOM_MAP_BACKFACE_CULLING_SKIPPED",
            prim_path,
            reason="mesh_contains_unmapped_faces",
            face_count=len(faces),
            mapped_face_count=len(mapped_faces),
        )

    points = mesh.GetPointsAttr().Get() or ()
    primvars = UsdGeom.PrimvarsAPI(mesh)
    tangent_u_primvar = primvars.GetPrimvar("tangentu")
    tangent_v_primvar = primvars.GetPrimvar("tangentv")
    face_vertex_offsets = []
    offset = 0
    for face in faces:
        face_vertex_offsets.append(offset)
        offset += len(face)

    winding_signs = set()
    for face_index in sorted(mapped_faces):
        point_indices = faces[face_index]
        if len(point_indices) < 3:
            return None, _diagnostic(
                "ROOM_MAP_BACKFACE_CULLING_SKIPPED",
                prim_path,
                reason="degenerate_face",
                face_index=face_index,
            )
        tangent_u = _primvar_value_for_face(
            tangent_u_primvar,
            face_index,
            point_indices,
            face_vertex_offsets[face_index],
        )
        tangent_v = _primvar_value_for_face(
            tangent_v_primvar,
            face_index,
            point_indices,
            face_vertex_offsets[face_index],
        )
        if tangent_u is None or tangent_v is None:
            return None, _diagnostic(
                "ROOM_MAP_BACKFACE_CULLING_SKIPPED",
                prim_path,
                reason="missing_tangent_frame",
                face_index=face_index,
            )
        point_0 = Gf.Vec3d(*points[point_indices[0]])
        point_1 = Gf.Vec3d(*points[point_indices[1]])
        point_2 = Gf.Vec3d(*points[point_indices[2]])
        geometric_normal = Gf.Cross(point_1 - point_0, point_2 - point_0)
        contract_normal = Gf.Cross(
            Gf.Vec3d(*tangent_u),
            Gf.Vec3d(*tangent_v),
        )
        normal_scale = (
            geometric_normal.GetLength() * contract_normal.GetLength()
        )
        if normal_scale <= 1.0e-12:
            return None, _diagnostic(
                "ROOM_MAP_BACKFACE_CULLING_SKIPPED",
                prim_path,
                reason="degenerate_normal",
                face_index=face_index,
            )
        cosine = (
            sum(
                geometric_normal[index] * contract_normal[index]
                for index in range(3)
            )
            / normal_scale
        )
        if abs(cosine) <= 1.0e-5:
            return None, _diagnostic(
                "ROOM_MAP_BACKFACE_CULLING_SKIPPED",
                prim_path,
                reason="winding_is_orthogonal_to_tangent_frame",
                face_index=face_index,
            )
        winding_signs.add(1 if cosine > 0.0 else -1)

    if len(winding_signs) != 1:
        return None, _diagnostic(
            "ROOM_MAP_BACKFACE_CULLING_SKIPPED",
            prim_path,
            reason="mixed_face_winding",
        )
    orientation = (
        UsdGeom.Tokens.rightHanded
        if winding_signs == {1}
        else UsdGeom.Tokens.leftHanded
    )
    return orientation, None


def _world_point(matrix: Gf.Matrix4d, value: object) -> Gf.Vec3d:
    return matrix.Transform(Gf.Vec3d(*value))


def _world_direction(matrix: Gf.Matrix4d, value: object) -> Gf.Vec3d:
    return matrix.TransformDir(Gf.Vec3d(*value))


def _building_root(prim: Usd.Prim) -> str:
    ancestry = []
    current = prim
    while current and not current.IsPseudoRoot():
        ancestry.append(current)
        current = current.GetParent()

    for candidate in ancestry:
        if (
            candidate.IsInstance()
            or candidate.HasAuthoredReferences()
            or candidate.GetMetadata("kind") in {"component", "assembly"}
        ):
            return str(candidate.GetPath())

    path = prim.GetPath()
    prefixes = path.GetPrefixes()
    if len(prefixes) >= 2 and str(prefixes[0]) == "/World":
        return str(prefixes[1])
    return str(prefixes[0]) if prefixes else str(path)


def _has_room_map_material_binding(prim: Usd.Prim) -> bool:
    material, relationship = UsdShade.MaterialBindingAPI(
        prim
    ).ComputeBoundMaterial()
    if not relationship or not material:
        return False
    for candidate in Usd.PrimRange(material.GetPrim()):
        source_asset = candidate.GetAttribute("info:mdl:sourceAsset").Get()
        if source_asset and source_asset.path.endswith("src/mdl/room_map.mdl"):
            return True
    return False


def extract_stage_apertures(
    stage: Usd.Stage,
    metrics: ResolvedStageMetrics,
) -> StageExtraction:
    """Extract one descriptor per supported mesh face from the composed stage."""

    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    apertures = []
    face_counts_by_prim = []
    diagnostics = []

    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        if not _has_room_map_material_binding(prim):
            continue
        mesh = UsdGeom.Mesh(prim)
        primvars = UsdGeom.PrimvarsAPI(mesh)
        source_primvars = {
            name: primvars.GetPrimvar(name)
            for name in _REQUIRED_SOURCE_PRIMVARS
        }
        if not all(source_primvars.values()):
            continue

        faces = _face_vertex_indices(mesh)
        points = mesh.GetPointsAttr().Get() or ()
        if not faces or not points:
            continue
        face_counts_by_prim.append((str(prim.GetPath()), len(faces)))
        world_transform = xform_cache.GetLocalToWorldTransform(prim)
        face_vertex_offset = 0

        for face_index, point_indices in enumerate(faces):
            if len(point_indices) != 4:
                diagnostics.append(
                    _diagnostic(
                        "UNSUPPORTED_APERTURE_TOPOLOGY",
                        str(prim.GetPath()),
                        face_index=face_index,
                        vertex_count=len(point_indices),
                    )
                )
                face_vertex_offset += len(point_indices)
                continue

            room_id = _primvar_value_for_face(
                source_primvars["roomID"],
                face_index,
                point_indices,
                face_vertex_offset,
            )
            tangent_u = _primvar_value_for_face(
                source_primvars["tangentu"],
                face_index,
                point_indices,
                face_vertex_offset,
            )
            tangent_v = _primvar_value_for_face(
                source_primvars["tangentv"],
                face_index,
                point_indices,
                face_vertex_offset,
            )
            if room_id is None or tangent_u is None or tangent_v is None:
                diagnostics.append(
                    _diagnostic(
                        "INVALID_SOURCE_PRIMVARS",
                        str(prim.GetPath()),
                        face_index=face_index,
                    )
                )
                face_vertex_offset += len(point_indices)
                continue

            world_points = [
                _world_point(world_transform, points[index])
                for index in point_indices
            ]
            centre = sum(world_points, Gf.Vec3d(0.0)) / len(world_points)
            world_tangent_u = _world_direction(world_transform, tangent_u)
            world_tangent_v = _world_direction(world_transform, tangent_v)
            scale = metrics.meters_per_unit
            apertures.append(
                ApertureDescriptor(
                    key=f"{prim.GetPath()}#{face_index}",
                    prim_path=str(prim.GetPath()),
                    face_index=face_index,
                    building_root=_building_root(prim),
                    room_id=int(room_id),
                    centre_metres=tuple(
                        float(value * scale) for value in centre
                    ),
                    tangent_u_metres=tuple(
                        float(value * scale) for value in world_tangent_u
                    ),
                    tangent_v_metres=tuple(
                        float(value * scale) for value in world_tangent_v
                    ),
                )
            )
            face_vertex_offset += len(point_indices)

    return StageExtraction(
        apertures=tuple(apertures),
        face_counts_by_prim=tuple(sorted(face_counts_by_prim)),
        diagnostics=tuple(diagnostics),
    )


class RuntimeLayerOwner:
    """Own exactly one removable ORMS sublayer beneath the Session Layer."""

    def __init__(self, stage: Usd.Stage):
        self.stage = stage
        self.layer = Sdf.Layer.CreateAnonymous("orms_shared_rooms.usda")
        self._attached = False

    def attach(self) -> Sdf.Layer:
        if self._attached:
            return self.layer
        session_layer = self.stage.GetSessionLayer()
        sublayers = list(session_layer.subLayerPaths)
        if self.layer.identifier not in sublayers:
            sublayers.insert(0, self.layer.identifier)
            session_layer.subLayerPaths = sublayers
        self._attached = True
        return self.layer

    def detach(self) -> None:
        if not self._attached:
            return
        session_layer = self.stage.GetSessionLayer()
        session_layer.subLayerPaths = [
            identifier
            for identifier in session_layer.subLayerPaths
            if identifier != self.layer.identifier
        ]
        self._attached = False


def _mapping_defaults(face_count: int) -> dict[str, list[object]]:
    return {
        DERIVED_ROOM_SIZE: [1] * face_count,
        DERIVED_ROOM_DEPTH_SIZE: [1] * face_count,
        DERIVED_ROOM_GROUP_ID: [0] * face_count,
        DERIVED_MAPPING_VALID: [0] * face_count,
        DERIVED_ROOM_AXIS_U: [(1.0, 0.0, 0.0)] * face_count,
        DERIVED_ROOM_AXIS_V: [(0.0, 1.0, 0.0)] * face_count,
        DERIVED_ROOM_SCALE: [(1.0, 1.0, 1.0)] * face_count,
        DERIVED_MAP_ORIGIN: [(0.0, 0.0, 0.0)] * face_count,
        DERIVED_MAP_AXIS_U: [(1.0, 0.0, 0.0)] * face_count,
        DERIVED_MAP_AXIS_V: [(0.0, 1.0, 0.0)] * face_count,
        DERIVED_SLICE_START_DEPTH: [0.0] * face_count,
        DERIVED_ROOM_PARAMETERS: [(11.0, 0.0, 0.0)] * face_count,
    }


def _set_mapping_values(
    values: dict[str, list[object]],
    mapping: DerivedApertureMapping,
) -> None:
    face_index = mapping.face_index
    values[DERIVED_ROOM_SIZE][face_index] = mapping.room_size
    values[DERIVED_ROOM_DEPTH_SIZE][face_index] = mapping.room_depth_size
    values[DERIVED_ROOM_GROUP_ID][face_index] = mapping.group_id
    values[DERIVED_MAPPING_VALID][face_index] = int(mapping.mapping_valid)
    values[DERIVED_ROOM_AXIS_U][face_index] = mapping.room_axis_u
    values[DERIVED_ROOM_AXIS_V][face_index] = mapping.room_axis_v
    values[DERIVED_ROOM_SCALE][face_index] = mapping.room_scale
    values[DERIVED_MAP_ORIGIN][face_index] = mapping.map_origin
    values[DERIVED_MAP_AXIS_U][face_index] = mapping.map_axis_u
    values[DERIVED_MAP_AXIS_V][face_index] = mapping.map_axis_v
    values[DERIVED_SLICE_START_DEPTH][face_index] = mapping.slice_start_depth
    depth_aligned_portal = (
        abs(mapping.map_axis_u[0]) <= 1.0e-6
        and abs(mapping.map_axis_u[2]) > 1.0e-6
    )
    portal_mode = 0.0
    if mapping.mapping_valid:
        portal_mode = (
            (2.0 if mapping.map_axis_u[2] >= 0.0 else -2.0)
            if depth_aligned_portal
            else 1.0
        )
    values[DERIVED_ROOM_PARAMETERS][face_index] = (
        float(mapping.room_size * 10 + mapping.room_depth_size),
        float(mapping.slice_start_depth),
        portal_mode,
    )


def _author_uniform_int_primvar(
    primvars: UsdGeom.PrimvarsAPI,
    name: str,
    values: Sequence[object],
) -> None:
    primvars.CreatePrimvar(
        name,
        Sdf.ValueTypeNames.IntArray,
        UsdGeom.Tokens.uniform,
    ).Set(Vt.IntArray([int(value) for value in values]))


def _author_uniform_float3_primvar(
    primvars: UsdGeom.PrimvarsAPI,
    name: str,
    values: Sequence[object],
) -> None:
    primvars.CreatePrimvar(
        name,
        Sdf.ValueTypeNames.Float3Array,
        UsdGeom.Tokens.uniform,
    ).Set(Vt.Vec3fArray([Gf.Vec3f(*value) for value in values]))


def _author_uniform_float_primvar(
    primvars: UsdGeom.PrimvarsAPI,
    name: str,
    values: Sequence[object],
) -> None:
    primvars.CreatePrimvar(
        name,
        Sdf.ValueTypeNames.FloatArray,
        UsdGeom.Tokens.uniform,
    ).Set(Vt.FloatArray([float(value) for value in values]))


def _author_face_varying_float3_primvar(
    primvars: UsdGeom.PrimvarsAPI,
    name: str,
    values: Sequence[object],
) -> None:
    primvars.CreatePrimvar(
        name,
        Sdf.ValueTypeNames.Float3Array,
        UsdGeom.Tokens.faceVarying,
    ).Set(Vt.Vec3fArray([Gf.Vec3f(*value) for value in values]))


def _primvar_value_for_face_vertex(
    primvar: UsdGeom.Primvar,
    values: Sequence[object],
    face_index: int,
    point_index: int,
    face_vertex_index: int,
) -> object | None:
    if values is None or len(values) == 0:
        return None
    interpolation = primvar.GetInterpolation()
    if interpolation == UsdGeom.Tokens.constant:
        return values[0]
    if interpolation == UsdGeom.Tokens.uniform:
        return values[face_index]
    if interpolation in {UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying}:
        return values[point_index]
    if interpolation == UsdGeom.Tokens.faceVarying:
        return values[face_vertex_index]
    return None


def _mapped_face_vertex_positions(
    mesh: UsdGeom.Mesh,
    mappings: Sequence[DerivedApertureMapping],
) -> tuple[tuple[float, float, float], ...]:
    """Bake the affine roomUV embedding that otherwise bloats the MDL DAG."""

    faces = _face_vertex_indices(mesh)
    primvars = UsdGeom.PrimvarsAPI(mesh)
    room_uv_primvar = primvars.GetPrimvar("roomUV")
    room_uv_values = room_uv_primvar.ComputeFlattened()
    mappings_by_face = {mapping.face_index: mapping for mapping in mappings}
    positions = []
    face_vertex_index = 0
    for face_index, point_indices in enumerate(faces):
        mapping = mappings_by_face.get(face_index)
        for point_index in point_indices:
            room_uv = _primvar_value_for_face_vertex(
                room_uv_primvar,
                room_uv_values,
                face_index,
                point_index,
                face_vertex_index,
            )
            if mapping is None or room_uv is None:
                positions.append((0.0, 0.0, 0.0))
            else:
                positions.append(
                    tuple(
                        float(
                            mapping.map_origin[axis]
                            + mapping.map_axis_u[axis] * float(room_uv[0])
                            + mapping.map_axis_v[axis] * float(room_uv[1])
                        )
                        for axis in range(3)
                    )
                )
            face_vertex_index += 1
    return tuple(positions)


def author_derived_primvars(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    extraction: StageExtraction,
    result: ClassificationResult,
) -> tuple[ClassifierDiagnostic, ...]:
    """Author only direct runtime mappings into the owned ORMS layer."""

    mappings_by_prim: dict[str, list[DerivedApertureMapping]] = defaultdict(
        list
    )
    for mapping in result.mappings:
        mappings_by_prim[mapping.prim_path].append(mapping)

    diagnostics = []
    with Usd.EditContext(stage, runtime_layer):
        for prim_path, face_count in extraction.face_counts_by_prim:
            prim = stage.GetPrimAtPath(prim_path)
            if not prim:
                continue
            mappings = mappings_by_prim.get(prim_path, ())
            values = _mapping_defaults(face_count)
            for mapping in mappings:
                _set_mapping_values(values, mapping)
            primvars = UsdGeom.PrimvarsAPI(prim)
            for name in (
                DERIVED_ROOM_SIZE,
                DERIVED_ROOM_DEPTH_SIZE,
                DERIVED_ROOM_GROUP_ID,
                DERIVED_MAPPING_VALID,
            ):
                _author_uniform_int_primvar(primvars, name, values[name])
            _author_uniform_float_primvar(
                primvars,
                DERIVED_SLICE_START_DEPTH,
                values[DERIVED_SLICE_START_DEPTH],
            )
            _author_uniform_float3_primvar(
                primvars,
                DERIVED_ROOM_PARAMETERS,
                values[DERIVED_ROOM_PARAMETERS],
            )
            for name in (
                DERIVED_ROOM_AXIS_U,
                DERIVED_ROOM_AXIS_V,
                DERIVED_ROOM_SCALE,
                DERIVED_MAP_ORIGIN,
                DERIVED_MAP_AXIS_U,
                DERIVED_MAP_AXIS_V,
            ):
                _author_uniform_float3_primvar(primvars, name, values[name])
            mesh = UsdGeom.Mesh(prim)
            _author_face_varying_float3_primvar(
                primvars,
                DERIVED_MAP_POSITION,
                _mapped_face_vertex_positions(mesh, mappings),
            )
            orientation, diagnostic = _room_map_mesh_orientation(
                mesh,
                tuple(mapping.face_index for mapping in mappings),
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
                continue
            mesh.CreateDoubleSidedAttr().Set(False)
            mesh.CreateOrientationAttr().Set(orientation)
    return tuple(diagnostics)


def _prototype_has_room_map_mesh(prototype: Usd.Prim) -> bool:
    for prim in Usd.PrimRange(prototype):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        primvars = UsdGeom.PrimvarsAPI(prim)
        if all(
            primvars.GetPrimvar(name) for name in _REQUIRED_SOURCE_PRIMVARS
        ):
            return True
    return False


def apply_instance_policy(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    settings: RuntimeClassifierSettings,
) -> tuple[ClassifierDiagnostic, ...]:
    """Preserve instances by default or de-instance them only in runtime state."""

    instances = tuple(prim for prim in stage.Traverse() if prim.IsInstance())
    affected = tuple(
        prim
        for prim in instances
        if prim.GetPrototype()
        and _prototype_has_room_map_mesh(prim.GetPrototype())
    )
    if settings.instance_policy == INSTANCE_POLICY_PRESERVE:
        return tuple(
            _diagnostic(
                "INSTANCE_PRESERVED_X1_FALLBACK",
                str(prim.GetPath()),
                instance_policy=INSTANCE_POLICY_PRESERVE,
            )
            for prim in affected
        )
    if settings.instance_policy != INSTANCE_POLICY_SESSION_DEINSTANCE:
        return (
            _diagnostic(
                "INVALID_INSTANCE_POLICY",
                "/",
                instance_policy=settings.instance_policy,
            ),
        )

    with Sdf.ChangeBlock(), Usd.EditContext(stage, runtime_layer):
        for prim in affected:
            prim.SetInstanceable(False)
    return tuple(
        _diagnostic(
            "SESSION_DEINSTANCE_ACTIVE",
            str(prim.GetPath()),
            instance_policy=INSTANCE_POLICY_SESSION_DEINSTANCE,
            trade_off="Instance sharing is disabled for runtime classification",
        )
        for prim in affected
    )


def _find_source_room_map_shader(stage: Usd.Stage) -> UsdShade.Shader | None:
    candidates = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdShade.Shader):
            continue
        source_asset = prim.GetAttribute("info:mdl:sourceAsset").Get()
        if source_asset and source_asset.path.endswith("src/mdl/room_map.mdl"):
            candidates.append(UsdShade.Shader(prim))
    return (
        min(candidates, key=lambda item: str(item.GetPath()))
        if candidates
        else None
    )


def _atlas_family_asset(
    repository_root: Path, room_size: int
) -> Sdf.AssetPath:
    family_name = (
        "room_map_debug" if room_size == 1 else f"room_map_debug_x{room_size}"
    )
    atlas_path = (
        repository_root
        / "assets"
        / "_external"
        / "tex"
        / family_name
        / f"{family_name}.<UDIM>.png"
    )
    return Sdf.AssetPath(atlas_path.as_posix())


def author_family_materials(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    repository_root: Path,
    usable_room_sizes: frozenset[int],
) -> dict[int, UsdShade.Material]:
    """Create no more than one shared material instance per atlas family."""

    source_shader = _find_source_room_map_shader(stage)
    source_material = (
        UsdShade.Material(source_shader.GetPrim().GetParent())
        if source_shader
        else None
    )
    materials = {}
    with Usd.EditContext(stage, runtime_layer):
        UsdGeom.Scope.Define(stage, "/__ORMSRuntime")
        UsdGeom.Scope.Define(stage, "/__ORMSRuntime/Looks")
        for room_size in sorted(usable_room_sizes & {1, 2, 3, 4}):
            material_path = f"/__ORMSRuntime/Looks/RoomMapX{room_size}"
            material = UsdShade.Material.Define(stage, material_path)
            if source_material:
                material.GetPrim().GetSpecializes().AddSpecialize(
                    source_material.GetPath()
                )
                shader = UsdShade.Shader(
                    stage.OverridePrim(f"{material_path}/Shader")
                )
            else:
                shader = UsdShade.Shader.Define(
                    stage, f"{material_path}/Shader"
                )
                shader_prim = shader.GetPrim()
                shader_prim.CreateAttribute(
                    "info:implementationSource",
                    Sdf.ValueTypeNames.Token,
                    custom=False,
                ).Set("sourceAsset")
                shader_prim.CreateAttribute(
                    "info:mdl:sourceAsset",
                    Sdf.ValueTypeNames.Asset,
                    custom=False,
                ).Set(
                    Sdf.AssetPath(
                        (
                            repository_root / "src" / "mdl" / "room_map.mdl"
                        ).as_posix()
                    )
                )
                shader_prim.CreateAttribute(
                    "info:mdl:sourceAsset:subIdentifier",
                    Sdf.ValueTypeNames.Token,
                    custom=False,
                ).Set("room_map")
                shader.CreateInput(
                    "camera_position_world", Sdf.ValueTypeNames.Float3
                ).Set(Gf.Vec3f(0.0))
                shader.CreateInput(
                    "room_variant_count", Sdf.ValueTypeNames.Int
                ).Set(8)
                shader_output = shader.CreateOutput(
                    "out", Sdf.ValueTypeNames.Token
                )
                material.CreateSurfaceOutput("mdl").ConnectToSource(
                    shader_output
                )
            shader.CreateInput("room_atlas", Sdf.ValueTypeNames.Asset).Set(
                _atlas_family_asset(repository_root, room_size)
            )
            materials[room_size] = material
    return materials


def author_family_bindings(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    result: ClassificationResult,
    materials: Mapping[int, UsdShade.Material],
) -> None:
    """Bind one effective shared family material to every classified face."""

    faces_by_subset: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    for mapping in result.mappings:
        if mapping.atlas_size in materials:
            faces_by_subset[
                (mapping.prim_path, mapping.group_id, mapping.atlas_size)
            ].append(mapping.face_index)

    with Usd.EditContext(stage, runtime_layer):
        for (prim_path, group_id, room_size), face_indices in sorted(
            faces_by_subset.items()
        ):
            mesh = UsdGeom.Mesh(stage.GetPrimAtPath(prim_path))
            if not mesh:
                continue
            subset = UsdGeom.Subset.CreateGeomSubset(
                mesh,
                f"ormsRoom{group_id}X{room_size}",
                UsdGeom.Tokens.face,
                Vt.IntArray(sorted(face_indices)),
                "materialBind",
            )
            UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(
                materials[room_size]
            )


def classify_stage(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    settings: RuntimeClassifierSettings,
    repository_root: Path,
    phase_callback: ClassificationPhaseCallback | None = None,
) -> StageClassification:
    """Classify one already-open stage and author its ephemeral mapping."""

    def report_phase(phase: str, **details: object) -> None:
        if phase_callback is not None:
            phase_callback(phase, details)

    instance_diagnostics = apply_instance_policy(
        stage, runtime_layer, settings
    )
    metrics = resolve_stage_metrics(stage, settings)
    available_room_sizes = discover_atlas_family_availability(repository_root)
    extraction = extract_stage_apertures(stage, metrics)
    extraction = StageExtraction(
        apertures=extraction.apertures,
        face_counts_by_prim=extraction.face_counts_by_prim,
        diagnostics=instance_diagnostics + extraction.diagnostics,
    )
    report_phase(
        "STAGE_EXTRACTION_COMPLETE",
        aperture_count=len(extraction.apertures),
        mesh_count=len(extraction.face_counts_by_prim),
        diagnostic_count=len(extraction.diagnostics),
        up_axis=metrics.up_axis,
        meters_per_unit=metrics.meters_per_unit,
        available_room_sizes=",".join(
            f"x{size}" for size in sorted(available_room_sizes)
        ),
    )
    result = classify_apertures(
        extraction.apertures,
        settings.core_settings(available_room_sizes),
        up_axis=metrics.up_axis,
    )
    report_phase(
        "CLASSIFICATION_COMPLETE",
        group_count=len(result.groups),
        mapping_count=len(result.mappings),
        diagnostic_count=len(result.diagnostics),
    )
    culling_diagnostics = author_derived_primvars(
        stage,
        runtime_layer,
        extraction,
        result,
    )
    if culling_diagnostics:
        extraction = StageExtraction(
            apertures=extraction.apertures,
            face_counts_by_prim=extraction.face_counts_by_prim,
            diagnostics=extraction.diagnostics + culling_diagnostics,
        )
    report_phase(
        "RUNTIME_PRIMVARS_AUTHORED",
        mapped_aperture_count=len(result.mappings),
        single_sided_mesh_count=(
            len(extraction.face_counts_by_prim) - len(culling_diagnostics)
        ),
        culling_diagnostic_count=len(culling_diagnostics),
    )
    usable_room_sizes = (
        settings.core_settings(available_room_sizes).enabled_room_sizes
        & available_room_sizes
    )
    materials = author_family_materials(
        stage,
        runtime_layer,
        repository_root,
        usable_room_sizes,
    )
    report_phase(
        "RUNTIME_MATERIALS_AUTHORED",
        material_count=len(materials),
        room_sizes=",".join(f"x{size}" for size in sorted(materials)),
    )
    author_family_bindings(stage, runtime_layer, result, materials)
    subset_count = len(
        {
            (mapping.prim_path, mapping.group_id, mapping.atlas_size)
            for mapping in result.mappings
            if mapping.atlas_size in materials
        }
    )
    report_phase(
        "RUNTIME_BINDINGS_AUTHORED",
        subset_count=subset_count,
    )
    return StageClassification(
        metrics=metrics,
        available_room_sizes=available_room_sizes,
        extraction=extraction,
        result=result,
        runtime_layer_identifier=runtime_layer.identifier,
    )


def settings_from_mapping(
    values: Mapping[str, object],
) -> RuntimeClassifierSettings:
    """Build validated settings from a Kit-like mapping for tests and scripts."""

    enabled_sizes = {1}
    for size in (2, 3, 4):
        if bool(values.get(f"enable_x{size}", True)):
            enabled_sizes.add(size)
    instance_policy_value = str(
        values.get("instance_policy", INSTANCE_POLICY_PRESERVE)
    )
    instance_policy = {
        "preserve": INSTANCE_POLICY_PRESERVE,
        "session de-instance": INSTANCE_POLICY_SESSION_DEINSTANCE,
        "session_deinstance": INSTANCE_POLICY_SESSION_DEINSTANCE,
    }.get(instance_policy_value.strip().lower(), INSTANCE_POLICY_PRESERVE)
    metrics_mode_value = str(values.get("metrics_mode", METRICS_MODE_AUTO))
    metrics_mode = {
        "auto": METRICS_MODE_AUTO,
        "auto from stage": METRICS_MODE_AUTO,
        "local override": METRICS_MODE_LOCAL_OVERRIDE,
        "local_override": METRICS_MODE_LOCAL_OVERRIDE,
    }.get(metrics_mode_value.strip().lower(), METRICS_MODE_AUTO)
    return RuntimeClassifierSettings(
        enabled_room_sizes=frozenset(enabled_sizes),
        partition_seed=int(values.get("partition_seed", 0)),
        instance_policy=instance_policy,
        metrics_mode=metrics_mode,
        local_up_axis=str(values.get("local_up_axis", "Y")),
        local_meters_per_unit=float(values.get("local_meters_per_unit", 1.0)),
        edge_gap_tolerance_metres=float(
            values.get("edge_gap_tolerance_metres", 0.65)
        ),
        floor_tolerance_metres=float(
            values.get("floor_tolerance_metres", 0.25)
        ),
        minimum_vertical_overlap=float(
            values.get("minimum_vertical_overlap", 0.5)
        ),
        maximum_turn_degrees=float(values.get("maximum_turn_degrees", 100.0)),
        corner_turn_threshold_degrees=float(
            values.get("corner_turn_threshold_degrees", 60.0)
        ),
    )


def settings_from_kit() -> RuntimeClassifierSettings:
    """Read persistent local ORMS values without authoring them into USD."""

    import carb.settings

    settings = carb.settings.get_settings()
    defaults = {
        "enable_x2": True,
        "enable_x3": True,
        "enable_x4": True,
        "partition_seed": 0,
        "instance_policy": INSTANCE_POLICY_PRESERVE,
        "metrics_mode": METRICS_MODE_AUTO,
        "local_up_axis": "Y",
        "local_meters_per_unit": 1.0,
        "edge_gap_tolerance_metres": 0.65,
        "floor_tolerance_metres": 0.25,
        "minimum_vertical_overlap": 0.5,
        "maximum_turn_degrees": 100.0,
        "corner_turn_threshold_degrees": 60.0,
    }
    values = {}
    for name, default in defaults.items():
        path = f"{KIT_SETTINGS_ROOT}/{name}"
        settings.set_default(path, default)
        values[name] = settings.get(path)
    return settings_from_mapping(values)


def _log_diagnostic(diagnostic: ClassifierDiagnostic) -> None:
    log_room_map_warning(
        owner="SHARED ROOM CLASSIFIER",
        process="RUNTIME CLASSIFICATION",
        state=diagnostic.state,
        details={
            "prim_path": diagnostic.prim_path,
            **dict(diagnostic.details),
        },
    )


class SharedRoomClassifier:
    """Manually started KRM-93 R&D classifier for an already-open stage."""

    def __init__(
        self,
        stage: Usd.Stage,
        repository_root: Path,
        settings: RuntimeClassifierSettings,
        trace_log_warning: Callable[..., None] | None = None,
    ):
        self._stage = stage
        self._repository_root = repository_root
        self._settings = settings
        self._layer_owner = RuntimeLayerOwner(stage)
        self._notice_key: Any | None = None
        self._is_authoring = False
        self._last: StageClassification | None = None
        self._geometry_ancestor_paths: frozenset[str] = frozenset()
        self._trace_log_warning = trace_log_warning
        self._first_frame_subscription: object | None = None

    @property
    def last_classification(self) -> StageClassification | None:
        return self._last

    def start(self, trigger: str = "manual_start") -> StageClassification:
        runtime_layer = self._layer_owner.attach()
        self._reclassify(runtime_layer, trigger=trigger)
        self._synchronise_existing_runtime_family_inputs()
        self._notice_key = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            self._stage,
        )
        return self._last  # type: ignore[return-value]

    def _synchronise_existing_runtime_family_inputs(self) -> None:
        """Reconcile saved family overrides before subscribing to new edits."""

        for input_name in sorted(_SHARED_RUNTIME_INPUT_NAMES):
            authored_paths = tuple(
                path
                for path in _runtime_family_input_paths(input_name)
                if (
                    (attribute := self._stage.GetAttributeAtPath(path))
                    and _has_direct_runtime_input_opinion(attribute)
                )
            )
            if not authored_paths:
                continue
            source_path = authored_paths[0]
            source_value = self._stage.GetAttributeAtPath(source_path).Get()
            conflicting_paths = tuple(
                path
                for path in authored_paths[1:]
                if self._stage.GetAttributeAtPath(path).Get() != source_value
            )
            if conflicting_paths:
                log_room_map_warning(
                    owner="KRM-93 CLASSIFIER",
                    process="RUNTIME MATERIAL INPUT SYNC",
                    state="CONFLICT",
                    details={
                        "input": input_name,
                        "family_paths": ",".join(
                            str(path) for path in authored_paths
                        ),
                        "message": (
                            "Saved atlas-family overrides disagree; edit one "
                            "runtime family input to choose the shared value."
                        ),
                    },
                )
                continue
            updated_count = _synchronise_runtime_family_input(
                self._stage,
                source_path,
            )
            if updated_count and self._trace_log_warning is not None:
                self._trace_log_warning(
                    owner="KRM-93 CLASSIFIER",
                    process="RUNTIME MATERIAL INPUT SYNC",
                    state="SYNCHRONISED",
                    details={
                        "trigger": "manual_start",
                        "input": input_name,
                        "source_path": str(source_path),
                        "updated_family_count": updated_count,
                        "family_values": _runtime_family_input_values(
                            self._stage,
                            input_name,
                        ),
                    },
                )

    def _reclassify(
        self,
        runtime_layer: Sdf.Layer | None = None,
        *,
        trigger: str = "usd_change",
        trigger_details: Mapping[str, object] | None = None,
    ) -> None:
        if self._is_authoring:
            return
        self._is_authoring = True
        try:
            layer = runtime_layer or self._layer_owner.layer
            layer.Clear()
            trace = (
                _RuntimeTrace(
                    trigger=trigger,
                    log_warning=self._trace_log_warning,
                )
                if self._trace_log_warning is not None
                else None
            )
            if trace is not None:
                run_details: dict[str, object] = {
                    "stage_identifier": self._stage.GetRootLayer().identifier,
                    "runtime_layer": layer.identifier,
                    "classifier_contract": (
                        _EXPECTED_CLASSIFIER_CONTRACT_VERSION
                    ),
                }
                if trigger_details:
                    run_details.update(trigger_details)
                trace.mark(
                    "RUNTIME_RUN_BEGIN",
                    run_details,
                )
            self._last = classify_stage(
                self._stage,
                layer,
                self._settings,
                self._repository_root,
                phase_callback=trace.mark if trace is not None else None,
            )
            geometry_ancestor_paths = set()
            for (
                prim_path,
                _face_count,
            ) in self._last.extraction.face_counts_by_prim:
                geometry_ancestor_paths.update(
                    str(prefix)
                    for prefix in Sdf.Path(prim_path).GetPrefixes()
                    if prefix.IsPrimPath()
                )
            self._geometry_ancestor_paths = frozenset(geometry_ancestor_paths)
            diagnostics = (
                self._last.metrics.diagnostics
                + self._last.extraction.diagnostics
                + self._last.result.diagnostics
            )
            for diagnostic in diagnostics:
                _log_diagnostic(diagnostic)
            if trace is not None:
                self._trace_material_submission(trace)
        finally:
            self._is_authoring = False

    def _trace_material_submission(self, trace: _RuntimeTrace) -> None:
        """Trace observable renderer boundaries without inventing completion."""

        self._first_frame_subscription = None

        def on_new_frame(_event: object) -> None:
            self._first_frame_subscription = None
            trace.mark(
                "FIRST_FRAME_AFTER_MATERIAL_UPDATE",
                {
                    "observation_signal": _FIRST_FRAME_SIGNAL,
                    "material_loading_complete": False,
                    "group_count": (
                        len(self._last.result.groups) if self._last else 0
                    ),
                },
            )

        trace.mark(
            "MATERIAL_UPDATE_SUBMITTED",
            {
                "first_frame_signal": _FIRST_FRAME_SIGNAL,
                "material_loading_complete": False,
                "material_family_count": len(
                    self._settings.core_settings(
                        self._last.available_room_sizes
                    ).enabled_room_sizes
                    & self._last.available_room_sizes
                ),
            },
        )
        trace.mark(
            "MATERIAL_LOADING_COMPLETION_UNOBSERVABLE",
            {
                "reason": (
                    "native_status_bar_waits_on_IRenderer_waitIdle_without_"
                    "a_public_Python_completion_event"
                ),
                "status_bar_activity": "Loading material...",
                "first_frame_is_completion": False,
            },
        )
        try:
            self._first_frame_subscription = _subscribe_to_next_rendered_frame(
                on_new_frame
            )
        except Exception as error:
            trace.mark(
                "FIRST_FRAME_OBSERVATION_UNAVAILABLE",
                {
                    "observation_signal": _FIRST_FRAME_SIGNAL,
                    "error": repr(error),
                },
            )

    def _on_objects_changed(
        self,
        notice: Usd.Notice.ObjectsChanged,
        _sender: Usd.Stage,
    ) -> None:
        if self._is_authoring:
            return
        resynced_paths = tuple(notice.GetResyncedPaths())
        changed_info_paths = tuple(notice.GetChangedInfoOnlyPaths())
        paths = resynced_paths + changed_info_paths
        shared_input_paths = tuple(
            path for path in paths if _runtime_family_input_name(path)
        )
        if shared_input_paths:
            self._is_authoring = True
            try:
                for path in shared_input_paths:
                    updated_count = _synchronise_runtime_family_input(
                        self._stage,
                        path,
                    )
                    input_name = _runtime_family_input_name(path)
                    if self._trace_log_warning is None:
                        continue
                    self._trace_log_warning(
                        owner="KRM-93 CLASSIFIER",
                        process="RUNTIME MATERIAL INPUT SYNC",
                        state="SYNCHRONISED",
                        details={
                            "trigger": "usd_change",
                            "input": input_name,
                            "source_path": str(path),
                            "updated_family_count": updated_count,
                            "family_values": _runtime_family_input_values(
                                self._stage,
                                input_name,
                            ),
                        },
                    )
            finally:
                self._is_authoring = False
        relevant_paths = tuple(
            path
            for path in resynced_paths
            if _is_relevant_change(
                self._stage,
                path,
                self._geometry_ancestor_paths,
                resynced=True,
            )
        ) + tuple(
            path
            for path in changed_info_paths
            if _is_relevant_change(
                self._stage,
                path,
                self._geometry_ancestor_paths,
                resynced=False,
            )
        )
        if relevant_paths:
            self._reclassify(
                trigger="usd_change",
                trigger_details=_trace_path_details(
                    resynced_paths=resynced_paths,
                    changed_info_paths=changed_info_paths,
                    relevant_paths=relevant_paths,
                ),
            )

    def stop(self) -> None:
        self._first_frame_subscription = None
        if self._notice_key is not None:
            self._notice_key.Revoke()
            self._notice_key = None
        self._layer_owner.detach()
        self._last = None


def _is_relevant_change(
    stage: Usd.Stage,
    path: Sdf.Path,
    geometry_ancestor_paths: frozenset[str],
    *,
    resynced: bool = True,
) -> bool:
    prim_path = path.GetPrimPath()
    if prim_path.HasPrefix(Sdf.Path("/__ORMSRuntime")):
        return False
    prim = stage.GetPrimAtPath(prim_path)
    if prim and prim.IsA(UsdGeom.Camera):
        return False
    if path.IsPropertyPath():
        name = str(path).rsplit(".", 1)[-1]
        if name.startswith("inputs:"):
            return False
        if name.startswith("primvars:"):
            primvar_name = name.removeprefix("primvars:").removesuffix(
                ":indices"
            )
            return primvar_name not in DERIVED_PRIMVAR_NAMES
        if name.startswith("xformOp:"):
            return str(prim_path) in geometry_ancestor_paths
        return name in {
            "points",
            "faceVertexCounts",
            "faceVertexIndices",
            "instanceable",
            "material:binding",
            "info:mdl:sourceAsset",
            "info:mdl:sourceAsset:subIdentifier",
        }
    return resynced


_classifier: SharedRoomClassifier | None = None
_context_subscription: Any | None = None
_repository_root: Path | None = None
_runtime_settings: RuntimeClassifierSettings | None = None
_previous_rtx_face_culling: bool | None = None
_owns_rtx_face_culling_setting = False


def _enable_rtx_single_sided_culling(
    settings_interface: Any | None = None,
) -> None:
    """Enable RTX culling while the manual ORMS runtime owns the setting."""

    global _previous_rtx_face_culling, _owns_rtx_face_culling_setting
    if _owns_rtx_face_culling_setting:
        return
    if settings_interface is None:
        import carb.settings

        settings_interface = carb.settings.get_settings()
    _previous_rtx_face_culling = bool(
        settings_interface.get(_RTX_FACE_CULLING_SETTING)
    )
    settings_interface.set(_RTX_FACE_CULLING_SETTING, True)
    _owns_rtx_face_culling_setting = True
    log_room_map_warning(
        owner="KRM-93 CLASSIFIER",
        process="RUNTIME BACKFACE CULLING",
        state="ENABLED",
        details={
            "setting": _RTX_FACE_CULLING_SETTING,
            "previous_value": _previous_rtx_face_culling,
            "runtime_value": True,
            "restored_on_stop": True,
        },
    )


def _restore_rtx_single_sided_culling(
    settings_interface: Any | None = None,
) -> None:
    """Restore the renderer setting captured by the manual ORMS runtime."""

    global _previous_rtx_face_culling, _owns_rtx_face_culling_setting
    if not _owns_rtx_face_culling_setting:
        return
    if settings_interface is None:
        import carb.settings

        settings_interface = carb.settings.get_settings()
    restored_value = bool(_previous_rtx_face_culling)
    settings_interface.set(
        _RTX_FACE_CULLING_SETTING,
        restored_value,
    )
    _previous_rtx_face_culling = None
    _owns_rtx_face_culling_setting = False
    log_room_map_warning(
        owner="KRM-93 CLASSIFIER",
        process="RUNTIME BACKFACE CULLING",
        state="RESTORED",
        details={
            "setting": _RTX_FACE_CULLING_SETTING,
            "restored_value": restored_value,
        },
    )


def _on_classifier_setting_changed() -> None:
    global _runtime_settings
    if _repository_root is None:
        return
    import omni.usd

    _runtime_settings = settings_from_kit()
    _replace_active_classifier(
        omni.usd.get_context().get_stage(),
        trigger="settings_change",
    )


def _replace_active_classifier(
    stage: Usd.Stage | None,
    *,
    trigger: str,
) -> None:
    global _classifier
    if _classifier:
        _classifier.stop()
        _classifier = None
    if stage is None or _repository_root is None or _runtime_settings is None:
        return
    _classifier = SharedRoomClassifier(
        stage,
        _repository_root,
        _runtime_settings,
        trace_log_warning=log_room_map_warning,
    )
    _classifier.start(trigger=trigger)


def _on_stage_event(event: object) -> None:
    import omni.usd

    event_name = getattr(event, "event_name", "")
    if not event_name:
        return
    event_type = int(omni.usd.stage_event_type(event_name))
    opened = getattr(omni.usd.StageEventType, "OPENED", None)
    closing_types = {
        int(value)
        for value in (
            getattr(omni.usd.StageEventType, "CLOSING", None),
            getattr(omni.usd.StageEventType, "CLOSED", None),
        )
        if value is not None
    }
    if opened is not None and event_type == int(opened):
        _replace_active_classifier(
            omni.usd.get_context().get_stage(),
            trigger="stage_open",
        )
    elif event_type in closing_types:
        _replace_active_classifier(None, trigger="stage_close")


def start(
    repository_root: str | Path | None = None,
    settings: RuntimeClassifierSettings | None = None,
) -> SharedRoomClassifier:
    """Start on the already-open stage, then subscribe to later stage changes."""

    import carb.eventdispatcher
    import omni.usd

    global _context_subscription, _repository_root, _runtime_settings
    stop()
    loaded_contract = getattr(
        _room_run_classifier,
        "CLASSIFIER_CONTRACT_VERSION",
        "missing",
    )
    if loaded_contract != _EXPECTED_CLASSIFIER_CONTRACT_VERSION:
        details = {
            "loaded_contract": loaded_contract,
            "expected_contract": _EXPECTED_CLASSIFIER_CONTRACT_VERSION,
            "action": (
                "reload room_run_classifier before shared_room_classifier"
            ),
        }
        log_room_map_warning(
            owner="ORMS",
            process="runtime_classifier",
            state="CLASSIFIER_MODULE_STALE",
            details=details,
        )
        raise RuntimeError(
            "Stale room_run_classifier module; reload it before "
            "shared_room_classifier"
        )
    context = omni.usd.get_context()
    stage = context.get_stage()
    if stage is None:
        raise RuntimeError(
            "Open a USD stage before starting the ORMS classifier"
        )
    if repository_root is None:
        root_real_path = stage.GetRootLayer().realPath
        if not root_real_path:
            raise RuntimeError(
                "Pass repository_root when the stage root is anonymous"
            )
        repository_root = Path(root_real_path).resolve().parent
        while repository_root.name != "_Room_Map_Shader_RnD":
            if repository_root.parent == repository_root:
                raise RuntimeError("Could not derive the ORMS repository root")
            repository_root = repository_root.parent

    _repository_root = Path(repository_root).resolve()
    shared_room_preferences.register(_on_classifier_setting_changed)
    _runtime_settings = settings or settings_from_kit()
    _enable_rtx_single_sided_culling()
    try:
        _replace_active_classifier(stage, trigger="manual_start")
        dispatcher = carb.eventdispatcher.get_eventdispatcher()
        _context_subscription = tuple(
            dispatcher.observe_event(
                event_name=context.stage_event_name(event_type),
                on_event=_on_stage_event,
                observer_name=(
                    "orms.shared_room_classifier." f"{event_name.lower()}"
                ),
            )
            for event_name, event_type in (
                ("OPENED", omni.usd.StageEventType.OPENED),
                ("CLOSING", omni.usd.StageEventType.CLOSING),
                ("CLOSED", omni.usd.StageEventType.CLOSED),
            )
        )
    except Exception:
        _restore_rtx_single_sided_culling()
        raise
    return _classifier  # type: ignore[return-value]


def inspect() -> StageClassification | None:
    """Return the latest R&D result without exposing editable window indices."""

    return _classifier.last_classification if _classifier else None


def stop() -> None:
    """Stop subscriptions and remove only the ORMS-owned runtime sublayer."""

    global _classifier, _context_subscription, _repository_root, _runtime_settings
    if _classifier:
        _classifier.stop()
        _classifier = None
    shared_room_preferences.unregister()
    subscriptions = (
        _context_subscription
        if isinstance(_context_subscription, tuple)
        else (_context_subscription,)
    )
    for subscription in subscriptions:
        reset = getattr(subscription, "reset", None)
        if callable(reset):
            reset()
    _context_subscription = None
    _repository_root = None
    _runtime_settings = None
    _restore_rtx_single_sided_culling()
