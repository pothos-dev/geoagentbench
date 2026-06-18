# crs-l1-london-laea-areas

## What this task probes

**Unprompted CRS reasoning for area calculation.** The agent receives a WGS84
GeoJSON of London-area admin polygons and is asked to compute their area in
square kilometres — but is given no guidance on which coordinate reference
system to use. The instruction asks only for a CSV output with `id`, `name`,
and `area_km2`.

The agent must independently recognise that computing `.area` on geographic
(lat/lon) coordinates produces values in degrees² — meaningless for area — and
choose an appropriate projected CRS (e.g. EPSG:3035 LAEA Europe, EPSG:27700
British National Grid, a UTM zone, or geodesic area via pyproj) before
computing the area. This tests the model's geospatial literacy without
hand-holding.

## Why this difficulty

L1: a single primary operation (area calculation) on fully bundled data, no
fetching, no data-quality issues. The twist — "you must reproject before
computing area, but nobody told you to" — is the skill being tested.

## Input / output formats

### Input

`inputs/london_admin.geojson` — 232 features in EPSG:4326. Each feature
is a `Polygon` (231) or `MultiPolygon` (1) with these attributes:

| Field | Type | Description |
|---|---|---|
| `id` | string | Overture stable feature id |
| `name` | string | English name (e.g. `Westminster`, `Bromley`) |
| `subtype` | string | `county` (33 London boroughs) or `locality` (199 surrounding civil parishes / small towns in the home counties) |
| `country` | string | `GB` for every feature |

### Output

`borough_areas.csv` — 232 rows.

| Field | Type | Description |
|---|---|---|
| `id` | string | preserved from input |
| `name` | string | preserved from input |
| `area_km2` | float64 | polygon area in km², computed in an appropriate projected CRS |

## Failure modes

1. **Agent computed area in WGS84 degrees².** The `.area` values are in
   degrees², off by ~10 orders of magnitude from km². This is the primary
   failure the task is designed to catch.
   *Detection:* `area_km2_per_feature_matches` and `total_area_within_2_percent`
   subchecks both fail. Covered by `broken_degrees_area`.
2. **Agent reprojected but reported area in m² instead of km².**
   *Detection:* area subchecks fail (off by factor 1e6). Covered by
   `broken_area_m2`.
3. **Agent wrote the wrong output format** (GeoJSON, Parquet, etc.).
   *Detection:* Gate 1 rejects (missing CSV file). Covered by
   `broken_wrong_format`.
4. **Agent dropped or mangled the id/name columns.**
   *Detection:* `feature_id_set_preserved` or `name_attribute_preserved`
   subchecks fail.
5. **Agent filtered out features** (e.g. only kept London boroughs).
   *Detection:* `row_count_within_5_percent` and `feature_id_set_preserved`
   subchecks fail.

## Expected weak-agent failure mode

The likeliest failure is **#1** — the agent calls `gdf.geometry.area` while
the GeoDataFrame is still in EPSG:4326 and writes the degrees² values as
`area_km2`. A geospatially literate agent recognises that WGS84 `.area` is
not meaningful and reprojects to an appropriate CRS first.

## Grader tolerance

The grader uses a 2 % per-feature tolerance to accept any reasonable
projection choice (LAEA Europe, UTM, OSGB, geodesic area). All such
projections agree to well under 1 % for London-sized features; the 2 % floor
provides margin for minor numerical differences across PROJ pipelines.
