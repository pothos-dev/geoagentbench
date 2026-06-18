# geo-l1-tokyo-busstop-buffer

## Story

Hiroshi Sato, a service planner at Tokyo Metro Co., is updating the
400 m walkable-catchment layer for stations and bus connectors after
a timetable revision. He needs a 400 m buffer around every connector,
exported as GeoParquet so the planning team's Python notebooks can
join it directly against the ridership table the controllers maintain.

## What this task probes

**Unprompted CRS reasoning for metric buffering.** The agent receives a
WGS84 GeoJSON of Tokyo connector points and is asked to create a 400 m
buffer around each — but is given no guidance on coordinate reference
systems. The agent must independently recognise that buffering 400 in
WGS84 means 400 *degrees* (not metres) and choose an appropriate projected
CRS (e.g. EPSG:6677 JGD2011 Plane IX, EPSG:32654 UTM 54N) for metric
buffering.

## Why this difficulty

L1: a single primary GIS operation (`buffer(400)` per row) on a fully
bundled 300-connector GeoJSON. No fetching, no chained transforms, no
attribute joins. The twist — "you must reproject before buffering, but
nobody told you to" — is the skill being tested.

## Input / output formats

### Input

`inputs/tokyo_connectors.geojson` — GeoJSON FeatureCollection,
EPSG:4326 (WGS84), 300 features.

| Field | Type | Notes |
|---|---|---|
| `connector_id` | string | Overture connector id (UUID-style). |
| `geometry` | Point (EPSG:4326) | junction points sliced from Overture 2026-04-15.0. |

### Output

`outputs/tokyo_stop_catchments.geoparquet` — GeoParquet, 300 features.
No output CRS specified — the model chooses.

| Field | Type | Notes |
|---|---|---|
| `connector_id` | string | preserved verbatim |
| `geometry` | Polygon | per-feature 400 m planar buffer |

## Failure modes

1. **Agent buffered in WGS84 degrees without reprojecting.** Calling
   `.buffer(400)` on WGS84 data creates buffers of 400 *degrees* radius
   — enormous polygons.
   *Detection:* `buffer_area_400m` fails (areas vastly wrong after
   reprojection to reference CRS); `per_id_iou_high` fails. Covered by
   `broken_degrees_buffer` (score 0.31).
2. **Agent buffered with the wrong radius** (200 m, 1 km).
   *Detection:* `buffer_area_400m` and `per_id_iou_high` both fail.
   Covered by `broken_wrong_radius` (score 0.50).
3. **Agent paired buffers with shifted centres** (wrong geometry column,
   off-by-one join).
   *Detection:* `per_id_iou_high` and `buffer_contains_source_point` fail.
   Covered by `broken_shifted_centers` (score 0.31).
4. **Agent wrote the wrong file format** (CSV with WKT, GeoJSON, etc.).
   *Detection:* Gate 1 rejects. Covered by `broken_wrong_format` (score 0.0).
5. **Agent dropped the `connector_id` column.**
   *Detection:* Gate 1 rejects (missing required column).
6. **Agent emitted Point geometry instead of buffering.**
   *Detection:* `geometry_types_polygonal` subcheck fails.
7. **Agent filtered out connectors.**
   *Detection:* `row_count_within_tolerance` subcheck fails.

## Expected weak-agent failure mode

The likeliest failure is **#1** — the agent calls `gdf.geometry.buffer(400)`
while the GeoDataFrame is still in EPSG:4326, producing buffers of 400
*degrees* radius. A geospatially literate agent recognises that the input
is in WGS84, that metric buffering requires a projected CRS, and reprojects
to an appropriate CRS for Tokyo before buffering.

## Grader tolerance

The grader reprojects the submission to EPSG:6677 (the reference CRS) for
all geometric comparisons. Area tolerance is ±2% of π·400² to accept any
reasonable projected CRS. IoU threshold is 0.95 to accommodate minor
projection differences.
