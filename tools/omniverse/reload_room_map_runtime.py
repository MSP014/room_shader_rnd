"""Reload and start the manual ORMS runtime from exact repository source."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

if __package__:
    from .runtime.diagnostics import corner_box_summaries
    from .runtime.source_loader import (
        RuntimeSourceLoader,
        stop_runtime_modules,
    )
else:
    import sys

    # Kit's Script Editor uses runpy.run_path(), which deliberately executes
    # this entry point without a package.  Expose the checkout root so the same
    # canonical imports work in both standalone and package execution modes.
    _SOURCE_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
    _source_repository_text = str(_SOURCE_REPOSITORY_ROOT)
    if _source_repository_text not in sys.path:
        sys.path.insert(0, _source_repository_text)
    from tools.omniverse.runtime.diagnostics import corner_box_summaries
    from tools.omniverse.runtime.source_loader import (
        RuntimeSourceLoader,
        stop_runtime_modules,
    )

_CONTRACT_VERSION = "shared_room_runtime_v48"
_INTERIOR_SET_DEPENDENCY_ORDER = (
    "interior_set_atlas_mode",
    "interior_set_identity",
    "interior_set_manifest",
    "interior_set_contracts",
    "interior_set_selectors",
    "interior_set_runtime_resources",
)
_ROOM_RUN_DEPENDENCY_ORDER = (
    "room_run_contracts",
    "room_run_topology",
    "room_run_mapping",
)
_SHARED_ROOM_DEPENDENCY_ORDER = (
    "shared_room_contracts",
    "shared_room_stage",
    "shared_room_settings",
    "shared_room_material_controls",
    "shared_room_authoring",
    "shared_room_interior_set_authoring",
    "shared_room_interior_set_diagnostics",
    "shared_room_pipeline",
    "shared_room_changes",
    "shared_room_material_diagnostics",
)


def _load_runtime_stack(
    loader: RuntimeSourceLoader,
) -> tuple[ModuleType, ModuleType, ModuleType, ModuleType, ModuleType]:
    """Load and validate the dependency graph around the active stage probe."""

    status = loader.load("status_log")
    status.log_room_map_warning(
        owner="SCENE LOAD PROBE",
        process="RUNTIME LOADER",
        state="LOADER_INVOKED",
        details={
            "classifier_contract": _CONTRACT_VERSION,
            "coverage": "from_this_log_forward",
        },
    )
    loader.load("runtime_resource_metrics")
    resources = loader.load("runtime_resources")
    for module_name in _INTERIOR_SET_DEPENDENCY_ORDER:
        loader.load(module_name)
    loader.load("runtime_stage_visibility")
    loader.load("stage_load_state")
    stage_probe = loader.load("stage_load_probe")
    stage_probe.start()

    for module_name in _ROOM_RUN_DEPENDENCY_ORDER:
        loader.load(module_name)
    core = loader.load("room_run_classifier")
    loaded_contract = getattr(core, "CLASSIFIER_CONTRACT_VERSION", "missing")
    if loaded_contract != _CONTRACT_VERSION:
        raise RuntimeError(
            "Unexpected ORMS classifier contract: "
            f"loaded={loaded_contract}, expected={_CONTRACT_VERSION}"
        )

    for module_name in _SHARED_ROOM_DEPENDENCY_ORDER:
        loader.load(module_name)
    loader.load("runtime_renderer_settings")
    shared = loader.load("shared_room_classifier")
    bridge = loader.load("camera_position_bridge")
    shared.log_room_map_warning(
        owner="SHARED ROOM CLASSIFIER",
        process="RUNTIME SOURCE LOAD",
        state="SOURCE_MODULES_LOADED",
        details={
            "classifier_contract": loaded_contract,
            "room_run_classifier": core.__file__,
            "shared_room_classifier": shared.__file__,
            "camera_position_bridge": bridge.__file__,
            "stage_load_probe": stage_probe.__file__,
        },
    )
    return stage_probe, core, shared, bridge, resources


def _seed_initial_camera(shared: ModuleType, bridge: ModuleType):
    """Seed the inherited camera primvar before material realisation starts."""

    import omni.usd

    stage = omni.usd.get_context().get_stage()
    initial_camera_position = bridge.active_camera_world_position(stage)
    camera_primvar_required = bool(
        stage is not None and shared.camera_position_primvar_required(stage)
    )
    camera_primvar_preexisting = bool(
        stage is not None and shared.camera_position_primvar_exists(stage)
    )
    if (
        stage is not None
        and initial_camera_position is not None
        and camera_primvar_required
    ):
        camera_primvar_path = shared.seed_camera_position_primvar(
            stage,
            initial_camera_position,
        )
        shared.log_room_map_warning(
            owner="CAMERA POSITION BRIDGE",
            process="INITIAL CAMERA POSITION SEED",
            state="ACTIVE",
            details={
                "attribute_path": camera_primvar_path or "unavailable",
                "world_position": initial_camera_position,
                "before_classifier_start": True,
                "preexisting_before_runtime": camera_primvar_preexisting,
                "source_contract": (
                    "predeclared"
                    if camera_primvar_preexisting
                    else "late_runtime_authored"
                ),
            },
        )
    else:
        shared.log_room_map_warning(
            owner="CAMERA POSITION BRIDGE",
            process="INITIAL CAMERA POSITION SEED",
            state="UNAVAILABLE",
            details={
                "stage_available": stage is not None,
                "camera_available": initial_camera_position is not None,
                "camera_primvar_required": camera_primvar_required,
                "before_classifier_start": True,
                "preexisting_before_runtime": camera_primvar_preexisting,
            },
        )


def reload_and_start(
    repository_root: str | Path,
    *,
    mdl_source_asset: str | None = None,
    atlas_families: tuple[tuple[int, str, int], ...] | None = None,
    interior_sets=None,
    interior_set_resources=None,
):
    """Replace cached ORMS modules with exact source and start the runtime."""

    root = Path(repository_root).resolve()
    loader = RuntimeSourceLoader(root)
    loader.prepare()
    _stage_probe, _core, shared, bridge, resources = _load_runtime_stack(
        loader
    )

    runtime_resources = None
    if mdl_source_asset is not None or atlas_families is not None:
        if mdl_source_asset is None or atlas_families is None:
            raise ValueError(
                "Pass both mdl_source_asset and atlas_families for packaged ORMS"
            )
        runtime_resources = resources.RuntimeResources(
            mdl_source_asset=mdl_source_asset,
            atlas_families=tuple(
                resources.RuntimeAtlasFamily(
                    room_size,
                    asset_path,
                    variant_count,
                )
                for room_size, asset_path, variant_count in atlas_families
            ),
        )

    _seed_initial_camera(shared, bridge)
    classifier = shared.start(
        root,
        resources=runtime_resources,
        interior_sets=interior_sets,
        interior_set_resources=interior_set_resources,
    )
    corner_summaries = corner_box_summaries(classifier.last_classification)
    shared.log_room_map_warning(
        owner="SHARED ROOM CLASSIFIER",
        process="RUNTIME SOURCE LOAD",
        state="CORNER_BOXES_AUTHORED",
        details={
            "corner_count": len(corner_summaries),
            "corners": "; ".join(corner_summaries),
        },
    )
    camera_bridge = bridge.start(classifier.camera_input_paths)
    return classifier, camera_bridge


def stop_runtime() -> None:
    """Stop every import route that may own callbacks or subscriptions."""

    stop_runtime_modules()
