"""Coordinate ORMS resources, assignment, and runtime lifecycle inside Kit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.omniverse.interior_sets.contracts import (
    DEFAULT_INTERIOR_SET_ID,
    InteriorSetCollection,
)
from tools.omniverse.interior_sets.runtime_resources import (
    InteriorSetRuntimeSnapshot,
)
from tools.omniverse.shared_room.interior_set_diagnostics import (
    InteriorSetDiagnostics,
)

from .interior_set_controller import InteriorSetController
from .interior_set_repository import InteriorSetSettingsRepository
from .interior_set_transaction import InteriorSetRollbackError
from .lifecycle import RuntimeLifecycleController, RuntimeState
from .material_library import MaterialLibraryRegistration
from .resources import (
    DEBUG_ASSET_SETTING,
    MATERIAL_SOURCE_ASSET,
    PRODUCTION_DIRECTORY_SETTING,
    ResourceLayout,
)
from .runtime_imports import activate_runtime_imports

_SETTINGS_ROOT = "/persistent/exts/msp.orms.runtime"
_AUTO_ASSIGN_SETTING = f"{_SETTINGS_ROOT}/autoAssignWindowsGlass"


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
        self._assignment_owner: Any | None = None
        self._lifecycle = RuntimeLifecycleController(
            state_changed=self._on_lifecycle_state_changed,
        )
        self._settings_window: Any | None = None
        self._interior_sets: InteriorSetController | None = None

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
        import carb.settings
        import omni.usd

        try:
            self._material_registration.start(
                self._extension_name,
                self._resources,
            )
            settings = carb.settings.get_settings()
            settings.set_default(_AUTO_ASSIGN_SETTING, True)
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

            self._ensure_runtime_path()
            from .settings_window import OrmsSettingsWindow

            self._settings_window = OrmsSettingsWindow()
            self._settings_window.start(
                classifier_changed=self._apply_classifier_settings,
                material_changed=self._apply_interior_set_material,
                apply_interior_sets=self._apply_interior_sets,
                rename_interior_set=self._rename_interior_set,
                interior_sets=self._interior_sets,
                runtime_diagnostics=(self._current_interior_set_diagnostics),
                start_runtime=self.start_runtime,
                restart_runtime=self.restart_runtime,
                stop_runtime=self.stop_runtime,
                restore_asset=self.restore_original_asset,
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

    def _ensure_runtime_path(self) -> None:
        """Expose this version and evict cached earlier ORMS installations."""

        import carb

        activation = activate_runtime_imports(self._resources.runtime_root)
        if activation.removed_modules:
            carb.log_info(
                "[ORMS] Replaced cached runtime from an earlier installation: "
                f"modules={len(activation.removed_modules)}, "
                "roots="
                f"{'; '.join(activation.removed_runtime_roots)}"
            )

    def _on_stage_event(self, event: object) -> None:
        import carb
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
            carb.log_error(f"[ORMS] Stage lifecycle failed: {error!r}")

    def _activate_current_stage(self) -> None:
        import carb
        import carb.settings
        import omni.usd

        self._deactivate_stage()
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        runtime_root = self._resources.runtime_root
        self._ensure_runtime_path()

        settings = carb.settings.get_settings()
        if self._interior_sets is None:
            raise RuntimeError("Interior Set configuration is unavailable")
        collection = self._interior_sets.applied
        runtime_snapshot = self._interior_sets.runtime_snapshot()
        default_runtime = runtime_snapshot.by_id(DEFAULT_INTERIOR_SET_ID)

        if bool(settings.get(_AUTO_ASSIGN_SETTING)):
            try:
                seed_x1 = default_runtime.resources.atlas_family(1)
            except KeyError:
                seed_x1 = None
            if seed_x1 is None:
                carb.log_warn(
                    "[ORMS] Windows Glass auto-assignment skipped: "
                    "no valid x1 atlas is available"
                )
            else:
                from tools.omniverse.runtime.assignment import (
                    AutoAssignmentOwner,
                )

                owner = AutoAssignmentOwner(
                    stage,
                    source_asset_path=MATERIAL_SOURCE_ASSET,
                    atlas_asset_path=seed_x1.asset_path,
                    atlas_variant_count=seed_x1.variant_count,
                )
                result = owner.apply()
                if result.assigned_prim_paths:
                    self._assignment_owner = owner
                decision_summary = "; ".join(
                    f"{decision.prim_path}:{decision.reason}"
                    for decision in result.decisions
                )
                carb.log_info(
                    "[ORMS] Windows Glass auto-assignment: "
                    f"assigned={len(result.assigned_prim_paths)}, "
                    f"examined={len(result.decisions)}, "
                    f"decisions={decision_summary or '<none>'}"
                )

        from tools.omniverse.shared_room.stage import (
            stage_has_room_map_source_mesh,
        )

        if not stage_has_room_map_source_mesh(stage):
            carb.log_info(
                "[ORMS] Stage activation skipped: no mesh is bound to an "
                "ORMS source material"
            )
            return

        from tools.omniverse.reload_room_map_runtime import (
            reload_and_start,
            stop_runtime,
        )

        try:
            classifier, camera_bridge = reload_and_start(
                runtime_root,
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
            )
        except Exception:
            stop_runtime()
            raise
        self._lifecycle.attach(classifier, camera_bridge, stop_runtime)
        if self._settings_window is not None:
            self._settings_window.refresh_interior_sets()

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

        import carb

        try:
            if self._lifecycle.resume():
                self._apply_classifier_settings()
                self._apply_material_settings()
                carb.log_info("[ORMS] Runtime resumed")
                return
            if self._lifecycle.state is RuntimeState.RUNNING:
                return
            self._activate_current_stage()
            if self._lifecycle.state is RuntimeState.RUNNING:
                carb.log_info("[ORMS] Runtime started by user")
        except Exception as error:
            self._handle_lifecycle_failure("Start", error)

    def restart_runtime(self) -> None:
        """Remove the current runtime result and rebuild it from settings."""

        import carb

        try:
            self._activate_current_stage()
            if self._lifecycle.state is RuntimeState.RUNNING:
                carb.log_info("[ORMS] Runtime restarted by user")
        except Exception as error:
            self._handle_lifecycle_failure("Restart", error)

    def stop_runtime(self) -> None:
        """Freeze the current ORMS result while releasing live callbacks."""

        import carb

        try:
            if self._lifecycle.pause():
                carb.log_info(
                    "[ORMS] Runtime stopped; current stage result remains frozen"
                )
        except Exception as error:
            self._handle_lifecycle_failure("Stop", error)

    def restore_original_asset(self) -> None:
        """Remove every ORMS-owned layer and reveal source asset bindings."""

        import carb

        try:
            self._deactivate_stage()
        except Exception as error:
            self._handle_lifecycle_failure("Restore Original Asset", error)
            return
        carb.log_info("[ORMS] Original asset state restored")

    def _handle_lifecycle_failure(
        self,
        action: str,
        error: Exception,
    ) -> None:
        import carb

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
        carb.log_error(f"[ORMS] {action} failed: {error!r}{cleanup_suffix}")

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
        from tools.omniverse.shared_room.settings import settings_from_kit

        classifier.set_settings(settings_from_kit())

    def _apply_material_settings(self) -> None:
        """Restore every applied Set's live profile after runtime resume."""

        if self._lifecycle.state is not RuntimeState.RUNNING:
            return
        classifier = self._lifecycle.classifier
        if classifier is None or self._interior_sets is None:
            return
        for item in self._interior_sets.applied.sets:
            classifier.set_interior_set_material_values(
                item.set_id,
                item.material_mapping(),
            )

    def _apply_interior_set_material(
        self,
        set_id: str,
        name: str,
        value: object,
    ) -> None:
        """Persist and author one Set-scoped live material edit."""

        if self._interior_sets is None:
            return
        classifier = self._lifecycle.classifier
        apply_runtime = (
            classifier.set_interior_set_material_values
            if classifier is not None
            and self._lifecycle.state is RuntimeState.RUNNING
            else None
        )
        self._interior_sets.update_material(
            set_id,
            name,
            value,
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
            if self._lifecycle.state is RuntimeState.RUNNING
            else None
        )
        try:
            self._interior_sets.apply(apply_runtime)
        except InteriorSetRollbackError as error:
            self._handle_lifecycle_failure(
                "Apply Interior Sets rollback",
                error,
            )
            raise

    def _apply_interior_sets_to_runtime(
        self,
        collection: InteriorSetCollection,
        resources: InteriorSetRuntimeSnapshot,
    ) -> None:
        """Rebuild Set families and retarget their live camera inputs."""

        classifier = self._lifecycle.classifier
        if classifier is None:
            raise RuntimeError("Running ORMS classifier is unavailable")
        classifier.apply_interior_sets(collection, resources)
        self._lifecycle.set_camera_input_paths(classifier.camera_input_paths)

    def _deactivate_stage(self) -> None:
        cleanup_errors: list[Exception] = []
        try:
            self._lifecycle.teardown()
        except Exception as error:
            cleanup_errors.append(error)
        assignment_owner, self._assignment_owner = (
            self._assignment_owner,
            None,
        )
        if assignment_owner is not None:
            try:
                assignment_owner.stop()
            except Exception as error:
                cleanup_errors.append(error)
        if cleanup_errors:
            details = "; ".join(repr(error) for error in cleanup_errors)
            raise RuntimeError(
                f"ORMS stage cleanup failed: {details}"
            ) from cleanup_errors[0]

    def stop(self) -> None:
        """Stop runtime work before removing callbacks and material resources."""

        import carb

        settings_window, self._settings_window = self._settings_window, None
        if settings_window is not None:
            settings_window.stop()
        try:
            self._deactivate_stage()
        except Exception as error:
            carb.log_error(f"[ORMS] Stage cleanup failed: {error!r}")
        for subscription in self._stage_subscriptions:
            reset = getattr(subscription, "reset", None)
            if callable(reset):
                reset()
        self._stage_subscriptions = ()
        self._material_registration.stop()
        self._interior_sets = None
        carb.log_info("[ORMS] Runtime extension stopped")
