# ADR 003: Dependency Locking & Isolation

## Status

Accepted

## Context

To ensure that Python tools and test scripts run predictably, we need deterministic dependency management.

## Decision

We enforce a **"One Env Per Project"** policy with strict locking:

### 1. Isolation

* **Environment Name:** `shader_rnd`
* **Environment Specification:** `environment.yml` (Python and installer
  baseline).
* **NEVER** install packages into the global Python or base Conda environment.

### 2. Dependency Locking

We use `pip-tools` for deterministic builds.

* **Source of Truth:** `requirements.in` (High-level deps).
* **Lockfile:** `requirements.txt` (generated via `pip-compile`). Contains exact
  versions for the repository toolchain.
* **Workflow:**
    1. Create or update `shader_rnd` from `environment.yml`.
    2. Edit `requirements.in`.
    3. Run `python -m piptools compile --no-strip-extras requirements.in`
       inside `shader_rnd`.
    4. Commit `environment.yml`, `requirements.in`, and `requirements.txt`.

## Consequences

* **Positive:** Repeatable dependency resolution. `pip-audit` works effectively.
* **Negative:** Extra step (`pip-compile`) when adding libraries.
