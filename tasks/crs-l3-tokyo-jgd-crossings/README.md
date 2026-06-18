# crs-l3-tokyo-jgd-crossings

## Story

Yuki Nakamura, an urban-mobility analyst at the Tokyo Metropolitan Government, is rebuilding the road-safety dashboard for Tokyo's 23 special wards. For each ward she needs to know how often the highway network crosses the ward boundary, with a 50 m operational buffer around each crossing for jurisdictional reporting -- and the work has to happen in JGD2011 Plane IX (EPSG:6677), the conformal national grid covering Tokyo, for honest distance-in-metres. The public-facing dashboard, however, ingests only WGS84, so the final per-ward density layer must be reprojected back. The agent must fetch Tokyo's `highway=*` and `boundary=administrative` from live Overpass, reproject to plane IX, identify crossing points, build planar buffers, intersect with wards, compute density, and emit a multi-layer GPKG that combines the engineering layers in JGD with the dashboard layer in WGS84.

## What this task probes

A full L3 CRS-reprojection workflow: discover -> fetch -> reproject -> analyse -> reproject again -> format-convert. Specifically:

* querying live OSM Overpass for the 23 special wards (`admin_level=7` boundary relations inside the Tokyo Metropolis area) and for the drivable highway network in their bounding box;
* round-trip reprojection between WGS84 and JGD2011 Plane IX (EPSG:6677), including the awareness that planar buffers and area calculations *must* happen in the projected metric frame, not in degrees;
* spatial-join "crosses" between LineStrings (highways) and the boundary lines of polygons (wards);
* planar buffering and per-buffer intersection with the ward that produced the crossing;
* per-ward density aggregation and a final reprojection back to WGS84 for the dashboard;
* writing a single multi-layer GPKG with *mixed per-layer CRSes*, which not every format permits.

## Why L3

Live data fetch (no bundled inputs), three composed analytical operations after the initial reprojection (crosses-detection, buffer, per-buffer intersection), per-feature aggregation, and a second reprojection back to WGS84 for the dashboard layer. Five output layers in two different CRSes inside a single container. The drift sensitivity is low-to-medium: the 23 ward count is essentially fixed in OSM, the drivable-highway count drifts at the 1% level over weeks, and per-ward crossing counts move by a handful at most -- enough that bit-equality is impossible but rank-correlation grading absorbs it.

## Input / output formats

**Inputs.** Live: OSM Overpass API. The reference fetches:

* `relation["boundary"="administrative"]["admin_level"="7"]` inside `area["name:en"="Tokyo"][admin_level=4]` -- 23 special-ward polygons.
* `way["highway"~"^(motorway|trunk|primary|secondary|tertiary|*_link|residential|unclassified|living_street)$"]` in the 23-wards bounding box -- ~85 k highway segments.

A weak agent that pulls *every* `highway=*` (footways, cycleways, paths, services) will exceed Overpass' practical timeout and may have to repeat with a narrower filter -- this is part of the task realism.

**Output.** `tokyo_crossings.gpkg`, single GPKG, five layers:

| Layer | Geometry | CRS | Schema |
|---|---|---|---|
| `wards_jgd` | Polygon | EPSG:6677 | `ward_id` (int), `ward_name_en` (string, nullable), `ward_name` (string, nullable). |
| `crossing_points` | Point | EPSG:6677 | `ward_id`, `ward_name_en`, `ward_name`, `osm_way_id`, `highway_class`, `crossing_index`. |
| `crossing_buffers_50m` | Polygon | EPSG:6677 | Same schema as `crossing_points`. Planar 50 m disc around each point. |
| `buffer_ward_intersection` | Polygon | EPSG:6677 | Same schema as `crossing_points` (without `highway_class`). Buffer clipped to the ward that produced the crossing. |
| `ward_crossing_density_wgs84` | Polygon | EPSG:4326 | `ward_id`, `ward_name_en`, `ward_name`, `crossing_count` (int), `ward_area_km2` (float, in JGD), `crossings_per_km2` (float). |

## Failure modes

1. **Skipped reprojection -- buffers in degrees.** Agent forgets to reproject highways/wards to EPSG:6677 before the geometric ops. The 50 m buffer is then literally 50° wide -- a single buffer covers half of Asia, intersection geometries are nonsense, and the JGD coordinate envelope check fails. -> Detection: `crs_match_*` (4 layers), `wards_jgd_in_plane_ix_envelope`, `buffer_mean_area_is_planar_50m`, `intersection_mean_area_below_buffer`. Covered by `broken_unprojected_pipeline`.

2. **Wrong density metric -- raw count instead of count/area.** Agent computes `crossing_count` per ward and writes that into the `crossings_per_km2` column without dividing by area. Tokyo wards range from ~10 km² (Taito) to ~100 km² (Ota), so ranking by raw count flips the top of the dashboard list compared to ranking by density. -> Detection: `density_rank_correlation_with_reference`, `top5_densest_wards_match`. Covered by `broken_wrong_density_metric`.

3. **Wrong output format -- single-layer GeoJSON, or CSV named .gpkg.** Agent writes a non-GPKG file (or a one-layer GPKG missing the four other layers). -> Detection: Gate 1 (`format_schema_valid`). Covered by `broken_wrong_format`.

4. **Density layer left in EPSG:6677.** Agent forgets to reproject the final density layer back to WGS84 for the public dashboard. -> Detection: `crs_match_ward_crossing_density_wgs84`, `density_layer_in_wgs84_envelope`. Principled-reasoning subcheck (not a dedicated broken).

5. **Buffer applied to highways, not to crossing points.** A canonical mis-read of the spec where the agent buffers each highway segment by 50 m and intersects with wards. The schema looks fine but the buffer count = highway count (~85 k, not ~5 k crossings) and per-buffer area is enormous. -> Detection: `crossing_count_within_tolerance` (massive count overshoot), `buffer_mean_area_is_planar_50m` (highway buffer area >> 50 m disc). Principled-reasoning subcheck.

6. **Wrong CRS metadata stamped without actual reprojection.** Agent calls `set_crs(6677)` without `to_crs(6677)` -- the geometry is still in lon/lat but the file claims EPSG:6677. -> Detection: `wards_jgd_in_plane_ix_envelope` (lat/lon values fall outside the plane IX numeric envelope). Principled-reasoning subcheck. The `buffer_mean_area_is_planar_50m` check also catches the downstream consequence.

7. **Used `intersects` predicate instead of `crosses`.** A highway that runs along the ward boundary (coincident overlap) gets counted as a crossing, inflating the count. -> Detection: `crossing_count_within_tolerance` (drift vs reference). Principled-reasoning subcheck (the +-15% tolerance still catches a 1.5x or 2x overshoot).

## Expected weak-agent failure mode

The most likely weak-agent error is **skipping the EPSG:6677 reprojection** and applying the 50 m buffer to lon/lat geometries. The prompt never names the EPSG code (it only asks for "the regional metric coordinate system"), so the agent must both pick JGD2011 Plane IX from regional convention and actually reproject into it. An agent that stamps the CRS metadata without reprojecting -- without grasping that buffer/area must be computed in projected metres -- will produce a buffer whose units are degrees. This makes the buffer area check the highest-leverage discriminator in the grader.
