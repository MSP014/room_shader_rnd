# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Track one observable asynchronous asset-loading batch at a time."""

from __future__ import annotations

from collections.abc import Callable


class AssetBatchTracker:
    """Own timing and message state for the current Kit asset-loading batch."""

    def __init__(self, clock: Callable[[], float]):
        self._clock = clock
        self.reset_for_stage_open()
        self.active = False

    @property
    def batch_id(self) -> int:
        """Return the identifier of the latest batch in the current stage run."""

        return self._batch_id

    def reset_for_stage_open(self) -> None:
        """Reset identifiers and timing after the previous batch is closed."""

        self._batch_id = 0
        self.active = False
        self._started_at: float | None = None
        self._stage_identifier: str | None = None
        self._max_total_files = 0
        self._current_message = ""
        self._current_message_started_at: float | None = None
        self._longest_message = "<none>"
        self._longest_message_ms = 0.0

    def start(self, stage_identifier: str) -> None:
        """Start a new batch after the caller resolves any active predecessor."""

        self._batch_id += 1
        self.active = True
        self._started_at = self._clock()
        self._stage_identifier = stage_identifier
        self._max_total_files = 0
        self._current_message = ""
        self._current_message_started_at = None
        self._longest_message = "<none>"
        self._longest_message_ms = 0.0

    def _close_message_interval(self, now: float) -> None:
        if self._current_message_started_at is None:
            return
        duration_ms = (now - self._current_message_started_at) * 1000.0
        if duration_ms > self._longest_message_ms:
            self._longest_message = self._current_message or "<empty>"
            self._longest_message_ms = duration_ms
        self._current_message_started_at = None

    def record_status(
        self,
        message: str,
        total_files: int,
        now: float,
    ) -> None:
        """Record the longest continuously reported loading message."""

        if not self.active:
            return
        self._max_total_files = max(self._max_total_files, total_files)
        if message == self._current_message:
            return
        self._close_message_interval(now)
        self._current_message = message
        if message:
            self._current_message_started_at = now

    def finish(
        self,
        state: str,
        *,
        terminal_reason: str,
        message: str,
        files_loaded: int,
        total_files: int,
        streaming_busy: bool,
    ) -> dict[str, object] | None:
        """Close the active batch and return its complete diagnostic payload."""

        if not self.active:
            return None
        now = self._clock()
        self._close_message_interval(now)
        self._max_total_files = max(self._max_total_files, total_files)
        duration_ms = (
            round((now - self._started_at) * 1000.0, 3)
            if self._started_at is not None
            else "unavailable"
        )
        details: dict[str, object] = {
            "asset_batch_id": self._batch_id,
            "asset_batch_stage_identifier": self._stage_identifier or "<none>",
            "asset_batch_duration_ms": duration_ms,
            "max_total_files": self._max_total_files,
            "longest_loading_message": self._longest_message,
            "longest_loading_message_ms": round(
                self._longest_message_ms,
                3,
            ),
            "final_loading_message": message or "<empty>",
            "final_files_loaded": files_loaded,
            "final_total_files": total_files,
            "final_streaming_busy": streaming_busy,
            "completion_scope": "current_async_asset_batch",
            "batch_terminal_reason": terminal_reason,
            "batch_completion_observed": (
                state == "ASSET_BATCH_LOADING_COMPLETE"
            ),
            "native_material_wait_complete": "unobservable",
            "renderer_idle_observable": False,
        }
        self.active = False
        self._started_at = None
        self._stage_identifier = None
        self._current_message_started_at = None
        return details
