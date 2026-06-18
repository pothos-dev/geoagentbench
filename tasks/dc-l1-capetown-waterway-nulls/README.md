# dc-l1-capetown-waterway-nulls

## What this task probes

Null / empty handling on a contractor-style GeoJSON of Cape Town
waterway centrelines. The input mixes three independent defect classes
that a junior on the persona's team would have to recognise in one
pass: features whose `geometry` is JSON `null` (parser-tolerant but
spatially meaningless), features whose `geometry` is a syntactically
valid `LineString` with empty `coordinates` (parses fine, still
empty), and rows whose required `waterway_type` attribute is `null`.
The agent must drop every feature in any of those three buckets, keep
everything else (in particular: rows whose only oddity is a null
`name` survive), and stamp the FeatureCollection with a top-level
`dropped_count` foreign member so the persona can audit the
contractor. No projection, no filtering by attribute value, no
geometric edit — pure null / empty cleanup with a small reporting
side-channel.

## Why this difficulty

L1: a single primary operation (defect-row drop) on a fully bundled
input. No fetching, no chained operations, no projection-sensitive
numerics. The persona's question admits exactly one correct answer
family: a correct solution drops the same 20 rows, keeps the same 80
rows (including the 5 with null `name`), and reports
`dropped_count = 20`.

## Input / output formats

### Input

`inputs/capetown_waterways.geojson` — 100 features in EPSG:4326.
Geometry: `LineString` (with the deliberate defects below). Property
schema:

| Field | Type | Description |
|---|---|---|
| `feature_id` | int | Stable contractor-supplied row id, 1..100 |
| `name` | string \| null | Free-form watercourse name (5 rows are deliberately null) |
| `waterway_type` | string \| null | One of {stream, river, drain, canal, ditch} (10 rows are deliberately null) |

Defect breakdown (by `feature_id`):

| Range | Defect | Count |
|---|---|---|
| 1–5   | `geometry` is JSON `null` | 5 |
| 6–10  | `geometry` is `{"type":"LineString","coordinates":[]}` | 5 |
| 11–15 | `geometry` is null AND `waterway_type` is null | 5 |
| 16–20 | `waterway_type` is null (geometry valid) | 5 |
| 21–25 | `name` is null (geometry valid, waterway_type valid) | 5 |
| 26–100 | fully clean | 75 |

### Output

`outputs/waterways_clean.geojson` — same property schema. The
FeatureCollection carries a top-level `dropped_count: 20` foreign
member; the `features` array contains the 80 retained rows
(`feature_ids` 21–100 in the reference, including the 5 with null
`name`).

## Failure modes

1. **Drop only `null` geometries — miss the empty-LineString variant
   and the null-`waterway_type` rows.** A common LLM failure: filter
   on `geometry.isna()` and call it done. *Detection:*
   `no_null_or_empty_geometry_in_output` detects the 5
   surviving empties; `no_null_waterway_type_in_output`
   detects the surviving null wt rows; the `dropped_count_correct`,
   `feature_count_within_tolerance`, and `feature_id_set_preserved`
   subchecks all flag the surviving rows. Covered by
   `broken_under_drop` (score 0.448).
2. **Over-drop — also drop rows with null `name`.** The agent applies
   a "drop any row with any null in any column" rule and loses 5
   otherwise-fine watercourses. *Detection:*
   `null_name_rows_preserved` is the principled detector;
   `feature_count_within_tolerance` (78 vs 80 → 2.5 %, passes) and
   `feature_id_set_preserved` (Jaccard 0.94, fails) catch it
   indirectly. Not covered by a broken solution; the dedicated
   subcheck is the principled detector.
3. **Forget the `dropped_count` foreign member.** The agent produces
   a clean GeoJSON but writes only the standard `type` / `features`
   keys. *Detection:* `dropped_count_present` and
   `dropped_count_correct` subchecks both fail. Not covered by a
   broken solution; the principled detectors are the two paired
   subchecks.
4. **Report a wrong `dropped_count` value.** The agent reports the
   total input row count, or some other number. *Detection:*
   `dropped_count_correct` subcheck (strict equality with 20). Not
   covered by a broken solution; the strict-equality subcheck is the
   principled detector.
5. **Output in the wrong CRS** — e.g., the agent reprojected to
   EPSG:3857 before writing. *Detection:* the two soft CRS subchecks
   (`crs_is_canonical`, `crs_in_meaningful_set`) both fail; the
   submission is reprojected to canonical for the remaining subchecks
   so the geometric work still counts; both CRS subchecks are weight-1
   schema checks. Covered by `broken_wrong_format` (score 0.931).
6. **Disturb geometries** — e.g., the agent ran the cleanup correctly
   but every kept LineString picked up a coordinate shift from a
   stray reprojection round-trip through Web Mercator. *Detection:*
   `geometry_preserved_per_id` subcheck (per-id Hausdorff ≤ 1e-7°).
   Covered by `broken_wrong_geometry` (score 0.914).
7. **Drop required columns.** The agent kept the right rows but
   stripped the `waterway_type` or `feature_id` column. *Detection:*
   Gate 1's required-column check rejects the file. Not covered by a
   broken solution; the gate is the principled detector.
8. **Mutate attribute values** — e.g., fill nulls with sentinel
   strings ("unknown") instead of dropping the rows. *Detection:*
   `no_null_waterway_type_in_output` would pass but
   `attributes_preserved_per_id` fails (the sentinel does not match
   the reference's actual non-null `waterway_type` for the kept ids,
   and the agent's "filled" rows now have ids that should have been
   dropped, breaking `feature_id_set_preserved`). Not covered by a
   broken solution; the per-id attribute subcheck is the principled
   detector.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — drop only `null`
geometries**. A naive `gdf = gdf[gdf.geometry.notna()]` filter is the
shortest-string completion of the persona's request and ignores both
the empty-LineString and the null-`waterway_type` cases. The grader
awards 0.448 for this failure (five subchecks fail, three of them the
weight-4 central cleaning detectors and two the weight-2 derivative /
report checks; per-id geometry, attributes and CRS still match for
the 80 common ids), so it is clearly distinguishable from a correct
solution (1.0), from a CRS-wrong solution (0.931), and from a
coords-jittered solution (0.914). Under the 2026-06-14 severity
weighting the central-skill failure (under-drop) sits far below the
two peripheral slips, which the blunt c749e57 3x-everything weighting
did not separate as sharply.
