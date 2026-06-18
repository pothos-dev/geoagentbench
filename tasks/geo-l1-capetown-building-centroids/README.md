# geo-l1-capetown-building-centroids

## Story

Thandi Nkosi, GIS lead on Cape Town's addressing-improvement project,
is preparing a centroid-only layer of the latest building footprints
so that the addressing team's lightweight web tool — which only
renders points — can plot the city's housing stock. She needs a
centroid for every building, exported as WGS84 GeoJSON with the
original building ID preserved as the join key back to the polygon
master.

## What this task probes

Per-feature **centroid** on Polygon / MultiPolygon footprints, plus a
mandatory **CRS reprojection from EPSG:32734 to EPSG:4326** on the way
out (the input ships in metric UTM 34S; the output must be WGS84). A
competent agent must also recognise the dBase 10-character
column-name limit on Shapefile input — the column the persona named as
`building_id` lands on disk as `building_i`, and the agent must
recover the original name on the GeoJSON output.

## Why this difficulty

L1: a single primary GIS operation (`centroid` per row) plus a single
mandatory reprojection on a fully bundled 122-feature shapefile. No
fetching, no chained transforms, no attribute joins. The two twists —
"centroid in projected metres, not degrees" and "Shapefile column-name
truncation" — are individually L1-level format-literacy gotchas.

## Input / output formats

### Input

`data/capetown_buildings.shp` (+ `.shx`, `.dbf`, `.prj`, `.cpg`
sidecars) — ESRI Shapefile, EPSG:32734, 122 features.

| Field | On-disk name | Type | Notes |
|---|---|---|---|
| `building_id` | `building_i` | string | dBase truncated; agent must restore the original name on output. |
| `geometry` | n/a | Polygon (EPSG:32734) | Cape Town CBD building footprints sliced from Overture 2026-04-15.0. |

### Output

`outputs/building_centroids.geojson` — GeoJSON FeatureCollection,
EPSG:4326, 122 features.

| Field | Type | Notes |
|---|---|---|
| `building_id` | string | preserved verbatim |
| `geometry` | Point (EPSG:4326) | per-feature planar centroid, reprojected |

## Failure modes

1. **Agent wrote a non-GeoJSON file** (CSV, Parquet, raw WKT).
   *Detection:* Gate 1 rejects (output not parseable as GeoJSON or
   filename mismatch). Covered by `broken_wrong_format` (score 0.0).
2. **Agent emitted the bbox corner instead of the geometric centroid.**
   *Detection:* `centroid_within_1m` and `centroid_median_distance_
   tight` fail (typical offset ≈ 17 m); `centroid_inside_own_
   footprint_bbox` partially fails. Covered by
   `broken_bbox_corner_instead_of_centroid` (score 0.421 under the
   2026-06-14 severity-weighted 9-subcheck grader; was 0.526 under the
   blunt-weighted grader, 0.571 under the 7-subcheck grader, and 0.4
   under the original 5-subcheck grader).
3. **Agent fabricated or re-numbered the building IDs** (lost the join
   key the persona explicitly required). *Detection:*
   `building_id_set_preserved` fails (Jaccard 0); the per-id distance
   subchecks all fail because no ids match. Covered by
   `broken_wrong_ids` (score 0.263 under the 2026-06-14 severity-
   weighted 9-subcheck grader; was 0.368 under the blunt-weighted
   grader, 0.429 under the 7-subcheck grader, and 0.2 under the
   original 5-subcheck grader).
4. **Agent computed the centroid in degrees** (forgot to project to
   metric before centroid), producing a centroid biased toward the
   equator on long features. *Detection:*
   `centroid_within_1m` and `centroid_median_distance_tight` fail.
   Not covered by a broken solution; principled detector is the
   distance subchecks (the in-degrees centroid offsets a metric one
   by metres on Cape Town latitudes, well above 1 m).
5. **Agent forgot to reproject to WGS84 on output** (left the file in
   EPSG:32734). *Detection:* the soft-CRS policy reprojects the
   submission to canonical for the geometric subchecks and fails only
   `crs_is_canonical` (`crs_in_meaningful_set` still passes because
   EPSG:32734 is the natural metric CRS here), a one-weight deduction
   (18/19 ≈ 0.947). Not covered by a broken solution; principled
   detector is the `crs_is_canonical` subcheck.
6. **Agent lost the truncated `building_i` column entirely** (read the
   shapefile, computed centroids, but dropped the attribute table on
   write). *Detection:* Gate 1 rejects (missing required column
   `building_id`). Not covered by a broken solution; principled
   detector is the gate.
7. **Agent used `point_on_surface` instead of `centroid`.** For
   convex rectangular footprints these coincide, but Cape Town's
   building set includes L-shaped and U-shaped footprints where the
   two operations diverge by metres. *Detection:*
   `centroid_median_distance_tight` (median ≤ 0.05 m) fails — even
   though `centroid_within_1m` may still pass on simple rectangles,
   the tighter threshold catches the systematic offset. Not covered
   by a broken solution; principled detector is the median-distance
   subcheck.
8. **Agent unioned all buildings first** then computed a single
   centroid. *Detection:* `row_count_within_tolerance` subcheck fails
   (1 vs 122), as do the id-keyed distance subchecks. Not covered by a
   broken solution; principled detector is the row-count subcheck.

## Expected weak-agent failure mode

The likeliest weak-agent failure is **#1 / #6** — applying GeoPandas'
default `.centroid` accessor on a GeoDataFrame loaded straight from
the shapefile *without* reading the `.prj` (so the geometry is in
metres but the agent assumes degrees), and then writing GeoJSON
without an explicit `to_crs(4326)`. Under the soft-CRS grader this
costs the `crs_is_canonical` subcheck (≈ 0.947 if everything else is
right). A more careful agent that reprojects but forgets the truncated
`building_i` column will trip Gate 1 on the missing-column check
instead.
