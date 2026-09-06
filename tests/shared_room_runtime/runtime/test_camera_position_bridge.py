# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the world-space camera bridge and its MDL input contract."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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
    / "exts"
    / "msp.orms.runtime"
    / "data"
    / "mdl"
    / "diagnostics"
    / "camera_direction_as_colour.mdl"
)
BRIDGE_PATH = (
    REPOSITORY_ROOT
    / "exts"
    / "msp.orms.runtime"
    / "msp"
    / "orms"
    / "scene"
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
    assert "self._runtime_layer or stage.GetSessionLayer()" in bridge_source
    assert "runtime_layer=runtime_layer" in bridge_source
    assert "def set_runtime_layer(" in bridge_source
    assert "def _runtime_layer_is_attached(" in bridge_source
    assert 'state="RUNTIME_LAYER_DETACHED"' in bridge_source
    assert "camera_position_world" in bridge_source
    assert "stage.Traverse()" in bridge_source
    assert "inputs:camera_position_world" in bridge_source
    assert "material_input_paths" in bridge_source
    assert "self._missing_input_paths" in bridge_source
    assert "self._reported_active_paths" in bridge_source
    assert "self._trace_log_warning" in bridge_source
    assert "trace_log_warning=trace_log_warning" in bridge_source
    assert "def set_material_input_paths(" in bridge_source
    assert "self._last_position = None" in bridge_source
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
    assert "def pause(self) -> None:" in bridge_source
    assert "def resume(self) -> None:" in bridge_source
    assert "def owned_subscription_count(self) -> int:" in bridge_source
    assert "def registered_observer_count(self) -> int:" in bridge_source
    assert "def update_callback_count(self) -> int:" in bridge_source
    assert "def successful_update_count(self) -> int:" in bridge_source
    assert "subscription.enabled = False" in bridge_source
    assert "subscription.enabled = True" in bridge_source
    assert 'process="CAMERA UPDATE RESUME"' in bridge_source
    assert "self.resume()" in bridge_source
    assert "subscription, self._subscription" in bridge_source
    assert "get_update_event_stream" not in bridge_source
    assert "carb.log_warn(" not in bridge_source


class _ObserverGuard:
    def __init__(self) -> None:
        self.enabled = True
        self.reset_count = 0

    def reset(self) -> None:
        self.enabled = False
        self.reset_count += 1


class _ResetOnlyObserverGuard:
    __slots__ = ("reset_count",)

    def __init__(self) -> None:
        self.reset_count = 0

    def reset(self) -> None:
        self.reset_count += 1


class _EventDispatcher:
    def __init__(self, guard_type=_ObserverGuard) -> None:
        self.guard_type = guard_type
        self.observe_calls = []

    def observe_event(self, **kwargs):
        guard = self.guard_type()
        self.observe_calls.append((kwargs, guard))
        return guard


def _load_bridge_with_kit_stubs(monkeypatch, guard_type=_ObserverGuard):
    dispatcher = _EventDispatcher(guard_type)
    carb = ModuleType("carb")
    carb.__path__ = []
    eventdispatcher = ModuleType("carb.eventdispatcher")
    eventdispatcher.get_eventdispatcher = lambda: dispatcher
    carb.eventdispatcher = eventdispatcher

    omni = ModuleType("omni")
    omni.__path__ = []
    kit = ModuleType("omni.kit")
    kit.__path__ = []
    app = ModuleType("omni.kit.app")
    app.GLOBAL_EVENT_UPDATE = "kit_update"
    viewport = ModuleType("omni.kit.viewport")
    viewport.__path__ = []
    viewport_utility = ModuleType("omni.kit.viewport.utility")
    viewport_utility.get_active_viewport = lambda: None
    usd = ModuleType("omni.usd")
    usd.get_context = lambda: None
    omni.kit = kit
    omni.usd = usd
    kit.app = app
    kit.viewport = viewport
    viewport.utility = viewport_utility

    package_name = "_orms_camera_bridge_test"
    package = ModuleType(package_name)
    package.__path__ = []
    status_log = ModuleType(f"{package_name}.status_log")
    status_log.log_room_map_warning = lambda **_record: None
    modules = {
        "carb": carb,
        "carb.eventdispatcher": eventdispatcher,
        "omni": omni,
        "omni.kit": kit,
        "omni.kit.app": app,
        "omni.kit.viewport": viewport,
        "omni.kit.viewport.utility": viewport_utility,
        "omni.usd": usd,
        package_name: package,
        f"{package_name}.status_log": status_log,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = f"{package_name}.camera_position_bridge"
    spec = importlib.util.spec_from_file_location(module_name, BRIDGE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module, dispatcher


def test_pause_disables_and_resume_reuses_the_same_observer(monkeypatch):
    module, dispatcher = _load_bridge_with_kit_stubs(monkeypatch)
    bridge = module.CameraPositionBridge(("/Looks/Shader.inputs:camera",))
    guard = dispatcher.observe_calls[0][1]
    bridge._last_position = (1.0, 2.0, 3.0)

    bridge.pause()

    assert not guard.enabled
    assert guard.reset_count == 0
    assert bridge.owned_subscription_count == 0
    assert bridge.registered_observer_count == 1

    bridge.resume()

    assert guard.enabled
    assert guard.reset_count == 0
    assert len(dispatcher.observe_calls) == 1
    assert bridge.owned_subscription_count == 1
    assert bridge.registered_observer_count == 1
    assert bridge._last_position is None


def test_repeated_resume_does_not_duplicate_the_observer(monkeypatch):
    module, dispatcher = _load_bridge_with_kit_stubs(monkeypatch)
    bridge = module.CameraPositionBridge(("/Looks/Shader.inputs:camera",))

    bridge.resume()
    bridge.pause()
    bridge.resume()
    bridge.resume()

    assert len(dispatcher.observe_calls) == 1
    assert bridge.registered_observer_count == 1
    assert bridge.owned_subscription_count == 1


def test_stop_permanently_resets_the_retained_observer(monkeypatch):
    module, dispatcher = _load_bridge_with_kit_stubs(monkeypatch)
    bridge = module.CameraPositionBridge(("/Looks/Shader.inputs:camera",))
    guard = dispatcher.observe_calls[0][1]
    bridge.pause()

    bridge.stop()

    assert guard.reset_count == 1
    assert bridge.registered_observer_count == 0
    assert bridge.owned_subscription_count == 0


def test_legacy_guard_falls_back_to_reset_and_fresh_registration(monkeypatch):
    module, dispatcher = _load_bridge_with_kit_stubs(
        monkeypatch,
        _ResetOnlyObserverGuard,
    )
    bridge = module.CameraPositionBridge(("/Looks/Shader.inputs:camera",))
    first_guard = dispatcher.observe_calls[0][1]

    bridge.pause()
    bridge.resume()

    assert first_guard.reset_count == 1
    assert len(dispatcher.observe_calls) == 2
    assert bridge.registered_observer_count == 1


def test_first_resumed_frame_forces_write_and_emits_confirmation(monkeypatch):
    module, _dispatcher = _load_bridge_with_kit_stubs(monkeypatch)
    stage = Usd.Stage.CreateInMemory()
    stage.DefinePrim("/Looks/Shader").CreateAttribute(
        "inputs:camera",
        Sdf.ValueTypeNames.Float3,
    )

    class _Context:
        @staticmethod
        def get_stage():
            return stage

    positions = [(1.0, 2.0, 3.0), (8.0, 9.0, 10.0)]
    trace_records = []
    module.omni.usd.get_context = lambda: _Context()
    module.active_camera_world_position = lambda _stage: positions[0]
    bridge = module.CameraPositionBridge(
        ("/Looks/Shader.inputs:camera",),
        runtime_layer=stage.GetSessionLayer(),
        trace_log_warning=lambda **record: trace_records.append(record),
    )
    bridge._on_update(None)
    bridge.pause()
    module.active_camera_world_position = lambda _stage: positions[1]

    bridge.resume()
    bridge._on_update(None)

    value = stage.GetAttributeAtPath("/Looks/Shader.inputs:camera").Get()
    assert tuple(value) == positions[1]
    assert bridge.update_callback_count == 2
    assert bridge.successful_update_count == 2
    resume_records = [
        record
        for record in trace_records
        if record["process"] == "CAMERA UPDATE RESUME"
    ]
    assert len(resume_records) == 1
    assert resume_records[0]["state"] == "ACTIVE"
    assert resume_records[0]["details"]["updated_input_count"] == 1
