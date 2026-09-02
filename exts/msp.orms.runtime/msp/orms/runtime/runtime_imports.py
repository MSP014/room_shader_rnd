"""Expose one installed ORMS runtime version through Python namespaces."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

_OWNED_MODULE_PREFIXES = (
    "tools.omniverse.runtime.",
    "tools.omniverse.room_run.",
    "tools.omniverse.shared_room.",
)
_OWNED_MODULE_NAMES = frozenset(
    {
        "camera_position_bridge",
        "runtime.camera_position_bridge",
        "shared_room.controller",
        "shared_room_classifier",
        "stage_load_probe",
        "tools.omniverse.camera_position_bridge",
        "tools.omniverse.reload_room_map_runtime",
        "tools.omniverse.room_run_classifier",
        "tools.omniverse.shared_room_classifier",
        "tools.omniverse.stage_load_probe",
    }
)
_PACKAGE_DIRECTORIES = (
    ("tools", "tools"),
    ("tools.omniverse", "tools/omniverse"),
    ("tools.omniverse.runtime", "tools/omniverse/runtime"),
    ("tools.omniverse.room_run", "tools/omniverse/room_run"),
    ("tools.omniverse.shared_room", "tools/omniverse/shared_room"),
)


@dataclass(frozen=True)
class RuntimeImportActivation:
    """Report stale version state removed from the current Python process."""

    removed_modules: tuple[str, ...]
    removed_runtime_roots: tuple[str, ...]


def _path_key(path: str | Path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def _runtime_root_from_source(path: str | Path) -> Path | None:
    current = Path(path).resolve()
    if current.is_file():
        current = current.parent
    while current != current.parent:
        if (
            current.name.casefold() == "omniverse"
            and current.parent.name.casefold() == "tools"
        ):
            return current.parent.parent
        current = current.parent
    return None


def _module_runtime_root(module: ModuleType) -> Path | None:
    source_path = getattr(module, "__file__", None)
    if not source_path:
        return None
    return _runtime_root_from_source(source_path)


def _is_owned_module_name(name: str) -> bool:
    return name in _OWNED_MODULE_NAMES or name.startswith(
        _OWNED_MODULE_PREFIXES
    )


def _detach_parent_attribute(name: str, module: ModuleType) -> None:
    parent_name, separator, child_name = name.rpartition(".")
    if not separator:
        return
    parent = sys.modules.get(parent_name)
    if parent is not None and getattr(parent, child_name, None) is module:
        delattr(parent, child_name)


def _is_installed_orms_runtime(path: str | Path) -> bool:
    normalised = str(Path(path)).replace("\\", "/").casefold()
    return "msp.orms.runtime-" in normalised and "/data/runtime" in normalised


def _is_stale_path(
    path: str | Path,
    *,
    current_root_key: str,
    stale_root_keys: frozenset[str],
) -> bool:
    path_key = _path_key(path)
    if path_key == current_root_key:
        return False
    if path_key in stale_root_keys or _is_installed_orms_runtime(path):
        return True
    runtime_root = _runtime_root_from_source(path)
    if runtime_root is None:
        return False
    runtime_root_key = _path_key(runtime_root)
    if runtime_root_key == current_root_key:
        return False
    return runtime_root_key in stale_root_keys or _is_installed_orms_runtime(
        runtime_root
    )


def _activate_package_paths(
    runtime_root: Path,
    stale_root_keys: frozenset[str],
) -> None:
    current_root_key = _path_key(runtime_root)
    for package_name, relative_directory in _PACKAGE_DIRECTORIES:
        package = sys.modules.get(package_name)
        if package is None:
            continue
        current_directory = runtime_root / relative_directory
        existing_paths = tuple(getattr(package, "__path__", ()))
        retained_paths = [
            path
            for path in existing_paths
            if _path_key(path) != _path_key(current_directory)
            and not _is_stale_path(
                path,
                current_root_key=current_root_key,
                stale_root_keys=stale_root_keys,
            )
        ]
        active_paths = [str(current_directory), *retained_paths]
        package.__path__ = active_paths
        specification = getattr(package, "__spec__", None)
        if specification is not None:
            specification.submodule_search_locations = active_paths


def _activate_sys_path(
    runtime_root: Path,
    stale_root_keys: frozenset[str],
) -> None:
    current_root_key = _path_key(runtime_root)
    retained_paths = [
        path
        for path in sys.path
        if _path_key(path) != current_root_key
        and not _is_stale_path(
            path,
            current_root_key=current_root_key,
            stale_root_keys=stale_root_keys,
        )
    ]
    sys.path[:] = [str(runtime_root), *retained_paths]


def activate_runtime_imports(
    runtime_root: str | Path,
) -> RuntimeImportActivation:
    """Replace cached ORMS modules from earlier installed versions."""

    current_root = Path(runtime_root).resolve()
    if not (current_root / "tools" / "omniverse").is_dir():
        raise FileNotFoundError(f"Invalid ORMS runtime root: {current_root}")
    current_root_key = _path_key(current_root)
    stale_modules = []
    stale_roots = set()
    for name, module in tuple(sys.modules.items()):
        if module is None or not _is_owned_module_name(name):
            continue
        loaded_root = _module_runtime_root(module)
        if loaded_root is None or _path_key(loaded_root) == current_root_key:
            continue
        stale_modules.append((name, module))
        stale_roots.add(loaded_root)

    # Kit shuts the previous extension down before starting the update. This
    # boundary replaces stale import identities; lifecycle teardown remains
    # owned by the previous service and must not be repeated here.
    for name, module in stale_modules:
        if sys.modules.get(name) is module:
            sys.modules.pop(name, None)
            _detach_parent_attribute(name, module)

    stale_root_keys = frozenset(_path_key(root) for root in stale_roots)
    _activate_sys_path(current_root, stale_root_keys)
    _activate_package_paths(current_root, stale_root_keys)
    return RuntimeImportActivation(
        removed_modules=tuple(sorted(name for name, _module in stale_modules)),
        removed_runtime_roots=tuple(sorted(str(root) for root in stale_roots)),
    )
