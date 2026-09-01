"""Load exact ORMS source modules while preserving lifecycle cleanup order."""

from __future__ import annotations

import sys
import tokenize
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

_RUNTIME_SOURCE_MODULES = {
    "status_log": (
        "tools.omniverse.runtime.status_log",
        "runtime/status_log.py",
    ),
    "runtime_resource_metrics": (
        "tools.omniverse.runtime.resource_metrics",
        "runtime/resource_metrics.py",
    ),
    "stage_load_state": (
        "tools.omniverse.runtime.stage_load_state",
        "runtime/stage_load_state.py",
    ),
    "stage_load_probe": (
        "tools.omniverse.runtime.stage_load_probe",
        "runtime/stage_load_probe.py",
    ),
    "room_run_contracts": (
        "tools.omniverse.room_run.contracts",
        "room_run/contracts.py",
    ),
    "room_run_topology": (
        "tools.omniverse.room_run.topology",
        "room_run/topology.py",
    ),
    "room_run_mapping": (
        "tools.omniverse.room_run.mapping",
        "room_run/mapping.py",
    ),
    "room_run_classifier": (
        "tools.omniverse.room_run.classifier",
        "room_run/classifier.py",
    ),
    "shared_room_contracts": (
        "tools.omniverse.shared_room.contracts",
        "shared_room/contracts.py",
    ),
    "shared_room_stage": (
        "tools.omniverse.shared_room.stage",
        "shared_room/stage.py",
    ),
    "shared_room_authoring": (
        "tools.omniverse.shared_room.authoring",
        "shared_room/authoring.py",
    ),
    "shared_room_pipeline": (
        "tools.omniverse.shared_room.pipeline",
        "shared_room/pipeline.py",
    ),
    "shared_room_settings": (
        "tools.omniverse.shared_room.settings",
        "shared_room/settings.py",
    ),
    "shared_room_changes": (
        "tools.omniverse.shared_room.changes",
        "shared_room/changes.py",
    ),
    "shared_room_material_diagnostics": (
        "tools.omniverse.shared_room.material_diagnostics",
        "shared_room/material_diagnostics.py",
    ),
    "runtime_renderer_settings": (
        "tools.omniverse.runtime.renderer_settings",
        "runtime/renderer_settings.py",
    ),
    "shared_room_preferences": (
        "tools.omniverse.shared_room.preferences",
        "shared_room/preferences.py",
    ),
    "shared_room_classifier": (
        "tools.omniverse.shared_room.controller",
        "shared_room/controller.py",
    ),
    "camera_position_bridge": (
        "tools.omniverse.runtime.camera_position_bridge",
        "runtime/camera_position_bridge.py",
    ),
}

# Old flat names remain cleanup targets because callbacks can outlive a source
# layout upgrade inside a long-running Kit process.
_LIFECYCLE_MODULE_NAMES = (
    "stage_load_probe",
    "tools.omniverse.stage_load_probe",
    "runtime.stage_load_probe",
    "tools.omniverse.runtime.stage_load_probe",
    "shared_room_classifier",
    "tools.omniverse.shared_room_classifier",
    "shared_room.controller",
    "tools.omniverse.shared_room.controller",
    "camera_position_bridge",
    "tools.omniverse.camera_position_bridge",
    "runtime.camera_position_bridge",
    "tools.omniverse.runtime.camera_position_bridge",
)


def stop_loaded_module(name: str) -> None:
    """Stop one cached module when it exposes an owned runtime lifecycle."""

    module = sys.modules.get(name)
    stop = getattr(module, "stop", None)
    if callable(stop):
        stop()


def load_source_module(name: str, source_path: Path) -> ModuleType:
    """Execute one exact source file under its fully qualified module name."""

    with tokenize.open(str(source_path)) as source_file:
        source = source_file.read()
    package_name, _, child_name = name.rpartition(".")
    parent = sys.modules.get(package_name) if package_name else None
    missing = object()
    previous = sys.modules.get(name, missing)
    previous_child = (
        getattr(parent, child_name, missing) if parent is not None else missing
    )
    module = ModuleType(name)
    module.__file__ = str(source_path)
    module.__package__ = package_name
    module.__spec__ = ModuleSpec(name, loader=None, origin=str(source_path))
    sys.modules[name] = module
    try:
        exec(  # nosec B102 -- executes a fixed, repository-owned module path.
            compile(source, str(source_path), "exec"),
            module.__dict__,
        )
    except Exception:
        if previous is missing:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        if parent is not None:
            if previous_child is missing:
                parent.__dict__.pop(child_name, None)
            else:
                setattr(parent, child_name, previous_child)
        raise
    if parent is not None:
        setattr(parent, child_name, module)
    return module


def _ensure_package(name: str, source_directory: Path) -> None:
    """Register a source package without importing cached child modules."""

    existing = sys.modules.get(name)
    source_text = str(source_directory)
    if existing is not None:
        package_paths = getattr(existing, "__path__", None)
        if package_paths is not None and source_text not in package_paths:
            package_paths.append(source_text)
        return

    parent_name, _, child_name = name.rpartition(".")
    package = ModuleType(name)
    package.__package__ = name
    package.__path__ = [source_text]
    package.__spec__ = ModuleSpec(name, loader=None, is_package=True)
    package.__spec__.submodule_search_locations = [source_text]
    sys.modules[name] = package
    parent = sys.modules.get(parent_name) if parent_name else None
    if parent is not None:
        setattr(parent, child_name, package)


class RuntimeSourceLoader:
    """Resolve and load the exact runtime dependency graph from one checkout."""

    def __init__(self, repository_root: str | Path):
        self.repository_root = Path(repository_root).resolve()
        self.module_root = self.repository_root / "tools" / "omniverse"
        self.source_paths = {
            name: self.module_root / relative_path
            for name, (_, relative_path) in _RUNTIME_SOURCE_MODULES.items()
        }
        self.qualified_names = {
            name: qualified_name
            for name, (qualified_name, _) in _RUNTIME_SOURCE_MODULES.items()
        }

    def prepare(self) -> None:
        """Validate sources, expose sibling imports, and stop live callbacks."""

        missing = tuple(
            str(path)
            for path in self.source_paths.values()
            if not path.is_file()
        )
        if missing:
            raise FileNotFoundError(f"Missing ORMS runtime source: {missing}")

        stop_runtime_modules()
        for package_name, source_directory in (
            ("tools", self.repository_root / "tools"),
            ("tools.omniverse", self.module_root),
            ("tools.omniverse.runtime", self.module_root / "runtime"),
            ("tools.omniverse.room_run", self.module_root / "room_run"),
            ("tools.omniverse.shared_room", self.module_root / "shared_room"),
        ):
            _ensure_package(package_name, source_directory)

    def load(self, name: str) -> ModuleType:
        """Load one declared dependency from its exact repository source."""

        try:
            source_path = self.source_paths[name]
            qualified_name = self.qualified_names[name]
        except KeyError as error:
            raise KeyError(f"Unknown ORMS runtime module: {name}") from error
        return load_source_module(qualified_name, source_path)


def stop_runtime_modules() -> None:
    """Stop every supported import route that may own runtime callbacks."""

    stopped_modules = set()
    for module_name in _LIFECYCLE_MODULE_NAMES:
        module = sys.modules.get(module_name)
        if module is None or id(module) in stopped_modules:
            continue
        stop_loaded_module(module_name)
        stopped_modules.add(id(module))
