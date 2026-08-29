import ast
from pathlib import Path

KRM93_ROOT = Path(__file__).resolve().parent
LAUNCHER_EXTENSION = (
    KRM93_ROOT / "kit_exts" / "msp.orms.krm93.fixture_launcher"
)


def test_visual_validation_bundle_is_complete():
    expected = {
        "launch_krm93_omniverse.bat",
        "mdl_compile_minimal.mdl",
        "mdl_compile_probe_observer.py",
        "run_mdl_compile_probes.py",
        "test_room_map_shared_rooms_omniverse.usda",
        "test_room_map_shared_rooms_houdini.usda",
        "test_room_map_shared_rooms_instances.usda",
    }
    assert expected <= {path.name for path in KRM93_ROOT.iterdir()}


def test_mdl_compile_bisection_has_bounded_phase_markers():
    runner_path = KRM93_ROOT / "run_mdl_compile_probes.py"
    observer_path = KRM93_ROOT / "mdl_compile_probe_observer.py"
    runner = runner_path.read_text(encoding="utf-8")
    observer = observer_path.read_text(encoding="utf-8")

    ast.parse(runner, filename=str(runner_path))
    ast.parse(observer, filename=str(observer_path))
    for phase in (
        "minimal",
        "shared_aperture",
        "walls_geometry",
        "one_slice_lookup",
        "five_lookups",
        "full_composition",
    ):
        assert f'"{phase}"' in runner
    assert "SHADER_NODE_BEGIN" in observer
    assert "SHADER_NODE_COMPLETE" in observer
    assert "LOADING_HEARTBEAT" in observer
    assert "fixture_timeout" in observer


def test_launcher_passes_the_stage_to_a_test_only_startup_extension():
    source = (KRM93_ROOT / "launch_krm93_omniverse.bat").read_text(
        encoding="utf-8"
    )
    assert "msp.case03.blackwell.kit" in source
    assert "--ext-folder" in source
    assert "--enable msp.orms.krm93.fixture_launcher" in source
    assert "--/app/content/emptyStageOnStart=true" in source
    assert "test_room_map_shared_rooms_omniverse.usda" in source
    assert source.count("snippetFolders/") == 2
    assert source.count("${kit}/snippets") == 2
    assert "--exec" not in source


def test_fixture_launcher_extension_is_importable_source():
    manifest = (LAUNCHER_EXTENSION / "config" / "extension.toml").read_text(
        encoding="utf-8"
    )
    source_path = (
        LAUNCHER_EXTENSION / "orms_krm93_fixture_launcher" / "extension.py"
    )
    source = source_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(source_path))
    assert 'name = "orms_krm93_fixture_launcher"' in manifest
    assert '"omni.kit.viewport.ready" = {}' in manifest
    assert "is_app_ready" in source
    assert "ViewportReady" in source
    assert '"VIEWPORT_FIRST_FRAME_READY"' in source
    assert source.index("await viewport_ready_future") < source.index(
        "open_stage_async"
    )
    assert "open_stage_async" in source
    assert "material_loading_completion_observable=False" in source
    assert "completion_claim=False" in source
