# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Define ordered semantic identity for coherent atlas families."""

from __future__ import annotations

from dataclasses import dataclass

VARIANT_MANIFEST_VERSION = 1


@dataclass(frozen=True)
class VariantIdentityManifest:
    """Describe the ordered semantic variants represented by one atlas."""

    namespace: str
    variant_ids: tuple[str, ...]
    version: int = VARIANT_MANIFEST_VERSION

    def __post_init__(self) -> None:
        if self.version != VARIANT_MANIFEST_VERSION:
            raise ValueError(
                "Unsupported ORMS variant manifest version: " f"{self.version}"
            )
        if not self.namespace.strip():
            raise ValueError("Variant manifest namespace must not be empty")
        if not self.variant_ids:
            raise ValueError("Variant manifest must contain at least one ID")
        if any(not item.strip() for item in self.variant_ids):
            raise ValueError("Variant IDs must not be empty")
        if len(set(self.variant_ids)) != len(self.variant_ids):
            raise ValueError("Variant IDs must be unique within one manifest")


def semantic_variant_index(
    room_id: int,
    variation_seed: int,
    variant_count: int,
) -> int:
    """Mirror the bounded MDL room-variant selection contract."""

    safe_count = max(int(variant_count), 1)
    mixed_id = int(room_id) * 1664525 + int(variation_seed) * 1013904223
    return ((mixed_id % safe_count) + safe_count) % safe_count


def semantic_variant_id(
    manifest: VariantIdentityManifest,
    room_id: int,
    variation_seed: int,
) -> str:
    """Resolve one room identity against a coherent ordered manifest."""

    index = semantic_variant_index(
        room_id,
        variation_seed,
        len(manifest.variant_ids),
    )
    return manifest.variant_ids[index]
