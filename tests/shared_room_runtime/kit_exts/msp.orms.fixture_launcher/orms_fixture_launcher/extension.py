# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Open the requested Room Map validation stage after Kit startup."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import carb
import omni.ext
import omni.kit.app
import omni.usd
from omni.kit.viewport.ready.viewport_ready import ViewportReady

_SETTINGS_ROOT = "/exts/msp.orms.fixture_launcher"

# The test extension is loaded from its own root, while diagnostics remain
# owned by the canonical ORMS extension package.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_EXTENSION_ROOT = _REPOSITORY_ROOT / "exts" / "msp.orms.runtime"
_extension_root_text = str(_EXTENSION_ROOT)
if _extension_root_text not in sys.path:
    sys.path.insert(0, _extension_root_text)


def _load_warning_logger():
    """Resolve the canonical formatter from the ORMS extension package."""

    from msp.orms.scene.status_log import log_room_map_warning

    return log_room_map_warning


log_room_map_warning = _load_warning_logger()


def _log(state: str, **details: object) -> None:
    """Route one visible launcher transition through the ORMS formatter."""

    log_room_map_warning(
        owner="VALIDATION FIXTURE LAUNCHER",
        process="KIT STAGE OPEN",
        state=state,
        details=details,
    )


class _ViewportReadySignal:
    """Receive the first-rendered-frame callback without adding another UI."""

    viewport_handle = None
    usd_context_name = ""
    viewport_name = "Viewport"

    def __init__(self, future: asyncio.Future[None]) -> None:
        self._future = future

    def build_ui(self) -> None:
        """Satisfy the ViewportReady interface without creating test UI."""

        pass

    def on_complete(self) -> None:
        """Resolve the launcher's future after the first rendered frame."""

        if not self._future.done():
            self._future.set_result(None)


class RoomMapFixtureLauncherExtension(omni.ext.IExt):
    """Schedule one stage-open request without starting the ORMS runtime."""

    def __init__(self) -> None:
        super().__init__()
        self._open_task: asyncio.Task | None = None
        self._viewport_ready: ViewportReady | None = None

    def on_startup(self, _ext_id: str) -> None:
        """Validate the requested fixture and schedule one asynchronous open."""

        settings = carb.settings.get_settings()
        value = settings.get(f"{_SETTINGS_ROOT}/stagePath")
        stage_path = Path(str(value or "")).resolve()
        if not stage_path.is_file():
            _log(
                "STAGE_PATH_INVALID",
                previous_state="EXTENSION_STARTUP",
                new_state="BLOCKED",
                trigger="EXTENSION_STARTUP",
                stage_path=stage_path,
                outcome="VALIDATION_FAILED",
            )
            return

        _log(
            "STAGE_OPEN_SCHEDULED",
            previous_state="EXTENSION_STARTUP",
            new_state="STAGE_OPEN_SCHEDULED",
            trigger="VALID_STAGE_PATH",
            stage_path=stage_path,
            classifier_auto_start=False,
            bootstrap_stage=True,
            outcome="SCHEDULED",
        )
        self._open_task = asyncio.ensure_future(self._open_stage(stage_path))

    async def _open_stage(self, stage_path: Path) -> None:
        try:
            app = omni.kit.app.get_app()
            loop = asyncio.get_running_loop()
            viewport_ready_future: asyncio.Future[None] = loop.create_future()
            self._viewport_ready = ViewportReady(
                _ViewportReadySignal(viewport_ready_future)
            )

            _log(
                "WAITING_FOR_KIT_READY",
                previous_state="STAGE_OPEN_SCHEDULED",
                new_state="WAITING_FOR_KIT_READY",
                trigger="OPEN_TASK_STARTED",
                app_ready=app.is_app_ready(),
                viewport_first_frame_ready=viewport_ready_future.done(),
                outcome="WAITING",
            )
            while not app.is_app_ready():
                await app.next_update_async()
            _log(
                "APP_READY",
                previous_state="WAITING_FOR_KIT_READY",
                new_state="APP_READY",
                trigger="KIT_APP_READY",
                app_ready=True,
                outcome="OBSERVED",
            )

            await viewport_ready_future
            _log(
                "VIEWPORT_FIRST_FRAME_READY",
                previous_state="APP_READY",
                new_state="VIEWPORT_FIRST_FRAME_READY",
                trigger="VIEWPORT_READY_CALLBACK",
                app_ready=True,
                viewport_first_frame_ready=True,
                outcome="OBSERVED",
            )

            # Let the native ready callback and bootstrap-stage work leave the
            # current update before replacing that stage with the fixture.
            await app.next_update_async()
            _log(
                "STAGE_OPEN_REQUEST_BEGIN",
                previous_state="VIEWPORT_FIRST_FRAME_READY",
                new_state="STAGE_OPEN_REQUEST_ACTIVE",
                trigger="BOOTSTRAP_STAGE_READY",
                stage_path=stage_path,
                outcome="REQUESTED",
            )
            result = await omni.usd.get_context().open_stage_async(
                stage_path.as_posix()
            )
            success = (
                bool(result[0]) if isinstance(result, tuple) else bool(result)
            )
            message = (
                result[1]
                if isinstance(result, tuple) and len(result) > 1
                else ""
            )
            state = (
                "STAGE_OPEN_REQUEST_COMPLETE"
                if success
                else "STAGE_OPEN_FAILED"
            )
            _log(
                state,
                previous_state="STAGE_OPEN_REQUEST_ACTIVE",
                new_state=state,
                trigger="OPEN_STAGE_ASYNC_COMPLETE",
                stage_path=stage_path,
                success=success,
                message=message,
                app_ready=True,
                viewport_first_frame_ready=True,
                material_loading_completion_observable=False,
                completion_claim=False,
                outcome="OPENED" if success else "FAILED",
            )
        except asyncio.CancelledError:
            _log(
                "STAGE_OPEN_CANCELLED",
                previous_state="STAGE_OPEN_IN_PROGRESS",
                new_state="CANCELLED",
                trigger="EXTENSION_SHUTDOWN",
                stage_path=stage_path,
                outcome="CANCELLED",
            )
            raise
        except Exception as error:
            _log(
                "STAGE_OPEN_FAILED",
                previous_state="STAGE_OPEN_IN_PROGRESS",
                new_state="FAILED",
                trigger="UNHANDLED_EXCEPTION",
                stage_path=stage_path,
                error=repr(error),
                outcome="FAILED",
            )
        finally:
            viewport_ready, self._viewport_ready = self._viewport_ready, None
            if viewport_ready is not None:
                viewport_ready.destroy()

    def on_shutdown(self) -> None:
        """Cancel the owned task and destroy the viewport-ready observer."""

        task_was_active = bool(
            self._open_task is not None and not self._open_task.done()
        )
        _log(
            "EXTENSION_SHUTDOWN_REQUESTED",
            previous_state="ACTIVE" if task_was_active else "IDLE",
            new_state="SHUTDOWN_REQUESTED",
            trigger="EXTENSION_SHUTDOWN",
            open_task_active=task_was_active,
            outcome="CANCELLING" if task_was_active else "NO_ACTIVE_TASK",
        )
        if task_was_active:
            self._open_task.cancel()
        self._open_task = None
        viewport_ready, self._viewport_ready = self._viewport_ready, None
        if viewport_ready is not None:
            viewport_ready.destroy()
        _log(
            "EXTENSION_SHUTDOWN_COMPLETE",
            previous_state="SHUTDOWN_REQUESTED",
            new_state="STOPPED",
            trigger="OWNED_RESOURCES_RELEASED",
            open_task_active=False,
            viewport_observer_active=False,
            outcome="STOPPED",
        )
