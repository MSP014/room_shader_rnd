"""Protect the visible lifecycle command and status contract."""

from msp.orms.runtime.lifecycle import RuntimeState
from msp.orms.runtime.lifecycle_controls import (
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
