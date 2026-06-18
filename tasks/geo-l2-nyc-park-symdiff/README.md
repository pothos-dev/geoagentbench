# geo-l2-nyc-park-symdiff

## Story

Rachel Goldberg, a landscape architect at NYC Parks, is reconciling
the official NYC Parks polygon layer against an OSM-derived parks
export from the open-data portal. Both feed the city's "find a park"
map and they disagree in dozens of places. She needs the symmetric
difference between the two sources — every patch claimed by one but
not the other — collected into discrepancy clusters with
point-on-surface label anchors, computed in NY State Plane (Long
Island) for accurate areas but delivered as WGS84 GeoJSON the
cartographer can drop straight into the Parks Department's web map.

## What this task probes

Geometric-ops composition on two polygon layers in a single GPKG
container: read both layers → symmetric difference (`A xor B`) →
connected-component clustering (collect: single → multi) → per-cluster
source classification (which side(s) contributed) → point-on-surface
for label anchors → write two GeoJSONs in WGS84 (EPSG:4326). The skill
chain is "symdiff + cluster + classify + label-anchor", with a
correctness trap on point-on-surface vs centroid (centroids of concave
or multi-part disagreement clusters frequently fall outside the
geometry).

## Why this difficulty

L2: a multi-step chain (symdiff → cluster → collect → classify →
anchor) on bundled data with two outputs that must agree on
cardinality. No fetching, no spatial-analysis primitives. The
clustering step (connected components of the symdiff) and the
"representative-point not centroid" requirement push the chain past a
single operation but stay within the L2 budget.

## Input / output formats

### Input

`inputs/nyc_parks.gpkg` — GPKG with two layers, both in EPSG:6539:

| Layer | Rows | Columns | Description |
|---|---|---|---|
| `parks_official` | 1380 | `park_id`, `park_class`, `geometry` | Authoritative NYC Parks polygons (full Overture `base.land_use` / `subtype=park` slice over central NYC). |
| `parks_osm` | 1372 | `park_id`, `park_class`, `geometry` | OSM-derived parks. Same set as `parks_official` minus 20 dropped, with 15 polygons shifted by ~30 m, plus 12 hand-crafted extras in non-park locations. |

### Outputs

`outputs/parks_disagreement.geojson` — GeoJSON, WGS84 (EPSG:4326), one
MultiPolygon per discrepancy cluster:

| Column | Type | Description |
|---|---|---|
| `cluster_id` | int | Stable id assigned by the reference; submission may reorder. |
| `source` | str | One of `parks_official`, `parks_osm`, `both`. |
| `area_m2` | float | Cluster area in projected metres². |
| `geometry` | MultiPolygon | Cluster geometry (collected). |

`outputs/park_label_anchors.geojson` — GeoJSON, WGS84 (EPSG:4326), one
Point per cluster, **must lie inside** the cluster geometry:

| Column | Type | Description |
|---|---|---|
| `cluster_id` | int | Foreign key to disagreement file. |
| `source` | str | Mirrors disagreement row. |
| `geometry` | Point | Point-on-surface (representative point). |

The reference produces 46 clusters: 20 `parks_official`-only,
12 `parks_osm`-only, 14 `both`. Total disagreement area ≈ 5.2 km².

## Failure modes

1. **Output not GeoJSON** (e.g. agent wrote one of the files as
   GeoParquet, CSV, or Shapefile). *Detection:* the hard
   `format_schema_valid` gate's GeoJSON-FeatureCollection sniff
   rejects either output. Covered by `broken_wrong_format`
   (score 0.000).
2. **Output in the wrong CRS** (e.g. left in the projected EPSG:6539
   instead of reprojecting to WGS84 for the GeoJSON write).
   *Detection:* soft-CRS policy. A declared non-WGS84 CRS is
   reprojected to canonical for the geometric subchecks and docked
   by `crs_is_canonical` + `crs_in_meaningful_set`. Projected
   coordinates written *without* a declared CRS are treated as
   implicit WGS84 and fail `total_area_within_tolerance` +
   `unioned_geometry_iou` instead. Not covered by a broken
   solution; principled detectors are the subchecks.
3. **Skipped the cluster-collect step** — agent emitted one row per
   individual symdiff polygon (~128 rows instead of 46 clusters).
   *Detection:* `count_within_tolerance` (±10 %) fails (128 vs 46).
   Not covered by a broken solution; principled detector is the
   subcheck.
4. **Dropped one side of the symdiff** — agent computed only `B − A`
   (or only `A − B`), missing the other side's clusters. *Detection:*
   `count_within_tolerance`, `source_label_distribution`,
   `total_area_within_tolerance`, `unioned_geometry_iou` all fail;
   multipoly and anchors-inside still pass. Covered by
   `broken_partial` (weighted score 0.30 — the four highest-weighted
   overlay subchecks, w=3/3/4/4, all fail).
5. **Used centroid instead of point-on-surface for anchors** —
   centroids of concave / multi-part clusters land outside the
   geometry. *Detection:* `anchors_inside_disagreements` fails;
   everything else passes. Covered by `broken_centroids` (weighted
   score 0.90 — only the secondary anchors-inside subcheck, w=2,
   fails; the symdiff overlay is correct).
6. **Mislabelled the `source` attribute** — agent classified all
   clusters as one label (e.g. always "both"), losing the
   per-side attribution. *Detection:* `source_label_distribution`
   subcheck fails (set Jaccard or per-source count tolerance).
   Not covered by a broken solution; principled detector is the
   subcheck.
7. **Forgot MultiPolygon coercion** — output disagreement file
   contains plain Polygon rows. *Detection:*
   `all_multipolygon_disagreement` subcheck fails. Not covered by a
   broken solution; principled detector is the subcheck.
8. **Cluster / anchor cardinality mismatch** — agent emitted N
   clusters but M anchors with N ≠ M. *Detection:*
   `anchor_count_matches_disagreements` subcheck fails.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#5 — using `centroid` instead
of `representative_point()` for the label anchors**. A baseline that
correctly computes the symdiff, clusters, and source labels but
reaches for `geom.centroid` will pass everything except the
anchors-inside subcheck (w=2; 18/20 = 0.90). The
next-most-likely is **#2 — missing the final WGS84 reprojection**:
observed live both as declared-EPSG:6539 output (docked on the two
CRS subchecks, 18/20 = 0.90, or 17/20 = 0.85 with a Polygon leak)
and as undeclared projected coordinates (fails the two highest-weight
overlay subchecks area + IoU, w=4 each, 12/20 = 0.60).
