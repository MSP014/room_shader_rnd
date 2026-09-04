"""Protect the compact installed-extension Interior Set fixture."""

from msp.orms.interior_sets.contracts import (
    InteriorSetCollection,
    InteriorSetConfig,
)
from msp.orms.interior_sets.runtime_resources import (
    InteriorSetRuntimeResources,
    InteriorSetRuntimeSnapshot,
)
from msp.orms.scene.resources import RuntimeResources
from msp.orms.shared_room.authoring import RuntimeLayerOwner
from msp.orms.shared_room.contracts import RuntimeClassifierSettings
from msp.orms.shared_room.pipeline import classify_stage
from pxr import Sdf, Usd

from ._support import REPOSITORY_ROOT

FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "shared_room_runtime"
    / "test_room_map_interior_sets_omniverse.usda"
)


def test_compact_fixture_exercises_default_priority_and_multiple_masks():
    stage = Usd.Stage.Open(str(FIXTURE))
    assert stage is not None
    source_before = stage.GetRootLayer().ExportToString()
    default = InteriorSetCollection.default_only().default.renamed(
        "Living Rooms"
    )
    kitchens = InteriorSetConfig(
        set_id="11111111-1111-1111-1111-111111111111",
        name="Kitchens",
        selectors=("*/Kitchens_Windows",),
    )
    shops = InteriorSetConfig(
        set_id="22222222-2222-2222-2222-222222222222",
        name="Shops",
        selectors=("*/Shop*_Windows",),
    )
    overlapping = InteriorSetConfig(
        set_id="33333333-3333-3333-3333-333333333333",
        name="Shop Override",
        selectors=("*/ShopFront_Windows",),
    )
    libraries = InteriorSetConfig(
        set_id="44444444-4444-4444-4444-444444444444",
        name="Libraries",
        selectors=("*/Library_Windows", "*/Archive_Glass"),
    )
    collection = InteriorSetCollection(
        (default, kitchens, shops, overlapping, libraries)
    )
    resources = RuntimeResources.from_repository(REPOSITORY_ROOT)
    runtime_resources = InteriorSetRuntimeSnapshot(
        tuple(
            InteriorSetRuntimeResources(item.set_id, resources)
            for item in collection.sets
        )
    )
    owner = RuntimeLayerOwner(stage)

    classification = classify_stage(
        stage,
        owner.attach(),
        RuntimeClassifierSettings(),
        resources,
        interior_sets=collection,
        interior_set_resources=runtime_resources,
    )
    by_path = {
        item.prim_path: item for item in classification.selector_resolutions
    }

    assert by_path["/World/BuildingA/LivingRoom_Windows"].used_default
    assert by_path["/World/BuildingA/Kitchens_Windows"].set_id == (
        kitchens.set_id
    )
    assert by_path["/World/BuildingB/Kitchens_Windows"].set_id == (
        kitchens.set_id
    )
    assert by_path["/World/BuildingA/ShopFront_Windows"].set_id == shops.set_id
    assert by_path["/World/BuildingA/ShopFront_Windows"].has_conflict
    assert by_path["/World/BuildingA/Library_Windows"].set_id == (
        libraries.set_id
    )
    assert by_path["/World/BuildingA/Archive_Glass"].set_id == libraries.set_id
    assert stage.GetAttributeAtPath(
        Sdf.Path(
            "/World/BuildingA/Kitchens_Windows.primvars:ormsInteriorSetId"
        )
    )
    assert stage.GetRootLayer().ExportToString() == source_before

    owner.detach()
    assert stage.GetRootLayer().ExportToString() == source_before
