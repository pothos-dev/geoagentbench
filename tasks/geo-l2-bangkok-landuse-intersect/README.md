# geo-l2-bangkok-landuse-intersect

## Story

Praphan Wongsa, a planner at the Bangkok Metropolitan Administration,
is preparing a green-cover briefing for an inter-agency
flood-mitigation working group. He has an Overture-style
`base.land_cover` sample for the Bangkok metro in WGS84 / UTM 47N
(EPSG:32647) and a single study-area polygon for the BMA boundary.
Several of the input polygons have self-intersecting rings that crash
his desktop GIS. He needs the agent to repair the bad geometries,
intersect the cleaned land-cover with the study-area polygon,
simplify at a 5 m tolerance for browser preview, and export GeoJSON
with per-feature `class` and `area_m2`.

## What this task probes

Geometric-ops composition: invalid-geometry repair (`make_valid`) →
overlay (intersection against a single study polygon) → MultiPolygon
coercion → planar simplify at a metric tolerance → per-feature area
computation → reproject to WGS84 for the GeoJSON write. The skill is
chaining four geometric operations correctly while preserving an
attribute column from the input and reporting `area_m2` in projected
metres² even though the geometry is written in WGS84.

## Why this difficulty

L2: a 4-step chain (`make_valid` → intersect → simplify → coerce) on
bundled data. No fetching, no spatial-analysis primitives. The
invalid-geometry repair sits before the overlay so an agent that
skips repair either crashes or silently drops features — the
ordering is part of the test.

## Input / output formats

### Inputs

`inputs/bangkok_landcover.parquet` — GeoParquet, EPSG:32647, ~21 660
polygons / MultiPolygons across 8 land-cover classes (`barren`,
`shrub`, `forest`, `crop`, `urban`, `wetland`, `mangrove`, `grass`).
Sliced from Overture release 2026-04-15.0. Columns: `id`, `class`,
`geometry`. **25 features have intentionally injected
self-intersecting rings**.

`inputs/bma_study_area.geojson` — GeoJSON, EPSG:32647, a single
hand-crafted polygon (~1 254 km²) approximating the BMA boundary as
an irregular octagon. One feature with a `name` attribute.

### Output

`outputs/bma_landcover_intersect.geojson` — GeoJSON, WGS84
(EPSG:4326), one row per land-cover feature with a non-empty
intersection against the study area:

| Column | Type | Description |
|---|---|---|
| `id` | str | Original Overture id (carried through). |
| `class` | str | Original land-cover class. |
| `area_m2` | float | Area of the clipped+simplified MultiPolygon, in projected metres². |
| `geometry` | MultiPolygon | Cleaned, clipped, and simplified MultiPolygon. |

Reference produces 3 453 features totalling ~980 km² of intersected
land-cover area inside the BMA study area.

## Failure modes

1. **Output not a GeoJSON** (e.g. agent emitted GeoParquet, CSV, or
   a Shapefile under the expected name). *Detection:* Gate 1's
   GeoJSON-FeatureCollection sniff rejects. Covered by
   `broken_wrong_format` (score 0.000).
2. **Output in the wrong CRS** (e.g. left in the projected EPSG:32647
   instead of reprojecting to WGS84 before writing). *Detection:*
   under the soft-CRS grader the submission is reprojected to WGS84
   for the geometric subchecks and loses the `crs_is_canonical` and
   `crs_in_meaningful_set` subchecks (2/15 of the weighted score).
   Not covered by a broken solution; principled detector is the
   subcheck pair.
3. **Skipped the intersection** — agent repaired and simplified but
   shipped the un-clipped land-cover (perhaps with a study-area-bbox
   prefilter only). *Detection:*
   `count_within_tolerance`, `total_area_within_tolerance`, and
   `unioned_geometry_iou` all fail; class set still matches.
   Covered by `broken_not_intersected` (score 0.133).
4. **Reported area in km² (or some other wrong unit)** — agent
   intersected and simplified correctly but mis-scaled the area.
   *Detection:* `total_area_within_tolerance` fails; everything else
   passes. Covered by `broken_area_in_km2` (score 0.600).
5. **Did not repair invalid geometries before intersecting** —
   shapely.intersection on a bowtie either raises a TopologyException
   (older GEOS) or silently produces a wrong result. The agent will
   either crash or under-count by ~25 features (~0.7 %) — within the
   ±5 % count tolerance but a real silent-correctness issue.
   *Detection:* not covered by a broken solution; principled
   detector is the bundled-input promise that 25 features need
   repair, plus the count-tolerance subcheck which catches the
   over-aggressive variants where many bowties cascade into bigger
   drops.
6. **Forgot to coerce to MultiPolygon** — output is a mix of Polygon
   and MultiPolygon (or all Polygon). *Detection:* `all_multipolygon`
   subcheck fails. Not covered by a broken solution; principled
   detector is the subcheck.
7. **Dropped the `class` or `area_m2` column.** *Detection:* Gate 1's
   required-columns check rejects. Not covered by a broken solution;
   principled detector is the gate.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#3 — skipping the
intersection step entirely**. A baseline that reads both files,
runs `make_valid`, simplifies at 5 m, and ships the result without
running `gpd.overlay(..., how='intersection')` ends up with the full
21 k features (or after a bbox prefilter, ~6 k features), which
fails the three central geometric subchecks (count w3, total_area w4,
IoU w4) for a low score (0.133 if the CRS is also left projected, since
the two CRS subchecks then fail too). The next-most-likely is
**#4 — reporting area in km²** (a common reflex when the human
mentions a "browser preview" / "small file"), which lands at
~0.60-0.73 (only the area subcheck plus the CRS pair fail). In practice
the most common live failure observed across recent runs is **#2 —
leaving the output in EPSG:32647**, which the soft-CRS grader prices at
13/15 = 0.867.
