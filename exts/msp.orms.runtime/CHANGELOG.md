# Changelog

## 0.1.5

- Replace the redundant production root, asset-pattern, and variant-count
  controls with one external atlas directory for each x1–x4 family.
- Discover the single UDIM sequence in each configured directory and derive
  its `<UDIM>` path and consecutive variant count automatically.

## 0.1.4

- Make in-process Extension Manager upgrades version-safe by evicting cached
  ORMS runtime modules that originate from an earlier installed package.
- Put the current runtime root first in `sys.path` and the existing
  `tools.omniverse` namespace package paths before loading stage, assignment,
  settings, or reload modules.

## 0.1.3

- Added explicit `Start`, `Restart`, `Stop`, and
  `Restore Original Asset` lifecycle controls to the ORMS window.
- `Stop` now freezes the current Session Layer result while releasing live
  USD and camera callbacks; `Start` resumes that same result.
- `Restart` performs a clean runtime rebuild, while restore removes both
  runtime and automatic-assignment Session Layers.

## 0.1.2

- Skip classifier and runtime authoring when the active stage contains no
  mesh bound to an ORMS source material.

## 0.1.1

- Added registry-ready package metadata and local filesystem publication.

## 0.1.0

- Added portable ORMS MDL, Python runtime, and packaged debug atlases.
- Added Material Library registration and reversible `Windows_Glass`
  assignment.
- Added the dockable ORMS settings window and local registry distribution.
