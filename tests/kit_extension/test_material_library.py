# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect symmetric ORMS MDL and Material Library registration."""

from pathlib import Path

import pytest
from msp.orms.runtime.materials.library import MaterialLibraryRegistration
from msp.orms.runtime.materials.visibility import MaterialVisibilityOwner
from msp.orms.runtime.resources import ResourceLayout

from . import _support  # noqa: F401


def _resources(tmp_path: Path) -> ResourceLayout:
    mdl_root = tmp_path / "mdl"
    mdl_root.mkdir()
    return ResourceLayout(
        extension_root=tmp_path,
        mdl_root=mdl_root,
        debug_atlases=(),
    )


def test_registration_adds_and_removes_the_exact_orms_entry(tmp_path):
    calls = []

    def register(extension_name, content_path):
        calls.append(("register", extension_name, content_path))
        return ["linked-room-map"]

    def deregister(extension_name, links):
        calls.append(("deregister", extension_name, tuple(links)))
        return True

    def add(source_asset, subidentifier, group, **kwargs):
        calls.append(
            (
                "add",
                source_asset,
                subidentifier,
                group,
                kwargs["display_name"],
            )
        )
        return True

    def remove(source_asset, subidentifier):
        calls.append(("remove", source_asset, subidentifier))
        return True

    filter_values = ["OmniPBR"]

    def set_filter_values(values):
        calls.append(("filter", tuple(values)))
        filter_values[:] = values

    visibility = MaterialVisibilityOwner(
        get_values=lambda: list(filter_values),
        set_values=set_filter_values,
    )

    registration = MaterialLibraryRegistration(
        register_content=register,
        deregister_content=deregister,
        add_material=add,
        remove_material=remove,
        visibility_owner=visibility,
    )

    registration.start("msp.orms.runtime", _resources(tmp_path))
    registration.stop()

    assert calls == [
        ("register", "msp.orms.runtime", str((tmp_path / "mdl").resolve())),
        ("filter", ("OmniPBR", "Omniverse Room Map Shader")),
        (
            "add",
            "room_map.mdl",
            "room_map",
            "ORMS",
            "Omniverse Room Map Shader",
        ),
        ("filter", ("OmniPBR",)),
        ("remove", "room_map.mdl", "room_map"),
        ("deregister", "msp.orms.runtime", ("linked-room-map",)),
    ]


def test_empty_mdl_registration_never_exposes_material_entry(tmp_path):
    added = []
    registration = MaterialLibraryRegistration(
        register_content=lambda _name, _path: [],
        deregister_content=lambda _name, _links: True,
        add_material=lambda *_args, **_kwargs: added.append(True),
        remove_material=lambda _asset, _subidentifier: True,
    )

    with pytest.raises(RuntimeError, match="register the ORMS MDL"):
        registration.start("msp.orms.runtime", _resources(tmp_path))

    assert added == []


def test_mdl_content_is_deregistered_even_if_library_removal_fails(tmp_path):
    calls = []

    def remove(_source_asset, _subidentifier):
        calls.append("remove")
        raise RuntimeError("material library unavailable")

    def deregister(_extension_name, _links):
        calls.append("deregister")
        return True

    registration = MaterialLibraryRegistration(
        register_content=lambda _name, _path: ["linked-room-map"],
        deregister_content=deregister,
        add_material=lambda *_args, **_kwargs: True,
        remove_material=remove,
    )
    registration.start("msp.orms.runtime", _resources(tmp_path))

    with pytest.raises(RuntimeError, match="material library unavailable"):
        registration.stop()

    assert calls == ["remove", "deregister"]
