# spa-l2-lagos-hotspot-overlaps

## Story

Adeola Bankole is a partner at a Lagos urban-density consultancy
preparing a hot-spot map for a state-level housing-policy review.
Her input layer carries land-use polygons with population-density
attributes plus a 1 km hex grid over greater Lagos. The land-use
polygons overlap each other from imperfect alignment between source
layers, producing thousands of sliver polygons under 100 m² that
distort area-weighted aggregations. She needs the slivers filtered,
an overlap-aware area-weighted mean density per hex, and the top
10% cells delivered as both a polygon GeoParquet (for her GIS
viewer) and a plain Parquet ranking (for her tabular dashboard).

## What this task probes

- **Sliver filter at a metric area threshold.** The agent must
  reproject to a metric Nigerian CRS (the reference uses
  EPSG:26331, Minna / UTM zone 31N; EPSG:26391, Minna / Nigeria
  West Belt, is accepted as equally canonical) before measuring
  area, otherwise polygon area is in degrees² and the threshold
  fails. Only after filtering is the area-weighted aggregation
  meaningful.
- **Overlap-aware spatial aggregation.** Per hex cell, the
  area-weighted mean of `pop_density` across all overlapping
  land-use polygons:
  `sum(intersection_area_i * pop_density_i) / sum(intersection_area_i)`.
  This is the spatial-aggregation primitive (Axis-5 spatial
  analysis) on data with overlapping inputs — a step beyond a
  simple non-overlapping spatial join.
- **Hot-spot ranking.** Top-N selection by a derived metric with a
  rank column emitted alongside the result.
- **Multi-output emission with mixed formats.** GeoParquet (CRS
  metadata + Polygon geometry) plus plain Parquet (tabular only).
  The agent must write both, and the two must agree on which cells
  are the hot-spots.
- **CRS reprojection on output.** Inputs are EPSG:4326; outputs are
  EPSG:26331.

## Why this difficulty

L2: chained operations on bundled data with no live fetching. The
pipeline is filter (by area, requires reprojection) → overlay
(intersection of land-use polygons with hex grid) →
group-and-aggregate (area-weighted mean + counts) →
rank-and-truncate. Above L1 (single primitive on bundled data),
below L3 (no live fetching, no discovery / data-source
identification step).

## Input / output formats

### Input

- `lagos_landuse.geojson` — 5 542 Polygon features in EPSG:4326.
  Columns: `id` (string; Overture id for real polygons or
  `SLIV-NNNNN` for synthetic slivers), `class` (string), `pop_density`
  (float, ppl/km²), `geometry`.
- `lagos_hex_grid.geojson` — 1 782 Polygon features in EPSG:4326.
  Columns: `hex_id` (string, e.g. `H011-017`), `geometry`. Built
  as a flat-topped 1 km hex grid in EPSG:26331 and reprojected.

### Output

- `outputs/hotspots.geoparquet` — top 10% hex cells (104 rows) in
  EPSG:26331. Columns: `hex_id`, `rank`, `area_weighted_density`,
  `geometry` (Polygon). Sorted by rank ascending.
- `outputs/hotspot_ranking.parquet` — same 104 rows as a plain
  Parquet, no geometry. Columns: `hex_id`, `rank`,
  `area_weighted_density`, `n_overlap_polygons`,
  `n_slivers_filtered`.

## Failure modes

1. **Output written in the wrong format / missing GeoParquet** (CSV,
   GeoJSON, or table-only). *Detection:* Gate 1 rejects on missing
   `hotspots.geoparquet`. Covered by `broken_wrong_format`
   (score 0.0).
2. **Slivers not filtered** — agent skipped the area-threshold step
   entirely, treats sliver polygons as real. *Detection:*
   `hex_id_set_jaccard_vs_reference` drops because the synthetic
   high-density slivers pull individual cells onto the top list;
   `n_overlap_polygons` and `n_slivers_filtered` mismatch on most
   shared cells. Covered by `broken_no_sliver_filter` (score 0.58).
3. **Wrong reduction or wrong unit on `area_weighted_density`** —
   agent emitted a sum, max, unweighted mean, or wrong-unit value
   while otherwise picking the right cells. *Detection:*
   `density_values_match_reference` fails (≥ 90% of shared cells
   must agree to within ±5% relative). Covered by
   `broken_wrong_density_values` (score 0.79).
4. **Area filter applied in the wrong CRS (degrees² instead of
   metres²)** — applying a "<100" threshold on EPSG:4326 areas
   removes virtually nothing because every polygon's degree² area
   is well below 100. *Detection:* manifests identically to mode 2
   above (slivers retained) — `hex_id_set_jaccard_vs_reference` and
   the count subchecks fail. Principled detector via the same
   subchecks; not covered by a separate broken solution.
5. **Hex geometries emitted in the wrong CRS** — polygons stamped
   with EPSG:26331 metadata but containing 4326 coordinates, or
   vice versa. *Detection:* the gate hard-fails only on a missing
   or unparseable CRS; any parseable CRS is reprojected to
   EPSG:26331 and the original pick is graded by the
   `crs_is_canonical` / `crs_in_meaningful_set` subchecks. If the
   metadata lies about the coordinates, `hex_geometries_match`
   fails per-row IoU vs the reference.
6. **Top-N count off by an arbitrary fraction (e.g. top 5% or top
   25%), or top 10% taken over the full 1 782-cell grid instead of
   the ~1 030 eligible cells** — agent misread "top 10%" or used
   the wrong base. *Detection:* the Tier-1 (weight-4)
   `hex_id_set_jaccard_vs_reference` subcheck drops below its 0.85
   floor (e.g. 104/179 ≈ 0.58). Principled detector; not covered
   by a separate broken solution.
7. **Rank column inconsistent with density ordering** — agent
   shuffled rows or assigned ranks from a different column.
   *Detection:* `rank_consistent_with_density` requires that
   sorting by rank ascending matches sorting by density
   descending, ranks are unique, and the smallest is 1.

## Expected weak-agent failure mode

The likeliest weak-agent failure is **#2** — applying area
filtering in EPSG:4326 (or skipping the filter altogether) so that
the synthetic slivers remain in the aggregation. The slivers pull a
chunk of the top 10% onto random hex cells where a single
high-density artefact is the only overlap. A more careful agent
that reprojects but uses an unweighted mean across overlapping
polygons (mode 3) lands at score ~0.79 — the cells are right but
the density is wrong.
