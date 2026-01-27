# ADR 003: Dependency Locking & Isolation

## Status

Accepted

## Context

To ensure that Python tools and test scripts run predictably, we need deterministic dependency management.

## Decision

We enforce a **"One Env Per Project"** policy with strict locking:

### 1. Isolation

* **Environment Name:** `shader_rnd`
* **NEVER** install packages into the global Python or base Conda environment.

### 2. Dependency Locking

We use `pip-tools` for deterministic builds.

* **Source of Truth:** `requirements.in` (High-level deps).
* **Lockfile:** `requirements.txt` (Generated via `pip-compile`). Contains exact versions + hashes.
* **Workflow:**
    1. Edit `requirements.in`.
    2. Run `pip-compile requirements.in`.
    3. Commit both files.

## Consequences

* **Positive:** 100% reproducibility. `pip-audit` works effectively.
* **Negative:** Extra step (`pip-compile`) when adding libraries.
