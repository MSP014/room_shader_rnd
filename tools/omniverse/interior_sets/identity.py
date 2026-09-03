"""Own stable Interior Set IDs and path-safe runtime tokens."""

from __future__ import annotations

from uuid import UUID, uuid4

INTERIOR_SET_SCHEMA_VERSION = 2
DEFAULT_INTERIOR_SET_ID = "00000000-0000-0000-0000-000000000000"
ROOM_SIZES = (1, 2, 3, 4)


def canonical_set_id(value: str) -> str:
    """Return a canonical UUID string or reject an unstable identity."""

    try:
        parsed = UUID(str(value))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid Interior Set UUID: {value!r}") from error
    canonical = str(parsed)
    if str(value) != canonical:
        raise ValueError(
            "Interior Set UUIDs must use canonical lowercase spelling: "
            f"{value!r}"
        )
    return canonical


def new_set_id() -> str:
    """Create one immutable non-default Interior Set identity."""

    return str(uuid4())


def runtime_set_token(set_id: str) -> str:
    """Encode a stable UUID as one path-safe runtime component."""

    return f"Set_{UUID(canonical_set_id(set_id)).hex}"
