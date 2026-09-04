"""Protect concise selector-conflict warnings outside diagnostics UI."""

from msp.orms.runtime.interior_sets.alerts import selector_conflict_alerts
from msp.orms.runtime.interior_sets.controller import InteriorSetController
from msp.orms.shared_room.interior_set_diagnostics import (
    InteriorSetDiagnostics,
    SelectorConflict,
)

from .test_interior_set_controller import (
    KITCHENS_ID,
    SHOPS_ID,
    _controller,
)


def test_selector_conflict_remains_visible_without_a_diagnostics_section():
    controller: InteriorSetController = _controller()
    controller.add(set_id=KITCHENS_ID)
    controller.rename(KITCHENS_ID, "Living Rooms")
    controller.add(set_id=SHOPS_ID)
    controller.rename(SHOPS_ID, "Cabinets")
    controller.apply()
    diagnostics = InteriorSetDiagnostics(
        active_set_count=3,
        aperture_counts=((KITCHENS_ID, 24),),
        room_size_counts=((KITCHENS_ID, 1, 24),),
        selector_match_counts=(),
        default_fallback_paths=(),
        conflicts=(
            SelectorConflict(
                prim_path="/Building/windows/cabinets",
                winning_set_id=KITCHENS_ID,
                matching_set_ids=(KITCHENS_ID, SHOPS_ID),
            ),
        ),
        atlas_families=(),
        coherence=(),
    )

    lines = selector_conflict_alerts(controller, diagnostics)

    assert lines[0].startswith("Applied selector conflict(s): 1")
    assert lines[1] == (
        "/Building/windows/cabinets matched Living Rooms, Cabinets; "
        "Living Rooms owns it."
    )
