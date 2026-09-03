"""Carry validated per-Set resources into the USD runtime."""

from __future__ import annotations

from dataclasses import dataclass

from ..runtime.resources import RuntimeResources


@dataclass(frozen=True)
class InteriorSetRuntimeResources:
    """Pair one immutable Set identity with its selected atlas families."""

    set_id: str
    resources: RuntimeResources
    variant_coherent: bool = True
    coherence_error: str | None = None
    variant_namespace: str | None = None
    variant_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class InteriorSetRuntimeSnapshot:
    """Hold ordered resource decisions for one applied configuration."""

    sets: tuple[InteriorSetRuntimeResources, ...]

    def __post_init__(self) -> None:
        identifiers = tuple(item.set_id for item in self.sets)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Runtime Interior Set identities must be unique")

    def by_id(self, set_id: str) -> InteriorSetRuntimeResources:
        """Return resources for one stable Set identity."""

        for item in self.sets:
            if item.set_id == set_id:
                return item
        raise KeyError(f"No runtime resources for Interior Set {set_id}")

    @property
    def available_room_sizes_by_set(
        self,
    ) -> dict[str, frozenset[int]]:
        """Return classifier-ready family availability per Set."""

        return {
            item.set_id: item.resources.available_room_sizes
            for item in self.sets
        }

    @property
    def incoherent_set_ids(self) -> frozenset[str]:
        """Return Sets that must not form cross-family corner rooms."""

        return frozenset(
            item.set_id for item in self.sets if not item.variant_coherent
        )
