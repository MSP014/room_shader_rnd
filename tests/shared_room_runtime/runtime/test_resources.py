"""Protect the installation-neutral ORMS runtime resource contract."""

from pathlib import Path

import pytest

from tools.omniverse.runtime.resources import (
    RuntimeAtlasFamily,
    RuntimeResources,
    is_room_map_source_asset,
)


def _touch_udim_family(asset_path: Path) -> None:
    asset_path.parent.mkdir(parents=True)
    for tile in range(1001, 1009):
        asset_path.with_name(
            asset_path.name.replace("<UDIM>", str(tile))
        ).touch()


def test_repository_adapter_exposes_only_complete_debug_families(tmp_path):
    mdl_root = tmp_path / "src" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    complete = (
        tmp_path
        / "assets"
        / "_external"
        / "tex"
        / "room_map_debug"
        / "room_map_debug.<UDIM>.png"
    )
    _touch_udim_family(complete)
    incomplete = (
        tmp_path
        / "assets"
        / "_external"
        / "tex"
        / "room_map_debug_x2"
        / "room_map_debug_x2.<UDIM>.png"
    )
    incomplete.parent.mkdir(parents=True)
    incomplete.with_name("room_map_debug_x2.1001.png").touch()

    resources = RuntimeResources.from_repository(tmp_path)

    assert resources.available_room_sizes == frozenset({1})
    assert resources.atlas_family(1).asset_path == complete.as_posix()
    assert resources.mdl_source_asset.endswith("src/mdl/room_map.mdl")
    with pytest.raises(KeyError, match="x2"):
        resources.atlas_family(2)


def test_resource_contract_rejects_duplicate_room_sizes():
    family = RuntimeAtlasFamily(1, "debug.<UDIM>.png", 8)

    with pytest.raises(ValueError, match="must be unique"):
        RuntimeResources("room_map.mdl", (family, family))


@pytest.mark.parametrize(
    "source_asset",
    (
        "room_map.mdl",
        "msp/orms/room_map.mdl",
        r"C:\\Kit\\exts\\msp.orms.runtime\\data\\mdl\\room_map_single.mdl",
    ),
)
def test_source_asset_recognition_is_installation_neutral(source_asset):
    assert is_room_map_source_asset(source_asset)
