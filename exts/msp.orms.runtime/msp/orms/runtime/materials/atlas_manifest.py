"""Load and compare semantic variant identities for atlas families."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from msp.orms.interior_sets.contracts import VariantIdentityManifest

VARIANT_MANIFEST_FILENAME = "orms_variants.json"
DEBUG_VARIANT_NAMESPACE = "orms.packaged_debug.v1"


@dataclass(frozen=True)
class ManifestCoherence:
    """Report whether several atlas families share ordered identities."""

    coherent: bool
    namespace: str | None
    variant_ids: tuple[str, ...]
    error: str | None = None


def debug_variant_manifest(variant_count: int) -> VariantIdentityManifest:
    """Return the built-in identity sequence shared by debug x1-x4."""

    return VariantIdentityManifest(
        namespace=DEBUG_VARIANT_NAMESPACE,
        variant_ids=tuple(
            f"debug-{index:04d}" for index in range(variant_count)
        ),
    )


def load_variant_manifest(
    directory: Path,
    variant_count: int,
) -> VariantIdentityManifest | None:
    """Load optional production metadata and validate its tile count."""

    path = directory / VARIANT_MANIFEST_FILENAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest = VariantIdentityManifest(
            version=int(payload["version"]),
            namespace=str(payload["namespace"]),
            variant_ids=tuple(str(item) for item in payload["variant_ids"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid ORMS variant manifest: {path}") from error
    if len(manifest.variant_ids) != variant_count:
        raise ValueError(
            "ORMs variant manifest count does not match its UDIM family: "
            f"manifest={len(manifest.variant_ids)}, tiles={variant_count}, "
            f"path={path}"
        )
    return manifest


def validate_manifest_coherence(
    manifests: Mapping[int, VariantIdentityManifest | None],
) -> ManifestCoherence:
    """Require one namespace and ordered identity sequence across families."""

    if not manifests:
        return ManifestCoherence(True, None, ())
    missing = tuple(
        room_size
        for room_size, manifest in sorted(manifests.items())
        if manifest is None
    )
    if missing:
        sizes = ", ".join(f"x{size}" for size in missing)
        return ManifestCoherence(
            False,
            None,
            (),
            f"Missing variant identity metadata for {sizes}",
        )
    present = tuple(
        manifest for manifest in manifests.values() if manifest is not None
    )
    reference = present[0]
    for room_size, manifest in sorted(manifests.items()):
        if manifest is None:
            continue
        if manifest.namespace != reference.namespace:
            return ManifestCoherence(
                False,
                None,
                (),
                "Variant namespace mismatch at "
                f"x{room_size}: {manifest.namespace!r} != "
                f"{reference.namespace!r}",
            )
        if manifest.variant_ids != reference.variant_ids:
            return ManifestCoherence(
                False,
                reference.namespace,
                reference.variant_ids,
                f"Ordered variant identity mismatch at x{room_size}",
            )
    return ManifestCoherence(
        True,
        reference.namespace,
        reference.variant_ids,
    )
