"""Author and remove all ephemeral ORMS opinions in the Session Layer."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

from ..room_run.contracts import (
    ClassificationResult,
    ClassifierDiagnostic,
    DerivedApertureMapping,
)
from .contracts import (
    _REQUIRED_SOURCE_PRIMVARS,
    _RTX_CUTOUT_OPT_IN_ATTRIBUTE,
    CAMERA_POSITION_PRIMVAR_NAME,
    CAMERA_POSITION_PRIMVAR_PATH,
    DERIVED_APERTURE_MASK_OFFSET_U,
    DERIVED_MAP_AXIS_U,
    DERIVED_MAP_AXIS_V,
    DERIVED_MAP_ORIGIN,
    DERIVED_MAP_POSITION,
    DERIVED_MAPPING_VALID,
    DERIVED_PHYSICAL_NORMAL,
    DERIVED_PRIMARY_APERTURE_MAX_U_012,
    DERIVED_PRIMARY_APERTURE_MIN_U_012,
    DERIVED_PRIMARY_APERTURE_U_3,
    DERIVED_ROOM_AXIS_U,
    DERIVED_ROOM_AXIS_V,
    DERIVED_ROOM_DEPTH_SIZE,
    DERIVED_ROOM_GROUP_ID,
    DERIVED_ROOM_PARAMETERS,
    DERIVED_ROOM_POSITION,
    DERIVED_ROOM_SCALE,
    DERIVED_ROOM_SIZE,
    DERIVED_SLICE_START_DEPTH,
    INSTANCE_POLICY_PRESERVE,
    INSTANCE_POLICY_SESSION_DEINSTANCE,
    RuntimeClassifierSettings,
    StageClassification,
    StageExtraction,
    _diagnostic,
)
from .stage import (
    _face_vertex_indices,
    _has_room_map_material_binding,
    _has_source_authored_x1_material_binding,
    _room_map_mesh_orientation,
)


class RuntimeLayerOwner:
    """Own exactly one removable ORMS sublayer beneath the Session Layer."""

    def __init__(self, stage: Usd.Stage):
        self.stage = stage
        self.layer = Sdf.Layer.CreateAnonymous("orms_shared_rooms.usda")
        self._attached = False

    def attach(self) -> Sdf.Layer:
        """Attach the owned layer strongest beneath the existing Session Layer."""

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
        """Remove only the owned sublayer and preserve unrelated session edits."""

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
        DERIVED_ROOM_POSITION: [(0.0, 0.0, 0.0)] * face_count,
        DERIVED_ROOM_SCALE: [(1.0, 1.0, 1.0)] * face_count,
        DERIVED_MAP_ORIGIN: [(0.0, 0.0, 0.0)] * face_count,
        DERIVED_MAP_AXIS_U: [(1.0, 0.0, 0.0)] * face_count,
        DERIVED_MAP_AXIS_V: [(0.0, 1.0, 0.0)] * face_count,
        DERIVED_PHYSICAL_NORMAL: [(0.0, 0.0, 1.0)] * face_count,
        DERIVED_SLICE_START_DEPTH: [0.0] * face_count,
        DERIVED_ROOM_PARAMETERS: [(11.0, 0.0, 0.0)] * face_count,
        DERIVED_PRIMARY_APERTURE_MIN_U_012: [(0.0, -1.0, -1.0)] * face_count,
        DERIVED_PRIMARY_APERTURE_MAX_U_012: [(1.0, -1.0, -1.0)] * face_count,
        DERIVED_PRIMARY_APERTURE_U_3: [(-1.0, -1.0, 0.0)] * face_count,
        DERIVED_APERTURE_MASK_OFFSET_U: [0.0] * face_count,
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
    values[DERIVED_PHYSICAL_NORMAL][face_index] = mapping.physical_normal
    values[DERIVED_SLICE_START_DEPTH][face_index] = mapping.slice_start_depth
    values[DERIVED_PRIMARY_APERTURE_MIN_U_012][face_index] = (
        mapping.primary_aperture_min_u[:3]
    )
    values[DERIVED_PRIMARY_APERTURE_MAX_U_012][face_index] = (
        mapping.primary_aperture_max_u[:3]
    )
    values[DERIVED_PRIMARY_APERTURE_U_3][face_index] = (
        mapping.primary_aperture_min_u[3],
        mapping.primary_aperture_max_u[3],
        0.0,
    )
    values[DERIVED_APERTURE_MASK_OFFSET_U][
        face_index
    ] = mapping.aperture_mask_offset_u
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


def _world_vector_to_object(
    local_to_world: Gf.Matrix4d,
    value: object,
) -> tuple[float, float, float]:
    """Store a world-space direction in the mesh's object coordinates."""

    converted = local_to_world.GetInverse().TransformDir(Gf.Vec3d(*value))
    return tuple(float(component) for component in converted)


def _world_normal_to_object(
    local_to_world: Gf.Matrix4d,
    value: object,
) -> tuple[float, float, float]:
    """Convert a world normal into the mesh's stable object frame."""

    converted = local_to_world.GetTranspose().TransformDir(Gf.Vec3d(*value))
    return tuple(float(component) for component in converted)


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
    apertures_by_key = {
        aperture.key: aperture for aperture in extraction.apertures
    }
    with Usd.EditContext(stage, runtime_layer):
        # Initialise every face to an explicit x1-safe contract, then overwrite
        # only faces that received a validated or diagnostic classifier mapping.
        for prim_path, face_count in extraction.face_counts_by_prim:
            prim = stage.GetPrimAtPath(prim_path)
            if not prim:
                continue
            mappings = mappings_by_prim.get(prim_path, ())
            values = _mapping_defaults(face_count)
            for mapping in mappings:
                _set_mapping_values(values, mapping)
                aperture = apertures_by_key.get(mapping.aperture_key)
                if aperture is not None:
                    values[DERIVED_ROOM_POSITION][
                        mapping.face_index
                    ] = aperture.room_position_world
            primvars = UsdGeom.PrimvarsAPI(prim)
            # Group identity and scalar controls vary per face. The affine room
            # position is face-varying because it is evaluated at each vertex.
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
            _author_uniform_float_primvar(
                primvars,
                DERIVED_APERTURE_MASK_OFFSET_U,
                values[DERIVED_APERTURE_MASK_OFFSET_U],
            )
            _author_uniform_float3_primvar(
                primvars,
                DERIVED_ROOM_PARAMETERS,
                values[DERIVED_ROOM_PARAMETERS],
            )
            for name in (
                DERIVED_ROOM_AXIS_U,
                DERIVED_ROOM_AXIS_V,
                DERIVED_ROOM_POSITION,
                DERIVED_ROOM_SCALE,
                DERIVED_MAP_ORIGIN,
                DERIVED_MAP_AXIS_U,
                DERIVED_MAP_AXIS_V,
                DERIVED_PHYSICAL_NORMAL,
                DERIVED_PRIMARY_APERTURE_MIN_U_012,
                DERIVED_PRIMARY_APERTURE_MAX_U_012,
                DERIVED_PRIMARY_APERTURE_U_3,
            ):
                _author_uniform_float3_primvar(primvars, name, values[name])
            mesh = UsdGeom.Mesh(prim)
            _author_face_varying_float3_primvar(
                primvars,
                DERIVED_MAP_POSITION,
                _mapped_face_vertex_positions(mesh, mappings),
            )
            # Single-sided RTX cutout requires one coherent source orientation;
            # mixed winding remains double-sided and reports why it was skipped.
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


@dataclass(frozen=True)
class _ObjectSpacePoseFrame:
    building_root: str
    face_index: int
    room_position: tuple[float, float, float]
    room_axis_u: tuple[float, float, float]
    room_axis_v: tuple[float, float, float]
    physical_normal: tuple[float, float, float]


def _build_object_space_pose_frames(
    stage: Usd.Stage,
    classification: StageClassification,
) -> dict[str, tuple[_ObjectSpacePoseFrame, ...]]:
    """Cache the small pose-dependent frame without rerunning grouping."""

    apertures_by_key = {
        aperture.key: aperture
        for aperture in classification.extraction.apertures
    }
    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    frames_by_prim: dict[str, list[_ObjectSpacePoseFrame]] = defaultdict(list)
    for mapping in classification.result.mappings:
        aperture = apertures_by_key.get(mapping.aperture_key)
        prim = stage.GetPrimAtPath(mapping.prim_path)
        if aperture is None or not prim:
            continue
        local_to_world = xform_cache.GetLocalToWorldTransform(prim)
        room_position = local_to_world.GetInverse().Transform(
            Gf.Vec3d(*aperture.room_position_world)
        )
        frames_by_prim[mapping.prim_path].append(
            _ObjectSpacePoseFrame(
                building_root=aperture.building_root,
                face_index=mapping.face_index,
                room_position=tuple(float(value) for value in room_position),
                room_axis_u=_world_vector_to_object(
                    local_to_world,
                    mapping.room_axis_u,
                ),
                room_axis_v=_world_vector_to_object(
                    local_to_world,
                    mapping.room_axis_v,
                ),
                physical_normal=_world_normal_to_object(
                    local_to_world,
                    mapping.physical_normal,
                ),
            )
        )
    return {
        prim_path: tuple(frames)
        for prim_path, frames in frames_by_prim.items()
    }


def _refresh_pose_primvars(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    frames_by_prim: Mapping[str, Sequence[_ObjectSpacePoseFrame]],
    building_roots: frozenset[str],
) -> int:
    """Update world-space shader inputs after a rigid building pose edit."""

    if not building_roots:
        return 0
    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    updated_faces = 0
    with Sdf.ChangeBlock(), Usd.EditContext(stage, runtime_layer):
        for prim_path, all_frames in frames_by_prim.items():
            frames = tuple(
                frame
                for frame in all_frames
                if frame.building_root in building_roots
            )
            if not frames:
                continue
            prim = stage.GetPrimAtPath(prim_path)
            if not prim:
                continue
            primvars = UsdGeom.PrimvarsAPI(prim)
            values = {}
            for name in (
                DERIVED_ROOM_POSITION,
                DERIVED_ROOM_AXIS_U,
                DERIVED_ROOM_AXIS_V,
                DERIVED_PHYSICAL_NORMAL,
            ):
                authored = primvars.GetPrimvar(name).Get()
                if authored is None:
                    break
                values[name] = list(authored)
            else:
                local_to_world = xform_cache.GetLocalToWorldTransform(prim)
                normal_transform = local_to_world.GetInverse().GetTranspose()
                for frame in frames:
                    face_index = frame.face_index
                    values[DERIVED_ROOM_POSITION][face_index] = (
                        local_to_world.Transform(
                            Gf.Vec3d(*frame.room_position)
                        )
                    )
                    values[DERIVED_ROOM_AXIS_U][face_index] = (
                        local_to_world.TransformDir(
                            Gf.Vec3d(*frame.room_axis_u)
                        )
                    )
                    values[DERIVED_ROOM_AXIS_V][face_index] = (
                        local_to_world.TransformDir(
                            Gf.Vec3d(*frame.room_axis_v)
                        )
                    )
                    values[DERIVED_PHYSICAL_NORMAL][face_index] = (
                        normal_transform.TransformDir(
                            Gf.Vec3d(*frame.physical_normal)
                        )
                    )
                    updated_faces += 1
                for name, authored_values in values.items():
                    _author_uniform_float3_primvar(
                        primvars,
                        name,
                        authored_values,
                    )
    return updated_faces


def _prototype_has_room_map_mesh(prototype: Usd.Prim) -> bool:
    for prim in Usd.PrimRange(prototype):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        primvars = UsdGeom.PrimvarsAPI(prim)
        if all(
            primvars.GetPrimvar(name) for name in _REQUIRED_SOURCE_PRIMVARS
        ) and _has_room_map_material_binding(prim):
            return True
    return False


def author_camera_position_primvar(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
) -> Sdf.Path | None:
    """Author the inherited camera channel used by preserved instances."""

    world = stage.GetPrimAtPath("/World")
    if not world:
        return None
    primvars = UsdGeom.PrimvarsAPI(world)
    existing = primvars.GetPrimvar(CAMERA_POSITION_PRIMVAR_NAME)
    if existing:
        return existing.GetAttr().GetPath()
    with Usd.EditContext(stage, runtime_layer):
        primvar = primvars.CreatePrimvar(
            CAMERA_POSITION_PRIMVAR_NAME,
            Sdf.ValueTypeNames.Float3,
            UsdGeom.Tokens.constant,
        )
        primvar.Set(Gf.Vec3f(0.0))
    return primvar.GetAttr().GetPath()


def seed_camera_position_primvar(
    stage: Usd.Stage,
    world_position: Sequence[float],
) -> Sdf.Path | None:
    """Seed the inherited camera channel before the first material sync."""

    world = stage.GetPrimAtPath("/World")
    if not world:
        return None
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        primvar = UsdGeom.PrimvarsAPI(world).CreatePrimvar(
            CAMERA_POSITION_PRIMVAR_NAME,
            Sdf.ValueTypeNames.Float3,
            UsdGeom.Tokens.constant,
        )
        primvar.Set(Gf.Vec3f(*world_position))
    return primvar.GetAttr().GetPath()


def camera_position_primvar_exists(stage: Usd.Stage) -> bool:
    """Return whether the composed stage declared the camera channel already."""

    world = stage.GetPrimAtPath("/World")
    if not world:
        return False
    return bool(
        UsdGeom.PrimvarsAPI(world).GetPrimvar(CAMERA_POSITION_PRIMVAR_NAME)
    )


def _primvar_has_varying_values(primvar: UsdGeom.Primvar) -> bool:
    if not primvar:
        return False
    values = primvar.ComputeFlattened()
    if not values:
        return False
    return len({tuple(value) for value in values}) > 1


def _preserved_instance_diagnostic(prim: Usd.Prim) -> ClassifierDiagnostic:
    proxy_meshes = tuple(
        proxy
        for proxy in Usd.PrimRange(
            prim,
            Usd.TraverseInstanceProxies(),
        )
        if proxy.IsA(UsdGeom.Mesh)
        and all(
            UsdGeom.PrimvarsAPI(proxy).GetPrimvar(name)
            for name in _REQUIRED_SOURCE_PRIMVARS
        )
        and _has_source_authored_x1_material_binding(proxy)
    )
    camera_primvars = tuple(
        UsdGeom.PrimvarsAPI(proxy).FindPrimvarWithInheritance(
            CAMERA_POSITION_PRIMVAR_NAME
        )
        for proxy in proxy_meshes
    )
    room_uv_varying_count = sum(
        _primvar_has_varying_values(
            UsdGeom.PrimvarsAPI(proxy).GetPrimvar("roomUV")
        )
        for proxy in proxy_meshes
    )
    st_varying_count = sum(
        _primvar_has_varying_values(
            UsdGeom.PrimvarsAPI(proxy).GetPrimvar("st")
        )
        for proxy in proxy_meshes
    )
    camera_primvar_count = sum(bool(primvar) for primvar in camera_primvars)
    has_x1_fallback = bool(proxy_meshes) and (
        room_uv_varying_count == len(proxy_meshes)
        and camera_primvar_count == len(proxy_meshes)
    )
    material_paths = sorted(
        {
            str(
                UsdShade.MaterialBindingAPI(proxy)
                .ComputeBoundMaterial()[0]
                .GetPath()
            )
            for proxy in proxy_meshes
        }
    )
    camera_values = sorted(
        {
            tuple(float(value) for value in primvar.Get())
            for primvar in camera_primvars
            if primvar and primvar.Get() is not None
        }
    )
    return _diagnostic(
        (
            "INSTANCE_PRESERVED_X1_FALLBACK"
            if has_x1_fallback
            else "INSTANCE_PRESERVED_WITHOUT_X1_FALLBACK"
        ),
        str(prim.GetPath()),
        fallback_render_path=(
            "source_authored_x1_binding" if has_x1_fallback else "unavailable"
        ),
        instance_policy=INSTANCE_POLICY_PRESERVE,
        requirement="prototype-bound room_map_single material",
        source_x1_proxy_count=len(proxy_meshes),
        source_x1_proxy_paths=",".join(
            str(proxy.GetPath()) for proxy in proxy_meshes
        ),
        source_material_paths=",".join(material_paths),
        room_uv_varying_proxy_count=room_uv_varying_count,
        st_varying_proxy_count=st_varying_count,
        camera_primvar_path=CAMERA_POSITION_PRIMVAR_PATH,
        camera_primvar_inherited_proxy_count=camera_primvar_count,
        camera_primvar_values=camera_values,
    )


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
        return tuple(_preserved_instance_diagnostic(prim) for prim in affected)
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
            material.GetPrim().CreateAttribute(
                _RTX_CUTOUT_OPT_IN_ATTRIBUTE,
                Sdf.ValueTypeNames.Bool,
                custom=False,
            ).Set(True)
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
            shader.CreateInput("enable_opacity", Sdf.ValueTypeNames.Bool).Set(
                True
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
