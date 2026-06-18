# Geospatial benchmark — author context

This document is the working brief for a task-design agent. It contains everything a task author needs to **understand the GIS skill space the benchmark covers** without dragging in the inventory-design framing or the HTTP-contract details. Read it before authoring any task.

The benchmark targets the **GIS analyst assistant** persona: an agent that fetches, transforms, analyses, and converts vector geospatial data on behalf of a human operator (urban planner, ecologist, public-sector spatial analyst). Every task you author should feel like a real request such an operator would send to such an agent — never an axis-checking exercise dressed up as a task.

---

## The six operation categories

Every task belongs to exactly one of these. The category names what GIS skill the task primarily probes; secondary categories may also appear inside the task.

1. **Data discovery & fetching** — locating and retrieving vector data from Overture, OSM/Overpass, Geofabrik PBFs, including historical Overture releases. Probes the agent's domain knowledge of where canonical vector data lives.
2. **Format I/O & conversion** — reading and writing vector formats with attribute preservation. Probes format literacy and gotchas (Shapefile 10-character column truncation, KML's HTML-in-description, GeoParquet schema metadata, etc.).
3. **CRS reprojection** — projecting between coordinate reference systems with correct datum handling. Projection-sensitive tolerances apply here.
4. **Geometric operations** — buffer, intersection, union, difference, simplify, dissolve. Single-operation or chained.
5. **Spatial analysis** — spatial joins, nearest-neighbour, distance and accessibility computation, point-in-polygon counts, hot-spot ranking, attribute-based aggregation, network routing.
6. **Data cleaning** — invalid-geometry repair, deduplication, snapping, MultiPolygon handling, null handling, encoding fixes.

---

## Difficulty levels

- **L1 — single operation on bundled data.** One operation on data shipped with the task. Probes basic competence. No discovery / fetching. Bundled inputs only.
- **L2 — 2–4 chained operations on bundled data.** Probes planning and composition. Bundled inputs only.
- **L3 — full real-world workflow.** Discover → fetch → transform → analyze → format-convert → output. Live data from Overture / Overpass / Geofabrik. May include intentional data-quality issues that the agent must detect and handle.

The expected score gradient L1 ≫ L2 ≫ L3 is itself a benchmark-validity check.

---

## Realism is non-negotiable

Each task must satisfy:

1. **Plausible real-world story.** Named persona + their question + what they do with the answer. The persona name + role lives in `README.md > Story` for the human reviewer's benefit, e.g. "Lukas, a junior planner at MA 18, needs… so he can decide…". The persona drives the *voice* of the `task.json` instruction string, but the persona does not introduce themselves *to the agent* — real users don't open chats with "Hi, I'm Lukas, a junior planner at MA 18". A task without a real-world persona behind it is rejected, but smuggling the persona's CV into the instruction string is also rejected. See `authoring/task-design-prompt.md > Instruction-string rules` for the voice rules.
2. **Unambiguous instruction.** Natural-language task prompt admits exactly one correct answer family. Multiple acceptable answers are forbidden by design.
3. **Drift-tolerant by construction.** Counts and areas graded with explicit tolerances (typically ±5%). Set-membership questions use Jaccard similarity rather than exact equality. Ranking-style questions ("which is largest?") are preferred where they fit. Answers must not pivot on a single feature being present or absent (except where the question is "is X in the data?" by design).
4. **Reference-runnable.** The reference solution must be runnable with the pinned reference toolchain — Python + GeoPandas + Shapely + PyOGRIO + DuckDB-spatial + PROJ — declared in `eval/pyproject.toml` (`uv run` from `eval/`).

---

## Output format restriction

Output formats are restricted to:

`JSON | CSV | GeoJSON | Parquet | GeoParquet | GPKG`

No Shapefile, KML, or unstructured outputs (Markdown, plain text, single number with no schema). Multi-output tasks declare each output file in `task.json` and the reference produces them under `reference/outputs/<name>` using exactly the names declared.

**Input formats are unrestricted** — the full input format axis (including legacy formats like Shapefile and KML) is in scope to test the agent's reading skills. Inputs come from `data/` (bundled) or live fetch (L3).

---

## Geometric operations covered

| Operation | Description |
|---|---|
| Buffer | Generates a polygon at a given distance around a feature. Planar buffers operate in projected metres. Geodesic buffers handle large extents and high latitudes correctly. |
| Intersection | Returns the geometric overlap of two geometries. |
| Union | Combines geometries into a single geometry; cascaded union dissolves shared boundaries across many features. |
| Difference | Subtracts one geometry from another, returning the part of the first that lies outside the second. |
| Symmetric difference | Returns the parts of two geometries that do not overlap, i.e. their union minus their intersection. |
| Clip | Restricts a geometry to the region inside a clip mask, often a rectangle or polygon boundary. |
| Simplify | Reduces vertex count while preserving overall shape within a tolerance. |
| Dissolve | Groups features by an attribute and unions their geometries within each group. |
| Convex hull | The smallest convex polygon that contains all input vertices. |
| Centroid | The geometric centre point of a feature. |
| Point-on-surface | A representative point guaranteed to lie inside the geometry, useful for label placement on concave shapes. |
| Bounding box | The axis-aligned minimum rectangle enclosing a geometry, also called the envelope. |
| Explode | Splits a multi-part geometry into one feature per part. |
| Collect | Aggregates single-part features into a multi-part geometry. |

---

## Spatial-analysis operations covered

| Operation | Description |
|---|---|
| Spatial join — within | Joins features from set A to features in set B whose geometry contains A's geometry entirely. |
| Spatial join — intersects | Joins features from A to B where the two geometries share any portion of space. |
| Spatial join — contains | Joins features from A to B where A's geometry entirely encloses B's geometry. |
| Spatial join — touches | Joins features whose geometries share a boundary but no interior points. |
| Spatial join — crosses | Joins features whose geometries pass through one another at lower dimension, e.g. a line crossing a polygon. |
| Spatial join — overlaps | Joins features of equal dimension whose interiors intersect but neither geometry fully contains the other. |
| Nearest neighbour | Finds the single closest feature in set B for each feature in set A. |
| k-nearest neighbours | Finds the k closest features in B for each feature in A. |
| Distance matrix | Computes pairwise distances between every feature of set A and every feature of set B. |
| Within-distance filter | Selects features in B that lie within a given distance threshold of features in A. |
| Point-in-polygon count | Counts how many points from set A fall inside each polygon in set B. |
| Spatial aggregation | Aggregates one or more attributes of features in A grouped by polygon B, using reductions such as sum, mean, count, or area-weighted mean over polygon overlaps. Encompasses the non-geometric attribute work (filters, value normalisation, type coercion) that real-world aggregation requires alongside the spatial step. |
| Hot-spot ranking | Ranks polygons by a spatially derived metric such as density or aggregated attribute to surface a top-N. |
| Shortest path | Computes the optimal route between two points along a road network. |
| Network distance matrix | Computes pairwise network distances between two feature sets along a road graph. |
| Isochrone | Polygon of all locations reachable within a given travel time or distance from an origin along a network. |
| Closest facility | Identifies the network-nearest facility from a set of candidates for each demand point. |

---

## Vector formats covered

| Format | Description |
|---|---|
| GeoJSON | Text-based JSON format with embedded geometry; lingua franca for web mapping. |
| GeoParquet | Columnar binary format with WKB geometry and CRS metadata; efficient for analytics on large feature sets. |
| Shapefile | Esri's legacy multi-file vector format; widespread but with well-known limits including a 10-character attribute name cap and a 2 GB per-file size limit. **Input only** (not allowed as output). |
| GPKG | OGC standard SQLite-based container; supports multiple layers in a single file. |
| CSV with WKT | Plain-text rows with a geometry column encoded as Well-Known Text; common output of business systems and SQL exports. |
| FlatGeobuf | Streamable binary format with a built-in spatial index, designed for HTTP range requests and partial reads. |
| KML / KMZ | XML-based format originating in Google Earth; KMZ is a zipped variant. **Input only** (not allowed as output). |

Output-only set: `JSON, CSV, GeoJSON, Parquet, GeoParquet, GPKG`.

---

## CRS variants covered

| Variant | Description |
|---|---|
| WGS84 (EPSG:4326) | Universal geographic CRS in degrees of latitude and longitude; default for GeoJSON. |
| Web Mercator (EPSG:3857) | Conformal cylindrical projection used by web map tile services; severe area distortion at high latitudes. |
| Conformal projection | Preserves local shape, angles, and short distances. UTM family and national Lambert Conformal Conic systems are typical instances. |
| Equal-area projection | Preserves polygon area at the cost of angular distortion. Lambert Azimuthal Equal-Area, Mollweide, Albers. |
| Polar projection | Polar stereographic family used at high latitudes, where standard cylindrical projections diverge. |
| Antimeridian-crossing geometries | Features whose geometry spans the ±180° meridian, requiring careful handling to avoid wrap-around artefacts. |

(Datum-shift handling is **out of scope** for v1 of the benchmark.)

---

## Data sources

| Source | Description |
|---|---|
| Overture Maps (current release) | Latest Overture release, hosted as partitioned Parquet on cloud object storage; covers places, buildings, transportation, base, addresses, divisions themes. |
| OSM Overpass — current | Live OSM database queried through the Overpass API; suitable for tag-filtered extracts of small to medium regions. |
| OSM Overpass — historical | Overpass attic queries against a past timestamp using the `[date:...]` directive. |
| Geofabrik PBF | Pre-built OSM regional extracts at country, state, or city level, distributed as `.osm.pbf`. Suitable for bulk processing. |
| Bundled local file | Input shipped with the task in `data/` and served by the harness over HTTP at runtime. |

L1 tasks must use **bundled local file** only. L3 tasks must use a non-bundled source (Overture / Overpass current / Overpass historical / Geofabrik). L2 may go either way but defaults to bundled.

**Overture is the default authoring source for bundled data.** When an L1 / L2 task needs real-world geographic features (boroughs, buildings, POIs, roads, water, land use, etc.), the bundled input must be produced by slicing a small bbox out of an Overture release at authoring time and committing the slice into `data/`. This holds regardless of the task's *output* format — fetch from Overture, then write the slice to whatever format the task declares (GeoJSON, GPKG, Shapefile, etc.). See `authoring/overture-reference.md` for collection list, hosting URLs, and DuckDB query patterns.

Pin the Overture release version (`YYYY-MM-DD.N`) inside the authoring helper (`data/_prepare_input.py`) so re-running it later remains reproducible. **Do not** download bundled data from random GitHub repos, gists, blog mirrors, or any source whose contents could change without notice.

Fall back to OSM Overpass or Geofabrik *only* when the task is intrinsically about an OSM tag family with no Overture equivalent (e.g. `boundary=protected_area`, niche `amenity=*` values). Record the rationale in `IMPLEMENTATION_NOTES.md > Open issues` so the orchestrator can audit it.

Hand-crafted inputs are still permitted (and sometimes required — e.g. mixed-geometry GeoJSON, intentionally-malformed Shapefiles, encoding-issue test files). When you hand-craft, document why in the helper's docstring.

---

## Data quality issues covered

| Issue | Description |
|---|---|
| Invalid geometries | Self-intersecting rings, bowties, and other geometries that violate simple-feature rules. |
| Wrong ring orientation | Exterior rings stored clockwise or interior rings counter-clockwise, violating the RFC 7946 right-hand rule. |
| Empty or null geometry | Features with `null` or empty geometry that pass parsing but carry no spatial extent. |
| Zero-area polygons | Degenerate polygons whose vertices are collinear or coincident. |
| MultiPolygon / Polygon coercion | Input declares Polygon but contains multi-part features, or vice versa. |
| Mixed geometry types | A single layer carrying multiple geometry types, e.g. Points and LineStrings together. |
| Sliver polygons | Tiny artefact polygons produced by overlaying imperfectly-aligned datasets. |
| Duplicate geometries | Multiple features sharing identical geometry, often with conflicting attribute values. |
| Unsnapped near-coincident vertices | Vertices that should be identical but differ by sub-millimetre. |
| Mixed CRSes in one source | Multi-layer container, e.g. a GPKG, in which layers declare different CRSes. |
| Encoding issues | Text attributes stored in one encoding (e.g. Latin-1) but declared as another (UTF-8). |
| Null or missing attributes | Feature rows with null values in fields the task references. |
| Attribute type coercion | Numeric values stored as strings, dates stored as strings or integers. |
| Inconsistent attribute values | The same logical entity recorded under multiple spellings, casings, or punctuation across rows. |
| Shapefile column truncation | The dBase 10-character attribute name limit silently truncates longer column names on write. |

---

## Geometry types

| Type | Description |
|---|---|
| Point | A single coordinate pair. |
| LineString | An ordered sequence of two or more coordinates. |
| Polygon | A closed area defined by an exterior ring and zero or more interior rings (holes). |
| MultiPoint | A collection of Points carried as a single feature. |
| MultiLineString | A collection of LineStrings carried as a single feature. |
| MultiPolygon | A collection of Polygons carried as a single feature. |

(GeometryCollection is **out of scope** for v1.)

---

## Overture themes and types

| Type | Description |
|---|---|
| `places.place` | Points of interest with names, categories, brands, addresses, websites. |
| `buildings.building` | Building footprint polygons with attributes for height, building class, roof shape, has_parts flag. |
| `buildings.building_part` | Sub-component polygons that attach to a parent building. |
| `transportation.segment` | Line geometry representing a stretch of road, path, or rail, with class, names, restrictions, speed-limit attributes. |
| `transportation.connector` | Point geometry at the junction between transportation segments. |
| `base.water` | Water bodies and watercourses. |
| `base.land` | Terrestrial natural features. |
| `base.land_cover` | Generalised land-cover classes derived from satellite observation. |
| `base.land_use` | Designated land use such as residential, commercial, industrial, agricultural, recreational. |
| `base.infrastructure` | Built infrastructure including bridges, dams, communication towers, utility installations. |
| `base.bathymetry` | Undersea depth contours and seabed features. |
| `addresses.address` | Postal address records. |
| `divisions.division` | Administrative entity record. |
| `divisions.division_area` | Polygon geometry of an administrative area. |
| `divisions.division_boundary` | Line geometry representing a boundary segment between adjacent divisions. |

---

## OSM tag families

| Tag family | Description |
|---|---|
| `highway=*` | Roads, streets, footways, cycleways; the highest-volume tag family in OSM. |
| `building=*` | Building footprints carried as closed ways or multipolygon relations. |
| `amenity=*` | Schools, hospitals, restaurants, banks, parking, benches. |
| `shop=*` | Retail points of interest. |
| `landuse=*` | Polygonal areas of designated land use. |
| `natural=*` | Natural features as points, lines, or polygons. |
| `waterway=*` | Linear watercourses. |
| `railway=*` | Rail infrastructure: tracks, stations, platforms, tram lines. |
| `boundary=administrative` | Administrative boundaries with `admin_level` indicating hierarchy. |
| `place=*` | Settlement markers and named places. |
| `leisure=*` | Recreational features. |
| Public-transport route relations | Bus, tram, train route relations linking ordered way and stop members. |

---

## Geographic regions and their distinctive properties

| Region | Distinctive property |
|---|---|
| Vienna, Austria | MGI / Austria Lambert (EPSG:31287); German names with diacritics. |
| London, United Kingdom | OSGB36 / British National Grid (EPSG:27700); dense Western OSM coverage. |
| Paris, France | RGF93 / Lambert-93 (EPSG:2154); French diacritics. |
| Tokyo, Japan | JGD2011 plane CRSes (EPSG:6677 family); CJK kanji and hiragana attribute values. |
| Bangkok, Thailand | Indian 1975 / UTM 47N (EPSG:24047); Thai script in attribute values. |
| Cairo, Egypt | Egypt Red Belt (EPSG:22992); Arabic right-to-left script. |
| New York, United States | NAD83 / NY State Plane (EPSG:6539 family); the US State Plane system spans dozens of zones. |
| Cape Town, South Africa | Hartebeesthoek94 / UTM 34S (EPSG:32734); southern-hemisphere UTM with a false northing offset originating at the equator. |
| Lagos, Nigeria | Minna / Nigeria West Belt (EPSG:26331); sparser OSM and Overture coverage than Western capitals. |
| Svalbard, Norway | Polar stereographic CRSes (EPSG:32661, EPSG:3995); high northern latitudes. |
| Fiji | Fiji 1986 / Fiji Map Grid (EPSG:3460); spans the ±180° meridian. |
| Antarctica | WGS 84 / Antarctic Polar Stereographic (EPSG:3031); extreme southern latitudes. |

---

## Data scale tiers

| Scale | Description |
|---|---|
| Small | ~10² features; fits trivially in memory. |
| Medium | ~10⁴–10⁵ features; fits in memory but naive O(n²) operations slow noticeably without a spatial index. |
| Large | 10⁶+ features; benefits from filtering or partition pushdown at fetch time rather than loading the full dataset. |

---

## Tolerance philosophy

The benchmark uses **drift-tolerant grading** so that L3 reference outputs can be regenerated against current live data without forcing systems-under-test to match bit-for-bit. Set tolerances using these heuristics during authoring; empirical refinement comes later from baseline-run measurements.

| Default | Use for |
|---|---|
| Count tolerance: ±5% | Feature counts on filtered subsets. |
| Area tolerance: ±5% | Total areas on dissolved or aggregated polygons. |
| Jaccard ≥ 0.9 | Set-membership questions (which features are in / out). |
| Ranking-style answers preferred | Top-N rankings instead of absolute thresholds where the task admits it. |
| No single-feature pivots | The grader must not flip score on the inclusion or exclusion of one feature, except for tasks whose explicit point is "is X present in the data?". |
| CRS-reprojection: principled bound | For tasks where the question is projection accuracy, set tolerances from first principles (sub-metre, sub-degree) — not from heuristics. |

Document the tolerance rationale in `metadata.yaml` per task.

---

## Anti-tautology requirements

A task author writes both the reference solution and the grader. The grader trivially gives 1.0 to its own reference. The "broken solution scores < 0.5" check is the only safeguard against grader-reference collusion — and the author also writes the broken solution. Two requirements protect against this:

1. **Failure-mode taxonomy in the README.** Enumerate at least five realistic ways a weak agent could fail this task. For each, name how the grader detects (or principled-reasons about) the failure. Examples for a buffer task: wrong CRS → buffer in degrees not metres → grader catches via area sanity check; wrong buffer radius → grader catches via area-tolerance subcheck; output in wrong format → grader catches via gate 1; missing attributes → grader catches via attribute-presence subcheck; off-by-one filter predicate → grader catches via feature-count tolerance.
2. **At least three broken solutions** under `tests/broken_*/outputs/`, each scoring in a *different* declared range. Designs that are wrong in different ways must be distinguishable by the grader. Concretely: one broken solution that produces output in the wrong format (gate-1 fail, score 0); one that produces structurally correct output with wrong attributes (some subchecks fail, partial score); one that produces structurally correct output with wrong geometry (different subchecks fail, different partial score). Score ranges live in `metadata.yaml` under `broken_solutions:`.

If a failure mode in the taxonomy isn't covered by a broken solution and can only be argued for in prose, mark it `not-handled` in the `Failure-mode coverage` section of `IMPLEMENTATION_NOTES.md` so it's visible to a later auditor.

---

## Determinism

For bundled-data tasks (L1 / L2): the reference solution must be deterministic. Sort outputs by stable feature ID before serialisation, fix random seeds for any stochastic operations, avoid relying on dict iteration order. Two consecutive runs of `reference/generate.py` produce byte-identical output files.

For live-data tasks (L3): two consecutive runs **may** produce slightly different outputs because Overture / Overpass can refresh between calls. When you observe a diff between the two reference runs you must reason about its origin:

- If the diff matches the kinds of differences you would expect from realistic upstream drift (a few features added or removed, attribute values shifted on a small subset), accept it and confirm your **grader's tolerance window absorbs the same magnitude of drift** when applied to systems under test.
- If the diff looks like it could come from non-determinism in your script (ordering changes, sampling differences with no fixed seed, dict iteration shuffling), fix the script.

The `Verification results` section of your `IMPLEMENTATION_NOTES.md` records which case applied.

---

## Per-task folder layout

```
tasks/<slug>/
├── task.json               # request body sent to systems under test
├── reference/
│   ├── generate.py         # produces reference outputs, deterministic
│   └── outputs/
│       └── <name>          # one file per declared expected_output, naming matches task.json
├── grade.py                # task-specific grader; returns ScoreReport
├── metadata.yaml           # category, difficulty, tolerances, broken-solution score ranges
├── README.md               # design rationale + failure-mode taxonomy + expected weak-agent failure mode
├── data/                   # bundled inputs (committed if hand-crafted; gitignored if generated)
├── tests/
│   ├── broken_<class_a>/outputs/<name>
│   ├── broken_<class_b>/outputs/<name>
│   └── broken_<class_c>/outputs/<name>
└── IMPLEMENTATION_NOTES.md  # author's notes for the orchestrator
```

The `<slug>` matches the task_id given to you (e.g. `dd-l1-vienna-gpkg-manifest`). All outputs and broken solutions use `outputs/<name>` so multi-output tasks work cleanly.

**How to run code.** Authoring runs Python on the host via `uv` against `eval/pyproject.toml`. From `eval/`: `uv run python tasks/<slug>/reference/generate.py`, `uv run python tasks/<slug>/grade.py …`, `uv run pytest`. See `authoring/task-design-prompt.md > How to run code` for the canonical commands.

---

## Acceptance check (run before declaring `completed`)

1. `reference/generate.py` runs end-to-end with no errors via `uv run python …` from `eval/`.
2. Re-running `reference/generate.py` produces outputs that are either bit-identical (L1 / L2) or differ only in ways consistent with upstream data drift (L3).
3. `grade.py` returns `ScoreReport.score >= 0.95` when applied to its own `reference/outputs/`.
4. Every broken solution returns a score in its declared range from `metadata.yaml`. The score must not be in the same range as the reference.
5. The README's failure-mode taxonomy lists at least five failure modes, each mapped to a broken-solution test or to a principled grader subcheck.
6. `pytest eval/tests/` (the project-level library tests) passes — your task did not break shared `eval/geo_grading` primitives.
7. `metadata.yaml` declares: category, difficulty, tolerances, broken-solution score ranges, drift_sensitivity (low / med / high), author, date.

If any of these fail and you cannot fix them, set status to `completed-with-caveats` (severity matching the failure) or `unsolvable` and record the diagnosis in `IMPLEMENTATION_NOTES.md`.

---

## Library extension policy

You may freely add or modify functions in `eval/geo_grading/`. Library tests (`eval/tests/test_*.py`) run after every task to catch regressions. If your task fundamentally requires a new primitive (e.g., area-weighted set similarity, network-distance comparison), add it to `eval/geo_grading/comparisons.py` with a unit test in `eval/tests/test_comparisons.py`. Document the addition in the `Library extensions` section of your `IMPLEMENTATION_NOTES.md`.

If you discover that an existing primitive has a bug, **do not silently fix it** — earlier tasks committed reference outputs against the current behaviour. Flag the bug in `Open issues` (severity high) and use a workaround in your own grader. The orchestrator will surface this for human review.

---

## Task image prompt (`image-prompt.md`)

Every task directory must contain an `image-prompt.md` file with a single image-generation prompt (no frontmatter, no markdown heading — just the prompt text). These prompts feed an image model to produce thumbnail cards for the benchmark UI.

### Style guide

All 36 prompts must follow the same visual formula:

- **Background:** Soft watercolor wash depicting the task's geographic region — landmarks, coastlines, river bends, urban fabric. Use muted, desaturated tones appropriate to the region (e.g. ink-wash grey for Tokyo, warm amber for Cairo, icy blue for Svalbard).
- **Foreground:** A technical diagram or schematic illustrating the task's core GIS operation — coordinate grids, polygon overlays, buffer rings, before/after transformations, filter funnels, format-conversion arrows, etc. The diagram should be clean and minimal, drawn with thin technical lines.
- **Composition:** The geographic and technical elements should be visually intertwined, not side-by-side panels. The watercolor background bleeds through the diagram.
- **Palette:** Muted throughout. Use at most 3–4 accent colours (e.g. coral red, teal, dusty gold, slate blue). No saturated primaries.
- **Style:** Flat, minimal — no 3D, no photorealism, no gradients except the watercolor wash.
- **Text:** Minimal. Only coordinate labels, CRS names, or short map labels where they reinforce the technical content. No titles, no captions, no paragraphs.
- **Aspect ratio:** 3:2, clean white margins.

### Writing the prompt

Structure the prompt as a single paragraph (or two short paragraphs) that covers:

1. **What the foreground shows** — name the specific GIS operation and how it's visualised (e.g. "building footprint polygons with centroid dots connected by dashed lines").
2. **What the background shows** — name the geographic region and its visual character (e.g. "soft watercolor background of Cape Town's coastline with Table Mountain").
3. **Palette and style** — restate the muted-palette, flat-style, no-3D constraints and list the specific accent colours you want.
4. **Aspect ratio and margins** — always end with "Aspect ratio 3:2, clean white margins."

### Example

For `crs-l2-fiji-antimeridian`:

> Technical diagram overlaid on a soft watercolor background of the Fiji archipelago and South Pacific ocean in muted teals and warm sand tones. The foreground shows GPS boat transects as dashed lines crossing the 180° meridian, with one line splitting cleanly at the antimeridian into two segments with small arrow endpoints. A faint graticule grid with longitude labels (179°E, 180°, 179°W) anchors the composition. Minimal, flat style — no 3D, no photorealism. Muted palette: slate blue lines, coral red for the split point, warm grey labels. Aspect ratio 3:2, clean white margins.

### Tags (`task.json`)

Each `task.json` also carries a `"tags"` dictionary (placed right after `"task_id"`) for filtering and faceted search. The schema has 9 keys:

| Key | Type | Description |
|---|---|---|
| `region` | string[] | Geographic anchor(s): `vienna`, `london`, `paris`, `tokyo`, `bangkok`, `cairo`, `nyc`, `capetown`, `lagos`, `svalbard`, `fiji`, `antarctica` |
| `data_source` | string[] | Where data comes from: `bundled`, `overture`, `overpass`, `overpass_historical`, `geofabrik` |
| `formats` | string[] | All formats touched (in+out): `geojson`, `geoparquet`, `parquet`, `gpkg`, `csv`, `csv_wkt`, `flatgeobuf`, `kml`, `shapefile`, `json`, `osm_pbf` |
| `crs` | string[] | All EPSG codes involved: `"EPSG:4326"`, `"EPSG:3857"`, etc. |
| `geometry_type` | string[] | Geometry types encountered: `point`, `linestring`, `polygon`, `multipoint`, `multilinestring`, `multipolygon` |
| `operations` | string[] | GIS operations from Axis 1+2: `buffer_planar`, `buffer_geodesic`, `intersection`, `union`, `difference`, `symmetric_difference`, `clip`, `simplify`, `dissolve`, `convex_hull`, `centroid`, `point_on_surface`, `bbox`, `explode`, `collect`, `join_within`, `join_intersects`, `join_contains`, `join_touches`, `join_crosses`, `join_overlaps`, `nearest_neighbour`, `knn`, `distance_matrix`, `within_distance`, `pip_count`, `spatial_aggregation`, `hotspot_ranking`, `shortest_path`, `network_distance_matrix`, `isochrone`, `closest_facility`, `reprojection`, `format_conversion`, `area_calculation`, `length_calculation`, `attribute_filter`, `schema_introspection` |
| `themes` | string[] | Overture themes (`places.place`, `buildings.building`, …) and OSM tag families (`highway`, `building`, `amenity`, `shop`, `landuse`, `natural`, `waterway`, `railway`, `boundary_administrative`, `place`, `leisure`, `public_transport_route`) |
| `quality_issues` | string[] | Data quality issues and gotchas: `invalid_geometry`, `wrong_ring_orientation`, `null_geometry`, `zero_area_polygon`, `mixed_geometry_types`, `sliver_polygons`, `duplicate_geometries`, `unsnapped_vertices`, `mixed_crs`, `encoding_issues`, `null_attributes`, `type_coercion`, `inconsistent_values`, `column_truncation`, `multi_single_coercion`, `antimeridian`, `polar`, `non_latin_script`, `geodesic`, `html_content` |
| `scale` | string | Data scale: `small`, `medium`, `large` |

All array fields use `[]` even for single values. Empty arrays `[]` are preferred over omitting the key. The `scale` field is the only plain string.
