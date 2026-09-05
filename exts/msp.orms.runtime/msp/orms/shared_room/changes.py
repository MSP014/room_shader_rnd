# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Classify USD notices as pose refreshes or geometric invalidations."""

from __future__ import annotations

from collections.abc import Sequence
from math import isclose

from pxr import Gf, Sdf, Usd, UsdGeom

from ..scene.resources import is_room_map_source_asset
from .contracts import RUNTIME_OWNED_PRIMVAR_NAMES
from .stage import _has_room_map_material_binding


def _is_dependency_path(
    prim_path: Sdf.Path,
    ancestor_paths: frozenset[str],
    dependency_root_paths: frozenset[str],
) -> bool:
    """Return whether a prim can alter an established ORMS dependency."""

    if str(prim_path) in ancestor_paths:
        return True
    return any(
        prim_path.HasPrefix(Sdf.Path(root)) for root in dependency_root_paths
    )


def _defines_room_map_shader(prim: Usd.Prim) -> bool:
    """Recognise a newly authored ORMS MDL source outside known dependencies."""

    if not prim:
        return False
    source_asset = prim.GetAttribute("info:mdl:sourceAsset")
    value = source_asset.Get() if source_asset else None
    return bool(value and is_room_map_source_asset(value.path))


def _building_root_transform_change_roots(
    paths: Sequence[Sdf.Path],
    building_root_paths: frozenset[str],
) -> frozenset[str]:
    roots = set()
    for path in paths:
        if not path.IsPropertyPath():
            continue
        prim_path = str(path.GetPrimPath())
        if prim_path not in building_root_paths:
            continue
        name = str(path).rsplit(".", 1)[-1]
        if name == "xformOpOrder" or name.startswith("xformOp:"):
            roots.add(prim_path)
    return frozenset(roots)


def _building_root_shape_signatures(
    stage: Usd.Stage,
    building_root_paths: Sequence[str],
) -> dict[str, tuple[float, ...]]:
    """Capture scale/shear while ignoring root translation and rotation."""

    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    signatures = {}
    for root in building_root_paths:
        prim = stage.GetPrimAtPath(root)
        if not prim:
            continue
        transform = xform_cache.GetLocalToWorldTransform(prim)
        axes = tuple(
            transform.TransformDir(axis)
            for axis in (
                Gf.Vec3d(1.0, 0.0, 0.0),
                Gf.Vec3d(0.0, 1.0, 0.0),
                Gf.Vec3d(0.0, 0.0, 1.0),
            )
        )
        signatures[root] = (
            axes[0] * axes[0],
            axes[1] * axes[1],
            axes[2] * axes[2],
            axes[0] * axes[1],
            axes[0] * axes[2],
            axes[1] * axes[2],
        )
    return signatures


def _shape_signatures_match(
    previous: tuple[float, ...] | None,
    current: tuple[float, ...],
) -> bool:
    return previous is not None and all(
        isclose(old, new, rel_tol=1e-9, abs_tol=1e-9)
        for old, new in zip(previous, current, strict=True)
    )


def _pose_change_roots(
    paths: Sequence[Sdf.Path],
    building_root_paths: frozenset[str],
) -> frozenset[str]:
    """Return roots whose rigid pose changed without affecting grouping."""

    roots = set()
    for path in paths:
        if not path.IsPropertyPath():
            continue
        prim_path = str(path.GetPrimPath())
        if prim_path not in building_root_paths:
            continue
        name = str(path).rsplit(".", 1)[-1]
        if name == "xformOpOrder" or name.startswith("xformOp:"):
            roots.add(prim_path)
    return frozenset(roots)


def _is_relevant_change(
    stage: Usd.Stage,
    path: Sdf.Path,
    geometry_ancestor_paths: frozenset[str],
    building_root_paths: frozenset[str] = frozenset(),
    changed_building_shape_roots: frozenset[str] = frozenset(),
    *,
    source_prim_root_paths: frozenset[str] = frozenset(),
    source_material_ancestor_paths: frozenset[str] = frozenset(),
    source_material_root_paths: frozenset[str] = frozenset(),
    resynced: bool = True,
) -> bool:
    prim_path = path.GetPrimPath()
    if prim_path.HasPrefix(Sdf.Path("/__ORMSRuntime")):
        return False
    prim = stage.GetPrimAtPath(prim_path)
    if prim and prim.IsA(UsdGeom.Camera):
        return False
    geometry_dependency = _is_dependency_path(
        prim_path,
        geometry_ancestor_paths,
        building_root_paths | source_prim_root_paths,
    )
    material_dependency = _is_dependency_path(
        prim_path,
        source_material_ancestor_paths,
        source_material_root_paths,
    )
    if path.IsPropertyPath():
        name = str(path).rsplit(".", 1)[-1]
        if name.startswith("inputs:"):
            return False
        if name.startswith("primvars:"):
            primvar_name = name.removeprefix("primvars:").removesuffix(
                ":indices"
            )
            return (
                geometry_dependency
                and primvar_name not in RUNTIME_OWNED_PRIMVAR_NAMES
            )
        if name.startswith("xformOp:"):
            prim_path_text = str(prim_path)
            if prim_path_text not in geometry_ancestor_paths:
                return False
            if prim_path_text in building_root_paths:
                return prim_path_text in changed_building_shape_roots
            return True
        if name == "xformOpOrder" and str(prim_path) in building_root_paths:
            return str(prim_path) in changed_building_shape_roots
        if name in {
            "points",
            "faceVertexCounts",
            "faceVertexIndices",
            "instanceable",
        }:
            return geometry_dependency
        if name == "material:binding":
            # A new manual binding can bring an otherwise unrelated mesh into
            # ORMS ownership; removal remains covered by the previous scope.
            return geometry_dependency or bool(
                prim
                and prim.IsA(UsdGeom.Mesh)
                and _has_room_map_material_binding(prim)
            )
        if name in {
            "info:mdl:sourceAsset",
            "info:mdl:sourceAsset:subIdentifier",
        }:
            # A source-asset edit can introduce a new ORMS seed outside the
            # previous material dependency tree.
            return material_dependency or _defines_room_map_shader(prim)
        return False
    newly_bound_mesh = bool(
        prim
        and prim.IsA(UsdGeom.Mesh)
        and _has_room_map_material_binding(prim)
    )
    return resynced and (
        geometry_dependency or material_dependency or newly_bound_mesh
    )
