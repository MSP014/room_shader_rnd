"""Protect deterministic standalone ORMS extension packaging."""

import json
from pathlib import Path

import pytest

from tools.package_orms_extension import build_extension


def _touch_debug_sources(repository_root: Path) -> None:
    texture_root = repository_root / "assets" / "_external" / "tex"
    family_names = (
        "room_map_debug",
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
        extension_root / "msp" / "orms" / "runtime" / "runtime_imports.py"
    ).write_text(
        "# version-safe import boundary\n",
        encoding="utf-8",
    )
    runtime_root = root / "tools" / "omniverse"
    runtime_root.mkdir(parents=True)
    (runtime_root / "reload_room_map_runtime.py").write_text(
        "# runtime entry point\n",
        encoding="utf-8",
    )
    mdl_root = root / "src" / "mdl"
    mdl_root.mkdir(parents=True)
    for filename in ("room_map.mdl", "room_map_single.mdl"):
        (mdl_root / filename).write_text("mdl 1.7;\n", encoding="utf-8")
    _touch_debug_sources(root)
    return root


def test_builder_materialises_runtime_mdl_and_public_debug_content(tmp_path):
    repository_root = _fake_repository(tmp_path)
    output = tmp_path / "bundle" / "msp.orms.runtime"

    built = build_extension(repository_root, output)

    assert built == output.resolve()
    assert (built / "data" / "mdl" / "room_map.mdl").is_file()
    assert (
        built
        / "data"
        / "runtime"
        / "tools"
        / "omniverse"
        / "reload_room_map_runtime.py"
    ).is_file()
    assert (
        built / "msp" / "orms" / "runtime" / "runtime_imports.py"
    ).is_file()
    assert (
        built
        / "data"
        / "atlases"
        / "debug"
        / "x4"
        / "room_map_debug_x4.1008.png"
    ).is_file()
    manifest = json.loads(
        (built / "data" / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["production_atlases_included"] is False
    assert all("production" not in item["path"] for item in manifest["files"])


def test_builder_refuses_to_overwrite_existing_output(tmp_path):
    repository_root = _fake_repository(tmp_path)
    output = tmp_path / "existing"
    output.mkdir()

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        build_extension(repository_root, output)
