# dc-l2-cairo-invalid-dedup

## Story

Reem Farouk, a data steward at Egypt's Land Registry Authority, has
inherited a parcel snapshot pulled from three legacy provincial
systems before the registry's recent unification. The bundle is in
Egypt Red Belt (EPSG:22992); geometry types mix Polygon and
MultiPolygon, several rings self-intersect (the upstream tool didn't
enforce simple-feature validity), some parcels appear twice with
conflicting metadata, and the join produced sliver polygons under 1 m²
along administrative seams. She needs a single canonical GeoParquet
with everything valid, schema-consistent, deduped, and slivers removed
— the foundation for the registry's new central repository.

## What this task probes

A four-operation data-cleaning chain on a single bundled fixture:

1. **Make-valid.** Repair self-intersecting rings via
   `shapely.make_valid`, keeping polygonal content.
2. **Sliver removal.** Drop features whose surviving geometry has
   area below 1 m².
3. **Deduplicate.** Collapse exact-equal geometries into one row,
   keeping the row with the smallest `record_seq` (the earliest
   record), and recomputing `area_m2` from the surviving geometry.
4. **Polygon → MultiPolygon coercion.** Promote single-part Polygons
   to 1-part MultiPolygons so the output schema is geometrically
   homogeneous.

A correct solution chains all four; the grader scores each step
independently so partial implementations land in distinct ranges.

## Why this difficulty

L2: 2–4 chained operations on bundled data. The persona's task names
four operations explicitly (validity, sliver removal, dedup,
geometry-type coercion) plus an implicit attribute step
(area_m2 recompute). Bundled inputs only, so no fetching skill is
exercised, but a faithful pipeline does require the agent to plan
the order (make_valid before dedup, recompute area after geometry
edits, coerce at the very end) — which is what L2 tests.

## Input / output formats

### Input

`inputs/cairo_parcels_legacy.geojson` — 290 features in EPSG:22992,
mix of Polygon and MultiPolygon. Composition:

| Bucket | Count | Notes |
|---|---|---|
| Clean rectangle parcels | 160 | parcel_id 1..210 minus the corrupt subsets |
| Multipart parcels | 30 | `MultiPolygon` of main rectangle + detached 8 m × 10 m annex |
| Self-intersecting rectangles | 20 | bowtie ring; `is_valid` is `False` |
| Exact-duplicate insertions | 50 | parcel_id in 900_001..900_050; geometry copied from a clean parcel; conflicting `parcel_class`; later `record_seq` |
| Sliver squares | 30 | parcel_id in 800_001..800_030; ~0.7 m × 0.7 m, area ≈ 0.49 m² |

Schema: `parcel_id` (int), `record_seq` (int), `parcel_class` (string),
`district` (string), `area_m2` (float, often stale).

### Output

`outputs/parcels_canonical.geoparquet` — 210 features in EPSG:22992,
every geometry valid `MultiPolygon`, no slivers, no exact duplicates.
Schema preserved (`parcel_id`, `record_seq`, `parcel_class`,
`district`, `area_m2`, `geometry`). `area_m2` is recomputed from the
surviving geometry's `.area` (in EPSG:22992 metres).

## Failure modes

1. **Skip `make_valid`.** Agent loops the input, applies dedup +
   sliver removal + MultiPolygon coercion + area recompute but never
   calls `shapely.make_valid`. The 20 bowtie polygons remain
   self-intersecting and shapely reports their `.area` as 0, so they
   slip past the sliver threshold *only* if the agent uses a different
   measure (envelope.area, hard-coded class) for the threshold.
   *Detection:* `all_geometries_valid` and `no_slivers` (area-0
   bowties are below 1 m²) fail. Under GEOS ≥ 3.13 `unary_union`
   resolves the bowtie self-intersections instead of raising, so
   `geometric_extent_preserved` passes (on older GEOS it raised
   TopologyException and the grader counted it failed). Covered by
   `broken_no_make_valid` (score 0.77 under the per-task reasoned weighting).
2. **Skip MultiPolygon coercion.** Agent does every other step but
   leaves single-part parcels as `Polygon`. *Detection:*
   `all_multipolygon` subcheck fails. Covered by `broken_no_coerce`
   (score 0.89 under the per-task reasoned weighting).
3. **Output in the wrong CRS.** A common confusion is "GeoParquet
   should be in WGS84 like GeoJSON" — the agent calls `to_crs(4326)`
   before writing. *Detection:* under the soft-CRS policy (commit
   05aabd6, 2026-05-28), the grader reprojects the submission back to
   EPSG:22992 so the geometric subchecks still run; the
   `crs_is_canonical` and `crs_in_meaningful_set` subchecks both fail
   (EPSG:4326 is outside the meaningful set {22992}). Covered by
   `broken_wrong_format` (score 0.94 under the per-task reasoned weighting).
4. **Skip dedup, run everything else.** Agent runs make_valid +
   sliver removal + MultiPolygon coercion + area recompute but does
   not deduplicate. The 50 duplicate insertions remain in the output.
   *Detection:* `feature_count_within_tolerance` fails (260 vs 210,
   ~24 %), and the `no_exact_duplicate_geometries` subcheck fails on
   the 50 duplicate WKB groups. Not covered by a broken solution; the
   count + WKB-uniqueness subchecks are the principled detectors.
5. **Skip sliver removal.** Agent passes every other step but never
   filters by area. The 30 sliver squares remain. *Detection:*
   `feature_count_within_tolerance` fails (240 vs 210, ~12.5 %), and
   the `no_slivers` subcheck fails on the 30 sub-1 m² squares. Not
   covered by a broken; the area-threshold subcheck is the principled
   detector.
6. **Dedup keep-rule inverted: keep the latest record.** Agent uses
   `keep="last"` instead of `keep="first"`, so the surviving rows
   carry the synthetic 900_000+ parcel_ids and the conflicting
   `parcel_class` values. *Detection:* `parcel_id_set_matches_reference`
   Jaccard collapses (50 wrong ids out of 210, Jaccard ≈ 0.59); the
   `identifying_attributes_match_reference` subcheck (matched on
   parcel_id, so when the surviving id is 900_*, the attribute join
   has zero common keys with the reference) also bites. Not covered
   by a broken; both detectors are principled.
7. **Skip `area_m2` recompute.** Agent keeps the legacy stale
   `area_m2` (1200 m² for every base parcel, including the bowties
   whose true repaired area is ~600 m²). *Detection:* the
   `area_m2_recomputed` subcheck (compares the column to its own
   `geometry.area`) fails on the 20 bowtie rows. Not covered by a
   broken; the self-consistency subcheck is the principled detector.
8. **Filter on `area_m2` column instead of `geometry.area`.** The
   legacy `area_m2` for slivers is ~0.49 (above 0 but the value
   reads as the original value, not a recompute). If the agent
   filters on `area_m2 >= 1.0` that works; if the agent filters on
   `area_m2 > sliver_count` or some wrong predicate, slivers survive
   and base parcels are dropped. *Detection:* feature-count or sliver
   subcheck. Not covered by a broken.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — skip `make_valid`**. A
naive agent reads the GeoJSON, runs `gdf.drop_duplicates(subset=...)`
on a stringified geometry column, drops slivers via `area < 1`,
wraps every Polygon as MultiPolygon, and writes GeoParquet. Without
explicit `make_valid`, the 20 bowtie geometries propagate untouched
and the `geometry.area`-based sliver filter accidentally drops all
20 of them too (their signed area is 0), leaving 190 features that
fail `feature_count_within_tolerance`, `parcel_id_set_matches_reference`,
and `geometric_extent_preserved` (~0.74 under the per-task reasoned
weighting). The bundled `broken_no_make_valid` variant (bowties
survive an envelope-based filter) lands at 0.77 - both visibly
distinct from a correct solution (1.0), a wrong-CRS solution (0.94),
and a no-coerce solution (0.89). The score ordering now tracks error
severity: skipping a central cleaning operation (make-valid 0.77,
coercion 0.89) drops the score substantially, while a purely cosmetic
wrong-CRS output (0.94) drops it only lightly.
