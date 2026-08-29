# NVIDIA MDL and OpenUSD Research Records

## Purpose

This directory is the ordered record of ORMS MDL and OpenUSD findings. Each
file describes an accepted implementation contract, the evidence supporting
it, a reproducible check, and the boundary beyond which it must not be used as
proof.

## Index

| Record | Jira | Result | Evidence state |
| --- | --- | --- | --- |
| [001 — MDL Hello World](001_hello_world.md) | KRM-85 | Portable MDL source asset and material binding | Renderer-validated |
| [002 — State Functions](002_state_functions.md) | KRM-86 | Available MDL state and the missing material view vector | Renderer-validated |
| [003 — Camera Position Bridge](003_camera_position_bridge.md) | KRM-86 | Session-layer viewport camera input | Renderer-validated |
| [004 — Primvar Access](004_primvar_access.md) | KRM-87 | Named NVIDIA MDL primvar lookups | Renderer-validated |
| [005 — Single Room Parallax](005_single_room_parallax.md) | KRM-88 | Five-face cross-atlas room box | Renderer-validated |
| [006 — Depth Slices](006_depth_slices.md) | KRM-89 | Four analytic alpha depth slices | Renderer-validated |
| [007 — Room Variants](007_room_variants.md) | KRM-90 | Deterministic roomID-to-UDIM selection | Renderer-validated |
| [008 — Window Apertures](008_window_apertures.md) | KRM-94 | Physical aperture scale and offset | Renderer-validated |
| [009 — Shared Multi-Window Rooms](009_shared_multi_window_rooms.md) | KRM-93 | Runtime x1–x4 atlas grouping, bays, and bounded rectangular corners | Automated evidence complete; renderer validation pending |

## Record contract

Every numbered record uses the following top-level headings in this order:

1. `Record` — Jira ownership, implementation, tests, scenes, and evidence
   state.
2. `Purpose` — the single question answered by the record.
3. `Accepted contract` — behaviour that downstream work may rely on.
4. `Evidence` — retained code, assets, fixtures, and important negative
   findings.
5. `Reproduction` — the shortest deterministic way to repeat the check.
6. `Validation record` — what was actually observed, including renderer and
   date when applicable.
7. `Boundary` — unsupported cases and explicit follow-up ownership.

Topic-specific third-level headings are allowed inside these sections. A
planned result must be labelled as pending; it must not be written as accepted
renderer evidence.

## Writing rules

- Use British English and repository-relative paths.
- State coordinate spaces, units, primvar types, interpolation, and ownership
  explicitly whenever they affect the result.
- Separate source-asset data, composed USD data, Session Layer opinions, and
  material inputs.
- Record both Omniverse-authored and DCC-exported evidence when the contract
  claims transport parity.
- Name the exact renderer modes used for visual acceptance.
- Keep the five-atlas-lookup budget visible whenever shader changes could
  affect it.
- Link to local authoritative evidence; external links are supporting context,
  not substitutes for retained tests and fixtures.

## Maintenance

Add the next zero-padded record only when implementation or research evidence
exists. Update this index in the same change. When a pending visual boundary is
accepted, update the record's evidence state and validation date without
rewriting the historical contract.
