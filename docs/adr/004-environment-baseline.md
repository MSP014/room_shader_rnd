# ADR 004: Environment Baseline

## Status

Accepted

## Context

Different Python versions introduce subtle incompatibilities. To ensure standardisation, we must lock the Python version.

## Decision

We anchor the `shader_rnd` environment on a specific Python baseline:

### 1. Python Version

* **Baseline**: **Python 3.12.x**.
* **Rationale**: This aligns repository tooling with the Python 3.12 runtime
  embedded in the validated NVIDIA Omniverse Kit 110.1.2 application. Houdini
  export code remains subject to the Python runtime bundled with the selected
  Houdini 20.0+ build rather than defining the repository baseline.

### 2. Base Configuration

* **Package Manager**: `conda` (Miniconda/Anaconda) for environment creation.
* **Environment Specification**: `environment.yml`.
* **Installer**: `pip < 26` within the activated Conda environment. This upper
  bound is required because `pip-tools 7.6.0` still uses a pip internal API
  removed in pip 26.

## Consequences

* **Positive:** Minimises "syntax error" or "library not found" issues.
* **Negative:** Existing Python 3.10 `shader_rnd` environments must be recreated
  or upgraded before running the repository quality gate.
