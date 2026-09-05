# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect the Houdini-to-OpenUSD named float3 primvar lookup contract."""

from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdShade

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPORTED_GRID_PATH = (
    REPOSITORY_ROOT
    / "assets"
    / "_external"
    / "usd"
    / "test_grid_attribs"
    / "test_grid_attribs.usd"
)
DIAGNOSTIC_STAGE_PATH = EXPORTED_GRID_PATH.with_name("primvar_access.usda")
DIAGNOSTIC_MODULE_PATH = (
    REPOSITORY_ROOT
    / "exts"
    / "msp.orms.runtime"
    / "data"
    / "mdl"
    / "diagnostics"
    / "primvar_as_colour.mdl"
)
EXPORTED_MESH_PATH = "/test_grid_attribs/geo/test_grid"

EXPECTED_PRIMVARS = {
    "roomP": UsdGeom.Tokens.vertex,
    "tangentu": UsdGeom.Tokens.vertex,
    "tangentv": UsdGeom.Tokens.vertex,
}

EXPECTED_BINDINGS = {
    "RoomPGrid": ("RoomP", "roomP", False),
    "TangentUGrid": ("TangentU", "tangentu", True),
    "TangentVGrid": ("TangentV", "tangentv", True),
}


def test_houdini_export_has_vertex_float3_room_map_primvars():
    stage = Usd.Stage.Open(str(EXPORTED_GRID_PATH))
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(EXPORTED_MESH_PATH))
    primvars_api = UsdGeom.PrimvarsAPI(mesh)
    point_count = len(mesh.GetPointsAttr().Get())

    assert point_count == 4

    for name, interpolation in EXPECTED_PRIMVARS.items():
        primvar = primvars_api.GetPrimvar(name)

        assert primvar.IsDefined()
        assert primvar.GetTypeName() == Sdf.ValueTypeNames.Float3Array
        assert primvar.GetInterpolation() == interpolation
        assert primvar.GetElementSize() == 1
        assert not primvar.IsIndexed()
        assert len(primvar.Get()) == point_count


def test_primvar_diagnostic_stage_binds_each_named_lookup():
    stage = Usd.Stage.Open(str(DIAGNOSTIC_STAGE_PATH))

    for grid_name, (
        material_name,
        primvar_name,
        remap_signed,
    ) in EXPECTED_BINDINGS.items():
        mesh = stage.GetPrimAtPath(f"/World/{grid_name}/geo/test_grid")
        material, relationship = UsdShade.MaterialBindingAPI(
            mesh
        ).ComputeBoundMaterial()
        shader = stage.GetPrimAtPath(f"/World/Looks/{material_name}/Shader")
        source_asset = shader.GetAttribute("info:mdl:sourceAsset").Get()

        assert relationship
        assert material.GetPath() == f"/World/Looks/{material_name}"
        assert source_asset.path.endswith("primvar_as_colour.mdl")
        assert shader.GetAttribute("inputs:primvar_name").Get() == primvar_name
        assert shader.GetAttribute("inputs:remap_signed").Get() == remap_signed


def test_primvar_diagnostic_uses_the_named_float3_lookup():
    source = DIAGNOSTIC_MODULE_PATH.read_text(encoding="utf-8")

    assert "import ::nvidia::support_definitions::*;" in source
    assert "nvidia::support_definitions::data_lookup_float3(" in source
    assert "primvar_name," in source
    assert "fallback_value" in source
