# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Coordinate assignment inspection, overrides, and reversible bindings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AssignmentItem:
    """Describe one recognised mesh and its current automatic-assignment state."""

    prim_path: str
    source_material_path: str
    eligible: bool
    assigned: bool
    reason: str
    override: bool | None
    override_editable: bool = True


@dataclass(frozen=True)
class AssignmentSnapshot:
    """Present the recognised meshes owned by one active stage session."""

    items: tuple[AssignmentItem, ...] = ()
    editable: bool = False


class AssignmentSession:
    """Keep per-stage overrides while automatic bindings are rebuilt."""

    def __init__(self, stage: Any) -> None:
        from msp.orms.scene.assignment_overrides import (
            AssignmentOverrideOwner,
        )

        self._stage = stage
        self._overrides = AssignmentOverrideOwner(stage)
        self._assignment_owner: Any | None = None
        self._result: Any | None = None

    def owns_stage(self, stage: Any) -> bool:
        """Return whether the session belongs to the supplied stage object."""

        return self._stage is stage

    @property
    def runtime_layer(self) -> Any | None:
        """Expose the attached assignment layer for pre-classifier inputs."""

        if self._assignment_owner is None:
            return None
        return self._assignment_owner.runtime_layer

    def apply(
        self,
        *,
        source_asset_path: str,
        atlas_asset_path: str,
        atlas_variant_count: int,
        instance_source_asset_path: str | None = None,
        material_input_values: Mapping[str, object] | None = None,
        candidate_selectors: tuple[str, ...] | None = None,
    ) -> Any:
        """Re-evaluate recognised meshes and replace automatic bindings."""

        from msp.orms.scene.assignment import AutoAssignmentOwner

        self.stop_assignments()
        owner = AutoAssignmentOwner(
            self._stage,
            source_asset_path=source_asset_path,
            instance_source_asset_path=instance_source_asset_path,
            atlas_asset_path=atlas_asset_path,
            atlas_variant_count=atlas_variant_count,
            material_input_values=material_input_values,
            candidate_selectors=candidate_selectors,
        )
        self._result = owner.apply()
        self._assignment_owner = owner
        return self._result

    def set_material_input_values(
        self,
        values: Mapping[str, object],
    ) -> int:
        """Update live auto-assignment materials when they exist."""

        if self._assignment_owner is None:
            return 0
        return self._assignment_owner.set_material_input_values(values)

    def inspect(self) -> AssignmentSnapshot:
        """Return the last pre-binding decisions with owned override state."""

        if self._result is None:
            from msp.orms.scene.assignment import (
                evaluate_windows_glass,
            )

            decisions = evaluate_windows_glass(self._stage)
            assigned_paths: frozenset[str] = frozenset()
        else:
            decisions = self._result.decisions
            assigned_paths = frozenset(self._result.assigned_prim_paths)
        return AssignmentSnapshot(
            tuple(
                AssignmentItem(
                    prim_path=decision.prim_path,
                    source_material_path=decision.source_material_path,
                    eligible=decision.eligible,
                    assigned=decision.prim_path in assigned_paths,
                    reason=decision.reason,
                    override=self._overrides.value_for(decision.prim_path),
                    override_editable=decision.override_editable,
                )
                for decision in decisions
            ),
            editable=True,
        )

    def set_override(self, prim_path: str, allowed: bool | None) -> None:
        """Author one Session-layer choice for a recognised mesh."""

        recognised = {item.prim_path for item in self.inspect().items}
        if prim_path not in recognised:
            raise ValueError(f"Mesh is not recognised by ORMS: {prim_path}")
        self._overrides.set_override(prim_path, allowed)

    def stop_assignments(self) -> None:
        """Remove automatic bindings while retaining explicit overrides."""

        owner, self._assignment_owner = self._assignment_owner, None
        if owner is not None:
            owner.stop()
        self._result = None

    def stop(self) -> None:
        """Remove both automatic bindings and every owned override opinion."""

        self.stop_assignments()
        self._overrides.stop()
