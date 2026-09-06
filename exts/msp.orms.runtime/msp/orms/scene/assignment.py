# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Own reversible default ORMS material assignment for eligible window meshes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

from ..interior_sets.selectors import selector_matches
from ..shared_room.material_controls import (
    MATERIAL_INPUT_TYPES,
    SINGLE_MATERIAL_INPUT_NAMES,
    material_input_values_from_mapping,
)
from .assignment_overrides import AUTO_ASSIGN_ATTRIBUTE
from .resources import is_room_map_source_asset
from .stage_visibility import hide_in_stage_window
from .traversal import iter_composed_prims

_AUTO_ASSIGN_LAYER_NAME = "orms_auto_assignment.usda"
_AUTO_ASSIGN_ROOT = Sdf.Path("/__ORMSAutoAssignment")
_AUTO_ASSIGN_MATERIAL_PATH = _AUTO_ASSIGN_ROOT.AppendPath("Looks/RoomMap")
_INSTANCE_MATERIAL_RELATIVE_PATH = Sdf.Path("mtl/ORMSRoomMapSingle")
_REQUIRED_SOURCE_PRIMVARS = (
    "roomID",
    "roomP",
    "tangentu",
    "tangentv",
    "roomUV",
)
_WINDOWS_GLASS_NAME = "windowsglass"
_WINDOWS_CONTAINER_NAME = "windows"


@dataclass(frozen=True)
class AssignmentDecision:
    """Explain whether one Windows Glass mesh is safe for auto-assignment."""

    prim_path: str
    source_material_path: str
    eligible: bool
    reason: str
    override_editable: bool = True


@dataclass(frozen=True)
class AssignmentResult:
    """Summarise one reversible auto-assignment pass."""

    decisions: tuple[AssignmentDecision, ...]
    assigned_prim_paths: tuple[str, ...]
    layer_identifier: str
    preserved_instance_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class _InstanceClassOverlay:
    """Map eligible proxies onto one existing source-class namespace."""

    root_path: Sdf.Path
    source_class_path: Sdf.Path
    proxy_paths: tuple[Sdf.Path, ...]


def _normalised_name(value: str) -> str:
    """Normalise common USD-safe variants of a Windows Glass identity."""

    return "".join(
        character for character in value.lower() if character.isalnum()
    )


def _bound_material(prim: Usd.Prim) -> UsdShade.Material | None:
    material, relationship = UsdShade.MaterialBindingAPI(
        prim
    ).ComputeBoundMaterial()
    return material if relationship and material else None


def _selector_matches_prim(mask: str, prim: Usd.Prim) -> bool:
    """Match a bare mesh-name mask or a complete composed-path mask."""

    candidate = str(prim.GetPath()) if "/" in mask else prim.GetName()
    return selector_matches(mask, candidate)


def _is_auto_assignment_candidate(
    prim: Usd.Prim,
    material: UsdShade.Material | None,
    candidate_selectors: tuple[str, ...] | None,
) -> bool:
    """Recognise configured meshes or the legacy compatibility identities."""

    auto_assign = prim.GetAttribute(AUTO_ASSIGN_ATTRIBUTE)
    if auto_assign and auto_assign.HasAuthoredValueOpinion():
        return True
    if candidate_selectors is not None and any(
        _selector_matches_prim(mask, prim) for mask in candidate_selectors
    ):
        return True

    if _normalised_name(prim.GetName()) == _WINDOWS_GLASS_NAME:
        return True
    ancestor = prim.GetParent()
    while ancestor:
        if _normalised_name(ancestor.GetName()) == _WINDOWS_CONTAINER_NAME:
            return True
        ancestor = ancestor.GetParent()
    if material is None:
        return False
    return (
        _normalised_name(material.GetPrim().GetName()) == _WINDOWS_GLASS_NAME
    )


def _uses_room_map_source_asset(material: UsdShade.Material) -> bool:
    for candidate in Usd.PrimRange(material.GetPrim()):
        source_asset = candidate.GetAttribute("info:mdl:sourceAsset").Get()
        if source_asset and is_room_map_source_asset(source_asset.path):
            return True
    return False


def _missing_source_primvars(mesh: UsdGeom.Mesh) -> tuple[str, ...]:
    primvars = UsdGeom.PrimvarsAPI(mesh)
    return tuple(
        name
        for name in _REQUIRED_SOURCE_PRIMVARS
        if not primvars.GetPrimvar(name)
    )


def _has_supported_topology(mesh: UsdGeom.Mesh) -> bool:
    counts = tuple(mesh.GetFaceVertexCountsAttr().Get() or ())
    return bool(counts) and all(count == 4 for count in counts)


def evaluate_windows_glass(
    stage: Usd.Stage,
    candidate_selectors: tuple[str, ...] | None = None,
) -> tuple[AssignmentDecision, ...]:
    """Return decisions for selector-matched meshes with a valid contract."""

    decisions = []
    for prim in iter_composed_prims(
        stage,
        include_instance_proxies=True,
    ):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        material = _bound_material(prim)
        if not _is_auto_assignment_candidate(
            prim,
            material,
            candidate_selectors,
        ):
            continue
        if material is not None and _uses_room_map_source_asset(material):
            continue
        source_material_path = (
            str(material.GetPath()) if material is not None else "<unbound>"
        )

        auto_assign = prim.GetAttribute(AUTO_ASSIGN_ATTRIBUTE)
        if auto_assign and auto_assign.HasAuthoredValueOpinion():
            if auto_assign.Get() is False:
                decisions.append(
                    AssignmentDecision(
                        str(prim.GetPath()),
                        source_material_path,
                        False,
                        "explicitly_excluded",
                        not prim.IsInstanceProxy(),
                    )
                )
                continue

        mesh = UsdGeom.Mesh(prim)
        missing = _missing_source_primvars(mesh)
        if missing:
            decisions.append(
                AssignmentDecision(
                    str(prim.GetPath()),
                    source_material_path,
                    False,
                    "missing_primvars:" + ",".join(missing),
                    not prim.IsInstanceProxy(),
                )
            )
            continue
        if not _has_supported_topology(mesh):
            decisions.append(
                AssignmentDecision(
                    str(prim.GetPath()),
                    source_material_path,
                    False,
                    "unsupported_topology",
                    not prim.IsInstanceProxy(),
                )
            )
            continue
        decisions.append(
            AssignmentDecision(
                str(prim.GetPath()),
                source_material_path,
                True,
                "windows_glass_contract_valid",
                not prim.IsInstanceProxy(),
            )
        )
    return tuple(decisions)


def _instance_root(prim: Usd.Prim) -> Usd.Prim | None:
    """Return the authorable instance root that owns one instance proxy."""

    current = prim
    while current and current.IsInstanceProxy():
        current = current.GetParent()
    return current if current and current.IsInstance() else None


def _instance_proxy_paths_by_root(
    stage: Usd.Stage,
    decisions: tuple[AssignmentDecision, ...],
) -> dict[str, tuple[Sdf.Path, ...]]:
    """Group eligible proxy targets under their authorable instance roots."""

    paths_by_root: dict[str, list[Sdf.Path]] = {}
    for decision in decisions:
        if not decision.eligible:
            continue
        prim = stage.GetPrimAtPath(decision.prim_path)
        if not prim.IsInstanceProxy():
            continue
        root = _instance_root(prim)
        if root:
            paths_by_root.setdefault(str(root.GetPath()), []).append(
                prim.GetPath()
            )
    return {
        root_path: tuple(sorted(paths))
        for root_path, paths in sorted(paths_by_root.items())
    }


def _existing_source_class_path(root: Usd.Prim) -> Sdf.Path | None:
    """Return the one unambiguous class already inherited by the source."""

    direct_inherits = tuple(root.GetInherits().GetAllDirectInherits())
    if len(direct_inherits) != 1:
        return None
    class_path = direct_inherits[0]
    return class_path if class_path.IsAbsolutePath() else None


def _instance_class_overlays(
    stage: Usd.Stage,
    paths_by_root: Mapping[str, tuple[Sdf.Path, ...]],
) -> tuple[tuple[_InstanceClassOverlay, ...], frozenset[str]]:
    """Plan class-local bindings without adding composition arcs."""

    overlays = []
    unsupported_paths = set()
    for root_path, proxy_paths in paths_by_root.items():
        root = stage.GetPrimAtPath(root_path)
        source_class_path = _existing_source_class_path(root)
        if source_class_path is None:
            unsupported_paths.update(str(path) for path in proxy_paths)
            continue
        overlays.append(
            _InstanceClassOverlay(
                root.GetPath(),
                source_class_path,
                proxy_paths,
            )
        )
    return tuple(overlays), frozenset(unsupported_paths)


def _author_seed_material(
    stage: Usd.Stage,
    material_path: Sdf.Path,
    source_asset_path: str,
    atlas_asset_path: str,
    atlas_variant_count: int,
    material_input_values: Mapping[str, object],
    *,
    subidentifier: str,
    supported_input_names: frozenset[str] | None = None,
) -> UsdShade.Material:
    """Author one ready ORMS material with the active artist profile."""

    owner_root_path = material_path.GetParentPath().GetParentPath()
    owner_root = stage.GetPrimAtPath(owner_root_path)
    if not owner_root:
        owner_root = UsdGeom.Scope.Define(stage, owner_root_path).GetPrim()
    if owner_root_path == _AUTO_ASSIGN_ROOT:
        hide_in_stage_window(owner_root)
    UsdGeom.Scope.Define(stage, material_path.GetParentPath())
    material = UsdShade.Material.Define(stage, material_path)
    shader = UsdShade.Shader.Define(
        stage,
        material_path.AppendPath("Shader"),
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
    ).Set(Sdf.AssetPath(source_asset_path))
    shader_prim.CreateAttribute(
        "info:mdl:sourceAsset:subIdentifier",
        Sdf.ValueTypeNames.Token,
        custom=False,
    ).Set(subidentifier)
    shader.CreateInput("room_atlas", Sdf.ValueTypeNames.Asset).Set(
        Sdf.AssetPath(atlas_asset_path)
    )
    shader.CreateInput("room_variant_count", Sdf.ValueTypeNames.Int).Set(
        max(int(atlas_variant_count), 1)
    )
    for name, value in material_input_values.items():
        if name not in MATERIAL_INPUT_TYPES or (
            supported_input_names is not None
            and name not in supported_input_names
        ):
            continue
        value_type = MATERIAL_INPUT_TYPES.get(name)
        if value_type is not None:
            shader.CreateInput(name, value_type).Set(value)
    if supported_input_names is None:
        shader.CreateInput("enable_opacity", Sdf.ValueTypeNames.Bool).Set(True)
    shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput("mdl").ConnectToSource(shader_output)
    return material


def _author_instance_class_overlays(
    stage: Usd.Stage,
    overlays: tuple[_InstanceClassOverlay, ...],
    source_asset_path: str,
    atlas_asset_path: str,
    atlas_variant_count: int,
    material_input_values: Mapping[str, object],
) -> tuple[Sdf.Path, ...]:
    """Bind windows through source classes already authored by Houdini.

    No inherit, reference, payload, or instance-root opinion is authored.  The
    x1 material lives below the existing class so inheritance maps its target
    into the corresponding instance-local material namespace.
    """

    relative_paths_by_class: dict[Sdf.Path, set[Sdf.Path]] = {}
    for overlay in overlays:
        relative_paths_by_class.setdefault(
            overlay.source_class_path,
            set(),
        ).update(
            path.MakeRelativePath(overlay.root_path)
            for path in overlay.proxy_paths
        )

    material_paths = []
    for class_path, relative_paths in sorted(
        relative_paths_by_class.items(),
        key=lambda item: str(item[0]),
    ):
        stage.CreateClassPrim(class_path)
        material_path = class_path.AppendPath(_INSTANCE_MATERIAL_RELATIVE_PATH)
        material = _author_seed_material(
            stage,
            material_path,
            source_asset_path,
            atlas_asset_path,
            atlas_variant_count,
            material_input_values,
            subidentifier="room_map_single",
            supported_input_names=SINGLE_MATERIAL_INPUT_NAMES,
        )
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(material_path.AppendPath("Shader"))
        )
        shader.CreateInput(
            "camera_position_world",
            Sdf.ValueTypeNames.Float3,
        ).Set(Gf.Vec3f(0.0))
        for relative_path in sorted(relative_paths):
            window_overlay = stage.OverridePrim(
                class_path.AppendPath(relative_path)
            )
            UsdShade.MaterialBindingAPI.Apply(window_overlay).Bind(material)
        material_paths.append(material_path)
    return tuple(material_paths)


class AutoAssignmentOwner:
    """Author and remove only the default assignment opinions owned by ORMS."""

    def __init__(
        self,
        stage: Usd.Stage,
        *,
        source_asset_path: str,
        atlas_asset_path: str,
        atlas_variant_count: int,
        instance_source_asset_path: str | None = None,
        material_input_values: Mapping[str, object] | None = None,
        candidate_selectors: tuple[str, ...] | None = None,
    ) -> None:
        self._stage = stage
        self._source_asset_path = source_asset_path
        self._atlas_asset_path = atlas_asset_path
        self._atlas_variant_count = atlas_variant_count
        self._instance_source_asset_path = (
            instance_source_asset_path or source_asset_path
        )
        self._material_input_values = material_input_values_from_mapping(
            material_input_values or {}
        )
        self._candidate_selectors = candidate_selectors
        self._layer = Sdf.Layer.CreateAnonymous(_AUTO_ASSIGN_LAYER_NAME)
        self._attached = False
        self._instance_material_paths: tuple[Sdf.Path, ...] = ()

    @property
    def layer_identifier(self) -> str:
        return self._layer.identifier

    @property
    def runtime_layer(self) -> Sdf.Layer | None:
        """Return the attached assignment layer used for early camera seeding."""

        return self._layer if self._attached else None

    def _attach(self) -> None:
        """Attach the assignment layer before authoring composed-stage state."""

        if self._attached:
            return
        session_layer = self._stage.GetSessionLayer()
        sublayers = list(session_layer.subLayerPaths)
        if self._layer.identifier not in sublayers:
            sublayers.insert(0, self._layer.identifier)
            session_layer.subLayerPaths = sublayers
        self._attached = True

    def apply(self) -> AssignmentResult:
        """Assign ORMS to valid Windows Glass meshes in an ephemeral layer."""

        decisions = evaluate_windows_glass(
            self._stage,
            self._candidate_selectors,
        )
        instance_paths_by_root = _instance_proxy_paths_by_root(
            self._stage,
            decisions,
        )
        instance_overlays, unsupported_proxy_paths = _instance_class_overlays(
            self._stage,
            instance_paths_by_root,
        )
        decisions = tuple(
            (
                replace(
                    decision,
                    eligible=False,
                    reason="native_instance_source_class_unavailable",
                )
                if decision.prim_path in unsupported_proxy_paths
                else decision
            )
            for decision in decisions
        )
        assigned_paths = tuple(
            decision.prim_path for decision in decisions if decision.eligible
        )
        if not assigned_paths:
            return AssignmentResult(decisions, (), self.layer_identifier)

        self._attach()
        try:
            with Usd.EditContext(self._stage, self._layer):
                direct_paths = tuple(
                    prim_path
                    for prim_path in assigned_paths
                    if not self._stage.GetPrimAtPath(
                        prim_path
                    ).IsInstanceProxy()
                )
                if direct_paths:
                    material = _author_seed_material(
                        self._stage,
                        _AUTO_ASSIGN_MATERIAL_PATH,
                        self._source_asset_path,
                        self._atlas_asset_path,
                        self._atlas_variant_count,
                        self._material_input_values,
                        subidentifier="room_map",
                    )
                for prim_path in direct_paths:
                    prim = self._stage.GetPrimAtPath(prim_path)
                    UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
                if instance_overlays:
                    self._instance_material_paths = (
                        _author_instance_class_overlays(
                            self._stage,
                            instance_overlays,
                            self._instance_source_asset_path,
                            self._atlas_asset_path,
                            self._atlas_variant_count,
                            self._material_input_values,
                        )
                    )
        except Exception:
            self.stop()
            raise
        return AssignmentResult(
            decisions,
            assigned_paths,
            self.layer_identifier,
            tuple(str(overlay.root_path) for overlay in instance_overlays),
        )

    def set_material_input_values(
        self,
        values: Mapping[str, object],
    ) -> int:
        """Update the owned direct-assignment material from one profile."""

        if not self._attached:
            return 0
        merged_values = dict(self._material_input_values)
        merged_values.update(values)
        normalised_values = material_input_values_from_mapping(merged_values)
        changed_names = tuple(
            name for name in values if name in MATERIAL_INPUT_TYPES
        )
        updated_count = 0
        with Usd.EditContext(self._stage, self._layer):
            material_targets = (
                (_AUTO_ASSIGN_MATERIAL_PATH, MATERIAL_INPUT_TYPES),
                *(
                    (material_path, SINGLE_MATERIAL_INPUT_NAMES)
                    for material_path in self._instance_material_paths
                ),
            )
            for material_path, supported_input_names in material_targets:
                shader = UsdShade.Shader(
                    self._stage.GetPrimAtPath(
                        material_path.AppendPath("Shader")
                    )
                )
                if not shader:
                    continue
                for name in changed_names:
                    if name not in supported_input_names:
                        continue
                    shader_input = shader.GetInput(name)
                    value = normalised_values[name]
                    if shader_input and shader_input.Get() != value:
                        shader_input.Set(value)
                        updated_count += 1
        self._material_input_values = normalised_values
        return updated_count

    def stop(self) -> None:
        """Remove the owned layer and reveal every original source binding."""

        if not self._attached:
            return
        session_layer = self._stage.GetSessionLayer()
        session_layer.subLayerPaths = [
            identifier
            for identifier in session_layer.subLayerPaths
            if identifier != self._layer.identifier
        ]
        self._attached = False
        self._instance_material_paths = ()
