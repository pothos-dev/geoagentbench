# Implementation notes — dc-l1-bangkok-attribute-coercion

## Status
completed

## Summary
L1 data-cleaning task: 100 Bangkok rail-station-mounted air-quality
sensor stations with every numeric column serialised as a JSON string
→ properly typed GeoJSON (`station_id` int; `sensor_value`,
`pm25_ug_m3`, `elevation_m` float; Thai-script `name_th` preserved
verbatim). Reference, grader, and three broken solutions built and
verified inside the project Docker container.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - no_coercion: 0.5555555555555556 (expected range [0.5, 0.6])
  - partial_coercion: 0.8888888888888888 (expected range [0.85, 0.92])
- Second-run output match: bit-identical (verified via `cp` + `diff -q`)
- Library tests after task: pass

## Failure-mode coverage
- Forget to coerce — pass the file through unchanged: broken_no_coercion
- Coerce floats but forget station_id: broken_partial_coercion
- Drop one of the required attribute columns: broken_wrong_format
- Coerce numeric values incorrectly (lossy parse): principled —
  `numeric_values_preserved` subcheck (relative tolerance 1e-3,
  per-cell pass-rate ≥ 0.99)
- Mangle the Thai `name_th` script via a non-UTF-8 stage: principled —
  `name_th_preserved_verbatim` subcheck (per-id exact-match rate ≥ 0.95)
- Edit the point coordinates: principled —
  `geometry_preserved_per_id` subcheck (per-id coordinate epsilon 1e-6°)
- Re-orient and accidentally change CRS: principled — Gate 1's
  `crs.to_epsg() == 4326` check
- Drop or duplicate features: principled — Gate 2 ±5% count tolerance
  + `station_id_set_preserved` Jaccard + `feature_id_set_via_geopandas`

## Open issues
- [severity: low] — Bundled input is hand-crafted because the defect
  under test (every numeric column serialised as a JSON string) does
  not exist in clean upstream data. The geographic anchor is a
  curated list of real Bangkok BTS / MRT / Airport Rail Link
  stations; the per-row sensor readings are closed-form functions of
  the row index. This follows AUTHOR_CONTEXT.md's permission for
  hand-crafted inputs when the task is *about* a malformed file.
  Documented in `data/_prepare_input.py`'s docstring and
  `metadata.yaml > notes`.

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — task uses `count_within_tolerance` and
`feature_set_equality_by_id` from the shared library. The four
type-checking subchecks parse raw JSON inline because JSON-type
inspection (string vs int vs float) is a primitive Python operation
that does not warrant a `geo_grading` helper given only one task
currently needs it.)

## Runtime
~20 minutes (peer tasks `dc-l1-tokyo-ring-orientation` and
`dc-l1-capetown-waterway-nulls` provided clear conventions for the
gate / subcheck split, the json-dump-for-determinism pattern, and the
broken-solution layout).

---

## Evaluator review 2026-05-26  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
A pure L1 data-cleaning task probing **attribute type coercion**. The bundled
GeoJSON of 100 Bangkok BTS / MRT / Airport Rail Link rail-mounted air-quality
sensor stations arrives with every numeric column (`station_id`,
`sensor_value`, `pm25_ug_m3`, `elevation_m`) serialised as a JSON *string*
rather than a JSON *number*. The agent must rewrite the file so the four
fields have proper JSON numeric types (int for the ID, floats for the
measurements) while preserving the Thai-script `name_th` column and the
point geometry. Output is GeoJSON in EPSG:4326. Persona: Suda Pongpan of
the Bangkok Metropolitan Administration; symptom: dashboard means come back
as NaN because the client-side `parseFloat` silently drops stringified
values mixed with Thai-script strings. Author block in this file plus the
initial commit `d570041` define the contract; inventory row (line 854 of
`benchmark/authoring/inventory.md`) corroborates the same axis values.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | d570041 | initial-authoring | Initial task — task.json, grade.py (9 subchecks + 2 gates), metadata.yaml (tolerances + 3 broken_solution measured scores), reference generate.py + outputs, three broken sets, hand-crafted `data/_prepare_input.py`, README. | (initial) |
| 2026-05-08 | fbd20f2 | docs-change | Repo split into thesis/, benchmark/, references/; task moved under benchmark/eval/tasks/. | Commit msg: "restructure: split repo into thesis/ benchmark/ references/" |
| 2026-05-08 | 001e459 | docs-change | benchmark/ split into authoring/ and eval/ subtrees. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-12 | ca819c8 | docs-change | Added visualize.py for every geometry-producing task. | Commit msg: "eval: add visualize.py for every geometry-producing task" |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" bullet list (CRS, geometry, required properties, type assertions). | Commit msg: "declare exact output schema in prompts to match graders" — closing the implicit-contract gap. |
| 2026-05-13 | 284b843 | docs-change | Added `tags{}` block (region, data_source, formats, crs, geometry_type, operations, themes, quality_issues, scale). Tags are metadata, not part of the prompt seen by the agent. | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ to benchmark/tasks/. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md. | Commit msg: "add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated image.webp. | Commit msg: "generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell. | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2. | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-13 | 4f0cfc0 | prompt-change | Folded the structured "Output schema:" bullet list into a single prose paragraph; same technical requirements preserved (Point geometry, station_id JSON integer, name_th preserved verbatim, three floats as JSON numbers). | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | f5d1e91 | prompt-change | Replaced specific defect description ("every numeric column as a JSON string — even station_id") with a symptom-based opener; dropped the explicit "Coerce sensor_value, pm25_ug_m3 and elevation_m to floats and station_id to integer" enumeration in favor of "Coerce all numeric properties to their appropriate JSON types (integers for IDs, floats for measurements)". | Commit msg: "Strip deducible information from DC task instructions" — removing column-name and per-column type instructions the agent can derive by inspecting the file. |
| 2026-05-15 | a78a513 | prompt-change | Dropped the parenthetical "(integers for IDs, floats for measurements)" — the agent must now derive that integers vs floats split from the data itself. | Commit msg: "Strip deducible information from DC task instructions (round 2)" |
| 2026-05-17 | 64740d0 | prompt-change | Larger rewrite: removed the "every numeric column as a JSON string" symptom-naming and the explicit "coerce to JSON types" directive. New instruction states the dashboard symptom (NaN averages) and asks the agent to "investigate the data and fix whatever is preventing the numeric computations from working correctly." Preserved: filename, CRS, format, Thai-script preservation, leave-geometry-and-strings-alone. | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" — symptoms over operations. |
| 2026-05-18 | f0c244a | grader-change | `crs_ok = sub.crs is not None and sub.crs.to_epsg() == 4326` replaced with `is_wgs84(sub.crs)` from the shared `geo_grading` package. Semantically equivalent (RFC 7946 absent-CRS now also passes; reference output has explicit CRS, so reference still scores 1.0). | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + minor grader-change) | Folder reorg: IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, data/→inputs/, reference/{generate.py,outputs/}→reference/solution/, tests/→reference/failures/. grade.py REFERENCE_OUT path updated; logic unchanged. task.json input URL updated to point to `tasks/dc-l1-.../inputs/...`. | Commit msg: "Reorganize task folder layout" — path-only refactor; answer key, grader logic, instruction, and reference output bytes are unchanged. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit `29a9ae3`, class: mixed — strictly a grader-change because grade.py was touched, but the touch was a path refactor with no semantic change to the answer key or grader logic).
- Most-recent *semantic* prompt-change: 2026-05-17T12:48:43Z (commit `64740d0`, prompt-change).
- Most-recent *semantic* grader-change: 2026-05-18T06:35:57Z (commit `f0c244a`, is_wgs84 consolidation — behaviour-preserving).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:13:57Z | 0.889 | done | stale (pre-cutoff by 1h38m, but only the path-refactor commit moved the cutoff; the run exercised identical grader logic and identical instruction) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:39:19Z | 0.889 | done | stale (pre is_wgs84 consolidation) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:07:48Z | 1.000 | done | stale |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T07:52:14Z | 0.889 | done | stale (pre `64740d0` semantic prompt-change) |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T03:12:49Z | 1.000 | done | stale |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T01:47:55Z | 1.000 | done | stale |
| run-20260516-2248Z | claude-code-opus-basic | 2026-05-16T23:31:21Z | 1.000 | done | stale |
| run-20260516-1130Z | claude-code-opus-basic | 2026-05-16T19:59:57Z | 1.000 | done | stale |
| run-20260516-0743Z | claude-code-opus-basic | 2026-05-16T07:57:03Z | 1.000 | done | stale |
| run-20260515-2053Z | claude-code-opus-basic | 2026-05-15T21:03:54Z | 1.000 | done | stale |
| run-20260515-0926Z | openrouter-deepseek-v4-flash-basic | 2026-05-15T10:52:16Z | 0.333 | done | stale |
| (~14 earlier runs) | (mix of opus/sonnet/haiku/deepseek/hy3/gemma) | 2026-05-12 .. 2026-05-15 | 0.0 .. 1.0 | mostly done | stale (pre semantic prompt-changes) |

No `current` run by the strict cutoff rule.

#### Verdict
**insufficient-evidence (strict) / calibrated (lenient)**

Strict reading: the only run after the path-refactor cutoff started 1h38m before the commit, so by the letter of the spec there are zero current runs and the verdict must be `insufficient-evidence`. However, the cutoff commit `29a9ae3` was a path refactor with no behavioural change to the grader or answer key; the latest run (`run-20260526-0748Z`, gemma4-26b, score 0.889) exercised an identical instruction, identical grader logic, and identical reference bytes. Under the lenient reading, the task is well-calibrated:

- The reference output scores 1.0 on the current grader (re-verified this run).
- All three broken solutions re-grade to their documented scores (0.0, 0.5556, 0.8889 — exact match with `metadata.yaml > broken_solutions > measured_score`).
- The latest stale-but-behaviourally-equivalent run lands in the documented `partial_coercion` regime (0.889): the model coerced the three measurement floats but left `station_id` un-integerised. That's exactly the failure mode the grader's `station_id_is_integer` subcheck is designed to detect — and the instruction (which deliberately no longer enumerates which columns to coerce) tests whether the agent inspects the data closely enough to spot the ID column too. Behaviour is as designed.
- Historical scores span the full sensible range (0.0, 0.333, 0.556, 0.889, 1.0) across model families of varying capability — the task discriminates.

The instruction has been progressively stripped of "nudges" through three rounds (`f5d1e91`, `a78a513`, `64740d0`); current state names neither the operation ("type coercion"), the affected columns, nor the int-vs-float split. What remains in the prompt — filename, output CRS, output format, Thai-script preservation, "leave string columns and the geometry alone" — is necessary information the agent cannot infer from format conventions alone. EPSG:4326 in the GeoJSON output is RFC 7946 by convention, but stating it explicitly is the project-wide convention for output-CRS specifications and is not a gift specific to this task.

#### Specific findings
- The reference grader on `reference/solution/outputs/` scores 1.0 (re-verified 2026-05-26).
- The three broken solutions re-grade to 0.0 / 0.5556 / 0.8889, matching `metadata.yaml > broken_solutions > measured_score` exactly — no `measured_score` update needed.
- The path-refactor cutoff at `29a9ae3` is technically a grader-change because grade.py was touched, but the touch was a single-line REFERENCE_OUT path update with identical semantics. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Strict reading of the evaluator-prompt cutoff rule classifies the latest run as stale, even though no behavioural change occurred between the run and the cutoff. Sweep-level guidance on whether path-only refactors should reset the cutoff would clarify many "completed-with-flags" verdicts across the sweep; until that is resolved, this task is flagged as insufficient-evidence on the strict reading. No action on the task itself.
- Author's `coverage.yaml` did not exist; written this run.

### 3. Changes applied this run

#### Unilateral edits
- (none — task is well-calibrated under both strict and lenient cutoff readings; no grader, instruction, or metadata change is justified by the evidence.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — sweep-level cutoff policy on path-only refactor commits.

#### Tests run
- grader on reference: 1.0
- grader on broken_wrong_format: 0.0
- grader on broken_no_coercion: 0.5556
- grader on broken_partial_coercion: 0.8889
- pytest (benchmark/eval): 35 passed

---

## Evaluator review 2026-05-27  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
A pure L1 data-cleaning task probing **attribute type coercion**. The bundled
GeoJSON of 100 Bangkok BTS / MRT / Airport Rail Link rail-mounted air-quality
sensor stations arrives with every numeric column (`station_id`,
`sensor_value`, `pm25_ug_m3`, `elevation_m`) serialised as a JSON *string*
(e.g. `"station_id": "1"`, `"sensor_value": "84.55"`) rather than a JSON
*number*. The agent must rewrite the file so the four fields have proper JSON
numeric types (int for the ID, floats for the measurements) while preserving
the Thai-script `name_th` column verbatim and leaving the point geometry
untouched. Output is GeoJSON in EPSG:4326. Persona: Suda Pongpan of the Bangkok
Metropolitan Administration; symptom: dashboard means come back as NaN because
the client-side `parseFloat` silently drops stringified values. The author
block above, the initial commit `d570041`, and the inventory row (line 854 of
`benchmark/authoring/inventory.md`) all corroborate the same axis values.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | d570041 | initial-authoring | Initial task — task.json (instruction enumerating the four columns + types), grade.py (2 gates + 9 subchecks), metadata.yaml (tolerances + 3 broken measured scores), reference generate.py + outputs, three broken sets, hand-crafted `data/_prepare_input.py`, README. | (initial) |
| 2026-05-08 | fbd20f2 | docs-change | Repo split into thesis/ benchmark/ references/; task moved under benchmark/eval/tasks/. | Commit msg: "restructure: split repo into thesis/ benchmark/ references/" |
| 2026-05-08 | 001e459 | docs-change | benchmark/ split into authoring/ and eval/ subtrees. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ to benchmark/tasks/. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md. | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated image.webp. | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated card image (FLUX schnell). | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated card image (nano-banana-2). | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-13 | 4f0cfc0 | prompt-change | Folded the structured "Output schema:" bullet list into one prose paragraph; technical requirements unchanged. | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | f5d1e91 | prompt-change | Replaced the explicit defect description and per-column enumeration with a more symptom-led opener (still named "coerce all numeric properties to JSON types"). | Commit msg: "Strip deducible information from DC task instructions" |
| 2026-05-15 | a78a513 | prompt-change | Dropped the parenthetical "(integers for IDs, floats for measurements)"; agent must now derive the int-vs-float split from the data. | Commit msg: "Strip deducible information from DC task instructions (round 2)" |
| 2026-05-17 | 64740d0 | prompt-change | Larger rewrite to the current symptom-only instruction: removed the "every numeric column as a JSON string" defect-naming and the "coerce to JSON types" directive; new text states the NaN-averages symptom and asks the agent to "investigate the data and fix whatever is preventing the numeric computations." Preserved: filename, CRS, format, Thai-script preservation, leave-geometry-and-strings-alone. (Verified against the d570041 baseline this run.) | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" |
| 2026-05-18 | f0c244a | grader-change | `crs_ok = sub.crs is not None and sub.crs.to_epsg() == 4326` → `is_wgs84(sub.crs)`. Diff confirmed: single-line substitution + import. Behaviour-preserving (reference has explicit CRS84, still scores 1.0). | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path-only grader-change) | Folder reorg: IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, data/→inputs/, reference/{generate.py,outputs/}→reference/solution/, tests/→reference/failures/. grade.py REFERENCE_OUT path string updated (diff confirmed: only the path constant changed); task.json input URL repointed to inputs/. No change to answer key, grader logic, instruction, or reference bytes. | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | faf89da | docs-change | Prior evaluator review committed (AUTHORING_HISTORY.md, coverage.yaml, audit/status.json). No task-file edits. | Commit msg: "Re-evaluate dc-l1-bangkok-attribute-coercion: calibrated, 1 low-severity flag" |

Note: a same-day commit `1f4a85c` ("Store bangkok/nyc-park reference output in WGS84, drop one-sided grader reproject") matched the slug grep but touches only `geo-l2-bangkok-landuse-intersect` and `geo-l2-nyc-park-symdiff` — its "bangkok" refers to the landuse task, not this one. It does **not** touch `dc-l1-bangkok-attribute-coercion` and is irrelevant to this task's cutoff.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37+02:00 == 2026-05-26T07:51:37Z (commit `29a9ae3`, class: mixed — counted as a grader-change because grade.py was touched, but the touch was a path-string refactor with no semantic change to grader logic or answer key).
- Most-recent *semantic* prompt-change: 2026-05-17T12:48:43Z (commit `64740d0`).
- Most-recent *semantic* grader-change: 2026-05-18T06:35:57Z (commit `f0c244a`, behaviour-preserving `is_wgs84` consolidation).

#### Runs considered
25 run directories exist under `benchmark/eval/runs/*/dc-l1-bangkok-attribute-coercion/`. Newest first; none started at/after the cutoff (2026-05-26T07:51:37Z).

| Run | Adapter / model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | google/gemma-4-26b-a4b-it | 2026-05-26T08:13:57Z | 0.889 | done | stale (started 1h38m before the path-refactor cutoff; identical grader logic, instruction, reference bytes) |
| run-20260517-1424Z | deepseek/deepseek-v4-flash | 2026-05-17T14:39:19Z | 0.889 | done | stale |
| run-20260517-1254Z | claude-opus-4-6 | 2026-05-17T13:07:48Z | 1.000 | done | stale |
| run-20260517-0614Z | deepseek/deepseek-v4-flash | 2026-05-17T07:52:14Z | 0.889 | done | stale |
| run-20260517-0304Z | deepseek/deepseek-v4-flash | 2026-05-17T03:12:49Z | 1.000 | done | stale |
| run-20260517-0134Z | claude-opus-4-6 | 2026-05-17T01:47:55Z | 1.000 | done | stale |
| run-20260516-2248Z .. run-20260514-0946Z | claude-opus-4-6 (×7) | 2026-05-14 .. 2026-05-16 | 1.000 | done | stale |
| run-20260515-0926Z | deepseek/deepseek-v4-flash | 2026-05-15T10:52:16Z | 0.333 | done | stale |
| run-20260513-0943Z | tencent/hy3-preview | 2026-05-13T09:49:12Z | 0.000 | done | stale |
| run-20260513-0922Z..0937Z | (no model) | 2026-05-13 | n/a | failed/cancelled — infra (ConnectError / missing OPENROUTER_API_KEY) | stale; model-side/infra, not task evidence |
| run-20260512-* (×5) | haiku / sonnet / deepseek | 2026-05-12 .. 2026-05-13 | 1.000 | done | stale (pre semantic prompt-changes) |

No `current` run by the strict cutoff rule.

#### Verdict
**insufficient-evidence**

By the letter of the cutoff rule, every run started before the 2026-05-26T07:51:37Z cutoff (the newest, gemma-4-26b, started 1h38m earlier), so there are zero `current` runs and the diagnostic verdict is `insufficient-evidence`. I have no concrete reason to suspect a calibration problem — so per the prompt I record "no current runs available" and do not raise a `grader-miscalibration-suspected` flag.

The cutoff was moved solely by commit `29a9ae3`, a path-only refactor (confirmed by diff: the grade.py change is a single REFERENCE_OUT path-string update). The latest stale run therefore exercised an identical instruction, identical grader logic, and identical reference bytes; under a pragmatic reading the task is well-calibrated:

- Reference output self-grades **1.0** on the current grader (all 2 gates + 9 subchecks pass; re-verified this run).
- All three broken solutions re-grade to **0.0 / 0.5556 / 0.8889**, matching `metadata.yaml > broken_solutions > measured_score` exactly — no `measured_score` update needed.
- Historical scores span the full sensible range (0.0, 0.333, 0.556, 0.889, 1.0) across model families of varying capability, so the grader discriminates. The 0.889 cluster is the documented `partial_coercion` regime (floats coerced, `station_id` left un-integerised) — exactly what the `station_id_is_integer` subcheck is built to catch.

Instruction calibration: three rounds of stripping (`f5d1e91`, `a78a513`, `64740d0`) removed the operation name, the affected column names, and the int-vs-float hint. What remains — output filename, output CRS (EPSG:4326), output format (GeoJSON), Thai-script preservation, and "leave string columns and the geometry alone" — is necessary information the agent cannot infer from format conventions alone. Stating EPSG:4326 is the project-wide output-CRS convention, not a task-specific gift. No `too-easy` gift remains to strip.

2c-CRS consistency: grader requires WGS84 via `is_wgs84(sub.crs)`; reference output is `urn:ogc:def:crs:OGC:1.3:CRS84` (= WGS84); `expected_outputs[].crs` is EPSG:4326; README states EPSG:4326. All four agree. The grader performs **no** reprojection of either side (the task is attribute-only). No one-sided reprojection, no CRS/README/reference mismatch. Consistent.

#### Specific findings
- Reference grader on `reference/solution/outputs/` scores 1.0 (re-verified 2026-05-27).
- Broken solutions re-grade to 0.0 / 0.5556 / 0.8889, matching `metadata.yaml` exactly — no edit needed.
- Input fixture confirmed: all six properties arrive as JSON strings (`station_id: "1"`, `sensor_value: "84.55"`, …), the exact defect under test.
- The strict cutoff verdict is `insufficient-evidence` purely because the only design-affecting commit since the last run was a path-only refactor `29a9ae3` that reset the cutoff without any behavioural change. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> A sweep-level policy on whether path-only refactor commits should reset the run-validity cutoff would resolve this and many sibling tasks; until then, no action on this task and a fresh run on the current layout would confirm the (lenient) calibrated reading. No task-file change is justified by the evidence.

### 3. Changes applied this run

#### Unilateral edits
- (none — task is well-calibrated under the pragmatic reading; the strict verdict is `insufficient-evidence` only because a path-only refactor reset the cutoff. No grader, instruction, or metadata change is justified.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — sweep-level cutoff policy on path-only refactor commits (a fresh run on the current layout would confirm calibration).

#### Tests run
- grader on reference: 1.0
- grader on broken_wrong_format: 0.0
- grader on broken_no_coercion: 0.5556
- grader on broken_partial_coercion: 0.8889
- pytest (benchmark/eval): 35 passed

---

## Evaluator review 2026-05-28  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior evaluator blocks: pure L1 data-cleaning task probing
**attribute type coercion**. The bundled GeoJSON of 100 Bangkok rail-mounted
air-quality sensor stations arrives with every numeric column
(`station_id`, `sensor_value`, `pm25_ug_m3`, `elevation_m`) serialised as
a JSON *string*; the agent must rewrite the file with proper JSON numeric
types (int for the ID, floats for the measurements) while preserving the
Thai-script `name_th` column and the point geometry. Persona Suda Pongpan,
NaN-averages symptom. Inventory row at `benchmark/authoring/inventory.md`
line 854 corroborates axis values.

#### Change log
Carrying forward the prior log; only new commits since the last evaluator
block are tabulated.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-27 | 3f8bf76 | docs-change | Prior evaluator-review block appended (AUTHORING_HISTORY.md, coverage.yaml, audit/status.json). No task-file edits. | Commit msg: "Re-evaluate dc-l1-bangkok-attribute-coercion: insufficient-evidence (no current runs; path-only refactor reset cutoff)" |
| 2026-05-28 | 622342b | docs-change | Repo-wide: `prompt_version: 2026-05-07-a` line removed from `metadata.yaml`. No tolerances, grader, instruction, or input change for this task. | Commit msg: "Add task content versioning; drop unused prompt_version" — removed unused metadata key; introduces `task.json.version` semantics. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T07:51:37Z (commit `29a9ae3`, class: mixed — counted because grade.py was touched, but the touch was a path-string refactor with no semantic change).
- The 2026-05-28 `622342b` commit removed `prompt_version` from `metadata.yaml`. That key is not referenced by the grader, runner, or any contract — confirmed unused (`grep -r prompt_version benchmark/eval/` returns nothing). Treated as a docs-change; **it does not reset the cutoff**.
- Most-recent *semantic* prompt-change: 2026-05-17T12:48:43Z (commit `64740d0`).
- Most-recent *semantic* grader-change: 2026-05-18T06:35:57Z (commit `f0c244a`, behaviour-preserving `is_wgs84` consolidation).

#### Runs considered
Four new runs since the last evaluator pass, all started after the
2026-05-26T07:51:37Z cutoff — for the first time, this task has `current`
runs by the strict rule.

| Run | Adapter / model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260527-2016Z | claude-code-opus-basic / claude-opus-4-7 | 2026-05-27T20:32:12Z | 1.000 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic / google/gemma-4-26b-a4b-it | 2026-05-27T23:35:31Z | 0.889 | done | current |
| run-20260528-0113Z | claude-code-opus-basic / claude-opus-4-7 | 2026-05-28T01:29:29Z | 1.000 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic / google/gemma-4-26b-a4b-it | 2026-05-28T03:23:44Z | 1.000 | done | current |

Stale runs (pre-cutoff): the 25 runs listed in the prior evaluator block —
see `audit/AUTHORING_HISTORY.md` "Evaluator review 2026-05-27" for the full
table. Scores spanned 0.0–1.0 across model families.

#### Verdict
**calibrated**

Four current runs across two model families (Claude Opus 4.7, gemma-4-26b);
three scored 1.000 and one scored 0.889. Output-file inspection for the
0.889 run (`run-20260527-2321Z`, gemma-4-26b): produced
`bangkok_aq_typed.geojson` with 100 features, all 5 required properties
present, Point geometry, EPSG:4326 — gates passed. The single failing
subcheck was `station_id_is_integer` (0/100); the other three type
subchecks (`sensor_value`, `pm25_ug_m3`, `elevation_m`) and all five
content / preservation subchecks passed. This is exactly the documented
`broken_partial_coercion` regime (0.889): floats coerced, ID forgotten —
the failure mode the task is designed to discriminate. Calibration is
working as intended.

The reference output self-grades 1.0 on the current grader; the three
broken solutions re-grade to 0.0 / 0.5556 / 0.8889 (exact match with
`metadata.yaml > broken_solutions > measured_score`). No tolerance,
grader, or instruction change is needed to fix calibration.

2c-CRS consistency: grader requires WGS84 via `is_wgs84(sub.crs)`;
reference output uses `urn:ogc:def:crs:OGC:1.3:CRS84` (≡ WGS84);
`expected_outputs[].crs` is `EPSG:4326`; README states EPSG:4326. All
four agree. The grader performs no reprojection of either side (the task
is attribute-only). No one-sided reprojection. Consistent.

#### Specific findings
- Reference grader on `reference/solution/outputs/` scores 1.0 (re-verified 2026-05-28).
- Broken solutions re-grade to 0.0 / 0.5556 / 0.8889, matching `metadata.yaml` exactly.
- Instruction redundancy spotted: `Output bangkok_aq_typed.geojson, GeoJSON in EPSG:4326.` The `expected_outputs[].format` is `geojson`, so by RFC 7946 the CRS is pinned to WGS84 by convention; the explicit `in EPSG:4326` is redundant per the evaluator-prompt's "Strip any CRS mention when the output is GeoJSON" rule. The trailing `GeoJSON` token is likewise redundant (the filename `.geojson` plus `expected_outputs[].format=geojson` already pins the format). Stripping the whole `, GeoJSON in EPSG:4326` tail is the cleanest one-shot strip per the rule's example list ("a trailing 'EPSG:4326 Points' in a prompt"). Applied unilaterally.
- `task.json` had no `version` field — implicitly v1. The instruction edit is a meaningful content change, so this evaluator block bumps to `version: 2` (the first explicit version stamp for this task, per `622342b` semantics).

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: stripped the redundant `, GeoJSON in EPSG:4326` tail from the instruction; added `version: 2` field. Re-grade on reference: 1.0. Reason: GeoJSON-CRS strip rule (Step 4) — `expected_outputs[].format=geojson` already pins WGS84 by RFC 7946 convention.
- `coverage.yaml`: refreshed `evaluator_run_at` to 2026-05-28T00:00:00Z. No slug changes.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none — no human-review flags this run.)

#### Tests run
- grader on reference: 1.0
- grader on broken_wrong_format: 0.0
- grader on broken_no_coercion: 0.5556
- grader on broken_partial_coercion: 0.8889
- pytest (benchmark/eval): 41 passed

---

## Evaluator review 2026-06-06  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior evaluator blocks: pure L1 data-cleaning task probing
**attribute type coercion**. 100 Bangkok rail-station-mounted air-quality
sensor stations arrive as GeoJSON with every numeric column
(`station_id`, `sensor_value`, `pm25_ug_m3`, `elevation_m`) serialised as
JSON strings; the agent must rewrite the file with proper JSON numeric
types (int for the ID, floats for the measurements) while preserving the
Thai-script `name_th` column and the point geometry. Persona Suda
Pongpan; NaN-averages symptom.

#### Change log
Carrying forward the prior log; only new commits since the last evaluator
block are tabulated.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | c2b0515 | docs-change | Prior evaluator review committed: stripped `, GeoJSON in EPSG:4326` tail from the instruction and added `version: 2`. AUTHORING_HISTORY.md / coverage.yaml / audit/status.json refreshed. | Commit msg: "Re-evaluate dc-l1-bangkok-attribute-coercion: calibrated; strip redundant GeoJSON+EPSG:4326 tail" |
| 2026-05-28 | 05aabd6 | grader-change | Repo-wide CRS softening: Gate 1 now soft-accepts any parseable CRS via `grade_crs_soft` (RFC 7946 implicit WGS84 also accepted). Two new subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) replace the prior Gate-1 hard-fail. For this attribute-only task `MEANINGFUL_EPSGS = {4326}`, so any non-4326 CRS docks both subchecks instead of zeroing the score. Total subchecks: 9 → 11. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — change applied across 21 graders to recover scores where the agent's geometry was correct but the CRS wasn't. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57Z** (commit `05aabd6`, class: grader-change — added two new CRS subchecks, replaced Gate 1's hard CRS fail with soft normalisation).
- Most-recent *semantic* prompt-change: 2026-05-28T13:32:11Z (commit `c2b0515`, stripped the GeoJSON+EPSG:4326 tail and bumped version to 2).

#### Runs considered
Eight runs since the cutoff. All `current`.

| Run | Adapter / model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | n/a | cancelled before start | current; no evidence |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:38:59Z | 0.909 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:54:02Z | 0.909 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T09:45:18Z | 0.909 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:15:05Z | 0.000 | done | current (model-side: missing output file) |
| run-20260528-2332Z | claude-code-opus-basic / claude-opus-4-7 | 2026-05-28T23:42:05Z | 0.909 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:33:18Z | 0.909 | done | current |
| run-20260528-1927Z | claude-code-opus-basic / claude-opus-4-7 | 2026-05-28T19:35:14Z | 0.909 | done | current |

Stale runs (pre-cutoff): see prior evaluator blocks. The `run-20260528-1624Z` gemma run scored 1.0 under the pre-soften grader (9 subchecks); not informative for the current 11-subcheck grader.

#### Verdict
**calibrated**

Seven scoring `current` runs across three model families (Claude Opus 4.7, gemma-4-26b, deepseek-v4-pro); six landed at 0.909 and one at 0.000. The 0.000 was a model-side failure (`run-20260529-0109Z`, gemma-4-26b basic: missing output file — agent never produced `bangkok_aq_typed.geojson`); not task evidence per the prompt's "Model-side failures are not task problems" rule.

The six 0.909 scores are all the documented `partial_coercion` regime: agent coerced the three float columns, left `station_id` as a JSON string. Score breakdown verified on `run-20260606-1129Z`: only `station_id_is_integer` fails (0/100); the other 10 subchecks (sensor_value/pm25_ug_m3/elevation_m as number, station_id set, numeric values, name_th, geometry, GeoPandas-view set, crs_is_canonical, crs_in_meaningful_set) all pass. That is exactly the failure mode the grader's `station_id_is_integer` subcheck is designed to discriminate, and the instruction (deliberately stripped of column names and the int-vs-float hint over three prior rounds) tests whether the agent inspects the data closely enough to spot the ID column. Behaviour is as designed.

Two things worth recording about the CRS-soften refactor:

1. The reference now scores 1.0 on 11 subchecks (was 9); broken solutions re-grade to 0.0 / 0.6364 / 0.9091 (were 0.0 / 0.5556 / 0.8889). `metadata.yaml > broken_solutions > measured_score` had not been refreshed for the new 11-subcheck total; this evaluator pass updates them.
2. `MEANINGFUL_EPSGS = {4326}` is narrow by design — the task is attribute-only and reprojection is not in scope, so a deliberately wrong CRS pick still costs both new subchecks (2/11). No widening proposed.

2c-CRS consistency: grader requires WGS84 via `grade_crs_soft` with `treat_none_as_wgs84=True`; reference output uses `urn:ogc:def:crs:OGC:1.3:CRS84` (≡ WGS84); `expected_outputs[].crs` is `EPSG:4326`; README states EPSG:4326. All four agree. The soft-CRS normalisation reprojects the submission to WGS84 *only when it arrives in a different CRS*, which is fine — both sides end up in WGS84 for the subchecks and the canonical-CRS subcheck still penalises the wrong pick.

Instruction calibration: re-read against house style. The previous instruction carried one em-dash (`but the results are wrong — means come back as NaN`) and one spec-grammar fragment (`Thai script in string fields must be preserved verbatim. Output bangkok_aq_typed.geojson.`). Rewrote into house style: opens with the symptom and the ask, full sentences throughout, no em-dashes, references the output file by name in a real sentence ("Write the result to bangkok_aq_typed.geojson"). All factual constraints preserved: the symptom (NaN averages), "leave the string columns and the geometry alone", Thai-script preservation, output filename. Deliberate omissions preserved: still no naming of the operation (coercion), the affected columns, the int-vs-float split, or the output CRS (RFC 7946 pins it).

#### Specific findings
- Reference grader on `reference/solution/outputs/` scores 1.0 (re-verified 2026-06-06; 11/11 subchecks).
- Broken solutions re-grade to 0.0 / 0.6364 / 0.9091 under the post-CRS-soften grader (11-subcheck total). Updating `metadata.yaml > broken_solutions > measured_score` and `expected_score_range` to match.
- `task.json.instruction` re-written into house style: removed em-dash, full sentences. Factual content and deliberate omissions preserved.
- `task.json.analyst_notes` added (was missing). Captures the hidden gotcha (symptom-only prompt asks the agent to diagnose the type-coercion defect on its own) and the documented partial-coercion pitfall (forgetting `station_id`).
- `version` bumped 2 → 3 (instruction edited).

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style rewrite of the instruction (removed em-dash, full sentences). Added `analyst_notes` block. Bumped `version` 2 → 3. Re-grade on reference: 1.0. Reason: house style (no em-dashes, full-sentence sentences) plus initial `analyst_notes` authoring.
- `metadata.yaml`: refreshed `broken_solutions > measured_score` and `expected_score_range` to the post-CRS-soften values (0.0, 0.6364, 0.9091); refreshed the prose descriptions to mention the two new CRS subchecks and the new 11-subcheck totals. Reason: stale measured scores after commit `05aabd6` added two subchecks.
- `coverage.yaml`: refreshed `evaluator_run_at` to 2026-06-06. No slug changes.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none — no human-review flags this run.)

#### Tests run
- grader on reference: 1.0
- grader on broken_wrong_format: 0.0
- grader on broken_no_coercion: 0.6364
- grader on broken_partial_coercion: 0.9091
- pytest (benchmark/eval): 41 passed

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geometry-type uniformity (Point) migrated to a new
  `geometry_type_point_only` subcheck.
- Feature-count tolerance (±5%) migrated to a new
  `feature_count_within_tolerance` subcheck.
- Subcheck total: 11 → 13.

### Verification
- Reference solution re-graded: 1.0 (13/13 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior evaluator blocks: pure L1 data-cleaning task probing
**attribute type coercion**. 100 Bangkok rail-station-mounted air-quality
sensor stations arrive as GeoJSON with every numeric column
(`station_id`, `sensor_value`, `pm25_ug_m3`, `elevation_m`) serialised as
JSON strings; the agent must rewrite the file with proper JSON numeric
types (int for the ID, floats for the measurements) while preserving the
Thai-script `name_th` column and the point geometry. Persona Suda
Pongpan; NaN-averages symptom. Inventory row at
`benchmark/authoring/inventory.md` line 854 corroborates the axis values.

#### Change log
Carrying forward the prior log; only new commits since the last evaluator
block (`0f1f87f`, 2026-06-06) are tabulated.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 0f1f87f | docs-change | Prior evaluator review committed: house-style instruction rewrite, analyst_notes added, version 2 → 3, broken measured scores refreshed to the 11-subcheck totals. | Commit msg: "Re-evaluate dc-l1-bangkok-attribute-coercion: calibrated; refresh broken scores, house-style instruction, add analyst_notes" |
| 2026-06-06 | 363aed2 | grader-change | Repo-wide Gate-2 removal: `structural_correctness` gate dropped; geometry-type uniformity and ±5% feature count migrated to new subchecks `geometry_type_point_only` and `feature_count_within_tolerance`. Subcheck total 11 → 13. The "Manual cleanup 2026-06-06" block above documents this; reference re-graded 1.0 in that commit. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" — gate was inconsistent across the 36 graders; salvageable defects should cost points, not zero the score. |
| 2026-06-07 | c749e57 | grader-change | Repo-wide weighting: six subchecks tagged `weight=3.0` (`feature_count_within_tolerance`, `station_id_set_preserved`, `numeric_values_preserved`, `name_th_preserved_verbatim`, `geometry_preserved_per_id`, `feature_id_set_via_geopandas`); the four type subchecks, geometry-type, and both CRS subchecks stay at weight 1. Total weight 13 → 25. | Commit msg: "Weight data-content subchecks 3x across all categories" — data-content subchecks weighted 3x repo-wide; schema/structural checks stay at 1.0. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:32:38Z** (commit `c749e57`, class: grader-change — subcheck weighting changed every non-trivial score).
- Most-recent prompt-change: 2026-06-06T14:47:07Z (commit `0f1f87f`, house-style rewrite, version 3).

#### Runs considered
42 run directories exist for this task; only runs at/after the cutoff are current. Version check: both current runs recorded `task_version: 3` and suite shas (`6510297`, `ec540aa`) that are descendants of `c749e57` — both pass.

| Run | Adapter / model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:04:55Z | 0.96 | done | current |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T09:17:10Z | 1.00 | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T13:16:46Z | 0.96 | done | stale (started 5h before the weighting cutoff; suite sha `06fd6c0` predates `c749e57`) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T17:56:33Z | 0.909 | done | stale (pre both new grader commits) |
| (38 earlier runs) | (mix of opus/sonnet/haiku/deepseek/gemma/hy3) | 2026-05-12 .. 2026-06-06 | 0.0 .. 1.0 | mostly done | stale (see prior evaluator blocks) |

#### Verdict
**insufficient-evidence**

Only two `current` runs exist and both come from one model family
(deepseek-v4-flash, basic and detailed prompt variants), so the strict
rule yields `insufficient-evidence`. What evidence there is looks
healthy: the detailed-prompt run scored 1.0 (full coercion, all 13
subchecks pass) and the basic-prompt run scored 0.96, failing only
`station_id_is_integer` (0/100 — floats coerced, ID left as a string),
which is exactly the documented `partial_coercion` regime the task is
designed to discriminate. Output inspection of both current runs: 100
features, all 5 required properties, Point-only geometry, EPSG:4326,
station_id Jaccard 1.0, 400/400 numeric cells matching, 100/100 Thai
names verbatim, 100/100 coordinates within 1e-6°.

One calibration observation worth flagging: the repo-wide 3x weighting
(`c749e57`) tagged the six content/set/geometry-preservation subchecks
at weight 3 but left the four type subchecks (the task's central skill)
at weight 1. On this task the weight-3 subchecks pass trivially for an
unmodified input, so a do-nothing pass-through now scores 0.84 (was
0.636 under equal weights) and the forgot-the-ID partial fix scores
0.96 (was 0.909). The grader still rank-orders the regimes correctly
(0 < 0.84 < 0.96 < 1.0), but the dynamic range allocated to the skill
under test shrank from 4/11 to 4/25 of the total weight, and the
documented `expected_score_range` for `broken_no_coercion` ([0.6, 0.7])
no longer held. For this task the JSON *types* arguably are the data
content the weighting commit meant to privilege. Whether the four type
subchecks should carry weight 3 here is a deliberate-policy question
(the `c749e57` diff shows the type checks were left at 1.0 across the
board), so it is flagged rather than edited.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `bangkok_aq_typed.geojson` | instruction, final sentence | stated |
| GeoJSON format | inferable from the `.geojson` filename | inferable |
| output CRS WGS84 | RFC 7946 convention; soft gate also treats absent CRS as WGS84 | inferable |
| 5 required properties present | "leave the string columns ... alone" + repair framing implies keep all columns | inferable |
| Point-only geometry | "leave ... the geometry alone" + input is all Points | stated/inferable |
| feature count ±5% | repair framing implies keep all rows | inferable |
| station_id as JSON integer | inferable from the data (sequential ID values "1".."100") | inferable |
| three measurement columns as JSON numbers | NaN-averages symptom + file inspection | inferable |
| numeric values preserved (1e-3 rel) | repair framing — fix types, not values | inferable |
| name_th verbatim | "keep Thai script in any string field exactly as it arrives" | stated |
| geometry coordinates preserved (1e-6°) | "leave ... the geometry alone" | stated |
| CRS canonical 4326 | unchanged-file framing | inferable |

Factual claims verified: input bundles as `bangkok_aq_stations` (matches
"the vendor's bangkok_aq_stations export"); all six properties arrive as
JSON strings including Thai-script `name_th` (verified against
`inputs/bangkok_aq_stations.geojson`); the NaN symptom is consistent with
the stringified numerics; output filename matches `expected_outputs[]`.
No missing or inaccurate claims.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it coerces `station_id` to
int and the three measurement columns to float, passes `name_th` /
`name_en` and the geometry through unchanged, and writes GeoJSON in
CRS84 (≡ WGS84). The only operation the prompt does not request is the
deterministic sort by `station_id` before serialisation, which is a
documented reproducibility measure (metadata notes); the grader compares
per-id and is order-insensitive, so submissions are not held to it. Not
a deviation worth a flag.

#### Specific findings
- Reference grader on `reference/solution/outputs/` scores 1.0 (re-verified 2026-06-11; 13 subchecks, total weight 25).
- Broken solutions re-grade to 0.0 / 0.84 / 0.96 under the weighted grader; `metadata.yaml > broken_solutions` measured scores, expected ranges, and descriptions refreshed (were 0.0 / 0.6364 / 0.9091 from the pre-weighting 11-subcheck era).
- README still described the two-gate grader (Gate 2 count tolerance, hard `crs.to_epsg() == 4326` gate) and the old broken scores (0.556 / 0.889); refreshed to the single-gate weighted-subcheck reality and the `inputs/` path (docs-change, no version bump).
- <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="med" --> The repo-wide 3x content weighting (`c749e57`) dilutes this task's central skill: the four type subchecks now carry 4/25 of the total weight, so a pass-through that fixes nothing scores 0.84 and the forgot-station_id partial fix scores 0.96, against an original design intent of 0.64 / 0.91 (see the pre-weighting `expected_score_range` of [0.6, 0.7] for `broken_no_coercion`). The human should decide whether the four type subchecks (`station_id_is_integer`, `sensor_value_is_number_not_string`, `pm25_ug_m3_is_number_not_string`, `elevation_m_is_number_not_string`) are this task's "data-content" checks and should be tagged `weight=3.0` (which would restore brokens to ≈ 0.636 / 0.909 with total weight 33), or whether the repo-wide schema-vs-content split is intended to apply uniformly. The same question likely applies to sibling DC tasks whose central defect is not content drift (ring orientation, nulls, dedup). If weights are changed, bump `version` and re-measure the broken scores.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` (0.0 / 0.84 / 0.96), `expected_score_range`, and descriptions to the weighted 13-subcheck grader; fixed the stale "structural gate" mention in the tolerances rationale. Re-grade on reference: 1.0. Reason: stale measured scores after commits `363aed2` (gate-2 drop) and `c749e57` (3x weighting).
- `README.md`: updated grader description to the single-gate weighted-subcheck reality (failure-mode detections, broken scores 0.84 / 0.96, soft-CRS subchecks, `inputs/` path). Docs-change, no version bump.
- `coverage.yaml`: refreshed `evaluator_run_at`. No slug changes (all slugs re-validated against `coverage-vocabulary.yaml`).
- No `version` bump: no change to instruction, grader logic, tolerances, or inputs this pass.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — grader-miscalibration-suspected — repo-wide 3x content weighting leaves the four type subchecks (the central skill) at 4/25 of total weight; consider tagging them weight=3.0.

#### Tests run
- grader on reference: 1.0
- grader on broken_wrong_format: 0.0
- grader on broken_no_coercion: 0.84
- grader on broken_partial_coercion: 0.96
- pytest (benchmark/eval): 41 passed

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### 1. Summary of change

Per-task reasoned subcheck weights replace the repo-wide `c749e57` 3x
content weighting. This is a **grading-only** change (weights in grade.py
only; no task.json version bump, no change to check logic, thresholds, or
gates). It resolves the open HR-001 (grader-miscalibration-suspected): the
blunt 3x content weighting left the four type-coercion subchecks - the
task's central skill - at 4/25 of total weight, so a do-nothing
pass-through scored 0.84.

The new weights are reasoned from what the task actually tests. This is a
data-cleaning task whose central skill is **attribute type coercion**, so
the four type subchecks are weighted highest; content-preservation
(should-not-touch correctness) is secondary; structural/cosmetic checks
(schema presence is a gate, geometry-type, CRS metadata) are lowest. One
near-redundant set check (`feature_id_set_via_geopandas`, a second Jaccard
on the same `station_id` key as `station_id_set_preserved`) is dropped to
weight 1.

### 2. Weight changes

| Subcheck | Group | old -> new |
|---|---|---|
| `station_id_is_integer` | central (type coercion) | 1.0 -> 6.0 |
| `sensor_value_is_number_not_string` | central (type coercion) | 1.0 -> 6.0 |
| `pm25_ug_m3_is_number_not_string` | central (type coercion) | 1.0 -> 6.0 |
| `elevation_m_is_number_not_string` | central (type coercion) | 1.0 -> 6.0 |
| `numeric_values_preserved` | content preservation | 3.0 -> 2.0 |
| `name_th_preserved_verbatim` | content preservation | 3.0 -> 2.0 |
| `geometry_preserved_per_id` | content preservation | 3.0 -> 2.0 |
| `station_id_set_preserved` | set/count integrity | 3.0 -> 2.0 |
| `feature_count_within_tolerance` | set/count integrity | 3.0 -> 2.0 |
| `feature_id_set_via_geopandas` | set integrity (redundant) | 3.0 -> 1.0 |
| `geometry_type_point_only` | structural/cosmetic | 1.0 -> 1.0 (unchanged; made explicit) |
| `crs_is_canonical` | cosmetic (CRS metadata) | 1.0 -> 1.0 (unchanged; made explicit) |
| `crs_in_meaningful_set` | cosmetic (CRS metadata) | 1.0 -> 1.0 (unchanged; made explicit) |

Total weight: 25 -> 38. Central-skill share: 4/25 (16%) -> 24/38 (63%).

### 3. Broken-score before -> after

| Broken | before | after | severity note |
|---|---|---|---|
| `broken_wrong_format` | 0.0 | 0.0 | gate fail (dropped required column); unchanged |
| `broken_no_coercion` | 0.84 | 0.3684 | do-nothing pass-through; all four central type checks fail -> substantial drop |
| `broken_partial_coercion` | 0.96 | 0.8421 | coerced floats, forgot station_id; one of four central checks misses -> meaningful but not catastrophic drop |
| reference | 1.0 | 1.0 | full coercion; unchanged |

Ordering is now sensible and monotone: 0.0 (gate fail) < 0.368 (skipped
the central coercion entirely) < 0.842 (did 3/4 of the central work) <
1.0 (correct). Spot-checks of hypothetical single-subcheck failures
confirm cosmetic/secondary slips sit near the top: wrong CRS (both
subchecks) 0.947, geometry-type only 0.974, a single content-preservation
violation (mangled Thai / edited coords / lossy values) 0.947 each. No
disjoint-failure inversion: the partial fix (one central check) at 0.842
stays above the do-nothing (four central checks) at 0.368, and below any
single cosmetic/content slip - the severity gradient holds.

### 4. Prior-run re-grade summary

Re-graded the `current`-version runs (the two newest, at/after the
`c749e57` weighting cutoff, recorded `task_version: 3`):

| Run | model | recorded (old weights) | re-graded (new weights) |
|---|---|---|---|
| run-20260608-074701Z | deepseek-v4-flash-detailed | 1.00 | 1.00 |
| run-20260609-084636Z | deepseek-v4-flash-basic | 0.96 | 0.8421 |
| run-20260607-112430Z | gemma4-26b-detailed (stale, pre-cutoff) | 0.96 | 0.8421 |

Notable shift: the partial-coercion runs (floats coerced, `station_id`
left as a string) drop 0.96 -> 0.842, correctly reflecting that forgetting
the ID coercion misses a quarter of the central skill. The full-coercion
run stays at 1.0. No inversions; the re-grade preserves the rank order of
the prior runs. (The 38 older runs predate the weighting era and are not
comparable at the current grader; not re-graded.)

### 5. Reasoning

The task tests one thing - rewriting stringified numerics as proper JSON
numeric types - and the grader should spend most of its dynamic range
there. The four type subchecks at weight 6 each (24/38 = 63%) make
failure of the central operation dominate the score, which is the point
HR-001 raised. Content-preservation checks (`numeric_values_preserved`,
`name_th_preserved_verbatim`, `geometry_preserved_per_id`) guard the
"leave the values, Thai script, and geometry alone" constraint; a
violation there is a real bug but a single secondary defect, so weight 2
each places them above the partial-coercion regime (correct: a destructive
edit in one should-not-touch column is one bug, whereas forgetting the ID
coercion misses a quarter of the whole task). Set/count integrity
(`station_id_set_preserved`, `feature_count_within_tolerance`) at weight 2
guards row preservation; the second GeoPandas-view Jaccard is a redundant
detector on the same key, so it drops to weight 1. Structural/cosmetic
checks - geometry-type uniformity and the two CRS-metadata subchecks - sit
at weight 1: schema presence is already a hard gate, the input is all
Points, and CRS is RFC-7946-implied for GeoJSON, so a wrong pick is the
most cosmetic slip available and should barely move the score.

No threshold, check-logic, or gate change was made or is recommended; the
thresholds (0.95 type pass-rate, 0.99 numeric-value pass-rate, 1e-3 rel
tol, 1e-6 deg geom eps, 0.95 Jaccard) remain as authored and are not
suspected of miscalibration.

### 6. Changes applied this run

#### Unilateral edits
- `grade.py`: subcheck `weight=` values only (table in section 2). No
  logic, threshold, or gate change. Re-grade on reference: 1.0.
- `metadata.yaml`: refreshed `broken_solutions > measured_score` and
  `expected_score_range` for `no_coercion` (0.84 -> 0.3684) and
  `partial_coercion` (0.96 -> 0.8421); rewrote the weight-arithmetic prose
  to the new per-task weights.
- `README.md`: refreshed the stale broken score fractions (0.84 -> 0.368,
  0.96 -> 0.842) and weight-total mentions (25 -> 38) in the failure-mode
  and weak-agent sections.
- `audit/status.json`: removed HR-001; recorded this run's edits.

#### Human-review items
- HR-001 (grader-miscalibration-suspected, type-coercion weighting):
  **resolved** by this recalibration; removed from `audit/status.json`.

#### Tests run
- grader on reference: 1.0
- grader on broken_wrong_format: 0.0
- grader on broken_no_coercion: 0.3684
- grader on broken_partial_coercion: 0.8421
- pytest: not run (orchestrator runs the suite)
