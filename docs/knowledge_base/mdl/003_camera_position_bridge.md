# Camera Position Bridge for MDL

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-86 — MDL State Functions, runtime follow-up |
| Implementation | `exts/msp.orms.runtime/msp/orms/scene/camera_position_bridge.py`, `exts/msp.orms.runtime/data/mdl/diagnostics/camera_direction_as_colour.mdl`, `exts/msp.orms.runtime/msp/orms/scene/status_log.py` |
| Automated evidence | `tests/shared_room_runtime/runtime/test_camera_position_bridge.py`, `tests/shared_room_runtime/runtime/test_status_log.py` |
| Validation scene | `assets/_external/usd/test_grid/camera_direction_bridge.usda` |
| Evidence state | Renderer-validated R&D bridge |
| Last validated | 18 August 2026 |

## Purpose

MDL material definitions do not expose the required camera/view vector. The
bridge supplies the active Kit viewport camera position as a dynamic `float3`
material input so MDL can derive:

```mdl
normalize(camera_position_world - surface_position_world)
```

## Accepted contract

`camera_position_world` is runtime-owned and uniform for the active viewport.
The bridge discovers all composed attributes named
`inputs:camera_position_world`, writes their world-space values into the stage
Session Layer, and does not save camera motion into source USD.

The shaded surface position is explicitly transformed from MDL internal space
to world space before subtraction. `roomP`, `N`, `tangentu`, `tangentv`, and
texture coordinates remain geometry or material data; later Room Map code must
transform the derived direction into its room frame explicitly.

Warnings use one formatted ORMS console entry with owner, process, state,
details, and host-local timestamp. Native Kit, USD, RTX, and MDL diagnostics
retain their own logger formatting.

## Evidence

| Component | Responsibility |
| --- | --- |
| `camera_direction_as_colour.mdl` | Visualises the derived world-space direction. |
| `camera_direction_bridge.usda` | Binds the diagnostic to Houdini-exported geometry. |
| `camera_position_bridge.py` | Tracks the active viewport and writes the Session Layer input. |
| `status_log.py` | Formats ORMS-owned warnings and errors. |

## Reproduction

Open `assets/_external/usd/test_grid/camera_direction_bridge.usda`, then run:

```python
from pathlib import Path
import sys
import omni.usd

root_layer = omni.usd.get_context().get_stage().GetRootLayer()
repository_root = Path(root_layer.realPath).parents[4]
extension_root = repository_root / "exts" / "msp.orms.runtime"
sys.path.append(str(extension_root))

from msp.orms.scene import camera_position_bridge

camera_position_bridge.stop()
camera_position_bridge.start()
```

Orbit or move the active viewport camera. The grid colour must change. Repeat
in RTX Real-Time and RTX Interactive (Path Tracing), then run
`camera_position_bridge.stop()`.

With no argument, `start()` discovers all camera inputs. A path or sequence of
paths may be supplied only for a deliberately restricted check.

## Validation record

On 18 August 2026, the diagnostic colour changed with active viewport camera
motion in both required renderer modes. The Script Editor reported no bridge
or MDL errors. Static source and USD checks are retained by the automated
tests.

## Boundary

This is a manually started R&D singleton, not a packaged extension and not a
multi-camera rendering contract. KRM-91 owns packaging it together with the
shared-room runtime classifier.
