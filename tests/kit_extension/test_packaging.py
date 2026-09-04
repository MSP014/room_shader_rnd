"""Protect deterministic standalone ORMS extension packaging."""

import json
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

from tools.package_orms_extension import build_extension

from ._support import REPOSITORY_ROOT


def _touch_debug_sources(repository_root: Path) -> None:
    texture_root = (
        repository_root / "exts" / "msp.orms.runtime" / "data" / "atlases"
    )
    family_names = (
        "room_map_debug_x1",
        "room_map_debug_x2",
        "room_map_debug_x3",
        "room_map_debug_x4",
    )
    for family_name in family_names:
        family_root = texture_root / family_name
        family_root.mkdir(parents=True)
        for tile in range(1001, 1009):
            (family_root / f"{family_name}.{tile}.png").write_bytes(
                f"{family_name}:{tile}".encode()
            )


def _fake_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    extension_root = root / "exts" / "msp.orms.runtime"
    (extension_root / "config").mkdir(parents=True)
    (extension_root / "config" / "extension.toml").write_text(
        '[package]\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (extension_root / "msp" / "orms" / "runtime").mkdir(parents=True)
    (extension_root / "msp" / "orms" / "runtime" / "extension.py").write_text(
        "# extension entry point\n",
        encoding="utf-8",
    )
    (
        extension_root
        / "msp"
        / "orms"
        / "runtime"
        / "reload_room_map_runtime.py"
    ).write_text(
        "# runtime entry point\n",
        encoding="utf-8",
    )
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    for filename in ("room_map.mdl", "room_map_single.mdl"):
        (mdl_root / filename).write_text("mdl 1.7;\n", encoding="utf-8")
    _touch_debug_sources(root)
    return root


def test_builder_packages_canonical_source_and_public_debug_content(tmp_path):
    repository_root = _fake_repository(tmp_path)
    output = tmp_path / "bundle" / "msp.orms.runtime"

    built = build_extension(repository_root, output)

    assert built == output.resolve()
    assert (built / "data" / "mdl" / "room_map.mdl").is_file()
    assert (
        built / "msp" / "orms" / "runtime" / "reload_room_map_runtime.py"
    ).is_file()
    assert not (built / "data" / "runtime").exists()
    assert (
        built
        / "data"
        / "atlases"
        / "room_map_debug_x4"
        / "room_map_debug_x4.1008.png"
    ).is_file()
    manifest = json.loads(
        (built / "data" / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["production_atlases_included"] is False
    assert manifest["source_policy"] == (
        "canonical extension tree with packaged debug atlases"
    )
    assert all("production" not in item["path"] for item in manifest["files"])


def test_builder_refuses_to_overwrite_existing_output(tmp_path):
    repository_root = _fake_repository(tmp_path)
    output = tmp_path / "existing"
    output.mkdir()

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        build_extension(repository_root, output)


def test_packaged_entry_point_imports_without_source_checkout(tmp_path):
    output = tmp_path / "bundle" / "msp.orms.runtime"
    built = build_extension(REPOSITORY_ROOT, output)
    script = """
import importlib
import sys
import types

bundle = sys.argv[1]
sys.path.insert(0, bundle)
omni = types.ModuleType("omni")
omni.__path__ = []
omni_ext = types.ModuleType("omni.ext")
omni_ext.IExt = type("IExt", (), {})
omni.ext = omni_ext
sys.modules["omni"] = omni
sys.modules["omni.ext"] = omni_ext
module = importlib.import_module("msp.orms.runtime.extension")
print(module.__file__)
"""

    result = subprocess.run(  # nosec B603
        (sys.executable, "-I", "-c", script, str(built)),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert str(built) in result.stdout
