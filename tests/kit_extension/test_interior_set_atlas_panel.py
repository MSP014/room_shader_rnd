# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect layout and collapse state in the staged Interior Set panel."""

import inspect

from msp.orms.runtime.ui.atlas_panel import (
    _build_structural_actions,
    _collapsable_frame,
    build_interior_set_atlas_panel,
)


def test_collapsable_frame_uses_supplied_state_and_callback():
    events = []

    class Frame:
        def __init__(self, title, **options):
            self.title = title
            self.options = options
            self.callback = None

        def set_collapsed_changed_fn(self, callback):
            self.callback = callback

    class Ui:
        CollapsableFrame = Frame

    frame = _collapsable_frame(
        Ui,
        "Living Rooms",
        collapsed=True,
        collapsed_changed=events.append,
    )

    assert frame.options == {"collapsed": True, "height": 0}
    frame.callback(False)
    assert events == [False]


def test_structural_actions_precede_the_repeatable_set_list():
    buttons = []

    class Stack:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class Ui:
        @staticmethod
        def HStack(**_options):
            return Stack()

        @staticmethod
        def Button(label, **options):
            buttons.append((label, options))

    class Controller:
        dirty = True

        def add(self):
            return None

        def revert(self):
            return None

    _build_structural_actions(
        Ui,
        Controller(),
        lambda: None,
        lambda: None,
    )

    assert [label for label, _options in buttons] == [
        "+ Add Interior Set",
        "Apply Interior Sets",
        "Revert unapplied changes",
        "Reset complete atlas configuration",
    ]
    source = inspect.getsource(build_interior_set_atlas_panel)
    assert source.index("_build_structural_actions(") < source.index(
        "for item in controller.draft.sets:"
    )
    assert '"Clear"' in source
    assert '"Clear all production folders"' in source
