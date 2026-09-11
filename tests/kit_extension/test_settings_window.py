# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the ORMS Window-menu surface and its direct model callbacks."""

import asyncio
from pathlib import Path

import pytest
from msp.orms.runtime.resources import (
    DEBUG_ASSET_SETTING,
    PRODUCTION_DIRECTORY_SETTING,
)
from msp.orms.runtime.ui.panel_state import InteriorSetPanelState
from msp.orms.runtime.ui.settings_window import MENU_GROUP, WINDOW_NAME
from msp.orms.shared_room.settings_panel import SETTINGS_TAB_LABELS


def test_settings_live_in_one_dockable_orms_window():
    assert WINDOW_NAME == "ORMS"
    assert MENU_GROUP == "Window"
    assert SETTINGS_TAB_LABELS == (
        "ORMS Classifier",
        "Material Parameters",
        "Interior Atlases",
    )


def test_debug_and_production_atlases_have_separate_setting_zones():
    assert PRODUCTION_DIRECTORY_SETTING.endswith(
        "/atlases/x{room_size}/directory"
    )
    assert DEBUG_ASSET_SETTING.endswith("/atlases/debug/x{room_size}/asset")


def test_scalar_and_item_models_both_notify_the_runtime():
    from msp.orms.runtime.ui.settings_window import OrmsSettingsWindow

    events = []

    class ScalarModel:
        def add_value_changed_fn(self, callback):
            callback(self)

    class ItemModel:
        def add_item_changed_fn(self, callback):
            callback(self, object())

    OrmsSettingsWindow._subscribe_model(
        ScalarModel(),
        lambda: events.append("scalar"),
    )
    OrmsSettingsWindow._subscribe_model(
        ItemModel(),
        lambda: events.append("item"),
    )

    assert events == ["scalar", "item"]


def test_service_owns_window_lifecycle_outside_stage_lifecycle():
    service_path = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
        / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")

    assert "self._settings_window.start(" in source
    assert "settings_window.stop()" in source
    assert "classifier.set_settings(settings_from_kit())" in source
    assert "self._lifecycle.stop()" in source
    assert "self._lifecycle.resume()" in source
    assert "self._lifecycle.teardown()" in source
    assert "Preferences" not in source
    assert "prompt_if_unsaved_stage" in source
    assert "open_stage_async" in source


def test_service_skips_runtime_without_a_room_map_source_mesh():
    service_path = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
        / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")

    assert "if not stage_has_room_map_source_mesh(stage):" in source
    assert "Stage activation skipped" in source


def test_apply_waits_for_renderer_release_before_runtime_publication(
    monkeypatch,
):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    monkeypatch.setattr(service_module, "_log_verbose_info", lambda _: None)

    async def scenario():
        events = []
        stage = object()
        assignment_session = object()

        async def next_update():
            events.append("renderer_release_update")
            await asyncio.sleep(0)

        service = OrmsRuntimeService.__new__(OrmsRuntimeService)
        service._runtime_reactivation_task = None
        service._runtime_reactivation_revision = 0
        service._prepare_current_stage_for_reactivation = lambda: (
            events.append("renderer_teardown") or (stage, assignment_session)
        )
        service._prepared_stage_is_current = (
            lambda candidate_stage, candidate_session: (
                candidate_stage is stage
                and candidate_session is assignment_session
            )
        )
        service._activate_current_stage = lambda **kwargs: events.append(
            ("runtime_publication", kwargs)
        )
        monkeypatch.setattr(service_module, "_next_kit_update", next_update)

        service._apply_interior_sets_to_runtime("sets", "resources")
        task = service._runtime_reactivation_task

        assert task is not None
        assert events == ["renderer_teardown"]
        await task
        assert events == [
            "renderer_teardown",
            "renderer_release_update",
            "renderer_release_update",
            (
                "runtime_publication",
                {
                    "audit_event": "INTERIOR_SETS_APPLIED",
                    "collection_override": "sets",
                    "runtime_snapshot_override": "resources",
                    "prepared_assignment_session": assignment_session,
                },
            ),
        ]

    asyncio.run(scenario())


def test_new_apply_supersedes_pending_renderer_reactivation(monkeypatch):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    monkeypatch.setattr(service_module, "_log_verbose_info", lambda _: None)

    async def scenario():
        stage = object()
        assignment_session = object()
        releases = []
        publications = []

        async def next_update():
            releases.append("update")
            await asyncio.sleep(0)

        service = OrmsRuntimeService.__new__(OrmsRuntimeService)
        service._runtime_reactivation_task = None
        service._runtime_reactivation_revision = 0
        service._prepare_current_stage_for_reactivation = lambda: (
            stage,
            assignment_session,
        )
        service._prepared_stage_is_current = lambda *_: True
        service._activate_current_stage = lambda **kwargs: publications.append(
            kwargs["collection_override"]
        )
        monkeypatch.setattr(service_module, "_next_kit_update", next_update)

        service._apply_interior_sets_to_runtime("production", "prod")
        superseded = service._runtime_reactivation_task
        service._apply_interior_sets_to_runtime("debug", "debug")
        newest = service._runtime_reactivation_task

        assert superseded is not None
        assert newest is not None
        assert newest is not superseded
        await asyncio.gather(
            superseded,
            newest,
            return_exceptions=True,
        )
        assert publications == ["debug"]
        assert releases == ["update", "update"]

    asyncio.run(scenario())


def test_public_apply_publishes_after_stale_renderer_nodes_are_gone(
    monkeypatch,
):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.lifecycle import RuntimeState
    from msp.orms.runtime.service import OrmsRuntimeService

    monkeypatch.setattr(service_module, "_log_verbose_info", lambda _: None)

    async def scenario():
        events = []
        stage = object()
        assignment_session = object()

        class Controller:
            @staticmethod
            def apply(apply_runtime):
                events.append("profile_committed")
                apply_runtime("debug_sets", "debug_resources")
                events.append("profile_accepted")

        class Lifecycle:
            state = RuntimeState.RUNNING

        async def next_update():
            if "stale_nodes_destroyed" not in events:
                events.append("stale_nodes_destroyed")
            else:
                events.append("renderer_idle_update")
            await asyncio.sleep(0)

        def publish(**kwargs):
            assert "stale_nodes_destroyed" in events
            events.append(
                (
                    "new_runtime_published",
                    kwargs["collection_override"],
                    kwargs["runtime_snapshot_override"],
                )
            )

        service = OrmsRuntimeService.__new__(OrmsRuntimeService)
        service._interior_sets = Controller()
        service._lifecycle = Lifecycle()
        service._runtime_reactivation_task = None
        service._runtime_reactivation_revision = 0
        service._prepare_current_stage_for_reactivation = lambda: (
            events.append("old_runtime_detached")
            or (stage, assignment_session)
        )
        service._prepared_stage_is_current = lambda *_: True
        service._activate_current_stage = publish
        monkeypatch.setattr(service_module, "_next_kit_update", next_update)

        service._apply_interior_sets()
        task = service._runtime_reactivation_task

        assert task is not None
        assert events == [
            "profile_committed",
            "old_runtime_detached",
            "profile_accepted",
        ]
        await task
        assert events == [
            "profile_committed",
            "old_runtime_detached",
            "profile_accepted",
            "stale_nodes_destroyed",
            "renderer_idle_update",
            (
                "new_runtime_published",
                "debug_sets",
                "debug_resources",
            ),
        ]

    asyncio.run(scenario())


def test_restore_cancels_pending_renderer_reactivation(monkeypatch):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    monkeypatch.setattr(service_module, "_log_verbose_info", lambda _: None)

    async def scenario():
        release = asyncio.Event()
        publications = []

        async def next_update():
            await release.wait()

        service = OrmsRuntimeService.__new__(OrmsRuntimeService)
        service._runtime_reactivation_task = None
        service._runtime_reactivation_revision = 0
        service._prepare_current_stage_for_reactivation = lambda: (
            object(),
            object(),
        )
        service._prepared_stage_is_current = lambda *_: True
        service._activate_current_stage = lambda **kwargs: publications.append(
            kwargs
        )
        monkeypatch.setattr(service_module, "_next_kit_update", next_update)

        service._apply_interior_sets_to_runtime("sets", "resources")
        task = service._runtime_reactivation_task
        assert task is not None
        await asyncio.sleep(0)
        service._cancel_runtime_reactivation()
        release.set()
        await task

        assert publications == []
        assert not service._runtime_reactivation_pending()

    asyncio.run(scenario())


def test_stale_stage_cannot_publish_delayed_apply(monkeypatch):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    monkeypatch.setattr(service_module, "_log_verbose_info", lambda _: None)

    async def scenario():
        publications = []

        async def next_update():
            await asyncio.sleep(0)

        service = OrmsRuntimeService.__new__(OrmsRuntimeService)
        service._runtime_reactivation_task = None
        service._runtime_reactivation_revision = 0
        service._prepare_current_stage_for_reactivation = lambda: (
            object(),
            object(),
        )
        service._prepared_stage_is_current = lambda *_: False
        service._activate_current_stage = lambda **kwargs: publications.append(
            kwargs
        )
        monkeypatch.setattr(service_module, "_next_kit_update", next_update)

        service._apply_interior_sets_to_runtime("sets", "resources")
        task = service._runtime_reactivation_task
        assert task is not None
        await task

        assert publications == []
        assert not service._runtime_reactivation_pending()

    asyncio.run(scenario())


def test_deferred_apply_failure_uses_fail_open_cleanup(monkeypatch):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    monkeypatch.setattr(service_module, "_log_verbose_info", lambda _: None)

    async def scenario():
        failures = []

        async def next_update():
            await asyncio.sleep(0)

        def fail_reactivation(**_kwargs):
            raise RuntimeError("renderer rebuild failed")

        service = OrmsRuntimeService.__new__(OrmsRuntimeService)
        service._runtime_reactivation_task = None
        service._runtime_reactivation_revision = 0
        service._prepare_current_stage_for_reactivation = lambda: (
            object(),
            object(),
        )
        service._prepared_stage_is_current = lambda *_: True
        service._activate_current_stage = fail_reactivation
        service._handle_lifecycle_failure = (
            lambda action, error: failures.append((action, str(error)))
        )
        monkeypatch.setattr(service_module, "_next_kit_update", next_update)

        service._apply_interior_sets_to_runtime("sets", "resources")
        task = service._runtime_reactivation_task
        assert task is not None
        await task

        assert failures == [("Apply Interior Sets", "renderer rebuild failed")]
        assert not service._runtime_reactivation_pending()

    asyncio.run(scenario())


def test_assignment_rebuild_tears_down_renderer_dependencies_first():
    from msp.orms.runtime.service import OrmsRuntimeService

    events = []
    stage = object()

    class Lifecycle:
        @staticmethod
        def teardown():
            events.append("renderer_teardown")

    class AssignmentSession:
        @staticmethod
        def owns_stage(candidate):
            return candidate is stage

        @staticmethod
        def stop_assignments():
            events.append("assignment_teardown")

    session = AssignmentSession()
    service = OrmsRuntimeService.__new__(OrmsRuntimeService)
    service._lifecycle = Lifecycle()
    service._assignment_session = session

    prepared = service._prepare_assignment_session(stage, True)

    assert prepared is session
    assert events == ["renderer_teardown", "assignment_teardown"]


def test_default_profile_updates_runtime_and_preserve_fallback_together():
    from msp.orms.interior_sets.contracts import DEFAULT_INTERIOR_SET_ID
    from msp.orms.runtime.lifecycle import RuntimeState
    from msp.orms.runtime.service import OrmsRuntimeService

    events = []

    class Classifier:
        @staticmethod
        def set_interior_set_material_values(set_id, values):
            events.append(("runtime", set_id, dict(values)))
            return 4

    class Lifecycle:
        state = RuntimeState.RUNNING
        classifier = Classifier()

    class AssignmentSession:
        @staticmethod
        def set_material_input_values(values):
            events.append(("fallback", dict(values)))
            return 1

    service = OrmsRuntimeService.__new__(OrmsRuntimeService)
    service._lifecycle = Lifecycle()
    service._assignment_session = AssignmentSession()

    updated_count = service._apply_live_material_values(
        DEFAULT_INTERIOR_SET_ID,
        {"emission_strength": 32000.0},
    )

    assert updated_count == 5
    assert events == [
        (
            "runtime",
            DEFAULT_INTERIOR_SET_ID,
            {"emission_strength": 32000.0},
        ),
        ("fallback", {"emission_strength": 32000.0}),
    ]


def test_automatic_assignment_receives_every_interior_set_mesh_selector():
    from msp.orms.interior_sets.contracts import InteriorSetCollection
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    collection = InteriorSetCollection.default_only().add(
        set_id="11111111-1111-1111-1111-111111111111"
    )
    specific = collection.sets[1]
    collection = collection.replace(
        type(specific)(
            set_id=specific.set_id,
            selectors=("*/Lobby_Panes",),
        )
    )
    calls = []

    class Settings:
        @staticmethod
        def get(path):
            return path == service_module._AUTO_ASSIGN_SETTING

    class Atlas:
        asset_path = "debug/x1/room_map_debug.<UDIM>.png"
        variant_count = 8

    class Resources:
        @staticmethod
        def atlas_family(room_size):
            assert room_size == 1
            return Atlas()

    class Snapshot:
        @staticmethod
        def by_id(set_id):
            assert set_id == collection.default.set_id
            return type("RuntimeSet", (), {"resources": Resources()})()

    class Session:
        @staticmethod
        def apply(**kwargs):
            calls.append(kwargs)
            result_type = type(
                "Result",
                (),
                {"decisions": (), "assigned_prim_paths": ()},
            )
            return result_type()

    service = OrmsRuntimeService.__new__(OrmsRuntimeService)
    service._resources = type(
        "Layout",
        (),
        {
            "mdl_root": Path(__file__).resolve().parents[2]
            / "exts/msp.orms.runtime/data/mdl"
        },
    )()
    service._apply_automatic_assignments(
        Session(),
        collection,
        Snapshot(),
        Settings(),
    )

    assert calls[0]["candidate_selectors"] == (
        "Windows_Glass",
        "*/Lobby_Panes",
    )


def test_stopped_runtime_keeps_assignment_inspection_read_only():
    from msp.orms.runtime.assignments.session import AssignmentSnapshot
    from msp.orms.runtime.lifecycle import RuntimeState
    from msp.orms.runtime.service import OrmsRuntimeService

    class Session:
        @staticmethod
        def inspect():
            return AssignmentSnapshot(items=("mesh",), editable=True)

    class Lifecycle:
        state = RuntimeState.STOPPED

    service = OrmsRuntimeService.__new__(OrmsRuntimeService)
    service._assignment_session = Session()
    service._lifecycle = Lifecycle()

    snapshot = service._current_assignment_snapshot()

    assert snapshot.items == ("mesh",)
    assert not snapshot.editable


def test_stop_freezes_runtime_without_removing_automatic_assignments(
    monkeypatch,
):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    events = []

    class Lifecycle:
        @staticmethod
        def stop():
            events.append("stop")
            return True

    class AssignmentSession:
        @staticmethod
        def stop_assignments():
            raise AssertionError("Stop must retain the frozen assignments")

    service = OrmsRuntimeService.__new__(OrmsRuntimeService)
    service._lifecycle = Lifecycle()
    service._assignment_session = AssignmentSession()
    monkeypatch.setattr(
        service_module, "_log_verbose_info", lambda _message: None
    )

    service.stop_runtime()

    assert events == ["stop"]


def test_restart_from_stop_resumes_without_recycling_renderer_prims(
    monkeypatch,
):
    from msp.orms.runtime import service as service_module
    from msp.orms.runtime.service import OrmsRuntimeService

    events = []

    class Lifecycle:
        @staticmethod
        def resume():
            events.append("resume")
            return True

    service = OrmsRuntimeService.__new__(OrmsRuntimeService)
    service._lifecycle = Lifecycle()
    service._apply_classifier_settings = lambda: events.append("classifier")
    service._apply_material_settings = lambda: events.append("materials")
    service._record_phase5_sample = events.append
    service._activate_current_stage = lambda **_kwargs: events.append(
        "rebuild"
    )
    monkeypatch.setattr(
        service_module, "_log_verbose_info", lambda _message: None
    )

    service.restart_runtime()

    assert events == ["resume", "classifier", "materials", "RESTARTED"]


def test_interior_set_ui_is_split_into_staged_and_live_modules():
    runtime_root = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
    )
    window_source = (runtime_root / "ui" / "settings_window.py").read_text(
        encoding="utf-8"
    )
    atlas_source = (runtime_root / "ui" / "atlas_panel.py").read_text(
        encoding="utf-8"
    )
    material_source = (runtime_root / "ui" / "material_panel.py").read_text(
        encoding="utf-8"
    )
    assignment_source = (runtime_root / "assignments" / "panel.py").read_text(
        encoding="utf-8"
    )
    debug_atlas_source = (
        runtime_root / "ui" / "debug_atlas_panel.py"
    ).read_text(encoding="utf-8")

    assert "build_interior_set_atlas_panel" in window_source
    assert "build_interior_set_material_panel" in window_source
    assert '"Apply Interior Sets"' in atlas_source
    assert '"Revert unapplied changes"' in atlas_source
    assert '"Window mesh names / paths"' in atlas_source
    assert '"+ Add Interior Set"' in atlas_source
    assert '"Duplicate"' in atlas_source
    assert '"Browse..."' in atlas_source
    assert '"Browse..."' in debug_atlas_source
    assert '"Clear"' in debug_atlas_source
    assert "Packaged default" in debug_atlas_source
    assert "Default is evaluated last" in atlas_source
    assert '"Debug (force global)"' in atlas_source
    assert '"Production + debug fallback"' in atlas_source
    assert '"Open Demo Scene"' in atlas_source
    assert atlas_source.index('"Production + debug fallback"') < (
        atlas_source.index('"Open Demo Scene"')
    )
    assert "InteriorSetProfileWorkflow" in window_source
    assert "MATERIAL_CONTROLS" in material_source
    assert "material_changed(" in material_source
    assert '"Use source rule"' in assignment_source
    assert '"Allow ORMS"' in assignment_source
    assert '"Exclude / restore source"' in assignment_source


def test_content_rebuild_preserves_window_and_selected_tab():
    from msp.orms.runtime.ui.settings_window import OrmsSettingsWindow

    class Frame:
        def __init__(self):
            self.rebuild_count = 0

        def rebuild(self):
            self.rebuild_count += 1

    class Window:
        def __init__(self):
            self.frame = Frame()

    settings_window = OrmsSettingsWindow()
    window = Window()
    settings_window._window = window
    settings_window._active_tab_index = 2
    settings_window._remember_debug_atlases_collapsed(True)

    settings_window._rebuild_window()

    assert settings_window._window is window
    assert settings_window._active_tab_index == 2
    assert settings_window._panel_state.debug_atlases_collapsed is True
    assert window.frame.rebuild_count == 1


def test_interior_set_collapsed_state_follows_uuid_through_reorder():
    state = InteriorSetPanelState()
    default_id = "00000000-0000-0000-0000-000000000000"
    living_id = "11111111-1111-1111-1111-111111111111"
    cabinets_id = "22222222-2222-2222-2222-222222222222"

    state.remember_set_collapsed(default_id, True)
    state.remember_set_collapsed(living_id, True)
    state.remember_set_collapsed(cabinets_id, False)
    state.retain_sets((default_id, cabinets_id, living_id))

    assert state.is_set_collapsed(default_id) is True
    assert state.is_set_collapsed(living_id) is True
    assert state.is_set_collapsed(cabinets_id) is False

    state.retain_sets((default_id, cabinets_id))

    assert state.is_set_collapsed(living_id) is False


def test_classifier_and_material_collapse_state_survives_rebuilds():
    state = InteriorSetPanelState()
    living_id = "11111111-1111-1111-1111-111111111111"
    removed_id = "22222222-2222-2222-2222-222222222222"
    classifier_key = "classifier:room_families"
    set_key = f"material:set:{living_id}"
    group_key = f"{set_key}:group:glass"
    removed_key = f"material:set:{removed_id}"

    state.remember_section_collapsed(classifier_key, True)
    state.remember_section_collapsed(set_key, True)
    state.remember_section_collapsed(group_key, True)
    state.remember_section_collapsed(removed_key, True)
    state.retain_sets((living_id,))

    assert state.is_section_collapsed(classifier_key) is True
    assert state.is_section_collapsed(set_key) is True
    assert state.is_section_collapsed(group_key) is True
    assert state.is_section_collapsed(removed_key) is False


def test_extension_declares_standard_directory_picker_dependency():
    config_path = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "config"
        / "extension.toml"
    )

    assert '"omni.kit.window.file_importer" = {}' in (
        config_path.read_text(encoding="utf-8")
    )
    assert '"omni.kit.window.file_exporter" = {}' in (
        config_path.read_text(encoding="utf-8")
    )


def test_material_apply_feedback_is_visible_inline_for_success_and_failure():
    from msp.orms.runtime.materials.update_feedback import (
        MaterialUpdateFeedback,
    )

    class Label:
        text = ""

    feedback = MaterialUpdateFeedback(lambda: None)
    label = Label()
    feedback.start(lambda *_args: 4, lambda *_args: 4)
    feedback.remember_label("set-id", label)

    feedback.apply("set-id", "glass_roughness", 0.2)

    assert label.text == "Applied to 4 runtime materials."

    def fail(*_args):
        raise ValueError("not finite")

    feedback.start(fail, lambda *_args: 4)
    with pytest.raises(ValueError, match="not finite"):
        feedback.apply("set-id", "glass_roughness", 0.2)

    assert label.text == "Apply failed: not finite"


def test_material_reset_feedback_rebuilds_fields_after_success():
    from msp.orms.runtime.materials.update_feedback import (
        MaterialUpdateFeedback,
    )

    rebuilds = []
    feedback = MaterialUpdateFeedback(lambda: rebuilds.append("rebuilt"))
    feedback.start(lambda *_args: 0, lambda *_args: 4)

    feedback.reset("set-id", "Glass")

    assert feedback.status("set-id") == (
        "Glass reset. Applied to 4 runtime materials."
    )
    assert rebuilds == ["rebuilt"]
