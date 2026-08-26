# Camera Position Bridge for MDL

## Purpose

MDL material definitions do not expose a camera/view vector. The Room Map
material therefore receives the active Kit camera position as a dynamic
`float3` input and derives a world-space view direction from the current
surface position.

`camera_direction_as_colour.mdl` is a diagnostic material, not Room Map
parallax logic. It makes the derived vector visible as RGB:

```mdl
normalize(camera_position_world - surface_position_world)
```

The surface position is explicitly transformed from MDL internal space to
world space before subtraction. This keeps both operands in the same
coordinate system.

## Prototype components

| Component | Responsibility |
| --- | --- |
| `src/mdl/diagnostics/camera_direction_as_colour.mdl` | Declares `camera_position_world` and visualises the derived direction. |
| `assets/_external/usd/test_grid/camera_direction_bridge.usda` | Binds the diagnostic material to the Houdini-exported UV grid. |
| `tools/omniverse/camera_position_bridge.py` | Obtains the active viewport camera and writes its world position into the material input. |

The bridge writes to the USD session layer. It changes the live stage without
saving camera motion into the `.usda` scene.

## Running in USD Composer

1. Open `assets/_external/usd/test_grid/camera_direction_bridge.usda`.
2. In the Script Editor, run:

   ```python
   from pathlib import Path
   import sys
   import omni.usd

   root_layer = omni.usd.get_context().get_stage().GetRootLayer()
   repository_root = Path(root_layer.realPath).parents[4]
   sys.path.append(str(repository_root / "tools" / "omniverse"))

   import importlib
   import camera_position_bridge

   camera_position_bridge.stop()
   camera_position_bridge = importlib.reload(camera_position_bridge)
   camera_position_bridge.start()
   ```

3. Move or orbit the active viewport camera. The grid colour must change.
4. To stop the live update, run `camera_position_bridge.stop()`.
5. Verify in RTX Real-Time and RTX Interactive (Path Tracing).

With no argument, `start()` discovers every composed
`inputs:camera_position_world` attribute in the active stage and updates all
of them. This is the normal mode for validation scenes with multiple Room Map
material instances. Pass one path, or a sequence of paths, to `start()` only
when a deliberately restricted target is required.

## Contract for later Room Map logic

`camera_position_world` is runtime-owned and uniform for the active viewport.
`roomP`, `N`, `tangentu`, `tangentv`, and `st` remain geometry/material data
coming from USD. The parallax implementation must transform the derived
world-space direction into the room's required coordinate frame explicitly.

## Validation record

Static USD and source contracts are covered by
`tests/test_camera_position_bridge.py`. Visual validation completed on 18 August 2026. In RTX Real-Time and RTX Interactive (Path Tracing), the grid colour changed as the active viewport camera moved. The Script Editor reported no bridge or MDL errors.
