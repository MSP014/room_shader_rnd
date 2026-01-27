# ADR 005: Asset Life Cycle & Hydration

## Status

Proposed

## Context

We deal with heavy texture atlases (EXR/PNG sequences) and USD caches that are unsuitable for Git storage. We need a reliable way to "hydrate" the repository with these heavy assets.

## Decision

We will implement a **Hydration Protocol** to reconstruct the operational environment:

1. **External Storage**: All non-textual assets (USD crates, textures) will be hosted on high-availability external storage (or kept in `_incoming`/local backup until hydration server is ready).
2. **Directory Mapping**: The external archive structure must mirror the local directory skeleton (`/assets`, `/geo`).
3. **Relative Path Integrity**: Every USD reference and Python script path MUST use relative paths. Absolute paths are strictly forbidden.

## Consequences

* **Positive:** Fast repository cloning, professional handling of heavy binary data.
* **Negative:** Requires an additional manual or scripted "hydration" step after cloning.
