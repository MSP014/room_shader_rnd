# ADR 002: QA & Security Protocols

## Status

Accepted

## Context

"Works on my machine" is not an acceptable delivery standard. We deal with complex shader logic where a single syntax error can crash the renderer.

## Decision

We enforce a strict "Shift Left" strategy using `pre-commit` hooks and automated guardrails:

### 1. Guardrails (Pre-commit)

* **Linting:** `black` (Formatting), `flake8` (Logic), `isort` (Imports) for Python tools.
* **Security:**
  * `bandit`: Scans for common security issues.
  * `pip-audit`: Checks `requirements.txt` for known vulnerabilities.
* **Hygiene:** `check-added-large-files` (Max 10MB) to prevent repo bloating.

### 2. Testing

* **Shader Validation**: Manual validation of MDL compilation in Omniverse is required before commit (until a CLI MDL checker is integrated).
* **Python Tools**: `pytest` must pass locally before push.

### 3. Secrets Management

* **Isolation**: All sensitive data (API keys, DB credentials) MUST be stored in a `.env` file.
* **Sanity**: The `.env` file MUST be included in `.gitignore`. Never commit secrets to version control.

## Consequences

* **Positive:** Higher code quality, reduced security risk, and blocked accidental large files.
* **Negative:** Initial setup friction.
