# MDL Primvar Access Contract

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-87 — MDL Primvar Access |
| Implementation | `exts/msp.orms.runtime/data/mdl/diagnostics/primvar_as_colour.mdl` |
| Automated evidence | `tests/test_primvar_access.py` |
| Validation scene | `assets/_external/usd/test_grid_attribs/primvar_access.usda` |
| Evidence state | Renderer-validated |
| Last validated | 18 August 2026 |

## Purpose

This diagnostic establishes the production access path for the Houdini-
exported Room Map frame attributes `roomP`, `tangentu`, and `tangentv`.

## Accepted contract

`support_definitions::data_lookup_float3` performs named lookup of each
`float3` primvar. The exported mesh stores the attributes as unindexed
`float3[]` data with `vertex` interpolation.

| Parameter | Type | Purpose |
| --- | --- | --- |
| `primvar_name` | `uniform string` | USD primvar name without `primvars:`. |
| `fallback_colour` | `color` | Magenta when named data is unavailable. |
| `remap_signed` | `bool` | Maps signed vectors from `[-1, 1]` to `[0, 1]`. |

Named NVIDIA MDL lookup is accepted as the production ORMS input path. Texture
coordinate transport remains a compatibility fallback only where NVIDIA
support definitions are unavailable.

## Evidence

`assets/_external/usd/test_grid_attribs/` contains four values for each frame
attribute on its four-point mesh. The validation stage binds three copies:

| Grid | Primvar | Expected encoded colour |
| --- | --- | --- |
| `RoomPGrid` | `roomP` | Green from `(0, 0.5263158, 0)`. |
| `TangentUGrid` | `tangentu` | Yellow after signed remapping. |
| `TangentVGrid` | `tangentv` | Light green after signed remapping. |

Magenta means the lookup returned its fallback rather than geometry data.

## Reproduction

Open `assets/_external/usd/test_grid_attribs/primvar_access.usda` in USD
Composer. Inspect all three grids in RTX Real-Time and RTX Interactive (Path
Tracing). The module must compile without MDL errors and none of the grids may
show the magenta fallback.

## Validation record

On 18 August 2026, both renderer modes produced the three expected distinct
encoded colours without MDL errors or magenta fallbacks. Automated checks
retain the exported USD types, interpolation, bindings, and source contract.

## Boundary

This record proves named `float3` lookup for the retained Omniverse renderer
environment. It does not define window grouping, room projection, or transport
for arbitrary primvar types and renderers.
