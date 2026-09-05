#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Stage and publish ORMS through a local Kit extension registry."""

from __future__ import annotations

import argparse
import os
import shutil

# Local Git and Kit commands are required by this publication boundary.
import subprocess  # nosec B404
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

if __package__:
    from .package_orms_extension import EXTENSION_NAME, build_extension
else:
    from package_orms_extension import EXTENSION_NAME, build_extension

WINDOWS_PLATFORM = "windows-x86_64"


def _staging_directory(kit_app_root: Path) -> Path:
    """Return the generated extension path consumed by ``publish_exts``."""

    return (
        kit_app_root
        / "_build"
        / WINDOWS_PLATFORM
        / "release"
        / "exts"
        / EXTENSION_NAME
    )


def _validate_kit_app(kit_app_root: Path) -> Path:
    """Validate the local Windows Kit App Template publishing boundary."""

    repo_launcher = kit_app_root / "repo.bat"
    kit_executable = (
        kit_app_root
        / "_build"
        / WINDOWS_PLATFORM
        / "release"
        / "kit"
        / "kit.exe"
    )
    missing = tuple(
        path for path in (repo_launcher, kit_executable) if not path.is_file()
    )
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Kit application publishing prerequisites are missing:\n"
            + missing_text
        )
    return repo_launcher


def _repository_url(repository_root: Path) -> str:
    """Return the source repository URL recorded in package metadata."""

    # Executable and arguments are fixed; no user value enters this command.
    result = subprocess.run(  # nosec B603
        ("git", "config", "--get", "remote.origin.url"),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    repository_url = result.stdout.strip()
    if not repository_url:
        raise RuntimeError("The ORMS repository has no remote.origin.url.")
    return repository_url


def publish_local_registry(
    repository_root: Path,
    kit_app_root: Path,
    registry_root: Path,
    repository_url: str,
    *,
    run_command: Callable[..., Any] = subprocess.run,
) -> None:
    """Publish one generated ORMS package and remove only owned staging."""

    root = repository_root.resolve()
    kit_root = kit_app_root.resolve()
    registry = registry_root.resolve()
    repo_launcher = _validate_kit_app(kit_root)
    staged_extension = _staging_directory(kit_root)
    if staged_extension.exists():
        raise FileExistsError(
            "Refusing to replace an existing Kit extension staging path: "
            f"{staged_extension}"
        )

    index_path = registry / "v2" / "registry.gz"
    index_stamp = (
        (index_path.stat().st_mtime_ns, index_path.stat().st_size)
        if index_path.is_file()
        else None
    )
    build_extension(root, staged_extension)
    try:
        command: Sequence[str] = (
            str(repo_launcher),
            "publish_exts",
            "-c",
            "release",
        )
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "remote.origin.url",
                "GIT_CONFIG_VALUE_0": repository_url,
                "GIT_DIR": str(root / ".git"),
                "GIT_WORK_TREE": str(root),
            }
        )
        run_command(
            command,
            cwd=kit_root,
            check=True,
            env=environment,
        )
        published_stamp = (
            (index_path.stat().st_mtime_ns, index_path.stat().st_size)
            if index_path.is_file()
            else None
        )
        if published_stamp is None or published_stamp == index_stamp:
            raise RuntimeError(
                "Kit publisher did not create or update the local registry "
                f"index: {index_path}"
            )
    finally:
        # The normal app must discover ORMS from the registry, not this
        # publisher-only staging copy.
        shutil.rmtree(staged_extension)


def main() -> int:
    """Parse the Kit App Template root and publish the local package."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kit-app-root",
        type=Path,
        required=True,
        help="Kit App Template repository configured for the ORMS registry.",
    )
    parser.add_argument(
        "--registry-root",
        type=Path,
        help=(
            "Registry configured in the Kit App Template. Defaults to "
            "<repository>/out/kit_registry."
        ),
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    registry_root = (
        args.registry_root or repository_root / "out" / "kit_registry"
    )
    publish_local_registry(
        repository_root,
        args.kit_app_root,
        registry_root,
        _repository_url(repository_root),
    )
    print("Published msp.orms.runtime to the configured local registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
