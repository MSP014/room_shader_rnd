# Changelog

## 0.1.20

- Keep mesh-assignment controls read-only while the runtime is stopped or
  failed, avoiding an implicit rebuild from a frozen state.
- Hide an empty material-feedback label until the first live result so it does
  not reserve unnecessary panel space.
- Keep genuine stage-load failures at Warning while routine trace traffic
  remains at Info.

## 0.1.19

- Add source-safe automatic mesh-assignment inspection and per-mesh
  Use-source, Allow, and Exclude controls on the Classifier tab.
- Explain lifecycle actions and the x1 fallback directly beside their controls.
- Add per-group and complete per-Set material resets with inline success and
  failure feedback.
- Add staged per-family, per-Set, and complete atlas reset actions.
- Replace the developer-oriented Extension Manager README with an artist-first
  setup, workflow, and troubleshooting guide.
- Author the mesh-scoped Interior Set diagnostic as a Fabric-safe constant
  scalar string primvar instead of a uniform string array.
- Route routine stage-load trace blocks to Info while retaining Warning for
  actionable anomalies.

## 0.1.18

- Count runtime materials in the per-Interior-Set hierarchy so renderer
  telemetry reports the generated material total instead of a false zero.

## 0.1.17

- Remove the developer-oriented Applied runtime diagnostics section from the
  Interior Atlases tab while retaining the full structured runtime log.
- Keep selector conflicts as concise actionable inline warnings because they
  directly affect Set ownership and priority configuration.

## 0.1.16

- Route every collapsible section on all three ORMS tabs through one
  content-sized layout helper so folded content releases its scroll height.
- Retain classifier, material Set, and nested material-group collapse state
  across safe UI rebuilds using stable semantic keys and Set UUIDs.
- Add a regression guard that prevents direct, stretching
  `CollapsableFrame` construction from returning to runtime UI modules.
- Give inactive tab and atlas-mode choices a lighter grey background while
  retaining a dark selected state, so the current choice is visible at a
  glance.

## 0.1.15

- Remove the arbitrary upper bound from Emission Strength while retaining its
  non-negative and finite-value validation.
- Place Add, Apply, and Revert immediately below Atlas mode so the structural
  transaction remains accessible above long Interior Set lists.
- Retarget the live camera bridge after every successful structural rebuild so
  newly added Set materials receive camera position without a manual Restart.

## 0.1.14

- Replace the profile path field and three-step action row with two direct
  actions: Save Profile opens a Save dialog and writes the selected path;
  Load Profile opens an Open dialog and stages the selected file.
- Match Kit file exporter's real keyword callback contract, including its
  named `selections` argument.

## 0.1.13

- Add portable, human-readable `.orms` scene profiles containing the applied
  Interior Set UUIDs, priority, selectors, production paths, atlas mode, and
  complete material profiles.
- Load profiles into staged draft state without changing persistent settings,
  Session Layer state, or runtime output until `Apply Interior Sets`.
- Add profile path, Browse, Load to Draft, Save Applied, and Save Applied As
  controls below the global packaged-debug paths.
- Validate profile schema, identities, selector syntax, material types/ranges,
  and file suffix before staging, and save through an atomic local-file replace.

## 0.1.12

- Preserve every Interior Set block's collapsed state by immutable Set UUID
  across Add, Duplicate, Remove, reorder, Apply, revert, and runtime refresh.
- Preserve the Atlas mode block state alongside the already retained
  diagnostics state.
- Surface applied selector conflicts above the collapsed diagnostics panel,
  including the matched prim path, competing Set labels, and priority winner.
- Include full selector-conflict ownership details in runtime phase logs.

## 0.1.11

- Preserve the diagnostics collapsed state across safe frame rebuilds and let
  collapsed atlas panels release their layout height.
- Commit Production mode with per-family packaged fallback when a configured
  atlas directory is absent or invalid, while retaining its visible error.
- Prevent the legacy source-material x1 atlas from overriding the selected
  Default Interior Set resource.

## 0.1.10

- Make the production atlas browser select directories rather than validating
  a stale filename inside the chosen folder.
- Open the browser at the complete current directory without populating its
  filename input from the directory's final path component.

## 0.1.9

- Add one staged global atlas mode: Debug forces packaged x1-x4 families for
  every classified window, while Production uses Set-local families with
  matching packaged debug fallbacks.
- Rehydrate runtime resource records across exact-source reload boundaries so
  stale Python class identities cannot be mistaken for filesystem paths.
- Use the supported Kit 1.1.21 file-importer callback contract for production
  atlas directory browsing.

## 0.1.8

- Preserve the active ORMS tab and rebuild only Frame content after structural
  edits, avoiding window destruction during OmniUI callbacks.
- Restore the independent global x1-x4 packaged debug paths and clarify that
  Default is an unconditional fallback rather than a selector target.
- Recognise semantic window meshes below a composed `windows` container while
  retaining the legacy `Windows_Glass` and explicit opt-in boundaries.

## 0.1.7

- Bootstrap the packaged Python runtime before importing the ORMS service so
  registry installations do not depend on a neighbouring source checkout.

## 0.1.6

- Add ordered Interior Sets with immutable UUID identity, composed-path
  selectors, per-Set x1-x4 atlas families, and complete material profiles.
- Stage structural UI edits behind `Apply Interior Sets` while retaining live
  Set-scoped material controls and presentation-only renaming.
- Validate cross-family semantic variant manifests, report selector/resource
  diagnostics, and preserve source USD through transactional Session Layer
  rebuilds and persistent-settings rollback.

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
