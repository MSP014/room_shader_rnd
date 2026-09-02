"""Interpret a composed OpenUSD stage as metre-space ORMS apertures."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pxr import Gf, Usd, UsdGeom, UsdShade

from ..room_run.contracts import ApertureDescriptor, ClassifierDiagnostic
from ..runtime.resources import (
    ROOM_MAP_MDL_FILENAME,
    ROOM_MAP_SINGLE_MDL_FILENAME,
    RuntimeResources,
    coerce_runtime_resources,
    mdl_source_asset_name,
)
from .contracts import (
    _REQUIRED_SOURCE_PRIMVARS,
    METRICS_MODE_AUTO,
    METRICS_MODE_LOCAL_OVERRIDE,
    ResolvedStageMetrics,
    RuntimeClassifierSettings,
    StageExtraction,
    _diagnostic,
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
    resources_or_repository_root: RuntimeResources | Path,
) -> frozenset[int]:
    """Return the x1 through x4 families validated by the resource boundary."""

    resources = coerce_runtime_resources(resources_or_repository_root)
    return resources.available_room_sizes


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


def _bound_material_using_source_asset(
    prim: Usd.Prim,
    source_asset_names: Sequence[str],
) -> UsdShade.Material | None:
    material, relationship = UsdShade.MaterialBindingAPI(
        prim
    ).ComputeBoundMaterial()
    if not relationship or not material:
        return None
    for candidate in Usd.PrimRange(material.GetPrim()):
        source_asset = candidate.GetAttribute("info:mdl:sourceAsset").Get()
        if (
            source_asset
            and mdl_source_asset_name(source_asset.path) in source_asset_names
        ):
            return material
    return None


def _bound_material_uses_source_asset(
    prim: Usd.Prim,
    source_asset_names: Sequence[str],
) -> bool:
    return bool(_bound_material_using_source_asset(prim, source_asset_names))


def _has_room_map_material_binding(prim: Usd.Prim) -> bool:
    return _bound_material_uses_source_asset(
        prim,
        (ROOM_MAP_MDL_FILENAME, ROOM_MAP_SINGLE_MDL_FILENAME),
    )


def stage_has_room_map_source_mesh(stage: Usd.Stage) -> bool:
    """Return whether the composed stage contains runtime-readable ORMS work."""

    return any(
        prim.IsA(UsdGeom.Mesh) and _has_room_map_material_binding(prim)
        for prim in stage.Traverse()
    )


def _has_source_authored_x1_material_binding(prim: Usd.Prim) -> bool:
    return _bound_material_uses_source_asset(
        prim,
        (ROOM_MAP_SINGLE_MDL_FILENAME,),
    )


def extract_stage_apertures(
    stage: Usd.Stage,
    metrics: ResolvedStageMetrics,
) -> StageExtraction:
    """Extract one descriptor per supported mesh face from the composed stage."""

    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    apertures = []
    source_prim_paths = []
    source_material_paths = set()
    face_counts_by_prim = []
    diagnostics = []

    # Traverse only composed meshes already bound to a Room Map source material;
    # unrelated stage geometry never enters classifier ownership.
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        source_material = _bound_material_using_source_asset(
            prim,
            (ROOM_MAP_MDL_FILENAME, ROOM_MAP_SINGLE_MDL_FILENAME),
        )
        if source_material is None:
            continue
        source_prim_paths.append(str(prim.GetPath()))
        source_material_paths.add(str(source_material.GetPath()))
        mesh = UsdGeom.Mesh(prim)
        primvars = UsdGeom.PrimvarsAPI(mesh)
        source_primvars = {
            name: primvars.GetPrimvar(name)
            for name in _REQUIRED_SOURCE_PRIMVARS
        }
        missing_primvars = tuple(
            name for name, primvar in source_primvars.items() if not primvar
        )
        if missing_primvars:
            diagnostics.append(
                _diagnostic(
                    "MISSING_SOURCE_PRIMVARS",
                    str(prim.GetPath()),
                    primvars=",".join(missing_primvars),
                )
            )
            continue

        faces = _face_vertex_indices(mesh)
        points = mesh.GetPointsAttr().Get() or ()
        if not faces or not points:
            continue
        face_counts_by_prim.append((str(prim.GetPath()), len(faces)))
        world_transform = xform_cache.GetLocalToWorldTransform(prim)
        face_vertex_offset = 0

        # The accepted source contract is one planar quad per aperture. Other
        # topology remains in the stage but receives a structured diagnostic.
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
            room_position = _primvar_value_for_face(
                source_primvars["roomP"],
                face_index,
                point_indices,
                face_vertex_offset,
            )
            if (
                room_id is None
                or tangent_u is None
                or tangent_v is None
                or room_position is None
            ):
                diagnostics.append(
                    _diagnostic(
                        "INVALID_SOURCE_PRIMVARS",
                        str(prim.GetPath()),
                        face_index=face_index,
                    )
                )
                face_vertex_offset += len(point_indices)
                continue

            # Pure classification uses metres regardless of authored stage units,
            # while the retained room position remains in world-space stage units.
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
                    room_position_world=tuple(
                        float(value)
                        for value in _world_point(
                            world_transform,
                            room_position,
                        )
                    ),
                )
            )
            face_vertex_offset += len(point_indices)

    return StageExtraction(
        apertures=tuple(apertures),
        source_prim_paths=tuple(sorted(source_prim_paths)),
        source_material_paths=tuple(sorted(source_material_paths)),
        face_counts_by_prim=tuple(sorted(face_counts_by_prim)),
        diagnostics=tuple(diagnostics),
    )
