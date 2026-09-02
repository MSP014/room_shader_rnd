"""Protect exact-source dependency loading and runtime start order."""

import subprocess
import sys
from pathlib import Path

from tools.omniverse import reload_room_map_runtime
from tools.omniverse import room_run_classifier as legacy_core_module
from tools.omniverse import shared_room_classifier as legacy_controller_module
from tools.omniverse.room_run import classifier as core_classifier_module
from tools.omniverse.shared_room import controller as classifier_module

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RELOAD_PATH = (
    REPOSITORY_ROOT / "tools" / "omniverse" / "reload_room_map_runtime.py"
)


def test_standalone_run_path_bootstraps_canonical_package_imports():
    script = (
        "import runpy\n"
        f"namespace = runpy.run_path({str(RELOAD_PATH)!r})\n"
        "assert callable(namespace['reload_and_start'])\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_historical_classifier_paths_alias_the_canonical_modules():
    assert legacy_core_module is core_classifier_module
    assert legacy_controller_module is classifier_module


def test_runtime_contract_versions_are_synchronised():
    versions = {
        core_classifier_module.CLASSIFIER_CONTRACT_VERSION,
        classifier_module._EXPECTED_CLASSIFIER_CONTRACT_VERSION,
        reload_room_map_runtime._CONTRACT_VERSION,
    }
    assert versions == {"shared_room_runtime_v47"}


def test_runtime_loader_targets_only_classified_window_material_inputs():
    source = Path(reload_room_map_runtime.__file__).read_text(encoding="utf-8")

    assert "_RUNTIME_CAMERA_INPUT_PATHS" not in source
    assert "/World.primvars:ormsCameraPositionWorld" not in source
    assert "bridge.start(classifier.camera_input_paths)" in source


def test_runtime_loader_seeds_camera_before_classifier_and_bridge_start():
    source = Path(reload_room_map_runtime.__file__).read_text(encoding="utf-8")

    seed_offset = source.index("shared.seed_camera_position_primvar(")
    classifier_offset = source.index("classifier = shared.start(")
    bridge_offset = source.index(
        "camera_bridge = bridge.start(classifier.camera_input_paths)"
    )

    assert seed_offset < classifier_offset < bridge_offset
