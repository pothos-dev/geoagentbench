# crs-l1-nyc-webmercator-cycleways

## What this task probes

CRS-reprojection literacy on web-tile data: the agent must recognise
EPSG:3857 (Web Mercator) as a projected metric CRS that needs to be
transformed back to EPSG:4326 (WGS84 lat/lon) before a Leaflet client can
ingest it, then perform that reprojection without disturbing the segment-
level geometry, identifiers, or attribute payload. Pure reprojection — no
filtering, joining, computation, or geometry edits.

## Why this difficulty

L1: a single primary operation (reproject) on a bundled file. No fetching,
no data-quality issues, no chained operations. The persona's question
admits exactly one correct answer family — every correctly reprojected
LineString has a deterministic WGS84 geometry given pyproj/PROJ's behaviour
on EPSG:3857 → EPSG:4326.

## Input / output formats

### Input

`inputs/nyc_cycleways_webmercator.geoparquet` — 272 features in EPSG:3857
(Web Mercator). All geometries are `LineString`. Schema:

| Field | Type | Description |
|---|---|---|
| `id` | string | Overture stable feature id |
| `class` | string | `cycleway` for every feature (filter predicate) |
| `subclass` | string | `cycle_crossing` or empty (Overture sub-classification) |
| `name` | string | Street / trail name (e.g. `East River Greenway`); blank for unnamed segments |

### Output

`outputs/nyc_cycleways_wgs84.geoparquet` — same 272 features in EPSG:4326,
identical schema. Geometries are reprojected from 3857 metres to lat/lon.

## Failure modes

1. **Forget to reproject (output still EPSG:3857).** *Detection:* the
   submission keeps a usable CRS so the hard gate passes; the grader
   reprojects it to EPSG:4326 for the geometric subchecks (which then
   pass), but the `crs_is_canonical` and `crs_in_meaningful_set`
   subchecks each dock a point for the non-4326 declaration. The closer
   broken-set match is `broken_wrong_crs` below for the case where the
   SUT only restamps the CRS without doing the math.
2. **Stamp the CRS as 4326 but leave coordinates in Web Mercator metres.**
   *Detection:* `coordinates_within_nyc_lonlat_envelope` subcheck (metres
   are at -8.2e6 / 5.0e6, far outside the NYC lon/lat box); `geometry_iou_high`
   (zero overlap with the reference); `per_feature_length_matches` and
   `total_network_length_within_1_percent` (lengths come out wrong because
   the geometry is on the wrong manifold). Covered by
   `broken_wrong_crs`.
3. **Save in the wrong format** (GeoJSON / Shapefile / plain Parquet without
   the geo metadata block). *Detection:* the hard gate's `gpd.read_parquet`
   call fails on the bytes. Covered by `broken_wrong_format`.
4. **Drop identifying attributes** during round-trip (e.g., reproject via
   `to_crs` on a geometry-only Series and lose `class` / `name`).
   *Detection:* `identifying_attributes_preserved` subcheck. Covered by
   `broken_wrong_attributes`.
5. **Drop or split features** (e.g., explode multi-vertex LineStrings into
   per-segment rows, or filter to a subclass). *Detection:* the
   `feature_count_within_5_percent` subcheck catches the gross filter
   case; the `feature_id_set_preserved` subcheck (Jaccard ≥ 0.95) catches
   subtler set differences. Not covered by a broken solution; the count
   subcheck is the principled detector.
6. **Reproject into the wrong target CRS** (e.g., into UTM 18N instead of
   WGS84 — both are metric, so a confused agent could pick the wrong one
   and not notice). *Detection:* the grader reprojects the submission to
   EPSG:4326 before the geometric subchecks, and the `crs_is_canonical`
   and `crs_in_meaningful_set` subchecks each dock a point for the
   non-4326 declaration. Not covered by a broken solution.
7. **Reproject correctly but write geometry as `MultiLineString` or
   collapse to a centroid `Point`.** *Detection:* `geometry_type_is_linestring`
   subcheck (only a `LineString`-only output earns it); a Point output
   additionally fails the IoU and length subchecks. Not covered by a
   broken solution; the geom-type subcheck is the detector.
8. **Reproject geometry but lose the line topology** (e.g., simplify
   aggressively, snapping to integer degrees). *Detection:* `geometry_iou_high`
   subcheck on the buffered network; `per_feature_length_matches` (a
   simplified line is shorter). Not covered by a broken solution.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#2 — the SUT relabels the CRS to
EPSG:4326 without actually transforming coordinates**. Web Mercator and
WGS84 share a common ancestor and a careless agent can `set_crs` instead
of `to_crs`. The grader awards 0.30 for this failure: the four
coordinate-proof subchecks fail (envelope weight 4, IoU weight 4,
per-feature length weight 3, total-length weight 3 - 14 of 20 weighted
points), while count, id-set, geom-type, attribute, and the two CRS-label
subchecks still pass. Those coordinate-proof subchecks carry the bulk of
the weight because they prove the reprojection actually happened, so this
dishonest "stamped 4326 but never transformed" file scores far below an
honestly-unprojected file (which loses only the two cheap CRS-label
subchecks, approximately 0.95). It is thus clearly distinguishable from a
correct solution (1.0), from a missing-attributes solution (0.90), and from
a wrong-format solution (0.0).
