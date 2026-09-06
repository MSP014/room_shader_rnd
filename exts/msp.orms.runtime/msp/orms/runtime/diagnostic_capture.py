# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Enable the complete Kit diagnostic surface needed by ORMS recovery."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

USD_DIAGNOSTICS_MUTED_SETTING = "/persistent/app/usd/muteUsdDiagnostics"
USD_CODING_ERRORS_MUTED_SETTING = "/persistent/app/usd/muteUsdCodingError"
CONSOLE_SOURCES_SETTING = "/persistent/app/extensions/console/sources"
CONSOLE_FILTER_LEVEL_SETTING = "/persistent/app/extensions/console/filterLevel"
FILE_LOG_LEVEL_SETTING = "/log/fileLogLevel"


def enable_complete_diagnostics(
    settings: Any,
    *,
    orms_verbose_setting: str,
    verbose_level: int,
) -> tuple[str, ...]:
    """Unmute USD, ORMS, file, and every registered Console provider."""

    settings.set(USD_DIAGNOSTICS_MUTED_SETTING, False)
    settings.set(USD_CODING_ERRORS_MUTED_SETTING, False)
    settings.set(orms_verbose_setting, True)
    settings.set(CONSOLE_FILTER_LEVEL_SETTING, verbose_level)
    settings.set(FILE_LOG_LEVEL_SETTING, "Verbose")

    sources = settings.get(CONSOLE_SOURCES_SETTING)
    source_names = (
        tuple(sorted(sources)) if isinstance(sources, Mapping) else ()
    )
    for source_name in source_names:
        settings.set(
            f"{CONSOLE_SOURCES_SETTING}/{source_name}",
            True,
        )
    return source_names
