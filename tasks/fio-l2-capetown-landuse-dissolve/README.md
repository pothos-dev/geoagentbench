# fio-l2-capetown-landuse-dissolve

## Story

Sipho Dlamini, a transport-equity researcher at the University of
Cape Town, has a parcel-level OSM `landuse=*` extract for the
metropolitan area in FlatGeobuf. He's preparing inputs for a
transit-corridor study and wants a tidy class-level summary the
team's spatial-SQL notebooks can join directly against the bus-route
table. Each landuse class collapsed into a single MultiPolygon, with
the total area and source-parcel count carried as attributes,
exported as GeoParquet.

## What this task probes

Format-I/O composition: attribute-grouped dissolve + collect (single
→ multi) + format conversion (FlatGeobuf → GeoParquet) + per-class
attribute computation. The skill is composing four operations into
one correct GeoParquet table, while keeping the input CRS
(EPSG:32734) and producing the expected MultiPolygon geometry kind.

## Why this difficulty

L2: a chain of operations on bundled data. The dissolve is the
primary geometric op; collecting per-group geometries to a single
MultiPolygon, computing per-group area and count, and emitting
GeoParquet round it out. No fetching, no spatial analysis. The task
ships entirely from `inputs/capetown_landuse.fgb`.

## Input / output formats

### Input

`inputs/capetown_landuse.fgb` — a FlatGeobuf in EPSG:32734 carrying
~30 000 land-use parcels across 72 distinct classes for the Cape
Town metropolitan area, sliced from Overture's `base.land_use`
release 2026-04-15.0. Columns: `id`, `class`, `subtype`, `geometry`.

### Output

`outputs/landuse_dissolved.geoparquet` — a GeoParquet with one row
per landuse class:

| Column | Type | Description |
|---|---|---|
| `class` | str | Landuse class value (e.g. `residential`, `vineyard`). |
| `parcel_count` | int | Number of input parcels in the class. |
| `area_m2` | float | Total dissolved area in projected metres². |
| `geometry` | MultiPolygon | Dissolved geometry of the class, collected to a single MultiPolygon. |

CRS: EPSG:32734. 72 rows.

## Failure modes

1. **Agent did not produce a GeoParquet at all** (e.g. left the
   output as the original FlatGeobuf, or wrote a CSV / GeoJSON).
   *Detection:* the `format_schema_valid` gate rejects
   (`gpd.read_parquet` fails). Covered by `broken_wrong_format`
   (score 0.000).
2. **Agent produced a GeoParquet but in the wrong CRS** (e.g.
   reprojected to EPSG:4326 before writing). *Detection:* the
   grader reprojects the submission to EPSG:32734 for the geometric
   subchecks and docks the `crs_is_canonical` and
   `crs_in_meaningful_set` subchecks. The gate only rejects when no
   usable CRS is declared at all. Not covered by a broken solution;
   principled detectors are the CRS subchecks.
3. **Agent forgot to collect** and kept one row per (class,
   sub-polygon) so the geometry column is `Polygon` rather than
   `MultiPolygon`. *Detection:* `multipolygon_only` subcheck fails;
   `one_row_per_class` may also fail; row count far above 72 also
   trips the row-count subcheck. Not covered by a broken solution;
   principled detectors are the geometry-type and row-count
   subchecks.
4. **Agent reported `area_m2` in the wrong units** (e.g. km², or
   computed area in the geographic CRS in degrees² before
   reprojecting). *Detection:* `area_m2_per_class_within_tolerance`
   fails; all other subchecks still pass. Covered by
   `broken_wrong_area_units` (score 0.824).
5. **Agent dropped the long tail of small classes** (kept only top
   N by parcel count). *Detection:* `class_set_jaccard`,
   `unioned_geometry_iou`, and `row_count_within_tolerance` fail
   simultaneously; per-class subchecks pass on the retained subset.
   Covered by `broken_partial_classes` (score 0.588).
6. **Agent omitted a required column** (`parcel_count`, `area_m2`,
   or `class`). *Detection:* the `format_schema_valid` gate's
   required-columns check rejects. Not covered by a broken
   solution; principled detector is the gate.
7. **Agent wrote one row per parcel** (skipped the dissolve
   entirely). *Detection:* either the gate rejects (no
   `parcel_count`/`area_m2` columns) or, if the agent invented
   per-row 1-and-area values, the row-count subcheck fails
   (~31 k vs reference 72) along with the per-class subchecks.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#4 — reporting area in km²
or otherwise mis-scaling the area column**. A baseline that
correctly dissolves and collects but reaches for `.area / 1e6` (a
common reflex when the human said "summary") trips the
`area_m2_per_class_within_tolerance` subcheck and lands at 0.824.
The next-most-likely is **#3 — forgetting the collect step** and
shipping mixed Polygon/MultiPolygon rows; that fails the
`multipolygon_only` subcheck (and the row-count subcheck if the
agent also kept one row per sub-polygon).
