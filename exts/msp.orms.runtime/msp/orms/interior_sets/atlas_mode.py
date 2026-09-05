# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Define the global staged atlas-selection policy for Interior Sets."""

ATLAS_MODE_DEBUG = "debug"
ATLAS_MODE_PRODUCTION = "production"
ATLAS_MODES = (ATLAS_MODE_DEBUG, ATLAS_MODE_PRODUCTION)


def normalise_atlas_mode(value: object) -> str:
    """Return one supported persisted mode or reject ambiguous input."""

    mode = str(value).strip().lower()
    if mode not in ATLAS_MODES:
        raise ValueError(f"Unsupported ORMS atlas mode: {value!r}")
    return mode
