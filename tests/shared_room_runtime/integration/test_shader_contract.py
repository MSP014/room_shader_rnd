"""Protect the shared-room runtime-to-MDL mapping and lookup budget."""

from ..shared_room._support import MDL_PATH


def test_mdl_consumes_direct_shared_mapping_with_the_existing_lookup_budget():
    source = MDL_PATH.read_text(encoding="utf-8")

    for primvar_name in (
        "ormsRoomParameters",
        "ormsRoomAxisU",
        "ormsRoomAxisV",
        "ormsRoomScale",
        "ormsRoomMapPosition",
    ):
        assert f'"{primvar_name}"' in source

    assert "float3 shared_aperture_position(" in source
    assert '"ormsRoomScale"' in source
    assert "ray_vector_room * safe_room_scale" in source
    assert (
        "float3 scaled_position = physical_position * room_scale * room_extent"
        in source
    )
    assert "bool depth_aligned_portal =" in source
    assert (
        "float front_position_x = scaled_position.x * aperture_scale.x"
        in source
    )
    assert "float side_position_z =" in source
    assert "? float3(" in source
    assert "scaled_position.x + 0.5 * room_width" in source
    assert (
        "safe_room_width = safe_room_extent * float(active_room_size)"
        in source
    )
    assert "float(active_room_depth_size)" in source
    assert "float3 ray_origin = shared_ray_origin;" in source
    assert "scaled_position.z" in source
    assert "math::max(derived_slice_start_depth, 0.0)" in source
    assert "float slice_start_depth = bay_extension_depth" in source
    assert (
        "safe_room_depth = base_room_depth + bay_extension_depth" not in source
    )
    assert "float slice_depth_span = base_room_depth" in source
    assert "float throat_projection_distance = has_bay_extension" in source
    assert "bool throat_entry_is_valid = has_bay_extension" in source
    assert "safe_room_front_depth + safe_room_depth" in source
    assert "float full_depth_coordinate = saturate(" in source
    assert "float ceiling_distance = positive_plane_distance(" in source
    assert "candidate_ceiling_distance" not in source
    assert "left_hit_is_in_full_depth" not in source
    assert "float3 trace_room_cross(" in source
    assert (
        "float3 hit_point = ray_origin + hit_distance * ray_direction"
        in source
    )
    assert "float3 room_trace = trace_room_cross(" in source
    assert "float room_hit_distance = room_trace.z" in source
    assert "slice_depth_span * saturate(slice_1_depth_percent" in source
    assert "bool slice_depth_range_is_valid" in source
    assert "float2 aperture_uv = aperture_coordinate(" not in source
    assert source.count("tex::lookup_float4(") == 5


def test_mdl_uses_binary_physical_and_corner_front_exit_cutouts():
    source = MDL_PATH.read_text(encoding="utf-8")
    assert "uniform bool enable_opacity = true" in source

    assert "bool point_is_in_room_depth(" not in source
    assert "bool back_hit_is_in_room_extent =" not in source
    assert "candidate_back_distance" not in source
    assert "physical_aperture_tangent_u_world" not in source
    assert "float physical_aperture_cutout_opacity(" in source
    assert "state::geometry_normal()" not in source
    assert "state::transform_normal(" not in source
    assert "state::transform_vector(" not in source
    assert "state::coordinate_object" not in source
    assert '"ormsRoomPositionWorld"' in source
    assert "float3 physical_normal_world" in source
    assert '"ormsPhysicalNormal"' in source
    assert "float3 derived_physical_normal" in source
    assert "physical_surface_cutout_opacity = depth_aligned_portal" in source
    assert "bool facing_input_is_valid" in source
    assert "!facing_input_is_valid || facing_cosine" in source
    assert "? 1.0\n    : 0.0;" in source
    assert "float physical_surface_cutout_opacity =" in source
    assert "bool front_exit_ray_is_valid = depth_aligned_portal" in source
    assert "float3 aperture_mask_scaled_position =" in source
    assert '"ormsApertureMaskOffsetU"' in source
    assert "float3(aperture_mask_offset_u, 0.0, 0.0)" in source
    assert "float3 aperture_mask_ray_origin = float3(" in source
    assert "aperture_mask_scaled_position.z" in source
    assert "aperture_mask_ray_origin.z" in source
    assert "aperture_mask_ray_origin + front_exit_distance" in source
    assert "float front_exit_distance =" in source
    assert "bool front_exit_is_open =" in source
    assert "front_exit_distance < room_hit_distance" not in source
    assert '"ormsPrimaryApertureMinU012"' in source
    assert '"ormsPrimaryApertureMaxU012"' in source
    assert '"ormsPrimaryApertureU3"' in source
    assert "data_lookup_float4(" not in source
    assert "int primary_aperture_count = math::max(" not in source
    assert "bool coordinate_is_in_primary_aperture_intervals(" in source
    assert "float mullion_half_width = 0.035" not in source
    assert (
        "bool front_exit_hits_primary_aperture = front_exit_is_open" in source
    )
    assert source.count("coordinate_is_in_primary_aperture_intervals(") == 2
    assert "float visible_room_limit_distance =" in source
    assert "math::min(room_hit_distance, front_exit_distance)" in source
    assert source.count("<= visible_room_limit_distance") == 4
    assert (
        "float slice_coverage = saturate(1.0 - room_transmittance);" in source
    )
    assert source.count("<= front_exit_distance") == 4
    assert "struct room_slice_composite" in source
    assert "room_slice_composite composite_room_slices(" in source
    assert "float front_exit_transmittance =" in source
    assert "float front_exit_slice_coverage =" in source
    assert "slice_composite.front_exit_coverage" in source
    assert "bool front_exit_has_slice_surface =" in source
    assert "front_exit_slice_coverage >= 0.5" in source
    assert "? front_exit_has_slice_surface ? 1.0 : 0.0" in source
    assert "color front_exit_slice_colour = composited_slice_colour" in source
    assert "math::max(slice_coverage, room_map_epsilon())" in source
    assert (
        "float production_cutout_opacity = !frame_is_valid\n" "        ? 1.0"
    ) in source
    assert "float room_cutout_opacity = enable_opacity" in source
    assert "? production_cutout_opacity" in source
    assert ": 1.0;" in source
    assert "* virtual_front_cutout_opacity" not in source
    assert (
        "color composited_room_colour = front_exit_hits_primary_aperture"
        in source
    )
    assert "? front_exit_slice_colour" in source
    assert "thin_walled: true" not in source
    assert "mode: df::scatter_transmit" not in source
    assert "float glass_roughness = 0.1" in source
    assert "float glass_reflectivity = 0.04" in source
    assert "color glass_tint = color(1.0)" in source
    assert "float glass_transmission = 1.0" in source
    assert "bool enable_emission = false" in source
    assert "bool emission_slice_1 = true" in source
    assert "bool emission_slice_4 = true" in source
    assert "float emission_threshold = 0.8" in source
    assert "float emission_softness = 0.1" in source
    assert "float room_emission_mask(" in source
    assert "float3(source_colour)" in source
    assert "math::smoothstep(" in source
    assert "struct room_emission_controls" in source
    assert "color emission_colour;" in source
    assert "emission.enabled && emission.slice_1_enabled" in source
    assert "emission.enabled && emission.slice_4_enabled" in source
    assert "room_face_emission_colour * room_transmittance" in source
    assert "composited_slice_emission_colour" in source
    assert "bool emission_hits_interior_surface =" in source
    assert (
        "!front_exit_hits_primary_aperture || front_exit_has_slice_surface"
        in source
    )
    assert "frame_is_valid && emission_hits_interior_surface" in source
    assert "emission_source_colour" in source
    assert "bsdf room_surface = df::diffuse_reflection_bsdf(" in source
    assert "bsdf glass_reflection = df::microfacet_ggx_smith_bsdf(" in source
    assert "mode: df::scatter_reflect" in source
    assert "bsdf room_behind_glass = df::custom_curve_layer(" in source
    assert "normal_reflectivity: safe_glass_reflectivity" in source
    assert "scattering: room_behind_glass" in source
    assert "intensity: visible_room_emission * emission_strength" in source
    assert "geometry: material_geometry(" in source
    assert "cutout_opacity: room_cutout_opacity" in source
    assert source.count("tex::lookup_float4(") == 5
