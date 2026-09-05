# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the exact-source dependency manifest used by manual reloads."""

from pathlib import Path

from msp.orms.scene import source_loader
from msp.orms.scene.source_loader import RuntimeSourceLoader

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXTENSION_ROOT = REPOSITORY_ROOT / "exts" / "msp.orms.runtime"


def test_runtime_source_manifest_covers_every_split_dependency():
    loader = RuntimeSourceLoader(EXTENSION_ROOT)

    expected = {
        "runtime_resource_metrics",
        "runtime_resources",
        "interior_set_atlas_mode",
        "interior_set_identity",
        "interior_set_manifest",
        "interior_set_contracts",
        "interior_set_selectors",
        "interior_set_runtime_resources",
        "runtime_stage_visibility",
        "stage_load_state",
        "stage_load_probe",
        "room_run_contracts",
        "room_run_topology",
        "room_run_mapping",
        "room_run_classifier",
        "shared_room_contracts",
        "shared_room_stage",
        "shared_room_authoring",
        "shared_room_interior_set_authoring",
        "shared_room_interior_set_diagnostics",
        "shared_room_pipeline",
        "shared_room_settings",
        "shared_room_changes",
        "shared_room_material_diagnostics",
        "shared_room_material_controls",
        "runtime_renderer_settings",
        "shared_room_classifier",
    }

    assert expected <= loader.source_paths.keys()
    assert all(path.is_file() for path in loader.source_paths.values())


def test_runtime_source_loader_uses_canonical_package_names():
    loader = RuntimeSourceLoader(EXTENSION_ROOT)
    loader.prepare()

    module = loader.load("room_run_contracts")

    assert module.__name__ == "msp.orms.classification.contracts"
    assert module.__package__ == "msp.orms.classification"
    assert Path(module.__file__) == loader.source_paths["room_run_contracts"]


def test_runtime_cleanup_retains_the_pre_consolidation_lifecycle_names():
    legacy_names = {
        "tools.omniverse.runtime.stage_load_probe",
        "tools.omniverse.shared_room_classifier",
        "tools.omniverse.shared_room.controller",
        "tools.omniverse.runtime.camera_position_bridge",
    }

    assert legacy_names <= set(source_loader._LIFECYCLE_MODULE_NAMES)
