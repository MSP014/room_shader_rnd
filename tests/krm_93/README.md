# KRM-93 validation bundle

This directory contains the focused automated tests and the three retained
validation stages for KRM-93.

## Start the default visual fixture

Run `launch_krm93_omniverse.bat`. The launcher starts
`msp.case03.blackwell.kit`, lets Kit render its lightweight bootstrap stage,
waits for both `app ready` and the first delivered viewport frame, and only
then opens `test_room_map_shared_rooms_omniverse.usda` automatically. This
keeps USD/MDL fixture loading out of Kit's own RTX startup path. It does not
start the classifier or camera bridge. After the stage opens, run this from
Kit's Script Editor:

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

The retained stages include `/World/KRM93Environment`, a DomeLight using the
project Kloofendal 4K HDRI at validation intensity. When the manual runtime is
started, it enables RTX single-sided face culling, aligns each complete Room
Map mesh's USD orientation with its `tangentu x tangentv` contract in the ORMS
Session Layer, and restores the prior renderer setting on stop or reload. A
mesh with incomplete, degenerate, or mixed-winding apertures is left unchanged
and produces an ORMS warning instead of being culled speculatively.

## Retained visual fixtures

- `test_room_map_shared_rooms_omniverse.usda` — isolated
  Omniverse-authored flat, bay, arc, and corner cases.
- `test_room_map_shared_rooms_houdini.usda` — KRM-93 capture layer over the
  shared Houdini-exported fixture at `../test_room_map_apertures_houdini.usda`.
- `test_room_map_shared_rooms_instances.usda` — referenced and instanceable
  copies of the Omniverse-authored fixture.

## Focused automated suite

From the repository root, run:

```powershell
python -m pytest tests/krm_93 -q
```

## MDL compile bisection

When Kit remains on a concrete material node, run the staged compiler probe
instead of repeatedly editing the production material and reopening Composer:

```powershell
python tests/krm_93/run_mdl_compile_probes.py
```

Individual phases can be selected with repeated `--probe` arguments, for
example:

```powershell
python tests/krm_93/run_mdl_compile_probes.py `
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
composition. It is a compiler diagnostic only and does not claim renderer or
production-extension readiness.
Pass `--keep-logs` only when the complete native Kit output is needed; the
files are written to the ignored `tests/krm_93/compile_probe_logs` directory.
