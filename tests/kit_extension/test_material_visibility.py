"""Protect reversible ORMS visibility in restricted material menus."""

from msp.orms.runtime.materials.visibility import MaterialVisibilityOwner

from . import _support  # noqa: F401


def _owner(values, changes):
    def set_values(updated):
        changes.append(tuple(updated))
        values[:] = updated

    return MaterialVisibilityOwner(
        get_values=lambda: list(values),
        set_values=set_values,
    )


def test_empty_allow_list_already_exposes_every_material():
    values = []
    changes = []
    owner = _owner(values, changes)

    owner.start("Omniverse Room Map Shader")
    owner.stop()

    assert values == []
    assert changes == []


def test_matching_pattern_does_not_mutate_host_filter():
    values = ["Omniverse*"]
    changes = []
    owner = _owner(values, changes)

    owner.start("Omniverse Room Map Shader")
    owner.stop()

    assert values == ["Omniverse*"]
    assert changes == []


def test_owned_entry_is_added_and_removed_without_losing_host_changes():
    values = ["OmniPBR"]
    changes = []
    owner = _owner(values, changes)

    owner.start("Omniverse Room Map Shader")
    values.append("Host Added Later")
    owner.stop()

    assert changes == [
        ("OmniPBR", "Omniverse Room Map Shader"),
        ("OmniPBR", "Host Added Later"),
    ]
    assert values == ["OmniPBR", "Host Added Later"]
