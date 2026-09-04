"""Protect the extension as the only canonical ORMS product source tree."""

from pathlib import Path

from ._support import EXTENSION_ROOT, REPOSITORY_ROOT


def _python_sources(root: Path):
    return root.rglob("*.py")


def test_product_source_is_owned_by_the_extension_tree():
    package_root = EXTENSION_ROOT / "msp" / "orms"

    for package_name in (
        "classification",
        "interior_sets",
        "runtime",
        "scene",
        "shared_room",
    ):
        assert (package_root / package_name / "__init__.py").is_file()

    for mdl_name in ("room_map.mdl", "room_map_single.mdl"):
        assert (EXTENSION_ROOT / "data" / "mdl" / mdl_name).is_file()

    assert not (REPOSITORY_ROOT / "tools" / "omniverse").exists()
    assert not (REPOSITORY_ROOT / "src" / "mdl").exists()
    assert not (package_root / "runtime" / "runtime_imports.py").exists()


def test_product_modules_do_not_import_the_legacy_tools_namespace():
    package_root = EXTENSION_ROOT / "msp" / "orms"

    for path in _python_sources(package_root):
        source = path.read_text(encoding="utf-8")
        assert "from tools.omniverse" not in source, path
        assert "import tools.omniverse" not in source, path
