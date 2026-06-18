# spa-l2-cairo-shop-knn

## Story

Mona Saleh runs a retail-density consultancy advising landlords near
downtown Cairo. She has a 10 000-shop OSM-style extract and 100 anchor
points marking her client's target market locations. For each anchor
she needs the five nearest shops (with metric distance and a 1 km
within-distance flag), plus a small 5×3 distance matrix from those
five shops to the anchor's three closest sibling anchors, all returned
as JSON. Several Cairo retail chains appear in the shop layer under
multiple Arabic / Latin transliterations of the same name; the
deliverable must canonicalise those before grouping so the chain
density figures aren't fragmented across spelling variants.

## What this task probes

- **k-nearest neighbours (k=5)** over a medium-scale point layer
  (~10⁴) against 100 anchor points, in a projected metric CRS
  (EPSG:22992 — Egypt Red Belt).
- **Within-distance filter** at 1 km expressed as a per-row boolean
  flag.
- **Distance matrix** (5×3) for a small subset per anchor — exercises
  the agent's ability to compose three spatial primitives in one
  pipeline.
- **Inconsistent attribute values** — variant transliterations of the
  same chain must collapse to one canonical `normalised_name`. This
  is the only Axis-6 data-quality issue in the task.
- **JSON output** with a nested schema (`anchor_id`,
  `anchor_name_normalised`, `knn[]`, `full_distance_matrix_m[][]`).

## Why this difficulty

L2: three chained spatial operations (knn, within-distance,
distance matrix) on fully bundled data, plus the attribute-cleaning
step that normalises chain transliterations. Inputs are committed in
the canonical metric CRS (EPSG:22992) so no reprojection is required;
output is JSON, not GeoJSON, so the agent must emit a non-spatial
serialisation. Above L1 (one operation, no chained transforms) and
below L3 (live data, full discovery → fetch → analysis pipeline).

## Input / output formats

### Input

- `inputs/cairo_retail.gpkg` — single GPKG with two layers in EPSG:22992:
  - `shops` — 10 000 Point features. Columns: `shop_id` (string,
    e.g. `S00001`), `raw_name` (string; mix of chain variants and
    "Local Shop NNNNN" filler), `geometry`.
  - `anchors` — 100 Point features. Columns: `anchor_id` (string,
    e.g. `M001`), `anchor_name` (string; carries deliberate casing /
    whitespace junk), `geometry`.

### Output

`outputs/market_neighbourhoods.json` — one JSON list, 100 entries,
one per anchor. Sample shape:

```json
[
  {
    "anchor_id": "M001",
    "anchor_name_normalised": "tahrir square plaza",
    "knn": [
      {
        "shop_id": "S07233",
        "normalised_name": "seoudi",
        "distance_m": 565.577,
        "within_1km": true
      },
      ...  // 4 more, sorted by distance ascending
    ],
    "full_distance_matrix_m": [
      [192.3, 528.4, 1620.1],   // row = knn shop 0, cols = sibling anchors
      ...                        // 4 more rows, one per knn shop
    ]
  },
  ...
]
```

## Failure modes

1. **Output written in the wrong format** (CSV, GeoJSON, GPKG,
   Parquet). *Detection:* Gate 1 rejects on missing `.json` filename.
   Covered by `broken_wrong_format` (score 0.0).
2. **Agent skipped chain canonicalisation** — emitted `raw_name` (or
   per-row hashed strings) verbatim under `normalised_name`.
   *Detection:* `chain_variants_collapsed` fails (each chain has 4
   distinct values; per-shop_id consistency may also fail). Covered
   by `broken_no_chain_normalisation` (score 0.90).
3. **Agent picked the wrong 5 shops** — wrong-CRS distance computation
   (degrees not metres), reversed nearest-neighbour direction, or
   picked the 5 *farthest* shops instead of nearest. *Detection:*
   `knn_distance_vector_matches_reference` and
   `knn_distances_agree_with_coords` fail; if the agent forgot to
   recompute the matrix, `distance_matrix_consistent_with_coords`
   also fails. Covered by `broken_wrong_knn_set` (score 0.35).
4. **Agent reported `distance_m` in kilometres or feet.** *Detection:*
   `knn_distances_agree_with_coords` (compares reported distance to
   coord-derived true distance for the named shop) fails;
   `within_1km` flag may also become inconsistent if computed against
   a different unit. Not covered by a broken solution; principled
   detector is subcheck 2.
5. **Agent collapsed `within_1km` to a constant** (always `true` or
   always derived from a wrong threshold). *Detection:*
   `within_1km_flag_correct` rejects when ≥ 1% of (anchor, knn)
   pairs disagree with `distance_m ≤ 1000`. Not covered by a broken
   solution; principled detector is subcheck 3.
6. **Agent over-collapsed transliterations** — folded distinct chains
   into a single canonical name (e.g. mapped both "Carrefour" and
   "HyperOne" to "supermarket"). *Detection:*
   `chain_variants_collapsed` requires per-chain distinct counts of
   1, but if multiple chain truth-sets share a single normalised
   value the per-shop consistency check still passes. The grader
   doesn't directly catch over-collapse across chains; principled
   detector lives in `metadata.yaml > tolerances.rationale` —
   noted as `not-handled` here for the auditor.
7. **Agent dropped or duplicated anchors.** *Detection:* the
   `record_count_within_5pct` (weight 1) and `anchor_id_set_jaccard`
   (weight 2) subchecks reject anchor-id-set drift and >5% row-count
   delta. Not covered by a broken solution; principled detectors are
   those subchecks.

## Expected weak-agent failure mode

The likeliest weak-agent failure is **#2** — emitting `raw_name`
verbatim or applying only a Latin lowercase normalisation (which
leaves the Arabic-script variants unfolded). A more careful agent
that does basic Latin folding but stops short of cross-script
clustering still leaves at least 4 of 8 chains split between Latin
and Arabic forms, tripping `chain_variants_collapsed`.
