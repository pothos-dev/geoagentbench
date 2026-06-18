# crs-l2-fiji-antimeridian

## Story

Mereani Tuilagi, a marine biologist at the University of the South
Pacific, has GPS transect tracks from a reef survey that several boats
logged across the ±180° meridian. Her colleagues' tooling drew the
crossing transects as ~359°-long arcs around the globe because the
vendor exporter wrote the LineStrings with longitudes wrapped
independently per vertex — a violation of RFC 7946 §3.1.9. She needs
the antimeridian crossings cut properly, the lot reprojected to Fiji
1986 / Fiji Map Grid (EPSG:3460), each transect re-assembled as a
MultiLineString, and an honest `length_m` per transect computed in the
projected CRS so the bottom-trawl-impact paper can cite per-transect
coverage figures that survive peer review.

## What this task probes

CRS-reprojection competence on a **wrap-around / antimeridian** input.
The agent must:

1. Recognise that the input violates RFC 7946 §3.1.9 — LineStrings
   declared with longitudes that hop straight from +179° to -179°
   between consecutive vertices instead of being split at ±180°.
2. Split each crossing LineString at the antimeridian (interpolate the
   latitude at lon=±180°, terminate the eastern part, start the
   western part on the matching opposite-sign boundary).
3. Reproject the parts to EPSG:3460 (Fiji Map Grid).
4. Re-assemble each transect's parts into a single
   `MultiLineString` feature in the output (one feature per
   `transect_id` regardless of how many parts it contains).
5. Compute `length_m` as the projected-CRS length of the assembled
   MultiLineString; preserve the input's identifying attributes.

The chained operations (split → reproject → collect → measure) and
the antimeridian gotcha put this task at L2.

## Why this difficulty

L2: 2–4 chained operations on a fully bundled file. No fetching, no
discovery, no live data drift. The chain is split-at-antimeridian →
reproject → assemble-Multi → compute-length. The
antimeridian-crossing input is the failure-recognition step that
distinguishes L2 from L1; a single `to_crs` call is *not* the
correct primary operation here.

## Input / output formats

### Input

`inputs/fiji_transects_wgs84.geojson` — 30 features in EPSG:4326. All
geometries are `LineString`. 10 of the 30 cross the antimeridian (and
do so in violation of RFC 7946 §3.1.9). Schema:

| Field | Type | Description |
|---|---|---|
| `transect_id` | string | Stable per-transect identifier (`T001`–`T030`) |
| `vessel` | string | Vessel name that logged the transect |
| `survey_date` | string | ISO-8601 survey date |
| `crosses_antimeridian_flag` | bool | True for the 10 wrap-encoded transects (the agent does *not* need to read this; it is only present so the bundled input remains self-describing for human review) |

### Output

`outputs/fiji_transects_fmg.geojson` — 30 features in EPSG:3460. All
geometries are `MultiLineString`. Schema:

| Field | Type | Description |
|---|---|---|
| `transect_id` | string | Carried through from input |
| `vessel` | string | Carried through |
| `survey_date` | string | Carried through |
| `length_m` | float64 | Length in metres in EPSG:3460 |

The 10 antimeridian-crossing transects come out as 2-part
MultiLineStrings; the 20 non-crossing transects come out as 1-part
MultiLineStrings.

## Failure modes

1. **Forget to reproject (or skip the whole pipeline).** Output is
   the WGS84 input untouched, no `length_m`, plain LineStrings.
   *Detection:* Gate 1 fails on the missing `length_m` column (the
   untouched input still declares a parseable CRS, so the soft-CRS
   part of the gate passes). Covered by `broken_wrong_format`.
2. **Stamp the CRS as 3460 but leave coordinates in WGS84 degrees**
   (`set_crs` instead of `to_crs`), and compute `length_m` from
   `geom.length` while still in degrees. *Detection:* Gate 1 passes
   because the metadata reads as 3460; `coordinates_within_fmg_fiji_envelope`
   fails (degrees vs metres band); `per_transect_length_matches`
   and `total_length_within_1_percent` fail (degree-valued length
   ~ 1e-5 of the metric reference); `geometry_type_is_multilinestring`
   and `antimeridian_crossings_split_into_multi_parts` also fail
   because the Multi assembly was skipped. Covered by
   `broken_wrong_crs_metadata_only`.
3. **Drop the `vessel` and `survey_date` columns** when assembling
   the output. *Detection:* `identifying_attributes_preserved`
   subcheck fails. All other subchecks pass. Covered by
   `broken_wrong_attributes`.
4. **Reproject without splitting at the antimeridian.** PROJ's
   transverse-Mercator wraps longitudes internally, so a naive
   `to_crs` actually gives correct *length_m* values for the crossing
   transects — but each crossing transect ends up as a single-part
   MultiLineString (or LineString) that, when un-projected back to
   WGS84 in any downstream tool, *re-introduces* the 359°-arc bug.
   *Detection:* `antimeridian_crossings_split_into_multi_parts`
   subcheck (10 crossing transects must each have ≥2 parts).
   Not covered by a broken solution; the dedicated topology subcheck
   is the principled detector.
5. **Reproject into a defensible-but-non-canonical CRS** (UTM 60S,
   EPSG:32760, also metric and Fiji-friendly for the bundled
   archipelago west of the antimeridian). *Detection:* Gate 1 accepts
   the submission and reprojects it into Fiji Map Grid for the
   spatial subchecks; the `crs_is_canonical` subcheck fails because
   the regional canonical is EPSG:3460, but `crs_in_meaningful_set`
   still passes. A correct UTM 60S pipeline scores 16.5/17 ≈ 0.971
   under the reasoned weights (only the weight-0.5 `crs_is_canonical`
   subcheck fails — the CRS-label pick is cosmetic relative to whether
   the reprojection actually happened). Not covered by a broken
   solution; the `crs_is_canonical` subcheck is the principled
   detector. CRSes outside the meaningful set (e.g. UTM 31N, any
   non-Fiji projected metric, or a misidentified Pacific zone) pass
   Gate 1 (the submission is reprojected into 3460 for spatial
   subchecks under the soft-CRS policy) but lose both CRS subchecks
   (weight 0.5 + 1.0), dropping the ceiling to 15.5/17 ≈ 0.912.
6. **Output one feature per part** (split at antimeridian, reproject,
   but write each part as a separate `LineString` feature with a
   duplicated `transect_id`). *Detection:* the weight-1.0
   `feature_count_within_5_percent` subcheck (40 features vs
   reference 30 = 33% over, fails ±5%) plus the
   `geometry_type_is_multilinestring` subcheck. Not covered by a
   broken solution; the count + Multi-type subchecks are the
   principled detectors.
7. **Compute `length_m` in WGS84 degrees instead of FMG metres** even
   after reprojecting geometry correctly. *Detection:* covered by
   `per_transect_length_matches` and `total_length_within_1_percent`.
   Not covered by a broken solution; the per-id length match is the
   principled detector.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#4 — reproject without
splitting at the antimeridian**. PROJ's internal longitude wrap masks
the bug at length-computation time, so an agent that calls a single
`to_crs(3460)` and assigns `geom.length` produces output that *looks*
correct on every numeric subcheck. Only the dedicated topology
subcheck catches it — and because the antimeridian split is the
task-defining skill it carries the top weight (4.0), so missing it
drops the score to 13/17 ≈ 0.765 when the transects are upcast to
MultiLineString (12/17 ≈ 0.706 if they are left as plain
LineStrings, and a further 0.5 weight lower if the agent also picks
UTM 60S). That is clearly distinguishable from a complete solution
(1.0), from a cosmetic attribute slip (0.941), from the metadata-only
declare-but-never-transform failure (0.294), and from the format
failure (0.0). The reasoned weighting deliberately puts this
central-skill miss well *below* a cosmetic attribute drop: failing
the defining gotcha must cost more than losing two string columns.
