# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect metric aperture extents in the retained Houdini export."""

import pytest
from pxr import Usd, UsdGeom

from ._fixture_support import HOUDINI_EXPORT


def test_houdini_export_tangent_lengths_encode_aperture_extents():
    stage = Usd.Stage.Open(str(HOUDINI_EXPORT), load=Usd.Stage.LoadAll)
    windows = UsdGeom.Mesh(stage.GetPrimAtPath("/test_bld/geo/windows"))
    primvars = UsdGeom.PrimvarsAPI(windows)
    points = windows.GetPointsAttr().Get()
    face_counts = windows.GetFaceVertexCountsAttr().Get()
    face_indices = windows.GetFaceVertexIndicesAttr().Get()
    room_positions = primvars.GetPrimvar("roomP").ComputeFlattened()
    tangents_u = primvars.GetPrimvar("tangentu").ComputeFlattened()
    tangents_v = primvars.GetPrimvar("tangentv").ComputeFlattened()
    face_offset = 0

    for face_count in face_counts:
        point_indices = face_indices[face_offset : face_offset + face_count]
        vertex_index = point_indices[0]
        room_position = room_positions[vertex_index]
        tangent_u = tangents_u[vertex_index]
        tangent_v = tangents_v[vertex_index]
        axis_u = tangent_u.GetNormalized()
        axis_v = tangent_v.GetNormalized()
        offsets = [points[index] - room_position for index in point_indices]
        aperture_width = max(offset * axis_u for offset in offsets) - min(
            offset * axis_u for offset in offsets
        )
        aperture_height = max(offset * axis_v for offset in offsets) - min(
            offset * axis_v for offset in offsets
        )

        assert tangent_u.GetLength() == pytest.approx(aperture_width)
        assert tangent_v.GetLength() == pytest.approx(aperture_height)
        face_offset += face_count
