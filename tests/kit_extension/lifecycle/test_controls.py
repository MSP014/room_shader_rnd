"""Protect the visible lifecycle command and status contract."""

from msp.orms.runtime.lifecycle import RuntimeState
from msp.orms.runtime.ui.lifecycle_controls import (
    LIFECYCLE_ACTION_HELP,
    LIFECYCLE_ACTION_LABELS,
    enabled_lifecycle_actions,
)


def test_classifier_tab_exposes_the_complete_lifecycle_command_set():
    assert LIFECYCLE_ACTION_LABELS == (
        ("start", "Start"),
        ("restart", "Restart"),
        ("stop", "Stop"),
        ("restore", "Restore Original Asset"),
    )
    assert "Start activates ORMS" in LIFECYCLE_ACTION_HELP["start"]
    assert "Stop freezes" in LIFECYCLE_ACTION_HELP["stop"]
    assert "Restart removes and rebuilds" in LIFECYCLE_ACTION_HELP["restart"]
    assert "Restore Original Asset removes" in LIFECYCLE_ACTION_HELP["restore"]


def test_lifecycle_actions_follow_the_visible_state():
    assert enabled_lifecycle_actions(RuntimeState.INACTIVE) == {"start"}
    assert enabled_lifecycle_actions(RuntimeState.RUNNING) == {
        "restart",
        "stop",
        "restore",
    }
    assert enabled_lifecycle_actions(RuntimeState.STOPPED) == {
        "start",
        "restart",
        "restore",
    }
    assert enabled_lifecycle_actions(RuntimeState.FAILED) == {
        "start",
        "restart",
        "restore",
    }
