# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the packaged extension's opt-in research logging boundary."""

from pathlib import Path

from msp.orms.runtime import service


class _Settings:
    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled

    def get(self, path: str) -> bool:
        assert path == service._VERBOSE_DIAGNOSTICS_SETTING
        return self._enabled


def test_verbose_diagnostics_setting_is_read_as_a_boolean():
    assert not service._verbose_diagnostics_enabled(_Settings(False))
    assert service._verbose_diagnostics_enabled(_Settings(True))


def test_runtime_service_defaults_research_diagnostics_off():
    source = Path(service.__file__).read_text(encoding="utf-8")

    assert (
        "settings.set_default(_VERBOSE_DIAGNOSTICS_SETTING, False)" in source
    )
    assert (
        "verbose_diagnostics=_verbose_diagnostics_enabled(settings)" in source
    )
