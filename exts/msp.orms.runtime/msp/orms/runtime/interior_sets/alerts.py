"""Format actionable Interior Set warnings for the artist-facing panel."""

from __future__ import annotations

from msp.orms.shared_room.interior_set_diagnostics import (
    InteriorSetDiagnostics,
)

from .controller import InteriorSetController


def selector_conflict_alerts(
    controller: InteriorSetController,
    diagnostics: InteriorSetDiagnostics | None,
) -> tuple[str, ...]:
    """Keep selector ownership conflicts visible without a diagnostics view."""

    if diagnostics is None or not diagnostics.conflicts:
        return ()

    lines = [
        "Applied selector conflict(s): "
        f"{len(diagnostics.conflicts)}. First matching Set wins by "
        "top-to-bottom priority."
    ]
    for conflict in diagnostics.conflicts[:3]:
        matching = ", ".join(
            controller.applied.label_for(set_id)
            for set_id in conflict.matching_set_ids
        )
        winner = controller.applied.label_for(conflict.winning_set_id)
        lines.append(
            f"{conflict.prim_path} matched {matching}; {winner} owns it."
        )
    hidden = len(diagnostics.conflicts) - 3
    if hidden > 0:
        lines.append(f"{hidden} more conflict(s); see the ORMS log.")
    return tuple(lines)
