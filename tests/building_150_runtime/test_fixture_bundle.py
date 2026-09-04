"""Validate the isolated Building 150 Kit fixture contract."""

import ast
from pathlib import Path

import pytest
from msp.orms.scene.assignment import (
    AutoAssignmentOwner,
    evaluate_windows_glass,
)
from msp.orms.shared_room import controller as classifier_module
from msp.orms.shared_room.controller import (
    RuntimeClassifierSettings,
    SharedRoomClassifier,
)
from msp.orms.shared_room.stage import (
    extract_stage_apertures,
    resolve_stage_metrics,
)
from pxr import Sdf, Usd, UsdGeom, UsdShade

FIXTURE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = FIXTURE_ROOT.parents[1]
STAGE_PATH = FIXTURE_ROOT / "test_room_map_building_150.usda"
SOURCE_STAGE_PATH = (
    REPOSITORY_ROOT
    / "assets"
    / "_external"
    / "usd"
    / "Moskovskiy_av_150"
    / "usd"
    / "Moskovskiy_av_150.usd"
)
WINDOW_ROOT_PATH = "/World/Building150/geo/render/windows"
SOURCE_WINDOW_ROOT_PATH = "/Moskovskiy_av_150/geo/render/windows"
WINDOW_NAMES = (
    "other_rooms",
    "halls",
    "living_rooms",
    "cabinets",
    "library_windows",
)
WINDOW_PATHS = tuple(f"{WINDOW_ROOT_PATH}/{name}" for name in WINDOW_NAMES)
SOURCE_WINDOW_PATHS = tuple(
    f"{SOURCE_WINDOW_ROOT_PATH}/{name}" for name in WINDOW_NAMES
)
EXPECTED_RUNTIME_INPUT_TYPES = {
    **{
        name: Sdf.ValueTypeNames.Bool
        for name in (
            "enable_opacity",
            "enable_emission",
            "emission_slice_1",
            "emission_slice_2",
            "emission_slice_3",
            "emission_slice_4",
            "enable_slice_1",
            "enable_slice_2",
            "enable_slice_3",
            "enable_slice_4",
        )
    },
    "room_atlas": Sdf.ValueTypeNames.Asset,
    "room_variant_count": Sdf.ValueTypeNames.Int,
    "variation_seed": Sdf.ValueTypeNames.Int,
    "camera_position_world": Sdf.ValueTypeNames.Float3,
    **{
        name: Sdf.ValueTypeNames.Float
        for name in (
            "room_depth",
            "room_uniform_scale",
            "slice_1_depth_percent",
            "slice_2_depth_percent",
            "slice_3_depth_percent",
            "slice_4_depth_percent",
            "glass_reflectivity",
            "glass_roughness",
            "glass_transmission",
            "emission_softness",
            "emission_strength",
            "emission_threshold",
        )
    },
    **{
        name: Sdf.ValueTypeNames.Float2
        for name in (
            "window_shift",
            "window_aperture_scale",
            "window_aperture_offset",
            "slice_1_offset",
            "slice_2_offset",
            "slice_3_offset",
            "slice_4_offset",
            "slice_1_scale",
            "slice_2_scale",
            "slice_3_scale",
            "slice_4_scale",
        )
    },
    "fallback_colour": Sdf.ValueTypeNames.Color3f,
    "glass_tint": Sdf.ValueTypeNames.Color3f,
}


def test_building_150_source_window_is_auto_assignment_candidate():
    stage = Usd.Stage.Open(str(SOURCE_STAGE_PATH), load=Usd.Stage.LoadAll)

    decisions = evaluate_windows_glass(stage)

    assert len(decisions) == len(SOURCE_WINDOW_PATHS)
    assert all(decision.eligible for decision in decisions)
    assert {decision.prim_path for decision in decisions} == set(
        SOURCE_WINDOW_PATHS
    )
    assert {decision.source_material_path for decision in decisions} == {
        "/Moskovskiy_av_150/mtl/base_lod00_mat"
    }


def test_building_150_auto_assignment_feeds_runtime_without_manual_script():
    stage = Usd.Stage.Open(str(SOURCE_STAGE_PATH), load=Usd.Stage.LoadAll)
    owner = AutoAssignmentOwner(
        stage,
        source_asset_path="room_map.mdl",
        atlas_asset_path="debug/x1/room_map_debug.<UDIM>.png",
        atlas_variant_count=8,
    )

    result = owner.apply()
    metrics = resolve_stage_metrics(stage, RuntimeClassifierSettings())
    extraction = extract_stage_apertures(stage, metrics)

    assert set(result.assigned_prim_paths) == set(SOURCE_WINDOW_PATHS)
    assert len(extraction.apertures) == 232
    for window_path in SOURCE_WINDOW_PATHS:
        window = stage.GetPrimAtPath(window_path)
        material, relationship = UsdShade.MaterialBindingAPI(
            window
        ).ComputeBoundMaterial()
        assert relationship
        assert str(material.GetPath()) == (
            "/__ORMSAutoAssignment/Looks/RoomMap"
        )

    owner.stop()

    for window_path in SOURCE_WINDOW_PATHS:
        window = stage.GetPrimAtPath(window_path)
        restored, relationship = UsdShade.MaterialBindingAPI(
            window
        ).ComputeBoundMaterial()
        assert relationship
        assert str(restored.GetPath()) == (
            "/Moskovskiy_av_150/mtl/base_lod00_mat"
        )


def test_building_150_runtime_is_published_in_one_live_stage_change(
    monkeypatch,
):
    stage = Usd.Stage.Open(str(STAGE_PATH), load=Usd.Stage.LoadAll)
    records = []
    submission_input_types = {}

    def record_trace(**record):
        records.append(record)
        if record["state"] != "MATERIAL_UPDATE_SUBMITTED":
            return
        shader = UsdShade.Shader(
            stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX1/Shader")
        )
        submission_input_types.update(
            {
                shader_input.GetBaseName(): shader_input.GetTypeName()
                for shader_input in shader.GetInputs()
            }
        )

    monkeypatch.setattr(
        classifier_module,
        "_subscribe_to_next_rendered_frame",
        lambda _callback: object(),
    )
    classifier = SharedRoomClassifier(
        stage,
        REPOSITORY_ROOT,
        RuntimeClassifierSettings(),
        trace_log_warning=record_trace,
    )

    classification = classifier.start()

    publication = next(
        record["details"]
        for record in records
        if record["state"] == "RUNTIME_LAYER_PUBLISHED"
    )
    material_state = next(
        record["details"]
        for record in records
        if record["state"] == "SOURCE_USD_STATE_AFTER_AUTHORING"
    )
    classification_state = next(
        record["details"]
        for record in records
        if record["state"] == "CLASSIFICATION_COMPLETE"
    )
    runtime_material_state = next(
        record["details"]
        for record in records
        if record["state"] == "RUNTIME_MATERIALS_AUTHORED"
    )
    assert len(classification.extraction.apertures) == 232
    assert len(classification.result.mappings) == 232
    assert classification.result.summary.group_size_counts == (
        (1, 98),
        (2, 33),
        (3, 12),
        (4, 8),
    )
    assert classification.result.summary.rejected_spacing_edge_count == 0
    assert classification_state["spacing_model"] == (
        "facade_median_centre_spacing_with_width_fallback"
    )
    assert classification_state["group_size_counts"] == (
        "x1=98,x2=33,x3=12,x4=8"
    )
    assert runtime_material_state["atlas_variant_counts"] == (
        "x1=56,x2=8,x3=8,x4=8"
    )
    normalised_atlas_assets = runtime_material_state["atlas_assets"].replace(
        "\\",
        "/",
    )
    assert (
        "x1="
        f"{REPOSITORY_ROOT.as_posix()}"
        "/assets/_external/tex/room_maps/room_map.<UDIM>.png"
        in normalised_atlas_assets
    )
    assert publication["authoring_notice_count"] == 1
    assert publication["runtime_layer_scope_valid"] is True
    assert publication["runtime_authored_source_material_path_count"] == 0
    assert publication["unexpected_runtime_authored_path_count"] == 0
    assert material_state["source_usd_material_network_unchanged"] is True
    assert material_state["changed_source_usd_fields"] == (
        "mesh_bindings,mesh_binding_opinions"
    )
    assert set(material_state["changed_mesh_binding_paths"].split(",")) == {
        path for path in WINDOW_PATHS if not path.endswith("/library_windows")
    }
    assert material_state["unexpected_mesh_binding_paths"] == "<none>"
    assert material_state["runtime_binding_scope_valid"] is True
    assert material_state["rendered_material_state_observable"] is False
    assert submission_input_types == EXPECTED_RUNTIME_INPUT_TYPES
    runtime_shader = UsdShade.Shader(
        stage.GetPrimAtPath("/__ORMSRuntime/Looks/RoomMapX1/Shader")
    )
    assert tuple(runtime_shader.GetInput("camera_position_world").Get()) == (
        30.0,
        16.0,
        75.0,
    )
    assert runtime_shader.GetInput("room_variant_count").Get() == 56
    assert (
        runtime_shader.GetInput("room_atlas")
        .Get()
        .path.endswith("assets/_external/tex/room_maps/room_map.<UDIM>.png")
    )
    for tile_number in range(1001, 1057):
        assert (
            REPOSITORY_ROOT
            / "assets"
            / "_external"
            / "tex"
            / "room_maps"
            / f"room_map.{tile_number}.png"
        ).is_file()
    for room_size in range(2, 5):
        family_shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert family_shader.GetInput("room_variant_count").Get() == 8
        family_name = f"room_map_debug_x{room_size}"
        assert (
            family_shader.GetInput("room_atlas")
            .Get()
            .path.endswith(f"{family_name}/{family_name}.<UDIM>.png")
        )
    for room_size in range(1, 5):
        family_shader = UsdShade.Shader(
            stage.GetPrimAtPath(
                f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            )
        )
        assert family_shader.GetInput("enable_emission").Get() is True
        for slice_index in range(1, 5):
            assert (
                family_shader.GetInput(f"emission_slice_{slice_index}").Get()
                is True
            )
        assert family_shader.GetInput("emission_strength").Get() == 5.0
        assert family_shader.GetInput("emission_threshold").Get() == (
            pytest.approx(0.8)
        )
        assert family_shader.GetInput("emission_softness").Get() == (
            pytest.approx(0.1)
        )
    assert runtime_shader.GetInput(
        "glass_reflectivity"
    ).Get() == pytest.approx(0.04)
    assert runtime_shader.GetInput("glass_roughness").Get() == pytest.approx(
        0.1
    )
    assert tuple(runtime_shader.GetInput("glass_tint").Get()) == (1.0,) * 3
    assert runtime_shader.GetInput("glass_transmission").Get() == 1.0
    assert tuple(runtime_shader.GetInput("window_aperture_scale").Get()) == (
        1.0,
        1.0,
    )
    assert runtime_shader.GetInput("slice_4_depth_percent").Get() == 80.0
    assert not UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World")).GetPrimvar(
        "ormsCameraPositionWorld"
    )
    assert classifier.camera_input_paths == (
        "/World/Looks/RoomMapSource/Shader.inputs:camera_position_world",
        *(
            f"/__ORMSRuntime/Looks/RoomMapX{room_size}/Shader"
            ".inputs:camera_position_world"
            for room_size in range(1, 5)
        ),
    )

    mesh_materials = {}
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        material, relationship = UsdShade.MaterialBindingAPI(
            prim
        ).ComputeBoundMaterial()
        assert relationship
        mesh_materials[str(prim.GetPath())] = str(material.GetPath())
    direct_window_materials = {
        f"{WINDOW_ROOT_PATH}/other_rooms": ("/__ORMSRuntime/Looks/RoomMapX1"),
        f"{WINDOW_ROOT_PATH}/halls": "/__ORMSRuntime/Looks/RoomMapX3",
        f"{WINDOW_ROOT_PATH}/living_rooms": ("/__ORMSRuntime/Looks/RoomMapX2"),
        f"{WINDOW_ROOT_PATH}/cabinets": "/__ORMSRuntime/Looks/RoomMapX4",
        f"{WINDOW_ROOT_PATH}/library_windows": "/World/Looks/RoomMapSource",
    }
    for window_path, material_path in direct_window_materials.items():
        assert mesh_materials.pop(window_path) == material_path
    assert set(mesh_materials.values()) == {
        "/World/Building150/mtl/base_lod00_mat"
    }

    expected_family_face_counts = {1: 98, 2: 66, 3: 36, 4: 32}
    for room_size, face_count in expected_family_face_counts.items():
        family_material_path = f"/__ORMSRuntime/Looks/RoomMapX{room_size}"
        direct_face_count = 0
        for window_path in WINDOW_PATHS:
            window = stage.GetPrimAtPath(window_path)
            material, _relationship = UsdShade.MaterialBindingAPI(
                window
            ).ComputeBoundMaterial()
            if str(material.GetPath()) == family_material_path:
                direct_face_count += len(
                    UsdGeom.Mesh(window).GetFaceVertexCountsAttr().Get()
                )
        family_subsets = tuple(
            UsdGeom.Subset(
                stage.GetPrimAtPath(f"{window_path}/ormsFamilyX{room_size}")
            )
            for window_path in WINDOW_PATHS
            if stage.GetPrimAtPath(
                f"{window_path}/ormsFamilyX{room_size}"
            ).IsValid()
        )
        assert (
            direct_face_count
            + sum(
                len(subset.GetIndicesAttr().Get()) for subset in family_subsets
            )
            == face_count
        )
        for subset in family_subsets:
            material, relationship = UsdShade.MaterialBindingAPI(
                subset.GetPrim()
            ).ComputeBoundMaterial()
            assert relationship
            assert str(material.GetPath()) == family_material_path

    classifier.stop()


def test_building_150_wrapper_preserves_the_source_contract():
    stage = Usd.Stage.Open(str(STAGE_PATH), load=Usd.Stage.LoadAll)
    expected = {
        "roomID": (Sdf.ValueTypeNames.IntArray, UsdGeom.Tokens.uniform),
        "roomP": (Sdf.ValueTypeNames.Float3Array, UsdGeom.Tokens.vertex),
        "tangentu": (Sdf.ValueTypeNames.Float3Array, UsdGeom.Tokens.vertex),
        "tangentv": (Sdf.ValueTypeNames.Float3Array, UsdGeom.Tokens.vertex),
        "roomUV": (
            Sdf.ValueTypeNames.TexCoord3fArray,
            UsdGeom.Tokens.faceVarying,
        ),
    }
    for window_path in WINDOW_PATHS:
        window = stage.GetPrimAtPath(window_path)
        primvars = UsdGeom.PrimvarsAPI(window)
        for name, (value_type, interpolation) in expected.items():
            primvar = primvars.GetPrimvar(name)
            assert primvar
            assert primvar.GetTypeName() == value_type
            assert primvar.GetInterpolation() == interpolation

        material, _relationship = UsdShade.MaterialBindingAPI(
            window
        ).ComputeBoundMaterial()
        assert material.GetPath() == Sdf.Path("/World/Looks/RoomMapSource")


def test_building_150_wrapper_changes_only_the_window_material():
    stage = Usd.Stage.Open(str(STAGE_PATH), load=Usd.Stage.LoadAll)
    mesh_materials = {}

    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        material, relationship = UsdShade.MaterialBindingAPI(
            prim
        ).ComputeBoundMaterial()
        assert relationship
        mesh_materials[str(prim.GetPath())] = str(material.GetPath())

    assert len(mesh_materials) == 33
    for window_path in WINDOW_PATHS:
        assert mesh_materials.pop(window_path) == "/World/Looks/RoomMapSource"
    assert set(mesh_materials.values()) == {
        "/World/Building150/mtl/base_lod00_mat"
    }


def test_shared_room_runtime_does_not_enable_scene_wide_face_culling():
    source_path = (
        REPOSITORY_ROOT
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "shared_room"
        / "controller.py"
    )
    source = source_path.read_text(encoding="utf-8")

    ast.parse(source, filename=str(source_path))
    assert "_enable_rtx_single_sided_culling" not in source
    assert "_enable_rtx_material_sync_loads" not in source


def test_building_150_wrapper_retains_the_hdri_without_a_camera():
    stage = Usd.Stage.Open(str(STAGE_PATH), load=Usd.Stage.LoadNone)
    dome = stage.GetPrimAtPath("/World/RoomMapEnvironment")

    assert dome.GetAttribute("inputs:exposure").Get() == 0
    assert dome.GetAttribute("inputs:intensity").Get() == 1000
    assert "kloofendal_48d_partly_cloudy_puresky_4k.exr" in str(
        dome.GetAttribute("inputs:texture:file").Get()
    )
    assert not any(prim.IsA(UsdGeom.Camera) for prim in stage.Traverse())


def test_building_150_launcher_reuses_the_shared_fixture_extension():
    source = (FIXTURE_ROOT / "launch_building_150_omniverse.bat").read_text(
        encoding="utf-8"
    )

    assert "msp.case03.blackwell.kit" in source
    assert "msp.orms.fixture_launcher" in source
    assert "test_room_map_building_150.usda" in source
    assert "..\\shared_room_runtime\\kit_exts" in source
    assert "--exec" not in source


def test_shared_fixture_launcher_uses_the_standard_warning_formatter():
    source_path = (
        REPOSITORY_ROOT
        / "tests"
        / "shared_room_runtime"
        / "kit_exts"
        / "msp.orms.fixture_launcher"
        / "orms_fixture_launcher"
        / "extension.py"
    )
    source = source_path.read_text(encoding="utf-8")

    ast.parse(source, filename=str(source_path))
    assert "log_room_map_warning(" in source
    assert "format_room_map_diagnostic_block" not in source
    assert "carb.log_warn(" not in source
    assert '"STAGE_OPEN_CANCELLED"' in source
    assert '"EXTENSION_SHUTDOWN_COMPLETE"' in source
