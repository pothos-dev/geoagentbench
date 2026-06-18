# Geospatial Agent Benchmark — Design

Bachelor thesis artifact. The thesis contribution is the **benchmark suite itself**; the two reference adapters exist to demonstrate the benchmark has discriminating power.

## 1. Scope and framing

### 1.1 What this benchmark is

A black-box evaluation suite for **geospatial agent systems**. Candidate systems are treated as opaque services accessed over HTTP; the benchmark grades the output artifacts they produce, not the process they used to produce them.

The benchmark targets the **GIS analyst assistant** persona: an agent that fetches, transforms, analyzes, and converts vector geospatial data on behalf of a human operator. Typical user: urban planner, ecologist, public-sector spatial analyst.

### 1.2 What this benchmark explicitly does not measure

- Raster / earth-observation workflows (satellite imagery, NDVI, time series).
- Cartography and map design (ungradeable without subjective review).
- Real-time / streaming geospatial workflows.
- 3D / point-cloud workflows.
- Multi-agent coordination, long-horizon memory beyond a single task.
- The underlying LLM in isolation. The unit of test is the full agent system (model + harness + prompt + tools).

These are documented in `docs/limitations.md` as future-work items.

### 1.3 Test variables

The benchmark holds the **task** constant and varies the **agent system under test**. The thesis baseline study additionally varies the system prompt (basic vs GIS-detailed) as a third axis to demonstrate that the benchmark is sensitive to prompt-quality differences, not only to whole-system swaps. System prompts must remain task-agnostic — no per-task tuning is permitted.

## 2. Domain coverage

### 2.1 Operation categories (6)

1. **Data discovery & fetching** — locating and retrieving from Overture, OSM/Overpass, Geofabrik PBFs, including historical Overture releases. Probes the agent's domain knowledge of where canonical vector data lives.
2. **Format I/O & conversion** — reading and writing GeoJSON, GeoParquet, Shapefile, GPKG with attribute preservation. Probes format literacy and gotchas (Shapefile 10-char column truncation, etc.).
3. **CRS reprojection** — projecting between coordinate reference systems with correct datum handling. Projection-sensitive grader tolerances apply here.
4. **Geometric operations** — buffer, intersection, union, difference, simplify, dissolve. Single-operation or chained.
5. **Spatial analysis** — spatial joins, nearest-neighbor, distance and accessibility computation, point-in-polygon counts, hot-spot ranking, attribute-based aggregation.
6. **Data cleaning** — invalid-geometry repair, deduplication, snapping, MultiPolygon handling, null handling, encoding fixes.

### 2.2 Difficulty levels (3)

- **L1 — Single-op, bundled data.** One operation on data shipped with the task. Probes basic competence. Expected: strong baseline ≥ 90%, weak baseline ~50%.
- **L2 — Multi-op pipeline, bundled data.** 2–4 chained operations. Probes planning and composition. Expected: strong ~70%, weak ~20%.
- **L3 — Full real-world workflow.** Discover → fetch → transform → analyze → format-convert → output. Probes end-to-end capability and may include intentional data-quality issues. Expected: strong ~50%, weak near-zero.

The expected-score gradient is itself a benchmark-validity check: if L3 is not harder than L1, the difficulty axis does not work.

### 2.3 Task count and distribution

**Target: 36 tasks**, distributed as 6 categories × (3 L1 + 2 L2 + 1 L3) = 6 × 6. The 3/2/1 difficulty split puts more mass on cheaper-to-author L1 tasks (needed for stable per-cell estimates) and fewer on expensive L3 tasks. If the thesis schedule tightens, the fallback target is 24 tasks (4 per category).

L1 tasks are always bundled-data — they isolate operation skill from discovery skill. L2/L3 tasks may mix bundled and discovery as appropriate.

I/O format coverage is an orthogonal axis, not a category. Task authoring distributes input/output formats across tasks so every category touches each of {GeoJSON, GeoParquet, Shapefile, GPKG} at least once. The format-conversion category concentrates on I/O quirks; other categories sprinkle them in.

## 3. Data strategy

### 3.1 Live data with reference regeneration

The benchmark uses **live data** from Overture and OSM. Reference solutions are regenerated against current live data shortly before each benchmark run. Pinning a frozen mirror was rejected because (a) it spoils the realism of "the agent must know where to look", and (b) infrastructure cost exceeds bachelor-thesis appetite.

This is a deliberate trade-off. **The benchmark is not bit-reproducible across calendar time.** Two runs against different Overture releases may produce slightly different scores. This is documented as the L1 limitation.

### 3.2 Drift mitigation

Tasks are designed to be **drift-tolerant**:

- Counts and areas are graded with explicit tolerances (typically ±5%).
- Set-membership questions use Jaccard similarity rather than exact equality.
- Ranking-style questions ("which is largest?") are preferred where they fit.
- Answers must not pivot on a single feature being present or absent.
- Date-anchored questions ("as of the last full Overture release") are used where applicable.

Reference regeneration is human-inspected, not fully automated:

- A visual-diff tool produces a side-by-side map of old vs new reference output, with differences highlighted.
- A textual feature-level diff is generated when small enough to read.
- The grader function is applied to old-vs-new reference pairs as a drift metric — close to 1.0 means within tolerance.
- Borderline cases are resolved by human review.

No quarantine automation. Reference updates are committed by hand after review, with the commit message recording the Overture release ID and OSM extract date.

### 3.3 Data source assumption

The benchmark documents Overture and OSM (with Overpass and Geofabrik as access methods) as the canonical vector sources expected at authoring time. The HTTP contract does **not** specify allowed sources — agents are expected to know. If a substantively better vector source is published in the future, the benchmark will need updating.

## 4. HTTP contract

### 4.1 Endpoints

- `POST /tasks` — submit a task. Returns `202 Accepted` with `task_id` and initial `status: "pending"`.
- `GET /tasks/{id}` — poll for status, logs, outputs, metadata. Returns the current state, with logs accumulating over time. Outputs become available when `status` becomes `succeeded`.
- `GET /artifacts/{task_id}/{name}` — download a named output artifact.
- `DELETE /tasks/{id}` — cancel a running task (optional, polite).

### 4.2 Request schema

```json
{
  "task_id": "vienna-schools-near-roads-001",
  "instruction": "Find all schools within 500m of a road tagged highway=primary in Vienna's 1st district. Output as GeoJSON in EPSG:4326.",
  "inputs": [
    {"name": "districts", "url": "https://.../vienna_districts.geojson", "format": "geojson"}
  ],
  "expected_outputs": [
    {"name": "result", "format": "geojson", "crs": "EPSG:4326", "geometry_type": "Point"}
  ],
  "deadline_seconds": 600
}
```

Notes:

- `instruction` is natural language — parsing it is the agent's job.
- `expected_outputs` declares format/CRS/geometry-type so the harness can mechanically validate without ambiguity. Tasks must specify outputs unambiguously; multiple acceptable answers are forbidden by design.
- `inputs` is omitted for pure-discovery tasks.
- `data_sources_allowed` is intentionally **not** in the contract. Documented expectation lives in `docs/`.

### 4.3 Response schema

```json
{
  "task_id": "...",
  "status": "pending" | "running" | "succeeded" | "failed" | "timeout",
  "started_at": "...",
  "completed_at": "...",
  "outputs": [
    {"name": "result", "url": "https://agent-host/artifacts/.../result.geojson", "format": "geojson"}
  ],
  "logs": {
    "events": [
      {"timestamp": "...", "type": "thinking" | "tool_call" | "tool_result" | "text" | "system", "content": "..."}
    ]
  },
  "metadata": {
    "duration_s": 142,
    "estimated_cost_usd": 0.42,
    "tool_call_count": 17,
    "agent_version": "...",
    "model": "..."
  }
}
```

Notes:

- Output storage is the agent's responsibility — any URL the harness can `GET` is acceptable.
- Logs are normalized into a common event format. Each adapter is responsible for translating its underlying agent's transcript into these event types. Logs are **for analysis only**, not graded.
- Token counts are not tracked. Cost (estimated USD) and duration are.
- Intermediate or internal logs are optional from an information-hiding perspective; the contract provides a structured place for them when the agent chooses to expose them.

## 5. Grading model

### 5.1 Per-task graders

Each task ships its own `grade.py` that compares the agent's output artifacts against a committed reference, returning a structured `ScoreReport`. Graders use a shared `geo_grading` library of geo-comparison primitives:

- `iou_with_tolerance(a, b, eps)` — geometric intersection-over-union.
- `feature_set_equality_by_id(a, b, key)` — set-equality on feature IDs.
- `attribute_match(a, b, fields, tolerance)` — attribute-level comparison with type coercion.
- `topology_equal_within_epsilon(a, b, eps)` — topological equivalence via DE-9IM.
- `count_within_tolerance(a, b, pct)` — feature-count tolerance check.

The shared library is itself a thesis deliverable — it is well-tested and documented as the technical artifact of the methodology chapter.

### 5.2 Layered scoring

Each task's grader applies layered checks:

1. **Gate 1 — Format / schema validity** (binary). Output exists, is parseable, declares the correct format and CRS, has expected attributes. Failure means score = 0; the agent did not deliver a usable artifact.
2. **Gate 2 — Structural correctness** (binary). Feature count within tolerance, geometry types as declared, no invalid geometries.
3. **Score axes** (each 0–1 via subcheck checklist). Spatial correctness, attribute correctness, format-conversion fidelity, and any task-specific axes apply where relevant.

Partial credit is implemented as a **checklist of binary subchecks**: each axis decomposes into N independent yes/no checks, and the axis score is `passed / total`. Per-task score is `total_passed / total_subchecks` across all axes (gates count as their own checks). This makes failure analysis human-readable: each subcheck is a sentence in the report.

### 5.3 Tolerance setting

- **Default: empirical.** Run the strong baseline 3× per task, observe the spread, set tolerances tight enough that the weak baseline mostly fails but the strong baseline mostly passes.
- **Override: principled.** For projection-sensitive tasks (CRS reprojection category and tasks with sub-meter spatial precision requirements), tolerances are set from first principles based on the geometry, datum, and method involved.

Tolerance values live in `metadata.yaml` per task, with a comment explaining the rationale.

### 5.4 What is not graded

- Agent process or implementation choices.
- Source of data fetching (graded indirectly via output correctness — if the output is right, source choice is fine).
- Log content or reasoning quality.
- Code style.

## 6. Reporting

### 6.1 Output files

A benchmark run produces three files in `runs/<run-id>/`:

- **`results.json`** — machine-readable, complete per-task data: gate outcomes, all subcheck results, axis scores, duration, cost, status, agent metadata, run metadata. Source of truth.
- **`report.md`** — human-readable summary: per-agent table, per-category and per-difficulty breakdowns, list of failed tasks, headline numbers.
- **`leaderboard.csv`** — one row per (agent, run-date) for cross-run tracking.

Anything fancier (statistical analyses, plots, Pareto frontiers) is computed downstream from `results.json` by thesis analysis scripts. The harness keeps reporting simple.

### 6.2 Headline numbers

- **Per-task score**: `passed_subchecks / total_subchecks`.
- **Overall score**: `total_passed_subchecks / total_subchecks_across_all_tasks`. No weighted aggregation in the harness.
- **Cost (USD, estimated)**: total across tasks, with per-task and per-category breakdowns.
- **Duration (s)**: total wall clock, with per-task and per-category breakdowns. Note: includes processing time, not only inference time. This is intentional — wall-clock is the meaningful metric for a black-box system.

### 6.3 Run metadata

Every run captures:

- Run date and time.
- Overture release ID and OSM extract date used by reference regeneration.
- Agent system, version, underlying model, adapter version.
- Harness version (git commit).
- Task set version (git commit).
- Pricing table version used for cost estimates.

Without this metadata no result is reproducible. The pricing table (`pricing.yaml`) is pinned with a `valid_as_of` date; future readers can re-cost runs against newer rates.

## 7. Reference solution generation

### 7.1 Toolchain

Python with pinned dependencies via `uv`: GeoPandas, Shapely, PyOGRIO, DuckDB-spatial. PROJ for CRS work. The reference toolchain is deliberately the boring, well-known, widely-validated stack — exotic libraries weaken the defense.

### 7.2 Per-task structure

Each task directory contains:

```
tasks/<category>/<difficulty>-<slug>/
├── task.json                # request body sent to agents
├── reference/
│   ├── generate.py          # produces the reference output
│   └── expected_output.*    # last regenerated reference (committed)
├── grade.py                 # task-specific grader
├── metadata.yaml            # category, difficulty, drift_sensitivity, tags, author, date, tolerances
├── README.md                # design rationale
├── data/                    # bundled inputs (if any)
└── tests/
    └── broken_output.*      # deliberately wrong output for grader smoke test
```

### 7.3 Determinism and validation

- All library versions pinned via `uv`.
- Reference scripts sort outputs deterministically (by stable feature ID or geometry hash) before serialization.
- Random seeds fixed for any stochastic operations (k-means clustering, sampling, etc.).
- **Self-consistency tests**: every reference script ships with a unit test asserting basic properties (feature count > 0, all geometries valid, declared CRS, no nulls in key fields).
- **Grader self-test**: every grader returns ≈1.0 on its own reference output. Every grader returns < 0.5 on the deliberate `broken_output.*`. This is a mandatory acceptance check.
- **Task-script audit**: 5–10 representative tasks across categories receive manual review by the author (in QGIS where useful). The audit validates *the task script* — that the OSM tag matches the task description, that attribute filters select the right rows, that the CRS in the script matches `task.json`. It does **not** validate PROJ/DuckDB/GeoPandas; those dependencies are validated by their own ecosystems.

### 7.4 Drift detection on regeneration

When `uv run benchmark regenerate-refs` runs:

1. Each task's `generate.py` runs against current live data, producing a candidate new reference.
2. The task's grader is applied to `(new_reference, old_reference)` — close to 1.0 means within tolerance.
3. A drift report (`drift-report.html`) is produced per task: side-by-side map with differences highlighted, textual feature-level diff (where small), grader score.
4. Human reviews the report and accepts or escalates. Accepted updates are committed with a message recording the Overture release ID and OSM extract date.

No quarantine logic — borderline cases are resolved by human inspection.

## 8. Repository layout

```
geo-agent-bench/
├── README.md                 # what this is, how to run, link to thesis
├── pyproject.toml            # uv-managed, pinned deps
├── pricing.yaml              # API rate table for cost estimation
├── benchmark/                # the harness
│   ├── runner.py             # task scheduler, talks to adapters
│   ├── grading/              # geo_grading primitives + task-grader interface
│   ├── reference/            # regeneration + drift-report tooling
│   ├── reporting/            # results.json + report.md + leaderboard.csv generators
│   └── lint.py               # task linter (enforces template + acceptance checklist)
├── tasks/                    # 36 task directories
├── adapters/
│   ├── claude_code_opus/     # strong baseline: Claude Code wrapper, GIS-developer system prompt
│   └── openrouter_react/     # weak baseline: ReAct loop, model swappable via config
├── docs/
│   ├── design.md             # this file
│   ├── contract.md           # full HTTP API spec
│   ├── authoring.md          # how to write a task
│   ├── limitations.md        # drift, contamination, scope
│   └── thesis.pdf            # the thesis, included
└── runs/                     # gitignored; benchmark run outputs land here
```

The repo is the artifact. The thesis is one chapter of the artifact. Both adapters live in the repo as reference implementations and as the extension story for future researchers ("here is how to write your own adapter").

## 9. Adapters

### 9.1 Strong baseline: `claude_code_opus`

A FastAPI service implementing the HTTP contract. On `POST /tasks`:

1. Spawns Claude Code in an isolated workdir with the instruction wrapped by a **GIS-developer system prompt** (basic and detailed variants ship as separate launch configs).
2. Polls the workdir for output files matching `expected_outputs`.
3. Normalizes Claude Code's transcript into the contract event format.
4. Exposes outputs via `GET /artifacts/{task_id}/{name}`.

Underlying model: Claude Opus via the Claude Code subscription. Cost is estimated from API rates in `pricing.yaml` even when running under subscription, for fair cross-agent comparison.

### 9.2 Weak baseline: `openrouter_react`

A FastAPI service implementing the HTTP contract. The agent is a ReAct loop built on an agent SDK (likely smolagents or pydantic-ai), with model swappable via config (target candidates: Qwen, GLM, DeepSeek; commit to one at experiment time, swap is one-line).

Available tools:

- `run_python(code)` — executes in a sandboxed Docker container with GeoPandas, Shapely, DuckDB-spatial, PyOGRIO, and PROJ pre-installed.
- `run_bash(cmd)` — same sandbox; covers `ogr2ogr`, `gdalinfo`, file I/O.
- `read_file(path)` / `write_file(path, content)` — workdir I/O.
- HTTP fetching is done via Python `requests` inside `run_python`.

Same basic and GIS-detailed system prompt variants as the strong agent.

### 9.3 Experimental matrix

For the discriminating-power study:

- 2 agent systems × 2 system prompts × N runs = at least 4 distinct configurations.
- Each configuration runs all 36 tasks N times for variance estimation.
- N = 3 minimum; overnight runs allow larger N if budget permits. Strong agent runs under Claude Code subscription (no marginal cost); weak agent runs against OpenRouter at low per-token rates.

## 10. Authoring workflow and acceptance checklist

A task is accepted into the benchmark only when all of the following hold:

1. `task.json` validates against the request schema.
2. `generate.py` runs end-to-end against current Overture/OSM and produces `expected_output.*`.
3. `grade.py` returns ≈1.0 when applied to its own `expected_output.*`.
4. `grade.py` returns < 0.5 when applied to `tests/broken_output.*`.
5. `metadata.yaml` declares category, difficulty, drift_sensitivity (low/med/high), tolerances, author, date.
6. `README.md` answers: what GIS skill does this probe? Why this difficulty? What is the expected failure mode for a weak agent? What are the input/output formats?
7. The task is unambiguous — only one correct answer family exists.
8. (For the audited subset) the task script has been manually reviewed.

Enforced by `uv run benchmark lint-tasks`, which is a runnable test, not CI.

## 11. Thesis validity argument

The thesis must defend six validity claims. Calibrated effort per claim:

| Claim | Evidence |
|---|---|
| **Construct validity** | Map each category to documented GIS workflows (cite Bolstad's *GIS Fundamentals* or OSGeo curriculum). One paragraph per category. |
| **Discriminating power** | Run the 4-configuration × 36-task × N-run matrix; report mean and bootstrap CI per category; paired sign test (or McNemar's) between weak and strong overall and per category. |
| **Coverage** | Coverage matrix (category × difficulty × I/O format) showing every cell has ≥1 task; explicit list of what is *not* covered. |
| **Reproducibility** | Documented procedure (regenerate refs → run agents → grade → report); example reproduction in appendix; live-data drift acknowledged as L1 limitation. |
| **Reference correctness** | Self-consistency tests + grader self-tests on every task; manual audit on 5–10 stratified tasks documented in appendix. |
| **Robustness to gaming** | Open-source from day one; argue execution-based grading + live-data references make memorization a weak attack; cite the trend in open SE benchmarks. |

The two evidence items that take real effort:

- **The discriminating-power study**: overnight runs collect samples; analysis chapter computes statistics. Plan thesis figures around bootstrap CI plots and Pareto (correctness vs cost) plots.
- **The 5–10 manual audits**: ~1 day of work, documented in the appendix as the authorship sanity-check.

## 12. Contamination and openness

Position taken in the thesis:

- The benchmark is **open from day one** — tasks, references, graders public.
- Execution-based grading + live-data references make leaked task descriptions a weak attack vector: even with prior knowledge of the task, the agent must produce correctly-formatted, currently-correct artifacts in the right CRS against the day's data.
- The weak-vs-strong-baseline gap, if present, is itself evidence that gaming is not dominant.
- Held-out task sets and explicit contamination probes are documented as **future work**, not part of this thesis.

## 13. Maintenance posture

- The benchmark is shipped in working state at the thesis submission date.
- Periodic reference regeneration (suggested cadence: monthly, aligned with Overture's release schedule) is documented as a maintainer responsibility.
- The thesis does not commit the author to indefinite maintenance.
- A `MAINTAINING.md` describes the regeneration workflow for future contributors.

## 14. Limitations summary

L1. **Live-data drift.** Scores are not bit-reproducible across calendar time. Mitigated by drift-tolerant task design and reference regeneration.

L2. **Contamination.** Open benchmark; mitigation relies on execution-based grading. Future work: held-out tasks.

L3. **Scope.** Vector-only, GIS-analyst persona. No raster, cartography, real-time, 3D, or multi-agent. Each is justified and explicitly out of scope.

L4. **Reference correctness.** Validated by self-consistency tests, grader self-tests, and a manual audit on a stratified subset. Not exhaustive.

L5. **Cost estimation.** Based on pinned API rates with a `valid_as_of` date. Wall-clock duration includes non-inference processing time as a deliberate black-box metric.

## 15. Decision log

Decisions taken during design grilling, summarized:

| # | Decision | Choice |
|---|---|---|
| 1 | Test scope | Black-box agent system, not isolated harness or model |
| 2 | Thesis contribution | The benchmark itself; 2 baselines validate discriminating power |
| 3 | Persona | Vector-only GIS analyst assistant |
| 4 | Data | Live data + reference regeneration; drift acknowledged |
| 5 | Contract | HTTP polling, downloadable output URLs, normalized event-stream logs |
| 6 | Grading | Per-task Python graders, layered gates + binary-subcheck checklists |
| 7 | Taxonomy | 6 categories × 3 difficulties = target 36 tasks |
| 8 | Reference validation | Visual diff + grader-as-drift-detector + 5–10 manual script audits |
| 9 | Reporting | High-info `results.json`, simple per-task and overall scores, cost + duration |
| 10 | Validity | Construct cite, discriminating-power study, coverage matrix, reproducibility doc, reference audit, gaming argument |
| 11 | Repo | Single repo, adapters in-repo, no CI |
| 12 | Adapters | Claude-Code-Opus and OpenRouter-ReAct, swappable model, two prompt variants |
| 13 | Openness | Open from day one, no held-out tasks |
| 14 | Maintenance | Working state at submission; monthly regen documented but not committed |
