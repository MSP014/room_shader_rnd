# KRM-92 — ORMS UI and Artist Workflow

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-92 |
| Preceding delivery | KRM-91 |
| Implementation target | Existing `Window > ORMS` panel and Extension Manager overview page |
| State | Planned next implementation task |
| Last reviewed | 3 September 2026 |

## Purpose

KRM-92 turns the functional ORMS controls accepted in KRM-91 into a coherent
artist-facing workflow. The task owns the presentation, discoverability,
editing affordances, validation feedback, and user guidance around the existing
runtime. It does not reopen the accepted shader, classifier, assignment,
lifecycle, or resource-routing contracts.

## Accepted starting point

KRM-91 already provides the functional baseline:

- one dockable `Window > ORMS` panel;
- the `ORMS Classifier`, `Material Parameters`, and `Interior Atlases` tabs;
- `Start`, `Stop`, `Restart`, and `Restore Original Asset` lifecycle controls;
- automatic recognition and reversible assignment of eligible
  `Windows_Glass` meshes;
- one shared set of material parameters applied to all x1-x4 family materials;
- four persistent production-atlas folder settings with packaged debug
  fallbacks;
- hidden Session-layer implementation prims;
- working settings callbacks and explicit atlas configuration application.

KRM-92 improves how artists understand and operate this functionality rather
than proving that the underlying functionality exists.

## Implementation plan

### Panel structure and runtime status

- establish a clear visual hierarchy for the lifecycle controls, runtime
  status, tabs, settings groups, and feedback messages;
- make `Inactive`, `Running`, `Stopped`, and `Failed` states immediately
  understandable;
- show concise explanations for `Start`, `Stop`, `Restart`, and
  `Restore Original Asset`, including the difference between freezing the
  current result and removing ORMS-owned scene state;
- disable or explain actions that are unavailable in the current lifecycle
  state.

### ORMS Classifier

- refine labels, grouping, tooltips, numeric controls, and fallback
  explanations for room-family and classifier settings;
- make it clear that disabling x2, x3, or x4 reclassifies those rooms through
  the x1 fallback rather than removing window geometry;
- expose the accepted per-mesh opt-out contract
  `orms:autoAssign = false` without requiring manual USD attribute authoring;
- provide an artist-facing way to inspect automatically assigned meshes and
  change or remove those assignments.

### Material Parameters

- organise the shared shader controls into readable functional groups;
- explain that each value is applied to all active x1-x4 family materials;
- provide appropriate reset affordances without presenting four duplicated
  material configurations;
- surface validation or failure feedback without exposing internal Session
  Layer prims.

### Interior Atlases

- replace raw path editing with a directory picker for each x1, x2, x3, and x4
  production family while preserving direct text editing where useful;
- show whether each family resolves to a production folder or its packaged
  debug fallback;
- validate the expected continuous UDIM sequence beginning at `1001` and show
  actionable inline errors;
- make the effect of `Apply atlas configuration` explicit and report whether
  the controlled runtime rebuild succeeded;
- provide per-family and full-section reset affordances.

### Extension Manager overview

- rewrite the ORMS overview/welcome page for an end user;
- lead with what ORMS does, how to open its window, how automatic assignment
  works, and how to configure production atlases;
- replace the current internal module-ownership and developer-oriented copy
  with concise installation, first-use, and troubleshooting guidance;
- keep technical implementation details in repository documentation rather
  than the product welcome page.

## Acceptance plan

Accept KRM-92 against an installed extension package launched through normal
Kit AUTOLOAD, without `--ext-folder`, `--enable`, or Script Editor snippets.
The check must confirm that:

1. an artist can discover and understand all principal ORMS controls from
   `Window > ORMS`;
2. lifecycle state and available actions remain unambiguous throughout start,
   stop, restart, restore, stage replacement, and extension disable/re-enable;
3. automatic assignments can be inspected and overridden from the UI;
4. production atlas folders can be selected, validated, applied, and reset
   without knowing the internal `<UDIM>` pattern or variant count;
5. material settings remain centralised rather than duplicated per family;
6. the Extension Manager overview accurately describes the artist workflow;
7. the UI changes do not regress the accepted RTX Real-Time or RTX Interactive
   behaviour from KRM-91.

## Boundary

This record covers only the KRM-92 UI and artist-workflow scope. Work owned by
other Jira issues is not tracked here.
