"""Protect packaged/debug and external/production atlas boundaries."""

import json
from pathlib import Path

import pytest
from msp.orms.interior_sets.atlas_mode import (
    ATLAS_MODE_DEBUG,
    ATLAS_MODE_PRODUCTION,
)
from msp.orms.interior_sets.contracts import (
    InteriorSetCollection,
    InteriorSetConfig,
    semantic_variant_id,
)
from msp.orms.runtime.interior_sets.resources import (
    resolve_interior_set_resources,
)
from msp.orms.runtime.resources import (
    PRODUCTION_DIRECTORY_SETTING,
    ResourceLayout,
    discover_production_atlas,
    resolve_debug_atlases,
    select_runtime_atlases,
)

from . import _support  # noqa: F401


def _touch_udim_family(asset_path: Path, variant_count: int = 8) -> None:
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    for tile in range(1001, 1001 + variant_count):
        asset_path.with_name(
            asset_path.name.replace("<UDIM>", str(tile))
        ).touch()


def _write_manifest(
    directory: Path,
    namespace: str,
    variant_ids: list[str],
) -> None:
    (directory / "orms_variants.json").write_text(
        json.dumps(
            {
                "version": 1,
                "namespace": namespace,
                "variant_ids": variant_ids,
            }
        ),
        encoding="utf-8",
    )


def test_external_texture_tree_is_not_a_debug_resource_fallback(
    tmp_path,
):
    extension_root = tmp_path / "workspace" / "exts" / "msp.orms.runtime"
    module_file = extension_root / "msp" / "orms" / "runtime" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    debug_asset = (
        tmp_path
        / "workspace"
        / "assets"
        / "_external"
        / "tex"
        / "room_map_debug_x1"
        / "room_map_debug_x1.<UDIM>.png"
    )
    _touch_udim_family(debug_asset)

    resources = ResourceLayout.discover(module_file)

    assert resources.mdl_root == mdl_root
    assert resources.debug_atlas(1) is None
    assert resources.debug_atlas(2) is None


def test_extension_owned_debug_resources_are_discovered(tmp_path):
    extension_root = tmp_path / "workspace" / "exts" / "msp.orms.runtime"
    module_file = extension_root / "msp" / "orms" / "runtime" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    debug_asset = (
        extension_root
        / "data"
        / "atlases"
        / "room_map_debug_x1"
        / "room_map_debug_x1.<UDIM>.png"
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
    variant_ids = [f"room-{index}" for index in range(56)]
    _write_manifest(family_directory, "kitchens.v1", variant_ids)

    atlas = discover_production_atlas(
        room_size=1,
        atlas_directory=family_directory,
    )

    assert atlas.asset_path == asset_path
    assert atlas.variant_count == 56
    assert atlas.source == "production"
    assert atlas.variant_manifest.namespace == "kitchens.v1"
    assert atlas.variant_manifest.variant_ids == tuple(variant_ids)


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
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    for room_size, family_name in (
        (1, "room_map_debug_x1"),
        (2, "room_map_debug_x2"),
    ):
        _touch_udim_family(
            extension_root
            / "data"
            / "atlases"
            / family_name
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


def test_manifest_count_must_match_the_udim_family(tmp_path):
    family_directory = tmp_path / "licensed-pack" / "x1"
    asset_path = family_directory / "room_map.<UDIM>.png"
    _touch_udim_family(asset_path, variant_count=2)
    _write_manifest(family_directory, "rooms.v1", ["room-0"])

    with pytest.raises(ValueError, match="does not match its UDIM family"):
        discover_production_atlas(
            room_size=1,
            atlas_directory=family_directory,
        )


def test_per_set_fallback_and_cross_family_coherence_are_independent(
    tmp_path,
):
    extension_root = tmp_path / "workspace" / "exts" / "msp.orms.runtime"
    module_file = extension_root / "msp" / "orms" / "runtime" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    for room_size, family_name in (
        (1, "room_map_debug_x1"),
        (2, "room_map_debug_x2"),
        (3, "room_map_debug_x3"),
        (4, "room_map_debug_x4"),
    ):
        _touch_udim_family(
            extension_root
            / "data"
            / "atlases"
            / family_name
            / f"{family_name}.<UDIM>.png"
        )
    production_x1 = tmp_path / "licensed-pack" / "x1"
    _touch_udim_family(production_x1 / "rooms.<UDIM>.png")
    _write_manifest(
        production_x1,
        "kitchens.v1",
        [f"kitchen-{index}" for index in range(8)],
    )
    default = InteriorSetCollection.default_only().default
    kitchens = InteriorSetConfig(
        set_id="11111111-1111-1111-1111-111111111111",
        atlas_directories=(str(production_x1), "missing", "", ""),
    )
    resources = ResourceLayout.discover(module_file)

    snapshots = resolve_interior_set_resources(
        resources,
        InteriorSetCollection((default, kitchens)),
        ATLAS_MODE_PRODUCTION,
    )

    default_snapshot, kitchen_snapshot = snapshots
    assert default_snapshot.coherence.coherent
    assert kitchen_snapshot.family(1).atlas.source == "production"
    assert kitchen_snapshot.family(2).atlas.source == "packaged"
    assert kitchen_snapshot.family(2).validation_error is not None
    assert not kitchen_snapshot.coherence.coherent

    debug_snapshots = resolve_interior_set_resources(
        resources,
        InteriorSetCollection((default, kitchens)),
        ATLAS_MODE_DEBUG,
    )
    debug_kitchens = debug_snapshots[1]
    assert all(
        family.atlas is not None and family.atlas.source == "packaged"
        for family in debug_kitchens.families
    )
    assert all(
        family.fallback_reason == "global debug mode"
        for family in debug_kitchens.families
    )
    assert all(
        family.validation_error is None for family in debug_kitchens.families
    )


def test_global_debug_override_replaces_one_family_and_invalid_path_falls_back(
    tmp_path,
):
    extension_root = tmp_path / "workspace" / "exts" / "msp.orms.runtime"
    module_file = extension_root / "msp" / "orms" / "runtime" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    mdl_root = extension_root / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    (mdl_root / "room_map_single.mdl").touch()
    packaged = (
        extension_root
        / "data"
        / "atlases"
        / "room_map_debug_x1"
        / "room_map_debug_x1.<UDIM>.png"
    )
    _touch_udim_family(packaged)
    custom_directory = tmp_path / "custom-debug-x1"
    _touch_udim_family(custom_directory / "diagnostic.<UDIM>.png", 4)
    resources = ResourceLayout.discover(module_file)

    custom = resolve_debug_atlases(
        resources,
        (str(custom_directory), "", "", ""),
    )[0]
    invalid = resolve_debug_atlases(
        resources,
        (str(tmp_path / "missing"), "", "", ""),
    )[0]

    assert custom.uses_override
    assert custom.atlas.source == "debug override"
    assert custom.atlas.variant_count == 4
    assert invalid.atlas.asset_path == packaged
    assert invalid.validation_error is not None

    default = InteriorSetCollection.default_only()
    debug_family = resolve_interior_set_resources(
        resources,
        default,
        ATLAS_MODE_DEBUG,
        (str(custom_directory), "", "", ""),
    )[0].family(1)
    production_fallback = resolve_interior_set_resources(
        resources,
        default,
        ATLAS_MODE_PRODUCTION,
        (str(custom_directory), "", "", ""),
    )[0].family(1)

    assert debug_family.atlas.source == "debug override"
    assert production_fallback.atlas.source == "debug override"


def test_coherent_x4_and_x1_resolve_the_same_corner_variant(tmp_path):
    variant_ids = [f"kitchen-{index}" for index in range(4)]
    families = []
    for room_size in (1, 4):
        directory = tmp_path / f"x{room_size}"
        _touch_udim_family(
            directory / "rooms.<UDIM>.png",
            variant_count=4,
        )
        _write_manifest(directory, "kitchens.v1", variant_ids)
        families.append(
            discover_production_atlas(
                room_size=room_size,
                atlas_directory=directory,
            )
        )

    x1_manifest = families[0].variant_manifest
    x4_manifest = families[1].variant_manifest

    assert x1_manifest is not None
    assert x4_manifest is not None
    assert semantic_variant_id(x1_manifest, 17, 3) == (
        semantic_variant_id(x4_manifest, 17, 3)
    )
