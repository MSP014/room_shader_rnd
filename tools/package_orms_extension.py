#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Build a standalone ORMS Kit extension from canonical repository sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

EXTENSION_NAME = "msp.orms.runtime"
DEBUG_FAMILY_NAMES = {
    1: "room_map_debug_x1",
    2: "room_map_debug_x2",
    3: "room_map_debug_x3",
    4: "room_map_debug_x4",
}
MDL_FILES = ("room_map.mdl", "room_map_single.mdl")
DEMO_STAGE = Path("Moskovskiy_av_150") / "usd" / "Moskovskiy_av_150_HDRI.usd"
DEMO_PROFILE = Path("Moskovskiy_av_150") / "usd" / "test_150.orms"
LICENSING_FILES = (
    Path("LICENSE.md"),
    Path("THIRD_PARTY_NOTICES.md"),
    Path("LICENSES") / "MIT.txt",
    Path("LICENSES") / "CC-BY-4.0.txt",
    Path("LICENSES") / "CC0-1.0.txt",
    Path("LICENSES") / "LicenseRef-MSP-Asset-Evaluation-1.0.txt",
)


def _required_debug_tiles(repository_root: Path) -> tuple[Path, ...]:
    texture_root = (
        repository_root / "exts" / EXTENSION_NAME / "data" / "atlases"
    )
    return tuple(
        texture_root / family_name / f"{family_name}.{tile}.png"
        for family_name in DEBUG_FAMILY_NAMES.values()
        for tile in range(1001, 1009)
    )


def _validate_sources(repository_root: Path, output_directory: Path) -> None:
    if output_directory.exists():
        raise FileExistsError(
            f"Refusing to overwrite an existing bundle: {output_directory}"
        )
    required = [
        repository_root
        / "exts"
        / EXTENSION_NAME
        / "config"
        / "extension.toml",
        repository_root
        / "exts"
        / EXTENSION_NAME
        / "msp"
        / "orms"
        / "runtime"
        / "reload_room_map_runtime.py",
    ]
    required.extend(
        repository_root / "exts" / EXTENSION_NAME / "data" / "mdl" / filename
        for filename in MDL_FILES
    )
    required.extend(_required_debug_tiles(repository_root))
    demo_root = repository_root / "assets" / "_demo"
    required.extend((demo_root / DEMO_STAGE, demo_root / DEMO_PROFILE))
    required.extend(repository_root / path for path in LICENSING_FILES)
    missing = tuple(path for path in required if not path.is_file())
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Cannot package ORMS; required source resources are missing:\n"
            + missing_text
        )


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(output_directory: Path) -> None:
    files = tuple(
        sorted(
            path
            for path in output_directory.rglob("*")
            if path.is_file() and path.name != "bundle_manifest.json"
        )
    )
    manifest = {
        "extension": EXTENSION_NAME,
        "source_policy": (
            "canonical extension tree with debug atlases and demo content"
        ),
        "production_atlases_included": False,
        "demo_content_included": True,
        "licensing": {
            "software": "MIT",
            "debug_atlases": "CC-BY-4.0",
            "demo_assets": "LicenseRef-MSP-Asset-Evaluation-1.0",
            "demo_hdri": "CC0-1.0",
            "map": "LICENSE.md",
            "third_party_notices": "THIRD_PARTY_NOTICES.md",
        },
        "files": [
            {
                "path": path.relative_to(output_directory).as_posix(),
                "sha256": _file_digest(path),
            }
            for path in files
        ],
    }
    manifest_path = output_directory / "data" / "bundle_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def build_extension(repository_root: Path, output_directory: Path) -> Path:
    """Create one non-overwriting standalone extension directory."""

    root = repository_root.resolve()
    output = output_directory.resolve()
    _validate_sources(root, output)
    template_root = root / "exts" / EXTENSION_NAME
    shutil.copytree(
        template_root,
        output,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(root / "assets" / "_demo", output / "data" / "demo")
    shutil.copy2(root / "LICENSE.md", output / "LICENSE.md")
    shutil.copy2(
        root / "THIRD_PARTY_NOTICES.md",
        output / "THIRD_PARTY_NOTICES.md",
    )
    shutil.copytree(root / "LICENSES", output / "LICENSES")
    _write_manifest(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New directory to create for the standalone Kit extension.",
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    output = build_extension(repository_root, args.output)
    print(f"Built {EXTENSION_NAME}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
