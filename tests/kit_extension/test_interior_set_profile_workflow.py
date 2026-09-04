"""Protect direct profile actions from prerequisite path state."""

from msp.orms.runtime.profiles.workflow import (
    InteriorSetProfileWorkflow,
)
from msp.orms.runtime.ui.panel_state import InteriorSetPanelState


def test_save_and_load_open_their_dialogs_without_a_preselected_path():
    calls = []

    class Picker:
        def choose_save_path(self, current_path, _changed):
            calls.append(("save", current_path))

        def choose_existing(self, current_path, _changed):
            calls.append(("load", current_path))

    state = InteriorSetPanelState()
    workflow = InteriorSetProfileWorkflow(
        state,
        lambda: None,
        lambda: None,
    )
    workflow._picker = Picker()

    workflow.save()
    workflow.load()

    assert calls == [("save", ""), ("load", "")]
