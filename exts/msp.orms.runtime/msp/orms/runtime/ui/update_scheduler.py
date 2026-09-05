# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Coalesce deferred ORMS UI callbacks on Kit's asyncio loop."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from ...scene.status_log import log_room_map_error


class UiUpdateScheduler:
    """Keep only the newest pending callback for each editable control."""

    def __init__(self) -> None:
        self._tasks: dict[str, Any] = {}

    def schedule(
        self,
        key: str,
        callback: Callable[[], None],
        *,
        delay_seconds: float,
    ) -> None:
        """Schedule one guarded update after a delay or the next Kit frame."""

        pending = self._tasks.pop(key, None)
        if pending is not None:
            pending.cancel()

        async def invoke() -> None:
            import omni.kit.app

            try:
                if delay_seconds:
                    await asyncio.sleep(delay_seconds)
                else:
                    await omni.kit.app.get_app().next_update_async()
                callback()
            except asyncio.CancelledError:
                return
            except Exception as error:
                log_room_map_error(
                    owner="ORMS UI",
                    process="DEFERRED SETTING UPDATE",
                    state="FAILED",
                    details={"key": key, "error": repr(error)},
                )
            finally:
                current = self._tasks.get(key)
                if current is asyncio.current_task():
                    self._tasks.pop(key, None)

        self._tasks[key] = asyncio.ensure_future(invoke())

    def stop(self) -> None:
        """Cancel and release every update owned by the ORMS window."""

        for task in self._tasks.values():
            task.cancel()
        self._tasks = {}
