"""Resolve composed prim paths against ordered Interior Set masks."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Iterable, TypeVar

from .contracts import InteriorSetCollection

_UNSUPPORTED_GLOB_CHARACTERS = frozenset("?[]")
_Aperture = TypeVar("_Aperture")


@dataclass(frozen=True)
class SelectorMatch:
    """Record every mask from one specific Set that matched a path."""

    set_id: str
    masks: tuple[str, ...]


@dataclass(frozen=True)
class SelectorResolution:
    """Describe deterministic assignment and any overlapping selectors."""

    prim_path: str
    set_id: str
    winning_mask: str | None
    specific_matches: tuple[SelectorMatch, ...]
    used_default: bool

    @property
    def has_conflict(self) -> bool:
        """Return whether more than one specific Set matched the path."""

        return len(self.specific_matches) > 1


def validate_selector(mask: str) -> str:
    """Normalise one bounded glob mask and reject expression syntax."""

    normalised = str(mask).strip()
    if not normalised:
        return ""
    if any(character in normalised for character in "\r\n\0"):
        raise ValueError("Interior Set selectors must occupy one line")
    if _UNSUPPORTED_GLOB_CHARACTERS.intersection(normalised):
        raise ValueError(
            "Interior Set selectors support literal path text and '*' only"
        )
    return normalised


def selector_matches(mask: str, prim_path: str) -> bool:
    """Match a complete composed path while allowing '*' across separators."""

    normalised = validate_selector(mask)
    if not normalised:
        return False
    expression = re.escape(normalised).replace(r"\*", ".*")
    return re.fullmatch(expression, prim_path) is not None


def validate_collection_selectors(
    collection: InteriorSetCollection,
) -> None:
    """Validate a complete draft without resolving any scene paths."""

    for item in collection.sets:
        for mask in item.selectors:
            validate_selector(mask)


def resolve_selector(
    prim_path: str,
    collection: InteriorSetCollection,
) -> SelectorResolution:
    """Resolve the first matching specific Set, then Default."""

    matches = []
    for item in collection.specific:
        matching_masks = tuple(
            mask
            for mask in item.selectors
            if selector_matches(mask, prim_path)
        )
        if matching_masks:
            matches.append(SelectorMatch(item.set_id, matching_masks))
    if not matches:
        return SelectorResolution(
            prim_path=prim_path,
            set_id=collection.default.set_id,
            winning_mask=None,
            specific_matches=(),
            used_default=True,
        )
    return SelectorResolution(
        prim_path=prim_path,
        set_id=matches[0].set_id,
        winning_mask=matches[0].masks[0],
        specific_matches=tuple(matches),
        used_default=False,
    )


def assign_apertures(
    apertures: Iterable[_Aperture],
    collection: InteriorSetCollection,
) -> tuple[tuple[_Aperture, ...], tuple[SelectorResolution, ...]]:
    """Resolve each mesh path once and enrich all of its apertures."""

    ordered = tuple(apertures)
    paths = tuple(sorted({str(item.prim_path) for item in ordered}))
    resolutions = tuple(
        resolve_selector(prim_path, collection) for prim_path in paths
    )
    by_path = {item.prim_path: item for item in resolutions}
    assigned = tuple(
        replace(
            aperture,
            interior_set_id=by_path[str(aperture.prim_path)].set_id,
        )
        for aperture in ordered
    )
    return assigned, resolutions
