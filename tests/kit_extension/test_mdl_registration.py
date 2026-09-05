# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect portable ORMS MDL registration outside the Kit install volume."""

from pathlib import Path

from msp.orms.runtime.materials import mdl_registration

from . import _support  # noqa: F401


def _write_mdl_tree(source_root: Path) -> None:
    source_root.mkdir()
    (source_root / "room_map.mdl").write_text(
        "mdl 1.7;",
        encoding="utf-8",
    )
    diagnostics = source_root / "diagnostics"
    diagnostics.mkdir()
    (diagnostics / "direction.mdl").write_text(
        "mdl 1.7;",
        encoding="utf-8",
    )


def test_cross_filesystem_registration_materialises_managed_copies(
    tmp_path,
    monkeypatch,
):
    source_root = tmp_path / "source"
    target_root = tmp_path / "search"
    _write_mdl_tree(source_root)
    target_root.mkdir()

    monkeypatch.setattr(
        mdl_registration,
        "_resolve_target_search_root",
        lambda: target_root,
    )
    monkeypatch.setattr(
        mdl_registration,
        "_same_filesystem",
        lambda _source, _target: False,
    )
    monkeypatch.setattr(
        mdl_registration,
        "_log_cross_filesystem_copy",
        lambda: None,
    )

    registered = mdl_registration.register_mdl_content(
        "msp.orms.runtime",
        str(source_root),
    )

    assert registered == [
        str(target_root / "diagnostics" / "direction.mdl"),
        str(target_root / "room_map.mdl"),
    ]
    assert (target_root / "room_map.mdl").read_text(encoding="utf-8") == (
        "mdl 1.7;"
    )


def test_same_filesystem_registration_delegates_to_kit(
    tmp_path,
    monkeypatch,
):
    source_root = tmp_path / "source"
    target_root = tmp_path / "search"
    _write_mdl_tree(source_root)
    target_root.mkdir()
    calls = []

    monkeypatch.setattr(
        mdl_registration,
        "_resolve_target_search_root",
        lambda: target_root,
    )
    monkeypatch.setattr(
        mdl_registration,
        "_same_filesystem",
        lambda _source, _target: True,
    )
    monkeypatch.setattr(
        mdl_registration,
        "_register_linked_content",
        lambda name, path: calls.append((name, path)) or ["linked"],
    )

    registered = mdl_registration.register_mdl_content(
        "msp.orms.runtime",
        str(source_root),
    )

    assert registered == ["linked"]
    assert calls == [("msp.orms.runtime", str(source_root.resolve()))]


def test_deregistration_removes_only_search_root_content(
    tmp_path,
    monkeypatch,
):
    target_root = tmp_path / "search"
    owned_file = target_root / "diagnostics" / "direction.mdl"
    outside_file = tmp_path / "outside.mdl"
    owned_file.parent.mkdir(parents=True)
    owned_file.write_text("owned", encoding="utf-8")
    outside_file.write_text("outside", encoding="utf-8")

    monkeypatch.setattr(
        mdl_registration,
        "_resolve_target_search_root",
        lambda: target_root,
    )

    removed = mdl_registration.deregister_mdl_content(
        "msp.orms.runtime",
        [str(owned_file), str(outside_file)],
    )

    assert removed is False
    assert not owned_file.exists()
    assert not owned_file.parent.exists()
    assert outside_file.read_text(encoding="utf-8") == "outside"
