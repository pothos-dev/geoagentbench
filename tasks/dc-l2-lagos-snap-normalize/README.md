# dc-l2-lagos-snap-normalize

## Story

Tunde Adeyemi leads a zoning-harmonisation pilot for Lagos State,
merging zoning datasets from six LGAs that each used their own
spelling conventions (`RESIDENTIAL`, `Residential`, `Resi.`, …)
and whose contractor digitisation produced sub-millimetre vertex
offsets between adjacent parcels (every dissolve falls into a
slivered mess). The dataset also contains zero-area "ghost"
polygons left over from collinear-vertex parcels that crash the
dissolve outright. He needs the agent to snap vertices at 1 mm,
drop the zero-area features, normalise the zoning class to a
four-value controlled vocabulary, filter out blank-class rows,
and aggregate per class — all delivered as GPKG in EPSG:26331
that feeds straight into the state's new zoning portal.

## What this task probes

A multi-step data-cleaning chain on a single bundled fixture:

1. **Vertex snapping at 1 mm.** Round every coordinate to a 1 mm
   grid (e.g., `shapely.set_precision(grid_size=0.001)`) so
   adjacent parcels' shared corners coincide exactly and the
   dissolve produces a clean polygon per class.
2. **Zero-area drop.** Filter out features whose `geometry.area`
   is 0 (collinear ghost polygons).
3. **Attribute normalisation.** Map every variant spelling of the
   zoning class to one of four canonical TitleCase values:
   `Residential`, `Commercial`, `Industrial`, `Agricultural`.
4. **Blank-row filter.** Drop rows whose normalised class is empty
   or whitespace.
5. **Spatial aggregation by class.** Dissolve (unary_union) per
   canonical class and recompute `area_m2` from the dissolved
   polygon's `.area` in metres.

The grader scores each step independently so partial implementations
land in distinct ranges.

## Why this difficulty

L2: 2–4 chained operations on bundled data. The persona names five
operations explicitly (snap, zero-area drop, normalise, filter
blanks, aggregate); a faithful pipeline must order them correctly
(snap before dissolve so the snap actually unifies vertices;
normalise before filter so blank-after-strip rows are caught;
zero-area drop before dissolve so ghosts don't propagate). Bundled
inputs only — no fetching skill is exercised.

## Input / output formats

### Input

`inputs/lagos_zoning_legacy.gpkg`, layer `lagos_zoning_legacy` —
10 080 features in EPSG:26331:

| Bucket | Count | Notes |
|---|---|---|
| Main-grid parcels | 10 000 | 100×100 grid of 10 m × 10 m squares; corners perturbed by 0–30 µm; class cycled through six variant spellings |
| Blank-class parcels | 50 | separate offset grid; `zoning_class` is empty / whitespace / None / tab |
| Zero-area ghost polygons | 30 | collinear-vertex degenerates; `geometry.area` is 0; stray-but-plausible class label |

Schema: `parcel_id` (int), `lga_source` (str), `zoning_class` (str
or null), `area_m2` (float, nominal 100.0 — stale), `geometry`
(Polygon).

### Output

`outputs/zoning_aggregated.gpkg` — 4 features in EPSG:26331, one
per canonical class. Each feature is a single-part Polygon
(500 m × 500 m square = 250 000 m²) covering its quadrant of the
main grid.

Schema: `zoning_class` (str ∈ {Residential, Commercial,
Industrial, Agricultural}), `area_m2` (float, recomputed from
`geometry.area`), `geometry` (Polygon).

## Failure modes

1. **Skip the 1 mm snap.** Agent drops zero-area, normalises class,
   filters blanks, dissolves, recomputes area, but never calls
   `shapely.set_precision` or any equivalent. `unary_union` still
   completes on perturbed parcels but each per-class polygon comes
   out as a MultiPolygon riddled with sub-mm interior holes along
   the internal grid lines. *Detection:* `geometry_type_polygon_only`
   and `no_interior_holes` subchecks both fail; the rest still pass.
   Covered by `broken_no_snap` (score 0.75 under the per-task
   reasoned weights: these two snap-detection subchecks carry
   weight 3 each, so skipping the snap costs 6/24).
2. **Output in the wrong CRS.** A common confusion is "Web Mercator
   for any web-portal export" — the agent calls `to_crs(3857)`
   before writing. *Detection:* under the soft-CRS policy the grader
   reprojects the submission to EPSG:26331 for the geometric
   subchecks (which still pass on an otherwise-correct pipeline)
   and docks two points via the `crs_is_canonical` and
   `crs_in_meaningful_set` subchecks. Covered by `broken_wrong_format`
   (score 0.917 under the per-task reasoned weights; total weight 24).
3. **Wrong canonical casing.** Agent normalises every variant but
   picks ALL-CAPS canonical labels (`RESIDENTIAL`, …) instead of
   the persona's TitleCase (`Residential`, …). *Detection:*
   `canonical_class_vocabulary` subcheck fails; per-class-area
   matches case-insensitively so other checks still pass. Covered
   by `broken_wrong_canonical` (score 0.958 under the per-task
   reasoned weights; `canonical_class_vocabulary` is weight 1 as a
   cosmetic house-style slip).
4. **Skip the blank-row filter.** Agent normalises the class but
   keeps blank rows, which produce a fifth row in the output (or
   a blank-class polygon). *Detection:* count gate fails on a
   five-row output (5 vs 4, 25 % deviation), or
   `no_blank_class_rows` / `canonical_class_vocabulary` subchecks
   fail if the count squeaks past. Not covered by a broken; gate
   + subcheck are the principled detectors.
5. **Skip the zero-area drop.** Agent leaves zero-area ghosts in
   the input and dissolves them. unary_union collapses the lines
   into nothing area-wise, so per-class areas remain ≈ 250 000 m²,
   but the ghosts can land in *any* class depending on their
   stray label. *Detection:* the per-class-area subcheck flags any
   shift larger than 0.5 % away from 250 000 m²; if the ghosts
   total under that threshold, the IoU subcheck still bites because
   the ghost lines don't intersect the reference quadrants.
   Not covered by a broken; principled subchecks are the detector.
6. **Skip the per-class aggregation; emit per-parcel rows.** Agent
   does every cleaning step but forgets to dissolve, emitting all
   ~10 000 parcels. *Detection:* count gate fails (10 000 vs 4).
   Not covered by a broken; gate is the principled detector.
7. **Snap with a coarser tolerance.** Agent uses 1 m or 1 cm
   instead of 1 mm. At 1 m the parcel boundaries get rounded to
   integer-metre positions and the quadrants still snap cleanly
   (every coordinate is a multiple of 10 m by construction), so
   this happens to pass. At 0.1 m or finer this also passes. The
   task is robust to reasonable snap-tolerance choices because
   the perturbation magnitudes (≤ 30 µm) are well below all of
   them. *Detection:* not handled — the persona's "1 mm" is the
   declared parameter but the grader does not enforce it because
   any tolerance ≥ 30 µm produces the same output.
8. **Emit MultiPolygon throughout.** Agent does every step
   correctly but wraps each per-class result as a MultiPolygon
   (the dissolve is a single 500 m × 500 m Polygon, but
   `unary_union(...)` on a list always coerces). *Detection:*
   `geometry_type_polygon_only` subcheck fails; everything else
   passes. Not covered by a broken; the strict-Polygon subcheck
   is the principled detector.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — skip the 1 mm snap**.
A naive agent reads the GPKG, filters `area > 0`, builds a class
normaliser, drops blanks, and calls `gdf.dissolve(by="zoning_class")`
without snapping first. GEOS's internal precision-model fudge
swallows the sub-mm gaps in the area total but leaves hundreds of
tiny interior rings. Under the per-task reasoned weights the grader
awards 0.75 - the largest deduction of any single failure mode,
because the two snap-detection subchecks (`no_interior_holes`,
`geometry_type_polygon_only`) each carry weight 3 as the task's
central gotcha. This sits below the wrong-CRS solution (0.917) and
the cosmetic wrong-canonical-casing solution (0.958), so the central
failure is penalised most and the cosmetic failure least; the
score.json subcheck trail disambiguates the modes.
