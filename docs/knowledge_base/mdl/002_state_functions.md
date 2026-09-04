# MDL State Function Diagnostics

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-86 — MDL State Functions |
| Implementation | `exts/msp.orms.runtime/data/mdl/diagnostics/normal_as_colour.mdl`, `position_as_colour.mdl`, `direction_as_colour.mdl`, `uv0_as_colour.mdl` |
| Automated evidence | `tests/test_state_diagnostics.py` |
| Validation scene | `assets/_external/usd/test_grid/state_diagnostics.usda` |
| Evidence state | Renderer-validated |
| Last validated | 18 August 2026 |

## Purpose

This diagnostic establishes which MDL state values Omniverse exposes on the
Houdini-exported grid before Room Map projection is implemented, including the
negative result for a material view vector.

## Accepted contract

| Material | State function | Colour encoding | Accepted observation |
| --- | --- | --- | --- |
| `normal_as_colour.mdl` | `state::normal()` | `normal * 0.5 + 0.5` | Stable pink-red for the grid's +X normal. |
| `position_as_colour.mdl` | `state::position()` | `(position + offset) * scale` | Green and blue follow the grid's Y and Z position. |
| `direction_as_colour.mdl` | `state::direction()` | `direction * 0.5 + 0.5` | Static under camera motion; not a material view vector. |
| `uv0_as_colour.mdl` | `state::texture_coordinate(0)` | `(U, V, 0)` | Red and green follow the exported UV axes. |

The materials use emission so the encoded values do not depend on scene
lighting. Room Map code must not use `state::direction()` as the camera-to-
surface direction.

## Evidence

The source geometry is `assets/_external/usd/test_grid/test_grid.usd`. Its mesh
at `/test_grid/geo/test_grid` supplies positions, vertex normals, and
face-varying `primvars:st`.

The validation stage binds four independent copies:

| Grid prim | Material |
| --- | --- |
| `/World/NormalGrid/geo/test_grid` | `Normal` |
| `/World/PositionGrid/geo/test_grid` | `Position` |
| `/World/DirectionGrid/geo/test_grid` | `Direction` |
| `/World/UV0Grid/geo/test_grid` | `UV0` |

## Reproduction

Open `assets/_external/usd/test_grid/state_diagnostics.usda` in USD Composer.
Confirm that all four modules compile, `NormalGrid` remains stable,
`PositionGrid` and `UV0Grid` show their gradients, and `DirectionGrid` remains
static while the viewport camera moves. Repeat in RTX Real-Time and RTX
Interactive (Path Tracing).

## Validation record

On 18 August 2026, OpenUSD confirmed the Houdini mesh, normals, and
`primvars:st` contract. Both renderer modes compiled and bound all four
diagnostics without MDL errors. `state::direction()` remained static across
camera motion, confirming the expected negative result.

## Boundary

This record does not provide the missing material view vector. The runtime
camera input and world-space direction derived from it are the contract of
[003 — Camera Position Bridge](003_camera_position_bridge.md).
