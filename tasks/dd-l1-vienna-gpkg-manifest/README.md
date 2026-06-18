# dd-l1-vienna-gpkg-manifest

## Story

Lukas Hofer, a junior planner at Vienna's MA 18 urban-planning
department, inherits a multi-layer GPKG from a retired colleague who
maintained the bicycle-network reform dataset. Before he scripts
against it he wants a one-page manifest listing each layer's name,
declared CRS, geometry type, feature count, and bounding box, so he
can decide which of the seven layers feed next month's briefing to
the city councillor and which are stale auxiliary cuts.

## What this task probes

GPKG multi-layer enumeration plus per-layer schema introspection: an
agent must list every layer in the container, read each layer's
declared CRS and geometry type without reprojecting or recomputing
anything, count the features, and compute the bounding box in the
**layer's own CRS** (no reprojection — the manifest is for the file
as it is, not as the agent thinks it should be). The skill being
measured is the GIS-literate move of opening a multi-layer container
with a tool that exposes its schema (pyogrio / fiona / ogrinfo /
DuckDB-spatial) rather than treating it as a single-layer file.

## Why this difficulty

L1: a single primary GIS operation (schema introspection) over a
fully bundled multi-layer GPKG fixture. No fetching, no
transformations, no spatial joins, no reprojection — the
"no reprojection" instruction is explicit in the prompt. The only
thing more L1 than this would be a single-layer schema check.

## Input / output formats

### Input

`inputs/vienna_planning.gpkg` — single GPKG with seven layers, all in
EPSG:31287 (MGI / Austria Lambert):

| Layer | Geometry | Features | Notes |
|---|---|---|---|
| `districts` | Polygon | 22 | Locality / microhood admin polygons (inner Vienna) |
| `parks` | MultiPolygon | 119 | Overture `base.land_use` `class='park'` |
| `waterbodies` | Polygon | 33 | Overture `base.water` (Donaukanal, ponds, etc.) |
| `schools` | Point | 40 | Overture `places.place` `category='school'` |
| `cafes` | Point | 392 | Stale auxiliary cut |
| `supermarkets` | Point | 87 | Stale auxiliary cut |
| `cycleway_segments` | LineString | 271 | Cycle-network segments |

### Output

`outputs/manifest.json` — a top-level JSON list with one record per
layer, fields:

```json
[
  {
    "layer_name": "districts",
    "crs": "EPSG:31287",
    "geometry_type": "Polygon",
    "feature_count": 22,
    "bbox": [623867.39, 481236.58, 626371.31, 484403.73]
  }
]
```

`bbox` is in the layer's own CRS (metres in EPSG:31287), in
`[xmin, ymin, xmax, ymax]` order. Order of records in the list is
not graded — the grader indexes by `layer_name`.

## Failure modes

1. **Agent only enumerated the layers it could guess from the task
   text** (`districts`, `parks`, `schools` from the inventory's
   primary trio) and missed the four auxiliary layers. *Detection:*
   `layers_complete` fails plus the four absent layers' 16 subchecks
   fail; only the three covered layers' 12 subchecks (weight 12 of
   32) pass. Covered by `broken_partial_layers` (score 0.375).
2. **Agent silently reprojected layers to EPSG:4326** before
   introspecting and reported `crs = "EPSG:4326"` plus bboxes in
   degrees. *Detection:* every layer's `crs_correct` and
   `bbox_correct` flips. Covered by `broken_wrong_crs_bbox`
   (score 0.5625).
3. **Agent wrote the manifest in the wrong format** (CSV, plain text,
   a JSON object instead of a list). *Detection:* Gate 1 rejects
   (top-level type check or required-keys check). Covered by
   `broken_wrong_format` (score 0.000).
4. **Agent treated the GPKG as single-layer** and only opened the
   default first layer (typically `cafes` alphabetically or the
   first-inserted layer). *Detection:* `layers_complete` fails plus
   six absent layers' 24 subchecks fail; only the present layer's 4
   subchecks (weight 4 of 32) pass. Not covered by a broken
   solution; principled detector is `layers_complete` plus the
   absent-layer subchecks.
5. **Agent reported each layer's bbox by computing the bounding box
   over *all* features in *every* layer** (the GPKG-wide bbox).
   *Detection:* every layer's `bbox_correct` fails because the
   per-layer extents differ. Not covered by a broken solution;
   principled detector is the per-layer `bbox_correct` subchecks.
6. **Agent reported geometry type as the per-feature type of the
   first feature** rather than the GPKG-declared layer type — e.g.
   reporting `Polygon` for `parks` (declared MultiPolygon) because
   the first feature happens to be a single Polygon. *Detection:*
   `parks_geom_type_correct` fails. Not covered by a broken
   solution; principled detector is the geom-type subcheck.
7. **Agent invented a CRS string format** like `"31287"` or
   `"WGS 84 / Austria Lambert"` rather than the canonical
   `"EPSG:31287"`. *Detection:* every `crs_correct` subcheck fails.
   Not covered by a broken solution; principled detector is the per-
   layer `crs_correct` subchecks (case-insensitive exact match on
   the EPSG-code string).
8. **Agent off-by-one on feature counts** (e.g. counted features but
   subtracted 1 for a header row that GPKG does not have, or
   reported `len(layers) - 1` somewhere). *Detection:*
   `<layer>_count_correct` fails for the affected layers. Not
   covered by a broken solution; principled detector is the count
   subcheck.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — partial layer
enumeration**. A weak agent that pattern-matches the inventory row's
primary trio (`districts`, `parks`, `schools`) and writes a
hand-coded manifest of just those three layers — without actually
opening the GPKG — produces a structurally perfect output that
scores 0.375. That is clearly distinguishable from a wrong-format
solution (0.000), a CRS-confusion solution (0.5625), and a fully
correct solution (1.000).
