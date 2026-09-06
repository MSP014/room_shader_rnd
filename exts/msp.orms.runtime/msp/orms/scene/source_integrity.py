# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Prove that one temporary ORMS run leaves its source stage unchanged."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from msp.orms.shared_room.material_diagnostics import (
    MaterialStateSnapshot,
    capture_material_state,
)
from pxr import Sdf, Usd

_SIDECAR_TOKENS = (".orms.", "adapter")


@dataclass(frozen=True)
class SourceFileState:
    """Identify one file-backed layer by exact bytes and filesystem metadata."""

    path: str
    size: int
    modified_ns: int
    digest: str


@dataclass(frozen=True)
class SourceLayerState:
    """Record the non-runtime properties needed to audit one source layer."""

    identifier: str
    real_path: str
    dirty: bool
    sublayers: tuple[str, ...]
    orms_spec_paths: tuple[str, ...]


@dataclass(frozen=True)
class StageSourceState:
    """Stable before/after state for a loaded source stage."""

    stage_identity: int
    root_identifier: str
    files: tuple[SourceFileState, ...]
    layers: tuple[SourceLayerState, ...]
    material_state: MaterialStateSnapshot
    instance_paths: tuple[str, ...]
    prototype_signatures: tuple[tuple[tuple[str, str], ...], ...]
    point_instancer_signature: tuple[tuple[str, tuple[str, ...]], ...]
    sidecar_entries: tuple[str, ...]


def _file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_layers(stage: Usd.Stage) -> tuple[Any, ...]:
    """Return only file-backed layers; anonymous ORMS layers are not sources."""

    return tuple(
        sorted(
            (layer for layer in stage.GetUsedLayers() if layer.realPath),
            key=lambda layer: str(Path(layer.realPath).resolve()).casefold(),
        )
    )


def _orms_spec_paths(layer: Any) -> tuple[str, ...]:
    paths: list[str] = []

    def visit(path: Sdf.Path) -> None:
        path_text = str(path)
        if "orms" in path_text.casefold():
            paths.append(path_text)

    layer.Traverse(Sdf.Path.absoluteRootPath, visit)
    return tuple(sorted(paths))


def _source_file_state(layer: Any) -> SourceFileState:
    path = Path(layer.realPath).resolve()
    stat = path.stat()
    return SourceFileState(
        path=str(path),
        size=stat.st_size,
        modified_ns=stat.st_mtime_ns,
        digest=_file_digest(path),
    )


def _source_layer_state(layer: Any) -> SourceLayerState:
    return SourceLayerState(
        identifier=layer.identifier,
        real_path=str(Path(layer.realPath).resolve()),
        dirty=bool(layer.dirty),
        sublayers=tuple(layer.subLayerPaths),
        orms_spec_paths=_orms_spec_paths(layer),
    )


def _instance_paths(stage: Usd.Stage) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(prim.GetPath())
            for prim in stage.Traverse()
            if prim.IsInstance()
        )
    )


def _prototype_signatures(
    stage: Usd.Stage,
) -> tuple[tuple[tuple[str, str], ...], ...]:
    signatures = []
    for prototype in stage.GetPrototypes():
        root_path = prototype.GetPath()
        signatures.append(
            tuple(
                (
                    str(prim.GetPath().MakeRelativePath(root_path)),
                    prim.GetTypeName(),
                )
                for prim in Usd.PrimRange(prototype)
            )
        )
    return tuple(sorted(signatures))


def _point_instancer_signature(
    stage: Usd.Stage,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    result = []
    for prim in stage.Traverse():
        if prim.GetTypeName() != "PointInstancer":
            continue
        relationship = prim.GetRelationship("prototypes")
        result.append(
            (
                str(prim.GetPath()),
                tuple(map(str, relationship.GetTargets())),
            )
        )
    return tuple(sorted(result))


def _sidecar_entries(layers: tuple[Any, ...]) -> tuple[str, ...]:
    directories = {Path(layer.realPath).resolve().parent for layer in layers}
    entries = []
    for directory in directories:
        try:
            children = directory.iterdir()
        except OSError:
            continue
        for child in children:
            name = child.name.casefold()
            if any(token in name for token in _SIDECAR_TOKENS):
                entries.append(str(child.resolve()))
    return tuple(sorted(entries, key=str.casefold))


def capture_stage_source_state(stage: Usd.Stage) -> StageSourceState:
    """Capture source bytes, composition identity, bindings, and instancing."""

    layers = _source_layers(stage)
    return StageSourceState(
        stage_identity=id(stage),
        root_identifier=stage.GetRootLayer().identifier,
        files=tuple(_source_file_state(layer) for layer in layers),
        layers=tuple(_source_layer_state(layer) for layer in layers),
        material_state=capture_material_state(
            stage,
            include_instance_proxies=True,
        ),
        instance_paths=_instance_paths(stage),
        prototype_signatures=_prototype_signatures(stage),
        point_instancer_signature=_point_instancer_signature(stage),
        sidecar_entries=_sidecar_entries(layers),
    )


def source_integrity_details(
    baseline: StageSourceState,
    restored: StageSourceState,
) -> dict[str, object]:
    """Return explicit evidence for every source-safety acceptance clause."""

    baseline_files = {item.path: item for item in baseline.files}
    restored_files = {item.path: item for item in restored.files}
    source_file_inventory_unchanged = (
        baseline_files.keys() == restored_files.keys()
    )
    source_file_bytes_unchanged = source_file_inventory_unchanged and all(
        restored_files[path].digest == item.digest
        and restored_files[path].size == item.size
        and restored_files[path].modified_ns == item.modified_ns
        for path, item in baseline_files.items()
    )
    baseline_layers = {item.real_path: item for item in baseline.layers}
    restored_layers = {item.real_path: item for item in restored.layers}
    source_layer_inventory_unchanged = (
        baseline_layers.keys() == restored_layers.keys()
    )
    source_layer_structure_unchanged = (
        source_layer_inventory_unchanged
        and all(
            restored_layers[path].identifier == item.identifier
            and restored_layers[path].sublayers == item.sublayers
            and restored_layers[path].orms_spec_paths == item.orms_spec_paths
            and restored_layers[path].dirty == item.dirty
            for path, item in baseline_layers.items()
        )
    )
    material_bindings_restored = (
        restored.material_state["mesh_bindings"]
        == baseline.material_state["mesh_bindings"]
        and restored.material_state["mesh_binding_opinions"]
        == baseline.material_state["mesh_binding_opinions"]
        and restored.material_state["subset_bindings"]
        == baseline.material_state["subset_bindings"]
    )
    source_material_networks_restored = all(
        restored.material_state[field] == baseline.material_state[field]
        for field in (
            "material_outputs",
            "texture_inputs",
            "unresolved_texture_inputs",
        )
    )
    details: dict[str, object] = {
        "same_stage_object": restored.stage_identity
        == baseline.stage_identity,
        "same_root_layer": restored.root_identifier
        == baseline.root_identifier,
        "source_file_count": len(restored.files),
        "source_file_inventory_unchanged": source_file_inventory_unchanged,
        "source_file_bytes_unchanged": source_file_bytes_unchanged,
        "source_layer_inventory_unchanged": source_layer_inventory_unchanged,
        "source_layer_structure_unchanged": source_layer_structure_unchanged,
        "material_bindings_restored": material_bindings_restored,
        "source_material_networks_restored": source_material_networks_restored,
        "instance_signature_unchanged": (
            restored.instance_paths == baseline.instance_paths
        ),
        "usd_prototype_count_before": len(baseline.prototype_signatures),
        "usd_prototype_count_after": len(restored.prototype_signatures),
        "usd_prototype_count_unchanged": (
            len(restored.prototype_signatures)
            == len(baseline.prototype_signatures)
        ),
        "usd_prototype_structure_unchanged": (
            restored.prototype_signatures == baseline.prototype_signatures
        ),
        "point_instancer_signature_unchanged": (
            restored.point_instancer_signature
            == baseline.point_instancer_signature
        ),
        "new_sidecar_or_adapter_entries": ",".join(
            sorted(
                set(restored.sidecar_entries) - set(baseline.sidecar_entries)
            )
        )
        or "<none>",
    }
    details["source_integrity_passed"] = (
        all(
            value is True
            for key, value in details.items()
            if key
            not in {
                "source_file_count",
                "usd_prototype_count_before",
                "usd_prototype_count_after",
                "new_sidecar_or_adapter_entries",
            }
        )
        and details["new_sidecar_or_adapter_entries"] == "<none>"
    )
    return details
