# KRM-92 — Interior Sets and ORMS Artist Workflow

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-92 |
| Preceding delivery | KRM-91 |
| Implementation target | Existing ORMS classifier, runtime service, resources, settings, Session Layer authoring, and `Window > ORMS` panel |
| State | In progress — Interior Sets core delivered; remaining KRM-92 UI scope reassessed; 0.1.18 renderer acceptance pending |
| Last reviewed | 4 September 2026 |

## Purpose

KRM-92 extends ORMS from one material profile with x1-x4 atlas families to
multiple independently configured Interior Sets. Each Interior Set selects a
semantic class of compatible window meshes, owns its x1-x4 production atlas
directories and complete material profile, and remains inside one ORMS runtime.

The required processing order is:

```text
one scene classifier
    -> Interior Set assignment
    -> shared-room grouping within each Interior Set
    -> per-Set x1-x4 material families
    -> ORMS-owned Session Layer bindings and diagnostics
```

This work must not create separate classifiers, controllers, runtime services,
or shader definitions for living rooms, kitchens, shops, libraries, or any
other semantic room type.

## Architectural decisions

### One classifier and two independent identities

- ORMS retains one scene classifier and one runtime owner.
- `interior_set_id` is resolved before final room grouping and becomes an
  additional grouping-compatibility boundary.
- Two apertures may share one derived room only when they satisfy the accepted
  geometry, building, floor, adjacency, and `roomID` rules and have the same
  `interior_set_id`.
- `roomID` remains the identity used for a concrete room and deterministic
  atlas variation. It must not encode the semantic room type.
- `interior_set_id` selects the atlas library and material profile. It must not
  replace or alter `roomID` hashing.
- The accepted geometric algorithm remains common to the scene. Interior Set
  assignment adds a semantic boundary; it does not duplicate the classifier.

### Interior Set contract

Each Interior Set contains:

- an immutable internal `set_id`, stored as a canonical UUID string;
- an editable display name;
- zero or more ordered target-path masks for a non-default Set;
- independent production atlas directories for x1, x2, x3, and x4;
- one complete copy of every accepted artist-facing material value;
- runtime resource and diagnostic state derived from those persistent values.

New non-default Sets receive a UUID when created. The Default Interior Set uses
one reserved, stable UUID. A display name is never used as a persistent key,
material identity, Session Layer ownership key, or migration key.

An empty display name is valid. The UI derives a transient fallback label such
as `ORMS 1`, `ORMS 2`, or `ORMS 3` from the current visible order without
changing `set_id`.

`+ Add Interior Set` creates a staged non-default Set with a new immutable
UUID, empty selectors, empty production atlas directories, and a snapshot of
the Default Set's current material profile. Later changes to Default do not
propagate into that new Set.

`Duplicate Interior Set` creates a staged non-default copy with a new immutable
UUID. It copies the selected Set's editable name, selectors, production atlas
directories, and material profile, inserts the copy directly after its source,
and makes the name visibly editable before application. Duplication never
copies runtime identity, generated material paths, diagnostics, or Session
Layer state.

### Default and priority rules

- Exactly one Default Interior Set always exists.
- It is created automatically, cannot be removed, and may be renamed.
- It owns every compatible ORMS aperture that does not match a specific Set.
- It has no selector of its own; the UI explains the fallback instead of
  exposing an input that selector resolution would ignore.
- The UI may pin Default as the first visible block, but selector resolution
  always evaluates it last.
- Specific Interior Sets are evaluated from top to bottom in their explicit UI
  order. The first matching specific Set wins.
- Reordering specific Sets changes selector priority without changing their
  IDs, settings, material identity, or atlas state.
- If a prim matches more than one specific Set, the first Set still wins and a
  selector-conflict diagnostic records every matching Set and mask.

### Selector contract

- Selectors operate on the absolute composed USD prim path reported for each
  compatible candidate mesh, before room grouping.
- Matching is case-sensitive and evaluates the complete normalised path.
- The first implementation supports literal characters and `*`; `*` may span
  path separators so `*/Kitchens_Windows` works at different hierarchy depths.
- Multiple masks in one Set are combined with logical OR.
- Empty masks are ignored, duplicate masks are normalised, and an empty mask
  list matches nothing for a specific Set.
- No boolean expression language, regular-expression mode, source-layer query,
  or semantic inference is introduced in this task.
- One mesh path resolves to one Interior Set. Selecting different Sets for
  individual faces inside the same mesh is outside this first contract.
- Existing compatibility validation and explicit auto-assignment exclusion
  remain authoritative before selector priority is considered.
- The one global compatibility boundary recognises the legacy
  `Windows_Glass` prim/material identity, explicitly opted-in meshes, and
  semantic child meshes exported beneath a `windows` container. Interior Set
  names do not add further eligibility classifiers.

Examples of valid masks include:

```text
*/Kitchens_Windows
*/Kitchen_Glass
*/Restaurant_Kitchen_Windows
*/Shop*_Windows
```

### Runtime material and resource identity

- Runtime materials are keyed by `(set_id, room_size)` and use the existing MDL
  definition.
- The runtime may create up to four material instances for every active Set.
- USD prim names use a path-safe encoding of the immutable UUID, for example
  `Set_<uuid_hex>/RoomMapX1`; the editable display name is presentation metadata
  only.
- Artist-facing labels may read `Living Rooms x1` or `Kitchens x4`, but renaming
  a Set must not replace material prims or break persistent settings.
- Packaged debug x1-x4 atlases remain one global fallback inventory.
- One global staged atlas mode makes that inventory directly testable. `Debug`
  forces packaged x1-x4 atlases for every compatible window in every Set,
  regardless of configured production paths. `Production` uses each Set's
  production xN family when available and the matching packaged debug xN only
  when that family is absent.
- Each Set resolves each production family independently. An unconfigured
  production xN directory falls back only that Set's xN family to the packaged
  debug xN atlas. An invalid staged or applied directory keeps its authored
  value, reports the exact resource error, and applies the matching packaged
  debug fallback without rejecting otherwise valid Sets or families.
- One Set's resource failure must not replace another Set's valid production
  family.
- Material edits are fanned out only to the active x1-x4 materials belonging to
  the edited Set.
- The existing maximum of one room-face lookup plus four depth-slice lookups per
  shaded aperture remains unchanged. Additional Sets increase material-instance
  and authoring counts, not per-pixel texture lookups.

### Cross-family semantic variant coherence

The x1-x4 production families inside one Interior Set form one semantic room
library, not four unrelated image collections. A shared corner may expose the
same room through different family sizes, so the room variant is resolved once
for the group and retained across every facade leg.

- Every production family participating in cross-family rooms provides a
  minimal versioned variant-identity manifest. The manifest contains the
  ordered stable `variant_id` represented by each continuous UDIM tile.
- For the first version, the same ordered `variant_id` sequence is required in
  every coherent production x1-x4 family. Tile `1001 + index` therefore
  represents the same semantic room in each family.
- The resource validator checks manifest version, manifest length, continuous
  UDIM count, duplicate IDs, family counts, and ordered identity equality. It
  does not attempt to infer semantic equivalence from pixels or filenames.
- The `roomID` and the Set's `variation_seed` select one semantic variant index
  for the shared room. Every participating x1-x4 family consumes that same
  index; each family must not hash or wrap the room independently.
- Packaged debug x1-x4 families expose one built-in shared variant namespace and
  ordered identity sequence. Their manifests remain global package data rather
  than copied persistent values in every Set.
- A missing production xN family still resolves to packaged debug xN for
  ordinary single-family groups. A mixed production/debug resource bundle is
  valid for a cross-family room only when the participating families advertise
  the same variant namespace and ordered identities.
- If required families have incompatible counts, identity order, namespace, or
  missing identity metadata, ORMS must report the incompatibility and must not
  bind semantically different sides of one room. The affected corner is safely
  decomposed into independent single-family groups through the accepted
  classifier fallback.
- Legacy production folders without variant-identity metadata remain usable for
  single-family rooms and are reported as `unverified legacy`. They cannot form
  a cross-family shared room until a compatible manifest is supplied.

This is a bounded identity manifest only. General layout, procedural atlas
discovery, and arbitrary family remapping remain outside KRM-92.

### Persistence and migration

The new schema is versioned and keyed by `set_id`:

```text
/persistent/exts/msp.orms.runtime/interior_sets/schema_version
/persistent/exts/msp.orms.runtime/interior_sets/active_slot
/persistent/exts/msp.orms.runtime/interior_sets/slots/<slot>/order
/persistent/exts/msp.orms.runtime/interior_sets/slots/<slot>/atlas_mode
/persistent/exts/msp.orms.runtime/interior_sets/slots/<slot>/sets/<set_id>/name
/persistent/exts/msp.orms.runtime/interior_sets/slots/<slot>/sets/<set_id>/selectors
/persistent/exts/msp.orms.runtime/interior_sets/slots/<slot>/sets/<set_id>/atlases/xN/directory
/persistent/exts/msp.orms.runtime/interior_sets/slots/<slot>/sets/<set_id>/material/<input_name>
```

The repository writes one complete inactive `a` or `b` slot and flips
`active_slot` only after that write succeeds. The preceding active slot remains
available for runtime rollback; a slot is cleared before it is reused so
removed Set subtrees cannot survive as stale active configuration.

Global geometric classifier settings remain global. They are not copied into
each Interior Set.

On the first compatible start, migration must:

1. detect the absence of the new schema;
2. create the reserved Default Interior Set;
3. copy the existing global x1-x4 production directories into Default;
4. copy every existing global material value into Default;
5. preserve the current Default name and empty specific-selector list;
6. write the new schema version only after the complete migration succeeds;
7. leave the legacy values readable for rollback during this release boundary;
8. preserve the existing resolved atlases, material values, and single-family
   results; legacy cross-family rooms with unverified or incompatible variant
   identity use the explicit coherence diagnostic and safe grouping fallback.
9. infer `Production` when a legacy snapshot contains at least one production
   directory, preserving its visual result; otherwise initialise `Debug`.

Migration is idempotent. Restarting after success must not create another
Default Set, generate a new ID, reorder Sets, or overwrite later edits.

### Editing transaction model

Interior Set structural edits are staged locally and committed through one
explicit `Apply Interior Sets` action. Material controls remain live.

- The UI owns a mutable draft and the service owns the last applied immutable
  Interior Set snapshot.
- Selector text, production atlas paths, order, Add, Duplicate, and Remove edit
  only the draft. Typing a partial mask or path must not write persistent
  settings, reclassify the stage, recreate materials, or touch Session Layer
  state.
- The global `Debug`/`Production` atlas mode is structural draft state and is
  committed atomically with the same `Apply Interior Sets` action.
- Add, Apply, and Revert remain directly below the atlas-mode selector, above
  the repeatable Set list, so their location does not move as Sets accumulate.
- A dirty-state indicator distinguishes the draft from the applied runtime.
  `Revert unapplied changes` restores the draft from the applied snapshot.
- `Apply Interior Sets` validates the complete candidate collection before any
  runtime mutation. Invalid UUIDs, order, Default ownership, and selector
  syntax reject the candidate as one unit. Missing or invalid production
  resources remain explicit per-family diagnostics and resolve through the
  matching packaged fallback.
- One successful Apply persists one coherent configuration and requests one
  controlled runtime rebuild. Intermediate field edits must never schedule
  independent rebuilds.
- If persistence or rebuild fails, ORMS restores the preceding applied settings
  and runtime snapshot. If runtime restoration also fails, the lifecycle enters
  the existing recoverable `Failed` state while source USD remains unchanged.
- Remove is confirmed in the draft, but persistent Set data and runtime state
  are deleted only by a successful Apply.
- Rename is live for an already applied Set: it updates persistent presentation
  data and UI labels without reclassification or material recreation. Renaming
  a staged new Set remains part of its draft until Apply.
- Material controls are live for already applied Sets and update only that
  Set's active x1-x4 materials. Material edits on a staged new or duplicated Set
  remain draft values until the Set is applied.
- `emission_strength` accepts any finite non-negative value. It has no
  arbitrary upper bound because useful scene exposure can require values in
  the thousands.
- Closing or rebuilding the window with a dirty draft requires an explicit
  Apply or Revert decision; it must not commit structural changes implicitly.

### Portable scene profiles

Persistent Kit settings remain the local user's active default, but different
USD scenes and buildings may require different Set libraries, selectors,
atlases, and material profiles. ORMS therefore also supports a manually chosen
portable scene-profile file with the `.orms` extension.

- `.orms` is a human-readable UTF-8 JSON document behind a domain-specific
  extension. It contains an explicit format marker and independent schema
  version; it is never executable Python, pickle, or source USD.
- Schema 1 stores the applied atlas mode and the complete ordered Interior Set
  collection: immutable UUIDs, display names, selectors, x1-x4 production
  directories, and every material value.
- `Save Profile...` always opens Kit's Save dialog, appends `.orms` when needed,
  and serialises the last applied snapshot to the confirmed destination. It
  never requires a path to be entered or selected beforehand. If a structural
  draft is dirty, the UI reports that those unapplied edits were not included.
- `Load Profile...` always opens Kit's Open dialog. Confirming a file parses and
  validates the whole profile, then replaces only the local Interior Set draft
  as one structural revision. Persistent settings, runtime materials, bindings,
  and Session Layer state remain unchanged until the normal
  `Apply Interior Sets` action succeeds.
- Load validation covers the file marker and schema, `.orms` suffix, mandatory
  Default identity and order, unique UUIDs, selector syntax, x1-x4 path types,
  atlas mode, known material names, value types, vector lengths, finite numbers,
  and accepted material ranges.
- Save uses a temporary sibling file followed by atomic replacement so an
  interrupted write does not leave a partially written target profile.
- Profile choice is manual and source-safe. ORMS does not author the profile
  path or its data into the USD scene and does not infer a local file from a
  source asset path.
- Schema 1 deliberately scopes import/export to Interior Sets and atlas mode.
  Global geometric classifier controls remain live process settings because
  importing them immediately would split one profile load across two different
  transaction models. A later schema may include classifier controls only after
  they join the same staged, validated, atomic Apply boundary.

### Source and lifecycle ownership

- Set configuration is user-local persistent Kit state, not source USD data.
- Resolved `interior_set_id`, generated material families, material bindings,
  subsets, and diagnostics are ORMS-owned ephemeral Session Layer state.
- Source USD layers, source material bindings, source primvars, and unrelated
  Session Layer opinions remain unchanged.
- Stop, restore, stage replacement, extension disable, Set removal, reorder,
  restart, and in-process upgrade must release or rebuild only state owned by
  the active ORMS service.
- Removing a non-default Set marks it for deletion in the draft. A successful
  `Apply Interior Sets` deletes its persistent configuration and rebuilds its
  formerly selected windows through the remaining specific Sets or Default.
- The Default Set cannot be removed through UI or service commands.

## Phased implementation plan

### Phase 1 — Freeze the current baseline and define plain-data contracts

1. Add a Default-only characterisation test around the accepted single-profile
   settings, resource selection, material values, grouping, bindings, and
   lifecycle result.
2. Define immutable plain-data contracts for `InteriorSetConfig`, ordered Set
   collections, selector results, per-Set resources, per-Set material values,
   and diagnostics.
3. Define the reserved Default UUID, UUID validation, path-safe runtime token,
   schema version, settings paths, fallback-label rules, draft/applied states,
   and the minimal variant-identity manifest.
4. Add `interior_set_id` to aperture, room-group, and derived-mapping contracts
   without introducing a Kit or `pxr` dependency into the pure classifier.
5. Include `interior_set_id` in stable room-group identity so equal `roomID`
   values in different Sets cannot collide.

### Phase 2 — Implement persistent storage and backward-compatible migration

1. Add a settings repository that owns schema loading, typed defaults, ordered
   Set IDs, create, duplicate, rename, selector edit, reorder, and non-default
   removal.
2. Store material and atlas values beneath immutable Set IDs.
3. Preserve global classifier settings in their current shared location.
4. Implement the one-time migration from the current global atlas and material
   keys into Default.
5. Make migration transactional at the schema-version boundary and safe to
   repeat after an interrupted start.
6. Separate the mutable UI draft from the immutable applied snapshot and expose
   one validated settings commit operation.
7. Test empty settings, legacy settings, already migrated settings, malformed
   IDs, stale order entries, interrupted Apply, and attempts to remove Default.
8. Define the independent versioned `.orms` JSON interchange schema and pure
   serializer/parser. Preserve UUIDs and order, fill newly introduced known
   material controls from defaults, and reject unknown schema versions or
   invalid values before staging.

### Phase 3 — Resolve Interior Sets before geometric grouping

1. Add one deterministic selector resolver operating on composed candidate mesh
   paths.
2. Return the winning `set_id`, winning mask, all conflicting matches, and
   whether Default fallback was used for every compatible aperture.
3. Resolve each unique mesh path once and apply the result to its extracted
   apertures.
4. Pass the enriched aperture collection through the existing single
   classifier invocation.
5. Update topology and grouping boundaries so apertures with different Set IDs
   never share an edge, run, corner, or derived room.
6. Preserve all existing geometry fallbacks, instance policy, stage-metric
   handling, `roomID` behaviour, partition seed, and x1-x4 limits.

### Phase 4 — Resolve per-Set atlas families and runtime materials

1. Replace the single selected atlas tuple with an ordered per-Set resource
   snapshot keyed by `set_id`.
2. Overlay each Set's production x1-x4 directories on the one packaged debug
   inventory independently.
3. Apply the global staged resource policy first: Debug selects every packaged
   family unconditionally; Production resolves each Set-local production
   family and falls back only its missing xN family.
4. Report authored directory, resolved asset, variant count, source kind,
   availability, fallback reason, and validation error for every `(set_id,
   room_size)` pair.
5. Load and validate ordered semantic variant IDs across production families;
   attach the shared built-in identity sequence to packaged debug families.
6. Resolve one semantic variant per room group and prove that every facade leg
   consumes the same identity even when its atlas sizes differ.
7. Prevent an incoherent family combination from creating a cross-family room;
   emit one diagnostic and use the accepted safe grouping fallback.
8. Replace the global x1-x4 material map with a map keyed by `(set_id,
   room_size)`.
9. Author path-safe material prims from immutable IDs and attach display labels
   separately.
10. Bind each aperture or generated subset to the material selected by its
   derived Set ID and atlas size.
11. Apply material changes only to one Set's active family and retain one
   committed update per affected material.

### Phase 5 — Integrate the single service and source-safe lifecycle

1. Extend the existing service snapshot and rebuild input with the ordered
   Interior Set configuration.
2. Keep one settings window, service, lifecycle state machine, classifier,
   camera bridge, assignment owner, and teardown path.
3. Keep live rename and targeted live material updates outside the structural
   rebuild path.
4. Stage selector, atlas, order, Add, Duplicate, and Remove changes without
   changing persistent settings or the running scene.
5. Validate and commit one complete draft through `Apply Interior Sets`, then
   schedule exactly one controlled rebuild and retarget the existing camera
   bridge to the rebuilt material-family inputs.
6. Roll back both settings and runtime to the preceding applied snapshot when a
   commit or rebuild fails.
7. Coalesce runtime work and cancel superseded tasks without duplicate
   callbacks, materials, subscriptions, or Session sublayers.
8. Re-resolve selectors on stage replacement and relevant composed-stage
   changes while filtering ORMS-authored changes from invalidation.
9. Prove stop, restore, restart, reload, disable/re-enable, removal, and reorder
   leave source USD unchanged and return one coherent runtime owner.

### Phase 6 — Build repeatable Interior Set UI

1. Replace the global production-atlas block with repeatable Interior Set
   blocks in `Interior Atlases`.
2. Pin Default visibly, label it as the fallback, allow renaming, and omit its
   Remove action.
3. For each Set, expose Name and x1-x4 production folders with directory
   pickers and direct text editing. Expose one-mask-per-line target paths only
   for specific Sets; explain unconditional fallback inside Default.
4. Add `+ Add Interior Set`, `Duplicate Interior Set`, Remove, Move Up, and Move
   Down actions. Add inherits a snapshot of Default's material profile while
   starting with empty selectors and atlas paths. Duplicate copies the selected
   Set's editable configuration but creates a new UUID.
5. Reorder controls affect specific Sets only and explain that order defines
   selector priority.
6. Mark structural edits as unapplied and provide `+ Add Interior Set`,
   `Apply Interior Sets`, and `Revert unapplied changes` directly below Atlas
   mode and above the Set list. No structural text field or list action may
   invoke classification directly.
7. Add one staged global `Debug` / `Production` selector. Debug forces the
   packaged x1-x4 inventory for every classified window; Production uses
   Set-local production families with matching packaged fallbacks. Changing
   this selector requires `Apply Interior Sets`. Use the same explicit visual
   choice language as the main tabs: the selected option is dark and inactive
   neighbours are visibly lighter grey.
8. Keep the four read-only packaged debug x1-x4 paths visible as an independent
   global diagnostic inventory, even when every Set has production overrides.
   Show the resolved production/debug choice independently for every Set and
   family without copying debug paths into per-Set persistent data.
9. Show family coherence state and the ordered semantic variant count for each
   Set, with actionable mismatched-manifest feedback.
10. Rebuild `Material Parameters` as repeatable per-Set groups containing Room,
   Window, Depth Slices, Glass, Diagnostics, and Emission.
11. Keep applied-Set material controls live and scoped to their own materials;
    keep controls for new staged Sets local until Apply.
12. Use `ORMS N` fallback labels for blank names and keep labels independent from
   runtime identity.
13. Rebuild only the window content through OmniUI's deferred `Frame.rebuild`
   path after add, remove, reorder, reload, or in-process extension upgrade.
   Preserve the selected tab and the docked window itself. Preserve Atlas mode
   and every Interior Set block's collapsed state by immutable `set_id`, so
   reorder and rename cannot transfer or reset presentation state. Every
   collapsible section across all three tabs uses content-sized layout,
   releases hidden content from the scroll extent, and retains state across UI
   rebuilds by a stable semantic key or Set UUID.
14. Add `Scene ORMS profile (.orms)` directly below the global packaged-debug
    paths with exactly two direct actions: Save Profile and Load Profile. Each
    action opens the appropriate Kit dialog and completes its operation after
    confirmation; no prerequisite path field or duplicate Save As workflow is
    exposed. Keep picker and file-I/O workflow modules outside the
    settings-window owner.

### Phase 7 — Add actionable diagnostics

Expose a stable diagnostic snapshot containing:

- active Interior Set count and ordered IDs/labels;
- compatible aperture count per Set;
- each winning selector and match count;
- selector conflicts with prim path, winning Set, and all matching specific
  Sets;
- Default-fallback apertures;
- x1, x2, x3, and x4 room counts within each Set;
- production or packaged-debug resource selection per Set and family;
- variant namespace, ordered semantic IDs, and cross-family coherence state;
- generated material paths and targeted material-update counts;
- draft/applied revision, dirty state, Apply or rollback result, migration
  result, malformed configuration, missing resources, and lifecycle recovery
  state.

Publish the complete snapshot to the structured ORMS log rather than a
developer-oriented UI dump. Keep only concise artist-actionable messages in
the panel: selector conflicts, invalid masks, invalid resources, failed Apply,
and fallback transitions. Internal paths, counters, migration detail, and
lifecycle traces must not consume permanent space in the artist workflow.

### Phase 8 — Automated and renderer validation

Add automated coverage for at least:

1. Default-only configuration reproduces current behaviour and visual inputs.
2. `*/Kitchens_Windows` selects matching meshes in multiple buildings.
3. Multiple masks inside one Set use OR matching.
4. A specific selector beats Default.
5. UI order deterministically resolves overlapping specific selectors and
   produces one conflict diagnostic.
6. Different Interior Sets cannot merge into one shared room even when
   `roomID` and all geometry conditions match.
7. Material changes in one Set do not affect another Set.
8. Production-atlas fallback operates independently per Set and per x1-x4
   family.
9. Renaming a Set preserves its internal identity, settings, generated material
   paths, and bindings.
10. Remove, reorder, restart, stage reload, restore, and extension reload retain
    correct ownership and leave source USD unchanged.
11. Migration from the global profile is idempotent and produces an equivalent
    Default-only runtime.
12. Blank names produce stable UI fallback labels without becoming persistent
    identity.
13. Material count grows only with active `(set_id, room_size)` pairs and the
    five-lookup shader budget remains unchanged.
14. Partial selector and atlas-path typing, Add, Duplicate, Remove, and reorder
    do not alter persistent settings, trigger classification, or touch Session
    Layer state before `Apply Interior Sets`.
15. One valid Apply commits one complete draft and produces exactly one
    controlled rebuild; invalid Apply and rebuild failure preserve or restore
    the preceding applied snapshot.
16. Material controls remain live and Set-scoped, while renaming an applied Set
    changes presentation without recreating runtime materials.
17. `+ Add Interior Set` inherits the current Default material profile but uses
    a new UUID, empty selectors, and empty production atlas directories.
18. `Duplicate Interior Set` copies editable configuration but never copies
    runtime identity or Session Layer ownership.
19. A corner using x4 on one facade and x1 on the other resolves the same
    semantic `variant_id` and index in both families.
20. Mismatched counts, reordered IDs, missing manifests, and incoherent
    production/debug combinations produce diagnostics and cannot create a
    semantically mismatched cross-family room.
21. Separately exported Houdini mesh prims such as `/LivingRoom_Windows`,
    `/Kitchens_Windows`, and `/Shop_Windows` resolve independently, while one
    `/Building/Windows_Glass` mesh cannot be divided by face or subset.
22. A legacy `Windows_Glass` mesh and semantic child meshes below a `windows`
    container pass the same global auto-assignment boundary; unrelated meshes
    remain untouched.
23. Applying or reverting a structural edit preserves the active tab, never
    destroys a window during an OmniUI event, and leaves the independent global
    packaged-debug paths visible.
24. Debug mode ignores configured production paths and selects packaged x1-x4
    for every Set; Production mode uses valid Set-local families and falls back
    independently for each absent xN family. The mode changes only on Apply and
    survives restart in the same atomic snapshot.
25. Collapsing any Interior Set block, then adding, duplicating, removing,
    reordering, applying, reverting, or refreshing runtime diagnostics retains
    the collapsed state of every surviving block by `set_id`.
26. An applied selector conflict remains visible as a concise inline warning
    and names the composed prim path, every competing Set, and the
    top-to-bottom priority winner; full details remain in the ORMS log.
27. A `.orms` save/load round trip preserves UUIDs, Set order, names, selectors,
    x1-x4 directories, atlas mode, and the complete material profiles.
28. Loading a valid `.orms` file creates one dirty draft revision without
    touching persistent settings, runtime callbacks, Session Layer state, or
    source USD before Apply.
29. Wrong suffixes, malformed JSON, unknown schema versions or material names,
    duplicate or invalid UUIDs, invalid Default order, invalid masks, non-finite
    values, wrong vector lengths, and out-of-range material values are rejected
    without changing the current draft.
30. Save with a dirty draft exports the applied snapshot and reports the
    exclusion; Save Profile appends `.orms`, and an interrupted write preserves
    the preceding complete file.
31. Emission Strength accepts finite non-negative values above 100, including
    values around 10,000, in both live controls and `.orms` profiles.
32. Applying a newly added Set retargets the existing camera bridge to its
    authored x1-x4 shader inputs; parallax works without pressing Restart.
33. Collapsing lifecycle, classifier, material Set, nested material group,
    profile, atlas-mode, or atlas Set sections releases their content height
    immediately. Structural rebuilds preserve the state of all surviving
    sections without adding blank scrollable regions.
34. The active main tab and selected Debug/Production atlas mode use a dark
    selected background; inactive sibling choices use a lighter grey
    background and update immediately when selection changes.

Retain `tests/shared_room_runtime/test_room_map_interior_sets_omniverse.usda`
as the compact fixture containing Default living rooms, kitchens selected
through one mask, shops selected through an overlapping pair of masks, and a
Set using multiple explicit masks. Validate assignment, grouping, per-Set
material edits, independent atlas fallback, camera response, restart, and
source restoration. Final visual acceptance remains required in RTX Real-Time
and RTX Interactive (Path Tracing) after the automated contract passes.

## Installed-runtime defect and correction record — 3–4 September 2026

This record is part of the KRM-92 delivery evidence. It separates confirmed
implementation defects from invalid production content and records the exact
correction boundary. Automated acceptance does not replace the pending live
renderer retest of the latest package.

### 1. Packaged extension could not import the shared runtime — 0.1.6

- **Observed:** registry-installed startup failed with
  `No module named 'tools.omniverse.interior_sets'`, then
  `No module named 'tools.omniverse'`.
- **Cause:** `extension.py` imported `service.py` before adding the packaged
  `data/runtime` tree to `sys.path` and constructing the bundled
  `tools.omniverse` namespace. The source checkout accidentally supplied that
  namespace during tests, but a clean registry installation did not.
- **Correction:** 0.1.7 bootstraps the packaged runtime before importing the
  service. The extension no longer depends on a neighbouring repository
  checkout.

### 2. Apply destroyed the UI during an OmniUI callback — 0.1.7

- **Observed:** `Apply Interior Sets` emitted
  `Container::destroy was called during an event or draw`, destroyed the
  settings window, and returned the artist from `Interior Atlases` to
  `ORMS Classifier`.
- **Cause:** structural actions called `_window.destroy()` and recreated the
  complete docked window synchronously from a button callback. The recreated
  window also lost the selected-tab state.
- **Correction:** 0.1.8 retains the window, stores the active tab, and requests
  a deferred content-only `Frame.rebuild()`.

### 3. Global packaged-debug controls disappeared — 0.1.6/0.1.7

- **Observed:** the repeatable Interior Set UI exposed production directories
  but no independent read-only x1-x4 packaged-debug paths.
- **Cause:** the first panel replacement treated debug atlases only as an
  internal fallback and omitted their established global inspection surface.
- **Correction:** 0.1.8 restores the four global packaged paths. They are not
  copied into any Set and remain available independently of production data.

### 4. Semantic child meshes never reached selector matching — 0.1.7

- **Observed:** a mask such as `*/living_rooms` matched the composed USD path
  visible in Stage, but no ORMS material appeared on the mesh.
- **Cause:** selector evaluation ran only after the global compatibility gate;
  that gate recognised the legacy `Windows_Glass` identity and explicit
  opt-in, but filtered semantic child meshes exported below a `windows`
  container before their paths could be matched.
- **Correction:** 0.1.8 extends the one global eligibility boundary to those
  semantic child meshes. It does not add semantic per-room classifiers. An
  explicitly stopped runtime remains stopped by design until `Start`.

### 5. Reloaded resources were mistaken for filesystem paths — 0.1.8

- **Observed:** stage activation failed with
  `TypeError: argument should be a str or an os.PathLike object where fspath
  returns a str, not 'RuntimeResources'`.
- **Cause:** exact-source reload replaced the Python class object. A resource
  record created by the preceding module generation failed the new
  `isinstance` check and fell into the path-coercion branch.
- **Correction:** 0.1.9 rehydrates resource records at the reload boundary
  instead of relying on cross-generation class identity.

### 6. Debug could not be forced independently from production — 0.1.8

- **Observed:** packaged debug atlases existed only as missing-family fallback,
  so the extension itself could not be tested with a guaranteed all-debug
  resource policy.
- **Cause:** no explicit global resource mode existed after the per-Set
  conversion.
- **Correction:** 0.1.9 adds staged `Debug (force packaged)` and
  `Production + debug fallback` modes. The mode is committed only by
  `Apply Interior Sets`.

### 7. Production directory Browse used incompatible and file-oriented APIs — 0.1.8/0.1.9

- **Observed:** Kit 1.1.21 rejected `click_cancel_handler`; after that callback
  mismatch was removed, selecting an existing directory still produced
  `room_maps is not valid` because the final directory component populated the
  filename field.
- **Cause:** the picker used a callback keyword not accepted by the installed
  `FileImporterExtension.show_window()` and then opened a directory as if it
  were an import-file selection.
- **Correction:** 0.1.9 adopts the installed callback contract. 0.1.10 opens at
  the full current directory, leaves the filename field empty, and commits the
  selected directory rather than validating a synthetic file path.

### 8. Collapsed diagnostics reopened and retained blank height — 0.1.10

- **Observed:** any panel rebuild reopened diagnostics; when manually collapsed,
  the frame left a large empty region in the layout.
- **Cause:** the frame was recreated with default state on every rebuild and
  retained a fixed content height while collapsed.
- **Correction:** 0.1.11 stores the artist's diagnostics state for the window
  lifetime and uses computed `height=0` layout behaviour.

### 9. Default x1 ignored its selected Interior Set atlas — 0.1.10

- **Observed:** windows continued to sample the legacy
  `assets/_external/tex/room_maps` x1 atlas while the Default Set displayed and
  applied a different production x1 directory.
- **Cause:** the authoring fallback deliberately preserved the source
  material's x1 atlas for both legacy mode and the new Default Set. That
  backward-compatibility branch incorrectly overrode explicit Default Set
  resource resolution.
- **Correction:** 0.1.11 preserves the source x1 atlas only when no Interior
  Set snapshot exists. Every explicit Set, including Default, now consumes its
  resolved runtime resource.

### 10. One invalid production family rejected the complete transaction — 0.1.10

- **Observed:** a malformed or incomplete xN folder prevented Apply, left the
  preceding configuration active, and made unrelated valid Set changes appear
  ineffective.
- **Cause:** the resource resolver already produced an independent packaged
  fallback, but the controller treated its retained validation diagnostic as a
  transaction-wide structural error.
- **Correction:** 0.1.11 commits the valid structural snapshot, uses packaged
  debug only for the invalid family, and keeps the exact resource error visible.
- **Content incident:** one Cabinets x4 sequence initially violated the naming
  contract. Renaming that asset sequence fixed the content; this was not an
  ORMS code defect.

### 11. Interior Set blocks lost collapsed state after reorder — 0.1.11

- **Observed:** collapsing the first Set and moving another Set up rebuilt the
  panel with the first Set expanded again.
- **Cause:** diagnostics state was retained, but every Set frame was still
  recreated with its default expanded state. Visible list position could not
  safely identify a Set across reorder.
- **Correction:** 0.1.12 stores block state in a dedicated transient UI-state
  owner keyed by immutable `set_id`; Add, Duplicate, Remove, reorder, Apply,
  revert, and diagnostics refresh retain each surviving block independently.
  Atlas mode state is retained through the same boundary. Automated UI tests
  pass; installed live retest remains pending.

### 12. A higher-priority duplicated selector silently stole Cabinets — 0.1.11

- **Observed:** after adding Living Rooms, Cabinets lost parallax even though
  its production folders remained configured.
- **Cause:** the applied collection contained two specific Sets matching
  `/Moskovskiy_av_150/geo/render/windows/cabinets`. The earlier Living Rooms Set
  won by the documented top-to-bottom rule. The retained log reports one
  conflict, assigns all 24 cabinet apertures to Set `66e8c3e4-...`, authors its
  `01_living_rooms` atlases, removes the now-unused Cabinets materials for Set
  `8f83bb37-...`, and rebinds the cabinets mesh. This was deterministic selector
  priority, not a classifier or parallax failure; the UI failed to make the
  consequence sufficiently visible.
- **Correction:** 0.1.12 keeps the required first-match rule but shows every
  applied conflict above the collapsed diagnostics block, including the prim
  path, competing Set labels, and winner. Runtime phase logs now include the
  same ownership details instead of only `selector_conflict_count`. To restore
  the intended scene configuration, Living Rooms must use its own mask such as
  `*/living_rooms`; Cabinets retains `*/cabinets`.

### Scope addition. Portable scene profiles — 0.1.13

- **Requirement:** different scenes and buildings need different ORMS Set,
  selector, atlas, and material configurations; one process-local persistent
  snapshot is not a portable scene workflow.
- **Decision:** expose direct Save Profile and Load Profile actions below the
  packaged debug paths. Each action owns its file-dialog step and completes the
  requested operation after confirmation. The custom extension makes the asset
  recognisable while the contents remain versioned, human-readable JSON.
- **Transaction boundary:** selection never loads implicitly, loading never
  applies implicitly, and saving never includes an uncommitted draft. Imported
  data reaches persistent settings and Session Layer output only through the
  existing `Apply Interior Sets` transaction.
- **Implementation:** 0.1.13 separates schema/I/O, Kit picker integration,
  presentation, and workflow coordination into dedicated modules. Automated
  round-trip, validation, picker-contract, and no-auto-Apply tests pass;
  installed live acceptance remains pending.

### 13. Profile saving exposed an internal two-step workflow — 0.1.13

- **Observed:** `Save Applied` failed with `Choose an ORMS scene profile path
  first`; the panel exposed a path field, Browse, Load to Draft, Save Applied,
  and Save Applied As even though the artist operation requires only Save and
  Load. Save As also failed when Kit invoked its callback with the named
  `selections` argument.
- **Cause:** the UI surfaced the workflow's internal path state as a required
  artist step and duplicated Save versus Save As. The exporter callback named
  its fourth parameter `_selections`, so it rejected Kit's real keyword call;
  the original test covered only a positional call and missed the mismatch.
- **Correction:** 0.1.14 removes the path field and all intermediate actions.
  `Save Profile...` opens the Save dialog and writes immediately after
  confirmation; `Load Profile...` opens the Open dialog and stages immediately
  after confirmation. The callback now accepts the exact `selections` keyword,
  and the regression test invokes it by the same named arguments as Kit.

### 14. Scene profiles rejected practical emission values — 0.1.14

- **Observed:** loading a valid artist profile failed with
  `Material value 'emission_strength' is above 100.0` when the scene required
  a value near 10,000 for visibly emissive interiors.
- **Cause:** the shared material-control description imposed an arbitrary
  maximum of 100. The same metadata clamped the live field and rejected the
  otherwise finite profile value.
- **Correction:** 0.1.15 removes only the upper bound. Emission Strength remains
  numeric, finite, and non-negative; live editing and profile loading now share
  that contract.

### 15. Structural actions moved with the end of the Set list — 0.1.14

- **Observed:** Add, Apply, and Revert were rendered after every Set block, so
  applying edits required scrolling to the bottom whenever the collection grew.
- **Cause:** the action row was appended after the repeatable Set loop even
  though the actions belong to the global transaction and atlas-mode policy.
- **Correction:** 0.1.15 places the single action row immediately below Atlas
  mode and above the repeatable Set list.

### 16. Newly added Sets required a manual runtime Restart — 0.1.14

- **Observed:** after applying Library and later Halls, their materials and
  bindings existed but parallax remained inactive until `Restart` was pressed
  on the Classifier tab.
- **Cause:** structural Apply rebuilt the classifier layer and authored the new
  per-Set shader inputs, while the existing camera bridge retained the fixed
  input-path list captured at initial runtime start. The new families therefore
  received no live `camera_position_world`; Restart recreated the bridge with
  the expanded list.
- **Correction:** 0.1.15 keeps the same runtime session and, after a successful
  structural rebuild, replaces the bridge's explicit target list. Its cached
  camera value is invalidated so the next Kit update seeds every new family.
  Removing or reordering Sets updates the same list without a full runtime
  teardown.

### 17. Collapsed sections retained a full blank scroll region — 0.1.15

- **Observed:** collapsing a Set on `Material Parameters` hid its controls but
  left a window-sized empty scroll region. Classifier sections and nested
  material groups used the same unsafe construction, while some Atlas sections
  already behaved correctly.
- **Cause:** collapsible frames were created independently across several UI
  modules. Only the previously corrected Atlas-specific frames requested
  computed `height=0`; the others inherited stretch sizing inside the tab
  stack. Classifier and material frames also had no stable state owner, so a
  content rebuild could reopen them.
- **Correction:** 0.1.16 makes one shared content-sized helper the only direct
  `CollapsableFrame` construction point for all three tabs. Classifier sections
  use stable semantic keys; material Set and nested group state includes the
  immutable Set UUID. Removing a Set drops its presentation state, while Add,
  Duplicate, reorder, Apply, revert, and diagnostics refresh preserve every
  surviving choice. A source-inventory regression test rejects future direct
  frame construction outside the helper. Installed live layout acceptance
  remains pending.

### 18. Active tab and atlas mode were visually ambiguous — 0.1.15

- **Observed:** all three main tab headers appeared to have the same dark
  background, so the active tab was clear only after reading the controls
  below it. Debug and Production mode buttons had the same ambiguity.
- **Cause:** the widgets updated OmniUI's `selected` flag correctly, but the
  host theme did not provide enough background contrast for that state.
- **Correction:** 0.1.16 routes both mutually exclusive button groups through
  one selection-button helper. Inactive choices use a lighter grey background;
  selected and pressed choices remain dark, with a separate hover state. The
  existing selected flags still own state, so the appearance follows tab and
  staged atlas-mode changes without duplicating selection logic.

### 19. Full runtime diagnostics occupied the artist workflow — 0.1.16

- **Observed:** the collapsed `Applied runtime diagnostics` header remained on
  the Interior Atlases tab even after its layout behaviour was corrected. Its
  internal counters and generated paths are useful for engineering diagnosis,
  but not for normal atlas authoring.
- **Cause:** the initial implementation exposed the complete diagnostic model
  directly in the artist panel instead of separating engineering evidence from
  actionable configuration feedback.
- **Correction:** 0.1.17 removes the full diagnostics section and its transient
  collapse state from the UI. The diagnostic snapshot and phase evidence stay
  in the ORMS log. Selector conflicts remain concise inline warnings because
  they identify an artist-correctable priority problem; per-family resource
  errors and fallback state remain beside the affected Set.

### 20. Renderer telemetry reported zero per-Set materials — 0.1.17

- **Observed:** the installed-session log recorded
  `RUNTIME_MATERIALS_AUTHORED material_count=20`, but later resource snapshots
  repeatedly reported `runtime_material_count=0` while those materials were
  visibly rendering.
- **Cause:** the low-rate renderer probe still counted only Material prims
  directly below `/__ORMSRuntime/Looks`, matching the former global-family
  layout. Interior Sets place them one level deeper under stable
  `Set_<internal_id>` scopes.
- **Correction:** 0.1.18 traverses the complete ORMS Looks subtree and counts
  both the legacy flat layout and per-Set material families. This is a
  telemetry correction; runtime authoring and rendering were already valid.

### Open installed-runtime findings after 0.1.16 acceptance

- **Fabric string-array warning:** `primvars:ormsInteriorSetId` is authored as
  a uniform `StringArray`, while Fabric does not support string-array primvars.
  USD and Hydra continued rendering correctly in the accepted session. The
  cause is the diagnostic semantic ID following the same per-face array shape
  as numeric derived data even though one mesh resolves to one Interior Set.
  This has not yet been corrected; replace it with a Fabric-safe constant
  representation without weakening Session Layer ownership or diagnostics.
- **Status trace severity/noise:** the stage-load probe emitted 112 structured
  trace blocks at Warning level during the captured session. The cause is the
  shared status sink routing routine progress and heartbeats through
  `carb.log_warn`. This has not yet been corrected; normal phase evidence must
  use Info/Debug severity and reserve Warning for actionable anomalies.
- **Hot-version shutdown reference:** disabling installed 0.1.15 before
  enabling 0.1.16 reported that the extension object remained referenced by
  two Python frames. Startup of 0.1.16 still succeeded. This has not been
  reproduced as a normal shutdown failure; verify 0.1.18 disable/re-enable and
  fix lifecycle ownership if the reference warning persists outside a hot
  version replacement.
- **Production variant manifests are absent:** the five configured production
  packs have equal x1-x4 tile counts within each Set, but none currently ships
  `orms_variants.json`. The resource validator therefore cannot prove ordered
  semantic identity across families and reports missing identity metadata.
  This is an external-content acceptance gap, not a classifier defect. Publish
  truthful namespace and ordered variant IDs for every production family
  before accepting cross-family corner identity in production mode.
- **Saved Library x3 path points at x2:** the captured runtime and the saved
  `test_150.orms` profile both resolve Library x3 to the `library_x2` directory.
  The picker and loader are preserving the applied value as designed; the
  profile data itself is wrong. Correct Library x3 to `library_x3`, Apply, and
  save the profile again.

### Phase 9 — Reassess the original KRM-92 UI scope

After Interior Sets are accepted, review every item in the deferred original
scope below and classify it as:

- retained without change;
- retained but rewritten for per-Set behaviour;
- already delivered by the Interior Set work;
- obsolete because it assumes one global atlas or material profile; or
- deferred to a separate task.

Only then finalise the remaining KRM-92 artist-workflow pass. Do not implement
the old plan mechanically against an architecture it no longer describes.

The reassessment after installed 0.1.16 acceptance is:

| Original KRM-92 area | Classification | Evidence and remaining action |
| --- | --- | --- |
| Panel hierarchy, retained collapse state, active-tab contrast | Already delivered | All three tabs use shared content-sized collapsible sections; tab and atlas-mode selection have explicit contrast. |
| Runtime state and action availability | Partially delivered | State and enabled actions are visible. Concise artist-facing explanations of Start, Stop, Restart, and Restore Original Asset are still missing. |
| Classifier labels and x1 fallback explanation | Retained, incomplete | Existing groups remain usable, but the UI does not explain that disabling x2-x4 reclassifies through x1. |
| Automatic-assignment inspection and `orms:autoAssign` override | Retained, not delivered | The runtime contract exists, but artists still cannot inspect, exclude, or restore mesh assignments from the ORMS UI. |
| Material organisation | Retained but rewritten per Set | Complete material profiles are grouped per Interior Set and update only that Set's x1-x4 family. |
| Material reset and inline validation feedback | Retained, not delivered | No per-group/per-Set reset affordance or dedicated inline failure feedback exists. |
| Atlas pickers, validation, fallback status, and controlled Apply | Retained but rewritten per Set; delivered | Direct editing and directory selection, per-family production/debug resolution, inline validation, staged edits, and explicit Apply are implemented. |
| Per-family and full atlas reset | Retained, not delivered | Reverting an unapplied draft is not the same as intentionally clearing one family or resetting the complete applied atlas configuration. |
| Extension Manager overview | Retained, not delivered | The packaged README still leads with module ownership, packaging, and developer commands instead of first-use artist guidance. |
| Installed renderer acceptance | Partially delivered | 0.1.16 was accepted on the retained five-Set scene in RTX Interactive; the final 0.1.18 package still needs the documented two-renderer acceptance pass. |

**Phase 9 verdict:** the Interior Sets architecture and workflow additions are
functionally delivered, but KRM-92 as a whole is not ready for Done. The
remaining artist-facing items above must either be implemented in KRM-92 or
explicitly split into follow-up issues before the Jira task is closed.

## Acceptance boundary

KRM-92 is ready for final UI-scope reassessment when:

- one installed ORMS runtime manages N Interior Sets through one classifier;
- selector precedence and Default fallback are deterministic and observable;
- room grouping never crosses an Interior Set boundary;
- atlases and complete material profiles are independent per Set;
- x1-x4 families preserve one semantic variant identity across shared corners;
- structural edits reach settings and Session Layer state only through one
  successful `Apply Interior Sets`, while applied material controls remain live;
- Add inherits Default material values and Duplicate preserves editable setup
  without reusing identity;
- portable `.orms` profiles round-trip the complete applied Interior Set
  snapshot and load only into staged state before Apply;
- rename and reorder preserve immutable identity;
- legacy single-profile settings migrate to an equivalent Default-only result;
- generated materials, bindings, and `interior_set_id` remain reversible
  ORMS-owned Session Layer state;
- the required automated matrix passes; and
- the retained mixed-Set fixture is visually accepted in both RTX modes.

## Risks and explicit boundaries

- Material and USD prim counts scale with active Sets and room sizes. Record
  those counts before making performance claims; do not impose an arbitrary Set
  limit without evidence.
- Path-level selection means one mesh cannot assign different Interior Sets to
  different faces in this version. Houdini must export semantic groups as
  separate mesh prims such as `/LivingRoom_Windows`, `/Kitchens_Windows`, and
  `/Shop_Windows`. Face and GeomSubset selectors belong to the ORMS 2.0 epic,
  not KRM-92.
- The resource validator can prove declared ID/count/order compatibility, not
  visual similarity between images. Atlas publishing remains responsible for
  assigning truthful semantic IDs.
- Display names are not unique identifiers and duplicate names are allowed;
  diagnostics must include the stable ID when labels are ambiguous.
- Selector conflict is deterministic but still visible. Priority resolution
  must not silently hide an overlapping configuration.
- No new per-pixel semantic lookup, shader definition, texture lookup, source
  primvar requirement, or permanent source authoring belongs to this task.
- Schema 1 `.orms` files may contain machine-specific absolute production
  paths. Sharing a profile does not make external atlas content portable;
  missing destinations use the existing per-family packaged-debug fallback.
- General expression parsing, inferred room semantics, per-type classifiers,
  and semantic encoding in `roomID` are explicitly out of scope.

---

## Deferred original KRM-92 scope

The following plan records the pre-Interior-Set KRM-92 scope. It is retained for
the Phase 9 reassessment and must not be treated as current implementation
instructions until that reassessment is complete.

### Original record

| Field | Value |
| --- | --- |
| Jira | KRM-92 |
| Preceding delivery | KRM-91 |
| Implementation target | Existing `Window > ORMS` panel and Extension Manager overview page |
| State | Planned next implementation task |
| Last reviewed | 3 September 2026 |

### Original purpose

KRM-92 turns the functional ORMS controls accepted in KRM-91 into a coherent
artist-facing workflow. The task owns the presentation, discoverability,
editing affordances, validation feedback, and user guidance around the existing
runtime. It does not reopen the accepted shader, classifier, assignment,
lifecycle, or resource-routing contracts.

### Original accepted starting point

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

### Original implementation plan

#### Panel structure and runtime status

- establish a clear visual hierarchy for the lifecycle controls, runtime
  status, tabs, settings groups, and feedback messages;
- make `Inactive`, `Running`, `Stopped`, and `Failed` states immediately
  understandable;
- show concise explanations for `Start`, `Stop`, `Restart`, and
  `Restore Original Asset`, including the difference between freezing the
  current result and removing ORMS-owned scene state;
- disable or explain actions that are unavailable in the current lifecycle
  state.

#### ORMS Classifier

- refine labels, grouping, tooltips, numeric controls, and fallback
  explanations for room-family and classifier settings;
- make it clear that disabling x2, x3, or x4 reclassifies those rooms through
  the x1 fallback rather than removing window geometry;
- expose the accepted per-mesh opt-out contract
  `orms:autoAssign = false` without requiring manual USD attribute authoring;
- provide an artist-facing way to inspect automatically assigned meshes and
  change or remove those assignments.

#### Material Parameters

- organise the shared shader controls into readable functional groups;
- explain that each value is applied to all active x1-x4 family materials;
- provide appropriate reset affordances without presenting four duplicated
  material configurations;
- surface validation or failure feedback without exposing internal Session
  Layer prims.

#### Interior Atlases

- replace raw path editing with a directory picker for each x1, x2, x3, and x4
  production family while preserving direct text editing where useful;
- show whether each family resolves to a production folder or its packaged
  debug fallback;
- validate the expected continuous UDIM sequence beginning at `1001` and show
  actionable inline errors;
- make the effect of `Apply atlas configuration` explicit and report whether
  the controlled runtime rebuild succeeded;
- provide per-family and full-section reset affordances.

#### Extension Manager overview

- rewrite the ORMS overview/welcome page for an end user;
- lead with what ORMS does, how to open its window, how automatic assignment
  works, and how to configure production atlases;
- replace the current internal module-ownership and developer-oriented copy
  with concise installation, first-use, and troubleshooting guidance;
- keep technical implementation details in repository documentation rather
  than the product welcome page.

### Original acceptance plan

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

### Original boundary

This record covers only the KRM-92 UI and artist-workflow scope. Work owned by
other Jira issues is not tracked here.
