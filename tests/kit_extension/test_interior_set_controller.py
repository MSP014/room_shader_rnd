"""Protect staged structural edits and one-shot runtime application."""

from pathlib import Path

import pytest
from msp.orms.interior_sets.atlas_mode import (
    ATLAS_MODE_DEBUG,
    ATLAS_MODE_PRODUCTION,
)
from msp.orms.interior_sets.contracts import DEFAULT_INTERIOR_SET_ID
from msp.orms.runtime.interior_sets.controller import InteriorSetController
from msp.orms.runtime.interior_sets.repository import (
    InteriorSetSettingsRepository,
)
from msp.orms.runtime.interior_sets.transaction import (
    InteriorSetRollbackError,
)
from msp.orms.runtime.resources import ResourceLayout

from . import _support  # noqa: F401

KITCHENS_ID = "11111111-1111-1111-1111-111111111111"
SHOPS_ID = "22222222-2222-2222-2222-222222222222"


class _Settings:
    def __init__(self):
        self.values = {}

    def get(self, path):
        return self.values.get(path)

    def set(self, path, value):
        self.values[path] = value

    def set_float_array(self, path, value):
        self.values[path] = list(value)

    def destroy_item(self, path):
        for key in tuple(self.values):
            if key == path or key.startswith(f"{path}/"):
                del self.values[key]


def _controller_with_settings():
    module_file = (
        Path(__file__).resolve().parents[2]
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
        / "resources.py"
    )
    settings = _Settings()
    controller = InteriorSetController(
        ResourceLayout.discover(module_file),
        InteriorSetSettingsRepository(settings),
    )
    return controller, settings


def _controller():
    return _controller_with_settings()[0]


def test_structural_edits_wait_for_one_explicit_apply():
    controller = _controller()
    applied = controller.applied
    runtime_calls = []

    controller.add(set_id=KITCHENS_ID)
    controller.stage_selectors(KITCHENS_ID, ("*/Kitchens_Windows",))

    assert controller.dirty
    assert controller.applied_revision == 0
    assert controller.draft_revision == 2
    assert controller.applied == applied
    assert len(controller.draft.sets) == 2
    assert not runtime_calls

    result = controller.apply(
        lambda collection, resources: runtime_calls.append(
            (collection, resources)
        )
    )

    assert result.rebuild_requested
    assert result.status == "applied"
    assert result.applied_revision == 2
    assert result.draft_revision == 2
    assert len(runtime_calls) == 1
    assert controller.applied == controller.draft
    assert not controller.dirty

    no_op = controller.apply(
        lambda _collection, _resources: runtime_calls.append("unexpected")
    )

    assert not no_op.rebuild_requested
    assert no_op.status == "no_changes"
    assert len(runtime_calls) == 1


def test_atlas_mode_is_staged_and_committed_with_the_same_apply():
    controller, settings = _controller_with_settings()
    runtime_calls = []

    assert controller.applied_atlas_mode == ATLAS_MODE_DEBUG
    controller.stage_atlas_mode(ATLAS_MODE_PRODUCTION)

    assert controller.dirty
    assert controller.applied_atlas_mode == ATLAS_MODE_DEBUG
    assert controller.draft_atlas_mode == ATLAS_MODE_PRODUCTION

    controller.apply(
        lambda _collection, resources: runtime_calls.append(resources)
    )

    assert controller.applied_atlas_mode == ATLAS_MODE_PRODUCTION
    assert not controller.dirty
    assert len(runtime_calls) == 1

    restarted = InteriorSetController(
        controller._resources,
        InteriorSetSettingsRepository(settings),
    )
    assert restarted.applied_atlas_mode == ATLAS_MODE_PRODUCTION

    restarted.stage_atlas_mode(ATLAS_MODE_DEBUG)
    restarted.revert()
    assert restarted.draft_atlas_mode == ATLAS_MODE_PRODUCTION


def test_debug_atlas_overrides_are_staged_applied_reverted_and_persisted():
    controller, settings = _controller_with_settings()
    packaged_x1 = controller.debug_atlas_display_directory(1)

    controller.stage_debug_atlas_directory(1, "custom-debug-x1")

    assert controller.dirty
    assert controller.applied_debug_atlas_directories[0] == ""
    assert controller.draft_debug_atlas_directories[0] == "custom-debug-x1"

    controller.revert()

    assert not controller.dirty
    assert controller.debug_atlas_display_directory(1) == packaged_x1

    controller.stage_debug_atlas_directory(1, "custom-debug-x1")
    controller.apply()
    restarted = InteriorSetController(
        controller._resources,
        InteriorSetSettingsRepository(settings),
    )

    assert restarted.applied_debug_atlas_directories[0] == "custom-debug-x1"
    restarted.clear_debug_atlas_directory(1)
    assert restarted.debug_atlas_display_directory(1) == packaged_x1


def test_scene_profile_load_stages_one_snapshot_without_persistence_or_apply():
    controller, settings = _controller_with_settings()
    persisted = dict(settings.values)
    candidate = controller.draft.add(set_id=KITCHENS_ID)
    runtime_calls = []

    staged = controller.stage_profile(candidate, ATLAS_MODE_PRODUCTION)

    assert staged == candidate
    assert controller.draft_atlas_mode == ATLAS_MODE_PRODUCTION
    assert controller.applied != candidate
    assert controller.dirty
    assert controller.draft_revision == 1
    assert controller.last_apply_status == "profile_staged"
    assert settings.values == persisted
    assert runtime_calls == []


def test_invalid_production_family_applies_with_packaged_fallback(tmp_path):
    controller = _controller()
    runtime_calls = []
    invalid_x4 = str(tmp_path / "missing-x4")
    controller.stage_atlas_mode(ATLAS_MODE_PRODUCTION)
    controller.stage_atlas_directories(
        DEFAULT_INTERIOR_SET_ID,
        ("", "", "", invalid_x4),
    )

    result = controller.apply(
        lambda _collection, resources: runtime_calls.append(resources)
    )

    family = (
        runtime_calls[0]
        .by_id(DEFAULT_INTERIOR_SET_ID)
        .resources.atlas_family(4)
    )
    assert result.status == "applied"
    assert family.source != "production"
    assert family.asset_path == (
        controller._resources.debug_atlas(4).asset_path.as_posix()
    )
    assert controller.applied.default.atlas_directory(4) == invalid_x4
    assert len(runtime_calls) == 1


def test_every_structural_gesture_stays_out_of_persistent_settings():
    controller, settings = _controller_with_settings()
    applied_settings = dict(settings.values)

    controller.add(set_id=KITCHENS_ID)
    controller.rename(KITCHENS_ID, "Kitchens")
    controller.stage_selectors(KITCHENS_ID, ("*/Kitchens_Windows",))
    controller.stage_atlas_directories(
        KITCHENS_ID,
        ("x1", "x2", "x3", "x4"),
    )
    controller.update_material(KITCHENS_ID, "glass_roughness", 0.4)
    controller.duplicate(KITCHENS_ID, set_id=SHOPS_ID)
    controller.move(SHOPS_ID, -1)
    controller.remove(KITCHENS_ID)

    assert controller.dirty
    assert settings.values == applied_settings


def test_atlas_family_and_complete_reset_remain_staged_until_apply():
    controller, settings = _controller_with_settings()
    controller.stage_atlas_directories(
        DEFAULT_INTERIOR_SET_ID,
        ("x1", "x2", "x3", "x4"),
    )
    controller.apply()
    applied_settings = dict(settings.values)

    controller.clear_atlas_family(DEFAULT_INTERIOR_SET_ID, 3)

    assert controller.draft.default.atlas_directories == (
        "x1",
        "x2",
        "",
        "x4",
    )
    assert controller.applied.default.atlas_directories == (
        "x1",
        "x2",
        "x3",
        "x4",
    )
    assert settings.values == applied_settings

    controller.clear_atlas_directories(DEFAULT_INTERIOR_SET_ID)

    assert controller.draft.default.atlas_directories == ("", "", "", "")
    assert settings.values == applied_settings

    controller.stage_atlas_mode(ATLAS_MODE_PRODUCTION)
    controller.stage_atlas_directories(
        DEFAULT_INTERIOR_SET_ID,
        ("new-x1", "new-x2", "new-x3", "new-x4"),
    )
    controller.stage_debug_atlas_directory(2, "custom-debug-x2")
    revision = controller.draft_revision

    controller.reset_atlas_configuration()

    assert controller.draft_atlas_mode == ATLAS_MODE_DEBUG
    assert controller.draft.default.atlas_directories == ("", "", "", "")
    assert controller.draft_debug_atlas_directories == ("", "", "", "")
    assert controller.draft_revision == revision + 1
    assert settings.values == applied_settings


def test_material_group_and_complete_reset_use_factory_defaults():
    controller = _controller()
    runtime_updates = []
    controller.update_material(
        DEFAULT_INTERIOR_SET_ID,
        "glass_roughness",
        0.83,
    )
    controller.update_material(
        DEFAULT_INTERIOR_SET_ID,
        "room_depth",
        9.0,
    )

    count = controller.reset_materials(
        DEFAULT_INTERIOR_SET_ID,
        "Glass",
        lambda set_id, values: runtime_updates.append((set_id, values)) or 4,
    )

    material = controller.applied.default.material_mapping()
    assert count == 4
    assert material["glass_roughness"] == 0.1
    assert material["room_depth"] == 9.0
    assert set(runtime_updates[0][1]) == {
        "glass_roughness",
        "glass_reflectivity",
        "glass_tint",
        "glass_transmission",
    }

    controller.reset_materials(DEFAULT_INTERIOR_SET_ID)

    assert controller.applied.default.material_mapping()["room_depth"] == 1.0


def test_invalid_material_value_is_rejected_before_persistence():
    controller, settings = _controller_with_settings()
    persisted = dict(settings.values)

    with pytest.raises(ValueError, match="above 1.0"):
        controller.update_material(
            DEFAULT_INTERIOR_SET_ID,
            "glass_roughness",
            4.0,
        )

    assert settings.values == persisted


def test_remove_reorder_and_restart_load_one_coherent_snapshot():
    controller, settings = _controller_with_settings()
    controller.add(set_id=KITCHENS_ID)
    controller.add(set_id=SHOPS_ID)
    controller.rename(SHOPS_ID, "Shops")
    controller.apply()
    controller.move(SHOPS_ID, -1)
    controller.remove(KITCHENS_ID)
    controller.apply()

    restarted = InteriorSetController(
        controller._resources,
        InteriorSetSettingsRepository(settings),
    )

    assert tuple(item.set_id for item in restarted.applied.sets) == (
        restarted.applied.default.set_id,
        SHOPS_ID,
    )
    assert restarted.applied.label_for(SHOPS_ID) == "Shops"
    assert not restarted.dirty


def test_invalid_draft_and_runtime_failure_preserve_applied_snapshot():
    controller = _controller()
    applied = controller.applied
    controller.add(set_id=KITCHENS_ID)
    controller.stage_selectors(KITCHENS_ID, ("*/Kitchen[",))

    with pytest.raises(ValueError, match="literal path text"):
        controller.apply(lambda _collection, _resources: None)
    assert controller.applied == applied
    assert controller.last_apply_status == "validation_failed"

    controller.revert()
    controller.add(set_id=KITCHENS_ID)

    def fail_runtime(_collection, _resources):
        raise RuntimeError("runtime rebuild failed")

    with pytest.raises(RuntimeError, match="runtime rebuild failed"):
        controller.apply(fail_runtime)

    assert controller.applied == applied
    assert controller.dirty
    assert controller.last_apply_status == "rolled_back"


def test_failed_persistent_rollback_has_explicit_failure_state(monkeypatch):
    controller = _controller()
    controller.add(set_id=KITCHENS_ID)

    def fail_rollback(_commit):
        raise RuntimeError("settings rollback failed")

    def fail_runtime(_collection, _resources):
        raise RuntimeError("runtime rebuild failed")

    monkeypatch.setattr(
        controller._repository,
        "rollback",
        fail_rollback,
    )

    with pytest.raises(InteriorSetRollbackError, match="rollback failed"):
        controller.apply(fail_runtime)

    assert controller.last_apply_status == "rollback_failed"
