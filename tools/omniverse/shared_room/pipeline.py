"""Compose stage interpretation, pure classification, and USD authoring."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from pxr import Sdf, Usd, UsdShade

from ..interior_sets.contracts import InteriorSetCollection
from ..interior_sets.runtime_resources import (
    InteriorSetRuntimeResources,
    InteriorSetRuntimeSnapshot,
)
from ..interior_sets.selectors import assign_apertures
from ..room_run.classifier import classify_apertures
from ..runtime.resources import RuntimeResources, coerce_runtime_resources
from .authoring import (
    apply_instance_policy,
    author_camera_position_primvar,
    author_derived_primvars,
    author_family_bindings,
    author_family_materials,
    camera_position_primvar_required,
)
from .contracts import (
    ClassificationPhaseCallback,
    RuntimeClassifierSettings,
    StageClassification,
    StageExtraction,
)
from .interior_set_authoring import (
    author_interior_set_materials,
    window_paths_by_set,
)
from .interior_set_diagnostics import build_interior_set_diagnostics
from .stage import extract_stage_apertures, resolve_stage_metrics


def _runtime_family_input_summary(
    materials: Mapping[object, UsdShade.Material],
    input_name: str,
) -> str:
    """Describe one authored input for every runtime atlas family."""

    values = []
    for family_key, material in sorted(
        materials.items(),
        key=lambda item: str(item[0]),
    ):
        value: object = "MISSING"
        for prim in Usd.PrimRange(material.GetPrim()):
            shader = UsdShade.Shader(prim)
            shader_input = shader.GetInput(input_name) if shader else None
            if not shader_input:
                continue
            value = shader_input.Get()
            if isinstance(value, Sdf.AssetPath):
                value = value.path
            break
        if isinstance(family_key, tuple):
            label = f"{family_key[0]}:x{family_key[1]}"
        else:
            label = f"x{family_key}"
        values.append(f"{label}={value}")
    return ",".join(values)


def classify_stage(
    stage: Usd.Stage,
    runtime_layer: Sdf.Layer,
    settings: RuntimeClassifierSettings,
    resources_or_repository_root: RuntimeResources | Path,
    phase_callback: ClassificationPhaseCallback | None = None,
    material_input_values: Mapping[str, object] | None = None,
    interior_sets: InteriorSetCollection | None = None,
    interior_set_resources: InteriorSetRuntimeSnapshot | None = None,
) -> StageClassification:
    """Classify one already-open stage and author its ephemeral mapping."""

    resources = coerce_runtime_resources(resources_or_repository_root)
    legacy_configuration = (
        interior_sets is None and interior_set_resources is None
    )
    configured_sets = interior_sets or InteriorSetCollection.default_only()
    runtime_resources = interior_set_resources
    if runtime_resources is None:
        if len(configured_sets.sets) != 1:
            raise ValueError(
                "Every configured Interior Set requires runtime resources"
            )
        runtime_resources = InteriorSetRuntimeSnapshot(
            (
                InteriorSetRuntimeResources(
                    set_id=configured_sets.default.set_id,
                    resources=resources,
                ),
            )
        )
    configured_ids = tuple(item.set_id for item in configured_sets.sets)
    runtime_ids = tuple(item.set_id for item in runtime_resources.sets)
    if configured_ids != runtime_ids:
        raise ValueError(
            "Interior Set configuration and runtime resources disagree"
        )

    def report_phase(phase: str, **details: object) -> None:
        if phase_callback is not None:
            phase_callback(phase, details)

    # Establish composition and resource policy before extracting geometry. All
    # authored opinions target the caller-owned ephemeral runtime layer.
    camera_position_primvar_path = (
        author_camera_position_primvar(stage, runtime_layer)
        if camera_position_primvar_required(stage)
        else None
    )
    instance_diagnostics = apply_instance_policy(
        stage, runtime_layer, settings
    )
    metrics = resolve_stage_metrics(stage, settings)
    available_room_sizes = frozenset(
        room_size
        for room_sizes in (
            runtime_resources.available_room_sizes_by_set.values()
        )
        for room_size in room_sizes
    )
    extraction = extract_stage_apertures(stage, metrics)
    assigned_apertures, selector_resolutions = assign_apertures(
        extraction.apertures,
        configured_sets,
    )
    extraction = StageExtraction(
        apertures=assigned_apertures,
        source_prim_paths=extraction.source_prim_paths,
        source_material_paths=extraction.source_material_paths,
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
    # The pure classifier receives metre-space descriptors and has no pxr or Kit
    # dependency; its deterministic result is reproducible in unit tests.
    result = classify_apertures(
        extraction.apertures,
        settings.core_settings(
            available_room_sizes,
            available_room_sizes_by_set=(
                runtime_resources.available_room_sizes_by_set
            ),
            incoherent_interior_set_ids=(runtime_resources.incoherent_set_ids),
        ),
        up_axis=metrics.up_axis,
    )
    summary = result.summary
    interior_set_diagnostics = build_interior_set_diagnostics(
        configured_sets,
        extraction,
        result,
        selector_resolutions,
        runtime_resources,
    )
    report_phase(
        "CLASSIFICATION_COMPLETE",
        group_count=len(result.groups),
        mapping_count=len(result.mappings),
        diagnostic_count=len(result.diagnostics),
        spacing_model=summary.spacing_model,
        building_count=summary.building_count,
        row_count=summary.row_count,
        facade_count=summary.facade_count,
        straight_candidate_count=summary.straight_candidate_count,
        transition_candidate_count=summary.transition_candidate_count,
        accepted_straight_edge_count=summary.accepted_straight_edge_count,
        accepted_transition_edge_count=summary.accepted_transition_edge_count,
        rejected_room_id_edge_count=summary.rejected_room_id_edge_count,
        rejected_interior_set_edge_count=(
            summary.rejected_interior_set_edge_count
        ),
        rejected_spacing_edge_count=summary.rejected_spacing_edge_count,
        local_pitch_min_metres=summary.local_pitch_min_metres,
        local_pitch_max_metres=summary.local_pitch_max_metres,
        group_size_counts=",".join(
            f"x{size}={count}" for size, count in summary.group_size_counts
        ),
        interior_set_count=interior_set_diagnostics.active_set_count,
        aperture_counts=repr(interior_set_diagnostics.aperture_counts),
        room_size_counts_by_set=repr(
            interior_set_diagnostics.room_size_counts
        ),
        default_fallback_paths=",".join(
            interior_set_diagnostics.default_fallback_paths
        ),
        selector_conflict_count=len(interior_set_diagnostics.conflicts),
        selector_conflicts=repr(
            tuple(
                (
                    conflict.prim_path,
                    conflict.winning_set_id,
                    conflict.matching_set_ids,
                )
                for conflict in interior_set_diagnostics.conflicts
            )
        ),
    )
    # Author direct shader inputs instead of rediscovering adjacency or expanding
    # affine mappings inside the per-fragment MDL graph.
    culling_diagnostics = author_derived_primvars(
        stage,
        runtime_layer,
        extraction,
        result,
    )
    if culling_diagnostics:
        extraction = StageExtraction(
            apertures=extraction.apertures,
            source_prim_paths=extraction.source_prim_paths,
            source_material_paths=extraction.source_material_paths,
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
        camera_position_primvar_path=(
            camera_position_primvar_path or "unavailable"
        ),
    )
    preserved_source_x1_count = sum(
        diagnostic.state == "INSTANCE_PRESERVED_X1_FALLBACK"
        for diagnostic in extraction.diagnostics
    )
    # Keep every available atlas family alive while the stage runtime exists.
    # Family toggles change only grouping and subset indices. Destroying an MDL
    # material on disable and recreating it on enable leaves newly rebound
    # faces transparent while RTX recompiles the material.
    materials: dict[object, UsdShade.Material] = {}
    if result.mappings and legacy_configuration:
        materials = author_family_materials(
            stage,
            runtime_layer,
            resources,
            available_room_sizes,
            tuple(sorted({item.prim_path for item in result.mappings})),
            material_input_values,
        )
    elif result.mappings:
        materials = author_interior_set_materials(
            stage,
            runtime_layer,
            configured_sets,
            runtime_resources,
            window_paths_by_set(result.mappings),
            legacy_default_values=material_input_values,
        )
    report_phase(
        "RUNTIME_MATERIALS_AUTHORED",
        material_count=len(materials),
        material_paths=",".join(
            str(material.GetPath()) for material in materials.values()
        ),
        room_sizes=",".join(
            (f"{key[0]}:x{key[1]}" if isinstance(key, tuple) else f"x{key}")
            for key in sorted(materials, key=str)
        ),
        atlas_assets=_runtime_family_input_summary(
            materials,
            "room_atlas",
        ),
        atlas_variant_counts=_runtime_family_input_summary(
            materials,
            "room_variant_count",
        ),
    )
    interior_set_diagnostics = replace(
        interior_set_diagnostics,
        generated_material_paths=tuple(
            str(material.GetPath()) for material in materials.values()
        ),
    )
    subset_count, direct_mesh_binding_count = (
        author_family_bindings(
            stage,
            runtime_layer,
            result,
            materials,
        )
        if materials
        else (0, 0)
    )
    report_phase(
        "RUNTIME_BINDINGS_AUTHORED",
        subset_count=subset_count,
        direct_mesh_binding_count=direct_mesh_binding_count,
        preserved_source_x1_count=preserved_source_x1_count,
    )
    return StageClassification(
        metrics=metrics,
        available_room_sizes=available_room_sizes,
        extraction=extraction,
        result=result,
        runtime_layer_identifier=runtime_layer.identifier,
        selector_resolutions=selector_resolutions,
        interior_set_diagnostics=interior_set_diagnostics,
    )
