"""Protect transactional Interior Set persistence and migration."""

import pytest
from msp.orms.interior_sets.atlas_mode import (
    ATLAS_MODE_DEBUG,
    ATLAS_MODE_PRODUCTION,
)
from msp.orms.interior_sets.contracts import DEFAULT_INTERIOR_SET_ID
from msp.orms.runtime.interior_set_repository import (
    INTERIOR_SET_SETTINGS_ROOT,
    InteriorSetSettingsRepository,
)
from msp.orms.runtime.resources import PRODUCTION_DIRECTORY_SETTING

from . import _support  # noqa: F401

KITCHENS_ID = "11111111-1111-1111-1111-111111111111"


class _Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.fail_path = None

    def get(self, path):
        return self.values.get(path)

    def set(self, path, value):
        if path == self.fail_path:
            raise RuntimeError("interrupted settings write")
        self.values[path] = value

    def set_float_array(self, path, value):
        self.set(path, list(value))

    def destroy_item(self, path):
        for key in tuple(self.values):
            if key == path or key.startswith(f"{path}/"):
                del self.values[key]


def test_legacy_globals_migrate_into_one_default_set_idempotently():
    settings = _Settings(
        {
            "/persistent/exts/orms/material/glass_roughness": 0.37,
            PRODUCTION_DIRECTORY_SETTING.format(room_size=2): "k:/x2",
        }
    )
    repository = InteriorSetSettingsRepository(settings)

    first = repository.ensure_migrated()
    second = repository.ensure_migrated()

    assert first.migrated
    assert not second.migrated
    assert first.collection == second.collection
    assert first.collection.default.set_id == DEFAULT_INTERIOR_SET_ID
    assert first.collection.default.atlas_directory(2) == "k:/x2"
    assert first.atlas_mode == ATLAS_MODE_PRODUCTION
    assert second.atlas_mode == ATLAS_MODE_PRODUCTION
    assert first.collection.default.material_mapping()[
        "glass_roughness"
    ] == pytest.approx(0.37)


def test_fresh_configuration_starts_in_forced_debug_mode():
    settings = _Settings()
    repository = InteriorSetSettingsRepository(settings)

    migration = repository.ensure_migrated()

    assert migration.atlas_mode == ATLAS_MODE_DEBUG
    assert repository.load_atlas_mode() == ATLAS_MODE_DEBUG


def test_failed_inactive_slot_write_preserves_applied_snapshot():
    settings = _Settings()
    repository = InteriorSetSettingsRepository(settings)
    applied = repository.ensure_migrated().collection
    candidate = applied.add(set_id=KITCHENS_ID)
    active_before = settings.get(f"{INTERIOR_SET_SETTINGS_ROOT}/active_slot")
    target_slot = "b" if active_before == "a" else "a"
    settings.fail_path = (
        f"{INTERIOR_SET_SETTINGS_ROOT}/slots/{target_slot}/order"
    )

    with pytest.raises(RuntimeError, match="interrupted settings write"):
        repository.commit(candidate)

    assert repository.load() == applied


def test_commit_can_roll_back_after_runtime_rebuild_failure():
    settings = _Settings()
    repository = InteriorSetSettingsRepository(settings)
    applied = repository.ensure_migrated().collection

    commit = repository.commit(applied.add(set_id=KITCHENS_ID))
    assert len(repository.load().sets) == 2

    repository.rollback(commit)

    assert repository.load() == applied


def test_reused_slot_drops_removed_set_subtree():
    settings = _Settings()
    repository = InteriorSetSettingsRepository(settings)
    default_only = repository.ensure_migrated().collection
    repository.commit(default_only.add(set_id=KITCHENS_ID))

    removed = repository.commit(default_only)
    removed_root = (
        f"{INTERIOR_SET_SETTINGS_ROOT}/slots/{removed.active_slot}/sets/"
        f"{KITCHENS_ID}"
    )

    assert not any(
        key == removed_root or key.startswith(f"{removed_root}/")
        for key in settings.values
    )


def test_live_rename_and_material_update_keep_stable_identity():
    settings = _Settings()
    repository = InteriorSetSettingsRepository(settings)
    repository.ensure_migrated()

    renamed = repository.rename(DEFAULT_INTERIOR_SET_ID, "Living Rooms")
    edited = repository.update_material(
        DEFAULT_INTERIOR_SET_ID,
        "glass_roughness",
        0.42,
    )

    assert renamed.default.set_id == DEFAULT_INTERIOR_SET_ID
    assert edited.default.name == "Living Rooms"
    assert edited.default.material_mapping()["glass_roughness"] == 0.42
