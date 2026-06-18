# geo-l1-cairo-multipoint-hull

## Story

Hatem Ibrahim, a service-area analyst at the Cairo Metro Authority, has
a station inventory in which each Metro station is a single MultiPoint
geometry listing all of that station's street-level entrance
coordinates. For an upcoming accessibility report he needs the convex
hull of each station's entrances — a coarse "footprint" of how widely
the underground station box extends — so the report's static maps can
show the spatial reach of every station while preserving the bilingual
Arabic / English station names.

## What this task probes

Per-feature **convex hull** on MultiPoint geometries plus attribute
preservation across the operation. The skill is recognising that the
right answer is a *per-row* hull (one polygon per station MultiPoint)
rather than a single hull over the entire dataset, and that the
geometric operation must not lose the two non-geometric columns the
persona explicitly named.

## Why this difficulty

L1: a single primary GIS operation (`convex_hull` per row) on a fully
bundled 20-station GeoJSON. No fetching, no chained transforms, no
projection — input and output are both EPSG:4326. The only twist is
the per-row vs. global hull distinction; everything else is mechanical
attribute carry-through.

## Input / output formats

### Input

`inputs/cairo_metro_stations.geojson` — GeoJSON FeatureCollection,
EPSG:4326, 20 features.

| Field | Type | Notes |
|---|---|---|
| `station_name_en` | string | English transliteration |
| `station_name_ar` | string | Arabic name (RTL UTF-8) |
| `geometry` | MultiPoint (EPSG:4326) | 3–5 entrance points per station |

### Output

`outputs/cairo_metro_hulls.geojson` — GeoJSON FeatureCollection,
EPSG:4326, 20 features.

| Field | Type | Notes |
|---|---|---|
| `station_name_en` | string | preserved verbatim |
| `station_name_ar` | string | preserved verbatim |
| `geometry` | Polygon (EPSG:4326) | convex hull of the input MultiPoint |

## Failure modes

1. **Agent wrote a non-GeoJSON file** (CSV, Parquet, raw WKT). *Detection:*
   Gate 1 rejects (cannot parse / required columns absent). Covered by
   `broken_wrong_format` (score 0.000).
2. **Agent returned the axis-aligned bounding box of each MultiPoint
   instead of the convex hull.** *Detection:*
   `hull_iou_against_reference` fails — bbox is ~30 % larger than the
   hull on 4–5-point inputs, dropping per-station IoU below 0.95.
   Covered by `broken_bbox_instead_of_hull` (score 0.783).
3. **Agent blanked the Arabic name column** (e.g. UTF-8 → CSV
   roundtrip mangled it and they refilled with empty strings to keep
   the schema). *Detection:* `station_name_ar_populated` and
   `arabic_names_match` both fail. Covered by `broken_empty_arabic`
   (score 0.826).
4. **Agent collapsed all stations into a single global convex hull.**
   *Detection:* `row_count_within_tolerance` subcheck fails (1 vs 20
   ≫ 5 % tolerance), and the per-station subchecks collapse with it.
   Not covered by a broken solution; principled detector is the
   row-count subcheck.
5. **Agent reprojected to a metric CRS** (e.g. EPSG:22992 for Cairo)
   before writing without converting back. *Detection:* CRS-soft
   grading reprojects the submission back to WGS84 for the geometric
   subchecks but docks `crs_is_canonical` and `crs_in_meaningful_set`.
   Not covered by a broken solution; principled detector is the CRS
   subcheck pair.
6. **Agent buffered each MultiPoint** (e.g. 50 m circle around each
   point, then unioned per station) instead of taking the hull.
   *Detection:* `hull_iou_against_reference` fails — the buffered
   union is much larger than the hull. Not covered by a broken
   solution; principled detector is the IoU subcheck.
7. **Agent paired the right hull with the wrong attribute row** (sort
   mismatch between hull and attribute columns). *Detection:*
   `hull_contains_input_points` fails — a swapped hull will not cover
   its claimed station's entrance MultiPoint. Not covered by a broken
   solution; principled detector is the containment subcheck.
8. **Agent returned each MultiPoint unchanged** (no operation
   applied). *Detection:* `geometry_types_polygon` subcheck fails
   (output is MultiPoint, not Polygon), and the IoU subcheck fails
   with it. Not covered by a broken solution; principled detector is
   the geometry-type subcheck.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 / #6 — applying a global
operation instead of a per-row one**, e.g.
`gpd.GeoSeries(unary_union(gdf.geometry).convex_hull)` returning a
single polygon over all entrances combined. That collapses 20 rows to
1 and trips the row-count subcheck immediately. A more careful
agent that applies the right operation but forgets that GeoPandas'
default `convex_hull` works element-wise might still trip on column
loss if they reach for `unary_union` from shapely, dropping the two
attribute columns en route.
