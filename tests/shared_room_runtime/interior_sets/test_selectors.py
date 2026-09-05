# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect deterministic path-level Interior Set selection."""

from msp.orms.classification.contracts import ApertureDescriptor
from msp.orms.interior_sets.contracts import (
    InteriorSetCollection,
    InteriorSetConfig,
)
from msp.orms.interior_sets.selectors import (
    assign_apertures,
    resolve_selector,
)

KITCHENS_ID = "11111111-1111-1111-1111-111111111111"
SHOPS_ID = "22222222-2222-2222-2222-222222222222"


def _configured_sets():
    default = InteriorSetCollection.default_only().default
    kitchens = InteriorSetConfig(
        set_id=KITCHENS_ID,
        name="Kitchens",
        selectors=(
            "*/Kitchens_Windows",
            "*/Restaurant_Kitchen_Windows",
        ),
    )
    shops = InteriorSetConfig(
        set_id=SHOPS_ID,
        name="Shops",
        selectors=("*/Shop*_Windows", "*/Kitchens_Windows"),
    )
    return InteriorSetCollection((default, kitchens, shops))


def test_mask_matches_multiple_buildings_and_multiple_masks_use_or():
    configured = _configured_sets()

    first = resolve_selector(
        "/World/BuildingA/Kitchens_Windows",
        configured,
    )
    second = resolve_selector(
        "/World/BuildingB/Restaurant_Kitchen_Windows",
        configured,
    )

    assert first.set_id == KITCHENS_ID
    assert second.set_id == KITCHENS_ID


def test_specific_priority_beats_default_and_reports_conflict():
    resolution = resolve_selector(
        "/World/Building/Kitchens_Windows",
        _configured_sets(),
    )

    assert resolution.set_id == KITCHENS_ID
    assert not resolution.used_default
    assert resolution.has_conflict
    assert tuple(item.set_id for item in resolution.specific_matches) == (
        KITCHENS_ID,
        SHOPS_ID,
    )


def test_default_is_used_only_when_no_specific_set_matches():
    configured = _configured_sets()

    resolution = resolve_selector(
        "/World/Building/LivingRoom_Windows",
        configured,
    )

    assert resolution.set_id == configured.default.set_id
    assert resolution.used_default
    assert resolution.winning_mask is None


def test_one_mesh_path_cannot_split_faces_between_sets():
    apertures = tuple(
        ApertureDescriptor(
            key=f"face-{face_index}",
            prim_path="/World/Building/Kitchens_Windows",
            face_index=face_index,
            building_root="/World/Building",
            room_id=face_index,
            centre_metres=(float(face_index), 0.0, 0.0),
            tangent_u_metres=(1.0, 0.0, 0.0),
            tangent_v_metres=(0.0, 1.0, 0.0),
        )
        for face_index in range(2)
    )

    assigned, resolutions = assign_apertures(apertures, _configured_sets())

    assert len(resolutions) == 1
    assert {item.interior_set_id for item in assigned} == {KITCHENS_ID}
