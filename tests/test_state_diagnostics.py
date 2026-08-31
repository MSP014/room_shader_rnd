"""Validate the retained MDL state-function diagnostic scene and bindings."""

from pathlib import Path

from pxr import Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE_PATH = (
    REPOSITORY_ROOT
    / "assets"
    / "_external"
    / "usd"
    / "test_grid"
    / "state_diagnostics.usda"
)


EXPECTED_DIAGNOSTICS = {
    "NormalGrid": ("Normal", "normal_as_colour.mdl", "state::normal()"),
    "PositionGrid": (
        "Position",
        "position_as_colour.mdl",
        "state::position()",
    ),
    "DirectionGrid": (
        "Direction",
        "direction_as_colour.mdl",
        "state::direction()",
    ),
    "UV0Grid": ("UV0", "uv0_as_colour.mdl", "state::texture_coordinate(0)"),
}


def test_state_diagnostics_stage_uses_four_houdini_grid_copies():
    stage = Usd.Stage.Open(str(STAGE_PATH))

    assert stage

    for grid_name in EXPECTED_DIAGNOSTICS:
        mesh = UsdGeom.Mesh(
            stage.GetPrimAtPath(f"/World/{grid_name}/geo/test_grid")
        )
        assert mesh.GetPointsAttr().Get()
        assert mesh.GetNormalsAttr().Get()

        st = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
        assert st.IsDefined()
        assert st.GetInterpolation() == UsdGeom.Tokens.faceVarying
        assert not mesh.GetPrim().GetVariantSets().HasVariantSet("diagnostic")


def test_each_grid_copy_has_its_diagnostic_material_bound():
    stage = Usd.Stage.Open(str(STAGE_PATH))

    for grid_name, (
        material_name,
        module_name,
        state_call,
    ) in EXPECTED_DIAGNOSTICS.items():
        mesh = stage.GetPrimAtPath(f"/World/{grid_name}/geo/test_grid")
        material, relationship = UsdShade.MaterialBindingAPI(
            mesh
        ).ComputeBoundMaterial()
        material_path = f"/World/Looks/{material_name}"
        shader = stage.GetPrimAtPath(f"{material_path}/Shader")
        source_asset = shader.GetAttribute("info:mdl:sourceAsset").Get()

        assert relationship
        assert material.GetPath() == material_path
        assert source_asset.path.endswith(module_name)
        module_path = (
            REPOSITORY_ROOT / "src" / "mdl" / "diagnostics" / module_name
        )
        assert state_call in module_path.read_text(encoding="utf-8")
