# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Synchronise an MDL camera-position input with the active Kit viewport.

Run this module inside USD Composer's Script Editor. The value is authored in
the USD session layer, so camera updates do not modify the opened stage file.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import carb.eventdispatcher
import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from pxr import Gf, Sdf, Usd, UsdGeom

from .status_log import log_room_map_warning

DEFAULT_CAMERA_POSITION_INPUT = (
    "/World/Looks/CameraDirection/Shader.inputs:camera_position_world"
)


def active_camera_world_position(
    stage: Usd.Stage | None = None,
) -> tuple[float, float, float] | None:
    """Return the active viewport camera position in world space."""

    stage = stage or omni.usd.get_context().get_stage()
    viewport = get_active_viewport()
    camera_path = getattr(viewport, "camera_path", None) if viewport else None
    if not stage or not camera_path:
        return None
    camera_prim = stage.GetPrimAtPath(camera_path)
    if not camera_prim:
        return None
    world_transform = UsdGeom.Xformable(
        camera_prim
    ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    world_position = world_transform.ExtractTranslation()
    return (
        float(world_position[0]),
        float(world_position[1]),
        float(world_position[2]),
    )


class CameraPositionBridge:
    """Write the active viewport camera world position into MDL inputs."""

    def __init__(
        self,
        material_input_paths: str | Sequence[str] | None = None,
        *,
        trace_log_warning: Callable[..., None] | None = (log_room_map_warning),
    ):
        self._auto_discover = material_input_paths is None
        if isinstance(material_input_paths, str):
            material_input_paths = (material_input_paths,)
        self._material_input_paths = tuple(
            Sdf.Path(path) for path in (material_input_paths or ())
        )
        self._stage_identifier: str | None = None
        self._missing_input_paths: set[Sdf.Path] = set()
        self._reported_active_paths: set[Sdf.Path] = set()
        self._warned_no_inputs = False
        self._last_position: tuple[float, float, float] | None = None
        self._trace_log_warning = trace_log_warning
        self._subscription = None
        self.resume()

    def resume(self) -> None:
        """Resume viewport-camera updates without changing the last value."""

        if self._subscription is not None:
            return
        self._subscription = (
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                on_event=self._on_update,
                observer_name="orms.camera_position_bridge.update",
            )
        )

    def set_material_input_paths(
        self,
        material_input_paths: str | Sequence[str],
    ) -> None:
        """Replace explicit targets after a structural runtime rebuild.

        Resetting the cached position guarantees that the next Kit update
        writes the current camera into newly authored material families.
        """

        if isinstance(material_input_paths, str):
            material_input_paths = (material_input_paths,)
        paths = tuple(
            dict.fromkeys(Sdf.Path(path) for path in material_input_paths)
        )
        if not self._auto_discover and paths == self._material_input_paths:
            return
        self._auto_discover = False
        self._material_input_paths = paths
        self._stage_identifier = None
        self._missing_input_paths.clear()
        self._reported_active_paths.intersection_update(paths)
        self._warned_no_inputs = False
        self._last_position = None

    def _discover_material_input_paths(
        self, stage: Usd.Stage
    ) -> tuple[Sdf.Path, ...]:
        """Find writable composed MDL camera-position inputs in the stage."""
        return tuple(
            prim.GetAttribute("inputs:camera_position_world").GetPath()
            for prim in stage.Traverse()
            if prim.GetAttribute("inputs:camera_position_world")
            and not prim.IsInstanceProxy()
        )

    def _refresh_material_input_paths(self, stage: Usd.Stage) -> None:
        if not self._auto_discover:
            return

        stage_identifier = stage.GetRootLayer().identifier
        if stage_identifier == self._stage_identifier:
            return

        self._material_input_paths = self._discover_material_input_paths(stage)
        self._stage_identifier = stage_identifier
        self._missing_input_paths.clear()
        self._reported_active_paths.clear()
        self._warned_no_inputs = False
        self._last_position = None

    def _on_update(self, _event) -> None:
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        self._refresh_material_input_paths(stage)
        if not self._material_input_paths:
            if not self._warned_no_inputs:
                log_room_map_warning(
                    owner="CAMERA POSITION BRIDGE",
                    process="MATERIAL INPUT DISCOVERY",
                    state="MISSING",
                    details={
                        "message": (
                            "Camera inputs were not found in the active stage."
                        )
                    },
                )
                self._warned_no_inputs = True
            return

        position = active_camera_world_position(stage)
        if position is None:
            return
        if position == self._last_position and not self._missing_input_paths:
            return

        with Usd.EditContext(stage, stage.GetSessionLayer()):
            for material_input_path in self._material_input_paths:
                material_input = stage.GetAttributeAtPath(material_input_path)
                if not material_input:
                    if material_input_path not in self._missing_input_paths:
                        log_room_map_warning(
                            owner="CAMERA POSITION BRIDGE",
                            process="MATERIAL INPUT UPDATE",
                            state="MISSING",
                            details={"input_path": material_input_path},
                        )
                    self._missing_input_paths.add(material_input_path)
                    continue

                if material_input.GetPrim().IsInstanceProxy():
                    if material_input_path not in self._missing_input_paths:
                        log_room_map_warning(
                            owner="CAMERA POSITION BRIDGE",
                            process="MATERIAL INPUT UPDATE",
                            state="INSTANCE_PROXY_SKIPPED",
                            details={"input_path": material_input_path},
                        )
                    self._missing_input_paths.add(material_input_path)
                    continue

                material_input.Set(Gf.Vec3f(*position))
                self._missing_input_paths.discard(material_input_path)
                if material_input_path not in self._reported_active_paths:
                    if self._trace_log_warning is not None:
                        self._trace_log_warning(
                            owner="CAMERA POSITION BRIDGE",
                            process="CAMERA POSITION ATTRIBUTE UPDATE",
                            state="ACTIVE",
                            details={
                                "attribute_path": material_input_path,
                                "world_position": position,
                            },
                        )
                    self._reported_active_paths.add(material_input_path)
        self._last_position = position

    def pause(self) -> None:
        """Freeze the last authored camera value and release live updates."""

        reset = getattr(self._subscription, "reset", None)
        if callable(reset):
            reset()
        self._subscription = None

    def stop(self) -> None:
        """Release the per-frame update subscription owned by this bridge."""

        self.pause()


_bridge: CameraPositionBridge | None = None


def start(
    material_input_paths: str | Sequence[str] | None = None,
    *,
    trace_log_warning: Callable[..., None] | None = log_room_map_warning,
) -> CameraPositionBridge:
    """Start the singleton bridge and return it for interactive inspection.

    With no argument, all ``inputs:camera_position_world`` attributes in the
    active stage are discovered. A path or a sequence of paths remains
    available for a deliberately restricted update target.
    """
    global _bridge
    stop()
    _bridge = CameraPositionBridge(
        material_input_paths,
        trace_log_warning=trace_log_warning,
    )
    return _bridge


def stop() -> None:
    """Stop the singleton bridge, if it is currently running."""
    global _bridge
    if _bridge:
        _bridge.stop()
        _bridge = None
