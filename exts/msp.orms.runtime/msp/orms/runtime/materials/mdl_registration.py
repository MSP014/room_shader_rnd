# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Register ORMS MDL content across local filesystem boundaries."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _resolve_target_search_root() -> Path:
    """Return Kit's extension-owned MDL search-path root."""

    import carb.tokens

    tokens = carb.tokens.get_tokens_interface()
    target = tokens.resolve("${omni.mdl}/search_paths/omniverse_exts")
    if not target:
        raise RuntimeError("Kit did not provide an MDL extension search path")
    return Path(target).resolve()


def _same_filesystem(source_root: Path, target_root: Path) -> bool:
    """Report whether hard links can cross between the two directories."""

    try:
        return source_root.stat().st_dev == target_root.stat().st_dev
    except OSError:
        return False


def _register_linked_content(
    extension_name: str,
    content_path: str,
) -> list[str]:
    """Delegate same-filesystem registration to Kit's supported helper."""

    import omni.mdl.neuraylib as neuraylib

    return list(
        neuraylib.register_extension_content(extension_name, content_path)
    )


def _copy_cross_filesystem_content(
    source_root: Path,
    target_root: Path,
) -> list[str]:
    """Materialise MDL files when Windows hard links cannot cross volumes."""

    registered: list[str] = []
    try:
        for source_path in sorted(source_root.rglob("*")):
            if not source_path.is_file():
                continue
            target_path = target_root / source_path.relative_to(source_root)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            registered.append(str(target_path))
    except Exception:
        _remove_registered_content(target_root, registered)
        raise
    return registered


def _normalised_absolute(path: str | Path) -> Path:
    """Normalise a path without following a registered symlink target."""

    return Path(os.path.abspath(path))


def _remove_registered_content(
    target_root: Path,
    registered_files: list[str],
) -> bool:
    """Remove only files owned beneath the resolved Kit search root."""

    normalised_root = _normalised_absolute(target_root)
    parent_directories: set[Path] = set()
    success = True
    for registered_file in registered_files:
        registered_path = _normalised_absolute(registered_file)
        try:
            registered_path.relative_to(normalised_root)
        except ValueError:
            success = False
            continue
        if registered_path.is_file() or registered_path.is_symlink():
            registered_path.unlink()
        elif registered_path.exists():
            success = False
            continue

        parent = registered_path.parent
        while parent != normalised_root:
            parent_directories.add(parent)
            parent = parent.parent

    for parent in sorted(
        parent_directories,
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            parent.rmdir()
        except OSError:
            pass
    return success


def _log_cross_filesystem_copy() -> None:
    """Explain why this checkout cannot use Kit's default hard links."""

    import carb

    carb.log_info(
        "[ORMS] MDL source and Kit search paths use different filesystems; "
        "materialising managed copies instead of hard links"
    )


def register_mdl_content(
    extension_name: str,
    content_path: str,
) -> list[str]:
    """Register MDL by link where possible and by managed copy otherwise."""

    source_root = Path(content_path).resolve()
    target_root = _resolve_target_search_root()
    if _same_filesystem(source_root, target_root):
        return _register_linked_content(extension_name, str(source_root))

    _log_cross_filesystem_copy()
    return _copy_cross_filesystem_content(source_root, target_root)


def deregister_mdl_content(
    extension_name: str,
    registered_files: list[str],
) -> bool:
    """Remove linked or copied content without escaping Kit's search root."""

    del extension_name
    return _remove_registered_content(
        _resolve_target_search_root(),
        registered_files,
    )
