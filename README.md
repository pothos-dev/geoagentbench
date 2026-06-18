# GeoAgentBench

A black-box evaluation suite for **geospatial agent systems**. Candidate
systems are treated as opaque services accessed over HTTP; the benchmark
grades the output artifacts they produce, not the process used to produce
them.

The target persona is the **GIS analyst assistant**: an agent that fetches,
transforms, analyzes, and converts vector geospatial data on behalf of a
human operator (urban planner, ecologist, public-sector spatial analyst).

Live results browser: https://geoagentbench.pothos.dev

> Bachelor thesis artifact. The contribution is the benchmark suite itself;
> the reference adapters exist to demonstrate it has discriminating power.
> See [`benchmark-design.md`](benchmark-design.md) for the full design.

## Task suite

36 tasks across **6 operation categories** and **3 difficulty levels**
(18 × L1, 12 × L2, 6 × L3):

| Prefix | Category |
|--------|----------|
| `dd`   | Data discovery & fetching (Overture, OSM/Overpass, Geofabrik) |
| `fio`  | Format I/O & conversion (GeoJSON, GeoParquet, Shapefile, GPKG) |
| `crs`  | CRS reprojection with correct datum handling |
| `geo`  | Geometric operations (buffer, intersection, union, dissolve, ...) |
| `spa`  | Spatial analysis (joins, nearest-neighbor, accessibility, ranking) |
| `dc`   | Data cleaning (invalid-geometry repair, dedup, snapping, encoding) |

Each `tasks/<id>/` contains:

```
metadata.yaml            task tags, level, category
task.json                the prompt and deliverable spec given to the agent
README.md                human-readable task description
inputs/                  bundled input data (+ _prepare.py that produced it)
reference/solution/      canonical outputs + generate.py
reference/failures/      _make_brokens.py (broken fixtures are NOT committed)
grade.py                 deterministic grader (tolerant comparison vs reference)
```

## Reference data

Bundled `inputs/` and `reference/solution/outputs/` are committed. Most are
derived from a **pinned Overture release**, and Overture purges old releases,
so the data is bundled rather than re-fetched on checkout. The graders pin
feature counts and tolerances calibrated against this data.

The deliberately-broken fixtures under `reference/failures/` are **not
committed** (they are never read at grade time). Regenerate any task's set:

```bash
cd eval && uv run python ../tasks/<task-id>/reference/failures/_make_brokens.py
```

## Running evals

The harness exposes candidate agents as an HTTP service; the eval CLI drives
tasks against it. Only OpenRouter is supported as an adapter.

```bash
# 1. Start the harness (requires OPENROUTER_API_KEY)
cd harness
cp .env.example .env   # then fill in OPENROUTER_API_KEY
export $(grep -v '^#' .env | xargs)
uv run python -m dispatcher        # serves http://localhost:8080

# 2. Run a suite against an adapter (see eval/adapters.yaml)
cd ../eval
uv run python -m eval.cli run <adapter-name>

# 3. Browse tasks and results
uv run python -m eval.cli ui       # http://localhost:8765
```

See [`harness/README.md`](harness/README.md) and [`eval/README.md`](eval/README.md)
for details.

## Layout

```
tasks/        the 36 benchmark tasks (definitions, data, graders)
harness/      HTTP harness wrapping an agent + tools in a sandbox
eval/         eval runner, graders, and results-browser UI
authoring/    tooling and prompts used to author and audit tasks
```
