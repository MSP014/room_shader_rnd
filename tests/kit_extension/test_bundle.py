"""Protect the minimal installable Kit extension manifest and documentation."""

import tomllib

from ._support import EXTENSION_ROOT


def test_extension_manifest_declares_required_runtime_dependencies():
    with (EXTENSION_ROOT / "config" / "extension.toml").open("rb") as stream:
        manifest = tomllib.load(stream)

    package = manifest["package"]
    assert package["title"] == "Omniverse Room Map Shader"
    assert package["version"] == "0.1.21"
    assert package["repository"] == (
        "https://github.com/MSP014/room_shader_rnd"
    )
    for field in ("readme", "changelog", "icon", "preview_image"):
        assert (EXTENSION_ROOT / package[field]).is_file()
    assert set(manifest["dependencies"]) == {
        "omni.usd",
        "omni.mdl.neuraylib",
        "omni.kit.material.library",
        "omni.kit.menu.utils",
        "omni.kit.window.file_importer",
        "omni.kit.window.file_exporter",
        "omni.kit.widget.settings",
    }
    assert manifest["python"]["module"] == [
        {"name": "msp.orms.runtime.extension"}
    ]


def test_extension_documents_both_texture_distribution_zones():
    atlas_document = (
        EXTENSION_ROOT / "data" / "atlases" / "README.md"
    ).read_text(encoding="utf-8")

    assert "data/atlases/debug/" in atlas_document
    assert "/atlases/xN/directory" in atlas_document
    assert "variantCount" not in atlas_document
    assert "do not live in this extension" in atlas_document


def test_extension_manager_readme_is_an_artist_workflow():
    overview = (EXTENSION_ROOT / "README.md").read_text(encoding="utf-8")

    for required in (
        "Window > ORMS",
        "Use source rule",
        "Restore Original Asset",
        "Debug (force packaged)",
        "Apply Interior Sets",
        "Save Profile...",
        "Troubleshooting",
    ):
        assert required in overview
    for developer_detail in (
        "package_orms_extension.py",
        "publish_orms_local_registry.py",
        "service.py",
        "module ownership",
    ):
        assert developer_detail not in overview
