"""Protect the world-space camera bridge and its MDL input contract."""

from pathlib import Path

from pxr import Sdf, Usd, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
STAGE_PATH = (
    REPOSITORY_ROOT
    / "assets"
    / "_external"
    / "usd"
    / "test_grid"
    / "camera_direction_bridge.usda"
)
MDL_PATH = (
    REPOSITORY_ROOT
    / "src"
    / "mdl"
    / "diagnostics"
    / "camera_direction_as_colour.mdl"
)
BRIDGE_PATH = (
    REPOSITORY_ROOT
    / "tools"
    / "omniverse"
    / "runtime"
    / "camera_position_bridge.py"
)


def test_camera_direction_stage_binds_a_camera_position_input():
    stage = Usd.Stage.Open(str(STAGE_PATH))

    assert stage

    mesh = stage.GetPrimAtPath("/World/CameraDirectionGrid/geo/test_grid")
    material, relationship = UsdShade.MaterialBindingAPI(
        mesh
    ).ComputeBoundMaterial()
    shader = UsdShade.Shader(
        stage.GetPrimAtPath("/World/Looks/CameraDirection/Shader")
    )
    camera_position = shader.GetInput("camera_position_world")

    assert relationship
    assert material.GetPath() == "/World/Looks/CameraDirection"
    assert camera_position.GetTypeName() == Sdf.ValueTypeNames.Float3
    assert tuple(camera_position.Get()) == (2.0, 1.0, 0.0)
    assert shader.GetImplementationSource() == "sourceAsset"
    source_asset = shader.GetPrim().GetAttribute("info:mdl:sourceAsset").Get()
    assert source_asset.path.endswith("camera_direction_as_colour.mdl")


def test_camera_direction_module_and_bridge_share_the_runtime_contract():
    mdl_source = MDL_PATH.read_text(encoding="utf-8")
    bridge_source = BRIDGE_PATH.read_text(encoding="utf-8")

    assert "float3 camera_position_world" in mdl_source
    assert "state::transform_point(" in mdl_source
    assert "state::coordinate_internal" in mdl_source
    assert "state::coordinate_world" in mdl_source
    assert "camera_position_world - surface_position_world" in mdl_source

    assert "get_active_viewport" in bridge_source
    assert "def active_camera_world_position(" in bridge_source
    assert "ComputeLocalToWorldTransform" in bridge_source
    assert "ExtractTranslation" in bridge_source
    assert "stage.GetSessionLayer()" in bridge_source
    assert "camera_position_world" in bridge_source
    assert "stage.Traverse()" in bridge_source
    assert "inputs:camera_position_world" in bridge_source
    assert "material_input_paths" in bridge_source
    assert "self._missing_input_paths" in bridge_source
    assert "self._reported_active_paths" in bridge_source
    assert 'state="ACTIVE"' in bridge_source
    assert "not prim.IsInstanceProxy()" in bridge_source
    assert "material_input.GetPrim().IsInstanceProxy()" in bridge_source
    assert 'state="INSTANCE_PROXY_SKIPPED"' in bridge_source
    assert "log_room_map_warning(" in bridge_source
    assert (
        "carb.eventdispatcher.get_eventdispatcher().observe_event("
        in bridge_source
    )
    assert "omni.kit.app.GLOBAL_EVENT_UPDATE" in bridge_source
    assert "get_update_event_stream" not in bridge_source
    assert "carb.log_warn(" not in bridge_source
