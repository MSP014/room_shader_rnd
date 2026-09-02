#!/usr/bin/env python3
"""Build a standalone ORMS Kit extension from canonical repository sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

EXTENSION_NAME = "msp.orms.runtime"
DEBUG_FAMILY_NAMES = {
    1: "room_map_debug",
    2: "room_map_debug_x2",
    3: "room_map_debug_x3",
    4: "room_map_debug_x4",
}
MDL_FILES = ("room_map.mdl", "room_map_single.mdl")


def _required_debug_tiles(repository_root: Path) -> tuple[Path, ...]:
    texture_root = repository_root / "assets" / "_external" / "tex"
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
        repository_root / "tools" / "omniverse" / "reload_room_map_runtime.py",
    ]
    required.extend(
        repository_root / "src" / "mdl" / filename for filename in MDL_FILES
    )
    required.extend(_required_debug_tiles(repository_root))
    missing = tuple(path for path in required if not path.is_file())
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Cannot package ORMS; required source resources are missing:\n"
            + missing_text
        )


def _copy_python_runtime(
    repository_root: Path, output_directory: Path
) -> None:
    source_root = repository_root / "tools" / "omniverse"
    target_root = output_directory / "data" / "runtime" / "tools" / "omniverse"
    for source_path in source_root.rglob("*.py"):
        relative_path = source_path.relative_to(source_root)
        target_path = target_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _copy_mdl_content(repository_root: Path, output_directory: Path) -> None:
    source_root = repository_root / "src" / "mdl"
    target_root = output_directory / "data" / "mdl"
    target_root.mkdir(parents=True, exist_ok=True)
    for filename in MDL_FILES:
        shutil.copy2(source_root / filename, target_root / filename)


def _copy_debug_atlases(repository_root: Path, output_directory: Path) -> None:
    source_root = repository_root / "assets" / "_external" / "tex"
    target_root = output_directory / "data" / "atlases" / "debug"
    for room_size, family_name in DEBUG_FAMILY_NAMES.items():
        family_target = target_root / f"x{room_size}"
        family_target.mkdir(parents=True, exist_ok=True)
        for tile in range(1001, 1009):
            filename = f"{family_name}.{tile}.png"
            shutil.copy2(
                source_root / family_name / filename,
                family_target / filename,
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
        "source_policy": "canonical repository sources copied at build time",
        "production_atlases_included": False,
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
    _copy_python_runtime(root, output)
    _copy_mdl_content(root, output)
    _copy_debug_atlases(root, output)
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
