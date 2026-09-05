# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect content-sized collapse behaviour across every ORMS tab."""

from pathlib import Path
from types import ModuleType

from msp.orms.shared_room.ui_buttons import (
    SELECTION_BUTTON_STYLE,
    selection_button,
)
from msp.orms.shared_room.ui_sections import collapsable_frame
from msp.orms.shared_room.ui_tooltips import with_wrapped_tooltip


def test_shared_collapsable_frame_releases_content_height_and_reports_state():
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

    frame = collapsable_frame(
        Ui,
        "Room families",
        collapsed=True,
        collapsed_changed=events.append,
    )

    assert frame.options == {"collapsed": True, "height": 0}
    frame.callback(False)
    assert events == [False]


def test_hover_help_is_fixed_width_and_word_wrapped(monkeypatch):
    label_options = []

    class Stack:
        def __init__(self, **options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class Widget:
        def set_tooltip_fn(self, callback):
            self.callback = callback

    omni = ModuleType("omni")
    ui = ModuleType("omni.ui")
    ui.VStack = Stack
    ui.Label = lambda text, **options: label_options.append((text, options))
    omni.ui = ui
    monkeypatch.setitem(__import__("sys").modules, "omni", omni)
    monkeypatch.setitem(__import__("sys").modules, "omni.ui", ui)

    widget = Widget()
    with_wrapped_tooltip(widget, "Readable hover help")
    widget.callback()

    assert label_options == [
        (
            "Readable hover help",
            {
                "width": 300,
                "height": 0,
                "word_wrap": True,
                "style": {"color": 0xFF202020},
            },
        )
    ]


def test_every_runtime_collapsable_frame_uses_the_shared_layout_helper():
    repository_root = Path(__file__).resolve().parents[2]
    search_roots = (
        repository_root
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "shared_room",
        repository_root
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime",
    )
    direct_constructors = []
    for root in search_roots:
        for path in root.glob("*.py"):
            if "ui.CollapsableFrame(" in path.read_text(encoding="utf-8"):
                direct_constructors.append(path.relative_to(repository_root))

    assert direct_constructors == [
        Path("exts/msp.orms.runtime/msp/orms/shared_room/ui_sections.py")
    ]


def test_tab_overlay_and_pages_are_content_sized():
    repository_root = Path(__file__).resolve().parents[2]
    source = (
        repository_root
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "shared_room"
        / "settings_panel.py"
    ).read_text(encoding="utf-8")

    assert "with ui.ZStack(height=0):" in source
    expected = (
        "visible=index == self._active_tab_index,\n"
        "                        height=0,"
    )
    assert expected in source


def test_selection_button_distinguishes_inactive_and_active_backgrounds():
    calls = []

    class Ui:
        @staticmethod
        def Button(text, **options):
            calls.append((text, options))
            return object()

    selection_button(
        Ui,
        "Interior Atlases",
        selected=True,
        clicked=lambda: None,
    )

    assert calls[0][1]["selected"] is True
    assert calls[0][1]["style"] is SELECTION_BUTTON_STYLE
    assert (
        SELECTION_BUTTON_STYLE["Button"]["background_color"]
        != SELECTION_BUTTON_STYLE["Button:selected"]["background_color"]
    )
