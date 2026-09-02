"""Protect packaged/debug and external/production atlas boundaries."""

from pathlib import Path

import pytest
from msp.orms.runtime.resources import (
    PRODUCTION_DIRECTORY_SETTING,
    ResourceLayout,
    discover_production_atlas,
    select_runtime_atlases,
)

from . import _support  # noqa: F401


def _touch_udim_family(asset_path: Path, variant_count: int = 8) -> None:
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    for tile in range(1001, 1001 + variant_count):
        asset_path.with_name(
            asset_path.name.replace("<UDIM>", str(tile))
        ).touch()


def test_checkout_layout_keeps_mdl_canonical_and_finds_debug_fallback(
    tmp_path,
):
    extension_root = tmp_path / "workspace" / "exts" / "msp.orms.runtime"
    module_file = extension_root / "msp" / "orms" / "runtime" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    (tmp_path / "workspace" / "tools" / "omniverse").mkdir(parents=True)
    mdl_root = tmp_path / "workspace" / "src" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    debug_asset = (
        tmp_path
        / "workspace"
        / "assets"
        / "_external"
        / "tex"
        / "room_map_debug"
        / "room_map_debug.<UDIM>.png"
    )
    _touch_udim_family(debug_asset)

    resources = ResourceLayout.discover(module_file)

    assert resources.runtime_root == tmp_path / "workspace"
    assert resources.mdl_root == mdl_root
    assert resources.debug_atlas(1).asset_path == debug_asset
    assert resources.debug_atlas(1).source == "checkout"
    assert resources.debug_atlas(2) is None


def test_packaged_resources_win_over_checkout_fallback(tmp_path):
    extension_root = tmp_path / "workspace" / "exts" / "msp.orms.runtime"
    module_file = extension_root / "msp" / "orms" / "runtime" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    (extension_root / "data" / "runtime" / "tools" / "omniverse").mkdir(
        parents=True
    )
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    debug_asset = (
        extension_root
        / "data"
        / "atlases"
        / "debug"
        / "x1"
        / "room_map_debug.<UDIM>.png"
    )
    _touch_udim_family(debug_asset)

    resources = ResourceLayout.discover(module_file)

    assert resources.mdl_root == mdl_root
    assert resources.debug_atlas(1).asset_path == debug_asset
    assert resources.debug_atlas(1).source == "packaged"


def test_production_atlas_is_discovered_from_family_directory(tmp_path):
    family_directory = tmp_path / "licensed-pack" / "x1"
    asset_path = family_directory / "room_map.<UDIM>.png"
    _touch_udim_family(asset_path, variant_count=56)

    atlas = discover_production_atlas(
        room_size=1,
        atlas_directory=family_directory,
    )

    assert atlas.asset_path == asset_path
    assert atlas.variant_count == 56
    assert atlas.source == "production"


def test_production_atlas_rejects_missing_udim_tiles(tmp_path):
    family_directory = tmp_path / "licensed-pack" / "x1"
    asset_path = family_directory / "room_map.<UDIM>.png"
    _touch_udim_family(asset_path, variant_count=3)
    asset_path.with_name("room_map.1002.png").unlink()

    with pytest.raises(FileNotFoundError, match="continuous from UDIM 1001"):
        discover_production_atlas(
            room_size=1,
            atlas_directory=family_directory,
        )


def test_production_atlas_rejects_ambiguous_family_directory(tmp_path):
    family_directory = tmp_path / "licensed-pack" / "x1"
    _touch_udim_family(
        family_directory / "day.<UDIM>.png",
        variant_count=2,
    )
    _touch_udim_family(
        family_directory / "night.<UDIM>.png",
        variant_count=2,
    )

    with pytest.raises(ValueError, match="exactly one UDIM sequence"):
        discover_production_atlas(
            room_size=1,
            atlas_directory=family_directory,
        )


def test_configured_production_family_overrides_only_matching_debug_size(
    tmp_path,
):
    extension_root = tmp_path / "workspace" / "exts" / "msp.orms.runtime"
    module_file = extension_root / "msp" / "orms" / "runtime" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    (extension_root / "data" / "runtime" / "tools" / "omniverse").mkdir(
        parents=True
    )
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    for room_size, family_name in (
        (1, "room_map_debug"),
        (2, "room_map_debug_x2"),
    ):
        _touch_udim_family(
            extension_root
            / "data"
            / "atlases"
            / "debug"
            / f"x{room_size}"
            / f"{family_name}.<UDIM>.png"
        )
    production_root = tmp_path / "licensed-pack"
    production_x1 = production_root / "x1" / "rooms.<UDIM>.png"
    _touch_udim_family(production_x1, variant_count=56)
    resources = ResourceLayout.discover(module_file)

    selected = select_runtime_atlases(
        resources,
        {
            PRODUCTION_DIRECTORY_SETTING.format(room_size=1): str(
                production_x1.parent
            ),
        },
    )

    assert [(atlas.room_size, atlas.source) for atlas in selected] == [
        (1, "production"),
        (2, "packaged"),
    ]
    assert selected[0].variant_count == 56
