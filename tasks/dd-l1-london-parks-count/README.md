# dd-l1-london-parks-count

## Story

Priya Shah, a data analyst on the Greater London Authority's parks
team, is sizing the green-space corpus before commissioning an
accessibility study. She has a FlatGeobuf snapshot of OSM-style park
polygons in inner London, in EPSG:27700 (British National Grid), and
needs to know how many parks exceed 1 hectare, what their combined
area is in hectares, and the WGS84 bounding box of that subset — so
the procurement officer can pick a study perimeter without having to
open QGIS.

## What this task probes

FlatGeobuf reading + planar-area filtering in a projected CRS
(EPSG:27700) + unit conversion (m² → ha) + bbox computation on a
*subset* of features + reprojection of that bbox to EPSG:4326,
serialised as a small JSON summary. The skill being measured is basic
literacy in a binary indexed vector format and the matching
three-line summary that a real analyst would compute before
commissioning a downstream study.

## Why this difficulty

L1: a single primary GIS operation (attribute / area filter) wrapped
in three trivial reductions (count, sum, bbox) over a fully bundled
FlatGeobuf fixture. No fetching, no chained transforms, no spatial
joins, no data-quality issues to detect. The only twist is that the
input CRS (EPSG:27700) and the output CRS (EPSG:4326) differ — a
single one-line reprojection step.

## Input / output formats

### Input

`inputs/london_parks.fgb` — 317 polygon features, EPSG:27700, with
columns:

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable Overture feature id |
| `name` | string | Park name (may be empty) |
| `class` | string | Overture land-use class — always `park` here |
| `geometry` | Polygon / MultiPolygon | Park footprint, EPSG:27700 |

Of the 317 polygons, 42 have area ≥ 1 ha (10 000 m²). The Royal Parks
(Hyde, Regent's, Green, St James's, Kensington Gardens) plus a
healthy spread of neighbourhood parks both above and below the
threshold are included.

### Output

`outputs/parks_summary.json` — single JSON object with three
top-level keys:

```json
{
  "count": 42,
  "total_area_ha": 519.1621,
  "bbox_wgs84": [xmin, ymin, xmax, ymax]
}
```

`bbox_wgs84` is a 4-list of floats in EPSG:4326 in
`[xmin, ymin, xmax, ymax]` order (longitude first).

## Failure modes

1. **Agent forgot the ≥ 1 ha filter** and reported summary stats
   over all 317 parks. *Detection:* `count_correct` (317 ≠ 42),
   `total_area_ha_correct` (~14 % over), three of four
   `bbox_*_correct` (the unfiltered set extends slightly further on
   three corners). Covered by `broken_wrong_filter` (score 0.143).
2. **Agent forgot the m² → ha unit conversion** and reported
   `total_area_ha` as the raw m² number (~5 191 621 instead of
   ~519). *Detection:* `total_area_ha_correct` fails by 10 000×,
   well outside the 1 % tolerance. Covered by `broken_wrong_units`
   (score 0.714).
3. **Agent computed area in geographic degrees** (filtered on
   `geometry.area` while still in EPSG:4326) without reprojecting,
   so "≥ 1 ha" was interpreted as "≥ 1 deg²" — astronomically
   wrong. *Detection:* `count_correct` returns 0; `total_area_ha`
   either crashes or reports 0; one or more bbox subchecks fail.
   Not covered by a broken solution; the principled detectors are
   `count_correct` + `total_area_ha_correct`.
4. **Agent forgot to reproject the bbox** to EPSG:4326 and
   reported it in EPSG:27700 (metre coordinates ~ 5×10⁵ easting,
   ~ 1.8×10⁵ northing). *Detection:* all four bbox componentwise
   subchecks fail by ~10⁵, AND `bbox_in_wgs84_range` fails because
   the metre-scale northing is outside `[-90, 90]` lat. Not covered
   by a broken solution; the principled detector is the four bbox
   subchecks plus the range subcheck.
5. **Agent swapped lon and lat in the bbox** (`[ymin, xmin, ymax,
   xmax]` instead of `[xmin, ymin, xmax, ymax]`). *Detection:* all
   four bbox componentwise subchecks fail (deltas ~ 50°), but
   `bbox_in_wgs84_range` still passes (the swap stays inside lon /
   lat extents). Not covered by a broken solution; principled
   detector is the four bbox subchecks.
6. **Agent computed bbox over the unfiltered set** but counted
   correctly. *Detection:* one or more of the four bbox subchecks
   fail; `count_correct` and `total_area_ha_correct` still pass.
   Not covered by a broken solution; principled detectors are the
   bbox componentwise subchecks.
7. **Agent wrote the summary in the wrong format** (CSV, plain
   text, a JSON shape with different top-level keys). *Detection:*
   Gate 1 rejects (cannot parse as JSON object, or required keys
   missing). Covered by `broken_wrong_format` (score 0.000).
8. **Agent picked the wrong area threshold** (e.g. ≥ 0.1 ha
   reading "1" as "1 km²"). *Detection:* `count_correct` and
   `total_area_ha_correct` both fail. Not covered by a broken
   solution; principled detectors are the count and area subchecks.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#2 — m² → ha unit slip**.
The shortest-string completion of "compute total area in hectares"
on a GeoPandas GeoSeries is `gdf.geometry.area.sum()`, which returns
m² in EPSG:27700. An agent that forgets the `/ 10_000` factor
delivers a structurally perfect output that fails on exactly one
subcheck and scores 0.714 — clearly distinguishable from a
no-filter solution (0.143), a wrong-format solution (0.0) and a
correct solution (1.000).
