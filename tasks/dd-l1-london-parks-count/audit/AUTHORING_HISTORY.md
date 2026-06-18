# Implementation notes — dd-l1-london-parks-count

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 data-discovery task: a FlatGeobuf of inner-London parks in
EPSG:27700 → small JSON summary with `count`, `total_area_ha`, and
`bbox_wgs84` for parks ≥ 1 ha. Reference, grader, and three broken
solutions built and verified inside the project Docker container.

## Verification results
- Reference grader score: 1.00 (7 / 7 subchecks pass)
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    the CSV body (cannot parse as JSON object), no subcheck runs.
  - wrong_filter: 0.286 (expected range [0.20, 0.40]) — 2 / 7 pass:
    bbox_ymax_correct (the unfiltered set's ymax happens to coincide
    with the filtered set's because a single ≥ 1 ha park provides the
    overall northernmost extent) and bbox_in_wgs84_range (the agent
    did reproject correctly, just over the wrong subset).
  - wrong_units: 0.857 (expected range [0.80, 0.90]) — 6 / 7 pass;
    only `total_area_ha_correct` fails (m² vs ha — 10 000× off,
    well outside the 1 % tolerance).
- Second-run output match: bit-identical (verified with `diff -q` on
  `reference/outputs/parks_summary.json` before/after a second
  `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Agent forgot the ≥ 1 ha filter: broken_wrong_filter
- Agent forgot the m² → ha unit conversion: broken_wrong_units
- Wrong output format (CSV / missing required keys): broken_wrong_format
- Agent computed area in geographic degrees: principled —
  `count_correct` (returns 0) + `total_area_ha_correct`
- Agent forgot to reproject bbox to EPSG:4326: principled — four
  bbox componentwise subchecks + `bbox_in_wgs84_range`
- Agent swapped lon and lat in bbox: principled — four bbox
  componentwise subchecks
- Agent computed bbox over the unfiltered set: principled — bbox
  componentwise subchecks
- Wrong area threshold (e.g. ≥ 0.1 ha): principled — `count_correct`
  + `total_area_ha_correct`

## Open issues
- [severity: low] — The inventory row tags this task with
  `leisure=park` (OSM), but the bundled fixture is sliced from
  Overture's `base.land_use` filtered to `class='park'`. Per
  AUTHOR_CONTEXT.md and OVERTURE_REFERENCE.md, Overture is the
  default authoring source and Overpass is a fallback only when no
  clean Overture equivalent exists. Overture's `class='park'` value
  is the structural equivalent of OSM `leisure=park` for green-
  space inventory purposes, so the Overture path is preferred. The
  FlatGeobuf format and EPSG:27700 CRS are properties of the
  bundled file and independent of the upstream source.

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — the grader uses only `Gate`, `Subcheck`, and `ScoreReport`
from `geo_grading`. Bbox componentwise checks, scalar tolerance
checks, and JSON-shape comparisons are computed inline because they
are simple JSON-shape comparisons, not geometric primitives.)

## Runtime
~12 minutes (one Overture slice fetch ~30 s, the rest local Docker
runs).

---

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
The task was authored on 2026-05-08 as an L1 data-discovery probe:
read a bundled FlatGeobuf of inner-London parks in EPSG:27700, filter
to features ≥ 1 ha, and emit a small JSON summary with `count`,
`total_area_ha`, and a `bbox_wgs84` 4-list. The inventory row lists
"Attribute filter + feature count + bbox" as the primary operation,
with the upstream OSM tag family `leisure=park`; the implementation
chose Overture's structurally equivalent `base.land_use class='park'`
as the data slice (documented in metadata.yaml's notes). The task
probes FlatGeobuf reading, planar-area filtering in a projected CRS,
m²-to-hectare unit conversion, and bbox reprojection on a subset of
features — exactly the kind of three-line summary a real analyst
would compute before commissioning a downstream accessibility study.
Three broken solutions (`wrong_format`, `wrong_filter`, `wrong_units`)
cover the canonical failure modes, with the m²/ha unit slip flagged
as the expected weak-agent mode.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | bc9e7c8 | initial-authoring | Initial task (task.json, grade.py, metadata.yaml, README.md, data/, reference/, tests/, IMPLEMENTATION_NOTES.md) | Initial authoring (status: completed). |
| 2026-05-13 | 2848436 | prompt-change | Added `tags` block to task.json (region, data_source, formats, crs, geometry_type, operations, themes, quality_issues, scale) | Commit msg: structured tags derived from inventory axes, for filtering. |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Card image generation pipeline. |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp (nano-banana-2) | Card image asset. |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ → benchmark/tasks/ | Tasks promoted to top-level (path refactor). |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Card-image regeneration. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Card-image regeneration. |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "a FlatGeobuf of" from the instruction (format hint removed; kept the EPSG:4326 bbox spec) | Commit msg: "strip deducible information from DD task instructions" — input format inferable from bundled filename extension. |
| 2026-05-17 | 88530c5 | prompt-change | Stripped trailing "(lon/lat, [xmin, ymin, xmax, ymax] in EPSG:4326)" suffix from the output-keys sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" — output CRS deducible from "WGS84 map" framing + the `bbox_wgs84` key name. |
| 2026-05-26 | 29a9ae3 | docs-change | Reorganised directory layout: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, data/ → inputs/, reference/{generate.py,outputs} → reference/solution/, tests/ → reference/failures/, image* → assets/. Adjusted internal paths in grade.py and _prepare.py | Commit msg: clearer layout separating machine contract, audit history, inputs, reference + failures, eval-UI assets. Mechanical refactor; no semantic change. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change).
- The 2026-05-26 reorganisation commit is a `docs-change` per its message (renames + path-string updates in grade.py reference). It moves the reference output path from `reference/outputs/parks_summary.json` to `reference/solution/outputs/parks_summary.json` and updates `grade.py` accordingly. Since the reference output bytes are unchanged (verified by `diff` against current run outputs), it does not invalidate runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:18:01Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:19:18Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:18Z | 1.00 | done | current |

Stale runs (pre-cutoff, not used as evidence): 23 runs across claude-code-{haiku,sonnet,opus}-basic and openrouter-{minimax-m2, deepseek-v4-flash, hy3-preview, gemma4-26b}-basic. Of these, 16 scored 1.0; one (deepseek-v4-flash, 2026-05-15) scored 0.4286 (looser instruction had additional gifts — pre-cutoff); one (deepseek-v4-flash, 2026-05-17 pre-cutoff) scored 0.0 (missing output file — model-side failure); four were cancelled or failed pre-task with connection / API-key errors (harness / config issues, not task issues).

#### Verdict
**calibrated**

All three current runs scored 1.0, but the current evidence spans agents of materially different capability (Opus, DeepSeek V4 Flash, Gemma 4 26B A4B) and L1 tasks are expected to be solved by all of them. The instruction has been deliberately stripped (twice, in 2026-05-14 and 2026-05-17) of every deducible hint — input format, input CRS, output CRS explicit form, bbox component order — leaving only persona constraints (`≥ 1 ha`, "hectares", "WGS84 map") and the output schema (filename + three top-level keys). The fact that the m² → ha unit slip (`broken_wrong_units` scores 0.857) and the no-filter mode (`broken_wrong_filter` scores 0.286) are distinguishable on the rubric confirms the grader still discriminates between failure modes. There is no over-specification: removing further hints (e.g. the word "WGS84") would collapse the bbox-output CRS into an under-specified choice and break the grader's `bbox_in_wgs84_range` subcheck's interpretability.

The stale 0.4286 deepseek run is worth noting — the looser prompt at that time included the explicit EPSG:4326 hint, and the model still failed. Removing the hint would not have helped; this is a model-side failure mode in the stale window. Not actionable.

#### Specific findings
- L1 calibration is intact: gates separate format failures from numerical failures, the seven subchecks each have a principled detector for one canonical mistake, and the bbox is split into four componentwise checks so a lon/lat swap is partially credited.
- Tolerances in `metadata.yaml` are well-justified by `author-context.md`: `area_pct=0.01` is tight enough to catch the 10 000× ha/m² slip but loose enough for pyogrio/fiona/GDAL float drift; `bbox_eps_deg=1e-4` ≈ 11 m at 51.5°N — far below any legitimate rounding.
- No grader miscalibration suspected. No prompt-grader inconsistency. Instruction is appropriately stripped.
- Inventory row tags `leisure=park` (OSM); implementation uses Overture `base.land_use class='park'`. `metadata.yaml` documents the rationale (Overture is the structural equivalent and the documented default per author-context.md). Not a mismatch — `coverage.yaml` records both for completeness.

### 3. Changes applied this run

#### Unilateral edits
None. The task is calibrated as-is.

#### Proposed but not applied (see HUMAN-REVIEW items)
None.

#### Tests run
- grader on reference: 1.00 (7 / 7 subchecks pass; both gates pass).
- pytest (benchmark/eval): 35 / 35 pass.

---

## Evaluator review 2026-05-27  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`bc9e7c8`) as an L1 data-discovery probe: read a
bundled FlatGeobuf of inner-London parks in EPSG:27700, filter to
features ≥ 1 ha, and emit a small JSON summary with `count`,
`total_area_ha`, and a `bbox_wgs84` 4-list. The inventory row
(`dd-l1-london-parks-count`) lists "Attribute filter + feature count +
bbox" as the primary op, region London, source bundled-local, format
in FlatGeobuf / out JSON, CRS in EPSG:27700 → bbox out EPSG:4326,
geometry Polygon, scale small (~10² parks), upstream OSM tag family
`leisure=park`. The implementation slices Overture `base.land_use`
filtered to `class='park'` (the structural equivalent; documented in
`metadata.yaml` notes and the author block above). The task exercises
FlatGeobuf reading, planar-area filtering in a projected CRS, m²→ha
unit conversion, and bbox reprojection of a feature subset — the kind
of three-line summary a GLA analyst (persona: Priya Shah) would compute
before commissioning an accessibility study. Three broken solutions
(`wrong_format`, `wrong_filter`, `wrong_units`) cover the canonical
failure classes, with the m²/ha unit slip nominated as the expected
weak-agent mode.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | bc9e7c8 | initial-authoring | Initial task (task.json, grade.py, metadata.yaml, README.md, data/, reference/generate.py + outputs, tests/, IMPLEMENTATION_NOTES.md) | Initial authoring (status: completed). |
| 2026-05-08 | fbd20f2 | docs-change | Repo restructure: moved task path under benchmark/ subtree | Commit msg: "restructure: split repo into thesis/ benchmark/ references/" — path move only, no semantic change. |
| 2026-05-08 | 001e459 | docs-change | Split benchmark into authoring/ + eval/ subtrees (task path → benchmark/eval/tasks/) | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" — path move only. |
| 2026-05-13 | 284b843 | prompt-change | Added `tags` block to task.json (region, data_source, formats, crs, geometry_type, operations, themes, quality_issues, scale) | Commit msg: "eval tasks: add structured tags to all 36 task.json files" — faceted-search metadata derived from inventory axes; does not touch instruction / inputs / expected_outputs answer key. |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Card-image generation pipeline. |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ → benchmark/tasks/ | Tasks promoted to top-level (path refactor). |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp (nano-banana-2) | Card-image asset. |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Card-image regeneration. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Card-image regeneration. |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "a FlatGeobuf of" from the instruction (format hint removed; EPSG:4326 bbox suffix kept) | Commit msg: "strip deducible information from DD task instructions" — input format inferable from bundled filename extension. |
| 2026-05-17 | 88530c5 | prompt-change | Stripped trailing "(lon/lat, [xmin, ymin, xmax, ymax] in EPSG:4326)" suffix from the output-keys sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" — output CRS deducible from "WGS84 map" framing + the `bbox_wgs84` key name. |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, data/ → inputs/ (`_prepare_input.py` → `_prepare.py`), reference/{generate.py,outputs} → reference/solution/, tests/ → reference/failures/, image* → assets/; updated path strings in grade.py, generate.py, _make_brokens.py, _prepare.py, task.json input URL | Commit msg: "Reorganize task folder layout" — mechanical rename + path-string update. Reference output bytes unchanged (verified: the parquet/json files are git-renamed, not modified). |
| 2026-05-26 | 7450e4c | docs-change | Prior evaluator review (block above): wrote coverage.yaml + AUTHORING_HISTORY evaluator block + status.json; verdict calibrated, no unilateral edits | Commit msg: "Re-evaluate dd-l1-london-parks-count: calibrated, no edits". |

Note: the prior evaluator block cited the tags commit as `2848436` (a
transposed/incorrect short SHA); the actual commit is `284b843`
(2026-05-13T07:34Z), made while the task lived at
`benchmark/eval/tasks/`. The two early restructure commits (`fbd20f2`,
`001e459`) were omitted from the prior block; both are pure path moves.
No correction is needed to any task artefact — the discrepancies are
purely in the prior history narrative.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change).
- Most recent answer-key-affecting commits are the two `prompt-change`
  instruction strips (`b04e9f0`, `88530c5`); `88530c5` is the later.
  The `tags` addition (`284b843`) touches only the faceted-search
  metadata, not the instruction / inputs / expected_outputs, so it does
  not move the cutoff. The 2026-05-26 reorg (`29a9ae3`) is a
  `docs-change` (renames + path-string updates); reference output bytes
  are unchanged, so it does not invalidate runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:18:01Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:19:18Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:18Z | 1.00 | done | current |

Stale runs (pre-cutoff, considered but not used as evidence): 23 runs
across claude-code-{haiku,sonnet,opus}-basic and openrouter-{minimax-m2,
deepseek-v4-flash, hy3-preview, gemma4-26b}-basic. Of these, 16 done at
1.0; one deepseek-v4-flash (2026-05-15, looser pre-cutoff prompt) at
0.4286; one deepseek-v4-flash (2026-05-17 pre-cutoff) at 0.0
(model-side: missing output file); four cancelled/failed pre-task with
ConnectError / OPENROUTER_API_KEY-not-configured (harness/config, not
task issues).

#### Verdict
**calibrated**

All three current runs scored 1.0, but they span agents of materially
different capability (Opus, DeepSeek V4 Flash, Gemma 4 26B A4B) and an
L1 single-filter-plus-reductions task is expected to be solvable by all
of them — a uniform 1.0 here is the designed gradient, not
over-specification. I independently re-derived the cutoff, re-ran the
grader on the reference (1.0, 7/7 subchecks + both gates), re-ran all
three broken solutions (0.0 / 0.2857 / 0.8571 — exactly their declared
`metadata.yaml` ranges and three distinct buckets), and re-ran pytest
(35/35). I inspected all three current-run outputs: each emitted
`parks_summary.json` (JSON, matching `expected_outputs[].name`) with
`count=42`, `total_area_ha≈519.16`, and a `bbox_wgs84` in EPSG:4326
matching the reference within tolerance; all 9 checks pass in each.
The instruction has been deliberately stripped twice (2026-05-14,
2026-05-17) of every deducible hint — input format, input CRS, explicit
output-CRS form, bbox component order — leaving only persona constraints
(`≥ 1 ha`, "hectares", "WGS84 map") and the redundant output schema
(filename + three keys). Stripping further (e.g. the word "WGS84")
would under-specify the bbox CRS. No gifts remain to strip.

2c-CRS check: the output is a non-spatial JSON scalar summary; the
grader compares scalars and does no reprojection on either side, so the
one-sided-reprojection failure mode does not apply. The
`expected_outputs[].crs` (EPSG:4326), the README's stated `bbox_wgs84`
CRS, and the reference `bbox_wgs84` values (lon/lat) all agree. The
input geometry is 317 MultiPolygon features in EPSG:27700; 42 are
≥ 1 ha (independently verified). No README/reference/contract CRS
disagreement.

The stale 0.4286 deepseek run is a model-side failure under the looser
pre-cutoff prompt (which still carried the explicit EPSG:4326 hint) —
removing the hint would not have helped, so it is not evidence the task
is mis-calibrated. Not actionable per the model-side-failure guidance.

#### Specific findings
- L1 calibration intact: Gate 1 separates format/schema failures from
  numerical failures; the seven subchecks each have a principled
  detector for one canonical mistake; the bbox is split into four
  componentwise checks so a lon/lat swap is partially credited and is
  distinguishable from a wrong-CRS bbox (caught additionally by
  `bbox_in_wgs84_range`). No proposed change.
- Tolerances in `metadata.yaml` remain well-justified per
  `author-context.md`: `area_pct=0.01` catches the 10 000× ha/m² slip
  yet absorbs pyogrio/fiona/GDAL float drift at the ~0.01 ha level;
  `bbox_eps_deg=1e-4` ≈ 11 m at 51.5°N, far below any legitimate
  rounding. No proposed change.
- No grader miscalibration suspected; no prompt-grader inconsistency.
- Inventory tags `leisure=park` (OSM); implementation uses Overture
  `base.land_use class='park'`. Documented and intentional per the
  Overture-default authoring rule. `coverage.yaml` records both
  (`overture_themes: [base.land_use]`, `osm_tag_families: [leisure]`).
  Not a mismatch; no flag.
- `coverage.yaml` slugs all validate against
  `coverage-vocabulary.yaml`. `geometry_types: [polygon, multipolygon]`
  is slightly generous (the file stores only MultiPolygon) but
  defensible since the design contract's `expected_outputs[].geometry_type`
  is Polygon and the feature concept is a park footprint. Kept.

### 3. Changes applied this run

#### Unilateral edits
None. The task is calibrated as-is; this run independently re-verified
the prior evaluator's verdict and refreshed the three evaluator
artefacts.

#### Proposed but not applied (see HUMAN-REVIEW items)
None.

#### Tests run
- grader on reference: 1.00 (2 gates + 7 subchecks all pass).
- broken solutions: wrong_format 0.0, wrong_filter 0.2857, wrong_units 0.8571 (all in declared ranges).
- pytest (benchmark/eval): 35 / 35 pass.

---

## Evaluator review 2026-05-28  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`bc9e7c8`) as an L1 data-discovery probe: read a
bundled FlatGeobuf of inner-London parks in EPSG:27700, filter to
features ≥ 1 ha, and emit a small JSON summary with `count`,
`total_area_ha`, and a `bbox_wgs84` 4-list. The inventory row lists
"Attribute filter + feature count + bbox" as the primary op, region
London, source bundled-local, format in FlatGeobuf / out JSON, CRS in
EPSG:27700 → bbox out EPSG:4326, geometry Polygon, scale small
(~10² parks), upstream OSM tag family `leisure=park`. The
implementation slices Overture `base.land_use` filtered to
`class='park'` (the structural equivalent; documented in
`metadata.yaml` notes and the author block above). The task probes
FlatGeobuf reading, planar-area filtering in a projected CRS, m²→ha
unit conversion, and bbox reprojection on a feature subset — the
three-line summary a GLA analyst (persona: Priya Shah) would compute
before commissioning an accessibility study. Three broken solutions
(`wrong_format`, `wrong_filter`, `wrong_units`) cover the canonical
failure classes; the m²/ha unit slip is the expected weak-agent mode.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | bc9e7c8 | initial-authoring | Initial task (task.json, grade.py, metadata.yaml, README.md, data/, reference/generate.py + outputs, tests/, IMPLEMENTATION_NOTES.md) | Initial authoring (status: completed). |
| 2026-05-08 | fbd20f2 | docs-change | Repo restructure under benchmark/ subtree | Commit msg: "restructure: split repo into thesis/ benchmark/ references/" — path move only. |
| 2026-05-08 | 001e459 | docs-change | Split benchmark into authoring/ + eval/ subtrees | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" — path move only. |
| 2026-05-13 | 284b843 | prompt-change | Added `tags` block to task.json (faceted-search metadata) | Commit msg: "eval tasks: add structured tags to all 36 task.json files" — derived from inventory axes; does not touch instruction / inputs / expected_outputs. |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Card-image pipeline. |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ → benchmark/tasks/ | Path refactor. |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp (nano-banana-2) | Card-image asset. |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Card-image regeneration. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Card-image regeneration. |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "a FlatGeobuf of" from the instruction | Commit msg: "strip deducible information from DD task instructions" — input format inferable from filename. |
| 2026-05-17 | 88530c5 | prompt-change | Stripped trailing "(lon/lat, [xmin, ymin, xmax, ymax] in EPSG:4326)" suffix from the output-keys sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts". |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg (IMPLEMENTATION_NOTES → audit/, data/ → inputs/, reference subtree, tests/ → reference/failures/, image* → assets/); path-string updates in grade.py, generate.py, _make_brokens.py, _prepare.py, task.json | Commit msg: "Reorganize task folder layout" — mechanical rename, reference output bytes unchanged. |
| 2026-05-26 | 7450e4c | docs-change | Prior evaluator review (calibrated; coverage.yaml + AUTHORING_HISTORY + status.json) | Re-evaluate, no edits. |
| 2026-05-27 | fb8de63 | docs-change | Prior evaluator review (calibrated; refreshed artefacts) | Re-evaluate, no edits. |
| 2026-05-28 | 622342b | docs-change | Removed unused `prompt_version: 2026-05-08-a` line from `metadata.yaml` (single-line deletion) | Commit msg: "Add task content versioning; drop unused prompt_version" — repo-wide infra change. Field was orchestrator authoring-template tag, no runtime relevance; does not touch instruction / inputs / expected_outputs / grader / tolerances. |

Note on classification of `622342b`: the commit's repo-level purpose is
to introduce `task.json.version` content-fingerprint semantics and the
evaluator-prompt's Step 4 bump rule. Within this task directory the
only edit is the `metadata.yaml > prompt_version` deletion. Per the
prompt's bump rules, that line is **not** one of the bump-triggering
fields (`instruction`, `inputs[]`, `expected_outputs[]`, `grade.py`,
`metadata.yaml > tolerances`, or any file under `inputs/`); therefore
the commit does not require a version bump and is `docs-change`. The
task is implicitly version 1 until an evaluator pass applies a
meaningful unilateral edit.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change).
- Unchanged from the prior evaluator-review block. The only commits
  touching this task directory since 2026-05-27 are `fb8de63`
  (prior evaluator review — `docs-change`) and `622342b`
  (`prompt_version` field removal in `metadata.yaml` — `docs-change`
  per the bump rules). Neither moves the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:18:01Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:19:18Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:18Z | 1.00 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:53:57Z | 1.00 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:46:30Z | 1.00 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:02:12Z | 1.00 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:35:26Z | 1.00 | done | current |

Stale runs (pre-cutoff, considered but not used as evidence): 23 runs
across claude-code-{haiku,sonnet,opus}-basic and openrouter-{minimax-m2,
deepseek-v4-flash, hy3-preview, gemma4-26b}-basic. Notable pre-cutoff
scores: 0.4286 deepseek-v4-flash (2026-05-15, looser prompt) and 0.0
deepseek-v4-flash (2026-05-17 pre-cutoff, missing output — model-side).
Four cancelled/failed pre-task with config errors (harness/config, not
task issues).

#### Verdict
**calibrated**

All seven `current` runs scored 1.0 across three different agent
families (Claude Opus 4.6 and 4.7, DeepSeek V4 Flash, Gemma 4 26B
A4B). The latest sweep added four new `current` runs (Opus 4.7 ×2,
Gemma 4 26B ×2 since 2026-05-27) — all 1.0, all seven subchecks +
both gates pass, output files match `expected_outputs[]`
(`parks_summary.json`) with `count=42`, `total_area_ha≈519.16`, bbox
in EPSG:4326 lon/lat within 1e-4° of the reference. L1 single-filter
tasks are designed to be solvable by all agents of any capability —
the uniform 1.0 is the designed gradient. The two grader-side
discriminators (the broken `wrong_filter` at 0.286 and `wrong_units`
at 0.857) are independently confirmed each evaluator pass; they
remain three distinct buckets, so the rubric still discriminates
between failure modes.

2c-CRS check: the output is a non-spatial JSON scalar summary; the
grader compares scalars and does no reprojection on either side, so
the one-sided-reprojection failure mode does not apply. The
`expected_outputs[].crs` (EPSG:4326), the README's stated `bbox_wgs84`
CRS, and the reference `bbox_wgs84` values (lon/lat) all agree. The
input geometry is 317 MultiPolygon features in EPSG:27700; 42 are
≥ 1 ha (independently verified). No README/reference/contract CRS
disagreement.

The instruction has been deliberately stripped twice (2026-05-14,
2026-05-17) of every deducible hint — input format, input CRS,
explicit output-CRS form, bbox component order — leaving only persona
constraints (`≥ 1 ha`, "hectares", "WGS84 map") and the output schema
(filename + three keys). The phrase "WGS84 map" is the minimal CRS
constraint that still lets the grader's `bbox_in_wgs84_range`
subcheck remain interpretable; removing it would under-specify the
bbox CRS. No further deducible gifts remain.

#### Specific findings
- L1 calibration intact: Gate 1 separates format/schema failures from
  numerical failures; the seven subchecks each have a principled
  detector for one canonical mistake; the bbox is split into four
  componentwise checks so a lon/lat swap is partially credited and is
  distinguishable from a wrong-CRS bbox (caught additionally by
  `bbox_in_wgs84_range`).
- Tolerances in `metadata.yaml` remain well-justified per
  `author-context.md`: `area_pct=0.01` catches the 10 000× ha/m² slip
  yet absorbs pyogrio/fiona/GDAL float drift at the ~0.01 ha level;
  `bbox_eps_deg=1e-4` ≈ 11 m at 51.5°N, far below any legitimate
  rounding.
- No grader miscalibration suspected; no prompt-grader inconsistency.
- Inventory tags `leisure=park` (OSM); implementation uses Overture
  `base.land_use class='park'`. Documented and intentional per the
  Overture-default authoring rule. `coverage.yaml` records both
  (`overture_themes: [base.land_use]`, `osm_tag_families: [leisure]`).
- `coverage.yaml` slugs all validate against
  `coverage-vocabulary.yaml`. `geometry_types: [polygon, multipolygon]`
  is slightly generous (the input file stores only MultiPolygon
  geometrically) but defensible since `expected_outputs[].geometry_type`
  is Polygon and the feature concept is a park footprint. Kept for
  consistency with the prior evaluator pass.
- `task.json` does not carry an explicit `version` field; per the
  evaluator-prompt rule, the task is implicitly version 1. No
  unilateral edit in this pass changes the prompt / grader / inputs
  contract, so the version is not bumped (correct).

### 3. Changes applied this run

#### Unilateral edits
None. The task remains calibrated as-is; this pass independently
re-verified the prior verdict, added four new post-cutoff `current`
runs to the runs table (all 1.0), and refreshed the three evaluator
artefacts.

#### Proposed but not applied (see HUMAN-REVIEW items)
None.

#### Tests run
- grader on reference: 1.00 (2 gates + 7 subchecks all pass).
- broken solutions: not re-run this pass (no grader or
  metadata.yaml changes since the 2026-05-27 re-run; declared ranges
  unchanged).
- pytest (benchmark/eval): 41 / 41 pass.

---

## Evaluator review 2026-06-06  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`bc9e7c8`) as an L1 data-discovery probe: read a
bundled FlatGeobuf of inner-London parks in EPSG:27700, filter to
features >= 1 ha, and emit a small JSON summary with `count`,
`total_area_ha`, and a `bbox_wgs84` 4-list. The inventory row lists
"Attribute filter + feature count + bbox" as the primary op, region
London, source bundled-local, format in FlatGeobuf / out JSON, CRS in
EPSG:27700 -> bbox out EPSG:4326, geometry Polygon, scale small
(~10^2 parks), upstream OSM tag family `leisure=park`. The
implementation slices Overture `base.land_use` filtered to
`class='park'` (the structural equivalent; documented in
`metadata.yaml` notes). The task exercises FlatGeobuf reading,
planar-area filtering in a projected CRS, m^2->ha unit conversion, and
bbox reprojection on a feature subset; three broken solutions
(`wrong_format`, `wrong_filter`, `wrong_units`) cover the canonical
failure classes, with the m^2/ha unit slip nominated as the expected
weak-agent mode.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | bc9e7c8 | initial-authoring | Initial task (task.json, grade.py, metadata.yaml, README.md, data/, reference/, tests/, IMPLEMENTATION_NOTES.md) | Initial authoring (status: completed). |
| 2026-05-08 | fbd20f2 | docs-change | Repo restructure under benchmark/ subtree | Path move. |
| 2026-05-08 | 001e459 | docs-change | Split benchmark into authoring/ + eval/ subtrees | Path move. |
| 2026-05-13 | 284b843 | prompt-change | Added `tags` block to task.json (faceted-search metadata) | Derived from inventory axes; does not touch instruction / inputs / expected_outputs. |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Card-image pipeline. |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ -> benchmark/tasks/ | Path refactor. |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp (nano-banana-2) | Card-image asset. |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Card-image regeneration. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Card-image regeneration. |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "a FlatGeobuf of" from the instruction | Commit msg: "strip deducible information from DD task instructions" - input format inferable from filename. |
| 2026-05-17 | 88530c5 | prompt-change | Stripped trailing "(lon/lat, [xmin, ymin, xmax, ymax] in EPSG:4326)" suffix from the output-keys sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts". |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg; path-string updates in grade.py, generate.py, _make_brokens.py, _prepare.py, task.json | Mechanical rename, reference output bytes unchanged. |
| 2026-05-26 | 7450e4c | docs-change | Prior evaluator review (calibrated). | Re-evaluate, no edits. |
| 2026-05-27 | fb8de63 | docs-change | Prior evaluator review (calibrated; refreshed artefacts). | Re-evaluate, no edits. |
| 2026-05-28 | 622342b | docs-change | Removed unused `prompt_version` line from `metadata.yaml` | Repo-wide infra change introducing `task.json.version` semantics; not a bump-triggering field. |
| 2026-05-28 | 1d5cbbb | docs-change | Prior evaluator review (calibrated; added new post-cutoff runs). | Re-evaluate, no edits. |

No new commits touching this task's design contract since 2026-05-28.
Cutoff stays at `88530c5` (2026-05-17).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change). Unchanged from the prior block.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:18:01Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:19:18Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:18Z | 1.00 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:53:57Z | 1.00 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:46:30Z | 1.00 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:02:12Z | 1.00 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:35:26Z | 1.00 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:14:22Z | 1.00 | done | current |
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T20:17:36Z | 1.00 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:58:51Z | 0.00 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T23:55:40Z | 1.00 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:27:11Z | 1.00 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T10:57:02Z | 1.00 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:59:38Z | 0.00 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:48:38Z | 1.00 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | n/a | cancelled | current (cancelled before start; not evidence) |

Stale runs (pre-cutoff, considered but not used as evidence): the 23
runs already enumerated in prior evaluator blocks; unchanged.

#### Verdict
**calibrated**

14 of 15 completed `current` runs (excluding the cancelled one) score
either 1.0 or 0.0 across four distinct agent families (Claude Opus
4.6/4.7, DeepSeek V4 Flash, DeepSeek V4 Pro, Gemma 4 26B A4B). The two
0.0 runs are both Gemma 4 26B (`run-20260528-2225Z` and
`run-20260606-0953Z`) and both fail Gate 2 (`structural_correctness`)
with the same diagnostic: `bbox_wgs84` shaped as a dict
(`{min_lon, min_lat, max_lon, max_lat}`) rather than the convention
4-list. Their `count` (42) and `total_area_ha` (519.1620805430861)
are bit-identical to the reference; the geometry pipeline is correct.
The 2026-05-17 prompt strip removed the explicit
`(lon/lat, [xmin, ymin, xmax, ymax])` shape hint deliberately, so the
agent has to infer the canonical bbox shape from convention - which
Opus, DeepSeek, and most Gemma runs do, but a minority of Gemma
attempts get wrong. The grader's Gate-2 list-shape requirement is the
canonical interpretation (GeoJSON RFC 7946, shapely/geopandas
`total_bounds`, rasterio bounds all return 4-tuples); the failure is
a model-side bbox-shape inference miss, not a task miscalibration.
The earlier `wrong_units` broken solution at 0.857 and `wrong_filter`
at 0.286 (re-verified this pass) keep the failure-mode rubric
distinguishing between unit slips, filter slips, and format errors -
the gradient is intact.

2c-CRS check: the output is a non-spatial JSON scalar summary; the
grader does no reprojection on either side, so the
one-sided-reprojection failure mode is structurally inapplicable.
`expected_outputs[].crs` (EPSG:4326), the README's stated
`bbox_wgs84` CRS, and the reference `bbox_wgs84` values (lon/lat) all
agree. Input geometry is 317 MultiPolygon features in EPSG:27700; 42
are >= 1 ha (independently verified). No README/reference/contract
CRS disagreement.

The instruction has been deliberately stripped twice (2026-05-14,
2026-05-17) of every deducible hint: input format, input CRS,
explicit output-CRS form, bbox component order, bbox shape. The
remaining persona constraints (`>= 1 ha`, "hectares", "WGS84 map")
plus the output schema (filename + three keys) are the minimal
specification. Stripping further (e.g. removing "WGS84") would
under-specify the bbox CRS. No further deducible gifts remain.

#### Specific findings
- L1 calibration intact: Gate 1 separates format/schema failures from
  numerical failures; Gate 2 catches bbox-shape inference misses; the
  seven subchecks each detect one canonical numerical mistake; the
  bbox is split into four componentwise checks plus a WGS84-range
  sanity check.
- Two new 0.0 runs (`run-20260528-2225Z`, `run-20260606-0953Z`) are
  both Gemma 4 26B failing Gate-2 with bbox-as-dict. Semantically
  perfect values; convention miss. Per the prompt's "model-side
  failures are not task problems" guidance, this is not actionable -
  bbox-as-list is standard convention, and three other agent families
  (and most Gemma runs) get it right.
- Tolerances in `metadata.yaml` remain well-justified per
  `author-context.md`: `area_pct=0.01` catches the 10000x ha/m^2 slip
  yet absorbs pyogrio/fiona/GDAL float drift at the ~0.01 ha level;
  `bbox_eps_deg=1e-4` ~= 11 m at 51.5N.
- No grader miscalibration suspected; no prompt-grader inconsistency.
- `task.json` was missing `analyst_notes`. Authored this pass per
  Step 4. The notes name the hidden gotcha (CRS-aware area then
  reproject the bbox) and list six pitfalls including the bbox-shape
  inference miss observed in the two failing Gemma runs. Authoring
  `analyst_notes` does not require a `version` bump (human-facing,
  not seen by the agent at run time).
- `coverage.yaml` slugs all validate against
  `coverage-vocabulary.yaml`. Refreshed `evaluator_run_at`.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `analyst_notes` block (description + approach +
  pitfalls) per Step 4. Re-grade on reference: 1.00. Reason: the
  field was missing and the task qualifies for `analyst_notes`
  authoring; no version bump required because it is human-facing
  only.

#### Proposed but not applied (see HUMAN-REVIEW items)
None.

#### Tests run
- grader on reference: 1.00 (2 gates + 7 subchecks all pass).
- broken solutions re-graded: wrong_format 0.0000, wrong_filter
  0.2857, wrong_units 0.8571 (all in declared ranges).
- pytest (benchmark/eval): 41 / 41 pass.


---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Old Gate-2 shape checks (`count` is int, `total_area_ha` is numeric,
  `bbox_wgs84` is list of 4 numbers) are now absorbed into defensive
  coercion inside the existing `count_correct`, `total_area_ha_correct`
  and bbox componentwise subchecks via new `_coerce_int` /
  `_coerce_float` / `_coerce_bbox` helpers. A wrong-typed field now
  costs the relevant subcheck instead of zeroing the score.
- No new subchecks added; subcheck count unchanged at 7.

### Verification
- Reference solution re-graded: 1.0 (7/7 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`bc9e7c8`) as an L1 data-discovery probe: read a
bundled FlatGeobuf of inner-London parks in EPSG:27700, filter to
features >= 1 ha, and emit a small JSON summary with `count`,
`total_area_ha`, and a `bbox_wgs84` 4-list. The inventory row lists
"Attribute filter + feature count + bbox" as the primary op, region
London, source bundled-local, FlatGeobuf in / JSON out, CRS
EPSG:27700 in / bbox out EPSG:4326, Polygon geometry, small scale,
upstream OSM tag family `leisure=park`. The implementation slices
Overture `base.land_use` filtered to `class='park'` (documented
structural equivalent). The task probes FlatGeobuf reading,
planar-area filtering in a projected CRS, m^2-to-ha conversion, and
bbox reprojection of a feature subset, with three broken solutions
covering the canonical failure classes.

#### Change log
Entries before 2026-06-06 are unchanged from the prior evaluator
blocks (initial authoring `bc9e7c8`; path/restructure commits;
tags `284b843`; prompt strips `b04e9f0`, `88530c5`; layout reorg
`29a9ae3`; evaluator reviews `7450e4c`, `fb8de63`, `1d5cbbb`;
versioning infra `622342b`). New commits since the 2026-06-06 block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 1969500 | docs-change | Prior evaluator review (calibrated); authored `analyst_notes` in task.json | Re-evaluate; analyst_notes is human-facing, no bump. |
| 2026-06-06 | 363aed2 | grader-change | Removed `Gate("structural_correctness", ...)`; absorbed its type-shape checks into `_coerce_int` / `_coerce_float` / `_coerce_bbox` defensive coercion inside the existing subchecks; subcheck count unchanged at 7 | Commit msg: benchmark-wide refactor to a single hard gate; shape-recoverable inputs (string counts, dict bboxes) now cost a point each instead of zeroing the score. |
| 2026-06-07 | 632ad1a | grader-change | Added `weight=3.0` to `count_correct`, `total_area_ha_correct`, and the four bbox componentwise subchecks; `bbox_in_wgs84_range` stays weight 1.0 (total weight 19) | Commit msg: weight data-content subchecks 3x in dd graders so a schema-clean but data-wrong submission scores visibly lower. |
| 2026-06-08 | 77fb1a6 | prompt-change | Appended "(as a [xmin, ymin, xmax, ymax] array)" to the instruction's output sentence; added `version: 2` | Commit msg: a Gemma run emitted a `{min_lon, ...}` dict that `_coerce_bbox` does not recognise and scored 0.32 despite perfect count + area; the shape hint disambiguates; rerun scored 1.00. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-08T06:19:23Z (commit 77fb1a6, class: prompt-change; task version 2).
- The two grader-change commits (363aed2 2026-06-06T20:11Z, 632ad1a
  2026-06-07T18:28Z) precede it; 77fb1a6 is the max.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-08T06:18:23Z | 1.00 | done | current (recorded task_version 2) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:14:55Z | 1.00 | done | current (task_version 2) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:23:12Z | 0.3684 | done | current (task_version 2) |

Validity note on run-20260607-112430Z: its per-task `started_at`
(06:18:23Z) is 60 seconds before the cutoff commit's timestamp, and
its `suite_git_sha` (06fd6c0) predates the bump, but the per-task
record carries `task_version: 2` and the bbox values match the v2
contract; commit 77fb1a6's message identifies this as the rerun
executed from the worktree that already contained the v2 prompt,
committed a minute later. Counted as current on that direct evidence.

Stale runs (not used as evidence): all 40 earlier runs enumerated in
prior evaluator blocks are now stale on the version check (graded as
implicit/explicit version 1, pre-Gate-2-removal and pre-weighting
graders). Their pattern (overwhelmingly 1.0 across Opus 4.6/4.7,
Sonnet, Haiku, DeepSeek V4 Flash/Pro, MiniMax M2, HY3, Gemma 4 26B;
two Gemma bbox-dict 0.0s that motivated 77fb1a6; a handful of
model-side/config failures) is consistent with the current verdict.

#### Verdict
**calibrated**

Three current runs span 1.00, 1.00, and 0.3684 across two agent
families. The 0.3684 run (run-20260609-084636Z) was inspected
output-side: `count=42` and `total_area_ha=519.162081` are exact, but
all four bbox componentwise subchecks fail with deltas of 4.7e-4 to
1.9e-3 degrees (roughly 50-200 m) against eps 1e-4. Its `solve.py`
(kept in the run's outputs/, no transcript read needed) shows why: it
took `total_bounds` in EPSG:27700, built a `box()` polygon from those
four corners, reprojected that polygon, and took its bounds, instead
of reprojecting the filtered features and taking their bounds. The
envelope-of-envelope is strictly wider on all four sides. This is a
genuine GIS error the task was designed to catch: the reference's own
comment ("bbox is computed *after* reprojection so the lat/lon
extents enclose the actual geometries, not the back-projected
EPSG:27700 envelope corners", reference/solution/generate.py:49-51)
anticipates exactly this shortcut. The weighted grader prices it
sensibly: count + area + range pass for 7/19 = 0.368, clearly between
the wrong-filter bucket (0.211) and the wrong-units bucket (0.842).
The grader discriminates, partial credit lands where designed, and
the two 1.0 runs confirm the v2 prompt is solvable by mid-tier
agents. No miscalibration.

2c-CRS: the output is a non-spatial JSON scalar summary; the grader
compares scalars and reprojects nothing on either side, so the
one-sided-reprojection failure mode is structurally inapplicable.
`expected_outputs[].crs` (EPSG:4326), the README's stated bbox CRS,
and the reference `bbox_wgs84` (lon/lat) all agree.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `parks_summary.json`, JSON object | instruction | stated |
| top-level keys count, total_area_ha, bbox_wgs84 | instruction | stated |
| >= 1 ha filter | instruction ("one hectare or more") | stated |
| area unit hectares | instruction + key name `total_area_ha` | stated |
| count strict equality | bundled deterministic input | inferable |
| area within 1 % | grader-internal tolerance | inferable (standard drift margin; natural failure modes are orders of magnitude off) |
| bbox in WGS84 lon/lat | instruction ("on a WGS84 map") + key name | stated |
| bbox shape [xmin, ymin, xmax, ymax] array | instruction (since v2) | stated |
| bbox of the reprojected features (not the reprojected envelope) | "bounding box ... around that subset on a WGS84 map" - the minimal bbox of the subset in WGS84 | inferable (canonical bbox semantics; eps 1e-4 deg requires the exact construction) |
| bbox components within 1e-4 deg | grader-internal tolerance | inferable (full-precision or >= 4-decimal rounding passes) |
| input CRS EPSG:27700, format FlatGeobuf | the file itself | inferable (deliberate omission - this is the discovery being tested) |

Factual claims checked: input name `london_parks` matches the bundled
`london_parks.fgb`; 317 features, 42 at >= 1 ha, 519.1621 ha total
and the reference bbox were re-verified against
reference/solution/outputs/parks_summary.json. No inaccurate claim.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: read, assert EPSG:27700,
planar-area filter at 10 000 m^2, sum / 10 000, reproject the subset
to EPSG:4326, take total_bounds, write the three keys. The only
unrequested operation is rounding `total_area_ha` to 4 decimals for
byte-determinism, which sits ~1e-7 relative to the value against a
1 % tolerance - immaterial to grading. No deviation flagged.

#### Specific findings
- The 2026-06-07 weighting commit (632ad1a) changed the broken-set
  scores but `metadata.yaml > broken_solutions > measured_score` was
  not refreshed: wrong_filter 0.2857 -> 0.2105, wrong_units 0.8571 ->
  0.8421 (wrong_format stays 0.0). Both remain inside their declared
  `expected_score_range`. Refreshed unilaterally this pass; README's
  cited scores updated to match.
- README still pointed at the pre-reorg `data/london_parks.fgb` path;
  corrected to `inputs/london_parks.fgb` (docs-change).
- `analyst_notes` claimed the prompt deliberately omits the bbox
  component order, which the v2 instruction now states; description
  corrected, the bbox-dict pitfall reworded for the post-Gate-2
  coercion behaviour, and a new pitfall added for the
  envelope-corner-reprojection error observed in run-20260609-084636Z.
  Human-facing only, no version bump.
- Instruction house style: persona voice intact, full sentences, no
  em-dashes, purpose-then-ask shape; "(london_parks)" matches the
  declared input name while preserving the deliberate format/CRS
  omission. No rewrite needed.
- Coverage tags unchanged from the prior pass; all slugs validate
  against coverage-vocabulary.yaml. `evaluator_run_at` refreshed.

### 3. Changes applied this run

#### Unilateral edits
- metadata.yaml: refreshed broken_solutions measured_score to the
  weighted grader's values (wrong_filter 0.2105, wrong_units 0.8421)
  with a one-line rationale each. Re-grade on reference: 1.00.
  Reason: stale since the 632ad1a weighting commit; Step 4 allows the
  refresh with one re-run. No version bump (exempt field).
- README.md: data/ -> inputs/ path fix; broken-set scores 0.286 ->
  0.211 and 0.857 -> 0.842 in the failure-mode list and the
  weak-agent paragraph. Re-grade on reference: 1.00. Reason: stale
  docs (docs-change, no bump).
- task.json: refreshed analyst_notes (description + pitfalls) per
  Step 4. Re-grade on reference: 1.00. Reason: stale claims after the
  v2 prompt change and Gate-2 removal; human-facing only, no bump.

#### Proposed but not applied (see HUMAN-REVIEW items)
None.

#### Tests run
- grader on reference: 1.00 (1 gate + 7 subchecks all pass).
- broken solutions re-graded: wrong_format 0.0000, wrong_filter
  0.2105, wrong_units 0.8421 (all inside declared ranges).
- pytest (benchmark/eval): 41 / 41 pass.

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change
**Recalibrated subcheck weights by error severity.** The 2026-06-07
repo-wide commit (632ad1a) bluntly set every "data-content" subcheck to
weight 3.0, which here meant count, area, AND all four bbox componentwise
checks were 3.0 while only `bbox_in_wgs84_range` stayed 1.0 (total 19).
That over-weighted the bbox: the four componentwise checks carried 12 of
19 points (63 %), even though they are the *secondary* deliverable and
almost always fail as a group (one error flips all four). The result was
an inverted severity ordering -- an envelope-of-envelope bbox slip with
perfect count + area scored 0.37, *below* the forgot-the-filter solution
(0.21) that botches the central question. Re-weighted so the central
data-content deliverables (count, area) dominate and the secondary bbox
is meaningful but not dominant.

### Weight changes
| Subcheck | Old | New | Rationale |
|---|---|---|---|
| count_correct | 3.0 | 3.0 | Central deliverable (headline count). Unchanged, stays highest. |
| total_area_ha_correct | 3.0 | 3.0 | Central deliverable (headline area). Unchanged, stays highest. |
| bbox_xmin_correct | 3.0 | 1.0 | Secondary deliverable, split x4 for lon/lat-swap partial credit; de-inflated. |
| bbox_ymin_correct | 3.0 | 1.0 | as above |
| bbox_xmax_correct | 3.0 | 1.0 | as above |
| bbox_ymax_correct | 3.0 | 1.0 | as above |
| bbox_in_wgs84_range | 1.0 | 0.5 | Structural sanity check ("plausibly WGS84?"), not a data answer; lowest. |

Total weight 19 -> 10.5.

### Broken scores before -> after
| Class | Before | After | Severity note |
|---|---|---|---|
| wrong_format | 0.0000 | 0.0000 | Unparseable -> gate fail. Most severe. |
| wrong_filter | 0.2105 | 0.1429 | Forgot the central >= 1 ha filter: count AND area both wrong. Now correctly the lowest non-zero bucket. |
| (envelope bbox, run-20260609) | 0.3684 | 0.6190 | Count + area perfect; only the secondary bbox perimeter ~50-200 m too wide. Was wrongly below wrong_filter; now correctly well above it. |
| wrong_units | 0.8421 | 0.7143 | Central count right; one central deliverable (area) off by a 10000x unit slip. Stays top non-zero bucket. |

Ordering: monotone and defensible -- format (0.0) < forgot-filter (0.143)
< envelope-of-envelope bbox (0.619) < unit slip (0.714) < correct (1.0).
A central-question failure (forgot filter) now scores far below a
secondary-deliverable slip with a perfect central answer (envelope bbox),
correcting the prior inversion. No disjoint-failure trap: count and area
are independent of the bbox group, and de-weighting the bbox cannot invert
the count/area-driven buckets.

### Prior-run re-grade (current task version 2)
| Run | Old | New |
|---|---|---|
| run-20260607-112430Z | 1.0000 | 1.0000 |
| run-20260608-074701Z | 1.0000 | 1.0000 |
| run-20260609-084636Z | 0.3684 | 0.6190 |

The only shift is the envelope-of-envelope run rising 0.37 -> 0.62. This
is the intended correction: a submission that nails both headline numbers
and only fluffs the bbox perimeter should not score below a solution that
got the central count + area wrong. The two perfect runs are unaffected.
Earlier runs (version 1) are stale and not re-graded.

### Reasoning
The central skill this data-delivery task probes is the planar-area
filter-and-reduce that produces `count` and `total_area_ha` -- the two
headline numbers the persona (Priya Shah) explicitly asks for. The
`bbox_wgs84` is a secondary deliverable (a study perimeter), correctly
split into four componentwise checks for lon/lat-swap partial credit but
not deserving 63 % of the rubric. The new weights put 6 of 10.5 points
(57 %) on the two central deliverables, 4 on the secondary bbox, and 0.5
on the cosmetic WGS84-range sanity check -- so a meaningful/central
mistake (wrong count or area) drives a large drop while a secondary bbox
slip costs proportionally less.

### Notes (not changed)
- Thresholds/gates untouched: `AREA_TOLERANCE_PCT=0.01`, `BBOX_EPS_DEG=1e-4`,
  the single `format_schema_valid` gate, and all check logic are unchanged.
  No threshold miscalibration suspected.

### Changes applied this run

#### Unilateral edits
- grade.py: subcheck `weight=` values only (table above). Re-grade on
  reference: 1.00.
- metadata.yaml: refreshed `broken_solutions` measured_score and
  expected_score_range for wrong_filter (0.1429, [0.10,0.25]) and
  wrong_units (0.7143, [0.65,0.78]); refreshed weight-arithmetic prose in
  the per-broken comments.
- README.md: refreshed stale broken score fractions (wrong_filter
  0.211 -> 0.143, wrong_units 0.842 -> 0.714) in the failure-mode list and
  the weak-agent paragraph.

#### Proposed but not applied (see HUMAN-REVIEW items)
None.

#### Tests run
- grader on reference: 1.00 (1 gate + 7 subchecks all pass).
- broken solutions re-graded: wrong_format 0.0000, wrong_filter 0.1429,
  wrong_units 0.7143 (all inside refreshed ranges).
- pytest: not run (orchestrator runs the suite).
