# Implementation notes — spa-l1-paris-amenity-within

## Prompt version
2026-05-07-a

## Status
completed

## Summary
L1 spatial_analysis task: `within` spatial join over 85 Paris amenity
Points and 20 arrondissement Polygons (both bundled in EPSG:2154 inside
a single multi-layer GPKG). The agent must emit a flat CSV of one row
per amenity with `osm_id`, `amenity_class`, the integer
`arrondissement_number`, and the verbatim `arrondissement_name`. The
gotcha is the persona's explicit instruction that the 20th arrondissement
must appear as `20` not `20e` — the integer parse out of the French
ordinal name is the deliberate attribute-side wrinkle. Reference,
grader, and three broken solutions built and verified inside the
project Docker container.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0])
  - kept_ordinal_suffix: 0.667 (expected range [0.55, 0.75])
  - name_used_id: 0.833 (expected range [0.75, 0.90])
- Second-run output match: bit-identical (verified via `cp` + `diff -q`;
  CSV has no metadata-timestamp wrinkle, sorting by `osm_id` makes the
  row order deterministic across pandas versions)
- Library tests after task: pass

## Failure-mode coverage
- Kept French ordinal suffix in `arrondissement_number`:
  broken_kept_ordinal_suffix
- Wrote arrondissement Overture id into `arrondissement_name` column:
  broken_name_used_id
- Dropped the `arrondissement_number` column: broken_wrong_format
  (Gate 1)
- Used `intersects` instead of `within`: not-handled (the bundled
  fixture has no boundary-edge points so the two predicates agree on
  every amenity; recorded in README failure modes for completeness)
- Inverted join (one row per arrondissement) or over-filter (only one
  arrondissement's amenities): principled — Gate 2 ±5% count tolerance

## Open issues
- [severity: low] — Inventory's OSM-tag axis names `amenity=*`; we did
  not fall back to OSM Overpass because Overture's `places.place`
  taxonomy covers the same amenity leaves (`pharmacy`, `bakery`,
  `cafe`, `library`, `restaurant`) with auditable Overture provenance
  — in line with `docs/AUTHOR_CONTEXT.md`'s "Overture is the default
  authoring source" rule. The five chosen leaves all use the same
  spelling in Overture and OSM, so the bundled `amenity_class` column
  carries OSM-compatible values verbatim and the agent does not need
  to normalise plurals (Overture's `banks` was excluded for exactly
  this reason — it would have introduced a singular/plural
  normalisation question that is out of scope for an L1 spatial-join
  task).

- [severity: low] — The `intersects`-vs-`within` failure mode is not
  covered by a dedicated broken solution because the bundled fixture
  is pre-clipped to the union of arrondissements, leaving no
  boundary-edge points where the two predicates would disagree. A
  future variant of this task could intentionally place a few points
  on shared boundaries to provoke that disagreement; for v1 the
  failure mode is documented in the README as principled-reasoning.

## Suggested prompt changes
(none)

## Inventory change proposals
(none — the inventory's spatial_join-within primary op, EPSG:2154 input
CRS, two-layer GPKG input, CSV output, "Small (~10² amenities, 20
arrondissements)" data scale, and OSM-tag axis (`amenity=*`) are all
met as written. Final amenity count is 85 not 100; the Overture
`places.place` slice for the central-Paris bbox capped at 22 per
category yielded 85 inside the arrondissement union, which still sits
firmly in the inventory's "Small (~10² amenities)" tier. Inventory
need not change.)

## Library extensions
(none — task uses `count_within_tolerance` and `jaccard_similarity_set`
from the shared library. The `_coerce_int` helper inside `grade.py` is
inlined because its purpose is the persona's gotcha for *this task*
specifically — papering it over with a regex-extract in a shared
primitive would silently rescue solutions the persona's downstream
join would actually break.)

## Runtime
~50 minutes (peer task `spa-l1-capetown-hospital-nn` provided the
two-layer-input pattern and the broken-solution authoring template;
the Overture-side discovery for Paris arrondissements (subtype =
`neighborhood` with name LIKE `%Arrondissement%` is the right slicer)
took one extra exploration query, and the grader's `_coerce_int`
helper needed a `numpy.integer` branch — `numpy.int64` is not
`isinstance(int)` in this Python build, which the first reference-grader
run caught with a 0/85 per-row-match failure on the reference's own
output.)

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Inventory row (`benchmark/authoring/inventory.md` lines 699-722) specifies an L1 spatial-analysis task: Émilie Dubois at INSEE tags a Paris amenity point dataset with the arrondissement each amenity sits inside. The bundled GPKG carries 85 amenity Points and 20 arrondissement Polygons in EPSG:2154; the agent emits a flat CSV with `osm_id, amenity_class, arrondissement_number (int), arrondissement_name`. The deliberate twist is the persona's gotcha: the integer arrondissement number must be parsed out of the French ordinal in the Overture name string (`"Paris 20e Arrondissement"` → `20`, not `"20e"`). Primary operation: spatial join — within. Originally authored 2026-05-08 as a recovered task brought over from the `tasks-run-2026-05-08-a` parallel branch.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Initial task: task.json, README, grade.py, metadata.yaml, reference/generate.py + outputs, data/_prepare_input.py, GPKG fixture, tests/_make_brokens.py + 3 broken outputs, IMPLEMENTATION_NOTES.md | Commit msg: "Brought over from tasks-run-2026-05-08-a, the most recent parallel branch where these two tasks were completed before the restructure." |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Bulk add across 36 task dirs. |
| 2026-05-13 | 1b8dda1 | docs-change | Generated image.webp | Bulk image generation across 36 dirs. |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Repo-wide refactor. No content change. |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via fal.ai FLUX schnell | Visual refresh; no task content change. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 (0.5K, 3:2) | Visual refresh; no task content change. |
| 2026-05-14 | 1bc112e | prompt-change | Stripped CRS hint and explicit ordinal-gotcha example ("`20e Arrondissement` is `20`, not `20e`") from instruction; kept "as a plain integer parsed from the name" wording. | Commit msg: "Strip deducible information from SPA task instructions… remove input CRS mentions, geometry type descriptions, feature counts, specific data value examples, and data quality issue details that the model should discover from file metadata." |
| 2026-05-17 | 7f31f98 | prompt-change | Replaced "Mind the suffixes on the arrondissement names — my downstream join wants `arrondissement_number` as a plain integer parsed from the name." with column-list schema `arrondissement_number (integer)`. | Commit msg: "Remove nudges from 6 spatial-analysis task prompts. Strip CRS codes, operation names, and explicit hints from instruction text while preserving output specs, column names, and unit requirements." |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`; `data/` → `inputs/`; `reference/{generate.py,outputs/}` → `reference/solution/`; `tests/` → `reference/failures/`; image assets into `assets/`; path strings updated in `task.json`, `grade.py`, `_prepare.py`, `_make_brokens.py`, `generate.py`. | Commit msg: "Reorganize task folder layout… migrate every benchmark task to a clearer layout." Path-only — no contract change. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit 7f31f98, class: prompt-change). The 2026-05-26 reorg (29a9ae3) is path-only and does not affect the task contract.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T14:12:12Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:55:06Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:13:19Z | 1.0 | done | current |

22 earlier runs (2026-05-12 to 2026-05-17 pre-cutoff) exist but are stale and excluded from diagnostic reasoning.

#### Verdict
**calibrated**

All three `current` runs scored 1.0 with all 6 subchecks passing (85/85 rows on every per-row check, osm_id-set Jaccard 1.0000). The three agent families span a wide capability range (Claude Opus, DeepSeek V4 Flash, Gemma 4 26B) and they score very differently on other tasks in the same `run-20260517-1254Z` sweep (e.g. dc-l3-vienna-overpass-historical 0.0, geo-l1-capetown-building-centroids 0.0, spa-l2-lagos-hotspot-overlaps 0.0), so the uniform 1.0 here is task-specific, not capability-uniform. Inspecting the two weaker agents' `solve.py`: both reach for `gpd.sjoin(..., predicate="within")` and use `re.search(r"(\d+)", name)` to pull the integer out of the ordinal — exactly the path the persona's design anticipated. The current instruction is already maximally stripped within the L1 contract: it names neither the CRS, the operation (`within`), the geometry types, nor the ordinal gotcha; the only schema commitments are the four output column names and types, which are necessary information the agent cannot infer. Capable mid-size open-source models reliably pass this L1 task — that is the calibrated outcome for L1, not a sign of over-specification.

#### Specific findings
- All three current agents independently chose `predicate="within"` (Gemma uses it explicitly, DeepSeek likewise). The persona's wrinkle (integer parse from "Paris 20e Arrondissement") is solvable with a one-line regex; the broken-solution `kept_ordinal_suffix` confirms the grader does catch agents that fail at this step. No gift in the prompt to strip.
- The `(integer)` annotation in the column list is schema information, not a gift. Stripping it would conflict with the design-prompt rule "Redundant output schema. End the instruction with a sentence restating output format and CRS" (here baked into the column declaration). Keep.
- Broken-solution scores in `metadata.yaml > broken_solutions > measured_score` were last verified at authoring time (0.000 / 0.667 / 0.833). No reason to suspect drift — grader is deterministic.
- File contract is consistent across `task.json`, `metadata.yaml`, `grade.py`, and `inventory.md` (single CSV output, EPSG:2154 input, two-layer GPKG, region=paris, primary op=spatial-join-within, scale=small).

### 3. Changes applied this run

#### Unilateral edits
- None.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (all 6 subchecks pass)
- pytest: pass (35 passed in 0.62s)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Inventory row (`benchmark/authoring/inventory.md` lines 699-722) specifies an L1 spatial-analysis task: Émilie Dubois on INSEE's municipal census team tags a Paris amenity point dataset with the arrondissement each amenity falls within for a neighbourhood demographic crosswalk. The bundled two-layer GPKG carries 85 `places.place` amenity Points and 20 `divisions.division_area` arrondissement Polygons, both reprojected to EPSG:2154 (RGF93 / Lambert-93). The agent emits a flat CSV with one row per amenity carrying `osm_id`, `amenity_class`, the integer `arrondissement_number`, and the verbatim `arrondissement_name`. Primary operation: spatial join — within. The deliberate design wrinkle is the persona's gotcha: the integer arrondissement number must be parsed out of the French ordinal embedded in the Overture name string (`"Paris 20e Arrondissement"` → `20`, not `"20e"`). Originally authored 2026-05-08 as a task recovered from the `tasks-run-2026-05-08-a` parallel branch.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Initial task: task.json, README, grade.py, metadata.yaml, reference generate.py + outputs, data/_prepare_input.py, GPKG fixture, tests/_make_brokens.py + 3 broken outputs, IMPLEMENTATION_NOTES.md | Commit msg: "task: spa-l1-paris-amenity-within, spa-l1-vienna-pip-count [recovered]" — brought over from the most recent parallel authoring branch. |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Bulk add across 36 task dirs. |
| 2026-05-13 | 1b8dda1 | docs-change | Generated image.webp | Bulk image generation across 36 dirs. |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Repo-wide refactor; no content change. |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via fal.ai FLUX schnell | Visual refresh; no task content change. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 (0.5K, 3:2) | Visual refresh; no task content change. |
| 2026-05-14 | 1bc112e | prompt-change | Dropped "Both layers are in Lambert-93." and the explicit ordinal-gotcha example ("`20e Arrondissement` is `20`, not `20e`") from the instruction; kept the "plain integer parsed from the name" wording. | Commit msg: "Strip deducible information from SPA task instructions… remove input CRS mentions… and specific data value examples… that the model should discover from file metadata." |
| 2026-05-17 | 7f31f98 | prompt-change | Replaced the "Mind the suffixes…plain integer parsed from the name." nudge with a bare column-list schema declaring `arrondissement_number (integer)` and `arrondissement_name (string)`. | Commit msg: "Remove nudges from 6 spatial-analysis task prompts. Strip CRS codes, operation names, and explicit hints from instruction text while preserving output specs, column names, and unit requirements." |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`; `data/` → `inputs/`; `reference/{generate.py,outputs/}` → `reference/solution/`; `tests/` → `reference/failures/`; assets into `assets/`; path strings updated in task.json, grade.py, _prepare.py, _make_brokens.py, generate.py. | Commit msg: "Reorganize task folder layout… migrate every benchmark task to a clearer layout." Path-only — no contract change. |
| 2026-05-26 | e38ae4b | docs-change | Prior evaluator review: appended evaluator-review block, wrote coverage.yaml + audit/status.json. Verdict: calibrated, no edits. | Commit msg: "Re-evaluate spa-l1-paris-amenity-within: calibrated, no edits". |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit 7f31f98, class: prompt-change). The 2026-05-26 reorg (29a9ae3) is path-only and the 2026-05-26 evaluator commit (e38ae4b) is docs-only; neither shifts the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T14:12:12Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:55:06Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:13:19Z | 1.0 | done | current |

23 earlier runs (2026-05-12 to 2026-05-17, started before the 2026-05-17T12:49Z cutoff) exist under `benchmark/eval/runs/` but are stale and excluded from diagnostic reasoning.

#### Verdict
**calibrated**

This is a confirmatory re-evaluation: no design-affecting commit has landed since the prior evaluator's 2026-05-26 review (e38ae4b), so the same three `current` runs remain the evidence base and the verdict is unchanged. All three scored 1.0 with all 6 subchecks passing (85/85 on every per-row check, osm_id-set Jaccard 1.0000); each produced exactly 85 rows with the four required columns (`osm_id, amenity_class, arrondissement_number, arrondissement_name`), matching the reference schema. The three agent families (Claude Opus, DeepSeek V4 Flash, Gemma 4 26B) span a wide capability range and score very differently on harder tasks in the same sweeps, so the uniform 1.0 here is task-specific rather than capability-uniform — the expected calibrated outcome for an L1 single-operation task. The output is non-spatial CSV (`crs: null`), so the 2c-CRS check is N/A; the README correctly states "n/a (tabular output)". The instruction is already maximally stripped within the L1 contract: it names neither the input CRS, the `within` operation, the geometry types, nor the ordinal gotcha — the only commitments are the four output column names and the `(integer)` / `(string)` type annotations, which are necessary schema information the agent cannot infer. The `too-easy` branch does not apply because there is no remaining gift to strip.

#### Specific findings
- Re-grade of the reference output scores 1.0 (6/6 subchecks); the grader is deterministic and the broken-solution scores in `metadata.yaml` (0.000 / 0.667 / 0.833) remain plausible — no re-run performed since no edit was applied and the prior evaluator already confirmed them.
- File contract is consistent across `task.json`, `metadata.yaml`, `grade.py`, `README.md`, and `inventory.md` (single CSV output, EPSG:2154 two-layer GPKG input, region=paris, primary op=spatial-join-within, scale=small). No change needed.
- EPSG:2154 (Lambert-93) is a Lambert Conformal Conic projection → coverage CRS slug `conformal` (per `coverage-vocabulary.yaml`); coverage.yaml carried forward unchanged from the prior review.

### 3. Changes applied this run

#### Unilateral edits
- None.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (all 6 subchecks pass)
- pytest: pass (35 passed in 0.89s)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Inventory row (`benchmark/authoring/inventory.md` lines 699-722) specifies an L1 spatial-analysis task: Émilie Dubois on INSEE's municipal census team tags a Paris amenity point dataset with the arrondissement each amenity falls within for a neighbourhood demographic crosswalk. The bundled two-layer GPKG carries 85 `places.place` amenity Points and 20 `divisions.division_area` arrondissement Polygons, both reprojected to EPSG:2154 (RGF93 / Lambert-93). The agent emits a flat CSV with one row per amenity carrying `osm_id`, `amenity_class`, the integer `arrondissement_number`, and the verbatim `arrondissement_name`. Primary operation: spatial join — within. The deliberate design wrinkle is the persona's gotcha: the integer arrondissement number must be parsed out of the French ordinal embedded in the Overture name string (`"Paris 20e Arrondissement"` → `20`, not `"20e"`). Originally authored 2026-05-08 as a task recovered from the `tasks-run-2026-05-08-a` parallel branch.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Initial task: task.json, README, grade.py, metadata.yaml, reference generate.py + outputs, data/_prepare_input.py, GPKG fixture, tests/_make_brokens.py + 3 broken outputs, IMPLEMENTATION_NOTES.md | Commit msg: "task: spa-l1-paris-amenity-within, spa-l1-vienna-pip-count [recovered]" — brought over from the most recent parallel authoring branch. |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Bulk add across 36 task dirs. |
| 2026-05-13 | 1b8dda1 | docs-change | Generated image.webp | Bulk image generation across 36 dirs. |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Repo-wide refactor; no content change. |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via fal.ai FLUX schnell | Visual refresh; no task content change. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 (0.5K, 3:2) | Visual refresh; no task content change. |
| 2026-05-14 | 1bc112e | prompt-change | Dropped "Both layers are in Lambert-93." and the explicit ordinal-gotcha example ("`20e Arrondissement` is `20`, not `20e`") from the instruction; kept the "plain integer parsed from the name" wording. | Commit msg: "Strip deducible information from SPA task instructions… remove input CRS mentions… and specific data value examples… that the model should discover from file metadata." |
| 2026-05-17 | 7f31f98 | prompt-change | Replaced the "Mind the suffixes…plain integer parsed from the name." nudge with a bare column-list schema declaring `arrondissement_number (integer)` and `arrondissement_name (string)`. | Commit msg: "Remove nudges from 6 spatial-analysis task prompts. Strip CRS codes, operation names, and explicit hints from instruction text while preserving output specs, column names, and unit requirements." |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`; `data/` → `inputs/`; `reference/{generate.py,outputs/}` → `reference/solution/`; `tests/` → `reference/failures/`; assets into `assets/`; path strings updated in task.json, grade.py, _prepare.py, _make_brokens.py, generate.py. | Commit msg: "Reorganize task folder layout… migrate every benchmark task to a clearer layout." Path-only — no contract change. |
| 2026-05-26 | e38ae4b | docs-change | First evaluator review: appended evaluator-review block, wrote coverage.yaml + audit/status.json. Verdict: calibrated, no edits. | Commit msg: "Re-evaluate spa-l1-paris-amenity-within: calibrated, no edits". |
| 2026-05-27 | 23f3da6 | docs-change | Second evaluator review: appended confirmatory evaluator-review block; refreshed status.json/coverage.yaml timestamps. Verdict unchanged: calibrated, no edits. | Commit msg: "Re-evaluate spa-l1-paris-amenity-within: calibrated, no edits". |
| 2026-05-28 | 622342b | docs-change | Repo-wide drop of the unused `prompt_version: 2026-05-07-a` field from `metadata.yaml`; introduced `task.json.version` semantics globally (this task implicitly v1 — no `version` field yet). One-line `metadata.yaml` deletion; no tolerance / grader / input change. | Commit msg: "Add task content versioning; drop unused prompt_version" — `prompt_version` "tagged the orchestrator's authoring template, not the task content, and has no runtime relevance". |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit 7f31f98, class: prompt-change). The 2026-05-26 reorg (29a9ae3), the prior evaluator commits (e38ae4b, 23f3da6), and the 2026-05-28 versioning commit (622342b — drops `metadata.yaml > prompt_version` only, no tolerance / grader / input change) are all docs-class and do not shift the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-opus-4-6 | 2026-05-17T14:12:12Z | 1.0 | done | current |
| run-20260517-1424Z | deepseek/deepseek-v4-flash | 2026-05-17T18:55:06Z | 1.0 | done | current |
| run-20260526-0748Z | google/gemma-4-26b-a4b-it | 2026-05-26T09:13:19Z | 1.0 | done | current |
| run-20260527-2016Z | claude-opus-4-7 | 2026-05-27T23:03:22Z | 1.0 | done | current |
| run-20260527-2321Z | google/gemma-4-26b-a4b-it | 2026-05-28T00:59:31Z | 1.0 | done | current |
| run-20260528-0113Z | claude-opus-4-7 | 2026-05-28T03:06:13Z | 1.0 | done | current |
| run-20260528-0317Z | google/gemma-4-26b-a4b-it | 2026-05-28T04:11:31Z | 1.0 | done | current |

22 earlier runs (2026-05-12 to 2026-05-17, started before the 2026-05-17T12:49Z cutoff) exist under `benchmark/eval/runs/` but are stale and excluded from diagnostic reasoning.

#### Verdict
**calibrated**

This is a confirmatory re-evaluation: no design-affecting commit has landed since the prior evaluator's 2026-05-27 review (23f3da6). The new versioning commit (622342b) only deletes the orchestrator-tracking field `prompt_version` from `metadata.yaml` and introduces `task.json.version` semantics globally; the grader, tolerances, input bundle, and instruction are untouched. The evidence base expands to seven `current` runs (three from the prior review plus four new 2026-05-27/28 runs against claude-opus-4-7 and gemma-4-26b), all of which produce 85-row CSVs with the four required columns and score 1.0 with 6/6 subchecks passing — confirming stable behaviour across two further claude-opus-4-7 sessions and two further gemma-4-26b sessions. The persona's gotcha (integer parse from "Paris 20e Arrondissement") continues to be solved correctly by all observed agents; the broken-solution `kept_ordinal_suffix` design still discriminates that failure mode. The agent family spread (Claude Opus 4-6 + 4-7, DeepSeek V4 Flash, Gemma 4 26B) covers a wide capability range that scores very differently on harder tasks in the same sweeps, so the uniform 1.0 here remains task-specific rather than capability-uniform — the expected calibrated outcome for an L1 single-operation task. The output is non-spatial CSV (`crs: null`), so the 2c-CRS check is N/A; the README correctly states "n/a (tabular output)". The instruction is already maximally stripped within the L1 contract: it names neither the input CRS, the `within` operation, the geometry types, nor the ordinal gotcha — the only commitments are the four output column names and the `(integer)` / `(string)` type annotations, which are necessary schema information the agent cannot infer.

#### Specific findings
- Re-grade of the reference output scores 1.0 (6/6 subchecks); the grader is deterministic and the broken-solution scores in `metadata.yaml` (0.000 / 0.667 / 0.833) remain plausible — no re-run performed since no edit was applied.
- The 2026-05-28 `prompt_version` removal is a metadata-cleanup field that never reached the grader or the agent; no contract impact. The task still carries no explicit `version` field in `task.json` and is implicitly v1 per the new convention. No unilateral edit this run, so no bump is owed.
- File contract is consistent across `task.json`, `metadata.yaml`, `grade.py`, `README.md`, and `inventory.md` (single CSV output, EPSG:2154 two-layer GPKG input, region=paris, primary op=spatial-join-within, scale=small). No change needed.
- EPSG:2154 (Lambert-93) is a Lambert Conformal Conic projection → coverage CRS slug `conformal` (per `coverage-vocabulary.yaml`); coverage.yaml carried forward unchanged from the prior review.

### 3. Changes applied this run

#### Unilateral edits
- None.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (all 6 subchecks pass)
- pytest: pass (41 passed in 0.54s)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Inventory row (`benchmark/authoring/inventory.md` lines 699-722) specifies an L1 spatial-analysis task: Émilie Dubois on INSEE's municipal census team tags a Paris amenity point dataset with the arrondissement each amenity falls within for a neighbourhood demographic crosswalk. The bundled two-layer GPKG carries 85 `places.place` amenity Points and 20 `divisions.division_area` arrondissement Polygons, both reprojected to EPSG:2154 (RGF93 / Lambert-93). The agent emits a flat CSV with one row per amenity carrying `osm_id`, `amenity_class`, the integer `arrondissement_number`, and the verbatim `arrondissement_name`. Primary operation: spatial join — within. The deliberate design wrinkle is the persona's gotcha: the integer arrondissement number must be parsed out of the French ordinal embedded in the Overture name string (`"Paris 20e Arrondissement"` → `20`, not `"20e"`).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Initial task: task.json, README, grade.py, metadata.yaml, reference generate.py + outputs, data/_prepare_input.py, GPKG fixture, tests/_make_brokens.py + 3 broken outputs, IMPLEMENTATION_NOTES.md | Commit msg: "task: spa-l1-paris-amenity-within, spa-l1-vienna-pip-count [recovered]" — brought over from the most recent parallel authoring branch. |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Bulk add across 36 task dirs. |
| 2026-05-13 | 1b8dda1 | docs-change | Generated image.webp | Bulk image generation across 36 dirs. |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Repo-wide refactor; no content change. |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via fal.ai FLUX schnell | Visual refresh; no task content change. |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 (0.5K, 3:2) | Visual refresh; no task content change. |
| 2026-05-14 | 1bc112e | prompt-change | Dropped "Both layers are in Lambert-93." and the explicit ordinal-gotcha example ("`20e Arrondissement` is `20`, not `20e`") from the instruction. | Commit msg: "Strip deducible information from SPA task instructions… remove input CRS mentions… and specific data value examples… that the model should discover from file metadata." |
| 2026-05-17 | 7f31f98 | prompt-change | Replaced the "Mind the suffixes…plain integer parsed from the name." nudge with a bare column-list schema declaring `arrondissement_number (integer)` and `arrondissement_name (string)`. | Commit msg: "Remove nudges from 6 spatial-analysis task prompts." |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg. | Commit msg: "Reorganize task folder layout." Path-only — no contract change. |
| 2026-05-26 | e38ae4b | docs-change | First evaluator review: calibrated, no edits. | Confirmatory pass. |
| 2026-05-27 | 23f3da6 | docs-change | Second evaluator review: calibrated, no edits. | Confirmatory pass. |
| 2026-05-28 | 622342b | docs-change | Repo-wide drop of unused `prompt_version: 2026-05-07-a` field from `metadata.yaml`; introduced `task.json.version` semantics globally (this task implicitly v1 — no `version` field yet). | Commit msg: "Add task content versioning; drop unused prompt_version". |
| 2026-05-28 | b935b66 | docs-change | Third evaluator review: calibrated, no edits. | Confirmatory pass. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit 7f31f98, class: prompt-change). The 2026-05-26 reorg (29a9ae3), the prior evaluator commits (e38ae4b, 23f3da6, b935b66), and the 2026-05-28 versioning commit (622342b — drops `metadata.yaml > prompt_version` only) are all docs-class and do not shift the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T14:12:12Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:55:06Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:13:19Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T23:03:22Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:59:31Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T03:06:13Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:11:31Z | 1.0 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:53:00Z | 1.0 | done | current |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T22:08:01Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:21:30Z | 0.0 | done | current — model-side: agent wrote `amenity_counts_by_arrondissement.geojson` instead of the requested CSV |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:49:11Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:08:49Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T18:06:39Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:28:33Z | failed | failed | current — model-side: harness UTF-8 decode error on the agent stream; on-disk CSV has wrong `arrondissement_number` values (e.g. 39, 98, 0) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:49:30Z | 1.0 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | cancelled | cancelled | current — model-side: run cancelled |

22 earlier runs (2026-05-12 to 2026-05-17, started before the 2026-05-17T12:49Z cutoff) exist under `benchmark/eval/runs/` but are stale and excluded from diagnostic reasoning.

#### Verdict
**calibrated**

The evidence base expands to 16 `current` runs across claude-opus-4-6/4-7, deepseek-v4-flash, deepseek-v4-pro, and gemma-4-26b (both basic and detailed prompt variants). 13 of 16 score 1.0 with all 6 subchecks passing; the three non-1.0 outcomes are all model-side rather than task-side (one gemma run wrote the wrong filename and a different file format; one gemma-detailed run failed with a harness UTF-8 decode error on the agent stream — the on-disk CSV has fabricated `arrondissement_number` values, confirming the underlying model output was already wrong; one gemma-detailed run was cancelled). Per the prompt's "Model-side failures are not task problems" rule, these do not impeach the task. The grader continues to discriminate correctly on broken solutions (0.000 / 0.667 / 0.833 for wrong_format / kept_ordinal_suffix / name_used_id). The output is non-spatial CSV (`crs: null`), so the 2c-CRS check is N/A. EPSG:2154 (Lambert-93) is a Lambert Conformal Conic projection → coverage CRS slug `conformal`. The instruction has been rewritten this pass for house style — see Section 3 — but the rewrite preserves every factual constraint and every deliberate omission (no CRS, no `within`, no ordinal example), so the calibrated verdict carries through.

#### Specific findings
- Re-grade of the reference output after the instruction rewrite scores 1.0 (6/6 subchecks). Broken-solution scores in `metadata.yaml` (0.000 / 0.667 / 0.833) remain plausible; the grader is deterministic and no grader edit was applied.
- The prior instruction read as spec-grammar ("For each amenity ... tag the arrondissement it sits in ... and emit a flat ..."): no persona purpose, opening with a fragment-style conditional, "emit" rather than "write". House-style rewrite applied (see Section 3).
- `analyst_notes` was missing from `task.json` and has been authored this pass to surface the hidden gotcha (integer parse out of the French ordinal name) for the human reviewer.
- File contract is consistent across `task.json`, `metadata.yaml`, `grade.py`, `README.md`, and `inventory.md` (single CSV output, EPSG:2154 two-layer GPKG input, region=paris, primary op=spatial-join-within, scale=small). No change needed.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: rewrote `instruction` in house style. New opener leads with the purpose (INSEE neighbourhood demographic crosswalk) before the ask, uses full sentences, references files by their actual names (`amenities`, `arrondissements`, `amenity_to_arrondissement.csv`), and keeps the bare schema commitments (`(integer)`, `(string)`). Preserved every factual constraint and every deliberate omission: no CRS mention, no `within` operation name, no ordinal-gotcha example. Re-grade on reference: 1.0.
- `task.json`: authored `analyst_notes` (description + 5-step approach + 5 pitfalls). The hidden gotcha (integer parse out of the French ordinal name) is the first pitfall.
- `task.json`: bumped `version` from implicit 1 to explicit 2 because the `instruction` field changed.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (all 6 subchecks pass)
- pytest: pass (41 passed in 1.14s)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Row-count ±5% check deleted: already covered by the stricter
  `exact_count_match` and `osm_id_set_jaccard` subchecks.
- Dropped the unused `count_within_tolerance` import.
- Subcheck count unchanged at 6.

### Verification
- Reference solution re-graded: 1.0 (6/6 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior reviews: inventory row (`benchmark/authoring/inventory.md`) specifies an L1 spatial-analysis task in which Émilie Dubois on INSEE's municipal census team tags 85 bundled Paris amenity Points with the arrondissement (20 Polygons, same EPSG:2154 GPKG) each falls within, emitting a flat CSV (`osm_id`, `amenity_class`, integer `arrondissement_number`, verbatim `arrondissement_name`). The deliberate wrinkle is parsing the integer out of the French ordinal in the Overture name ("Paris 20e Arrondissement" → 20, not "20e"). Primary operation: spatial join — within.

#### Change log
Commits through 2026-05-28 (622342b) are documented in the prior review blocks above and are not re-classified here. New since the 2026-06-06 review block was written:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 83bbf41 | mixed (prompt-change + docs-change) | Fourth evaluator review: house-style rewrite of `instruction`, authored `analyst_notes`, bumped `version` 1 → 2; coverage.yaml + status.json refresh. | Commit msg: "Re-evaluate spa-l1-paris-amenity-within: house-style rewrite + analyst_notes". |
| 2026-06-06 | 363aed2 | grader-change | Dropped `Gate("structural_correctness", ...)` (count ±5% early-return) from `grade.py`; single hard `format_schema_valid` gate remains; unused `count_within_tolerance` import removed; subcheck count unchanged at 6. Documented in the "Manual cleanup 2026-06-06" block above. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" — repo-wide consistency refactor; count failures now cost subcheck points instead of collapsing the score. |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to all six subchecks in `grade.py` (repo-wide: data-content subchecks weighted 3x, structural stay 1.0; this grader has no structural subchecks, so all six are 3.0). | Commit msg: "Weight data-content subchecks 3x across all categories". |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38Z (commit c749e57, class: grader-change). The 83bbf41 prompt rewrite (2026-06-06T16:54:47Z) and the 363aed2 gate drop (2026-06-06T20:11:02Z) are superseded by this later cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260607-112430Z | google/gemma-4-26b-a4b-it | 2026-06-07T18:45:55Z | 1.0 | done | current (suite sha 06fd6c0 predates c749e57, but the weighting is score-neutral here: all six subchecks carry the same weight, so unweighted and weighted scores are identical; task version 2 == current 2) |
| run-20260608-074701Z | deepseek/deepseek-v4-flash | 2026-06-09T07:32:37Z | 1.0 | done | current (suite sha 6510297 includes c749e57; version 2) |
| run-20260609-084636Z | deepseek/deepseek-v4-flash | 2026-06-09T12:33:30Z | 1.0 | done | current (suite sha ec540aa includes c749e57; version 2) |

39 earlier runs (2026-05-12 through 2026-06-06, plus the 2026-06-06 failed/cancelled gemma runs) started before the 2026-06-07T18:32:38Z cutoff and are stale for the current grader generation; the 16 runs from 2026-05-17 onward were reviewed in detail in the 2026-06-06 block above and their conclusions (13/16 at 1.0, three model-side failures) still inform the capability-spread picture.

#### Verdict
**calibrated**

All three current runs scored 1.0 with 6/6 subchecks; each produced an 85-row CSV whose header and first rows match the reference schema exactly (verified by direct file inspection). The two new grader commits are score-neutral for this task: the gate-2 drop only changes the score of count-mismatched submissions (0 → partial), and the 3x weighting is uniform across all six subchecks, so every historical score ratio is preserved — confirmed by re-running the grader on the reference (1.0) and all three broken sets (0.0 / 0.6667 / 0.8333, identical to `metadata.yaml > measured_score`). The current evidence spans two agent families (Gemma 4 26B, DeepSeek V4 Flash) that score very differently on harder tasks in the same sweeps, and the larger 16-run pre-cutoff history covers Claude Opus and DeepSeek V4 Pro at the same uniform 1.0, so the result is task-specific, not capability-uniform — the expected calibrated outcome for an L1 single-operation task. Output is non-spatial CSV (`crs: null`), so the 2c-CRS check is N/A.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `amenity_to_arrondissement.csv`, CSV-parseable | instruction (filename + extension) | stated |
| required columns `osm_id`, `amenity_class`, `arrondissement_number`, `arrondissement_name` | instruction column list | stated |
| exact row count (one row per amenity, 85) | instruction ("one row per amenity") | stated |
| osm_id set Jaccard ≥ 0.95 | carry `osm_id` through from the amenity layer | inferable |
| `arrondissement_number` integer in 1..20 | instruction declares "(integer)"; value derived by parsing the arrondissement name | stated + inferable |
| per-row `arrondissement_number` match | correct within join + ordinal parse | inferable |
| per-row `arrondissement_name` verbatim match | instruction declares the column (string); the obvious source is the polygon layer's `name` | inferable |
| per-row `amenity_class` match | carry through from the amenity layer | inferable |

Factual claims verified: layer names `amenities` and `arrondissements` exist in `inputs/paris_amenities.gpkg` (85 Points / 20 Polygons, both EPSG:2154); amenity layer carries `osm_id` and `amenity_class`; reference output has exactly the four declared columns. No missing constraints, no inaccurate claims.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads the two named layers, runs `sjoin(..., predicate="within")`, parses the integer with an ordinal-aware regex, and writes exactly the four requested columns. The `sort_values("osm_id")` step is not requested by the prompt, but it is a determinism measure only — the grader joins on `osm_id` and is row-order-agnostic, so it cannot disadvantage or advantage any submission. No deviation worth flagging.

#### Specific findings
- The gate-2 removal changes the score landscape for truncated/inverted-join submissions (formerly Gate-2 → 0, now 4/6 ≈ 0.67 when the columns survive). This follows the deliberate repo-wide design in 363aed2 ("count failures cost subcheck points instead of collapsing the score") and no current run exhibits the shape, so it is recorded as a consequence, not flagged. README failure modes 5 and 6 still claimed "Gate 2 ... score = 0" — fixed (docs-change).
- README also quoted persona prompt text that was stripped from the instruction in May ("must list the 20th arrondissement as `20` not `20e`", "Both layers are in Lambert-93") as if it were still in the prompt, referenced "Gate 1", and pointed at the pre-reorg `data/` path — all fixed (docs-change).
- `metadata.yaml > tolerances > rationale` claimed "Gate 2 uses the L1 default ±5% count tolerance" against a grader that no longer has Gate 2 — rationale sentence corrected (docs-level wording fix; no tolerance value changed, no version bump owed).
- Broken-set scores re-measured under the weighted grader: 0.0 / 0.6666... / 0.8333... — identical to the recorded `measured_score` values, so no metadata update needed.
- `version` stays at 2: this pass made no instruction, grader, tolerance-value, or input change. The two repo-wide grader commits (363aed2, c749e57) did not bump versions anywhere; for this task they are score-neutral, and run validity is handled by the timestamp cutoff above.

### 3. Changes applied this run

#### Unilateral edits
- `README.md`: replaced stale Gate-2/Gate-1 detection claims in failure modes 3, 5, 6 with the current subcheck-based behaviour (including the new partial-credit consequence), removed two stale quotes of long-stripped prompt text, fixed `data/` → `inputs/` path. Re-grade on reference: 1.0. Reason: docs drifted from the post-2026-06-06 grader and the post-May prompt.
- `metadata.yaml`: corrected the tolerances rationale sentence that referenced the removed Gate 2 (wording only, no tolerance value changed). Re-grade on reference: 1.0. Reason: stale claim about grader structure.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (6/6 subchecks)
- grader on broken sets: wrong_format 0.0, kept_ordinal_suffix 0.6667, name_used_id 0.8333 (all match metadata.yaml)
- pytest: pass (41 passed)

---

## Evaluator review 2026-06-14 — weight recalibration  (evaluator-commit <pending>)

### Change (one line)
**RECALIBRATED**: replaced the blunt uniform `weight=3.0` on all six subchecks (from the repo-wide c749e57 sweep) with severity-tiered weights that make the central within-join checks dominate and treat the attribute-format gotcha and input passthrough as cosmetic. Grading-only; no version bump (task stays v2).

### Why the uniform weighting was miscalibrated
Under all-equal weights every subcheck is worth 1/6, so three failure classes of very different severity all collapsed to the **same 0.667**: an inverted/over-filtered join (wrong join *shape*, count+jaccard fail), a genuine within-join error (wrong arrondissement per amenity, number+name row fail), and the purely cosmetic ordinal-format slip (kept "20e" — join fully correct). A cosmetic slip should not cost the same as the central skill failing. The central skill here is **correct within/containment per amenity**, proven primarily by `arrondissement_number_per_row_match` and the join-shape checks (`exact_count_match`, `osm_id_set_jaccard`); `arrondissement_number_is_integer_1_to_20` is an attribute-*format* gate and `amenity_class_per_row_match` is a pure input passthrough — neither involves spatial reasoning.

### Weight changes
| Subcheck | Role | Old | New |
|---|---|---|---|
| exact_count_match | join shape (central) | 3.0 | 3.0 |
| osm_id_set_jaccard | join completeness (central) | 3.0 | 3.0 |
| arrondissement_number_per_row_match | correct containment per row (THE central skill) | 3.0 | 3.0 |
| arrondissement_name_per_row_match | containment via name; partly redundant, also catches id-vs-name slip | 3.0 | 2.0 |
| arrondissement_number_is_integer_1_to_20 | attribute-format gotcha (not spatial) | 3.0 | 1.0 |
| amenity_class_per_row_match | input passthrough (cosmetic) | 3.0 | 1.0 |

Total weight 18 → 13.

### Broken scores before → after
| Class | Before | After | Severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | gate fail (missing column) — unaffected by weights |
| kept_ordinal_suffix | 0.6667 | 0.6923 | cosmetic ordinal slip, join correct — sits above a real join error |
| name_used_id | 0.8333 | 0.8462 | lightest partial: column-pick slip, join + number fully correct |

Non-fixture failure classes (principled detectors, computed not measured): inverted/over-filter join → 0.538 (both weight-3 join-shape checks fail, most severe partial); genuine within-join error (wrong polygon per amenity, number+name row fail) → 0.615.

### Ordering check
Monotone and defensible: 0.0 (gate) < 0.538 (wrong join shape) < 0.615 (wrong containment) < 0.692 (cosmetic ordinal) < 0.846 (column-pick slip) < 1.0 (correct). The two fixture brokens keep their relative order and stay inside their `expected_score_range`. No disjoint-failure inversion: down-weighting `is_integer` (format) while keeping `number_per_row` at 3 preserves a strong wrong-containment signal, since `number_per_row` coerces and compares the value itself.

### Prior runs re-graded
The current-generation runs (run-20260607-112430Z, run-20260608-074701Z, run-20260609-084636Z) all re-grade to 1.0 (full pass) under the new weights — unchanged, as a full pass is 1.0 under any positive weighting and a gate failure is 0.0 regardless. No partial-scoring run exists at v2, so no prior-run score shifted. No significant shifts.

### Reasoning summary
The repo-wide c749e57 weighting was a no-op for this grader's *ordering* (uniform weights = unweighted ratio) and actively flattened three distinct severity tiers onto 0.667. The new tiering puts the largest score drops on the spatial-join core (shape, completeness, per-row containment) and the smallest drops on the format gotcha and the passthrough column, so a meaningful mistake now drops the score meaningfully while a cosmetic one only lightly. Logic, thresholds, and gates untouched.

### Changes applied
- `grade.py`: weight= edits on four subchecks (see table). No logic/threshold/gate change.
- `metadata.yaml`: updated `kept_ordinal_suffix` / `name_used_id` `measured_score` (0.6923 / 0.8462) and their weight-arithmetic prose.
- `README.md`: refreshed stale score fractions in failure modes 1, 2, 5, 6 and the weak-agent section.

### Tests run
- grader on reference: 1.0 (6/6 subchecks)
- grader on broken sets: wrong_format 0.0, kept_ordinal_suffix 0.6923, name_used_id 0.8462 (match updated metadata.yaml)
- pytest: not-run (orchestrator runs the suite)
