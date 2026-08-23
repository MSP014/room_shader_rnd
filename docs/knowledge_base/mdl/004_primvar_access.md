# MDL Primvar Access Contract

## Purpose

This diagnostic establishes the proposed access path for the Room Map frame
attributes exported from Houdini: `roomP`, `tangentu`, and `tangentv`.

The Houdini export at `assets/_external/usd/test_grid_attribs/` stores each
attribute as an unindexed `float3[]` primvar with `vertex` interpolation. The
mesh has four points, so each attribute contains four values.

## Proposed MDL access path

`src/mdl/diagnostics/primvar_as_colour.mdl` uses
`support_definitions::data_lookup_float3` with a named lookup and a visible
magenta fallback. The function is the Omniverse Material Graph primvar lookup
for named `float3` data.

The material accepts:

| Parameter | Type | Purpose |
| --- | --- | --- |
| `primvar_name` | `uniform string` | The USD primvar name, without the `primvars:` prefix. |
| `fallback_colour` | `color` | Magenta diagnostic value if the named data is unavailable. |
| `remap_signed` | `bool` | Maps signed vectors from `[-1, 1]` to `[0, 1]` for inspection. |

`assets/_external/usd/test_grid_attribs/primvar_access.usda` binds the same
material to three copies of the exported grid:

| Grid | Primvar | Expected encoded colour |
| --- | --- | --- |
| `RoomPGrid` | `roomP` | Green, from `(0, 0.5263158, 0)`. |
| `TangentUGrid` | `tangentu` | Yellow, after mapping `(0, 0, -1)` from signed to display range. |
| `TangentVGrid` | `tangentv` | Light green, after mapping `(0, 1, 0)` from signed to display range. |

Magenta on any grid means the lookup returned its fallback, not geometry data.

## Validation boundary

Static checks in `tests/test_primvar_access.py` verify the exported USD
contract, material bindings, and diagnostic source. They do not compile MDL or
prove renderer behaviour.

For runtime validation, open `primvar_access.usda` in USD Composer and inspect
all three grids in both RTX Real-Time and RTX Interactive (Path Tracing). The
module must compile without MDL errors and show the expected encoded colours.

Only after that observation may this named lookup be accepted as the production
input path for the Room Map shader. If it fails, the fallback investigation is
to transport the frame vectors through explicitly assigned texture-coordinate
channels.

## Runtime validation record

Visual validation completed on 18 August 2026 in NVIDIA USD Composer.

- RTX Real-Time rendered `RoomPGrid`, `TangentUGrid`, and `TangentVGrid` with their expected distinct encoded colours.
- RTX Interactive (Path Tracing) reproduced the same three diagnostic results.
- The diagnostic module compiled without MDL errors and no grid displayed the magenta fallback colour.

The named `float3` lookup is therefore accepted as the production input path for
Room Map frame attributes in Omniverse. Texture-coordinate channels remain a
fallback only for environments that do not provide the NVIDIA support-definitions
module.
