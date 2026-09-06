# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the packaged extension's recovery diagnostic capture."""

from pathlib import Path

from msp.orms.runtime import service
from msp.orms.runtime.diagnostic_capture import (
    CONSOLE_FILTER_LEVEL_SETTING,
    CONSOLE_SOURCES_SETTING,
    FILE_LOG_LEVEL_SETTING,
    USD_CODING_ERRORS_MUTED_SETTING,
    USD_DIAGNOSTICS_MUTED_SETTING,
    enable_complete_diagnostics,
)


class _Settings:
    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled

    def get(self, path: str) -> bool:
        assert path == service._VERBOSE_DIAGNOSTICS_SETTING
        return self._enabled


class _WritableSettings:
    def __init__(self, values=None) -> None:
        self.values = dict(values or {})

    def get(self, path: str):
        return self.values.get(path)

    def set(self, path: str, value) -> None:
        self.values[path] = value


def test_verbose_diagnostics_setting_is_read_as_a_boolean():
    assert not service._verbose_diagnostics_enabled(_Settings(False))
    assert service._verbose_diagnostics_enabled(_Settings(True))


def test_complete_diagnostics_unmutes_every_required_channel():
    settings = _WritableSettings(
        {
            CONSOLE_SOURCES_SETTING: {
                "omni.usd": False,
                "rtx.scenedb": False,
            }
        }
    )

    sources = enable_complete_diagnostics(
        settings,
        orms_verbose_setting=service._VERBOSE_DIAGNOSTICS_SETTING,
        verbose_level=0,
    )

    assert sources == ("omni.usd", "rtx.scenedb")
    assert settings.values[USD_DIAGNOSTICS_MUTED_SETTING] is False
    assert settings.values[USD_CODING_ERRORS_MUTED_SETTING] is False
    assert settings.values[service._VERBOSE_DIAGNOSTICS_SETTING] is True
    assert settings.values[CONSOLE_FILTER_LEVEL_SETTING] == 0
    assert settings.values[FILE_LOG_LEVEL_SETTING] == "Verbose"
    assert settings.values[f"{CONSOLE_SOURCES_SETTING}/omni.usd"] is True
    assert settings.values[f"{CONSOLE_SOURCES_SETTING}/rtx.scenedb"] is True


def test_complete_diagnostics_handles_missing_console_sources():
    settings = _WritableSettings()

    sources = enable_complete_diagnostics(
        settings,
        orms_verbose_setting=service._VERBOSE_DIAGNOSTICS_SETTING,
        verbose_level=0,
    )

    assert sources == ()
    assert settings.values[USD_DIAGNOSTICS_MUTED_SETTING] is False


def test_complete_diagnostics_is_idempotent():
    settings = _WritableSettings({CONSOLE_SOURCES_SETTING: {"omni.usd": True}})

    for _index in range(2):
        enable_complete_diagnostics(
            settings,
            orms_verbose_setting=service._VERBOSE_DIAGNOSTICS_SETTING,
            verbose_level=0,
        )

    assert settings.values[f"{CONSOLE_SOURCES_SETTING}/omni.usd"] is True


def test_runtime_service_enables_recovery_diagnostics_before_activation():
    source = Path(service.__file__).read_text(encoding="utf-8")

    assert "source_names = enable_complete_diagnostics(" in source
    assert (
        "verbose_diagnostics=_verbose_diagnostics_enabled(settings)" in source
    )
