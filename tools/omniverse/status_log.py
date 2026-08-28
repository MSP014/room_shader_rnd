# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Format visually isolated Room Map console diagnostics."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

_STATUS_SEPARATOR = "=" * 20


def room_map_local_timestamp() -> str:
    """Return a millisecond-precision host-local timestamp with its offset."""

    local_now = datetime.now().astimezone()
    offset = local_now.strftime("%z")
    return (
        local_now.strftime("%Y-%m-%d %H:%M:%S.")
        + f"{local_now.microsecond // 1000:03d} {offset[:3]}:{offset[3:]}"
    )


def with_room_map_local_timestamp(message: str) -> str:
    """Append one readable local timestamp to a Room Map diagnostic."""

    return f"{message} | Local time: {room_map_local_timestamp()}"


def format_room_map_status_block(
    content: str,
    *,
    append_local_timestamp: Callable[[str], str] = (
        with_room_map_local_timestamp
    ),
) -> str:
    """Keep one timestamped Room Map record readable in a Kit log entry."""

    stamped_content = append_local_timestamp(content)
    return f"\n{_STATUS_SEPARATOR}\n{stamped_content}\n{_STATUS_SEPARATOR}"


def format_room_map_diagnostic_content(
    *,
    owner: str,
    process: str,
    state: str,
    details: Mapping[str, object],
) -> str:
    """Put a technical diagnostic into owner, state, and detail lines."""

    lines = [f"ROOM MAP {owner}", f"process={process} | state={state}"]
    lines.extend(f"{name}={value}" for name, value in details.items())
    return "\n".join(lines)


def format_room_map_diagnostic_block(
    *,
    owner: str,
    process: str,
    state: str,
    details: Mapping[str, object],
    append_local_timestamp: Callable[[str], str] = (
        with_room_map_local_timestamp
    ),
) -> str:
    """Format one timestamped Room Map block from semantic fields."""

    return format_room_map_status_block(
        format_room_map_diagnostic_content(
            owner=owner,
            process=process,
            state=state,
            details=details,
        ),
        append_local_timestamp=append_local_timestamp,
    )


def log_room_map_warning(
    *,
    owner: str,
    process: str,
    state: str,
    details: Mapping[str, object],
    log_warning: Callable[[str], None] | None = None,
    append_local_timestamp: Callable[[str], str] = (
        with_room_map_local_timestamp
    ),
) -> None:
    """Write one formatted Room Map warning through Kit or an injected sink."""

    if log_warning is None:
        import carb

        log_warning = carb.log_warn

    log_warning(
        format_room_map_diagnostic_block(
            owner=owner,
            process=process,
            state=state,
            details=details,
            append_local_timestamp=append_local_timestamp,
        )
    )


def log_room_map_error(
    *,
    owner: str,
    process: str,
    state: str,
    details: Mapping[str, object],
    log_error: Callable[[str], None] | None = None,
    append_local_timestamp: Callable[[str], str] = (
        with_room_map_local_timestamp
    ),
) -> None:
    """Write one formatted Room Map error through Kit or an injected sink."""

    if log_error is None:
        import carb

        log_error = carb.log_error

    log_error(
        format_room_map_diagnostic_block(
            owner=owner,
            process=process,
            state=state,
            details=details,
            append_local_timestamp=append_local_timestamp,
        )
    )
