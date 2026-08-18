from pathlib import Path

from pxr import Usd, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = (
    REPOSITORY_ROOT
    / "assets"
    / "_external"
    / "usd"
    / "hello_world_material.usda"
)


def test_hello_world_stage_binds_the_mdl_material():
    stage = Usd.Stage.Open(str(STAGE_PATH))

    assert stage

    cube = stage.GetPrimAtPath("/World/Cube")
    material, binding_relationship = UsdShade.MaterialBindingAPI(
        cube
    ).ComputeBoundMaterial()

    assert binding_relationship
    assert material.GetPath() == "/World/Looks/HelloWorld"

    shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Looks/HelloWorld/Shader")
    )
    assert shader.GetImplementationSource() == "sourceAsset"
    assert (
        shader.GetPrim()
        .GetAttribute("info:mdl:sourceAsset:subIdentifier")
        .Get()
        == "hello_world"
    )
