"""Protect the two-action ORMS scene-profile UI."""

import sys
from types import ModuleType

from msp.orms.runtime.interior_set_profile_panel import (
    build_interior_set_profile_panel,
)


def test_profile_panel_exposes_only_direct_save_and_load_actions(monkeypatch):
    buttons = []

    class Scope:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Frame(Scope):
        def __init__(self, *_args, **_options):
            pass

        def set_collapsed_changed_fn(self, _callback):
            pass

    omni = ModuleType("omni")
    omni.__path__ = []
    ui = ModuleType("omni.ui")
    ui.CollapsableFrame = Frame
    ui.VStack = lambda **_options: Scope()
    ui.HStack = lambda **_options: Scope()
    ui.Label = lambda *_args, **_options: None
    ui.Button = lambda label, **_options: buttons.append(label)
    monkeypatch.setitem(sys.modules, "omni", omni)
    monkeypatch.setitem(sys.modules, "omni.ui", ui)

    build_interior_set_profile_panel(
        lambda: None,
        lambda: None,
        None,
    )

    assert buttons == ["Save Profile...", "Load Profile..."]
