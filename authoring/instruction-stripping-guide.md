# Instruction stripping guide

This guide defines what information belongs in a `task.json` instruction string and what must be stripped. The benchmark tests whether an agent **knows how to do GIS work**, not whether it can follow a recipe. Every piece of deducible information left in the instruction is a piece of GIS competence we fail to measure.

The principle: **specify the goal and the output contract, not the analysis strategy.**

---

## The three buckets

Every sentence in an instruction falls into one of three buckets:

### 1. KEEP — non-deducible problem definition

Information the agent cannot derive from domain knowledge alone. This is the "what" of the task.

- **The goal / question being asked.** "Need every building footprint exceeding 1000 m2 across greater Lagos." The agent must know what it's looking for.
- **Geographic scope.** Bounding box coordinates, region name, administrative unit name. "Bounding box: xmin 3.1, ymin 6.35, xmax 3.7, ymax 6.75."
- **Thresholds and parameters that define the problem.** "exceeding 1000 m2", "within 400 m", "top 10%", "below 100 m2 are slivers". These are design choices the persona made, not derivable facts.
- **Output schema.** Column names, file names, formats, CRS, geometry types. This is the contract the agent must fulfil.
- **Data source identity (L3 only).** "from Overture", "from OpenStreetMap via Overpass". The agent needs to know where to look. But not which specific theme, collection, or API endpoint — that's domain knowledge.
- **Domain-specific business rules.** "normalise zoning_class to exactly these four canonical values: Residential / Commercial / Industrial / Agricultural". The agent can't guess these.
- **Persona voice and context.** The motivating story that makes the instruction feel real. "Updating the flood-risk model before rainy season." Keep it — it's not procedural.

### 2. STRIP — deducible analysis strategy

Information a competent GIS analyst would know or figure out. This is the "how" of the task.

- **Which CRS to use for intermediate computation.** "Compute areas in EPSG:26331" — a GIS agent should know to pick an appropriate equal-area or local projected CRS for the region. Exception: when the output CRS is specified, that stays (it's part of the output contract).
- **Which algorithm or technique to use.** "spatial-join the filtered buildings", "use partition pushdown", "geodesic buffers" — the agent should figure out the right approach.
- **Which specific data collection, theme, or table to query.** "Grab Lagos LGA boundaries from Overture administrative boundaries" — the agent should know where administrative boundaries live. (For L3, naming the top-level source "Overture" or "OSM" is fine; naming the specific theme `divisions.division_area` is not.)
- **Step-by-step procedure.** "First reproject, then filter, then join, then aggregate" — the agent should plan its own pipeline.
- **Implementation hints.** "don't download the whole thing", "via partition pushdown on the S3 bucket" — these are performance tips, not requirements.
- **Named GIS operations when the operation is implied by the goal.** "dissolve by class" when the instruction already says "one row per class" — the agent should know that collapsing rows by a grouping key requires a dissolve/aggregate.
- **Intermediate representations.** "project to EPSG:3031, then clip to landmass" — if the output is in EPSG:3031 and clipped to land, the agent should figure out the pipeline.

### 3. EDGE CASES — judgment required

Some information sits on the boundary. Apply these tiebreakers:

- **Named statistical measures stay.** "area-weighted mean density", "median height" — these define WHAT to compute, not how. The agent can't guess the persona wants a median vs a mean.
- **Output CRS always stays** — it's part of the output contract, not an analysis choice.
- **Named projections stay when they ARE the answer.** In a CRS-reprojection task where the whole point is "reproject to Lambert-93", the target CRS is the goal, not the method. Strip intermediate CRSes used only for computation.
- **Accuracy requirements stay, technique names don't.** "buffers must be accurate at polar latitudes" stays; "geodesic buffers" doesn't. "Honest 400 m buffer measured in metres" stays; "in a projected CRS" doesn't.
- **Filter predicates stay when arbitrary.** "highway=primary" is a domain choice; "buildings with height > 0" may be deducible from "buildings with a height attribute".
- **Canonical value lists stay.** If the persona defines exactly four zoning classes or three status labels, that's a business rule.

---

## Decision flowchart

For each sentence or clause in the instruction, ask:

```
1. Does this define WHAT the output must contain?
   → YES: keep it (output contract)

2. Does this define WHERE to look (L3 source identity, region, bbox)?
   → YES: keep the source name and geographic scope
   → But strip specific theme/collection/table names

3. Does this define a threshold, parameter, or business rule
   the agent couldn't derive from the output schema alone?
   → YES: keep it

4. Could a senior GIS analyst figure this out from the goal
   and output schema?
   → YES: strip it — this is what we're testing

5. Does this name a technique, algorithm, CRS, or data path
   that serves only as an implementation hint?
   → YES: strip it
```

---

## Difficulty-specific rules

### L1 — single operation, bundled data

Stripping is minimal. L1 instructions are already short and the operation is usually explicit (the task IS "reproject to X" or "compute centroids"). The main targets:

- Strip intermediate CRS hints when the output CRS is already specified.
- Strip format-handling instructions that a competent agent should know (e.g., "parse WKT from the geometry column" when the input is declared as `csv_wkt`).

### L2 — multi-step, bundled data

Stripping matters most here. L2 instructions often degenerate into step-by-step recipes. Targets:

- Strip operation sequencing ("first X, then Y, then Z").
- Strip intermediate CRS for computation when only the output CRS matters.
- Strip join strategy descriptions ("spatial-join A to B") when the output schema implies the join.
- Keep thresholds, aggregation functions (mean vs median vs sum), and filter predicates that represent persona choices.

### L3 — full workflow, live data

Stripping is most aggressive. The whole point of L3 is end-to-end capability. Targets:

- Strip specific Overture themes, OSM tag families, and collection paths. Name only the top-level source.
- Strip data access strategy ("partition pushdown", "Overpass query with bbox").
- Strip pipeline steps. State the goal and the output; let the agent plan.
- Keep: source identity ("from Overture", "from OSM"), geographic scope, output schema, accuracy requirements.

---

## Before / after examples

### Example 1: Lagos buildings (L3, data discovery)

**Before (procedural):**
> Need every building footprint exceeding 1000 m2 across greater Lagos — pull from Overture via partition pushdown on the S3 bucket, don't download the whole thing. Bounding box: xmin 3.1, ymin 6.35, xmax 3.7, ymax 6.75. Compute footprint areas in EPSG:26331 (Minna / Nigeria West Belt), keep only those above the threshold, export geometries in WGS84.
>
> Also need a per-LGA roll-up for the dashboard. Grab Lagos Local Government Area boundaries from Overture administrative boundaries, spatial-join the filtered buildings, and produce one summary row per LGA with the LGA name, building count, total footprint area, how many buildings carry a non-null Overture height, and the median height where available (null otherwise).

**After (goal-oriented):**
> Updating the flood-risk model before rainy season. Need every building footprint exceeding 1000 m2 across greater Lagos from Overture. Bounding box: xmin 3.1, ymin 6.35, xmax 3.7, ymax 6.75.
>
> Also need a per-LGA roll-up: for each Lagos Local Government Area, the building count, total footprint area, count of buildings with a non-null Overture height, and the median height where available (null otherwise).

**What was stripped and why:**
- "via partition pushdown on the S3 bucket, don't download the whole thing" — implementation hint.
- "Compute footprint areas in EPSG:26331 (Minna / Nigeria West Belt)" — intermediate CRS choice; agent should pick appropriate projection for Nigeria.
- "Grab Lagos Local Government Area boundaries from Overture administrative boundaries" — specific collection; agent should know where LGA boundaries live.
- "spatial-join the filtered buildings" — analysis strategy; the output schema implies the join.
- "export geometries in WGS84" — redundant with output schema.

**What stayed and why:**
- "exceeding 1000 m2" — threshold (persona's design choice).
- "Bounding box: xmin 3.1, ymin 6.35, xmax 3.7, ymax 6.75" — geographic scope.
- "from Overture" — L3 source identity.
- "median height where available (null otherwise)" — specific aggregation function.
- "per-LGA" — the grouping unit.
- Output schema paragraph (column names, formats, CRS) — output contract.

### Example 2: Tokyo bus-stop buffers (L1, geometric operation)

**Before:**
> We're refreshing the 400 m walkable-catchment layer for `tokyo_connectors`. I need an honest 400 m buffer around every connector, measured in metres in a projected CRS — no degree shortcuts.

**After:**
> Refreshing the 400 m walkable-catchment layer for `tokyo_connectors`. Need a 400 m buffer around every connector — honest metric distance, not degrees.

**What was stripped:** "in a projected CRS" — the agent should know that metric buffers require projection.

### Example 3: Bangkok land-use intersect (L2, geometric operations)

**Before:**
> `landcover` is a land-cover dataset for the Bangkok metro — some geometries may need repairing before processing. `study_area` defines the BMA boundary. Clip the cleaned land-cover to the study area, drop anything that falls fully outside, simplify at a 5 m tolerance so the file is small enough for the policy lead to preview in a browser, and keep the original land-cover `class` string plus a per-feature `area_m2` computed in EPSG:32647 metres squared.

**After:**
> Working on a flood-mitigation green-cover briefing. `landcover` has land-cover polygons for the Bangkok metro; `study_area` defines the BMA boundary. I need the land-cover clipped to the study area and simplified at 5 m tolerance, with the original `class` string and a per-feature `area_m2` in square metres.

**What was stripped:**
- "some geometries may need repairing before processing" — the agent should handle invalid geometry as standard practice.
- "drop anything that falls fully outside" — implied by "clipped to the study area".
- "computed in EPSG:32647" — intermediate CRS; agent should pick appropriate UTM zone.
- Step-by-step ordering (clean, clip, drop, simplify, compute).

### Example 4: Antarctic stations (L3, complex workflow)

**Before:**
> At these latitudes planar buffering is rubbish, so the buffers must be geodesic. Pull stations from Overture's current places.place theme — filter to Antarctica (below -60 latitude). Also grab base.land, base.water, and base.bathymetry for the continent.
>
> For each station draw a 200 km geodesic buffer, project to EPSG:3031, clip to the Antarctic landmass, then union overlapping spheres into coalitions

**After:**
> Each Antarctic research station has a notional 200 km operational sphere — buffers must be geographically accurate at polar latitudes. Pull stations from Overture south of -60 latitude, along with the Antarctic landmass and water features.
>
> Land-clipped station spheres grouped into coalitions where they overlap.

**What was stripped:**
- "planar buffering is rubbish, so the buffers must be geodesic" → replaced with "geographically accurate at polar latitudes" (accuracy requirement without naming the technique).
- "places.place theme", "base.land, base.water, base.bathymetry" — specific Overture themes.
- "project to EPSG:3031, clip to Antarctic landmass, then union" — pipeline steps.

---

## Applying this guide

When rewriting an instruction:

1. **Read the output schema first.** Many "procedural" sentences in the instruction just restate what the output schema already declares. If `expected_outputs` says GeoParquet in EPSG:4326, the instruction doesn't need to say "export as GeoParquet in WGS84".
2. **Identify every verb phrase.** "reproject to", "spatial-join", "clip to", "compute in", "filter by", "dissolve by" — each is a candidate for stripping.
3. **For each verb, ask: is this the goal or the method?** "Filter buildings above 1000 m2" is the goal. "Compute areas in EPSG:26331" is the method.
4. **Preserve the voice.** Stripping procedural content should not flatten the persona's tone. A terse engineer stays terse; a chatty analyst stays chatty. Remove the recipe, keep the personality.
5. **Re-read the stripped instruction without looking at the output schema.** Is the goal still unambiguous? If not, you stripped too much. Add back the minimum needed for clarity.
6. **Check the redundant output-schema sentence.** The task-design-prompt requires a closing sentence restating format and CRS. This stays — it's an intentional safety net, not procedural leakage.

---

## What this guide does NOT change

- **Output schema in `expected_outputs[]`.** Column names, formats, CRS, geometry types are always fully specified. This is the grading contract, not a hint.
- **The redundant output-schema sentence** at the end of the instruction. Intentional by design.
- **Persona voice and story context.** The motivating sentence ("Updating the flood-risk model before rainy season") stays.
- **Thresholds, tolerances, and business rules.** These are non-deducible design choices.
- **The `tags` dictionary in `task.json`.** Tags are for benchmark infrastructure, not for the agent.
