"""Protect pure reader-facing summaries of classified corner boxes."""

from types import SimpleNamespace

from tools.omniverse.runtime.diagnostics import corner_box_summaries


def test_corner_box_summaries_ignore_straight_rooms_and_describe_corners():
    straight = SimpleNamespace(
        aperture_keys=("a", "b"),
        room_size=2,
        room_depth_size=1,
        room_id=1,
        derived_id=10,
    )
    corner = SimpleNamespace(
        aperture_keys=("c", "d", "e"),
        room_size=2,
        room_depth_size=1,
        room_id=2,
        derived_id=20,
    )
    mapping = SimpleNamespace(
        group_id=20,
        room_axis_u=(1.0, 0.0, 0.0),
        atlas_size=2,
        room_size=2,
        room_scale=(2.0, 1.0, 1.0),
        primary_aperture_min_u=(0.0, -1.0, -1.0, -1.0),
        primary_aperture_max_u=(1.0, -1.0, -1.0, -1.0),
        map_origin=(0.0, 0.0, 0.0),
        map_axis_u=(0.0, 0.0, 1.0),
        aperture_mask_offset_u=0.25,
    )
    classification = SimpleNamespace(
        result=SimpleNamespace(
            groups=(straight, corner),
            mappings=(mapping,),
        )
    )

    summaries = corner_box_summaries(classification)

    assert len(summaries) == 1
    assert summaries[0].startswith("roomID=2:box=x2x1")
    assert "side_u_offsets_m=(0.25,)" in summaries[0]


def test_corner_box_summaries_accepts_an_unclassified_stage():
    assert corner_box_summaries(None) == ()
