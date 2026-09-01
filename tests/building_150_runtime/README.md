# Building 150 ORMS Runtime Fixture

This KRM-98 bundle composes the external Building 150 component without
modifying its source layers. The wrapper overrides only the material binding
on `Windows_Glass` and supplies the retained KRM-93 HDRI.

Run `launch_building_150_omniverse.bat` to open the wrapper through the shared
fixture-launcher extension. The extension waits for Kit readiness and the first
bootstrap viewport frame before requesting the production stage.

The launcher deliberately does not start ORMS or claim renderer completion.
After the stage-open record appears, start the canonical manual runtime through
`tools/omniverse/reload_room_map_runtime.py` in Kit's Script Editor. Follow the
runtime and renderer-validation boundaries documented in
`../shared_room_runtime/README.md`.

Frame the building with the active viewport camera. Validate the result in RTX
Real-Time and RTX Interactive or Path Tracing.

The wrapper authors the real x1 atlas at
`assets/_external/tex/room_maps/room_map.<UDIM>.png` with 56 variants. Runtime
x1 uses that source atlas, while x2–x4 deliberately retain their eight-variant
labelled debug families until matching real assets exist. The fixture enables
the shared x1–x4 luminance-selected emission controls at strength `5.0`,
threshold `0.8`, and softness `0.1` for the current visual pass. Boolean
`emission_slice_1` through `emission_slice_4` controls independently decide
which depth slices may emit while preserving every slice in colour and alpha
composition.
