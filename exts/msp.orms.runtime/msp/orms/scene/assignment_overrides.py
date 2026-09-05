# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Own source-safe per-mesh automatic-assignment overrides."""

from __future__ import annotations

from pxr import Sdf, Usd

AUTO_ASSIGN_ATTRIBUTE = "orms:autoAssign"
_OVERRIDE_LAYER_NAME = "orms_auto_assignment_overrides.usda"


class AssignmentOverrideOwner:
    """Author explicit allow/exclude choices in one anonymous Session layer."""

    def __init__(self, stage: Usd.Stage) -> None:
        self._stage = stage
        self._layer = Sdf.Layer.CreateAnonymous(_OVERRIDE_LAYER_NAME)
        self._values: dict[str, bool] = {}
        self._attached = False

    @property
    def values(self) -> tuple[tuple[str, bool], ...]:
        """Return only choices authored by this owner."""

        return tuple(sorted(self._values.items()))

    def value_for(self, prim_path: str) -> bool | None:
        """Return the owned choice or None when source policy is authoritative."""

        return self._values.get(prim_path)

    def set_override(self, prim_path: str, allowed: bool | None) -> None:
        """Set an allow/exclude opinion or reveal the source policy again."""

        path = Sdf.Path(prim_path)
        if not path.IsAbsolutePath() or not path.IsPrimPath():
            raise ValueError(f"Invalid assignment prim path: {prim_path!r}")
        prim = self._stage.GetPrimAtPath(path)
        if not prim:
            raise ValueError(f"Assignment prim does not exist: {prim_path}")

        if allowed is None:
            if prim_path not in self._values:
                return
            with Usd.EditContext(self._stage, self._layer):
                prim.RemoveProperty(AUTO_ASSIGN_ATTRIBUTE)
            self._values.pop(prim_path, None)
            if not self._values:
                self._detach()
            return

        self._attach()
        with Usd.EditContext(self._stage, self._layer):
            prim.CreateAttribute(
                AUTO_ASSIGN_ATTRIBUTE,
                Sdf.ValueTypeNames.Bool,
            ).Set(bool(allowed))
        self._values[prim_path] = bool(allowed)

    def _attach(self) -> None:
        if self._attached:
            return
        session_layer = self._stage.GetSessionLayer()
        sublayers = list(session_layer.subLayerPaths)
        sublayers.insert(0, self._layer.identifier)
        session_layer.subLayerPaths = sublayers
        self._attached = True

    def _detach(self) -> None:
        if not self._attached:
            return
        session_layer = self._stage.GetSessionLayer()
        session_layer.subLayerPaths = [
            identifier
            for identifier in session_layer.subLayerPaths
            if identifier != self._layer.identifier
        ]
        self._attached = False

    def stop(self) -> None:
        """Remove the complete owned override layer and release local state."""

        self._detach()
        self._values.clear()
