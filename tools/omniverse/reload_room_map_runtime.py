"""Load the manual ORMS R&D runtime from repository source, bypassing caches."""

from __future__ import annotations

import sys
import tokenize
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

_CONTRACT_VERSION = "krm93_packed_mapping_v12"


def _stop_loaded_module(name: str) -> None:
    module = sys.modules.get(name)
    stop = getattr(module, "stop", None)
    if callable(stop):
        stop()


def _load_source_module(name: str, source_path: Path) -> ModuleType:
    """Execute one exact source file without consulting import bytecode."""

    with tokenize.open(str(source_path)) as source_file:
        source = source_file.read()
    module = ModuleType(name)
    module.__file__ = str(source_path)
    module.__package__ = ""
    module.__spec__ = ModuleSpec(name, loader=None, origin=str(source_path))
    sys.modules[name] = module
    try:
        exec(  # nosec B102 -- executes a fixed, repository-owned module path.
            compile(source, str(source_path), "exec"),
            module.__dict__,
        )
    except Exception:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise
    return module


def reload_and_start(repository_root: str | Path):
    """Replace cached ORMS modules with exact repository source and start."""

    root = Path(repository_root).resolve()
    module_root = root / "tools" / "omniverse"
    source_paths = {
        "status_log": module_root / "status_log.py",
        "stage_load_probe": module_root / "stage_load_probe.py",
        "room_run_classifier": module_root / "room_run_classifier.py",
        "shared_room_classifier": module_root / "shared_room_classifier.py",
        "camera_position_bridge": module_root / "camera_position_bridge.py",
    }
    missing = tuple(
        str(path) for path in source_paths.values() if not path.is_file()
    )
    if missing:
        raise FileNotFoundError(f"Missing ORMS runtime source: {missing}")

    module_root_text = str(module_root)
    if module_root_text not in sys.path:
        sys.path.insert(0, module_root_text)

    for module_name in (
        "stage_load_probe",
        "tools.omniverse.stage_load_probe",
        "shared_room_classifier",
        "tools.omniverse.shared_room_classifier",
        "camera_position_bridge",
        "tools.omniverse.camera_position_bridge",
    ):
        _stop_loaded_module(module_name)

    status = _load_source_module(
        "status_log",
        source_paths["status_log"],
    )
    status.log_room_map_warning(
        owner="SCENE LOAD PROBE",
        process="RUNTIME LOADER",
        state="LOADER_INVOKED",
        details={
            "classifier_contract": _CONTRACT_VERSION,
            "coverage": "from_this_log_forward",
        },
    )
    stage_probe = _load_source_module(
        "stage_load_probe",
        source_paths["stage_load_probe"],
    )
    stage_probe.start()

    core = _load_source_module(
        "room_run_classifier",
        source_paths["room_run_classifier"],
    )
    loaded_contract = getattr(core, "CLASSIFIER_CONTRACT_VERSION", "missing")
    if loaded_contract != _CONTRACT_VERSION:
        raise RuntimeError(
            "Unexpected ORMS classifier contract: "
            f"loaded={loaded_contract}, expected={_CONTRACT_VERSION}"
        )

    shared = _load_source_module(
        "shared_room_classifier",
        source_paths["shared_room_classifier"],
    )
    bridge = _load_source_module(
        "camera_position_bridge",
        source_paths["camera_position_bridge"],
    )
    shared.log_room_map_warning(
        owner="KRM-93 CLASSIFIER",
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
    classifier = shared.start(root)
    classification = classifier.last_classification
    corner_summaries = []
    if classification is not None:
        mappings_by_group = {}
        for mapping in classification.result.mappings:
            mappings_by_group.setdefault(mapping.group_id, []).append(mapping)
        for group in classification.result.groups:
            if len(group.aperture_keys) <= group.room_size:
                continue
            mappings = mappings_by_group.get(group.derived_id, ())
            axes = sorted(
                {
                    tuple(round(value, 4) for value in mapping.room_axis_u)
                    for mapping in mappings
                }
            )
            atlas_sizes = sorted({mapping.atlas_size for mapping in mappings})
            corner_summaries.append(
                f"roomID={group.room_id}:box=x{group.room_size}"
                f"x{group.room_depth_size},axes={axes},atlases={atlas_sizes}"
            )
    shared.log_room_map_warning(
        owner="KRM-93 CLASSIFIER",
        process="RUNTIME SOURCE LOAD",
        state="CORNER_BOXES_AUTHORED",
        details={
            "corner_count": len(corner_summaries),
            "corners": "; ".join(corner_summaries),
        },
    )
    camera_bridge = bridge.start()
    return classifier, camera_bridge


def stop_runtime() -> None:
    """Stop either top-level or package-loaded manual ORMS runtime modules."""

    for module_name in (
        "stage_load_probe",
        "tools.omniverse.stage_load_probe",
        "shared_room_classifier",
        "tools.omniverse.shared_room_classifier",
        "camera_position_bridge",
        "tools.omniverse.camera_position_bridge",
    ):
        _stop_loaded_module(module_name)
