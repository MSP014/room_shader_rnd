"""Protect the installation-neutral ORMS runtime resource contract."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from msp.orms.scene.resources import (
    RuntimeAtlasFamily,
    RuntimeResources,
    coerce_runtime_resources,
    is_room_map_source_asset,
)


def test_structural_coercion_survives_reloaded_module_identity():
    previous_module_record = SimpleNamespace(
        mdl_source_asset="packaged/room_map.mdl",
        atlas_families=(
            SimpleNamespace(
                room_size=1,
                asset_path="debug/x1.<UDIM>.png",
                variant_count=8,
                source="packaged",
            ),
        ),
    )

    resources = coerce_runtime_resources(previous_module_record)

    assert isinstance(resources, RuntimeResources)
    assert resources.mdl_source_asset == "packaged/room_map.mdl"
    assert resources.atlas_family(1).source == "packaged"


def _touch_udim_family(asset_path: Path) -> None:
    asset_path.parent.mkdir(parents=True)
    for tile in range(1001, 1009):
        asset_path.with_name(
            asset_path.name.replace("<UDIM>", str(tile))
        ).touch()


def test_repository_adapter_exposes_only_complete_debug_families(tmp_path):
    mdl_root = tmp_path / "exts" / "msp.orms.runtime" / "data" / "mdl"
    mdl_root.mkdir(parents=True)
    (mdl_root / "room_map.mdl").touch()
    complete = (
        tmp_path
        / "exts"
        / "msp.orms.runtime"
        / "data"
        / "atlases"
        / "room_map_debug_x1"
        / "room_map_debug_x1.<UDIM>.png"
    )
    _touch_udim_family(complete)
    incomplete = (
        tmp_path
        / "exts"
        / "msp.orms.runtime"
        / "data"
        / "atlases"
        / "room_map_debug_x2"
        / "room_map_debug_x2.<UDIM>.png"
    )
    incomplete.parent.mkdir(parents=True)
    incomplete.with_name("room_map_debug_x2.1001.png").touch()

    resources = RuntimeResources.from_repository(tmp_path)

    assert resources.available_room_sizes == frozenset({1})
    assert resources.atlas_family(1).asset_path == complete.as_posix()
    assert resources.mdl_source_asset.endswith(
        "exts/msp.orms.runtime/data/mdl/room_map.mdl"
    )
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
