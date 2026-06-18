# crs-l1-paris-lambert93

## What this task probes

CRS-reprojection literacy on a real French study area. The agent must
recognise that RGF93 / Lambert-93 (EPSG:2154) is the official metric
projected CRS for mainland France, take a small WGS84 GeoJSON of Paris
(Marais) building footprints, and reproject it into EPSG:2154 without
disturbing the polygon-level geometry, identifiers, or attribute payload.
Pure reprojection — no filtering, joining, computation, or geometry edits.

## Why this difficulty

L1: a single primary operation (reproject) on a fully bundled file. No
fetching, no data-quality issues, no chained operations. The persona's
question admits exactly one correct answer family — every correctly
reprojected building has a deterministic Lambert-93 geometry given
pyproj/PROJ's behaviour on EPSG:4326 → EPSG:2154.

## Input / output formats

### Input

`data/paris_buildings_wgs84.geojson` — 330 features in EPSG:4326. All
geometries are `Polygon`. Schema:

| Field | Type | Description |
|---|---|---|
| `id` | string | Overture stable feature id |
| `class` | string | Building class (`apartments`, `hotel`, ...); blank where Overture lacks the value |
| `subtype` | string | Overture sub-classification (`residential`, `commercial`, ...) |
| `name` | string | Primary name where Overture has one (e.g. `Hôtel de Nice`); blank otherwise |
| `height` | float64 | Roof height in metres; mostly NaN in this slice |
| `num_floors` | float64 | Floor count; populated for ~⅔ of features |

### Output

`outputs/paris_buildings_lambert93.gpkg`. Same 330 features in EPSG:2154
with identical schema. Geometries are reprojected from WGS84 degrees to
Lambert-93 metres and written as a GeoPackage so the CRS is embedded in
the file itself (no RFC 7946 friction).

## Failure modes

1. **Forget to reproject (output still EPSG:4326).** *Detection:* the
   `crs_is_canonical` and `crs_in_meaningful_set` subchecks both fail.
   The soft CRS grader reprojects the submission to Lambert-93 before the
   geometric subchecks run, so a forgot-to-reproject still scores partial
   credit on geometry while losing both CRS subchecks. Covered by
   `broken_wrong_format`.
2. **Stamp the CRS as 2154 but leave coordinates in WGS84 degrees.** A
   weak agent who reaches for `set_crs` instead of `to_crs` produces a
   file that opens cleanly with `2154` metadata but whose geometries are
   still at lon=2°, lat=49°. *Detection:*
   `coordinates_within_lambert93_paris_envelope` (degrees fall outside
   the 6e5 / 6.86e6 metres band); `geometry_iou_high` (zero overlap);
   `per_feature_area_matches` and `total_area_within_1_percent` (areas
   in degrees² are ~1e-10 of the m² reference). Covered by
   `broken_wrong_crs`.
3. **Drop the non-string columns (`height`, `num_floors`)** when
   round-tripping through a thinned GeoDataFrame. *Detection:*
   `original_columns_preserved` subcheck fails. The `class` / `subtype` /
   `name` string attributes still match because the SUT carried them
   through. Covered by `broken_wrong_attributes`.
4. **Reproject into the wrong target CRS** (e.g., into UTM 31N instead of
   Lambert-93, both metric and Paris-friendly, so a confused agent could
   pick the wrong one and not notice). *Detection:* the `crs_is_canonical`
   subcheck fails for any CRS other than EPSG:2154, while UTM 31N stays in
   the meaningful set and still earns `crs_in_meaningful_set`. Not covered
   by a broken solution; the two CRS subchecks are the principled
   detectors.
5. **Filter or drop features by mistake** (e.g., only keep `class =
   'apartments'` rows). *Detection:* the `feature_count_within_5_percent`
   subcheck catches gross filters and the `feature_id_set_preserved`
   subcheck (Jaccard ≥ 0.95) catches subtler set differences. Not covered
   by a broken solution; both detectors are principled.
6. **Reproject correctly but write geometry as `MultiPolygon`** by upcasting
   every polygon. *Detection:* `geometry_type_is_polygon` subcheck fails
   (MultiPolygon is allowed at the structural gate but only Polygon-only
   earns the subcheck). Not covered by a broken solution.
7. **Reproject geometry but lose topology** (e.g., aggressive simplify or
   centroid replacement). *Detection:* `geometry_iou_high` collapses;
   `per_feature_area_matches` and `total_area_within_1_percent` flag the
   scale change. Not covered by a broken solution; the IoU + area
   subchecks are the principled detectors.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#2, stamps the CRS as 2154
without actually transforming coordinates**. WGS84 and Lambert-93 share
no common origin and the discrepancy is enormous, but a careless agent
who maps "set the CRS to EPSG:2154" to `gdf.set_crs(2154,
allow_override=True)` produces an output that opens cleanly with 2154
metadata but holds garbage spatial content. The grader awards 0.52 for
this failure (the high-weight envelope plus the IoU / per-feature area /
total-area subchecks fail; the gate, feature-count, geom-type, id-set,
attributes, columns, and both CRS-declaration subchecks pass) so it is
clearly distinguishable from a correct solution (1.0), from a
missing-attributes solution (0.97), and from a forgot-to-reproject
solution (0.66). Note the silent-corruption file (0.52) scores *below*
the forgot-to-reproject file (0.66): the envelope is weighted as a
CRS-correctness check (it proves the reprojection happened), so stamping
the right label while leaving the coordinates in degrees is penalised
harder than honestly leaving the file in EPSG:4326.
