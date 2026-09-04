"""Read and write portable staged Interior Set scene profiles."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.omniverse.interior_sets.atlas_mode import normalise_atlas_mode
from tools.omniverse.interior_sets.contracts import (
    ROOM_SIZES,
    InteriorSetCollection,
    InteriorSetConfig,
)

from .interior_set_material_values import normalise_material_profile
from .interior_set_storage import normalise_collection

PROFILE_FORMAT = "msp.orms.scene-profile"
PROFILE_SCHEMA_VERSION = 1
PROFILE_SUFFIX = ".orms"


@dataclass(frozen=True)
class InteriorSetSceneProfile:
    """Hold one validated portable Interior Set configuration."""

    collection: InteriorSetCollection
    atlas_mode: str


def _as_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _as_sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be an array")
    return value


def _material_profile(value: object) -> tuple[tuple[str, object], ...]:
    raw = _as_mapping(value, "Interior Set material")
    return normalise_material_profile(raw)


def _interior_set(value: object) -> InteriorSetConfig:
    raw = _as_mapping(value, "Interior Set")
    set_id = raw.get("set_id")
    name = raw.get("name", "")
    if not isinstance(set_id, str):
        raise ValueError("Interior Set set_id must be a UUID string")
    if not isinstance(name, str):
        raise ValueError(f"Interior Set {set_id} name must be text")
    selectors = _as_sequence(raw.get("selectors", ()), "selectors")
    if not all(isinstance(mask, str) for mask in selectors):
        raise ValueError(f"Interior Set {set_id} selectors must be text")
    atlases = _as_mapping(raw.get("atlases", {}), "atlases")
    atlas_directories = []
    for room_size in ROOM_SIZES:
        directory = atlases.get(f"x{room_size}", "")
        if not isinstance(directory, str):
            raise ValueError(
                f"Interior Set {set_id} x{room_size} atlas must be text"
            )
        atlas_directories.append(directory)
    return InteriorSetConfig(
        set_id=set_id,
        name=name,
        selectors=tuple(selectors),
        atlas_directories=tuple(atlas_directories),
        material_values=_material_profile(raw.get("material", {})),
    )


def profile_document(profile: InteriorSetSceneProfile) -> dict[str, object]:
    """Return the stable JSON-compatible document for one applied profile."""

    collection = normalise_collection(profile.collection)
    return {
        "format": PROFILE_FORMAT,
        "schema_version": PROFILE_SCHEMA_VERSION,
        "scope": "interior_sets",
        "atlas_mode": normalise_atlas_mode(profile.atlas_mode),
        "interior_sets": [
            {
                "set_id": item.set_id,
                "name": item.name,
                "selectors": list(item.selectors),
                "atlases": {
                    f"x{room_size}": item.atlas_directory(room_size)
                    for room_size in ROOM_SIZES
                },
                "material": {
                    name: list(value) if isinstance(value, tuple) else value
                    for name, value in item.material_values
                },
            }
            for item in collection.sets
        ],
    }


def profile_from_document(value: object) -> InteriorSetSceneProfile:
    """Validate an untrusted JSON document without mutating settings or USD."""

    raw = _as_mapping(value, "ORMS scene profile")
    if raw.get("format") != PROFILE_FORMAT:
        raise ValueError("File is not an ORMS scene profile")
    if raw.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported ORMS scene profile schema: "
            f"{raw.get('schema_version')!r}"
        )
    items = _as_sequence(raw.get("interior_sets"), "interior_sets")
    collection = normalise_collection(
        InteriorSetCollection(tuple(_interior_set(item) for item in items))
    )
    return InteriorSetSceneProfile(
        collection=collection,
        atlas_mode=normalise_atlas_mode(raw.get("atlas_mode")),
    )


def profile_path(path: str, *, append_suffix: bool) -> Path:
    """Return one local profile path with an explicit `.orms` suffix."""

    text = str(path).strip()
    if not text:
        raise ValueError("Choose an ORMS scene profile path first")
    candidate = Path(text).expanduser()
    if candidate.suffix.lower() != PROFILE_SUFFIX:
        if not append_suffix:
            raise ValueError("ORMS scene profiles must use the .orms suffix")
        candidate = candidate.with_suffix(PROFILE_SUFFIX)
    return candidate


def save_scene_profile(
    path: str,
    profile: InteriorSetSceneProfile,
) -> Path:
    """Atomically write one applied profile and return its final path."""

    target = profile_path(path, append_suffix=True)
    if not target.parent.is_dir():
        raise ValueError(f"Profile directory does not exist: {target.parent}")
    document = profile_document(profile)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return target


def load_scene_profile(path: str) -> InteriorSetSceneProfile:
    """Read and validate one local `.orms` file without applying it."""

    source = profile_path(path, append_suffix=False)
    if not source.is_file():
        raise ValueError(f"ORMS scene profile does not exist: {source}")
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read ORMS scene profile: {error}") from error
    return profile_from_document(document)
