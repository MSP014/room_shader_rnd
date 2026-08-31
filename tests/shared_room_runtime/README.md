# Shared-room runtime validation bundle

This directory contains the focused automated tests and the four retained
validation stages for the shared-room classifier.

## Start the default visual fixture

Run `launch_shared_rooms_omniverse.bat`. The launcher starts
`msp.case03.blackwell.kit`, lets Kit render its lightweight bootstrap stage,
waits for both `app ready` and the first delivered viewport frame, and only
then opens `test_room_map_shared_rooms_omniverse.usda` automatically. This
keeps USD/MDL fixture loading out of Kit's own RTX startup path. It does not
start the classifier or camera bridge. After the stage opens, run this from
Kit's Script Editor:

Run `launch_shared_rooms_instances_omniverse.bat` instead to use the same bootstrap
and startup extension with `test_room_map_shared_rooms_instances.usda`.

Run `launch_shared_rooms_houdini_omniverse.bat` to open the capture layer over the
Houdini-exported `assets/_external/usd/test_bld/test_bld.usd` component asset.
The capture layer preserves the payload/geometry/material layers and overrides
only the windows' material binding with the Room Map source material expected
by the runtime classifier.

Run `launch_shared_rooms_houdini_instances_omniverse.bat` for two
`instanceable = true` references to an instance-ready adapter over that same
Houdini component. This fixture exercises Preserve and Session de-instance
without substituting Omniverse-authored building geometry. In Preserve mode,
the prototype-authored `room_map_single` binding remains on the eligible window
mesh proxies; the facade, roof, and other Houdini material bindings remain
untouched. The shader reads the exported face-varying `roomUV` primvar and the
instance fixture predeclares the inherited
`/World.primvars:ormsCameraPositionWorld` channel before Hydra first syncs the
prototype material. The camera bridge updates only its Session Layer value.
Creating that primvar for the first time after the instance has rendered is
not a valid Preserve startup path because the already-synced prototype
material may not discover the late scene-data channel until it is rebuilt.
The source x1 fallback also reads each aperture's `roomID` and selects one of
the eight `room_map_debug` UDIM variants; equal IDs remain visually stable
while different logical rooms do not all collapse to tile `1001`.

```python
from pathlib import Path
import runpy

import omni.usd

root_layer = omni.usd.get_context().get_stage().GetRootLayer()
stage_path = Path(root_layer.realPath).resolve()
repository_root = next(
    parent
    for parent in stage_path.parents
    if (parent / "tools" / "omniverse" / "reload_room_map_runtime.py").is_file()
)
orms_runtime_loader = runpy.run_path(
    str(repository_root / "tools" / "omniverse" / "reload_room_map_runtime.py")
)
orms_runtime_loader["reload_and_start"](repository_root)
```

### Path Tracing cutout diagnosis

The completed bisection established two renderer boundaries. RTX Interactive
evaluates the binary cutout and its face-varying projection inputs, but not the
previous uniform `float4` scene-data lookups that carried the four aperture
intervals, so the production contract packs those intervals into three uniform
`float3` primvars. RTX Interactive Path Tracing also did not provide a stable
physical-facing result through `state::geometry_normal()`, so the classifier
now authors the aperture's stable world-space normal as the uniform
`ormsPhysicalNormal` primvar. Both renderers consume that value directly for
the physical backface cutout and use the same exact, slice-aware portal mask.
The temporary runtime diagnostic modes were removed after the production path
passed in RT and PT.

The launcher keeps the Kit application repository read-only. Its small local
extension exists only to schedule the stage-open request after Kit startup;
it does not package ORMS or change the KRM-91 production-extension scope.
Its warning-level markers distinguish `APP_READY`,
`VIEWPORT_FIRST_FRAME_READY`, and `STAGE_OPEN_REQUEST_BEGIN`; they do not claim
that MDL material loading has completed.
The startup scene-load probe emits one 15-second heartbeat with the current
loading path/counts, time without progress, average Kit-update FPS/frame time,
process and host memory, and the public Hydra GPU-memory fields available in
this Kit build. Faster state transitions are logged immediately.
Pending work reports `loading_status_stalled_for_ms`; once the native loading
status is empty, that field becomes `not_applicable` and the separate
`loading_status_idle_for_ms` counter is used instead.

The retained stages include `/World/RoomMapEnvironment`, a DomeLight using the
project Kloofendal 4K HDRI at validation intensity. When the manual runtime is
started, it enables RTX single-sided face culling, aligns each complete Room
Map mesh's USD orientation with its `tangentu x tangentv` contract in the ORMS
Session Layer, and restores the prior renderer setting on stop or reload. A
mesh with incomplete, degenerate, or mixed-winding apertures is left unchanged
and produces an ORMS warning instead of being culled speculatively.
The runtime retains an object-space pose cache for the derived room basis and
physical normal. Moving or rotating a classified building root refreshes their
authored world-space primvars without rerunning geometric classification. Scale
and edits below the building root remain classification-invalidating.

## Retained visual fixtures

- `test_room_map_shared_rooms_omniverse.usda` — isolated
  Omniverse-authored flat, bay, arc, and corner cases.
- `test_room_map_shared_rooms_houdini.usda` — shared-room capture layer over the
  Houdini-exported component asset at
  `../../assets/_external/usd/test_bld/test_bld.usd`.
- `test_room_map_shared_rooms_instances.usda` — referenced and instanceable
  copies of the Omniverse-authored fixture.
- `test_room_map_shared_rooms_houdini_instances.usda` — referenced and
  instanceable copies of the Houdini-exported component through
  `test_room_map_shared_rooms_houdini_instance_source.usda`.

## Focused automated suite

From the repository root, run:

```powershell
python -m pytest tests/shared_room_runtime -q
```

## MDL compile bisection

When Kit remains on a concrete material node, run the staged compiler probe
instead of repeatedly editing the production material and reopening Composer:

```powershell
python tests/shared_room_runtime/run_mdl_compile_probes.py
```

Individual phases can be selected with repeated `--probe` arguments, for
example:

```powershell
python tests/shared_room_runtime/run_mdl_compile_probes.py `
  --probe shared_aperture `
  --probe walls_geometry `
  --probe full_composition
```

Every phase is compiled in a separate headless Kit process under a fresh MDL
module filename. The warning stream records `SHADER_NODE_BEGIN`,
`SHADER_NODE_COMPLETE`, a 15-second stalled-loading heartbeat, and a bounded
timeout containing the last native loading message. This identifies whether a
regression comes from runtime primvar access, shared-aperture mapping,
camera/ray math, wall tracing, slice geometry, texture lookups, or final
composition. The `minimal` phase also compiles the production binary physical-
aperture backface cutout and its fail-open camera fallback, so a cutout backend
regression is reported before any atlas lookup is introduced. The
`front_exit_cutout` phase separately compiles the corner side-portal path that
opens up to four exact primary-facade aperture spans authored from the real
window geometry in `ormsPrimaryApertureMinU012`,
`ormsPrimaryApertureMaxU012`, and `ormsPrimaryApertureU3`. This preserves
unequal widths and facade gaps rather than reconstructing a regular grid in
MDL. Physical backfaces and the virtual front exit both retain a binary
geometry cutout. The four intervals use three `float3` scene-data values
because the retained Kit 110.1 PT any-hit path accepted the same projection
inputs but not the previous `float4` interval lookups. The front-exit mask
follows a
separate geometry-derived ray origin, so artistic aperture scale, offset, and
window shift continue to affect the virtual interior without moving the real
window cutouts. Corner depth is measured from the actual primary-window plane,
not from the nearest edge of the side aperture, so a physical gap between the
two facade legs remains part of the side-view projection. The virtual room box
may still snap to its logical corner boundary, but `ormsApertureMaskOffsetU`
retains the exact physical side-window plane for cutout projection; facade
thickness or an authored gap therefore cannot shift the primary-window holes.
It is a compiler diagnostic only and does not claim renderer or production-
extension readiness.
Pass `--keep-logs` only when the complete native Kit output is needed; the
files are written to the ignored `tests/shared_room_runtime/compile_probe_logs`
directory.
