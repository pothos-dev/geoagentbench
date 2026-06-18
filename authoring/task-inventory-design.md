# Task Designer Agent — Brief

You are the task designer for a benchmark evaluating geospatial agent systems. Your job is to produce a complete inventory of 36 task specifications that, taken together, satisfy the coverage and validity constraints below. You do **not** write the reference solutions or graders — only the task specs and supporting metadata.

Read `benchmark-design.md` (at the benchmark root) first. This document supplements it; benchmark-design.md is authoritative on framing, scope, and HTTP contract.

---

## Mission

Produce `authoring/inventory.md` (the source of truth) containing 36 task rows, each with full axis assignments and a one-paragraph realism story. The inventory is the input to all downstream task authoring (per-task `task.json`, `generate.py`, `grade.py`).

The benchmark targets the **GIS analyst assistant** persona: an agent that fetches, transforms, analyses, and converts vector geospatial data on behalf of a human operator (urban planner, ecologist, public-sector spatial analyst).

---

## Hard constraints

### Task count and distribution

- **Total tasks: 36.**
- **6 categories × (3 L1 + 2 L2 + 1 L3) = 18 L1 + 12 L2 + 6 L3.**
- The six task categories: `data_discovery`, `format_io`, `crs_reprojection`, `geometric_ops`, `spatial_analysis`, `data_cleaning`.
- Difficulty levels:
  - **L1** — single operation on bundled data. Probes basic competence. No discovery / fetching.
  - **L2** — 2–4 chained operations on bundled data. Probes planning and composition.
  - **L3** — full real-world workflow: discover → fetch → transform → analyze → format-convert → output. May include intentional data-quality issues.

### Coverage target

Every variant on every axis (listed below) must be hit by at least one task. The inventory **must** include a coverage matrix (axis × variant → task IDs that hit it) demonstrating ≥1× coverage. Uncovered variants are a defect.

### Per-task quality bar

Each task must satisfy:

1. The instruction is natural language but unambiguous — exactly one correct answer family exists.
2. The task has a plausible real-world story (named persona + their question + what they do with the answer). Contrived axis-checking tasks are rejected.
3. The task is drift-tolerant — count/area tolerances ≥ ±5%, set-membership via Jaccard, ranking-style answers preferred. No pivot on a single feature being present/absent (except where the question is "is X in the data" by design).
4. The reference solution must be runnable with the pinned reference toolchain (Python + GeoPandas + Shapely + PyOGRIO + DuckDB-spatial + PROJ).
5. L1 tasks must use bundled data only (source axis = `bundled_local`).
6. L3 tasks must use a non-bundled source (Overture / Overpass current / Overpass historical / Geofabrik).
7. Output formats are restricted to: JSON, CSV, GeoJSON, Parquet, GeoParquet, GPKG. No Shapefile, KML, or unstructured outputs (Markdown / plain text / single number with no schema).
8. Input formats are unrestricted — the full input format axis (including legacy formats like Shapefile and KML) is in scope to test the agent's reading skills.

---

## Coverage axes

The coverage matrix is the union of all variants on all axes. Tasks naturally touch multiple axes; one task can cover one variant on each of ~7 axes simultaneously. Use this density.

### Axis 1 — Geometric operations (14 variants)

Buffer (include planar variants and at least one geodesic large-extent variant), Intersection, Union (including cascaded), Difference, Symmetric difference, Clip, Simplify, Dissolve, Convex hull, Centroid, Point-on-surface, Bounding box, Explode (multi → single), Collect (single → multi).

### Axis 2 — Spatial analysis (17 variants)

Six topological-predicate spatial joins: within, intersects, contains, touches, crosses, overlaps. Plus: Nearest neighbour, k-nearest neighbours, Distance matrix (full m × n), Within-distance filter, Point-in-polygon count, Spatial aggregation (must include at least one task using non-geometric attribute work — filter, value normalisation, type coercion — alongside the spatial step, and at least one task using area-weighted mean over polygon overlaps), Hot-spot ranking. Plus four routing/network ops: Shortest path, Network distance matrix, Isochrone, Closest facility (by network distance).

### Axis 3 — Format I/O (7 variants, input side)

GeoJSON, GeoParquet, Shapefile, GPKG, CSV with WKT, FlatGeobuf, KML/KMZ.

Output formats restricted to: JSON, CSV, GeoJSON, Parquet, GeoParquet, GPKG (six). The input set is for what tasks deliver to the agent; the output set is what the agent must produce. Outputs may include multi-layer single files (e.g. GPKG with multiple layers, or GeoJSON with nested feature collections) where the task narrative justifies it.

### Axis 4 — CRS reprojection (7 variants)

WGS84 (EPSG:4326), Web Mercator (EPSG:3857), Conformal projection (UTM family or national Lambert Conformal Conic), Equal-area projection (LAEA / Mollweide / Albers), Polar projection (polar stereographic), Antimeridian-crossing geometries, Datum shift (e.g. WGS84 ↔ ETRS89, NAD83, GDA2020 — must invoke a real PROJ transformation pipeline, not a pure projection swap).

### Axis 5 — Data discovery and fetching (5 variants)

Overture Maps current release (cloud-hosted Parquet), OSM via Overpass API — current, OSM via Overpass API — historical (`[date:...]` directive), Geofabrik regional PBF, Bundled local file (served by the harness over HTTP).

### Axis 6 — Data quality issues (15 variants)

Invalid geometries (self-intersections / bowties), Wrong ring orientation (RFC 7946 violation), Empty or null geometry, Zero-area polygons, MultiPolygon / Polygon coercion, Mixed geometry types in one layer, Sliver polygons (overlay artefacts from imperfectly-aligned datasets), Duplicate geometries, Unsnapped near-coincident vertices, Mixed CRSes in one source (e.g. multi-layer GPKG with disagreeing CRSes), Encoding issues (Latin-1 / UTF-8 mojibake), Null or missing attributes, Attribute type coercion (numeric-as-string, dates-as-strings), Inconsistent attribute values (variant spellings/casings of the same logical entity), Shapefile column truncation (10-character dBase limit on write).

### Axis 7 — Geometry type (7 variants)

Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon, GeometryCollection. The GeometryCollection task likely needs a custom-crafted GeoJSON input; the agent must split or normalise it before processing.

### Axis 8 — Overture themes and types (15 variants)

`places.place`, `buildings.building`, `buildings.building_part`, `transportation.segment`, `transportation.connector`, `base.water`, `base.land`, `base.land_cover`, `base.land_use`, `base.infrastructure`, `base.bathymetry`, `addresses.address`, `divisions.division`, `divisions.division_area`, `divisions.division_boundary`.

### Axis 9 — OSM tag families (12 variants)

`highway=*`, `building=*`, `amenity=*`, `shop=*`, `landuse=*`, `natural=*`, `waterway=*`, `railway=*`, `boundary=administrative`, `place=*`, `leisure=*`, public-transport route relations.

### Axis 10 — Geographic region (12 candidate variants — pool)

Vienna (AT), London (UK), Paris (FR), Tokyo (JP), Bangkok (TH), Cairo (EG), New York (US), Cape Town (ZA), Lagos (NG), Svalbard (NO), Fiji, Antarctica. Distinctive properties of each region (CRS / script / data density / latitude / antimeridian) drive variant selection — see `thesis.typ` Region table for the full property notes. You do not need to cover all 12 regions in 36 tasks; pick a subset that exercises:

- ≥ 1 task in Vienna (author's home region for ground-truth sanity checks)
- ≥ 1 task with non-Latin script attributes (Tokyo or Bangkok or Cairo)
- ≥ 1 task in the southern hemisphere (Cape Town, Buenos Aires substitute, or Antarctica)
- ≥ 1 task at high latitude (Svalbard or Antarctica) — pairs with polar CRS variant
- ≥ 1 task crossing the antimeridian (Fiji) — pairs with antimeridian CRS variant
- ≥ 1 task in a sparsely-mapped region (Lagos)

### Axis 11 — Data scale (3 variants)

Small (~10² features, fits trivially in memory), Medium (~10⁴–10⁵ features, fits but naive O(n²) is slow), Large (10⁶+ features, requires intelligent filtering / partition pushdown at fetch time — at least one task must exercise this).

---

## Strategy / process

Execute in phases. Each phase produces or extends `authoring/inventory.md`. Do not skip ahead.

### Phase 1 — Inventory schema

Define the inventory table schema. Recommended columns:

`task_id` · `category` · `difficulty` · `region` · `data_source` · `primary_op` · `secondary_ops` · `format_in` · `format_out` · `crs_in` · `crs_out` · `geometry_type` · `data_scale` · `data_quality_issue` (if any) · `theme_or_tags` · `story` (one paragraph) · `output_artifacts` (list of `expected_outputs[]`)

Format the inventory as a markdown document with one row per task, plus a coverage-matrix appendix.

### Phase 2 — L1 tasks (18 tasks)

L1 conditions: bundled data, single primary operation, simple narratives. Three tasks per category.

Use L1 to cover the bulk of:
- Axis 1 (Geometric ops): all 14 fit naturally — many will live in `geometric_ops` L1 + L1s in adjacent categories.
- Axis 2 (Spatial analysis): the simpler half — 1-NN, point-in-polygon count, simple spatial joins (within / intersects / contains).
- Axis 3 (Formats): distribute across L1 input/output combinations.
- Axis 4 (CRS): WGS84, Web Mercator, basic conformal/equal-area choices.
- Axis 6 (Data cleaning): the simpler issues — null geometry, ring orientation, type coercion.
- Axis 7 (Geometry type): all 7 fit in L1 if distributed across categories.
- Axis 11 (Data scale): all small or medium for L1.

Do not allocate routing ops, datum shifts, or large data-scale to L1 — those need L2/L3.

### Phase 3 — L2 tasks (12 tasks)

L2 conditions: bundled data, 2–4 chained operations. Two tasks per category.

Use L2 to cover:
- Most of Axis 6 (Data cleaning) — cleaning is intrinsically multi-step and a natural L2 home.
- Harder Axis 2 (Spatial analysis) variants — k-NN, distance matrix, hot-spot ranking, the four less common spatial-join predicates (touches / crosses / overlaps).
- Antimeridian and polar CRS handling — pair with appropriate regions.
- GeometryCollection (Axis 7) — likely a custom-crafted L2 task requiring decomposition before further processing.
- Cross-category compositions: e.g. cleaning slivers then dissolving (cleaning + geometric op).

### Phase 4 — L3 tasks (6 tasks)

L3 conditions: live data, full workflow, strong real-world stories. One task per category.

Use L3 to cover:
- Axis 5 (Data sources): all four non-bundled variants must be hit across the 6 L3 tasks (Overture current, Overpass current, Overpass historical, Geofabrik PBF). The 6th L3 can use bundled data only if the workflow nature warrants it — but normally L3 means live.
- Routing/network ops in Axis 2 — these need real road networks (OSM / Overture transportation).
- Axis 11 "Large" — at least one L3 task exercises filter-before-load on partitioned Parquet.
- Datum shift task (Axis 4) — typically belongs to L3 cadastral / engineering scenario.
- The harder regions — non-Western or high-latitude or antimeridian.
- Real-world data-quality realism — most live-data L3 tasks naturally inherit messy data; document which quality issues each L3 task exposes.

### Phase 5 — Coverage check

After Phase 4, build the coverage-matrix appendix:
- Rows: every variant of every axis (all ~114 variants).
- Columns: axis name, variant name, list of task_ids that hit it, hit count.
- Highlight any variant with hit count = 0 — those are gaps.

For each gap, do one of:
1. Modify an existing task to incorporate the missing variant (preferred — preserves story integrity).
2. Swap a task wholesale — only if no graceful incorporation exists.

Iterate until every variant has hit count ≥ 1.

### Phase 6 — Realism / story audit

Audit every task's `story` paragraph:
- Is the persona named and plausible? (urban planner, ecologist, public health analyst, transport planner, etc.)
- Does the question they're asking sound like something a human would actually ask?
- Does the answer they receive lead to a plausible decision or report?

Reject tasks that fail this audit. Replace them and re-run Phase 5.

---

## Heuristics

- **Story-first for L3.** Start with a real-world scenario; map onto axes second. Axis-first L3 tasks read as contrived.
- **Region-anchored.** Pick the region first per task; it constrains language, CRS, data sources, and themes — reduces combinatorial explosion.
- **Tight axes first.** Axis 2 (Spatial analysis, 17 variants) and Axis 6 (Data cleaning, 15 variants) are the tightest fits. Allocate them across the entire 36-task inventory, not just within their nominal category.
- **Density per task.** A task using Vienna + OSM `amenity=*` + GeoJSON-in / GeoParquet-out + MGI Lambert + centroid + point geometry covers ~7 axes in one row. Aim for this density in L2 and L3 especially.
- **Don't manufacture rare variants in implausible contexts.** A "compute road isochrones in Antarctica" task technically pairs polar + isochrone but is absurd. If two variants don't combine plausibly, separate them across two tasks.
- **Symmetry between Overture and OSM coverage.** Tasks that exercise an Overture theme can often have an OSM-tag-family sibling — both axes are about navigating large data sources. Use this to balance source-axis representation.

---

## Deliverables

Produce these files in order. Stop and ask the user before proceeding to the next file if anything is ambiguous.

1. **`authoring/inventory.md`** — the inventory table with 36 rows + coverage-matrix appendix. Source of truth for the benchmark.

2. **`authoring/coverage.md`** *(optional, can be inside inventory.md)* — pivoted view of axis × variant → task IDs.

Do **not** write per-task `task.json`, `generate.py`, or `grade.py` files. Those are downstream artefacts authored after the inventory is approved.

---

## Output format reminder

Inventory rows are markdown table rows. Stories are one paragraph each. EPSG codes are written as `EPSG:NNNN`. Output artefact specs match the HTTP contract's `expected_outputs[]` shape (`{name, format, crs?, geometry_type?}`).

If you need information you don't have, ask the user — do not invent constraints.
