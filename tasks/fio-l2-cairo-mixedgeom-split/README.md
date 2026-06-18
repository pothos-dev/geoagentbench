# fio-l2-cairo-mixedgeom-split

## Story

Yusra Al-Sayed, a heritage analyst at Egypt's Ministry of Antiquities,
has hand-curated a GeoJSON describing dozens of Cairo heritage sites:
each site contributes its enclosure polygon, its axial street
LineStrings, and its significant Point markers as separate features
sharing a common `site_id`, and the file mixes Polygon and
MultiPolygon variants in the same FeatureCollection. The downstream
desktop tool (a Ministry-internal QGIS plug-in) only ingests typed
GPKG layers in Egypt Red Belt (EPSG:22992) and refuses multi-part
polygons. She needs the agent to sort the features into per-type
layers, explode the multi-part polygons into singletons, reproject,
and preserve the site ID linking everything together.

## What this task probes

Format I/O composition: geometry-type stratification + multi-part
explode + CRS reprojection + multi-layer GPKG write, with attribute
preservation (`site_id` foreign key) across all three output layers.
The skill is composing *four* format / clean-up operations into one
correct GPKG, while keeping the cross-layer link discoverable.

## Why this difficulty

L2: a chain of four operations on bundled data. None of the
individual steps is hard, but the agent has to compose them in the
right order, route different geometry kinds to different layers,
explode without losing the part-to-site association, and write a
multi-layer GPKG (not three separate files). No fetching, no spatial
analysis. The task ships entirely from `inputs/heritage_sites.geojson`.

## Input / output formats

### Input

`inputs/heritage_sites.geojson` — a single FeatureCollection in
EPSG:4326 carrying 50 features across 10 heritage sites. Each site
contributes:

- 1 enclosure (Polygon for 5 sites, MultiPolygon for 5)
- 1–2 axial-street LineStrings
- 2–3 marker Points

Each feature has `site_id`, `feature_kind`, `name_en`, `name_ar`.

### Output

`heritage.gpkg` — a multi-layer GPKG with three layers:

| Layer | Geometry | Features |
|---|---|---|
| `points`   | Point        | 25 |
| `lines`    | LineString   | 15 |
| `polygons` | Polygon (singletons; no MultiPolygon) | 15 |

Every layer is in EPSG:22992 (Egypt Red Belt) and carries `site_id`
plus `feature_kind`, `name_en`, `name_ar`, `part_index`.

## Failure modes

Scores below are for the weighted 15-subcheck grader under the
2026-06-14 reasoned weights (total weight 32). The central-skill
detectors carry weight 4: `polygons_singletons_only` and
`polygons_count_within_tolerance` (the explode co-detectors) and
`crs_is_canonical` (the regional-CRS discriminator). The geometry-
agreement trio (`polygons_geometry_iou`, `points_geometry_per_site`,
`lines_geometry_per_site`) and `site_id_jaccard_union` carry weight 3.
Structural / cosmetic / pure-label checks carry weight 1: the
geometry-type trio, `total_count_within_tolerance`, the points/lines
per-layer counts, `site_id_populated`, and `crs_in_meaningful_set`.

1. **Agent did not produce a GPKG at all** (e.g. left output as the
   original mixed GeoJSON, or wrote three separate files).
   *Detection:* the `format_schema_valid` gate rejects (file isn't
   a GPKG with the three expected layers). Covered by
   `broken_wrong_format` (score 0.000).
2. **Agent wrote the GPKG but stuffed everything into a single
   layer** (no stratification by geometry type). *Detection:*
   the gate rejects — the expected layer names `points` / `lines` /
   `polygons` are absent. Not covered by a broken solution;
   principled detector is the gate's layer-name check.
3. **Agent stratified but did not explode MultiPolygons.**
   *Detection:* `polygons_singletons_only` (weight 4) fails
   (MultiPolygon present in polygons layer);
   `polygons_count_within_tolerance` (weight 4) also fails
   (unexploded count 10 is 33 % below the reference's
   post-explode count of 15, well outside the ±5 % tolerance).
   Covered by `broken_no_explode` (score 24/32 = 0.750).
4. **Agent forgot to reproject** (left output in EPSG:4326).
   *Detection:* the gate still accepts (4326 is a usable CRS), but
   both CRS subchecks fail (`crs_is_canonical` because 22992 is the
   canonical, `crs_in_meaningful_set` because 4326 is not in
   {22992, 32636}). The submission is reprojected to 22992 for the
   geometry subchecks, so geometric work that was otherwise correct
   in WGS84 still earns the geometry credits. A clean WGS84
   pipeline scores 27/32 ≈ 0.844 (loses the weight-4
   `crs_is_canonical` plus the weight-1 `crs_in_meaningful_set`).
   Not covered by a broken solution; the two CRS subchecks are the
   principled detector.
4b. **Agent reprojects into a defensible-but-non-canonical CRS**
   (UTM 36N, EPSG:32636, the generic metric pick for Cairo).
   *Detection:* the gate accepts the submission and the grader
   reprojects it into Egypt Red Belt for the spatial subchecks; the
   `crs_is_canonical` subcheck fails because the regional canonical
   is EPSG:22992, while `crs_in_meaningful_set` passes (32636 is in
   the accept set). A 32636 pipeline that is otherwise correct
   scores 28/32 = 0.875 (loses only the weight-4 `crs_is_canonical`).
   Not covered by a broken solution; the `crs_is_canonical` subcheck
   is the principled detector.
5. **Agent reprojected with x/y axis swap** (e.g. mis-set
   `always_xy` on a PROJ pipeline). *Detection:* coordinates land
   in the right CRS magnitude range so the gate passes, but the
   three weight-3 geometry subchecks `polygons_geometry_iou`,
   `points_geometry_per_site`, and `lines_geometry_per_site` all
   fail. Covered by `broken_geom_corruption` (score 23/32 ≈ 0.719).
6. **Agent dropped the `site_id` column** (made it a join key but
   forgot to write it). *Detection:* the gate's site_id-column
   check rejects on the first layer that lacks it. Not covered by a
   broken solution; principled detector is the gate.
7. **Agent dropped one whole geometry kind** (e.g. forgot points,
   wrote only lines and polygons). *Detection:* the gate's
   layer-name check rejects, *or* if the agent created an empty
   `points` layer the per-layer count subcheck and the site-id
   Jaccard subcheck both fail. Not covered by a broken solution;
   principled detector is the layer-name gate plus the count
   subchecks.
8. **Agent renamed `feature_kind` or otherwise lost the
   per-feature discriminator.** *Detection:* the per-site geometry
   subchecks fall back to `site_id`-only matching and lose
   resolution; if the agent also dropped or shuffled coordinates
   the per-site subchecks then fail. Cosmetically tolerated when
   geometry remains correct; sharply penalised when geometry
   drifts.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#3 — stratifying without
exploding**. A baseline agent that calls
`gdf[gdf.geom_type.isin(["Polygon","MultiPolygon"])]` and writes
that to the polygons layer ships MultiPolygons through unchanged.
The desktop tool rejects multi-parts; the grader catches this with
two simultaneous weight-4 subcheck failures (singletons + count)
that drop the score to 0.750.
