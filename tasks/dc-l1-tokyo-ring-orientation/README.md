# dc-l1-tokyo-ring-orientation

## What this task probes

Ring-orientation repair under RFC 7946 §3.1.6. The bundled GeoJSON of
Tokyo building footprints encodes polygon rings in OGC orientation —
exterior rings are clockwise, interior rings are counter-clockwise. RFC
7946 §3.1.6 mandates the opposite ("right-hand rule"): exteriors
counter-clockwise, interiors clockwise. The agent must read the
malformed file, re-orient every polygon to comply with RFC 7946,
preserve every attribute and the geometric shape exactly, and write the
result back as GeoJSON in EPSG:4326. No projection, no filtering, no
geometric edit beyond reversing ring vertex order — pure data cleaning.

## Why this difficulty

L1: a single primary operation (ring re-orientation) on a fully bundled
input. No fetching, no chained operations, no projection-sensitive
numerics. The persona's question admits exactly one correct answer
family — every correct solution produces the same geometric extent, the
same set of feature_ids, and the same attributes, with every exterior
ring CCW and every interior ring CW.

## Input / output formats

### Input

`inputs/tokyo_buildings_legacy.geojson` — 100 building footprints in
EPSG:4326, all `Polygon` geometry. Five fixed features (`feature_id`
6, 18, 32, 50, 74) carry a synthetic interior ring. **Every exterior
ring is CW; every interior ring is CCW** — the OGC orientation the
persona's legacy tool produced.

| Field | Type | Description |
|---|---|---|
| `feature_id` | int | Stable per-task primary key (1–100) |
| `overture_id` | string | Original Overture id (UUID-like) |
| `name_primary` | string | Building name (often empty; CJK where present) |
| `building_class` | string | Overture building class (often empty) |
| `height` | float / null | Height in metres if known |

### Output

`outputs/tokyo_buildings_fixed.geojson` — same 100 features in
EPSG:4326, identical schema, with **every exterior ring CCW and every
interior ring CW** (RFC 7946 §3.1.6 compliant). Geometry and attributes
are otherwise untouched.

## Failure modes

1. **Forget to fix orientation — pass the file through unchanged.** A
   naive agent runs `gpd.read_file → gdf.to_file` and gets exactly the
   input back; geopandas does not normalise ring orientation on read or
   write. *Detection:* `exterior_rings_ccw` and `interior_rings_cw`
   subchecks both fail; everything else passes because no geometry or
   attribute changed. Covered by `broken_wrong_orientation` (score
   0.643).
2. **Fix exteriors but forget interiors.** The agent loops every
   polygon and reverses the exterior ring's coordinate list, but does
   not touch the interior rings — RFC 7946 §3.1.6 has *two* clauses
   and a partial implementation satisfies only the more obvious one.
   *Detection:* `interior_rings_cw` subcheck fails, everything else
   passes. Covered by `broken_partial_orientation` (score 0.821).
3. **Drop one of the required attribute columns.** The agent extracted
   a subset of properties (e.g., kept only `feature_id`, `name_primary`,
   `height`) before writing. *Detection:* the `format_schema_valid`
   gate's required-column check rejects the file before any subchecks
   run. Covered by `broken_wrong_format` (score 0.0).
4. **Drop interior rings while fixing orientation.** A common
   simplification path is "reconstruct each polygon from just the
   reversed exterior", which silently drops every hole. The geometry's
   area changes only by the sum of hole areas (small for a building
   with a tiny courtyard) so a pure-area metric would not catch it.
   *Detection:* `polygons_with_holes_preserved` subcheck fails (sub
   has 0 polygons-with-holes, ref has 5). Not covered by a broken
   solution; the principled hole-count subcheck is the detector.
5. **Re-orient correctly but simplify or buffer geometry.** A stray
   `simplify(0.0001)` or `buffer(0)` step nudges vertices.
   *Detection:* `per_feature_geometry_preserved` subcheck fails
   (per-id IoU drops below 0.99). Not covered by a broken solution;
   the per-id IoU subcheck is the principled detector.
6. **Re-orient and accidentally change CRS.** The agent calls
   `to_crs(3857)` or `set_crs(3857)` thinking projected coordinates
   are required. *Detection:* the two soft CRS subchecks
   (`crs_is_canonical`, `crs_in_meaningful_set`) both fail, docking
   two points off the total. Gate 1 still passes as long as the CRS
   is parseable, so the geometric work is graded on its own merits.
   Not covered by a broken solution; the soft CRS subchecks are the
   principled detector.
7. **Drop or duplicate features.** The agent applied a filter
   predicate (e.g., "buildings with non-null height") before writing.
   *Detection:* the `feature_count_within_tolerance` subcheck (±5 %)
   catches gross drops; the
   `feature_id_set_preserved` Jaccard subcheck (≥ 0.95) catches
   subtler set differences. Not covered by a broken solution; both
   detectors are principled.
8. **Re-encode the file via a non-GeoJSON intermediate format.** The
   agent uses Shapefile as a staging format (which silently truncates
   `overture_id` if it ever stored a long-form column, and re-orients
   to OGC convention on round-trip). *Detection:* the
   `format_schema_valid` gate's required-columns check and the
   `exterior_rings_ccw` subcheck both bite. Not
   covered by a broken solution.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — read, write, no
orientation fix**. A naive `gpd.read_file → gdf.to_file` round trip
preserves dtypes, attributes, geometry and even orientation (the
strings stay strings, the rings stay reversed) and the file looks
superficially correct: same schema, same coordinates, same feature
count. Only an explicit ring-orientation check catches it. The grader
awards 0.643 for this failure (both weight-5 orientation subchecks
fail; every preservation subcheck passes), so it is clearly
distinguishable from a correct solution (1.0), from a missing-column
solution (0.0), and from a partial-orientation solution (0.821).
