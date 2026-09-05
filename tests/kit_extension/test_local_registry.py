# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the local Kit registry publication boundary."""

from pathlib import Path

import pytest

from tests.kit_extension.test_packaging import _fake_repository
from tools.publish_orms_local_registry import (
    _staging_directory,
    publish_local_registry,
)


def _fake_kit_app(tmp_path: Path) -> Path:
    root = tmp_path / "kit_app"
    (root / "repo.bat").parent.mkdir(parents=True)
    (root / "repo.bat").write_text("@echo off\n", encoding="utf-8")
    kit_executable = (
        root / "_build" / "windows-x86_64" / "release" / "kit" / "kit.exe"
    )
    kit_executable.parent.mkdir(parents=True)
    kit_executable.write_bytes(b"kit")
    return root


def test_publisher_stages_for_repo_tool_and_removes_owned_copy(tmp_path):
    repository_root = _fake_repository(tmp_path)
    kit_app_root = _fake_kit_app(tmp_path)
    registry_root = tmp_path / "registry"
    staged_extension = _staging_directory(kit_app_root)
    calls = []

    def run_command(command, *, cwd, check, env):
        assert (staged_extension / "config" / "extension.toml").is_file()
        assert env["GIT_CONFIG_VALUE_0"] == "https://example.invalid/orms.git"
        assert env["GIT_DIR"] == str(repository_root / ".git")
        assert env["GIT_WORK_TREE"] == str(repository_root)
        index_path = registry_root / "v2" / "registry.gz"
        index_path.parent.mkdir(parents=True)
        index_path.write_bytes(b"index")
        calls.append((tuple(command), cwd, check))

    publish_local_registry(
        repository_root,
        kit_app_root,
        registry_root,
        "https://example.invalid/orms.git",
        run_command=run_command,
    )

    assert calls == [
        (
            (
                str(kit_app_root / "repo.bat"),
                "publish_exts",
                "-c",
                "release",
            ),
            kit_app_root,
            True,
        )
    ]
    assert not staged_extension.exists()


def test_publisher_preserves_pre_existing_staging(tmp_path):
    repository_root = _fake_repository(tmp_path)
    kit_app_root = _fake_kit_app(tmp_path)
    staged_extension = _staging_directory(kit_app_root)
    staged_extension.mkdir(parents=True)
    marker = staged_extension / "owned_elsewhere.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to replace"):
        publish_local_registry(
            repository_root,
            kit_app_root,
            tmp_path / "registry",
            "https://example.invalid/orms.git",
        )

    assert marker.read_text(encoding="utf-8") == "keep"


def test_publisher_rejects_false_success_without_registry_index(tmp_path):
    repository_root = _fake_repository(tmp_path)
    kit_app_root = _fake_kit_app(tmp_path)
    staged_extension = _staging_directory(kit_app_root)

    with pytest.raises(RuntimeError, match="did not create or update"):
        publish_local_registry(
            repository_root,
            kit_app_root,
            tmp_path / "registry",
            "https://example.invalid/orms.git",
            run_command=lambda *args, **kwargs: None,
        )

    assert not staged_extension.exists()
