"""Own reversible default ORMS material assignment for eligible window meshes."""

from __future__ import annotations

from dataclasses import dataclass

from pxr import Sdf, Usd, UsdGeom, UsdShade

from .resources import is_room_map_source_asset
from .stage_visibility import hide_in_stage_window

_AUTO_ASSIGN_ATTRIBUTE = "orms:autoAssign"
_AUTO_ASSIGN_LAYER_NAME = "orms_auto_assignment.usda"
_AUTO_ASSIGN_ROOT = Sdf.Path("/__ORMSAutoAssignment")
_AUTO_ASSIGN_MATERIAL_PATH = _AUTO_ASSIGN_ROOT.AppendPath("Looks/RoomMap")
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


@dataclass(frozen=True)
class AssignmentResult:
    """Summarise one reversible auto-assignment pass."""

    decisions: tuple[AssignmentDecision, ...]
    assigned_prim_paths: tuple[str, ...]
    layer_identifier: str


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


def _is_auto_assignment_candidate(
    prim: Usd.Prim,
    material: UsdShade.Material | None,
) -> bool:
    """Recognise legacy meshes and semantic meshes below a window container."""

    if _normalised_name(prim.GetName()) == _WINDOWS_GLASS_NAME:
        return True
    ancestor = prim.GetParent()
    while ancestor:
        if _normalised_name(ancestor.GetName()) == _WINDOWS_CONTAINER_NAME:
            return True
        ancestor = ancestor.GetParent()
    auto_assign = prim.GetAttribute(_AUTO_ASSIGN_ATTRIBUTE)
    if auto_assign and auto_assign.HasAuthoredValueOpinion():
        if auto_assign.Get() is True:
            return True
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


def evaluate_windows_glass(stage: Usd.Stage) -> tuple[AssignmentDecision, ...]:
    """Return decisions for Windows Glass meshes with a valid ORMS contract."""

    decisions = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        material = _bound_material(prim)
        if not _is_auto_assignment_candidate(prim, material):
            continue
        if material is not None and _uses_room_map_source_asset(material):
            continue
        source_material_path = (
            str(material.GetPath()) if material is not None else "<unbound>"
        )

        auto_assign = prim.GetAttribute(_AUTO_ASSIGN_ATTRIBUTE)
        if auto_assign and auto_assign.HasAuthoredValueOpinion():
            if auto_assign.Get() is False:
                decisions.append(
                    AssignmentDecision(
                        str(prim.GetPath()),
                        source_material_path,
                        False,
                        "explicitly_excluded",
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
                )
            )
            continue
        decisions.append(
            AssignmentDecision(
                str(prim.GetPath()),
                source_material_path,
                True,
                "windows_glass_contract_valid",
            )
        )
    return tuple(decisions)


def _author_seed_material(
    stage: Usd.Stage,
    source_asset_path: str,
    atlas_asset_path: str,
    atlas_variant_count: int,
) -> UsdShade.Material:
    """Author the smallest ready ORMS material consumed by the classifier."""

    root = UsdGeom.Scope.Define(stage, _AUTO_ASSIGN_ROOT)
    hide_in_stage_window(root.GetPrim())
    UsdGeom.Scope.Define(stage, _AUTO_ASSIGN_ROOT.AppendPath("Looks"))
    material = UsdShade.Material.Define(stage, _AUTO_ASSIGN_MATERIAL_PATH)
    shader = UsdShade.Shader.Define(
        stage,
        _AUTO_ASSIGN_MATERIAL_PATH.AppendPath("Shader"),
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
    ).Set("room_map")
    shader.CreateInput("room_atlas", Sdf.ValueTypeNames.Asset).Set(
        Sdf.AssetPath(atlas_asset_path)
    )
    shader.CreateInput("room_variant_count", Sdf.ValueTypeNames.Int).Set(
        max(int(atlas_variant_count), 1)
    )
    shader.CreateInput("enable_opacity", Sdf.ValueTypeNames.Bool).Set(True)
    shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput("mdl").ConnectToSource(shader_output)
    return material


class AutoAssignmentOwner:
    """Author and remove only the default assignment opinions owned by ORMS."""

    def __init__(
        self,
        stage: Usd.Stage,
        *,
        source_asset_path: str,
        atlas_asset_path: str,
        atlas_variant_count: int,
    ) -> None:
        self._stage = stage
        self._source_asset_path = source_asset_path
        self._atlas_asset_path = atlas_asset_path
        self._atlas_variant_count = atlas_variant_count
        self._layer = Sdf.Layer.CreateAnonymous(_AUTO_ASSIGN_LAYER_NAME)
        self._attached = False

    @property
    def layer_identifier(self) -> str:
        return self._layer.identifier

    def apply(self) -> AssignmentResult:
        """Assign ORMS to valid Windows Glass meshes in an ephemeral layer."""

        decisions = evaluate_windows_glass(self._stage)
        assigned_paths = tuple(
            decision.prim_path for decision in decisions if decision.eligible
        )
        if not assigned_paths:
            return AssignmentResult(decisions, (), self.layer_identifier)

        session_layer = self._stage.GetSessionLayer()
        sublayers = list(session_layer.subLayerPaths)
        if self._layer.identifier not in sublayers:
            sublayers.insert(0, self._layer.identifier)
            session_layer.subLayerPaths = sublayers
        self._attached = True
        try:
            with Usd.EditContext(self._stage, self._layer):
                material = _author_seed_material(
                    self._stage,
                    self._source_asset_path,
                    self._atlas_asset_path,
                    self._atlas_variant_count,
                )
                for prim_path in assigned_paths:
                    prim = self._stage.GetPrimAtPath(prim_path)
                    UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
        except Exception:
            self.stop()
            raise
        return AssignmentResult(
            decisions,
            assigned_paths,
            self.layer_identifier,
        )

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
