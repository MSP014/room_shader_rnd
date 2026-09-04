"""Protect the retained visual, source-material, and camera fixture contract."""

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdLux, UsdShade

from ._fixture_support import (
    HDRI_ASSET_PATH,
    HDRI_PATH,
    HOUDINI_FIXTURE,
    HOUDINI_INSTANCE_FIXTURE,
    HOUDINI_INSTANCE_SOURCE,
    INSTANCE_FIXTURE,
    OMNIVERSE_FIXTURE,
)


@pytest.mark.parametrize(
    "fixture_path",
    (
        OMNIVERSE_FIXTURE,
        HOUDINI_FIXTURE,
        HOUDINI_INSTANCE_FIXTURE,
        INSTANCE_FIXTURE,
    ),
)
def test_visual_fixtures_use_the_room_map_hdri_environment(fixture_path):
    stage = Usd.Stage.Open(str(fixture_path), load=Usd.Stage.LoadAll)
    dome = UsdLux.DomeLight(stage.GetPrimAtPath("/World/RoomMapEnvironment"))

    assert dome
    assert dome.GetTextureFileAttr().Get().path == HDRI_ASSET_PATH
    assert dome.GetTextureFormatAttr().Get() == "latlong"
    assert dome.GetExposureAttr().Get() == 0.0
    assert dome.GetIntensityAttr().Get() == 1000.0
    dome_prim = dome.GetPrim()
    assert dome_prim.GetAttribute("xformOp:rotateX").Get() == -90.0
    assert dome_prim.GetAttribute("xformOpOrder").Get() == ["xformOp:rotateX"]
    assert HDRI_PATH.is_file()


@pytest.mark.parametrize(
    ("fixture_path", "shader_path"),
    (
        (
            OMNIVERSE_FIXTURE,
            "/World/Building/Looks/RoomMapSource/Shader",
        ),
        (HOUDINI_FIXTURE, "/World/Looks/RoomMapSource/Shader"),
        (
            HOUDINI_INSTANCE_SOURCE,
            "/HoudiniBuilding/Looks/RoomMapSource/Shader",
        ),
    ),
)
def test_source_x1_materials_enable_all_debug_variants(
    fixture_path,
    shader_path,
):
    stage = Usd.Stage.Open(str(fixture_path), load=Usd.Stage.LoadAll)
    shader = UsdShade.Shader(stage.GetPrimAtPath(shader_path))

    assert shader
    assert shader.GetInput("room_variant_count").Get() == 8
    assert shader.GetInput("variation_seed").Get() == 0
    assert (
        shader.GetInput("room_atlas")
        .Get()
        .path.endswith("room_map_debug_x1/room_map_debug_x1.<UDIM>.png")
    )


@pytest.mark.parametrize(
    "fixture_path",
    (HOUDINI_INSTANCE_FIXTURE, INSTANCE_FIXTURE),
)
def test_instance_fixtures_predeclare_camera_primvar_before_runtime(
    fixture_path,
):
    stage = Usd.Stage.Open(str(fixture_path), load=Usd.Stage.LoadAll)
    primvar = UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World")).GetPrimvar(
        "ormsCameraPositionWorld"
    )

    assert primvar
    assert primvar.GetTypeName() == Sdf.ValueTypeNames.Float3
    assert primvar.GetInterpolation() == UsdGeom.Tokens.constant
    assert tuple(primvar.Get()) == (8.0, 3.0, 5.0)

    instance_roots = tuple(
        child
        for child in stage.GetPrimAtPath("/World").GetChildren()
        if child.IsInstance()
    )
    assert len(instance_roots) == 2
    inherited_primvars = tuple(
        UsdGeom.PrimvarsAPI(proxy).FindPrimvarWithInheritance(
            "ormsCameraPositionWorld"
        )
        for instance in instance_roots
        for proxy in Usd.PrimRange(instance, Usd.TraverseInstanceProxies())
        if proxy.IsA(UsdGeom.Mesh)
        and UsdGeom.PrimvarsAPI(proxy).GetPrimvar("roomUV")
    )
    assert inherited_primvars
    assert all(inherited_primvars)
    assert {tuple(inherited.Get()) for inherited in inherited_primvars} == {
        (8.0, 3.0, 5.0)
    }
