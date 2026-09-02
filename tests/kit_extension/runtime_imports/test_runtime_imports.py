"""Protect in-process upgrades between installed ORMS runtime versions."""

from __future__ import annotations

import importlib
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

from msp.orms.runtime.runtime_imports import activate_runtime_imports


def _isolate_orms_modules(monkeypatch) -> None:
    isolated_modules = {
        name: module
        for name, module in sys.modules.items()
        if name != "tools" and not name.startswith("tools.")
    }
    monkeypatch.setattr(sys, "modules", isolated_modules)


def _namespace_package(name: str, source_path: Path) -> ModuleType:
    package = ModuleType(name)
    package.__package__ = name
    package.__path__ = [str(source_path)]
    package.__spec__ = ModuleSpec(name, loader=None, is_package=True)
    package.__spec__.submodule_search_locations = package.__path__
    return package


def _install_fake_packages(
    monkeypatch,
    runtime_root: Path,
) -> ModuleType:
    packages = (
        ("tools", runtime_root / "tools"),
        ("tools.omniverse", runtime_root / "tools" / "omniverse"),
        (
            "tools.omniverse.shared_room",
            runtime_root / "tools" / "omniverse" / "shared_room",
        ),
    )
    created = {}
    for name, source_path in packages:
        package = _namespace_package(name, source_path)
        monkeypatch.setitem(sys.modules, name, package)
        created[name] = package
        parent_name, separator, child_name = name.rpartition(".")
        if separator:
            setattr(created[parent_name], child_name, package)
    return created["tools.omniverse.shared_room"]


def _runtime_version_root(tmp_path: Path, version: str) -> Path:
    return tmp_path / f"msp.orms.runtime-{version}" / "data" / "runtime"


def test_upgrade_replaces_cached_module_and_namespace_paths(
    tmp_path,
    monkeypatch,
):
    old_root = _runtime_version_root(tmp_path, "0.1.1")
    current_root = _runtime_version_root(tmp_path, "0.1.4")
    relative_source = Path("tools/omniverse/shared_room/upgrade_probe.py")
    old_source = old_root / relative_source
    current_source = current_root / relative_source
    old_source.parent.mkdir(parents=True)
    current_source.parent.mkdir(parents=True)
    old_source.write_text("VERSION = 'old'\n", encoding="utf-8")
    current_source.write_text("VERSION = 'current'\n", encoding="utf-8")

    _isolate_orms_modules(monkeypatch)
    shared_room_package = _install_fake_packages(monkeypatch, old_root)
    module_name = "tools.omniverse.shared_room.upgrade_probe"
    old_module = ModuleType(module_name)
    old_module.__file__ = str(old_source)
    old_module.VERSION = "old"
    monkeypatch.setitem(sys.modules, module_name, old_module)
    monkeypatch.setattr(
        shared_room_package,
        "upgrade_probe",
        old_module,
        raising=False,
    )
    monkeypatch.setattr(sys, "path", [str(old_root), *sys.path])

    activation = activate_runtime_imports(current_root)
    importlib.invalidate_caches()
    imported = importlib.import_module(module_name)

    assert activation.removed_modules == (module_name,)
    assert activation.removed_runtime_roots == (str(old_root.resolve()),)
    assert imported is not old_module
    assert imported.VERSION == "current"
    assert Path(imported.__file__) == current_source
    assert Path(sys.path[0]) == current_root
    assert str(old_root) not in sys.path
    assert Path(shared_room_package.__path__[0]) == (
        current_root / "tools" / "omniverse" / "shared_room"
    )
    assert str(old_source.parent) not in shared_room_package.__path__


def test_current_runtime_module_is_not_reloaded(tmp_path, monkeypatch):
    current_root = _runtime_version_root(tmp_path, "0.1.4")
    current_source = (
        current_root
        / "tools"
        / "omniverse"
        / "shared_room"
        / "upgrade_probe.py"
    )
    current_source.parent.mkdir(parents=True)
    current_source.write_text("VERSION = 'current'\n", encoding="utf-8")
    _isolate_orms_modules(monkeypatch)
    shared_room_package = _install_fake_packages(monkeypatch, current_root)
    module_name = "tools.omniverse.shared_room.upgrade_probe"
    current_module = ModuleType(module_name)
    current_module.__file__ = str(current_source)
    monkeypatch.setitem(sys.modules, module_name, current_module)
    monkeypatch.setattr(
        shared_room_package,
        "upgrade_probe",
        current_module,
        raising=False,
    )

    activation = activate_runtime_imports(current_root)

    assert activation.removed_modules == ()
    assert activation.removed_runtime_roots == ()
    assert sys.modules[module_name] is current_module
    assert shared_room_package.upgrade_probe is current_module
