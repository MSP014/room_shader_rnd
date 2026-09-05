# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Capture composed USD material declarations across runtime boundaries."""

from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any, TypedDict

from pxr import Sdf, Usd, UsdShade

_RUNTIME_MATERIAL_ROOT = Sdf.Path("/__ORMSRuntime/Looks")

BindingRecord = tuple[str, str]
DiagnosticRecord = tuple[str, ...]


class MaterialStateSnapshot(TypedDict):
    """Stable source-material and effective-binding diagnostic contract."""

    mesh_bindings: tuple[BindingRecord, ...]
    mesh_binding_opinions: tuple[DiagnosticRecord, ...]
    material_outputs: tuple[DiagnosticRecord, ...]
    texture_inputs: tuple[DiagnosticRecord, ...]
    unresolved_texture_inputs: tuple[str, ...]
    source_state_digest: str
    mesh_binding_counts: tuple[tuple[str, int], ...]
    mesh_binding_opinion_count: int
    subset_bindings: tuple[BindingRecord, ...]
    subset_binding_counts: tuple[tuple[str, int], ...]
    source_material_paths: tuple[str, ...]


def _resolved_asset_exists(resolved_path: str) -> bool:
    """Accept a concrete file or the first tile of a UDIM asset pattern."""

    candidates = (
        resolved_path,
        resolved_path.replace("<UDIM>", "1001"),
        resolved_path.replace("<UVTILE>", "u1_v1"),
    )
    return any(
        candidate and Path(candidate).is_file() for candidate in candidates
    )


def _asset_path_for_diagnostics(
    shader_input: UsdShade.Input,
    value: Sdf.AssetPath,
) -> str:
    """Resolve tokenised paths that USD deliberately leaves unresolved."""

    if value.resolvedPath:
        return value.resolvedPath
    for attribute_spec in shader_input.GetAttr().GetPropertyStack():
        layer_path = attribute_spec.layer.realPath
        if layer_path:
            return str((Path(layer_path).parent / value.path).resolve())
    return value.path


def _connected_sources(port: Any) -> tuple[str, ...]:
    if not port:
        return ()
    result = port.GetConnectedSources()
    sources = result[0] if isinstance(result, tuple) else result
    return tuple(
        f"{source.source.GetPrim().GetPath()}.{source.sourceName}"
        for source in sources
    )


def _property_stack_layers(prop: Any) -> str:
    layers = tuple(spec.layer.identifier for spec in prop.GetPropertyStack())
    return ",".join(layers) or "<none>"


def _surface_source(
    material: UsdShade.Material,
    render_context: str,
) -> str:
    source, source_name, source_type = material.ComputeSurfaceSource(
        render_context
    )
    if not source:
        return "<none>"
    return f"{source.GetPrim().GetPath()}.{source_name}" f":{source_type}"


def _binding_records(
    stage: Usd.Stage,
    type_name: str,
) -> tuple[tuple[str, str], ...]:
    records = []
    for prim in stage.Traverse():
        if prim.GetTypeName() != type_name:
            continue
        material, _relationship = UsdShade.MaterialBindingAPI(
            prim
        ).ComputeBoundMaterial()
        material_path = (
            str(material.GetPrim().GetPath())
            if material and material.GetPrim()
            else "<unbound>"
        )
        records.append((str(prim.GetPath()), material_path))
    return tuple(sorted(records))


def _binding_opinion_records(
    stage: Usd.Stage,
    type_name: str,
) -> tuple[tuple[str, ...], ...]:
    records = []
    for prim in stage.Traverse():
        if prim.GetTypeName() != type_name:
            continue
        for relationship in prim.GetRelationships():
            if not relationship.GetName().startswith("material:binding"):
                continue
            records.append(
                (
                    str(relationship.GetPath()),
                    f"targets={','.join(map(str, relationship.GetTargets()))}",
                    f"layers={_property_stack_layers(relationship)}",
                )
            )
    return tuple(sorted(records))


def _binding_counts(
    records: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(Counter(material for _prim, material in records).items())
    )


def _material_records(
    stage: Usd.Stage,
    material_paths: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    outputs = []
    textures = []
    unresolved = []
    for material_path in material_paths:
        prim = stage.GetPrimAtPath(material_path)
        if not prim or not prim.IsA(UsdShade.Material):
            outputs.append((material_path, "missing_material"))
            continue
        material = UsdShade.Material(prim)
        output_records = tuple(
            f"{output.GetFullName()}->{','.join(_connected_sources(output))}"
            f"[layers={_property_stack_layers(output.GetAttr())}]"
            for output in material.GetOutputs()
        )
        source_records = tuple(
            f"{context or 'universal'}={_surface_source(material, context)}"
            for context in ("", "mtlx", "mdl")
        )
        outputs.append(
            (
                material_path,
                *sorted(output_records),
                *source_records,
            )
        )
        for shader_prim in Usd.PrimRange(prim):
            if not shader_prim.IsA(UsdShade.Shader):
                continue
            shader = UsdShade.Shader(shader_prim)
            shader_id = shader.GetIdAttr().Get() or "<missing>"
            coordinate_sources = tuple(
                f"{name}={','.join(_connected_sources(shader.GetInput(name)))}"
                for name in ("texcoord", "st")
                if shader.GetInput(name)
            )
            for shader_input in shader.GetInputs():
                value = shader_input.Get()
                if not isinstance(value, Sdf.AssetPath):
                    continue
                resolved_path = _asset_path_for_diagnostics(
                    shader_input,
                    value,
                )
                resolved = _resolved_asset_exists(resolved_path)
                input_path = (
                    f"{shader_prim.GetPath()}.{shader_input.GetBaseName()}"
                )
                textures.append(
                    (
                        input_path,
                        f"shader_id={shader_id}",
                        f"authored={value.path}",
                        f"resolved={resolved_path or '<empty>'}",
                        f"resolved_file={resolved}",
                        f"layers={_property_stack_layers(shader_input.GetAttr())}",
                        *coordinate_sources,
                    )
                )
                if not resolved:
                    unresolved.append(input_path)
    return tuple(outputs), tuple(textures), tuple(sorted(unresolved))


def capture_material_state(
    stage: Usd.Stage,
    source_material_paths: tuple[str, ...] | None = None,
) -> MaterialStateSnapshot:
    """Return a stable snapshot of source materials and effective bindings."""

    mesh_bindings = _binding_records(stage, "Mesh")
    mesh_binding_opinions = _binding_opinion_records(stage, "Mesh")
    subset_bindings = _binding_records(stage, "GeomSubset")
    if source_material_paths is None:
        source_material_paths = tuple(
            sorted(
                {
                    material_path
                    for _prim_path, material_path in mesh_bindings
                    if material_path != "<unbound>"
                    and not Sdf.Path(material_path).HasPrefix(
                        _RUNTIME_MATERIAL_ROOT
                    )
                }
            )
        )
    material_outputs, texture_inputs, unresolved = _material_records(
        stage,
        source_material_paths,
    )
    source_payload = {
        "mesh_bindings": mesh_bindings,
        "mesh_binding_opinions": mesh_binding_opinions,
        "material_outputs": material_outputs,
        "texture_inputs": texture_inputs,
        "unresolved_texture_inputs": unresolved,
    }
    digest = sha256(
        json.dumps(
            source_payload,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return MaterialStateSnapshot(
        **source_payload,
        source_state_digest=digest,
        mesh_binding_counts=_binding_counts(mesh_bindings),
        mesh_binding_opinion_count=len(mesh_binding_opinions),
        subset_bindings=subset_bindings,
        subset_binding_counts=_binding_counts(subset_bindings),
        source_material_paths=source_material_paths,
    )


def material_state_log_details(
    snapshot: MaterialStateSnapshot,
    baseline: MaterialStateSnapshot | None = None,
    allowed_binding_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    """Flatten a snapshot into bounded warning-visible diagnostic fields."""

    def summarise_pairs(value: tuple[tuple[str, int], ...]) -> str:
        return ",".join(f"{name}={count}" for name, count in value) or "<none>"

    def summarise_records(value: tuple[DiagnosticRecord, ...]) -> str:
        return ";".join("|".join(record) for record in value) or "<none>"

    details: dict[str, object] = {
        "source_usd_state_digest": snapshot["source_state_digest"],
        "rendered_material_state_observable": False,
        "rendered_material_state": "unobservable_from_usd_snapshot",
        "mesh_count": len(snapshot["mesh_bindings"]),
        "mesh_binding_counts": summarise_pairs(
            snapshot["mesh_binding_counts"]
        ),
        "mesh_binding_opinion_count": snapshot["mesh_binding_opinion_count"],
        "subset_count": len(snapshot["subset_bindings"]),
        "subset_binding_counts": summarise_pairs(
            snapshot["subset_binding_counts"]
        ),
        "source_material_paths": ",".join(snapshot["source_material_paths"]),
        "source_material_outputs": summarise_records(
            snapshot["material_outputs"]
        ),
        "source_texture_inputs": summarise_records(snapshot["texture_inputs"]),
        "unresolved_texture_inputs": ",".join(
            snapshot["unresolved_texture_inputs"]
        )
        or "<none>",
    }
    if baseline is not None:
        details["baseline_source_usd_state_digest"] = baseline[
            "source_state_digest"
        ]
        details["source_usd_state_unchanged"] = (
            snapshot["source_state_digest"] == baseline["source_state_digest"]
        )
        compared_fields = (
            "mesh_bindings",
            "mesh_binding_opinions",
            "material_outputs",
            "texture_inputs",
            "unresolved_texture_inputs",
        )
        details["changed_source_usd_fields"] = (
            ",".join(
                field
                for field in compared_fields
                if snapshot[field] != baseline[field]
            )
            or "<none>"
        )
        previous_bindings = dict(baseline["mesh_bindings"])
        current_bindings = dict(snapshot["mesh_bindings"])
        changed_binding_paths = tuple(
            sorted(
                path
                for path in previous_bindings.keys() | current_bindings.keys()
                if previous_bindings.get(path) != current_bindings.get(path)
            )
        )
        unexpected_binding_paths = tuple(
            path
            for path in changed_binding_paths
            if path not in allowed_binding_paths
        )
        material_network_fields = (
            "material_outputs",
            "texture_inputs",
            "unresolved_texture_inputs",
        )
        details["source_usd_material_network_unchanged"] = all(
            snapshot[field] == baseline[field]
            for field in material_network_fields
        )
        details["changed_mesh_binding_paths"] = (
            ",".join(changed_binding_paths) or "<none>"
        )
        details["unexpected_mesh_binding_paths"] = (
            ",".join(unexpected_binding_paths) or "<none>"
        )
        details["runtime_binding_scope_valid"] = not unexpected_binding_paths
    return details
