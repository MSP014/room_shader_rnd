# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Exercise the ORMS camera bridge through real Kit update events."""

import asyncio
import traceback

import omni.kit.app
import omni.usd
from msp.orms.scene import camera_position_bridge as bridge_module
from pxr import Gf, Sdf, Usd, UsdGeom

_CAMERA_PRIMVAR_PATH = "/World.primvars:ormsCameraPositionWorld"


async def _run() -> None:
    app = omni.kit.app.get_app()
    worker = None
    try:
        context = omni.usd.get_context()
        await context.new_stage_async()
        stage = context.get_stage()
        if stage is None:
            raise RuntimeError("Kit did not create the camera probe stage")
        UsdGeom.Xform.Define(stage, "/World")
        with Usd.EditContext(stage, stage.GetSessionLayer()):
            primvar = UsdGeom.PrimvarsAPI(
                stage.GetPrimAtPath("/World")
            ).CreatePrimvar(
                "ormsCameraPositionWorld",
                Sdf.ValueTypeNames.Float3,
                UsdGeom.Tokens.constant,
            )
            primvar.Set(Gf.Vec3f(0.0))

        camera_position = [1.0, 2.0, 3.0]
        bridge_module.active_camera_world_position = lambda _stage: tuple(
            camera_position
        )
        worker = bridge_module.CameraPositionBridge(
            (_CAMERA_PRIMVAR_PATH,),
            trace_log_warning=None,
        )

        await app.next_update_async()
        await app.next_update_async()
        first = tuple(stage.GetAttributeAtPath(_CAMERA_PRIMVAR_PATH).Get())
        if first != (1.0, 2.0, 3.0):
            raise AssertionError(f"Initial camera update failed: {first}")

        camera_position[:] = (8.0, 9.0, 10.0)
        await app.next_update_async()
        await app.next_update_async()
        moved = tuple(stage.GetAttributeAtPath(_CAMERA_PRIMVAR_PATH).Get())
        if moved != (8.0, 9.0, 10.0):
            raise AssertionError(f"Moved camera update failed: {moved}")

        print(
            "ORMS_CAMERA_RUNTIME_PROBE state=COMPLETE"
            f" module={bridge_module.__file__} first={first} moved={moved}"
        )
    except Exception:
        print("ORMS_CAMERA_RUNTIME_PROBE state=FAILED")
        traceback.print_exc()
    finally:
        if worker is not None:
            worker.stop()
        app.post_quit()


asyncio.ensure_future(_run())
