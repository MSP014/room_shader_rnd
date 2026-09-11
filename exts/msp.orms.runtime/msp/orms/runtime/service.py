# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Coordinate ORMS resources, assignment, and runtime lifecycle inside Kit."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from msp.orms.interior_sets.contracts import (
    DEFAULT_INTERIOR_SET_ID,
    InteriorSetCollection,
)
from msp.orms.interior_sets.runtime_resources import (
    InteriorSetRuntimeSnapshot,
)
from msp.orms.scene.status_log import (
    log_room_map_error,
    log_room_map_warning,
)
from msp.orms.shared_room.interior_set_diagnostics import (
    InteriorSetDiagnostics,
)

from .assignments.session import AssignmentSession, AssignmentSnapshot
from .demo_scene import open_demo_scene as open_demo_scene_content
from .diagnostic_capture import enable_complete_diagnostics
from .interior_sets.controller import InteriorSetController
from .interior_sets.repository import InteriorSetSettingsRepository
from .interior_sets.transaction import InteriorSetRollbackError
from .lifecycle import RuntimeLifecycleController, RuntimeState
from .materials.library import MaterialLibraryRegistration
from .phase5_audit import Phase5RuntimeAudit
from .resources import (
    DEBUG_ASSET_SETTING,
    MATERIAL_SOURCE_ASSET,
    PRESERVED_INSTANCE_MATERIAL_SOURCE_ASSET,
    PRODUCTION_DIRECTORY_SETTING,
    ResourceLayout,
)

_SETTINGS_ROOT = "/persistent/exts/msp.orms.runtime"
_AUTO_ASSIGN_SETTING = f"{_SETTINGS_ROOT}/autoAssignWindowsGlass"
_VERBOSE_DIAGNOSTICS_SETTING = f"{_SETTINGS_ROOT}/verboseDiagnostics"
_RENDERER_RELEASE_UPDATE_COUNT = 2


def _verbose_diagnostics_enabled(settings: Any | None = None) -> bool:
    """Return whether the opt-in research trace should run and emit logs."""

    if settings is None:
        import carb.settings

        settings = carb.settings.get_settings()
    return bool(settings.get(_VERBOSE_DIAGNOSTICS_SETTING))


def _log_verbose_info(message: str) -> None:
    """Keep routine lifecycle chatter behind the diagnostics switch."""

    if not _verbose_diagnostics_enabled():
        return
    import carb

    carb.log_info(message)


def _assignment_selectors(
    collection: InteriorSetCollection,
) -> tuple[str, ...]:
    """Flatten configured mesh selectors without changing Set priority."""

    return tuple(
        dict.fromkeys(
            mask
            for item in collection.sets
            for mask in item.selectors
            if mask.strip()
        )
    )


def _kit_settings() -> Any:
    """Return the process-wide Kit settings interface at the API boundary."""

    import carb.settings

    return carb.settings.get_settings()


async def _next_kit_update() -> None:
    """Yield until Kit has completed another application update."""

    import omni.kit.app

    await omni.kit.app.get_app().next_update_async()


class OrmsRuntimeService:
    """Own all callbacks and ephemeral USD layers created by the extension."""

    def __init__(
        self,
        *,
        extension_name: str,
        resources: ResourceLayout,
    ) -> None:
        self._extension_name = extension_name
        self._resources = resources
        self._material_registration = MaterialLibraryRegistration()
        self._stage_subscriptions: tuple[Any, ...] = ()
        self._assignment_session: AssignmentSession | None = None
        self._lifecycle = RuntimeLifecycleController(
            state_changed=self._on_lifecycle_state_changed,
        )
        self._settings_window: Any | None = None
        self._interior_sets: InteriorSetController | None = None
        self._demo_open_task: asyncio.Task[None] | None = None
        self._runtime_reactivation_task: asyncio.Task[None] | None = None
        self._runtime_reactivation_revision = 0
        self._phase5_audit: Phase5RuntimeAudit | None = None

    @classmethod
    def discover(
        cls,
        ext_id: str,
        module_file: str | Path,
    ) -> "OrmsRuntimeService":
        """Resolve the installed extension name and relocatable resources."""

        import omni.ext

        return cls(
            extension_name=omni.ext.get_extension_name(ext_id),
            resources=ResourceLayout.discover(module_file),
        )

    def start(self) -> None:
        """Register ORMS and activate it for the current and future stages."""

        import carb
        import carb.eventdispatcher
        import omni.usd

        try:
            self._material_registration.start(
                self._extension_name,
                self._resources,
            )
            settings = carb.settings.get_settings()
            settings.set_default(_AUTO_ASSIGN_SETTING, True)
            import carb.logging

            source_names = enable_complete_diagnostics(
                settings,
                orms_verbose_setting=_VERBOSE_DIAGNOSTICS_SETTING,
                verbose_level=carb.logging.LEVEL_VERBOSE,
            )
            carb.logging.acquire_logging().set_level_threshold(
                carb.logging.LEVEL_VERBOSE
            )
            carb.log_info(
                "[ORMS] Complete diagnostics enabled: "
                "USD diagnostics unmuted, ORMS trace enabled, "
                f"Console sources enabled={len(source_names)}"
            )
            for room_size in (1, 2, 3, 4):
                debug_atlas = self._resources.debug_atlas(room_size)
                settings.set(
                    DEBUG_ASSET_SETTING.format(room_size=room_size),
                    (
                        debug_atlas.asset_path.as_posix()
                        if debug_atlas is not None
                        else ""
                    ),
                )
                settings.set_default(
                    PRODUCTION_DIRECTORY_SETTING.format(room_size=room_size),
                    "",
                )
            self._interior_sets = InteriorSetController(
                self._resources,
                InteriorSetSettingsRepository(settings),
            )

            from .ui.settings_window import OrmsSettingsWindow

            self._settings_window = OrmsSettingsWindow()
            self._settings_window.start(
                classifier_changed=self._apply_classifier_settings,
                assignment_changed=self._set_auto_assignment_override,
                assignment_snapshot=self._current_assignment_snapshot,
                material_changed=self._apply_interior_set_material,
                material_reset=self._reset_interior_set_materials,
                apply_interior_sets=self._apply_interior_sets,
                rename_interior_set=self._rename_interior_set,
                interior_sets=self._interior_sets,
                runtime_diagnostics=(self._current_interior_set_diagnostics),
                start_runtime=self.start_runtime,
                restart_runtime=self.restart_runtime,
                stop_runtime=self.stop_runtime,
                restore_asset=self.restore_original_asset,
                open_demo_scene=self.open_demo_scene,
                demo_scene_available=(
                    self._resources.demo_stage is not None
                    and self._resources.demo_profile is not None
                ),
            )
            self._settings_window.set_lifecycle_state(self._lifecycle.state)

            context = omni.usd.get_context()
            dispatcher = carb.eventdispatcher.get_eventdispatcher()
            self._stage_subscriptions = tuple(
                dispatcher.observe_event(
                    event_name=context.stage_event_name(event_type),
                    on_event=self._on_stage_event,
                    observer_name=f"msp.orms.runtime.{event_label.lower()}",
                )
                for event_label, event_type in (
                    ("OPENED", omni.usd.StageEventType.OPENED),
                    ("CLOSING", omni.usd.StageEventType.CLOSING),
                    ("CLOSED", omni.usd.StageEventType.CLOSED),
                )
            )
            if context.get_stage() is not None:
                self._activate_current_stage()
        except Exception:
            self.stop()
            raise
        carb.log_info("[ORMS] Runtime extension started")

    def open_demo_scene(self) -> None:
        """Prompt for unsaved work before scheduling the bundled demo."""

        if (
            self._resources.demo_stage is None
            or self._resources.demo_profile is None
        ):
            self._set_demo_scene_status(
                "Demo content is unavailable in this ORMS installation."
            )
            return
        if self._demo_open_task is not None:
            self._set_demo_scene_status("The demo scene is already opening.")
            return

        import omni.kit.window.file

        omni.kit.window.file.prompt_if_unsaved_stage(
            self._schedule_demo_scene_open
        )

    def _schedule_demo_scene_open(self) -> None:
        """Capture onboarding eligibility only after the save prompt clears."""

        controller = self._interior_sets
        if controller is None or self._demo_open_task is not None:
            return
        auto_apply_profile = controller.is_factory_configuration
        self._set_demo_scene_status("Opening the ORMS demo scene...")
        self._demo_open_task = asyncio.ensure_future(
            self._run_demo_scene_open(auto_apply_profile)
        )

    async def _run_demo_scene_open(self, auto_apply_profile: bool) -> None:
        stage_path = self._resources.demo_stage
        profile_path = self._resources.demo_profile
        controller = self._interior_sets
        try:
            if (
                stage_path is None
                or profile_path is None
                or controller is None
            ):
                raise RuntimeError("ORMS demo resources are unavailable")
            status = await open_demo_scene_content(
                stage_path,
                profile_path,
                controller,
                self._apply_interior_sets,
                self._open_stage_async,
                auto_apply_profile=auto_apply_profile,
            )
            self._set_demo_scene_status(status)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._set_demo_scene_status(f"Demo scene failed: {error}")
            log_room_map_error(
                owner="DEMO SCENE",
                process="OPEN",
                state="FAILED",
                details={"error": repr(error)},
            )
        finally:
            if self._demo_open_task is asyncio.current_task():
                self._demo_open_task = None

    @staticmethod
    async def _open_stage_async(stage_path: str) -> object:
        """Open one stage through Kit without blocking its main thread."""

        import omni.usd

        return await omni.usd.get_context().open_stage_async(stage_path)

    def _set_demo_scene_status(self, status: str) -> None:
        if self._settings_window is not None:
            self._settings_window.set_demo_scene_status(status)

    def _on_stage_event(self, event: object) -> None:
        import omni.usd

        event_name = getattr(event, "event_name", "")
        if not event_name:
            return
        event_type = int(omni.usd.stage_event_type(event_name))
        opened = int(omni.usd.StageEventType.OPENED)
        closing_types = {
            int(omni.usd.StageEventType.CLOSING),
            int(omni.usd.StageEventType.CLOSED),
        }
        try:
            if event_type == opened:
                self._activate_current_stage()
            elif event_type in closing_types:
                self._deactivate_stage()
        except Exception as error:
            self._deactivate_stage()
            self._lifecycle.fail()
            log_room_map_error(
                owner="ORMS RUNTIME SERVICE",
                process="STAGE EVENT",
                state="FAILED",
                details={"error": repr(error)},
            )

    def _activate_current_stage(
        self,
        *,
        preserve_assignment_overrides: bool = False,
        audit_event: str = "STARTED",
        collection_override: InteriorSetCollection | None = None,
        runtime_snapshot_override: InteriorSetRuntimeSnapshot | None = None,
        prepared_assignment_session: AssignmentSession | None = None,
    ) -> None:
        import carb
        import carb.settings
        import omni.usd

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._deactivate_stage()
            return
        if prepared_assignment_session is None:
            assignment_session = self._prepare_assignment_session(
                stage,
                preserve_assignment_overrides,
            )
        else:
            assignment_session = prepared_assignment_session
            if (
                self._assignment_session is not assignment_session
                or not assignment_session.owns_stage(stage)
            ):
                raise RuntimeError(
                    "Prepared ORMS assignment session no longer owns the "
                    "active stage"
                )
        settings = _kit_settings()
        self._ensure_phase5_audit(stage, settings)
        has_collection_override = collection_override is not None
        has_snapshot_override = runtime_snapshot_override is not None
        if has_collection_override != has_snapshot_override:
            raise ValueError(
                "Runtime collection and resource overrides must be supplied "
                "together"
            )
        if self._interior_sets is None and not has_collection_override:
            raise RuntimeError("Interior Set configuration is unavailable")
        collection = (
            collection_override
            if collection_override is not None
            else self._interior_sets.applied
        )
        runtime_snapshot = (
            runtime_snapshot_override
            if runtime_snapshot_override is not None
            else self._interior_sets.runtime_snapshot()
        )
        default_runtime = runtime_snapshot.by_id(DEFAULT_INTERIOR_SET_ID)

        self._apply_automatic_assignments(
            assignment_session,
            collection,
            runtime_snapshot,
            settings,
        )

        from msp.orms.shared_room.stage import (
            stage_has_room_map_source_mesh,
        )

        if not stage_has_room_map_source_mesh(stage):
            if _verbose_diagnostics_enabled(settings):
                carb.log_info(
                    "[ORMS] Stage activation skipped: no mesh is bound to an "
                    "ORMS source material"
                )
            self._refresh_settings_window()
            return

        from msp.orms.runtime.reload_room_map_runtime import (
            reload_and_start,
            stop_runtime,
        )

        try:
            classifier, camera_bridge = reload_and_start(
                self._resources.extension_root,
                mdl_source_asset=MATERIAL_SOURCE_ASSET,
                atlas_families=tuple(
                    (
                        atlas.room_size,
                        atlas.asset_path,
                        atlas.variant_count,
                    )
                    for atlas in default_runtime.resources.atlas_families
                ),
                interior_sets=collection,
                interior_set_resources=runtime_snapshot,
                camera_seed_layer=assignment_session.runtime_layer,
                verbose_diagnostics=_verbose_diagnostics_enabled(settings),
            )
        except Exception:
            stop_runtime()
            raise
        self._lifecycle.attach(classifier, camera_bridge, stop_runtime)
        self._record_phase5_sample(audit_event)
        self._refresh_settings_window()

    def _prepare_assignment_session(
        self,
        stage: object,
        preserve_overrides: bool,
    ) -> AssignmentSession:
        """Reuse only current-stage overrides across a controlled rebuild."""

        session = self._assignment_session
        if (
            preserve_overrides
            and session is not None
            and session.owns_stage(stage)
        ):
            self._lifecycle.teardown()
            session.stop_assignments()
            return session
        self._deactivate_stage()
        session = AssignmentSession(stage)
        self._assignment_session = session
        return session

    def _apply_automatic_assignments(
        self,
        assignment_session: AssignmentSession,
        collection: InteriorSetCollection,
        runtime_snapshot: InteriorSetRuntimeSnapshot,
        settings: Any,
    ) -> None:
        """Apply configured mesh selectors without editing live instances."""

        if not bool(settings.get(_AUTO_ASSIGN_SETTING)):
            assignment_session.stop_assignments()
            return
        default_runtime = runtime_snapshot.by_id(DEFAULT_INTERIOR_SET_ID)
        try:
            seed_x1 = default_runtime.resources.atlas_family(1)
        except KeyError:
            seed_x1 = None
        if seed_x1 is None:
            assignment_session.stop_assignments()
            log_room_map_warning(
                owner="ORMS RUNTIME SERVICE",
                process="WINDOW MESH AUTO-ASSIGNMENT",
                state="SKIPPED",
                details={"reason": "no valid x1 atlas is available"},
            )
            return
        result = assignment_session.apply(
            source_asset_path=MATERIAL_SOURCE_ASSET,
            instance_source_asset_path=(
                self._resources.mdl_root
                / PRESERVED_INSTANCE_MATERIAL_SOURCE_ASSET
            ).as_posix(),
            atlas_asset_path=seed_x1.asset_path,
            atlas_variant_count=seed_x1.variant_count,
            material_input_values=collection.default.material_mapping(),
            candidate_selectors=_assignment_selectors(collection),
        )
        if not _verbose_diagnostics_enabled(settings):
            return
        import carb

        decision_summary = "; ".join(
            f"{decision.prim_path}:{decision.reason}"
            for decision in result.decisions
        )
        carb.log_info(
            "[ORMS] Window mesh auto-assignment: "
            f"assigned={len(result.assigned_prim_paths)}, "
            f"examined={len(result.decisions)}, "
            f"decisions={decision_summary or '<none>'}"
        )

    def _refresh_settings_window(self) -> None:
        if self._settings_window is not None:
            self._settings_window.refresh_interior_sets()

    def _current_assignment_snapshot(self) -> AssignmentSnapshot:
        """Return recognised meshes without exposing assignment ownership."""

        if self._assignment_session is None:
            return AssignmentSnapshot()
        snapshot = self._assignment_session.inspect()
        editable = self._lifecycle.state not in {
            RuntimeState.STOPPED,
            RuntimeState.FAILED,
        }
        return AssignmentSnapshot(snapshot.items, editable=editable)

    def _set_auto_assignment_override(
        self,
        prim_path: str,
        allowed: bool | None,
    ) -> None:
        """Apply one source-safe mesh override and rebuild the active stage."""

        if self._assignment_session is None:
            raise RuntimeError("No active ORMS assignment session")
        self._assignment_session.set_override(prim_path, allowed)
        self._activate_current_stage(preserve_assignment_overrides=True)

    def _current_interior_set_diagnostics(
        self,
    ) -> InteriorSetDiagnostics | None:
        """Return the last stable applied runtime diagnostic snapshot."""

        classifier = self._lifecycle.classifier
        if classifier is None or classifier.last_classification is None:
            return None
        return classifier.last_classification.interior_set_diagnostics

    def start_runtime(self) -> None:
        """Start an inactive stage or resume its frozen runtime session."""

        try:
            if self._runtime_reactivation_pending():
                return
            if self._resume_frozen_runtime("RESUMED"):
                _log_verbose_info("[ORMS] Runtime resumed")
                return
            if self._lifecycle.state is RuntimeState.RUNNING:
                return
            self._activate_current_stage(
                preserve_assignment_overrides=True,
                audit_event="STARTED",
            )
            if self._lifecycle.state is RuntimeState.RUNNING:
                _log_verbose_info("[ORMS] Runtime started by user")
        except Exception as error:
            self._handle_lifecycle_failure("Start", error)

    def restart_runtime(self) -> None:
        """Resume a stopped result, otherwise rebuild it from settings."""

        try:
            if self._runtime_reactivation_pending():
                return
            if self._resume_frozen_runtime("RESTARTED"):
                _log_verbose_info("[ORMS] Frozen runtime resumed by Restart")
                return
            self._activate_current_stage(
                preserve_assignment_overrides=True,
                audit_event="RESTARTED",
            )
            if self._lifecycle.state is RuntimeState.RUNNING:
                _log_verbose_info("[ORMS] Runtime restarted by user")
        except Exception as error:
            self._handle_lifecycle_failure("Restart", error)

    def _resume_frozen_runtime(self, audit_event: str) -> bool:
        """Resume one stopped session without recycling its renderer prims."""

        if not self._lifecycle.resume():
            return False
        self._apply_classifier_settings()
        self._apply_material_settings()
        self._record_phase5_sample(audit_event)
        return True

    def stop_runtime(self) -> None:
        """Freeze the current ORMS result while retaining UI configuration."""

        try:
            paused = self._lifecycle.stop()
            if paused:
                self._record_phase5_sample("STOPPED")
                _log_verbose_info(
                    "[ORMS] Runtime stopped with parallax frozen"
                )
        except Exception as error:
            self._handle_lifecycle_failure("Stop", error)

    def restore_original_asset(self) -> None:
        """Remove every ORMS-owned layer and reveal source asset bindings."""

        try:
            self._deactivate_stage(audit_event="RESTORED")
        except Exception as error:
            self._handle_lifecycle_failure("Restore Original Asset", error)
            return
        self._refresh_settings_window()
        _log_verbose_info("[ORMS] Original asset state restored")

    def _handle_lifecycle_failure(
        self,
        action: str,
        error: Exception,
    ) -> None:
        cleanup_error = None
        try:
            self._deactivate_stage()
        except Exception as caught_error:
            cleanup_error = caught_error
        self._lifecycle.fail()
        cleanup_suffix = (
            f"; cleanup failed: {cleanup_error!r}"
            if cleanup_error is not None
            else ""
        )
        log_room_map_error(
            owner="ORMS RUNTIME SERVICE",
            process=action.upper(),
            state="FAILED",
            details={"error": f"{error!r}{cleanup_suffix}"},
        )

    def _on_lifecycle_state_changed(self, state: RuntimeState) -> None:
        if self._settings_window is not None:
            self._settings_window.set_lifecycle_state(state)

    def _apply_classifier_settings(self) -> None:
        """Apply the central classifier controls to the active stage once."""

        if self._lifecycle.state is not RuntimeState.RUNNING:
            return
        classifier = self._lifecycle.classifier
        if classifier is None:
            return
        from msp.orms.shared_room.settings import settings_from_kit

        classifier.set_settings(settings_from_kit())

    def _apply_material_settings(self) -> None:
        """Restore every applied Set's live profile after runtime resume."""

        if self._lifecycle.state is not RuntimeState.RUNNING:
            return
        if self._interior_sets is None:
            return
        for item in self._interior_sets.applied.sets:
            self._apply_live_material_values(
                item.set_id,
                item.material_mapping(),
            )

    def _apply_live_material_values(
        self,
        set_id: str,
        values: Mapping[str, object],
    ) -> int:
        """Route one profile to classified and Preserve fallback materials."""

        updated_count = 0
        classifier = self._lifecycle.classifier
        if (
            classifier is not None
            and self._lifecycle.state is RuntimeState.RUNNING
        ):
            updated_count += classifier.set_interior_set_material_values(
                set_id,
                values,
            )
        assignment_session = self._assignment_session
        if (
            set_id == DEFAULT_INTERIOR_SET_ID
            and assignment_session is not None
        ):
            updated_count += assignment_session.set_material_input_values(
                values
            )
        return updated_count

    def _apply_interior_set_material(
        self,
        set_id: str,
        name: str,
        value: object,
    ) -> int:
        """Persist and author one Set-scoped live material edit."""

        if self._interior_sets is None:
            return 0
        apply_runtime = (
            self._apply_live_material_values
            if self._lifecycle.state is RuntimeState.RUNNING
            else None
        )
        return self._interior_sets.update_material(
            set_id,
            name,
            value,
            apply_runtime,
        )

    def _reset_interior_set_materials(
        self,
        set_id: str,
        group: str | None,
    ) -> int:
        """Restore factory values for one Set and update its live family."""

        if self._interior_sets is None:
            return 0
        apply_runtime = (
            self._apply_live_material_values
            if self._lifecycle.state is RuntimeState.RUNNING
            else None
        )
        return self._interior_sets.reset_materials(
            set_id,
            group,
            apply_runtime,
        )

    def _rename_interior_set(self, set_id: str, name: str) -> None:
        """Persist presentation and update existing material labels live."""

        if self._interior_sets is None:
            return
        try:
            self._interior_sets.applied.by_id(set_id)
        except KeyError:
            applied = False
        else:
            applied = True
        self._interior_sets.rename(set_id, name)
        classifier = self._lifecycle.classifier
        if (
            applied
            and classifier is not None
            and self._lifecycle.state is RuntimeState.RUNNING
        ):
            classifier.rename_interior_set(set_id, name)

    def _apply_interior_sets(self) -> None:
        """Commit the complete UI draft and rebuild the runtime once."""

        if self._interior_sets is None:
            return
        apply_runtime = (
            self._apply_interior_sets_to_runtime
            if (
                self._lifecycle.state is RuntimeState.RUNNING
                or self._runtime_reactivation_pending()
            )
            else None
        )
        try:
            self._interior_sets.apply(apply_runtime)
        except Exception as error:
            action = (
                "Apply Interior Sets rollback"
                if isinstance(error, InteriorSetRollbackError)
                else "Apply Interior Sets"
            )
            self._handle_lifecycle_failure(action, error)
            raise

    def _apply_interior_sets_to_runtime(
        self,
        collection: InteriorSetCollection,
        resources: InteriorSetRuntimeSnapshot,
    ) -> None:
        """Reactivate only after RTX releases the previous MDL graph."""

        prepared = self._prepare_current_stage_for_reactivation()
        if prepared is None:
            return
        stage, assignment_session = prepared
        self._schedule_runtime_reactivation(
            stage,
            assignment_session,
            collection,
            resources,
        )

    def _prepare_current_stage_for_reactivation(
        self,
    ) -> tuple[object, AssignmentSession] | None:
        """Detach renderer dependencies before replacing assignment data."""

        import omni.usd

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._deactivate_stage()
            return None
        assignment_session = self._prepare_assignment_session(stage, True)
        return stage, assignment_session

    def _schedule_runtime_reactivation(
        self,
        stage: object,
        assignment_session: AssignmentSession,
        collection: InteriorSetCollection,
        resources: InteriorSetRuntimeSnapshot,
    ) -> None:
        """Coalesce Apply requests and publish after renderer cleanup."""

        self._cancel_runtime_reactivation()
        revision = self._runtime_reactivation_revision
        self._runtime_reactivation_task = asyncio.ensure_future(
            self._reactivate_after_renderer_release(
                revision,
                stage,
                assignment_session,
                collection,
                resources,
            )
        )
        _log_verbose_info(
            "[ORMS] Interior Set Apply waiting for RTX material release"
        )

    async def _reactivate_after_renderer_release(
        self,
        revision: int,
        stage: object,
        assignment_session: AssignmentSession,
        collection: InteriorSetCollection,
        resources: InteriorSetRuntimeSnapshot,
    ) -> None:
        """Publish the newest Apply only after two complete Kit updates."""

        current_task = asyncio.current_task()
        try:
            for _ in range(_RENDERER_RELEASE_UPDATE_COUNT):
                await _next_kit_update()
            if revision != self._runtime_reactivation_revision:
                return
            if not self._prepared_stage_is_current(
                stage,
                assignment_session,
            ):
                return
            if self._runtime_reactivation_task is current_task:
                self._runtime_reactivation_task = None
            self._activate_current_stage(
                audit_event="INTERIOR_SETS_APPLIED",
                collection_override=collection,
                runtime_snapshot_override=resources,
                prepared_assignment_session=assignment_session,
            )
            _log_verbose_info(
                "[ORMS] Interior Set Apply reactivated after RTX release"
            )
        except asyncio.CancelledError:
            return
        except Exception as error:
            if self._runtime_reactivation_task is current_task:
                self._runtime_reactivation_task = None
            self._handle_lifecycle_failure("Apply Interior Sets", error)
        finally:
            if self._runtime_reactivation_task is current_task:
                self._runtime_reactivation_task = None

    def _prepared_stage_is_current(
        self,
        stage: object,
        assignment_session: AssignmentSession,
    ) -> bool:
        """Reject a delayed Apply after stage or owner replacement."""

        import omni.usd

        return (
            omni.usd.get_context().get_stage() is stage
            and self._assignment_session is assignment_session
            and assignment_session.owns_stage(stage)
        )

    def _runtime_reactivation_pending(self) -> bool:
        task = getattr(self, "_runtime_reactivation_task", None)
        return task is not None and not task.done()

    def _cancel_runtime_reactivation(self) -> None:
        """Invalidate and cancel one not-yet-published Apply request."""

        self._runtime_reactivation_revision = (
            getattr(self, "_runtime_reactivation_revision", 0) + 1
        )
        task, self._runtime_reactivation_task = (
            getattr(self, "_runtime_reactivation_task", None),
            None,
        )
        if task is not None and not task.done():
            task.cancel()

    def _phase5_ownership_details(self) -> dict[str, object]:
        details: dict[str, object] = self._lifecycle.ownership_details()
        classifier = self._lifecycle.classifier
        details.update(
            {
                "assignment_session_count": int(
                    self._assignment_session is not None
                ),
                "camera_target_count": len(
                    tuple(getattr(classifier, "camera_input_paths", ()))
                ),
                "service_stage_subscription_count": len(
                    getattr(self, "_stage_subscriptions", ())
                ),
            }
        )
        return details

    def _ensure_phase5_audit(self, stage: Any, settings: Any) -> None:
        if not _verbose_diagnostics_enabled(settings):
            return
        audit = getattr(self, "_phase5_audit", None)
        if audit is not None and audit.owns_stage(stage):
            return
        try:
            self._phase5_audit = Phase5RuntimeAudit(stage)
        except Exception as error:
            self._phase5_audit = None
            log_room_map_warning(
                owner="ORMS PHASE 5 AUDIT",
                process="SOURCE AND RESOURCE BASELINE",
                state="UNAVAILABLE",
                details={"error": repr(error)},
            )

    def _record_phase5_sample(self, event: str) -> None:
        audit = getattr(self, "_phase5_audit", None)
        if audit is None:
            return
        try:
            audit.sample(event, self._phase5_ownership_details())
        except Exception as error:
            log_room_map_warning(
                owner="ORMS PHASE 5 AUDIT",
                process="LIFECYCLE RESOURCE SAMPLE",
                state="UNAVAILABLE",
                details={"event": event, "error": repr(error)},
            )

    def _deactivate_stage(self, *, audit_event: str = "DEACTIVATED") -> None:
        cleanup_errors: list[Exception] = []
        self._cancel_runtime_reactivation()
        try:
            self._lifecycle.teardown()
        except Exception as error:
            cleanup_errors.append(error)
        assignment_session, self._assignment_session = (
            self._assignment_session,
            None,
        )
        if assignment_session is not None:
            try:
                assignment_session.stop()
            except Exception as error:
                cleanup_errors.append(error)
        audit, self._phase5_audit = getattr(self, "_phase5_audit", None), None
        if audit is not None:
            try:
                audit.finish(audit_event, self._phase5_ownership_details())
            except Exception as error:
                cleanup_errors.append(error)
        if cleanup_errors:
            details = "; ".join(repr(error) for error in cleanup_errors)
            raise RuntimeError(
                f"ORMS stage cleanup failed: {details}"
            ) from cleanup_errors[0]

    def stop(self) -> None:
        """Stop runtime work before removing callbacks and material resources."""

        demo_open_task, self._demo_open_task = self._demo_open_task, None
        if demo_open_task is not None and not demo_open_task.done():
            demo_open_task.cancel()
        settings_window, self._settings_window = self._settings_window, None
        if settings_window is not None:
            settings_window.stop()
        try:
            self._deactivate_stage()
        except Exception as error:
            log_room_map_error(
                owner="ORMS RUNTIME SERVICE",
                process="SHUTDOWN CLEANUP",
                state="FAILED",
                details={"error": repr(error)},
            )
        for subscription in self._stage_subscriptions:
            reset = getattr(subscription, "reset", None)
            if callable(reset):
                reset()
        self._stage_subscriptions = ()
        self._material_registration.stop()
        self._interior_sets = None
        _log_verbose_info("[ORMS] Runtime extension stopped")
