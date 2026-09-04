"""Protect instance-policy authoring on retained composed fixtures."""

from collections import Counter
from pathlib import Path

import pytest
from msp.orms.shared_room.controller import (
    INSTANCE_POLICY_SESSION_DEINSTANCE,
    RuntimeClassifierSettings,
)
from pxr import Usd, UsdGeom, UsdShade

from ._fixture_support import (
    HOUDINI_INSTANCE_FIXTURE,
    HOUDINI_INSTANCE_SOURCE,
    INSTANCE_FIXTURE,
    _classify,
    _family_material_sizes,
)


@pytest.mark.parametrize(
    ("fixture_path", "instance_names", "aperture_count", "group_sizes"),
    (
        (
            INSTANCE_FIXTURE,
            {"BuildingA", "BuildingB"},
            94,
            Counter({1: 4, 2: 8, 3: 8, 4: 8}),
        ),
        (
            HOUDINI_INSTANCE_FIXTURE,
            {"HoudiniBuildingA", "HoudiniBuildingB"},
            280,
            Counter({1: 190, 2: 8, 3: 8, 4: 6}),
        ),
    ),
)
def test_real_instance_fixtures_support_both_runtime_policies(
    fixture_path,
    instance_names,
    aperture_count,
    group_sizes,
):
    preserve_stage, preserve_owner, preserve = _classify(fixture_path)

    instances = tuple(
        child
        for child in preserve_stage.GetPrimAtPath("/World").GetChildren()
        if child.GetName() in instance_names
    )
    assert len(instances) == 2
    assert all(prim.IsInstance() for prim in instances)
    assert not preserve.extraction.apertures
    assert Counter(
        diagnostic.state for diagnostic in preserve.extraction.diagnostics
    ) == Counter({"INSTANCE_PRESERVED_X1_FALLBACK": 2})
    for diagnostic in preserve.extraction.diagnostics:
        details = dict(diagnostic.details)
        assert details["source_x1_proxy_count"] > 0
        assert (
            details["room_uv_varying_proxy_count"]
            == details["source_x1_proxy_count"]
        )
        assert (
            details["camera_primvar_inherited_proxy_count"]
            == details["source_x1_proxy_count"]
        )
    assert _family_material_sizes(preserve_stage) == set()
    assert (
        tuple(
            str(prim.GetAttribute("inputs:camera_position_world").GetPath())
            for prim in preserve_stage.Traverse()
            if prim.GetAttribute("inputs:camera_position_world")
        )
        == ()
    )
    for instance in instances:
        meshes = tuple(
            prim
            for prim in Usd.PrimRange(
                instance,
                Usd.TraverseInstanceProxies(),
            )
            if prim.IsA(UsdGeom.Mesh)
        )
        assert meshes
        eligible_meshes = tuple(
            mesh
            for mesh in meshes
            if all(
                UsdGeom.PrimvarsAPI(mesh).GetPrimvar(name)
                for name in (
                    "roomID",
                    "roomP",
                    "tangentu",
                    "tangentv",
                    "roomUV",
                )
            )
            and str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            ).endswith("/Looks/RoomMapSource")
        )
        preserved_meshes = tuple(
            mesh for mesh in meshes if mesh not in eligible_meshes
        )
        assert eligible_meshes
        assert {
            str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            )
            for mesh in eligible_meshes
        } == {f"{instance.GetPath()}/Looks/RoomMapSource"}
        assert all(
            str(
                UsdShade.MaterialBindingAPI(mesh)
                .ComputeBoundMaterial()[0]
                .GetPath()
            )
            != f"{instance.GetPath()}/Looks/RoomMapSource"
            for mesh in preserved_meshes
        )
        assert not instance.GetRelationship(
            "material:binding:collection:ormsRoomMapWindows"
        )
        if fixture_path == HOUDINI_INSTANCE_FIXTURE:
            assert preserved_meshes
            assert any(
                str(
                    UsdShade.MaterialBindingAPI(mesh)
                    .ComputeBoundMaterial()[0]
                    .GetPath()
                ).endswith("/mtl/test_mat")
                for mesh in preserved_meshes
            )

    preserve_owner.detach()

    assert not any(
        prim.GetRelationship("material:binding:collection:ormsRoomMapWindows")
        for prim in instances
    )

    deinstance_stage, deinstance_owner, deinstance = _classify(
        fixture_path,
        RuntimeClassifierSettings(
            instance_policy=INSTANCE_POLICY_SESSION_DEINSTANCE
        ),
    )
    deinstanced = tuple(
        child
        for child in deinstance_stage.GetPrimAtPath("/World").GetChildren()
        if child.GetName() in instance_names
    )
    assert not any(prim.IsInstance() for prim in deinstanced)
    assert len(deinstance.extraction.apertures) == aperture_count
    assert (
        Counter(group.room_size for group in deinstance.result.groups)
        == group_sizes
    )

    deinstance_owner.detach()

    assert all(prim.IsInstance() for prim in deinstanced)


def test_houdini_instance_fixture_uses_the_exported_component_layers():
    stage = Usd.Stage.Open(
        str(HOUDINI_INSTANCE_FIXTURE),
        load=Usd.Stage.LoadAll,
    )

    used_layer_names = {
        Path(layer.realPath).name
        for layer in stage.GetUsedLayers()
        if layer.realPath
    }
    assert stage.GetRootLayer().customLayerData["orms:fixtureOrigin"] == (
        "Referenced and instanceable Houdini-exported geometry"
    )
    assert {
        HOUDINI_INSTANCE_SOURCE.name,
        "test_bld.usd",
        "payload.usdc",
        "geo.usdc",
        "mtl.usdc",
    }.issubset(used_layer_names)
