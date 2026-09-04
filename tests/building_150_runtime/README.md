# Building 150 ORMS Runtime Fixture

This KRM-98 bundle composes the external Building 150 component without
modifying its source layers. The wrapper supplies the retained KRM-93 HDRI and
overrides only the source material binding on the semantic window meshes below
the building's `windows` container. It does not author Interior Set assignment,
runtime materials, or persistent ORMS configuration.

Run `launch_building_150_omniverse.bat` to open the wrapper through the shared
fixture-launcher extension. The extension waits for Kit readiness and the first
bootstrap viewport frame before requesting the production stage.

The launcher deliberately does not start ORMS or claim renderer completion.
After the stage-open record appears, use the installed `msp.orms.runtime`
0.1.20 extension through **Window > ORMS**. Configure or load the required
Interior Sets, press **Apply Interior Sets**, and press **Start** if the runtime
is inactive. The manual
`exts/msp.orms.runtime/msp/orms/runtime/reload_room_map_runtime.py` entry point
is reserved for exact-source development, not normal fixture acceptance.
Follow the runtime and renderer-validation boundaries documented in
`../shared_room_runtime/README.md`.

Frame the building with the active viewport camera. Validate the result in RTX
Real-Time and RTX Interactive or Path Tracing.

The wrapper's source material authors the legacy real x1 atlas at
`assets/_external/tex/room_maps/room_map.<UDIM>.png` with 56 variants. Runtime
behaviour is selected by the applied Interior Sets: Debug forces the packaged
x1–x4 families, while Production resolves every Set's configured x1–x4
families with independent packaged fallback. The source atlas and emission
values remain a reversible pre-extension baseline restored when ORMS ownership
is removed. Each applied Set owns its complete luminance-selected emission and
material profile; Boolean `emission_slice_1` through `emission_slice_4`
independently decide which depth slices may emit while preserving every slice
in colour and alpha composition.
