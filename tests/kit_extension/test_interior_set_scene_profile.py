"""Protect portable, staged `.orms` scene-profile round trips."""

import json
from dataclasses import replace

import pytest
from msp.orms.interior_sets.atlas_mode import ATLAS_MODE_PRODUCTION
from msp.orms.interior_sets.contracts import InteriorSetCollection
from msp.orms.runtime import interior_set_scene_profile as profile_module
from msp.orms.runtime.interior_set_scene_profile import (
    PROFILE_FORMAT,
    InteriorSetSceneProfile,
    load_scene_profile,
    profile_document,
    profile_from_document,
    save_scene_profile,
)
from msp.orms.shared_room.material_controls import MATERIAL_CONTROLS

KITCHENS_ID = "11111111-1111-1111-1111-111111111111"


def _profile() -> InteriorSetSceneProfile:
    materials = tuple(
        (control.name, control.default) for control in MATERIAL_CONTROLS
    )
    collection = InteriorSetCollection.default_only(materials)
    default = replace(
        collection.default,
        name="Living Rooms",
        atlas_directories=("living-x1", "", "", ""),
    )
    collection = collection.replace(default).add(set_id=KITCHENS_ID)
    kitchens = replace(
        collection.by_id(KITCHENS_ID),
        name="Kitchens",
        selectors=("*/Kitchens_Windows", "*/Kitchen_Glass"),
        atlas_directories=("k-x1", "k-x2", "k-x3", "k-x4"),
        material_values=tuple(
            (name, 0.37 if name == "glass_roughness" else value)
            for name, value in materials
        ),
    )
    return InteriorSetSceneProfile(
        collection=collection.replace(kitchens),
        atlas_mode=ATLAS_MODE_PRODUCTION,
    )


def test_scene_profile_round_trip_preserves_identity_order_and_values(
    tmp_path,
):
    source = _profile()

    saved = save_scene_profile(str(tmp_path / "building_150"), source)
    loaded = load_scene_profile(str(saved))

    assert saved.suffix == ".orms"
    assert loaded == source
    document = json.loads(saved.read_text(encoding="utf-8"))
    assert document["format"] == PROFILE_FORMAT
    assert document["scope"] == "interior_sets"
    assert [item["set_id"] for item in document["interior_sets"]] == [
        item.set_id for item in source.collection.sets
    ]


def test_scene_profile_rejects_wrong_suffix_and_unknown_material(tmp_path):
    document = profile_document(_profile())
    document["interior_sets"][0]["material"]["unknown_input"] = 1
    wrong_suffix = tmp_path / "profile.json"
    wrong_suffix.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.orms suffix"):
        load_scene_profile(str(wrong_suffix))
    with pytest.raises(ValueError, match="Unknown material controls"):
        profile_from_document(document)


def test_scene_profile_rejects_malformed_identity_and_material_range():
    document = profile_document(_profile())
    document["interior_sets"][1]["set_id"] = "not-a-uuid"

    with pytest.raises(ValueError, match="UUID"):
        profile_from_document(document)

    document = profile_document(_profile())
    document["interior_sets"][1]["material"]["glass_roughness"] = 5.0
    with pytest.raises(ValueError, match="above 1.0"):
        profile_from_document(document)


def test_scene_profile_accepts_unbounded_non_negative_emission_strength():
    document = profile_document(_profile())
    material = document["interior_sets"][1]["material"]
    material["emission_strength"] = 10_000.0

    loaded = profile_from_document(document)

    assert (
        loaded.collection.by_id(KITCHENS_ID).material_mapping()[
            "emission_strength"
        ]
        == 10_000.0
    )

    material["emission_strength"] = -1.0
    with pytest.raises(ValueError, match="below 0.0"):
        profile_from_document(document)


def test_interrupted_save_preserves_the_preceding_complete_file(
    tmp_path,
    monkeypatch,
):
    target = tmp_path / "building.orms"
    target.write_text("preceding complete profile", encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("interrupted replace")

    monkeypatch.setattr(profile_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="interrupted replace"):
        save_scene_profile(str(target), _profile())

    assert target.read_text(encoding="utf-8") == "preceding complete profile"
    assert tuple(tmp_path.glob("*.tmp")) == ()
