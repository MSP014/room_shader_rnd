import ast
from pathlib import Path

VALIDATION_ROOT = Path(__file__).resolve().parent
LAUNCHER_EXTENSION = VALIDATION_ROOT / "kit_exts" / "msp.orms.fixture_launcher"


def test_visual_validation_bundle_is_complete():
    expected = {
        "launch_shared_rooms_houdini_omniverse.bat",
        "launch_shared_rooms_houdini_instances_omniverse.bat",
        "launch_shared_rooms_instances_omniverse.bat",
        "launch_shared_rooms_omniverse.bat",
        "mdl_compile_minimal.mdl",
        "mdl_compile_probe_observer.py",
        "run_mdl_compile_probes.py",
        "test_room_map_shared_rooms_omniverse.usda",
        "test_room_map_shared_rooms_houdini.usda",
        "test_room_map_shared_rooms_houdini_instance_source.usda",
        "test_room_map_shared_rooms_houdini_instances.usda",
        "test_room_map_shared_rooms_instances.usda",
    }
    assert expected <= {path.name for path in VALIDATION_ROOT.iterdir()}


def test_mdl_compile_bisection_has_bounded_phase_markers():
    runner_path = VALIDATION_ROOT / "run_mdl_compile_probes.py"
    observer_path = VALIDATION_ROOT / "mdl_compile_probe_observer.py"
    runner = runner_path.read_text(encoding="utf-8")
    observer = observer_path.read_text(encoding="utf-8")

    ast.parse(runner, filename=str(runner_path))
    ast.parse(observer, filename=str(observer_path))
    for phase in (
        "minimal",
        "shared_aperture",
        "front_exit_cutout",
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
    assert '"MDLC   comp error:"' in runner
    assert '"Unable to find SdrShaderNode"' in runner
    assert 'terminal = "COMPILE_ERROR"' in runner
    assert 'sourceAsset:subIdentifier = "room_map"' in runner


def test_minimal_compile_probe_covers_fail_open_binary_backface_cutout():
    source = (VALIDATION_ROOT / "mdl_compile_minimal.mdl").read_text(
        encoding="utf-8"
    )
    production_source = (
        VALIDATION_ROOT.parents[1] / "src" / "mdl" / "room_map.mdl"
    ).read_text(encoding="utf-8")

    function_marker = "float physical_aperture_cutout_opacity("
    probe_function_start = source.index(function_marker)
    production_function_start = production_source.index(function_marker)
    probe_function_end = source.index("\n\n", probe_function_start) + 2
    production_function_end = (
        production_source.index("\n\n", production_function_start) + 2
    )

    assert (
        source[probe_function_start:probe_function_end]
        == production_source[production_function_start:production_function_end]
    )
    assert "state::geometry_normal()" in source
    assert "state::transform_normal(" in source
    assert "bool facing_input_is_valid" in source
    assert "!facing_input_is_valid || facing_cosine" in source
    assert "? 1.0\n    : 0.0;" in source
    assert "geometry: material_geometry(" in source
    assert "cutout_opacity: room_cutout_opacity" in source


def test_launcher_passes_the_stage_to_a_test_only_startup_extension():
    source = (VALIDATION_ROOT / "launch_shared_rooms_omniverse.bat").read_text(
        encoding="utf-8"
    )
    assert "msp.case03.blackwell.kit" in source
    assert "--ext-folder" in source
    assert "--enable msp.orms.fixture_launcher" in source
    assert "--/app/content/emptyStageOnStart=true" in source
    assert "test_room_map_shared_rooms_omniverse.usda" in source
    assert source.count("snippetFolders/") == 2
    assert source.count("${kit}/snippets") == 2
    assert "--exec" not in source


def test_instance_launcher_passes_the_instance_stage_to_the_same_extension():
    source = (
        VALIDATION_ROOT / "launch_shared_rooms_instances_omniverse.bat"
    ).read_text(encoding="utf-8")
    assert "msp.case03.blackwell.kit" in source
    assert "--ext-folder" in source
    assert "--enable msp.orms.fixture_launcher" in source
    assert "--/app/content/emptyStageOnStart=true" in source
    assert "test_room_map_shared_rooms_instances.usda" in source
    assert "test_room_map_shared_rooms_omniverse.usda" not in source
    assert source.count("snippetFolders/") == 2
    assert source.count("${kit}/snippets") == 2
    assert "--exec" not in source


def test_houdini_launcher_passes_the_houdini_stage_to_the_same_extension():
    source = (
        VALIDATION_ROOT / "launch_shared_rooms_houdini_omniverse.bat"
    ).read_text(encoding="utf-8")
    assert "msp.case03.blackwell.kit" in source
    assert "--ext-folder" in source
    assert "--enable msp.orms.fixture_launcher" in source
    assert "--/app/content/emptyStageOnStart=true" in source
    assert "test_room_map_shared_rooms_houdini.usda" in source
    assert "test_room_map_shared_rooms_omniverse.usda" not in source
    assert "test_room_map_shared_rooms_instances.usda" not in source
    assert source.count("snippetFolders/") == 2
    assert source.count("${kit}/snippets") == 2
    assert "--exec" not in source


def test_houdini_instance_launcher_passes_its_stage_to_the_same_extension():
    source = (
        VALIDATION_ROOT / "launch_shared_rooms_houdini_instances_omniverse.bat"
    ).read_text(encoding="utf-8")
    assert "msp.case03.blackwell.kit" in source
    assert "--ext-folder" in source
    assert "--enable msp.orms.fixture_launcher" in source
    assert "--/app/content/emptyStageOnStart=true" in source
    assert "test_room_map_shared_rooms_houdini_instances.usda" in source
    assert "test_room_map_shared_rooms_omniverse.usda" not in source
    assert "test_room_map_shared_rooms_instances.usda" not in source
    assert source.count("snippetFolders/") == 2
    assert source.count("${kit}/snippets") == 2
    assert "--exec" not in source


def test_fixture_launcher_extension_is_importable_source():
    manifest = (LAUNCHER_EXTENSION / "config" / "extension.toml").read_text(
        encoding="utf-8"
    )
    source_path = LAUNCHER_EXTENSION / "orms_fixture_launcher" / "extension.py"
    source = source_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(source_path))
    assert 'name = "orms_fixture_launcher"' in manifest
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
