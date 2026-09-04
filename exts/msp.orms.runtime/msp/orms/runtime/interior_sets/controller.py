"""Coordinate staged Interior Set edits, persistence, and runtime Apply."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

from msp.orms.interior_sets.atlas_mode import (
    ATLAS_MODE_DEBUG,
    normalise_atlas_mode,
)
from msp.orms.interior_sets.contracts import (
    InteriorSetCollection,
    InteriorSetTransaction,
)
from msp.orms.interior_sets.runtime_resources import (
    InteriorSetRuntimeSnapshot,
)
from msp.orms.interior_sets.selectors import (
    validate_collection_selectors,
)

from ..resources import (
    DebugAtlasDecision,
    ResourceLayout,
    resolve_debug_atlases,
)
from .material_values import (
    material_defaults_for_group,
    normalise_material_changes,
)
from .repository import (
    InteriorSetSettingsRepository,
    MigrationResult,
)
from .resources import (
    InteriorSetResourceSnapshot,
    build_runtime_resource_snapshot,
    resolve_interior_set_resources,
)
from .storage import normalise_collection
from .transaction import (
    InteriorSetApplyResult,
    InteriorSetRollbackError,
)

RuntimeApply = Callable[
    [InteriorSetCollection, InteriorSetRuntimeSnapshot],
    object,
]
MaterialApply = Callable[[str, Mapping[str, object]], int]


class InteriorSetController:
    """Own the draft/applied boundary outside UI and USD implementation."""

    def __init__(
        self,
        resources: ResourceLayout,
        repository: InteriorSetSettingsRepository,
    ) -> None:
        migration = repository.ensure_migrated()
        self._resources = resources
        self._repository = repository
        self._migration = migration
        self._transaction = InteriorSetTransaction.from_applied(
            migration.collection,
            migration.atlas_mode,
            migration.debug_atlas_directories,
        )
        self._last_apply_status = "loaded"
        self._last_material_update_counts: dict[str, int] = {}

    @classmethod
    def from_kit(cls, resources: ResourceLayout) -> "InteriorSetController":
        """Load or migrate the persistent applied configuration."""

        return cls(resources, InteriorSetSettingsRepository.from_kit())

    @property
    def applied(self) -> InteriorSetCollection:
        """Return the immutable configuration used by the current runtime."""

        return self._transaction.applied

    @property
    def draft(self) -> InteriorSetCollection:
        """Return the local structural candidate shown by the UI."""

        return self._transaction.draft

    @property
    def dirty(self) -> bool:
        """Return whether structural edits await explicit Apply."""

        return self._transaction.dirty

    @property
    def applied_atlas_mode(self) -> str:
        """Return the global atlas policy used by the current runtime."""

        return self._transaction.applied_atlas_mode

    @property
    def draft_atlas_mode(self) -> str:
        """Return the staged global atlas policy shown by the UI."""

        return self._transaction.draft_atlas_mode

    @property
    def applied_debug_atlas_directories(
        self,
    ) -> tuple[str, str, str, str]:
        """Return committed global debug-family override directories."""

        return self._transaction.applied_debug_atlas_directories

    @property
    def draft_debug_atlas_directories(
        self,
    ) -> tuple[str, str, str, str]:
        """Return staged global debug-family override directories."""

        return self._transaction.draft_debug_atlas_directories

    @property
    def applied_revision(self) -> int:
        """Return the structural revision currently owned by runtime."""

        return self._transaction.applied_revision

    @property
    def draft_revision(self) -> int:
        """Return the latest locally edited structural revision."""

        return self._transaction.draft_revision

    @property
    def last_apply_status(self) -> str:
        """Return the last structural transaction outcome."""

        return self._last_apply_status

    @property
    def migration_result(self) -> MigrationResult:
        """Return the immutable startup migration result."""

        return self._migration

    @property
    def material_update_counts(self) -> tuple[tuple[str, int], ...]:
        """Return the last targeted runtime update count for each Set."""

        return tuple(sorted(self._last_material_update_counts.items()))

    def runtime_snapshot(
        self,
        collection: InteriorSetCollection | None = None,
        atlas_mode: str | None = None,
        debug_atlas_directories: tuple[str, str, str, str] | None = None,
    ) -> InteriorSetRuntimeSnapshot:
        """Resolve per-Set atlas choices without mutating settings or USD."""

        return build_runtime_resource_snapshot(
            self._resources,
            collection or self.applied,
            atlas_mode or self.applied_atlas_mode,
            (
                debug_atlas_directories
                if debug_atlas_directories is not None
                else self.applied_debug_atlas_directories
            ),
        )

    def resource_decisions(
        self,
    ) -> tuple[InteriorSetResourceSnapshot, ...]:
        """Return draft resource diagnostics without applying them."""

        return resolve_interior_set_resources(
            self._resources,
            self.draft,
            self.draft_atlas_mode,
            self.draft_debug_atlas_directories,
        )

    def debug_atlas_decisions(self) -> tuple[DebugAtlasDecision, ...]:
        """Return staged global debug-resource diagnostics."""

        return resolve_debug_atlases(
            self._resources,
            self.draft_debug_atlas_directories,
        )

    def debug_atlas_display_directory(self, room_size: int) -> str:
        """Return a staged override or its effective packaged directory."""

        if room_size not in range(1, 5):
            raise ValueError(f"Unsupported ORMS room size: x{room_size}")
        configured = self.draft_debug_atlas_directories[room_size - 1]
        if configured:
            return configured
        packaged = self._resources.debug_atlas(room_size)
        return packaged.asset_path.parent.as_posix() if packaged else ""

    def stage_atlas_mode(self, atlas_mode: str) -> str:
        """Stage Debug or Production selection without rebuilding runtime."""

        mode = normalise_atlas_mode(atlas_mode)
        self._transaction.stage_atlas_mode(mode)
        return mode

    def stage_debug_atlas_directory(
        self,
        room_size: int,
        directory: str,
    ) -> tuple[str, str, str, str]:
        """Stage one global debug-family override without rebuilding USD."""

        if room_size not in range(1, 5):
            raise ValueError(f"Unsupported ORMS room size: x{room_size}")
        directories = list(self.draft_debug_atlas_directories)
        directories[room_size - 1] = str(directory)
        self._transaction.stage_debug_atlas_directories(tuple(directories))
        return self.draft_debug_atlas_directories

    def clear_debug_atlas_directory(
        self,
        room_size: int,
    ) -> tuple[str, str, str, str]:
        """Clear one override so the extension-owned default is restored."""

        return self.stage_debug_atlas_directory(room_size, "")

    def stage_profile(
        self,
        collection: InteriorSetCollection,
        atlas_mode: str,
    ) -> InteriorSetCollection:
        """Load one validated portable profile into draft state only."""

        candidate = normalise_collection(collection)
        validate_collection_selectors(candidate)
        mode = normalise_atlas_mode(atlas_mode)
        self._transaction.stage_snapshot(candidate, mode)
        self._last_apply_status = "profile_staged"
        return self.draft

    def add(self, *, set_id: str | None = None) -> InteriorSetCollection:
        """Stage a blank Set inheriting the current Default material profile."""

        self._transaction.stage(self.draft.add(set_id=set_id))
        return self.draft

    def duplicate(
        self,
        source_id: str,
        *,
        set_id: str | None = None,
    ) -> InteriorSetCollection:
        """Stage an editable copy with a fresh runtime identity."""

        self._transaction.stage(self.draft.duplicate(source_id, set_id=set_id))
        return self.draft

    def remove(self, set_id: str) -> InteriorSetCollection:
        """Stage removal while leaving applied state and USD untouched."""

        self._transaction.stage(self.draft.remove(set_id))
        return self.draft

    def move(self, set_id: str, offset: int) -> InteriorSetCollection:
        """Stage one deterministic selector-priority change."""

        self._transaction.stage(self.draft.move(set_id, offset))
        return self.draft

    def stage_selectors(
        self,
        set_id: str,
        selectors: tuple[str, ...],
    ) -> InteriorSetCollection:
        """Keep partial selector text in the draft only."""

        item = self.draft.by_id(set_id)
        self._transaction.stage(
            self.draft.replace(replace(item, selectors=selectors))
        )
        return self.draft

    def stage_atlas_directories(
        self,
        set_id: str,
        directories: tuple[str, str, str, str],
    ) -> InteriorSetCollection:
        """Keep x1-x4 production paths in the draft only."""

        item = self.draft.by_id(set_id)
        self._transaction.stage(
            self.draft.replace(replace(item, atlas_directories=directories))
        )
        return self.draft

    def clear_atlas_family(
        self,
        set_id: str,
        room_size: int,
    ) -> InteriorSetCollection:
        """Stage removal of one production family so debug fallback applies."""

        if room_size not in range(1, 5):
            raise ValueError(f"Unsupported ORMS room size: x{room_size}")
        directories = list(self.draft.by_id(set_id).atlas_directories)
        directories[room_size - 1] = ""
        return self.stage_atlas_directories(set_id, tuple(directories))

    def clear_atlas_directories(
        self,
        set_id: str,
    ) -> InteriorSetCollection:
        """Stage removal of every production family for one Set."""

        return self.stage_atlas_directories(set_id, ("", "", "", ""))

    def reset_atlas_configuration(self) -> InteriorSetCollection:
        """Stage factory atlas policy for every Set as one transaction edit."""

        collection = self.draft
        for item in collection.sets:
            collection = collection.replace(
                replace(item, atlas_directories=("", "", "", ""))
            )
        self._transaction.stage_snapshot(
            collection,
            ATLAS_MODE_DEBUG,
            ("", "", "", ""),
        )
        return self.draft

    def rename(
        self,
        set_id: str,
        name: str,
    ) -> InteriorSetCollection:
        """Apply existing-Set names live and keep new-Set names staged."""

        try:
            self.applied.by_id(set_id)
        except KeyError:
            item = self.draft.by_id(set_id)
            self._transaction.stage(self.draft.replace(item.renamed(name)))
            return self.draft

        applied = self._repository.rename(set_id, name)
        self._transaction.applied = applied
        try:
            draft_item = self.draft.by_id(set_id)
        except KeyError:
            return self.draft
        self._transaction.draft = self.draft.replace(draft_item.renamed(name))
        return self.draft

    def update_material(
        self,
        set_id: str,
        name: str,
        value: object,
        apply_runtime: MaterialApply | None = None,
    ) -> int:
        """Apply existing-Set materials live; keep new Sets in the draft."""

        return self.update_materials(
            set_id,
            {name: value},
            apply_runtime,
        )

    def update_materials(
        self,
        set_id: str,
        changed_values: Mapping[str, object],
        apply_runtime: MaterialApply | None = None,
    ) -> int:
        """Apply one live editing gesture to one existing Set."""

        changed_values = normalise_material_changes(changed_values)
        try:
            self.applied.by_id(set_id)
        except KeyError:
            item = self.draft.by_id(set_id)
            values = item.material_mapping()
            values.update(changed_values)
            self._transaction.stage(
                self.draft.replace(
                    replace(item, material_values=tuple(values.items()))
                )
            )
            return 0

        applied = self._repository.update_materials(
            set_id,
            changed_values,
        )
        self._transaction.applied = applied
        draft_item = self.draft.by_id(set_id)
        values = draft_item.material_mapping()
        values.update(changed_values)
        self._transaction.draft = self.draft.replace(
            replace(draft_item, material_values=tuple(values.items()))
        )
        updated_count = (
            apply_runtime(set_id, changed_values) if apply_runtime else 0
        )
        self._last_material_update_counts[set_id] = updated_count
        return updated_count

    def reset_materials(
        self,
        set_id: str,
        group: str | None = None,
        apply_runtime: MaterialApply | None = None,
    ) -> int:
        """Reset one group or the complete Set profile to factory defaults."""

        return self.update_materials(
            set_id,
            material_defaults_for_group(group),
            apply_runtime,
        )

    def apply(
        self,
        apply_runtime: RuntimeApply | None = None,
    ) -> InteriorSetApplyResult:
        """Commit one validated draft and request one runtime rebuild."""

        if not self.dirty:
            self._last_apply_status = "no_changes"
            return InteriorSetApplyResult(
                collection=self.applied,
                rebuild_requested=False,
                applied_revision=self.applied_revision,
                draft_revision=self.draft_revision,
                status=self._last_apply_status,
            )
        try:
            validate_collection_selectors(self.draft)
            decisions = self.resource_decisions()
        except Exception:
            self._last_apply_status = "validation_failed"
            raise
        runtime_snapshot = build_runtime_resource_snapshot(
            self._resources,
            self.draft,
            self.draft_atlas_mode,
            self.draft_debug_atlas_directories,
            decisions,
        )
        try:
            commit = self._repository.commit(
                self.draft,
                self.draft_atlas_mode,
                self.draft_debug_atlas_directories,
            )
        except Exception:
            self._last_apply_status = "persistence_failed"
            raise
        try:
            if apply_runtime is not None:
                apply_runtime(commit.collection, runtime_snapshot)
        except Exception as runtime_error:
            try:
                self._repository.rollback(commit)
            except Exception as rollback_error:
                self._last_apply_status = "rollback_failed"
                raise InteriorSetRollbackError(
                    runtime_error,
                    rollback_error,
                ) from runtime_error
            self._last_apply_status = "rolled_back"
            raise
        self._transaction.draft = commit.collection
        self._transaction.accept()
        self._last_apply_status = "applied"
        return InteriorSetApplyResult(
            collection=self.applied,
            rebuild_requested=apply_runtime is not None,
            applied_revision=self.applied_revision,
            draft_revision=self.draft_revision,
            status=self._last_apply_status,
        )

    def revert(self) -> InteriorSetCollection:
        """Discard every unapplied structural edit."""

        collection = self._transaction.revert()
        self._last_apply_status = "reverted"
        return collection
