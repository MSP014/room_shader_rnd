# Omniverse Room Map Shader

Omniverse Room Map Shader (ORMS) turns compatible flat window meshes into
parallax interiors. One scene classifier can serve living rooms, kitchens,
shops, libraries, and other window groups through independent Interior Sets.
All generated materials and bindings remain temporary Session Layer state;
the source USD asset is not rewritten.

## First use

1. Install and enable **Omniverse Room Map Shader** in Extension Manager.
2. Open a compatible USD stage.
3. Open **Window > ORMS**.
4. Use **ORMS Classifier** to review recognised window meshes, then press
   **Start** if the runtime is inactive.
5. Use **Interior Atlases** to choose Debug or Production mode and configure
   the Interior Sets required by the scene.

A compatible window mesh has quad topology and the `roomID`, `roomP`,
`tangentu`, `tangentv`, and `roomUV` primvars. ORMS recognises legacy
`Windows_Glass` meshes, semantic mesh prims below a `windows` container, and
meshes explicitly opted in with `orms:autoAssign=true`.

## ORMS Classifier

The classifier tab controls room grouping for the complete scene. It also
lists recognised meshes and lets you choose one of three source-safe policies:

- **Use source rule** reveals the asset's own `orms:autoAssign` value;
- **Allow ORMS** adds a temporary `orms:autoAssign=true` override;
- **Exclude / restore source** adds a temporary `orms:autoAssign=false`
  override and reveals the source material binding.

These overrides exist only in an ORMS-owned Session Layer. They survive a
runtime restart on the current stage, but **Restore Original Asset**, extension
disable, or stage replacement removes them.

The lifecycle actions have distinct effects:

- **Start** activates ORMS, or resumes a stopped result;
- **Stop** freezes the current visual result and releases live updates;
- **Restart** removes and rebuilds ORMS state from the current settings;
- **Restore Original Asset** removes all ORMS-owned Session Layer opinions.

x1 rooms are always available. Disabling x2, x3, or x4 reclassifies affected
rooms through the x1 fallback; it does not remove their window geometry.

## Material Parameters

Each Interior Set owns one complete material profile. Editing a value is live
and updates only that Set's active x1-x4 runtime materials. Inline feedback
reports whether the change reached live materials or was saved for later use.

Use a group reset to restore only Room, Window, Depth slices, Glass,
Diagnostics, or Emission values. Use **Reset complete material profile** to
restore every material value in that Interior Set to factory defaults.

## Interior Atlases

The four packaged debug atlas paths are read-only global extension resources.
They are independent of production configuration and remain available for
diagnosis in every scene.

- **Debug (force packaged)** uses packaged x1-x4 atlases for every classified
  window in every Interior Set.
- **Production + debug fallback** uses each Set's configured x1-x4 production
  families. A missing or invalid family falls back independently to the
  matching packaged debug family.

Interior Set selectors use simple glob-style composed prim paths, for example
`*/Kitchens_Windows`. Specific Sets are evaluated from top to bottom; the first
match wins. The mandatory Default Set is evaluated last and receives every
remaining compatible window. One composed mesh path resolves to exactly one
Interior Set; assigning different Sets to faces or subsets of one mesh is
outside the 0.1.20 contract.

Selectors, production paths, order, Add, Duplicate, Remove, atlas mode, and
atlas resets are staged edits. Press **Apply Interior Sets** once to validate,
save, and rebuild the scene. **Revert unapplied changes** discards the draft.
Use **Clear** beside one xN family, or **Clear all production folders** for one
Set, to stage an intentional return to packaged fallback. **Reset complete
atlas configuration** clears production folders for every Set and stages Debug
mode as one reset action.

Use **Save Profile...** to save the applied Interior Sets and atlas mode as a
portable, human-readable `.orms` file. **Load Profile...** loads a profile into
the draft; review it and press **Apply Interior Sets** before it affects the
scene. Global geometric classifier controls remain local process settings in
schema 1 and are not imported by the profile.

## Troubleshooting

- If a mesh is not listed, check its composed prim path, quad topology,
  required primvars, material binding, and `orms:autoAssign` source value.
- If a Set is unused, check its case-sensitive masks and selector priority.
- If a family shows packaged fallback, check the production directory, UDIM
  sequence beginning at 1001, and variant-identity manifest.
- If x1–x4 manifests do not share one namespace and ordered ID sequence, ORMS
  reports the mismatch and safely prevents an incoherent cross-family room.
- If a material edit fails, read the inline message beside that Interior Set.
- Use Debug mode to separate ORMS runtime problems from production-atlas
  content problems.

Technical architecture, authoring contracts, and validation evidence are kept
in the project repository rather than this artist overview.
