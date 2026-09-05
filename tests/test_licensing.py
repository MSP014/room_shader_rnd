# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the public ORMS licensing and source-identification boundary."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXTENSION_ROOT = REPOSITORY_ROOT / "exts" / "msp.orms.runtime"


def _assert_spdx_header(path: Path, comment_prefix: str) -> None:
    leading_lines = path.read_text(encoding="utf-8").splitlines()[:4]
    assert (
        f"{comment_prefix} SPDX-FileCopyrightText: 2026 Maksim Pospelkov"
        in leading_lines
    ), path
    assert (
        f"{comment_prefix} SPDX-License-Identifier: MIT" in leading_lines
    ), path


def test_public_python_and_mdl_sources_identify_the_mit_grant():
    python_roots = (
        EXTENSION_ROOT / "msp",
        REPOSITORY_ROOT / "tests",
        REPOSITORY_ROOT / "tools",
    )
    python_files = tuple(
        path for root in python_roots for path in root.rglob("*.py")
    )
    mdl_files = tuple((EXTENSION_ROOT / "data" / "mdl").rglob("*.mdl"))

    assert python_files
    assert mdl_files
    for path in python_files:
        _assert_spdx_header(path, "#")
    for path in mdl_files:
        _assert_spdx_header(path, "//")


def test_licence_map_names_every_public_distribution_zone():
    licence_map = (REPOSITORY_ROOT / "LICENSE.md").read_text(encoding="utf-8")

    for identifier in (
        "MIT",
        "CC-BY-4.0",
        "LicenseRef-MSP-Asset-Evaluation-1.0",
        "CC0-1.0",
    ):
        assert identifier in licence_map

    assert "assets/_demo/Moskovskiy_av_150/**" in licence_map
    assert "assets/_demo/living_rooms/**" in licence_map
    assert "room_map_debug_x*/**/*.png" in licence_map


def test_demo_stage_and_third_party_notice_retain_provenance():
    demo_stage = (
        REPOSITORY_ROOT
        / "assets"
        / "_demo"
        / "Moskovskiy_av_150"
        / "usd"
        / "Moskovskiy_av_150.usd"
    ).read_text(encoding="utf-8")
    notices = (REPOSITORY_ROOT / "THIRD_PARTY_NOTICES.md").read_text(
        encoding="utf-8"
    )

    assert 'assetLicense = "LicenseRef-MSP-Asset-Evaluation-1.0"' in demo_stage
    assert "Greg Zaal" in notices
    assert "Jarod Guest" in notices
    assert "CC0 1.0" in notices
