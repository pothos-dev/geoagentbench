# Implementation notes — crs-l1-paris-lambert93

## Status
completed

## Summary
L1 CRS-reprojection task: WGS84 GeoJSON of 330 Paris (Marais) building
footprints → EPSG:2154 (Lambert-93) GeoJSON, attributes preserved.
Re-verified end-to-end under prompt_version 2026-05-07-a; all acceptance
checks pass with no code changes required (the prior 2026-05-06-a
authoring already complied with the "persona-doesn't-introduce-themselves"
rule that 2026-05-07-a clarified). Cosmetic README fix: the broken-solution
mention `broken_wrong_crs_metadata_only` was retitled to match the
filesystem directory `broken_wrong_crs`.

## Verification results
- Reference grader score: 1.00 (8/8 subchecks)
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - wrong_crs_metadata_only: 0.50 (expected range [0.4, 0.6])
  - wrong_attributes: 0.875 (expected range [0.8, 0.95])
- Second-run output match: bit-identical (re-ran `reference/generate.py`
  inside Docker; `diff` against pre-run snapshot returned no output)
- Library tests after task: pass (32/32 via `uv run pytest`)

## Failure-mode coverage
- Forgot to reproject (output still EPSG:4326): broken_wrong_format
- Stamped CRS as 2154 without reprojecting (WGS84 coords in 2154 metadata):
  broken_wrong_crs
- Dropped `height` / `num_floors` columns: broken_wrong_attributes
- Reprojected into wrong target CRS (e.g., UTM 31N): principled — Gate 1
  EPSG-equality check (`crs.to_epsg() == 2154`)
- Filter / drop features by mistake: principled — Gate 2 count tolerance
  + `feature_id_set_preserved` subcheck
- Wrote geometry as MultiPolygon (upcast): principled —
  `geometry_type_is_polygon` subcheck
- Lost topology (aggressive simplify / centroid): principled —
  `geometry_iou_high` + per-feature / total area subchecks

## Open issues
- [low] OVERTURE_REFERENCE.md's example DuckDB query uses an HTTPS Azure
  blob URL with a `*.parquet` glob. With current DuckDB (1.5.2) that path
  errors out. The s3://overturemaps-us-west-2 path works only with an
  anonymous SECRET block (`CREATE SECRET (... TYPE s3, KEY_ID '', SECRET
  '', REGION 'us-west-2' ...)`). Working pattern recorded in
  `data/_prepare_input.py`. Same issue flagged by the peer London / NYC
  CRS tasks.

## Suggested prompt changes
- [med] `prompts/task-design-prompt.md` lists the pinned dependencies as
  "geopandas, shapely, pyogrio, pyproj, duckdb, pandas, numpy, requests,
  pyyaml" — `pyarrow` is also needed (and present in `pyproject.toml` and
  the `geo-bench-author` image), since several inventory tasks declare
  GeoParquet I/O. The prompt's deps list lags reality; please update.
  Same suggestion already raised by the peer NYC and London CRS tasks.

## Inventory change proposals
(none)

## Library extensions
(none — task uses only existing primitives:
`feature_set_equality_by_id`, `attribute_match`, `count_within_tolerance`,
`iou_with_tolerance`)

## Runtime
~5 minutes (verification only: reference re-run, three broken grades,
pytest, notes / metadata refresh; no fetching, no image rebuild).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Task probes CRS-reprojection literacy at the L1 tier on a real French
study area: take a small bundled WGS84 GeoJSON of Paris (Marais)
building footprints and reproject to RGF93 / Lambert-93 (EPSG:2154)
with attributes and Polygon-only geometry preserved. The inventory row
(`benchmark/authoring/inventory.md`, lines 339–362) frames the persona
as Camille Roux at IGN preparing a sample for a downstream heat-loss
model that refuses lat/lon. The original instruction (commit
`fbd20f2`, 2026-05-08) explicitly named "RGF93 / Lambert-93 metres"
and "EPSG:2154"; later strips removed those nudges in line with the
project's instruction-stripping policy.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | fbd20f2 | initial-authoring | Initial task drop under `benchmark/tasks/crs-l1-paris-lambert93/` (task.json, grade.py, metadata, README, IMPLEMENTATION_NOTES, reference/generate.py + outputs, three broken sets, data/ + _prepare_input.py). | Commit msg: "restructure: split repo into thesis/ benchmark/ references/" — initial commit lands the task as part of the repo reshuffle. |
| 2026-05-08 | 001e459 | mixed (docs-change/path-only) | File-rename only: `benchmark/tasks/.../` → `benchmark/eval/tasks/.../` (no content changes per `--stat` showing 0/0 line counts). | Commit msg: "benchmark: split into authoring/ and eval/ subtrees". |
| 2026-05-12 | ca819c8 | docs-change | Added `visualize.py` for this and every other geometry-producing task. | Commit msg: "eval: add visualize.py for every geometry-producing task". |
| 2026-05-12 | 9f5006e | docs-change | Added `reference/visualizations/buildings.pmtiles` + `layers.json` as a side-effect of authoring an unrelated task. | Commit msg: "task: dc-l3-vienna-overpass-historical [completed]" — visualization artefacts only. |
| 2026-05-13 | 1710715 | prompt-change | Appended a structured "Output schema:" bullet block to `task.json.instruction`. | Commit msg: "eval tasks: declare exact output schema in prompts to match graders … No grader changes; no subchecks loosened." |
| 2026-05-13 | 284b843 | prompt-change (tags only) | Added structured `tags` dict to `task.json` (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale). | Commit msg: "eval tasks: add structured tags to all 36 task.json files". |
| 2026-05-13 | 4f0cfc0 | prompt-change | Folded the bullet "Output schema:" block into a prose paragraph in the instruction. | Commit msg: "Merge output schema blocks into prose for 6 task instructions … preserving all technical requirements." |
| 2026-05-13 | 89150101, 1b8dda1 | docs-change | Added `image-prompt.md` and `image.webp` task-card asset. | Commit msgs: "tasks: add image-prompt.md to all 36 task directories", "tasks: generate image.webp for all 36 task directories". |
| 2026-05-13 | 3c65373, cfbdc7c | docs-change | Regenerated `image.webp` (FLUX schnell, then nano-banana-2). | Commit msgs cosmetic — visual asset regen only. |
| 2026-05-13 | a3a8d53 | docs-change | Path rename: `benchmark/eval/tasks/` → `benchmark/tasks/`. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/". |
| 2026-05-14 | d5c283d | prompt-change | Stripped deducible information from instruction: removed "WGS84" input-CRS mention, removed geometry-type description ("Polygon"), removed input column enumeration, condensed leading clause. Output target CRS (`EPSG:2154`) still named. | Commit msg: "Strip deducible information from CRS task instructions … Output requirements (target CRS, output columns, output geometry types) and task framing are preserved." |
| 2026-05-17 | b4583b4 | prompt-change | Removed explicit `EPSG:2154` and `RGF93 / Lambert-93` names from the instruction; replaced with "standard official projection for the Paris region". Output filename retains `lambert93` as the contractual hint. | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" — explanation thin but consistent with the stripping policy in `instruction-stripping-guide.md > STRIP — deducible analysis strategy`. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Commit message does not explicitly state *why* now and not earlier; rationale inferred from `instruction-stripping-guide.md`. |
| 2026-05-26 | 29a9ae3 | mixed (path-only + minor) | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/{generate.py,outputs/,visualizations/}` → `reference/solution/...`, `tests/` → `reference/failures/`, `image{.webp,-prompt.md}` → `assets/`. Path references in grader, generator, broken-set script, prepare script, task.json input URL adjusted accordingly. Content of generate.py / grade.py / metadata otherwise unchanged. | Commit msg: "Reorganize task folder layout" — explicit and clean. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit `b4583b4`, class: prompt-change — the last instruction strip).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:55:20Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:25:53Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:50:56Z | 1.0 | done | current |

Stale (pre-cutoff) runs: 23 runs from 2026-05-12 → 2026-05-17T06Z covering claude-haiku, claude-sonnet, claude-opus, deepseek-v4-flash, gemma4-26b (4× failed/cancelled — model-side), and one stale 0.0 score (`run-20260517-0614Z`, deepseek-v4-flash) caused by the model writing output still stamped EPSG:4326 (Gate 1 fail) — that pre-dates the cutoff and is not evidence on the current prompt.

#### Verdict
**calibrated**

The cut-down instruction still admits exactly one correct answer family. All three current runs — spanning three model families of meaningfully different capability (Claude Opus, DeepSeek V4 flash, Gemma 4 26B) — produced bit-correct EPSG:2154 reprojections (IoU 1.000000, per-feature area match 1.0, all 8 subchecks pass). The L1 specification expects a single-op reprojection on bundled data to be solvable by any agent with basic GIS competence; "all current runs at 1.0" on L1 is not by itself a "too-easy" symptom. Crucially, the instruction does *not* over-specify: the EPSG code, the algorithm name, the input CRS, and the input geometry type have all been stripped (commits `d5c283d`, `b4583b4`). The only target-CRS cues left are (a) the output filename `paris_buildings_lambert93.geojson` and (b) "standard official projection for the Paris region" — both are necessary information per `instruction-stripping-guide.md` (output filenames are part of the contract; geographic scope is KEEP). Reading the three current `solve.py` files confirms each agent independently mapped "Paris / standard projection / lambert93 filename" to EPSG:2154, which is the test we want. Broken-solution scores (0.0 / 0.5 / 0.875) match `metadata.yaml > broken_solutions.measured_score` exactly, so the grader still discriminates failure modes as designed.

#### Specific findings
- Instruction wording, voice, word count (~73 of 80 L1 budget), and persona-as-author rule all comply with `task-design-prompt.md`. No edits proposed.
- Tolerances in `metadata.yaml` (count_pct 0.05, area_pct 0.01, jaccard_min 0.95, geom_eps_m 0.001) match the projection-accuracy rationale in `author-context.md > CRS-reprojection: principled bound`. No edits proposed.
- All three broken sets grade to their declared `measured_score` (0.0, 0.5, 0.875). No edits proposed.
- The reference output is byte-stable: a current grader run yields IoU 1.000000 and 0.0000% total-area diff against the committed reference. No edits proposed.
- Stale 0.0 run (`run-20260517-0614Z`, deepseek-v4-flash) at gate 1 (CRS still 4326) pre-dates the b4583b4 strip and is not a signal on the current prompt; the same agent post-cutoff (`run-20260517-1424Z`) scored 1.0.
- README's `## Story` mentions "Marais", which is consistent with the inventory's Marais bbox; no inconsistency.

### 3. Changes applied this run

#### Unilateral edits
(none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit `b4583b4` ("Remove CRS/operation nudges from 5 CRS task prompts") removed the explicit EPSG:2154 and Lambert-93 names from the instruction; the rationale is inferable from `instruction-stripping-guide.md` (CRS naming is deducible from geographic context) but not stated in the commit message itself. Low severity — current behaviour is consistent with documented policy.

#### Tests run
- grader on reference (`reference/solution/outputs/`): 1.0 (8/8 subchecks pass; IoU 1.000000; total-area rel diff 0.0000%)
- grader on `broken_wrong_format`: 0.0 (matches `metadata.yaml > expected_score_range [0.0, 0.0]`)
- grader on `broken_wrong_crs`: 0.5 (matches `[0.4, 0.6]`)
- grader on `broken_wrong_attributes`: 0.875 (matches `[0.8, 0.95]`)
- pytest: 32/32 substantive tests pass. One collection-time `ImportError` in `tests/test_runner_smoke.py` because the eval venv is not bootstrapped (`pyogrio` needs `gdal-config`, `httpx` not installed). This is an env-setup gap, not a code regression, and is unrelated to this task. Tested with `PYTHONPATH=benchmark/eval /home/nhp/project/.venv/bin/python -m pytest -q --ignore=tests/test_runner_smoke.py`.

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
This is an L1 CRS-reprojection task: take a small bundled WGS84 GeoJSON of
Paris (Marais) building footprints and reproject it to RGF93 / Lambert-93
(EPSG:2154) with attributes verbatim and geometry kept as Polygon (no
upcast to MultiPolygon). The inventory row (`benchmark/authoring/inventory.md`,
lines 339–362) frames the persona as Camille Roux, an IGN cadastre intern,
preparing a sample for a colleague's heat-loss model that refuses lat/lon.
The earliest committed instruction (commit `7b96e3f`, 2026-05-07, then
re-landed verbatim in the repo restructure `fbd20f2`, 2026-05-08) named
"RGF93 / Lambert-93 metres" and "EPSG:2154" explicitly; later commits
stripped those nudges in line with the project's instruction-stripping
policy (`benchmark/authoring/instruction-stripping-guide.md`).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 7b96e3f | initial-authoring | First completed drop of the task under the (pre-restructure) `tasks/crs-l1-paris-lambert93/` path: README/metadata/IMPLEMENTATION_NOTES tweaks on top of the authored task.json + grader + reference + brokens. Initial instruction names "RGF93 / Lambert-93 metres" and "EPSG:2154". | Commit msg: "task: crs-l1-paris-lambert93 [completed]" — authoring agent's completion commit. |
| 2026-05-08 | fbd20f2 | initial-authoring (re-landed) | Repo restructure that re-lands the task verbatim under `benchmark/tasks/crs-l1-paris-lambert93/`. Instruction unchanged from `7b96e3f`. | Commit msg: "restructure: split repo into thesis/ benchmark/ references/". |
| 2026-05-08 | 001e459 | docs-change (path-only) | File-rename only: `benchmark/tasks/...` → `benchmark/eval/tasks/...`. No content change. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees". |
| 2026-05-12 | ca819c8 | docs-change | Added `visualize.py` for geometry-producing tasks. | Commit msg: "eval: add visualize.py for every geometry-producing task". |
| 2026-05-12 | 9f500eb | docs-change | Added `reference/visualizations/buildings.pmtiles` + `layers.json` as a side-effect of another task. | Commit msg: "task: dc-l3-vienna-overpass-historical [completed]". |
| 2026-05-13 | 1710715 | prompt-change | Appended a structured "Output schema:" block to `task.json.instruction`. | Commit msg: "eval tasks: declare exact output schema in prompts to match graders … No grader changes; no subchecks loosened." |
| 2026-05-13 | 284b843 | prompt-change (tags only) | Added structured `tags` dict to `task.json`. | Commit msg: "eval tasks: add structured tags to all 36 task.json files". |
| 2026-05-13 | 4f0cfc0 | prompt-change | Folded the bullet "Output schema:" block into a prose paragraph in the instruction. | Commit msg: "Merge output schema blocks into prose for 6 task instructions … preserving all technical requirements." |
| 2026-05-13 | 8915010, 1b8dda1 | docs-change | Added `image-prompt.md` and `image.webp` task-card asset. | Commit msgs: "tasks: add image-prompt.md to all 36 task directories", "tasks: generate image.webp …". |
| 2026-05-13 | 3c65373, cfbdc7c | docs-change | Regenerated `image.webp` (FLUX schnell, then nano-banana-2). | Commit msgs: visual-asset regen only. |
| 2026-05-13 | a3a8d53 | docs-change (path-only) | Path rename: `benchmark/eval/tasks/` → `benchmark/tasks/`. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/". |
| 2026-05-14 | d5c283d | prompt-change | Stripped deducible info from the instruction: removed "WGS84" input-CRS mention, removed the "Polygon" geometry-type description, removed the input-column enumeration, condensed the leading clause. Output target CRS (`EPSG:2154`) still named. | Commit msg: "Strip deducible information from CRS task instructions … Output requirements (target CRS, output columns, output geometry types) and task framing are preserved." |
| 2026-05-17 | b4583b4 | prompt-change | Removed the explicit `EPSG:2154` and `RGF93 / Lambert-93` names from the instruction; replaced with "standard official projection for the Paris region". Output filename retains `lambert93` as the contractual hint. | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" — explanation thin but consistent with `instruction-stripping-guide.md > STRIP — deducible analysis strategy`. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Commit message does not state *why* now and not earlier; rationale inferred from `instruction-stripping-guide.md`. |
| 2026-05-26 | 29a9ae3 | docs-change (path-only) | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/{generate.py,outputs/,visualizations/}` → `reference/solution/...`, `tests/` → `reference/failures/`, `image{.webp,-prompt.md}` → `assets/`. Only path references inside grade.py / generate.py / _make_brokens.py / _prepare.py and the `task.json` input URL (`data/` → `inputs/`) were updated; instruction text, grading logic, and reference outputs are byte-unchanged. | Commit msg: "Reorganize task folder layout" — explicit and clean. Treated as non-answer-affecting (path-only). |
| 2026-05-26 | 353937f | docs-change (evaluator artefacts) | Prior evaluator review: appended `audit/AUTHORING_HISTORY.md` block, wrote `coverage.yaml` and `audit/status.json`. Verdict calibrated; HR-001 raised. No unilateral edits. | Commit msg: "Re-evaluate crs-l1-paris-lambert93: calibrated, 1 flag (low)". |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit `b4583b4`, class: prompt-change — the last instruction strip). The 2026-05-26 reorg (`29a9ae3`) is path-only: it touches the `task.json` input URL and internal path constants but leaves the instruction string, grading logic, and reference outputs byte-identical, so it does not move the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-opus-4-6 | 2026-05-17T12:55:20Z | 1.0 | done | current |
| run-20260517-1424Z | deepseek/deepseek-v4-flash | 2026-05-17T14:25:53Z | 1.0 | done | current |
| run-20260526-0748Z | google/gemma-4-26b-a4b-it | 2026-05-26T07:50:56Z | 1.0 | done | current |

Stale (pre-cutoff) runs considered but not used as evidence on the current prompt: 25 runs from 2026-05-12 → 2026-05-17T06Z spanning claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-6, deepseek-v4-flash, tencent/hy3-preview, and gemma4-26b. Most scored 1.0. Four are model-side failures (gemma4-26b: `ConnectError`, `OPENROUTER_API_KEY not configured`, two `cancelled`) — agent-engineering / infra issues, not task problems. Two 2026-05-12 claude-code-sonnet-basic run dirs exist but their `run.json` contains no `crs-l1-paris-lambert93` task block (partial run), so they carry no score. One stale 0.0 (`run-20260517-0614Z`, deepseek-v4-flash) failed Gate 1 by writing output still stamped EPSG:4326; it pre-dates the b4583b4 strip and the same model post-cutoff (`run-20260517-1424Z`) scored 1.0, so it is not a signal on the current prompt.

#### Verdict
**calibrated**

All three current runs span three meaningfully different model families (Claude Opus 4.6, DeepSeek V4 Flash, Gemma 4 26B) and each independently produced a bit-correct EPSG:2154 reprojection: 330 features, Polygon-only, identical schema (`id, class, subtype, name, height, num_floors`), matching the reference exactly. The current instruction has had the EPSG code, the CRS name, the input CRS, the algorithm name, and the geometry-type description all stripped (commits `d5c283d`, `b4583b4`); the agent must independently map "standard official projection for the Paris region" → EPSG:2154. The only residual target-CRS cue is the output filename `paris_buildings_lambert93.geojson`, which is part of the I/O contract per `instruction-stripping-guide.md`. This is therefore *not* over-specified, so "all current runs at 1.0 on an L1 single-op" does not meet the `too-easy` bar (which additionally requires instruction over-specification). The grader discriminates failure modes as designed: re-running it now yields reference 1.0 (8/8), `broken_wrong_format` 0.0, `broken_wrong_crs` 0.5, `broken_wrong_attributes` 0.875 — exactly the `metadata.yaml > broken_solutions.measured_score` values, in three distinct ranges. CRS/format consistency (Step 2c-CRS) holds: reference output, `expected_outputs[].crs`, and README all agree on EPSG:2154 GeoJSON, and `grade.py` compares both submission and reference in their native EPSG:2154 — there is no one-sided reprojection in the grader (IoU and per-feature/total area are all computed in the metric CRS on both sides).

#### Specific findings
- Instruction voice, persona-as-author compliance, and word budget (~73 of the 80-word L1 budget) all comply with `task-design-prompt.md`. No edit proposed.
- Tolerances in `metadata.yaml` (count_pct 0.05, area_pct 0.01, jaccard_min 0.95, geom_eps_m 0.001) match the projection-accuracy rationale in `author-context.md > Tolerance philosophy > CRS-reprojection: principled bound`. No edit proposed.
- Reference output is byte-stable: a current grader run yields IoU 1.000000 and 0.0000% total-area diff against the committed reference. No edit proposed.
- All `coverage.yaml` slugs validate against `coverage-vocabulary.yaml`; `crs_variants: [wgs84, conformal]` correctly captures the WGS84 input and the Lambert-Conformal-Conic (EPSG:2154) output. No vocabulary gap. Re-emitted with a fresh `evaluator_run_at` timestamp; values unchanged from the prior evaluator block.
- HR-001 (commit `b4583b4`'s thin rationale) carried forward from the prior evaluator block; the inference from `instruction-stripping-guide.md` is unchanged. Low severity.

### 3. Changes applied this run

#### Unilateral edits
(none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit `b4583b4` ("Remove CRS/operation nudges from 5 CRS task prompts") removed the explicit EPSG:2154 and Lambert-93 names from the instruction; the rationale is inferable from `instruction-stripping-guide.md` (CRS naming is deducible from geographic context) but not stated in the commit message itself. Low severity — current behaviour is consistent with documented policy.

#### Tests run
- grader on reference (`reference/solution/outputs/`): 1.0 (8/8 subchecks; IoU 1.000000; total-area rel diff 0.0000%)
- grader on `broken_wrong_format`: 0.0 (matches `metadata.yaml > expected_score_range [0.0, 0.0]`)
- grader on `broken_wrong_crs`: 0.5 (matches `[0.4, 0.6]`)
- grader on `broken_wrong_attributes`: 0.875 (matches `[0.8, 0.95]`)
- pytest: pass (35/35 via `cd benchmark/eval && uv run pytest`)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
L1 CRS-reprojection task: a small bundled WGS84 GeoJSON of Paris (Marais) building footprints is reprojected into RGF93 / Lambert-93 (EPSG:2154), polygon-only, with attributes verbatim. Persona Camille Roux (IGN cadastre intern) preparing a sample for a downstream heat-loss model that refuses lat/lon, per the inventory row (`benchmark/authoring/inventory.md`, lines 339–362). The earliest committed instruction (`7b96e3f`, 2026-05-07) named EPSG:2154 / Lambert-93 explicitly; subsequent strips removed those nudges in line with `instruction-stripping-guide.md`.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 7b96e3f | initial-authoring | First completed drop of the task. Instruction names "RGF93 / Lambert-93 metres" and "EPSG:2154". | Commit msg: "task: crs-l1-paris-lambert93 [completed]". |
| 2026-05-08 | fbd20f2 | initial-authoring (re-landed) | Repo restructure re-lands task verbatim under `benchmark/tasks/...`. | Commit msg: "restructure: split repo into thesis/ benchmark/ references/". |
| 2026-05-08 | 001e459 | docs-change (path-only) | Path rename: `benchmark/tasks/...` → `benchmark/eval/tasks/...`. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees". |
| 2026-05-12 | ca819c8 | docs-change | Added `visualize.py` for geometry-producing tasks. | Commit msg: "eval: add visualize.py for every geometry-producing task". |
| 2026-05-12 | 9f500eb | docs-change | Added `reference/visualizations/buildings.pmtiles` + `layers.json` as a side-effect of another task. | Commit msg: "task: dc-l3-vienna-overpass-historical [completed]". |
| 2026-05-13 | 1710715 | prompt-change | Appended a structured "Output schema:" block to `task.json.instruction`. | Commit msg: "eval tasks: declare exact output schema in prompts to match graders … No grader changes; no subchecks loosened." |
| 2026-05-13 | 284b843 | prompt-change (tags only) | Added structured `tags` dict to `task.json`. | Commit msg: "eval tasks: add structured tags to all 36 task.json files". |
| 2026-05-13 | 4f0cfc0 | prompt-change | Folded the bullet "Output schema:" block into a prose paragraph. | Commit msg: "Merge output schema blocks into prose for 6 task instructions". |
| 2026-05-13 | 8915010, 1b8dda1 | docs-change | Added `image-prompt.md` and `image.webp` task-card asset. | Commit msgs: "tasks: add image-prompt.md …", "tasks: generate image.webp …". |
| 2026-05-13 | 3c65373, cfbdc7c | docs-change | Regenerated `image.webp`. | Commit msgs: visual-asset regen only. |
| 2026-05-13 | a3a8d53 | docs-change (path-only) | Path rename: `benchmark/eval/tasks/` → `benchmark/tasks/`. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/". |
| 2026-05-14 | d5c283d | prompt-change | Stripped deducible info from the instruction (removed WGS84 input-CRS mention, the Polygon geometry-type description, the input-column enumeration; condensed leading clause). Output target CRS (`EPSG:2154`) still named. | Commit msg: "Strip deducible information from CRS task instructions … Output requirements (target CRS, output columns, output geometry types) and task framing are preserved." |
| 2026-05-17 | b4583b4 | prompt-change | Removed explicit `EPSG:2154` and `RGF93 / Lambert-93` names from the instruction; replaced with "standard official projection for the Paris region". Output filename retains `lambert93` as the contractual hint. | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" — thin but consistent with `instruction-stripping-guide.md > STRIP — deducible analysis strategy`. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Commit message does not state *why* now and not earlier; rationale inferred from `instruction-stripping-guide.md`. |
| 2026-05-26 | 29a9ae3 | docs-change (path-only) | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/{generate.py,outputs/,visualizations/}` → `reference/solution/...`, `tests/` → `reference/failures/`, `image{.webp,-prompt.md}` → `assets/`. Only path references inside grade.py / generate.py / _make_brokens.py / _prepare.py and `task.json` input URL updated; instruction text, grading logic, reference outputs byte-unchanged. | Commit msg: "Reorganize task folder layout". Non-answer-affecting (path-only). |
| 2026-05-26 | 353937f | docs-change (evaluator artefacts) | Prior evaluator block + coverage.yaml + status.json. | Commit msg: "Re-evaluate crs-l1-paris-lambert93: calibrated, 1 flag (low)". |
| 2026-05-27 | c71e0f6 | docs-change (evaluator artefacts) | Prior evaluator block + coverage.yaml + status.json. | Commit msg: "Re-evaluate crs-l1-paris-lambert93: calibrated, 1 flag (low)". |
| 2026-05-28 | 622342b | docs-change (metadata-only) | Project-wide change: removed the now-unused `prompt_version: 2026-05-07-a` line from `metadata.yaml`. Instruction, grader, tolerances, reference, inputs, brokens all byte-unchanged. (`task.json` was *not* edited for this slug — no `prompt_version` was present to drop, and no `version` was added yet.) | Commit msg: "Add task content versioning; drop unused prompt_version" — global infra change, explicit. Treated as non-answer-affecting (`prompt_version` was an authoring-template tag, not part of the prompt/grader/input contract). |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit `b4583b4`, class: prompt-change — the last instruction strip). The 2026-05-26 reorg (`29a9ae3`) is path-only; the 2026-05-28 versioning change (`622342b`) only removed an authoring-template tag from `metadata.yaml` (no prompt/grader/tolerance/input edit, no `task.json` change for this slug). Neither moves the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:54:11Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:24:31Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:48:55Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T20:16:18Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:21:16Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T01:13:49Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:17:33Z | 1.0 | done | current |

Stale (pre-cutoff) runs: 24 runs from 2026-05-12 → 2026-05-17T06Z spanning claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-6, deepseek-v4-flash, tencent/hy3-preview, gemma4-26b. Most scored 1.0. A few are model-side failures (network errors, `cancelled`). One stale 0.0 (`run-20260517-0614Z`, deepseek-v4-flash) failed Gate 1 by writing output still stamped EPSG:4326; it pre-dates the b4583b4 strip and the same model post-cutoff (`run-20260517-1424Z`) scored 1.0. No signal on the current prompt.

#### Verdict
**calibrated**

Seven `current` runs from three meaningfully distinct model families (Claude Opus, DeepSeek V4 Flash, Gemma 4 26B) all produce bit-correct EPSG:2154 reprojections — 330 features, Polygon-only, schema `id, class, subtype, name, height, num_floors`, IoU 1.000000, per-feature area match 1.0, all 8 subchecks pass. The instruction has had the EPSG code, the CRS name, the input CRS, the algorithm name, the input column list, and the geometry-type description all stripped; the only residual target-CRS cue is the output filename `paris_buildings_lambert93.geojson` (part of the I/O contract per `instruction-stripping-guide.md`) plus the prose "standard official projection for the Paris region". The agent must independently map "Paris / official projection / lambert93 filename" → EPSG:2154. This is *not* over-specified, so "all current runs at 1.0 on an L1 single-op" does not meet the `too-easy` bar (which additionally requires instruction over-specification). The grader still discriminates failure modes as designed: re-run now yields reference 1.0 (8/8), `broken_wrong_format` 0.0, `broken_wrong_crs` 0.5, `broken_wrong_attributes` 0.875 — exactly the `metadata.yaml > broken_solutions.measured_score` values, in three distinct ranges.

Step 2c-CRS check: reference output, `expected_outputs[].crs`, and README all agree on EPSG:2154 GeoJSON; `grade.py` compares both submission and reference in their native EPSG:2154 (no one-sided reprojection in the grader — IoU and per-feature/total area are computed in metres on both sides). Output filename is consistent (`paris_buildings_lambert93.geojson` in instruction, `expected_outputs[]`, README, reference, brokens).

Step 4 unilateral-edit triggers checked and ruled out:
- *GeoJSON-CRS strip* — does not apply: the instruction contains no EPSG/WGS84/4326 mentions to remove. The output is GeoJSON but intentionally in EPSG:2154 (RFC-7946-non-compliant by design; same precedent as the London/NYC peer CRS tasks). The grader's CRS gate requires EPSG:2154 — that is the test.
- *Tighten redundant statements* — examined two near-duplicates and rejected:
  - "Geometries must stay as Polygon — do not upcast to MultiPolygon" vs. `expected_outputs[].geometry_type: Polygon`. The schema field alone does **not** encode the non-mutation invariant: `grade.py` lets MultiPolygon pass the structural gate (`geom_types.issubset({"Polygon", "MultiPolygon"})`) and only the `geometry_type_is_polygon` subcheck penalises an upcast. The "do not upcast to MultiPolygon" wording is the constraint the subcheck enforces; deleting it would weaken the test. Keep.
  - "attributes unchanged" (para 1) vs. "Preserve every input column without dropping any" (para 2). The two pin different things: the first is a value-preservation statement; the second is a schema/column-presence statement. The grader has both subchecks (`identifying_attributes_preserved`, `original_columns_preserved`) and they fail independently in the broken sets (`wrong_attributes` drops columns but not values). Tightening either away would leave one constraint unstated. Keep both.
- *CRS accept-list refactor* — does not apply: no current run was Gate-1-rejected for picking a defensible alternative CRS (every current run picked EPSG:2154 directly). The instruction language ("standard official projection for the Paris region") already nudges toward Lambert-93 without naming the code; further refactor is unjustified without observed evidence of a Gate-1 miss.
- *Loosen a grader tolerance* — does not apply: no correct-looking output rejected by drift.
- *Tighten a grader subcheck* — does not apply: every broken set still scores in its declared range.
- *Refresh `measured_score`* — does not apply: re-run scores (0.0 / 0.5 / 0.875) match `metadata.yaml` exactly.
- *Vocabulary slug add* — does not apply: `coverage.yaml` slugs already validate.

No prompt/grader/tolerance/input edit applied this pass, so no `task.json.version` bump is required.

#### Specific findings
- Instruction voice, persona-as-author compliance, and word budget (~73 of the 80-word L1 budget) all comply with `task-design-prompt.md`. No edit proposed.
- Tolerances in `metadata.yaml` (count_pct 0.05, area_pct 0.01, jaccard_min 0.95, geom_eps_m 0.001) match the projection-accuracy rationale in `author-context.md`. No edit proposed.
- Reference output is byte-stable: current grader run yields IoU 1.000000 and 0.0000% total-area diff. No edit proposed.
- `coverage.yaml` slugs validate against `coverage-vocabulary.yaml`; `crs_variants: [wgs84, conformal]` correctly captures the WGS84 input and the Lambert-Conformal-Conic (EPSG:2154) output. Re-emitted with a fresh `evaluator_run_at` timestamp; values unchanged from the prior evaluator block.
- HR-001 (commit `b4583b4`'s thin rationale) carried forward from the prior evaluator block; inference from `instruction-stripping-guide.md` unchanged. Low severity.

### 3. Changes applied this run

#### Unilateral edits
(none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit `b4583b4` ("Remove CRS/operation nudges from 5 CRS task prompts") removed the explicit EPSG:2154 and Lambert-93 names from the instruction; rationale inferable from `instruction-stripping-guide.md` (CRS naming deducible from geographic context) but not stated in the commit message itself. Low severity — current behaviour is consistent with documented policy.

#### Tests run
- grader on reference (`reference/solution/outputs/`): 1.0 (8/8 subchecks; IoU 1.000000; total-area rel diff 0.0000%)
- grader on `broken_wrong_format`: 0.0 (matches `metadata.yaml > expected_score_range [0.0, 0.0]`)
- grader on `broken_wrong_crs`: 0.5 (matches `[0.4, 0.6]`)
- grader on `broken_wrong_attributes`: 0.875 (matches `[0.8, 0.95]`)
- pytest: pass (41/41 via `cd benchmark/eval && uv run pytest`)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
L1 CRS-reprojection task: a small bundled WGS84 GeoJSON of Paris (Marais) building footprints is reprojected into RGF93 / Lambert-93 (EPSG:2154), polygon-only, with attributes verbatim. Persona is Camille Roux (IGN cadastre intern) preparing a sample for a downstream heat-loss model that refuses lat/lon, per the inventory row (`benchmark/authoring/inventory.md`, lines 339–362). Two recent project-wide passes meaningfully reshaped this task since the prior evaluator block: (a) `05aabd6` softened the CRS hard-fail across 21 graders into a two-subcheck deduction, and (b) `b0bc006` migrated the output format from GeoJSON to GeoPackage (so the CRS lives in the file itself instead of fighting RFC 7946) and rewrote the instruction in the project's house style.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | docs-change (metadata-only) | Project-wide: removed the now-unused `prompt_version` line from `metadata.yaml`. Instruction, grader, tolerances, reference, inputs, brokens all byte-unchanged. (Captured in the prior evaluator block already; included here for continuity.) | Commit msg: "Add task content versioning; drop unused prompt_version". Non-answer-affecting. |
| 2026-05-28 | 05aabd6 | grader-change | Replaced the Gate-1 hard CRS check with `grade_crs_soft`: any submission with a usable CRS now passes the gate, the submission is reprojected to EPSG:2154 for downstream geometric subchecks, and two new subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) dock points. `MEANINGFUL_EPSGS = {2154, 32631}` adds UTM 31N as a defensible alternative for Paris. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — over-penalised correct-geometry-wrong-CRS submissions previously sank to 0; new policy charges 1 point for a meaningful-set pick and 2 for outside the meaningful set. Explicit and well-reasoned. |
| 2026-06-06 | b0bc006 | mixed (prompt-change + grader-change + reference-change + tests-change + docs-change) | Output format flipped from GeoJSON to GeoPackage. `task.json` instruction fully rewritten in house style; `expected_outputs[0]` switched to `format: gpkg`, `geometry_type: Polygon` pinned. New `analyst_notes` field added. `task.json.version` bumped 1→2. `grade.py` switched to `.gpkg` filename and reads via geopandas. `reference/solution/generate.py` and `reference/failures/_make_brokens.py` updated to write GPKG and fix pre-existing `TASK_DIR` path math. Reference output and all three broken outputs regenerated. `README.md` rewritten for GeoPackage and refreshed scores. `metadata.yaml > broken_solutions.measured_score` refreshed: `wrong_format` 0.0→0.8, `wrong_crs` 0.5→0.6, `wrong_attributes` 0.875→0.9. `coverage.yaml > formats_out` updated to `[gpkg]`. `visualize.py` `src_filename` switched to `.gpkg`. | Commit msg: "Migrate crs-l1-paris-lambert93 output to GeoPackage and rewrite prompt" — explicit: GeoPackage is the canonical native container for projected vector data and embeds the CRS in the file itself; this avoids RFC 7946's WGS84-mandate conflict with the Lambert-93 output. Clean, well-reasoned single-commit migration. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-06T14:05:42+00:00 (commit `b0bc006`, class: mixed — prompt-change + grader-change + reference-change + tests-change). This commit changes the output filename, the output format, the grader, the reference, and the broken sets simultaneously, so it invalidates all prior runs as evidence on the current task.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| (no runs after cutoff) | — | — | — | — | — |

Stale (pre-cutoff) runs: 41 prior run dirs include `crs-l1-paris-lambert93`. The six most recent (`run-20260606-0942Z` … `run-20260606-1334Z`, all openrouter-gemma4-26b-detailed, started 09:53Z–13:36Z on 2026-06-06) scored 1.0 against the old `.geojson` grader and contract — they pre-date the `b0bc006` cutoff at 14:05Z by hours and are not evidence on the current `.gpkg` task. Earlier stale runs (2026-05-12 → 2026-05-28) span claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-6, deepseek-v4-flash, tencent/hy3-preview, and gemma4-26b. Most scored 1.0 on the old contract; a handful are model-side failures (network errors, `cancelled`). None are valid evidence on the current prompt or grader.

#### Verdict
**insufficient-evidence**

No runs have been executed against the current `.gpkg` task and the softened CRS grader. The diagnostic part of Step 2 stops here as the prompt directs: "no current runs available". The internal cross-checks that do not require runs all pass:

- Grader on the (newly regenerated) reference: 1.0, 10/10 subchecks, IoU 1.000000, total-area rel diff 0.0000%.
- Grader on broken sets: `broken_wrong_format` 0.8 (within metadata range [0.75, 0.85]), `broken_wrong_crs` 0.6 (within [0.5, 0.7]), `broken_wrong_attributes` 0.9 (within [0.85, 0.95]). All three measured scores match `metadata.yaml > broken_solutions.measured_score` exactly.
- Step 2c-CRS check: reference output (`paris_buildings_lambert93.gpkg` in EPSG:2154), `expected_outputs[].crs` (EPSG:2154), `expected_outputs[].format` (`gpkg`), README's stated output (`outputs/paris_buildings_lambert93.gpkg` in EPSG:2154), instruction's stated output (`paris_buildings_lambert93.gpkg`), and the grader's `OUTPUT_NAME` (`paris_buildings_lambert93.gpkg`) all agree. The grader uses `grade_crs_soft` to reproject the submission to EPSG:2154 for the geometric subchecks, and the same metric CRS is the reference's native CRS — a symmetric comparison, not one-sided.
- Step 4 unilateral-edit triggers all checked and ruled out (details below).

Since the diagnostic verdict is `insufficient-evidence` purely on run-state grounds — not on any concrete reason to suspect grader miscalibration — no `grader-miscalibration-suspected` flag is raised. The orchestrator should re-evaluate this task after at least two `current` runs from meaningfully distinct model families exist.

Step 4 unilateral-edit triggers checked and ruled out:
- *GeoJSON-CRS strip* — does not apply: output is GeoPackage now (`expected_outputs[0].format: gpkg`); GeoPackage embeds CRS in the file, so no RFC 7946 friction. The instruction contains no EPSG, WGS84, or 4326 mentions to strip — `b0bc006` already cleaned these. Grep confirms no remaining CRS literals in `task.json.instruction`.
- *Tighten redundant statements* — examined and rejected. The instruction is one paragraph with: (1) the why, (2) the ask plus the four constraints (attributes alone, Polygon not MultiPolygon, GeoPackage to `paris_buildings_lambert93.gpkg`, `id` as the key). The Polygon/MultiPolygon wording encodes a non-mutation invariant the grader's `geometry_type_is_polygon` subcheck enforces; `expected_outputs[].geometry_type: Polygon` alone does not encode it because the structural gate accepts both Polygon and MultiPolygon. The "attributes alone" wording is the value-preservation phrasing; `original_columns_preserved` and `identifying_attributes_preserved` are two distinct grader checks. No redundancy to strip.
- *Strip a clear gift from the instruction* — does not apply: the EPSG code, the CRS name (Lambert-93 in prose), the input CRS, the algorithm name, and the input column list have all already been stripped (commits `d5c283d`, `b4583b4`, `b0bc006`). The residual cues are "standard official projection for the Paris region" (category-level hint, per Step 4's CRS accept-list refactor guidance), the output filename `paris_buildings_lambert93.gpkg` (I/O contract), and the constraint "keep every geometry as a plain Polygon" (non-mutation invariant). All are necessary information.
- *House-style rewrite* — does not apply: `b0bc006` just rewrote the instruction in house style. Re-reading: opens with the purpose ("Our heat-loss model won't accept..."), then the ask ("Can you convert..."); full sentences; no em-dashes; jargon-free; concrete filename; no CRS mention; persona/context preserved. Compliant.
- *Author or refresh `analyst_notes`* — does not apply: `b0bc006` just authored `analyst_notes` with description, approach (five steps, imperative voice, no library names), and pitfalls (five full sentences). Re-reading against the schema: description states the hidden gotcha ("the prompt deliberately uses the category-level hint 'standard official projection for the Paris region' instead of naming the EPSG"); approach is high-level prose; pitfalls cover hidden gotcha first (UTM-zone vs Lambert-93, Web Mercator) then mundane mistakes (Polygon → MultiPolygon round-trip, dropped columns, wrong output format). Compliant.
- *CRS accept-list refactor* — already implemented. `grade.py` uses `grade_crs_soft(sub, MEANINGFUL_EPSGS={2154, 32631}, CANONICAL_EPSG=2154)`, which (a) Gate-1-accepts any usable CRS, (b) reprojects to canonical for downstream subchecks, and (c) docks via `crs_is_canonical` (canonical only) and `crs_in_meaningful_set` (canonical or UTM 31N). The instruction's "standard official projection for the Paris region" is the category-level hint Step 4 prescribes (national grid family, not naming the EPSG, not naming the datum, not enumerating alternatives). Compliant.
- *Loosen a grader tolerance* — does not apply: no correct-looking output rejected by drift (no current runs to inspect, and the reference grades to 1.0).
- *Tighten a grader subcheck* — does not apply: every broken set scores in its declared range.
- *Refresh `broken_solutions > measured_score`* — does not apply: re-run scores (0.8 / 0.6 / 0.9) match `metadata.yaml` exactly. `b0bc006` already refreshed these.
- *Vocabulary slug add* — does not apply: `coverage.yaml` slugs all validate against `coverage-vocabulary.yaml`. `formats_out: [gpkg]` matches the migrated contract.

No prompt/grader/tolerance/input edit applied this pass, so no `task.json.version` bump is required (current value `2`, set by `b0bc006`).

#### Specific findings
- Instruction voice, persona-as-author compliance, and house-style rules all comply with `task-design-prompt.md`. No edit proposed.
- Tolerances in `metadata.yaml` (count_pct 0.05, area_pct 0.01, jaccard_min 0.95, geom_eps_m 0.001) match the projection-accuracy rationale in `author-context.md`. No edit proposed.
- Reference output is byte-stable on the regenerated GPKG: current grader run yields IoU 1.000000 and 0.0000% total-area diff. No edit proposed.
- `coverage.yaml` slugs validate against `coverage-vocabulary.yaml`; `formats_out: [gpkg]` correctly captures the migration. Re-emitted with a fresh `evaluator_run_at` timestamp; values unchanged from the prior evaluator block aside from the format flip (which `b0bc006` already applied to `coverage.yaml`).
- The inventory row (`benchmark/authoring/inventory.md`, lines 339–362) still lists `Format out: GeoJSON` and the output artifact `paris_buildings_lambert93.geojson`. The `b0bc006` migration to GeoPackage did not update the inventory. <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Inventory and current `task.json`/`expected_outputs[]`/README disagree on the output format (inventory: GeoJSON / `.geojson`; current task: GeoPackage / `.gpkg`). Inventory edit is outside this evaluator's lane; a human should update inventory.md lines 350 and 360 to match the current contract.
- HR-002 — design-rationale carry-forward — Commit `b4583b4` (2026-05-17) removed the explicit EPSG:2154 and Lambert-93 names from the instruction; rationale inferable from `instruction-stripping-guide.md` but not stated in the commit message itself. Three prior evaluator blocks have flagged this. Low severity — current behaviour consistent with documented policy and the `b0bc006` rewrite preserves the same category-level-hint phrasing.

### 3. Changes applied this run

#### Unilateral edits
(none — `b0bc006` already applied the GPKG migration, the house-style rewrite, the `analyst_notes` author, the `measured_score` refresh, and the `coverage.yaml` format flip in a single coherent commit; no follow-up unilateral edit is justified.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — `benchmark/authoring/inventory.md` (lines 339–362) still records Format out: GeoJSON / `paris_buildings_lambert93.geojson`, contradicting the migrated `.gpkg` contract introduced by `b0bc006`. Human edit required (file is outside the task dir). Low severity — discoverability for the matrix script may be affected if the inventory is also consumed downstream.
- HR-002 — design-rationale — Commit `b4583b4` (2026-05-17) stripped the explicit EPSG:2154 and Lambert-93 names from the instruction; commit message does not explicitly justify, rationale inferred from `instruction-stripping-guide.md`. Carried forward from three prior evaluator blocks. Low severity.

#### Tests run
- grader on reference (`reference/solution/outputs/`): 1.0 (10/10 subchecks; IoU 1.000000; total-area rel diff 0.0000%)
- grader on `broken_wrong_format`: 0.8 (matches `metadata.yaml > measured_score 0.8`, in range [0.75, 0.85])
- grader on `broken_wrong_crs`: 0.6 (matches `metadata.yaml > measured_score 0.6`, in range [0.5, 0.7])
- grader on `broken_wrong_attributes`: 0.9 (matches `metadata.yaml > measured_score 0.9`, in range [0.85, 0.95])
- pytest: pass (41/41 via `cd benchmark/eval && uv run pytest`)


---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geom-type Polygon-family check from Gate 2 dropped — already covered
  (more strictly) by the existing `geometry_type_is_polygon` subcheck.
- Feature-count-within-5%-of-reference migrated from Gate 2 to a new
  `feature_count_within_5_percent` subcheck.
- Subcheck count grew from 10 to 11.

### Verification
- Reference solution re-graded: 1.0 (11/11 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
L1 CRS-reprojection task: a small bundled WGS84 GeoJSON of Paris (Marais) building footprints is reprojected into RGF93 / Lambert-93 (EPSG:2154), polygon-only, attributes verbatim. Persona Camille Roux (IGN cadastre intern) prepares a sample for a downstream heat-loss model that refuses lat/lon (`benchmark/authoring/inventory.md`, lines 339-362). Full pre-2026-06-06 history is reconstructed in the four prior evaluator blocks; this block covers the two project-wide grader passes that landed since the 2026-06-06 review.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 99394fe | docs-change (evaluator artefacts) | Prior evaluator block + coverage.yaml + status.json. Verdict insufficient-evidence; 2 low flags. | Commit msg: "Re-evaluate crs-l1-paris-lambert93: insufficient-evidence, 2 flags (low)". |
| 2026-06-06 | 363aed2 | grader-change | Removed the `structural_correctness` gate from `grade.py`: the count-within-5% check migrated from Gate 2 to a new `feature_count_within_5_percent` subcheck, the Gate-2 Polygon-family check was dropped (already covered more strictly by `geometry_type_is_polygon`), subcheck count 10 -> 11. Documented in the "Manual cleanup 2026-06-06" section above. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" - Gate 2 was inconsistent across the 36 graders; shape-recoverable inputs now cost a point instead of collapsing to 0. Explicit and well-reasoned. |
| 2026-06-07 | 05b389b | grader-change | Re-tagged six data-content subchecks with `weight=3.0` (`feature_count_within_5_percent`, `feature_id_set_preserved`, `geometry_iou_high`, `per_feature_area_matches`, `total_area_within_1_percent`, `identifying_attributes_preserved`); schema/structural checks (envelope, geometry type, column presence, both CRS subchecks) keep weight 1.0. Total weight 11 -> 23. `metadata.yaml > broken_solutions` was *not* refreshed in this commit. | Commit msg: "Weight data-content subchecks 3x in CRS graders" - a clean-schema-wrong-data submission should score visibly lower than a correct-data slightly-off-schema one. Explicit. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:28:18+00:00 (commit `05b389b`, class: grader-change - the 3x data-content weighting). The earlier Gate-2 removal (`363aed2`, 2026-06-06T20:11Z) is also design-affecting but is superseded by the later commit.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | deepseek/deepseek-v4-flash | 2026-06-09T06:50:45Z | 1.0 | done | current (suite `6510297` includes `05b389b`; task version 2) |
| run-20260609-084636Z | deepseek/deepseek-v4-flash | 2026-06-09T08:50:33Z | 1.0 | done | current (suite `ec540aa` includes `05b389b`; task version 2) |

Stale (pre-cutoff) runs: 28 further run dirs include this task. `run-20260606-1733Z` (gemma-4-26b, 1.0) ran against the post-GPKG contract but pre-dates both grader passes; `run-20260607-112430Z` (gemma-4-26b, 1.0, suite `06fd6c0`) pre-dates the weighting commit. All 26 older runs (2026-05-12 -> 2026-06-06) were already classified stale by prior evaluator blocks (GPKG migration `b0bc006` invalidated everything before 2026-06-06T14:05Z).

#### Verdict
**insufficient-evidence**

Only two `current` runs exist and both come from one agent family (deepseek-v4-flash), which meets the prompt's insufficient-evidence bar regardless of their scores. Both runs are clean: 330 features, EPSG:2154, Polygon-only, schema `id, class, subtype, name, height, num_floors`, exact filename, score 1.0 under the weighted grader. No evidence of too-strict or too-easy behaviour; the task needs current runs from at least one more model family before a calibration verdict is possible.

Static checks (2c-CRS, 2c-INFO, 2c-REF) all run regardless:

- 2c-CRS: reference output (`paris_buildings_lambert93.gpkg`, EPSG:2154), `expected_outputs[]` (`gpkg`, EPSG:2154, Polygon), README, instruction filename, and grader `OUTPUT_NAME` all agree. `grade_crs_soft` normalizes the submission to the canonical EPSG:2154 per the declared accept-list policy (`MEANINGFUL_EPSGS = {2154, 32631}`, canonical 2154) - a one-sided reprojection implementing a declared accept-list, which Step 2c-CRS explicitly permits. The reference is natively EPSG:2154, so all metric comparisons are symmetric.
- 2c-REF: `reference/solution/generate.py` is faithful - read, `to_crs(EPSG:2154)`, write GPKG, attributes untouched. The defensive `sort_values("id")` is determinism plumbing on an input already sorted by id (a no-op on the data; all grader checks are order-independent), not a semantic deviation. No flag.
- One re-measured mismatch (now fixed, see below): `metadata.yaml > broken_solutions` still carried the pre-weighting scores 0.8 / 0.6 / 0.875-era ranges; the current grader yields `broken_wrong_format` 0.913, `broken_wrong_crs` 0.565, `broken_wrong_attributes` 0.957.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `paris_buildings_lambert93.gpkg`, GeoPackage | instruction ("Write the result as a GeoPackage to ...") | stated |
| usable CRS declared in the file | inferable (GPKG embeds CRS by format convention) | inferable |
| feature count within 5% / id set preserved (Jaccard >= 0.95) | instruction ("convert the buildings over", "use `id` as the key") | stated/inferable |
| coordinates actually in Lambert-93 metres (envelope, IoU, areas) | instruction ("coordinates in metres using the standard official projection for the Paris region") | inferable (regional convention -> EPSG:2154; filename `lambert93` is the contractual hint) |
| geometry stays Polygon (no MultiPolygon upcast) | instruction ("keep every geometry as a plain Polygon rather than turning it into a MultiPolygon") | stated |
| attributes/columns preserved (`class`, `subtype`, `name`, `height`, `num_floors`) | instruction ("leave the attributes alone") | stated |
| `crs_is_canonical` EPSG:2154 | category-level hint ("standard official projection for the Paris region") + filename | inferable |
| `crs_in_meaningful_set` {2154, 32631} | grader-internal accept-list | inferable (defensible-alternative policy; passing it requires no extra knowledge beyond the canonical pick) |

Factual claims verified: the bundled input exists (`inputs/paris_buildings_wgs84.geojson`, 330 features, EPSG:4326, Polygon-only - "in lat/lon" is accurate); output filename consistent across instruction / `expected_outputs[]` / grader / reference / brokens; column names in the reference schema match the input verbatim. The instruction's "the `paris_buildings` file" matches `inputs[].name` (`paris_buildings`) rather than the literal filename; both current runs located the file without friction, and the literal filename would leak the input CRS ("wgs84"), so the looser reference is acceptable as a deliberate omission.

#### Reference faithfulness
Faithful. `generate.py` does exactly the asked-for reprojection with attributes passed through; the only extra operation is a stable sort by `id` for byte-determinism of the committed artefact, which is a no-op on the already-sorted input and invisible to every grader check.

#### Specific findings
- `metadata.yaml > broken_solutions` was stale after the two grader passes: measured 0.913 / 0.565 / 0.957 vs recorded 0.8 / 0.6 / 0.9, with `wrong_format` (0.913 vs range [0.75, 0.85]) and `wrong_attributes` (0.957 vs [0.85, 0.95]) outside their declared ranges. Refreshed unilaterally (measured_score, ranges, and the score arithmetic inside the descriptions; total weight is now 23). No version bump - `broken_solutions` is audit metadata, not the grading contract.
- The 3x weighting dilutes the CRS deduction that is this CRS task's central skill: a submission that never reprojects at all (`broken_wrong_format`) loses only the two weight-1 CRS subchecks (2/23) and scores 0.913, and a dropped-columns submission scores 0.957 - both within a few points of a perfect run. Score ordering across failure classes is still monotone and sensible (1.0 > 0.957 > 0.913 > 0.565), but the separation between "skipped the core operation" and "perfect" has shrunk from 0.2 to 0.087 as a side effect of `05b389b` keeping CRS subchecks at weight 1.0 while tripling data-content checks that `grade_crs_soft`'s normalization makes pass regardless of the agent's CRS choice. <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="med" --> A human should decide whether the two CRS subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) in CRS-category tasks should also carry weight 3.0 (or similar) so that the category's central skill is not the cheapest thing to fail. This is a deliberate project-wide policy from `05b389b` applied to all CRS graders, so the fix (if any) should be applied consistently across the family rather than unilaterally here; a grader weight change would require a `version` bump per task.
- README's failure-mode section referenced the removed Gate 2 and the pre-weighting scores (0.6 / 0.9 / 0.8). Fixed unilaterally (docs-change, no bump).
- Inventory row (`benchmark/authoring/inventory.md`, lines 339-362) still records Format out: GeoJSON and output artifact `paris_buildings_lambert93.geojson`, contradicting the `.gpkg` contract from `b0bc006`. Carried forward. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Human should update the inventory row (Format out and the output-artifacts bullet) to GeoPackage / `paris_buildings_lambert93.gpkg`; the file is outside this evaluator's lane.
- Commit `b4583b4` (2026-05-17) stripped explicit EPSG:2154 / Lambert-93 names from the instruction without stating why in the message; rationale inferable from `instruction-stripping-guide.md`. Carried forward from four prior blocks. <!-- HUMAN-REVIEW id="HR-003" category="design-rationale" severity="low" --> Low severity - behaviour is consistent with documented stripping policy.
- Step 4 triggers otherwise checked and ruled out: instruction already house-style compliant (rewritten in `b0bc006`), `analyst_notes` present and schema-compliant, no redundant statements (the Polygon non-upcast and attributes-alone phrasings each pin a constraint `expected_outputs[]` does not), CRS accept-list refactor already implemented in `grade.py`, no tolerance drift observed, coverage slugs all validate.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions` (measured_score 0.8/0.6/0.9 -> 0.913/0.565/0.957, ranges and description arithmetic updated for the 23-point weighted grader). Re-grade on reference: 1.0. Reason: `363aed2` + `05b389b` changed the grader without refreshing the recorded broken-set scores; two of three were outside their declared ranges.
- `README.md`: replaced the stale "Gate 2's count tolerance" reference with the `feature_count_within_5_percent` subcheck and updated the weak-agent score comparison (0.6/0.9/0.8 -> 0.57/0.96/0.91). Re-grade on reference: 1.0. Reason: docs drifted from the current grader structure.

No `task.json.version` bump: neither edit touches the instruction, grader, tolerances, or inputs (current version stays 2).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 - grader-miscalibration-suspected - 3x data-content weighting dilutes the CRS deduction in CRS-category tasks; "never reprojected" now scores 0.913. Family-wide policy call.
- HR-002 - inventory-mismatch - inventory.md still records GeoJSON output for this task (carry-forward).
- HR-003 - design-rationale - commit `b4583b4` rationale not stated in message (carry-forward).

#### Tests run
- grader on reference (`reference/solution/outputs/`): 1.0 (11/11 subchecks)
- grader on `broken_wrong_format`: 0.913 (matches refreshed `metadata.yaml`)
- grader on `broken_wrong_crs`: 0.565 (matches refreshed `metadata.yaml`)
- grader on `broken_wrong_attributes`: 0.957 (matches refreshed `metadata.yaml`)
- pytest: pass (41/41 via `cd benchmark/eval && uv run pytest`)

---

## Grader recalibration 2026-06-14  (evaluator-commit <pending>)

### Change
Per-task reasoned CRS-dominant subcheck weights replace the project-wide
05b389b 3x data-content weighting. This is a CRS-selection-primary task,
so CRS-correctness now dominates the score budget. Crucially, the
high-weight CRS group is the set of checks that prove the reprojection
*actually happened* (the two CRS-declaration subchecks **and** the
Lambert-93 envelope, which is functionally a transform-proof check), not
merely the metadata-declaration label. Grading-only change; no
`task.json.version` bump (current version stays 2). This resolves the
prior block's HR-001 (`grader-miscalibration-suspected`): a never-reproject
submission no longer scores 0.913.

### Weight changes (subcheck: old -> new)
| Subcheck | Class | old | new |
|---|---|---|---|
| `feature_count_within_5_percent` | data-content | 3.0 | 1.0 |
| `feature_id_set_preserved` | data-content | 3.0 | 1.0 |
| `identifying_attributes_preserved` | data-content | 3.0 | 1.0 |
| `coordinates_within_lambert93_paris_envelope` | CRS-correctness (transform proof) | 1.0 | 5.0 |
| `crs_is_canonical` | CRS-declaration | 1.0 | 5.0 |
| `crs_in_meaningful_set` | CRS-declaration | 1.0 | 5.0 |
| `geometry_iou_high` | CRS-correctness | 3.0 | 3.0 (unchanged) |
| `per_feature_area_matches` | CRS-correctness | 3.0 | 3.0 (unchanged) |
| `total_area_within_1_percent` | CRS-correctness | 3.0 | 3.0 (unchanged) |
| `geometry_type_is_polygon` | structural | 1.0 | 1.0 (unchanged) |
| `original_columns_preserved` | structural | 1.0 | 1.0 (unchanged) |

Total weight: 23 -> 29.

### Broken scores (before -> after)
| Broken | Failing subchecks | before | after | Severity note |
|---|---|---|---|---|
| reference (correct) | none | 1.000 | 1.000 | unchanged; >= 0.95 |
| `wrong_attributes` | `original_columns_preserved` (w1) | 0.957 | 0.966 | cosmetic — near top, only a structural column-presence check fails |
| `wrong_format` (honest, never reprojected, labeled 4326) | `crs_is_canonical` + `crs_in_meaningful_set` (w5+w5) | 0.913 | 0.655 | substantial drop — the core CRS pick is wrong; geometry passes only because the grader reprojects it |
| `wrong_crs` (silent corruption: 2154 stamped, degrees coords) | envelope (w5) + IoU + per-feat-area + total-area (w3 each) | 0.565 | 0.517 | substantial drop — passes the declaration labels but fails every transform-proof check |

Ordering is monotone and sensible: 1.000 > 0.966 > 0.655 > 0.517. The
silent-corruption/honest-unprojected **inversion is avoided**: `wrong_crs`
(0.517) scores *below* `wrong_format` (0.655). This holds precisely
because the envelope check is weighted as a CRS-correctness check
(weight 5) rather than left at weight 1 — up-weighting only the two
CRS-declaration labels would have rewarded the silent-corruption file
(which passes both labels) over the honest miss, the inversion called
out in the prior HR-001.

### Prior-run re-grade summary
The two `current`-validity runs at task version 2 listed in the
2026-06-11 block (`run-20260608-074701Z`, `run-20260609-084636Z`, both
deepseek-v4-flash) are bit-correct reprojections; re-graded under the new
weights both stay 1.0 (recorded 1.0 -> 1.0, no shift — every subcheck
passes, so reweighting cannot move a perfect score). No other current
runs exist (stale pre-2026-06-06 / pre-weighting runs invalidated by the
GPKG migration and grader passes per prior blocks). No notable shifts.

### Reasoning
The 05b389b pass bluntly tripled "data-content" subchecks across every
grader and left CRS-declaration at weight 1, which for a CRS-primary task
made the category's central skill the cheapest thing to fail (a
never-reproject submission scored 0.913). The fix weights the two
CRS-declaration checks and the transform-proof envelope at 5, keeps the
geometric transform checks (IoU, per-feature area, total area) at 3, and
drops the count/id-set/attributes content checks to 1. Treating the
envelope as a high-weight CRS-correctness check is what makes both CRS
brokens lose heavily while keeping the silent-corruption file below the
honest-unprojected file. Thresholds, gates, and check logic are
unchanged; only `weight=` values moved.

### Tests run
- grader on reference (`reference/solution/outputs/`): 1.0 (11/11 subchecks)
- grader on `broken_wrong_format`: 0.655 (matches refreshed `metadata.yaml`)
- grader on `broken_wrong_crs`: 0.517 (matches refreshed `metadata.yaml`)
- grader on `broken_wrong_attributes`: 0.966 (matches refreshed `metadata.yaml`)
- pytest: not run (orchestrator runs the suite)
