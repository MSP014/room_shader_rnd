"""Synchronise an MDL camera-position input with the active Kit viewport.

Run this module inside USD Composer's Script Editor. The value is authored in
the USD session layer, so camera updates do not modify the opened stage file.
"""

from __future__ import annotations

import carb
import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from pxr import Gf, Sdf, Usd, UsdGeom

DEFAULT_CAMERA_POSITION_INPUT = (
    "/World/Looks/CameraDirection/Shader.inputs:camera_position_world"
)


class CameraPositionBridge:
    """Write the active viewport camera world position into an MDL input."""

    def __init__(
        self, material_input_path: str = DEFAULT_CAMERA_POSITION_INPUT
    ):
        self._material_input_path = Sdf.Path(material_input_path)
        self._last_position: tuple[float, float, float] | None = None
        self._subscription = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(
                self._on_update,
                name="room_map_camera_position_bridge",
            )
        )

    def _on_update(self, _event) -> None:
        stage = omni.usd.get_context().get_stage()
        viewport = get_active_viewport()
        camera_path = (
            getattr(viewport, "camera_path", None) if viewport else None
        )
        if not stage or not camera_path:
            return

        camera_prim = stage.GetPrimAtPath(camera_path)
        if not camera_prim:
            return

        world_transform = UsdGeom.Xformable(
            camera_prim
        ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        world_position = world_transform.ExtractTranslation()
        position = (
            float(world_position[0]),
            float(world_position[1]),
            float(world_position[2]),
        )
        if position == self._last_position:
            return

        material_input = stage.GetAttributeAtPath(self._material_input_path)
        if not material_input:
            carb.log_warn(
                f"Room Map camera input was not found: {self._material_input_path}"
            )
            return

        with Usd.EditContext(stage, stage.GetSessionLayer()):
            material_input.Set(Gf.Vec3f(*position))
        self._last_position = position

    def stop(self) -> None:
        self._subscription = None


_bridge: CameraPositionBridge | None = None


def start(
    material_input_path: str = DEFAULT_CAMERA_POSITION_INPUT,
) -> CameraPositionBridge:
    """Start the singleton bridge and return it for interactive inspection."""
    global _bridge
    stop()
    _bridge = CameraPositionBridge(material_input_path)
    return _bridge


def stop() -> None:
    """Stop the singleton bridge, if it is currently running."""
    global _bridge
    if _bridge:
        _bridge.stop()
        _bridge = None
