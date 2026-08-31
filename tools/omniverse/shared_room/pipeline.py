"""Compose stage interpretation, pure classification, and USD authoring."""

from __future__ import annotations

from pathlib import Path

from pxr import Sdf, Usd

from ..room_run.classifier import classify_apertures
from .authoring import (
    apply_instance_policy,
    author_camera_position_primvar,
    author_derived_primvars,
    author_family_bindings,
    author_family_materials,
)
from .contracts import (
    ClassificationPhaseCallback,
    RuntimeClassifierSettings,
    StageClassification,
    StageExtraction,
)
from .stage import (
    discover_atlas_family_availability,
    extract_stage_apertures,
    resolve_stage_metrics,
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

    # Establish composition and resource policy before extracting geometry. All
    # authored opinions target the caller-owned ephemeral runtime layer.
    camera_position_primvar_path = author_camera_position_primvar(
        stage,
        runtime_layer,
    )
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
    # The pure classifier receives metre-space descriptors and has no pxr or Kit
    # dependency; its deterministic result is reproducible in unit tests.
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
    usable_room_sizes = (
        settings.core_settings(available_room_sizes).enabled_room_sizes
        & available_room_sizes
    )
    preserved_source_x1_count = sum(
        diagnostic.state == "INSTANCE_PRESERVED_X1_FALLBACK"
        for diagnostic in extraction.diagnostics
    )
    # Reuse at most one material per available atlas family, then bind subsets
    # so every aperture has exactly one effective x1-x4 material.
    materials = (
        author_family_materials(
            stage,
            runtime_layer,
            repository_root,
            usable_room_sizes,
        )
        if result.mappings
        else {}
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
        preserved_source_x1_count=preserved_source_x1_count,
    )
    return StageClassification(
        metrics=metrics,
        available_room_sizes=available_room_sizes,
        extraction=extraction,
        result=result,
        runtime_layer_identifier=runtime_layer.identifier,
    )
