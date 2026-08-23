# MDL State Function Diagnostics

## Purpose

This diagnostic set establishes which MDL state values Omniverse exposes on a
Houdini-exported grid before the Room Map parallax mathematics is implemented.

The source geometry is `assets/_external/usd/test_grid/test_grid.usd`. Its mesh
is `/test_grid/geo/test_grid` and supplies vertex positions, vertex normals,
and a face-varying `primvars:st` channel.

## Diagnostic materials

| Material | State function | Colour encoding | Expected observation |
| --- | --- | --- | --- |
| `normal_as_colour.mdl` | `state::normal()` | `normal * 0.5 + 0.5` | Stable pink-red for the grid's +X normal. |
| `position_as_colour.mdl` | `state::position()` | `(position + offset) * scale` | Green increases along +Y; blue increases along +Z. |
| `direction_as_colour.mdl` | `state::direction()` | `direction * 0.5 + 0.5` | Static while the viewport camera moves: MDL reserves this value for environment lookups, not material view direction. |
| `uv0_as_colour.mdl` | `state::texture_coordinate(0)` | `(U, V, 0)` | Red follows U and green follows V across the grid. |

The diagnostic materials include emission so their encoded values remain visible
without depending on scene lighting.

## Test stage

Open `assets/_external/usd/test_grid/state_diagnostics.usda` in USD Composer.
The stage contains four independently bound copies of the Houdini grid:

| Grid prim | Material |
| --- | --- |
| `/World/NormalGrid/geo/test_grid` | `Normal` |
| `/World/PositionGrid/geo/test_grid` | `Position` |
| `/World/DirectionGrid/geo/test_grid` | `Direction` |
| `/World/UV0Grid/geo/test_grid` | `UV0` |

This avoids variant-selection state in Composer: all diagnostics are visible
at the same time. For `position`, the USD material configures
`position_offset` from the Houdini export's lower bounds. This maps the
original grid's Y and Z extents into the visible 0-1 range without hard-coding
those bounds in the MDL module.
## Validation checklist

- Confirm all four material modules compile and bind without MDL errors.
- Confirm `NormalGrid` remains stable when the camera moves.
- Confirm `PositionGrid` and `UV0Grid` show their respective gradients.
- Confirm `DirectionGrid` remains static while the viewport camera moves; this is the expected negative result.
- Repeat the observations in RTX Real-Time and RTX Interactive (Path Tracing).
## Current status`r`n`r`nOpenUSD confirms the Houdini mesh, normals, and `primvars:st` contract. RTX Real-Time and RTX Interactive (Path Tracing) compile and bind all four diagnostics without MDL errors. `state::direction()` remains static across camera movement, confirming that it cannot supply the Room Map view vector in an MDL material definition.`r`n
## Follow-up: runtime camera input

The diagnostic showed that `state::direction()` is not a material view vector.
`camera_position_bridge.py` supplies the missing runtime camera position through
a material input and `camera_direction_as_colour.mdl` derives the view direction
from it. Visual validation in RTX Real-Time and RTX Interactive (Path Tracing)
confirmed that this derived direction changes with active viewport camera motion.
