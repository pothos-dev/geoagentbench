# Implementation notes — geo-l2-nyc-park-symdiff

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L2 geometric-ops chain over a bundled two-layer GPKG (`parks_official`
≈ 1380 polygons, `parks_osm` ≈ 1372 polygons, both EPSG:6539). Agent
must symmetric-difference the two layers, cluster the result into
connected components, classify each cluster's `source`, collect into
one MultiPolygon per cluster, and emit point-on-surface label
anchors. Reference produces 46 clusters (20 official-only, 12
OSM-only, 14 `both`). Reference, grader, and three broken solutions
verified inside the project Docker container.

## Verification results
- Reference grader score: 1.000 (6 / 6 subchecks pass).
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    the anchors file (GeoParquet bytes under the `.geojson` name).
  - partial: 0.333 (expected range [0.25, 0.45]) — four subchecks
    fail (`count_within_tolerance`, `source_label_distribution`,
    `total_area_within_tolerance`, `unioned_geometry_iou`); two
    pass (`all_multipolygon_disagreement`,
    `anchors_inside_disagreements`).
  - centroids: 0.833 (expected range [0.75, 0.90]) — only
    `anchors_inside_disagreements` fails (31 / 46 anchors inside,
    threshold 0.99).
- Second-run output match: bit-identical (verified with `diff -q`
  on both `reference/outputs/parks_disagreement.geojson` and
  `reference/outputs/park_label_anchors.geojson` between two runs
  inside Docker; outputs are sorted by cluster bounds and pyogrio's
  GeoJSON writer is byte-stable for fixed inputs and pinned
  dependency versions).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Output not GeoJSON: broken_wrong_format
- Wrong output CRS: principled — Gate 1 CRS check
- Skipped cluster-collect (one row per symdiff polygon): principled
  — Gate 2 row-count tolerance (128 vs 46 ≈ 178 % off)
- Dropped one side of the symdiff: broken_partial
- Centroid instead of representative_point for anchors:
  broken_centroids
- Mislabelled `source` attribute: principled —
  `source_label_distribution` subcheck (set Jaccard + per-source
  count tolerance)
- Forgot MultiPolygon coercion: principled —
  `all_multipolygon_disagreement` subcheck
- Cluster / anchor cardinality mismatch: principled — Gate 2
  cardinality check

## Open issues
(none)

## Suggested prompt changes
(none)

## Inventory change proposals
- The inventory row's Overture theme is listed as
  `base.infrastructure`, but parks live in `base.land_use` with
  `subtype='park'` in the Overture schema (verified against release
  2026-04-15.0 — `base.infrastructure` carries bridges, dams, towers,
  utility installations, not parks). The bundled-input helper uses
  the closer `base.land_use` / `subtype='park'` match. Suggest
  updating the inventory row's Overture-themes column to
  `base.land_use` for this task.

## Library extensions
(none — grader uses `Gate`, `Subcheck`, `ScoreReport`,
`count_within_tolerance`, `iou_with_tolerance`, and
`jaccard_similarity_set`. Per-source count comparison is inline
because the small-integer-distribution-with-tolerance pattern is
specific to this task; not yet generic enough to warrant a primitive.)

## Runtime
~30 minutes (Overture probe + slice ~45 s, reference run ~25 s,
broken-solution generation ~15 s; all runs inside the project
Docker container).

---

# Evaluator review log

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is a bundled L2 geometric-ops chain over a two-layer NYC parks
GeoPackage (~1380 official polygons, ~1372 OSM-derived polygons in
EPSG:6539). The agent must symmetric-difference the two layers, cluster
the result into connected components, classify each cluster's `source`
attribute (`parks_official` | `parks_osm` | `both`), collect into one
MultiPolygon per cluster, and emit a point-on-surface label anchor per
cluster — testing the "symdiff + cluster + classify + label-anchor"
chain with a concave-cluster trap on `centroid` vs `representative_point`.
At initial authoring the agent was also told the GPKG layers and outputs
were both in EPSG:6539 (NY State Plane Long Island). The inventory row
lists the Overture theme as `base.infrastructure`, but the bundled-input
helper uses `base.land_use` / `subtype='park'` — the author flagged the
inventory mismatch in metadata.yaml notes and IMPLEMENTATION_NOTES.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 40d3a93 | initial-authoring | Initial task (data, grader, reference, broken sets) | (initial) |
| 2026-05-08 | 001e459 | docs-change | Split benchmark into authoring/ and eval/ subtrees | Repo reorganization (not task-specific) |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ to benchmark/tasks/ | Repo reorganization (not task-specific) |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md | Asset prep |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Asset prep |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded structured "Output schema:" bullet list into prose; instruction otherwise unchanged | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task card image via FLUX schnell | Asset refresh |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card image via nano-banana-2 | Asset refresh |
| 2026-05-14 | f40e39e | prompt-change | Removed "GeoPackage with two layers, `parks_official` and `parks_osm`, both in NY State Plane Long Island (EPSG:6539)" — now just "GeoPackage with official and OSM-derived park layers" | Commit msg: "Strip deducible information from GEO task instructions" |
| 2026-05-15 | 6500d9a | prompt-change | Dropped trailing "not merely at its centroid" qualifier from anchor-inside requirement | Commit msg: "Strip deducible information from GEO task instructions (batch 2)" |
| 2026-05-17 | 64740d0 | prompt-change | Reworded "discrepancy clusters" → "adjacent disagreement patches merged together"; "cluster" → "group" throughout; dropped explicit "in EPSG:6539" output CRS hint | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" (note: although the commit message is data-cleaning-themed, this task was included in the batch) <!-- HUMAN-REVIEW id="HR-003" category="design-rationale" severity="low" --> Why the geo task was bundled with the dc-* batch is not stated in the commit message |
| 2026-05-17 | db638f4 | mixed (grader-change + prompt-change) | Grader: replaced strict `EPSG:6539` Gate-1 CRS check with `is_wgs84()` (accepts EPSG:4326 / OGC:CRS84) and reprojects submission to EPSG:6539 internally for geometric comparison. task.json `tags.crs` and `expected_outputs[].crs` flipped from `EPSG:6539` to `EPSG:4326`. Reference solution and reference outputs were NOT updated and remain in EPSG:6539. | Commit msg: "Fix graders and prompts for 6 tasks that regressed after nudge removal" |
| 2026-05-26 | 29a9ae3 | mixed (file moves) | Folder reorganization: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md; data/ → inputs/; reference/{generate.py,outputs/} → reference/solution/; tests/ → reference/failures/; image assets → assets/. grade.py path constants updated accordingly. File contents otherwise unchanged. | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T19:17:27+00:00 (commit db638f4, class: mixed — grader+prompt). Later folder-reorg commit 29a9ae3 (2026-05-26T09:51:37Z) renamed paths but did not change semantics for either the grader or the agent-visible instruction; runs after 2026-05-17T19:17:27Z are treated as `current`.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:01:06Z | 0.0 | done (failed — model-side: agent could not install `fiona` and never wrote outputs) | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T17:51:25Z | 1.0 | done | stale (pre-cutoff: graded against the pre-db638f4 grader that required EPSG:6539 — submission was EPSG:6539) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:49:37Z | 0.0 | done | stale (pre-cutoff) |
| 24 earlier runs | various claude/openrouter | 2026-05-12 … 2026-05-17 | mostly 1.0 | done | stale (pre-cutoff) |

Footnote on stale runs: the 22 runs that scored 1.0 before 2026-05-17T19:17:27Z all wrote outputs in EPSG:6539, matching the original (pre-fix) grader. After the grader flipped to require WGS 84, none of those submissions would pass Gate 1 unchanged. Stale runs cannot be used to claim the task is calibrated under the current grader.

#### Verdict
**insufficient-evidence**

Only one `current` run exists, and it is a clear model-side failure: the openrouter-gemma4-26b agent could not install `fiona` (gdal-config missing in the sandbox), gave up, and never wrote the two expected GeoJSON outputs. Per the evaluator prompt, model-side failures are not task problems and do not constitute evidence the task is too strict or too easy. No agent under the current (post-db638f4) grader has yet produced output for this task, so calibration cannot be confirmed or refuted from runs.

However, an independent inspection of the current state surfaces a concrete grader/reference inconsistency that needs human attention (see specific findings below). The grader and instruction are mutually consistent — both expect WGS 84 output — but the **reference outputs in `reference/solution/outputs/` are in EPSG:6539**, and `reference/solution/generate.py` writes EPSG:6539 by design. Running the grader on the reference itself fails Gate 1 with `disagreement CRS is 6539, expected WGS 84`. This violates the evaluator-prompt invariant that "re-grade on reference must be ≥ 0.95". The grading of *agent* submissions is still correct (submission in WGS 84 is reprojected internally to EPSG:6539 for geometric comparison against the 6539 reference) — but the reference cannot self-validate.

#### Specific findings
- The reference outputs (`reference/solution/outputs/parks_disagreement.geojson` and `park_label_anchors.geojson`) are in EPSG:6539, while Gate 1 of `grade.py` requires WGS 84. Running `uv run python grade.py reference/solution/outputs` returns score 0.0 with the message `disagreement CRS is 6539, expected WGS 84`. The fix is to regenerate the reference outputs in EPSG:4326 (modify `reference/solution/generate.py` to call `to_crs("EPSG:4326")` before `to_file`, and re-run the generator). This requires editing `reference/solution/generate.py` and `reference/solution/outputs/`, which the evaluator prompt forbids unilaterally. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="med" --> Regenerate `reference/solution/outputs/*.geojson` in EPSG:4326 and update `reference/solution/generate.py` to write WGS 84, so the reference re-grade invariant holds. Score on agent submissions is unaffected by this fix.
- `metadata.yaml > notes` and `IMPLEMENTATION_NOTES` flag that the inventory row uses Overture theme `base.infrastructure`, while the bundled inputs are sliced from `base.land_use` / `subtype='park'`. The inventory row at `benchmark/authoring/inventory.md` line 610 still reads `base.infrastructure`. This was an author-proposed inventory change that has not been merged. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Update inventory.md line 610 to `base.land_use` to match the actual data source.
- The 2026-05-17 nudge-removal commit (64740d0) — described in its message as a data-cleaning-task batch — included this geometric-ops task. The wording changes (cluster → group, dropping the EPSG:6539 output hint) match the dc-batch theme of removing answer-giving nudges, but the commit message does not state why a geo task was bundled into the dc batch. Low severity — the changes themselves look defensible as nudge removal, just under-explained. Flagged above as HR-003.
- `metadata.yaml > tolerances.rationale` mentions per-source count tolerance of ±20 %; the grader code reads `PER_SOURCE_TOL = 0.20`. Consistent. No flag.
- `metadata.yaml > broken_solutions.measured_score` values (0.0, 0.3333, 0.8333) are not re-verified this evaluator run because the broken sets cannot be re-graded without first fixing the reference (every broken set would also fail Gate 1 for the same EPSG:6539 reason — the broken solutions were generated from the reference outputs with the same CRS). Re-verify after HR-001 is resolved.

### 3. Changes applied this run

#### Unilateral edits
- (none — every candidate edit lives in `reference/solution/` or `inputs/` and is therefore out of scope for unilateral application; the grader and instruction are mutually consistent and need no change.)

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — regenerate reference outputs in EPSG:4326 so the reference passes Gate 1 of its own grader
- HR-002 — inventory-mismatch — update `inventory.md` Overture-themes column from `base.infrastructure` to `base.land_use`
- HR-003 — design-rationale — clarify why this geometric-ops task was bundled in the 2026-05-17 dc-batch "nudge removal" commit

#### Tests run
- grader on reference: 0.0 (Gate 1 fails: reference is EPSG:6539, grader expects WGS 84). See HR-001.
- pytest (benchmark/eval): 35 passed.

## Evaluator review 2026-05-26 (evidence-gather follow-up)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new design-affecting commits since the prior evaluator block. `git log --follow`
on the task directory shows the most recent commit is the prior evaluator's own
artefact commit (69d556c, 2026-05-26T14:35Z), preceded by the folder reorg
(29a9ae3) and the grader/prompt fix (db638f4, 2026-05-17T19:17Z). The design
history reconstructed in the prior block (above) stands unchanged; I do not repeat
the change-log table. The design-affecting cutoff is unchanged at
**2026-05-17T19:17:27Z (commit db638f4)**.

This follow-up re-evaluation was triggered because two fresh runs (opus + gemma)
were added for this task after the prior evaluator's `insufficient-evidence`
verdict, and the orchestrator asked specifically whether live agent submissions
still grade correctly given the EPSG:6539-reference / WGS84-grader split.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T19:17:27Z (commit db638f4, class: mixed — grader+prompt). Unchanged from prior block.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:03:48Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:47:20Z | 0.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:01:06Z | 0.0 | done (model-side: no outputs) | current |
| earlier runs (≤ 2026-05-17) | various | — | mostly 1.0 | done | stale (pre-cutoff; graded against pre-db638f4 grader) |

#### Verdict
**calibrated** (for agent grading), with a persisting reference/test-fixture defect carried over as HR-001.

The orchestrator's question — *do live agent submissions still grade correctly?* —
is answered **yes**, with decisive evidence from two current runs of two different
agent families:

- **opus (1.0).** Wrote both GeoJSONs in **WGS84 (EPSG:4326)** — verified: bounds
  (-74.0498, 40.6569, -73.8556, 40.8698), 46 MultiPolygon clusters. The grader's
  Gate 1 `is_wgs84()` accepted it, reprojected internally to EPSG:6539
  (`grade.py:163-164`), and all 6 subchecks passed perfectly (count 46/46, area
  rel-diff 0.0000, IoU 1.0000, source distribution Jaccard 1.000, 46/46 anchors
  inside). This proves the WGS84-submission → reproject → compare-against-6539-ref
  path is sound.
- **gemma (0.0).** Wrote both files in **EPSG:6539** (bounds in the ~970k–1024k
  metre range, characteristic of NY State Plane) with **128 rows** (no
  cluster-collect). Gate 1 correctly rejected on `disagreement CRS is 6539,
  expected WGS 84`. This is a genuine double task-failure — wrong output CRS
  (README failure-mode #2) AND skipped cluster-collect (failure-mode #3) — that the
  grader is designed to catch. The 0.0 is the correct outcome, not a grader bug.

The instruction and grader are mutually consistent (both expect WGS84 GeoJSON
output): `expected_outputs[].crs == "EPSG:4326"`, the redundant output-schema
sentence names GeoJSON, and GeoJSON ⇒ WGS84 by RFC 7946 convention. A capable
agent inferred this; a weak agent echoed the input's native 6539 into the GeoJSON.
The split between EPSG:6539 (input/internal) and WGS84 (output) is therefore part
of what the task legitimately tests, not a miscalibration.

#### Specific findings
- **HR-001 (carried forward, confirmed and escalated in scope).** The reference
  outputs in `reference/solution/outputs/*.geojson` are EPSG:6539; running
  `grade.py reference/solution/outputs` returns **0.0** (Gate 1: `disagreement CRS
  is 6539, expected WGS 84`). This violates the "re-grade on reference ≥ 0.95"
  invariant. **New this run:** I re-graded all three broken solutions and confirmed
  the defect has propagated to the test fixtures — the brokens were generated *from*
  the 6539 reference (`_make_brokens.py:41 TARGET_CRS = "EPSG:6539"`), so they are
  all EPSG:6539:
    - `broken_wrong_format`: 0.0 — still correct (fails on the GeoParquet anchors).
    - `broken_partial`: **0.0** — metadata declares [0.25, 0.45] / measured 0.3333;
      now collapses to Gate-1 CRS rejection before any subcheck runs.
    - `broken_centroids`: **0.0** — metadata declares [0.75, 0.90] / measured 0.8333;
      now collapses to Gate-1 CRS rejection before any subcheck runs.
  Consequence: the grader's three broken scores are no longer in *distinct* ranges
  (0.0, 0.0, 0.0) — the anti-tautology "grader has resolution" guarantee is broken,
  and `metadata.yaml > broken_solutions > measured_score` (0.0/0.3333/0.8333) is now
  stale. The fix is the same single root cause as the prior HR-001: regenerate the
  reference outputs (and the derived broken sets) in EPSG:4326 by having
  `reference/solution/generate.py` and `_make_brokens.py` write WGS84. Both live
  under `reference/`, which the evaluator may not edit unilaterally — flagged.
  Agent grading is unaffected by this fix (the opus 1.0 already demonstrates correct
  agent grading); the defect is confined to reference self-validation and broken-set
  resolution. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="med" --> Regenerate `reference/solution/outputs/*.geojson` AND `reference/failures/broken_*/outputs/*.geojson` in EPSG:4326 (edit `reference/solution/generate.py` and `reference/failures/_make_brokens.py` to write WGS84), then re-grade: reference must score ≥ 0.95 and the three broken sets must return to distinct ranges (~0.0 / ~0.33 / ~0.83). Update `metadata.yaml > broken_solutions > measured_score` afterwards.
- **HR-002 (carried forward, unchanged).** `authoring/inventory.md` line 610 lists
  Overture theme `base.infrastructure`; the bundled inputs are sliced from
  `base.land_use` / `subtype='park'` (author-flagged in metadata.yaml notes and
  IMPLEMENTATION_NOTES). The inventory row has not been updated. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Update inventory.md line 610 Overture-themes column from `base.infrastructure` to `base.land_use`.
- **HR-003 (carried forward, unchanged).** Commit 64740d0 ("Remove answer-giving
  nudges from data-cleaning task prompts", 2026-05-17) modified this geometric-ops
  task's instruction. The wording changes (cluster → group; dropped the explicit
  EPSG:6539 output hint) are defensible as nudge removal, but the commit message
  does not explain why a geo task was bundled into a dc-batch. <!-- HUMAN-REVIEW id="HR-003" category="design-rationale" severity="low" --> Clarify the rationale for bundling this geometric-ops task into the 2026-05-17 data-cleaning nudge-removal batch.
- The prior block's verdict was `insufficient-evidence` because the only current
  run then was a model-side failure. Two current runs from distinct agent families
  now exist (opus 1.0, gemma 0.0, both correct), so the agent-facing verdict is
  upgraded to `calibrated`. The verdict change reflects new run evidence, not any
  change to the task.

### 3. Changes applied this run

#### Unilateral edits
- (none — the only defect requiring code change, HR-001, lives entirely under
  `reference/`, which the evaluator may not edit unilaterally. The grader and
  instruction are mutually consistent and need no change. coverage.yaml's
  `evaluator_run_at` timestamp refreshed; no semantic change.)

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — regenerate reference outputs AND broken sets in EPSG:4326 so the reference self-validates and the broken sets regain distinct score ranges (now all 0.0)
- HR-002 — inventory-mismatch — update inventory.md line 610 Overture theme to `base.land_use`
- HR-003 — design-rationale — clarify why this geo task was in the 2026-05-17 dc nudge-removal batch

#### Tests run
- grader on reference (`reference/solution/outputs`): 0.0 (Gate 1: EPSG:6539 ≠ WGS84). See HR-001.
- grader on broken sets: wrong_format 0.0 (intended), partial 0.0 (intended 0.333), centroids 0.0 (intended 0.833) — two collapsed to Gate-1 CRS rejection. See HR-001.
- grader on live agent submissions: opus run-20260526-1753Z = 1.0 (6/6 subchecks); gemma run-20260526-1922Z = 0.0 (correct — agent wrote 6539, 128 rows). Agent grading verified sound.
- pytest (benchmark/eval): 35 passed.

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the prior two evaluator blocks: a bundled L2 geometric-ops chain
over a two-layer NYC parks GeoPackage (1380 official polygons, 1372 OSM-derived,
both EPSG:6539). The agent symmetric-differences the two layers, clusters the
result into connected components, classifies each cluster's `source`
(`parks_official` | `parks_osm` | `both`), collects into one MultiPolygon per
cluster, and emits a point-on-surface label anchor — testing
"symdiff + cluster + classify + label-anchor" with a concave-cluster trap on
`centroid` vs `representative_point`. I do not repeat the full change-log table
from the prior blocks; only the one new design-affecting commit is added below.

#### Change log (delta since prior evaluator block)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-27 | 1f4a85c | mixed (reference-change + grader-change + docs-change) | Reference outputs regenerated in WGS84 (EPSG:4326); `reference/solution/generate.py` now reprojects to EPSG:4326 before writing while keeping `area_m2` in projected metres; `grade.py` dropped the one-sided submission→6539 reproject and instead reprojects BOTH sides to EPSG:6539 only for the area-sum subcheck; README aligned to WGS84 (output-CRS and failure-mode #2 wording). | Commit msg: "Store bangkok/nyc-park reference output in WGS84, drop one-sided grader reproject" — resolves the prior HR-001 reference/grader CRS split so the reference self-grades 1.0; states existing opus/gemma run scores are unchanged. This is the human fix for the prior blocks' HR-001 core defect. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-27T14:06:03Z** (commit 1f4a85c, class: mixed — reference-change + grader-change). This advances the cutoff past every recorded run; all 29 stored runs now pre-date it and are `stale` by timestamp. Agent-facing calibration is instead established by re-grading the two most-recent submissions' on-disk output files against the current grader (see below) — the rigorous equivalent of a current run for the unchanged-submission case the fix commit asserts.

#### Runs considered
| Run | Adapter | Started | Stored score | Re-graded (current grader) | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:03:48Z | 1.0 | **1.0** (6/6 subchecks) | stale by ts; re-graded current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:47:20Z | 0.0 | **0.0** (Gate 1: wrote EPSG:6539) | stale by ts; re-graded current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:01:06Z | 0.0 | — (model-side: no outputs written) | stale by ts |
| 26 earlier runs (≤ 2026-05-17) | various claude/openrouter | 2026-05-12 … 2026-05-17 | mostly 1.0 | — | stale (graded against pre-db638f4 grader; outputs were EPSG:6539) |

Footnote: all 29 stored runs started before the new cutoff, so none is `current` by timestamp. Rather than treat the task as `insufficient-evidence`, I re-graded the two on-disk submissions from the two most-recent distinct agent families against the current (post-1f4a85c) grader. Opus's WGS84 submission scores a clean 1.0 (all six subchecks pass); gemma's EPSG:6539 submission is correctly rejected at Gate 1. This confirms the fix commit's claim ("existing opus/gemma runs score unchanged") and establishes agent-facing calibration from two agent families under the current grader.

#### Verdict
**calibrated**

The prior two evaluator blocks' central defect (HR-001: reference outputs in EPSG:6539 while the grader required WGS84, so the reference self-graded 0.0 and the broken sets collapsed) has been **resolved at its root** by commit 1f4a85c. Verified this run:

- `grade.py reference/solution/outputs` now returns **1.0** (6/6 subchecks). The reference self-validates above the 0.95 invariant.
- 2c-CRS consistency now holds end-to-end: reference outputs are EPSG:4326 (verified: bounds -74.0498, 40.6569, -73.8556, 40.8698; 46 MultiPolygon clusters; 46 Point anchors); `expected_outputs[].crs == "EPSG:4326"`; README states "WGS84 (EPSG:4326)"; and the grader's only metric-CRS use is the area subcheck, which reprojects **both** sides to EPSG:6539 (`grade.py:246-247`) — the permitted two-sided transform, not a one-sided submission reproject.
- Source distribution matches the README exactly (20 `parks_official`, 12 `parks_osm`, 14 `both`); total disagreement area ≈ 5.18 km².
- Re-grading the two latest submissions confirms agent grading is sound and discriminating (opus 1.0, gemma 0.0).

One narrower defect persists and is carried forward as HR-001 (see below): the three broken-solution fixtures were not regenerated by 1f4a85c and remain EPSG:6539, so the grader has lost resolution **on its own test fixtures** (though not on real agent submissions). This does not change the agent-facing verdict but must be fixed to restore the anti-tautology resolution guarantee.

#### Specific findings
- **HR-001 (carried forward, narrowed to the broken fixtures only).** Commit 1f4a85c regenerated `reference/solution/outputs/*.geojson` in WGS84 and updated the grader, but did **not** regenerate the broken-solution fixtures. `reference/failures/_make_brokens.py:41` still sets `TARGET_CRS = "EPSG:6539"`, and all three `reference/failures/broken_*/outputs/parks_disagreement.geojson` files declare `urn:ogc:def:crs:EPSG::6539`. Re-grading this run: `broken_wrong_format` 0.0 (still correct — fails on the GeoParquet anchors), but `broken_partial` **0.0** (metadata declares [0.25, 0.45] / measured 0.3333) and `broken_centroids` **0.0** (metadata declares [0.75, 0.90] / measured 0.8333) — both now collapse to Gate 1 (`disagreement CRS is 6539, expected WGS 84`) before any subcheck runs. The grader's three broken scores are therefore no longer in distinct ranges (0.0 / 0.0 / 0.0), and `metadata.yaml > broken_solutions > measured_score` is stale for `partial` and `centroids`. The fix is to regenerate the broken sets in EPSG:4326 (set `_make_brokens.py` to write WGS84 / derive from the now-WGS84 reference, then re-run it) and update the two stale `measured_score` values. `reference/failures/` is off-limits to the evaluator, so this is flagged. Agent grading is unaffected (opus 1.0 / gemma 0.0 verified above). <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="med" --> Regenerate `reference/failures/broken_*/outputs/*.geojson` in EPSG:4326 (update `reference/failures/_make_brokens.py` `TARGET_CRS`/write-CRS to WGS84 and re-run it against the now-WGS84 reference), then confirm the three broken sets return to distinct ranges (~0.0 / ~0.33 / ~0.83) and update `metadata.yaml > broken_solutions > measured_score` for `partial` and `centroids`.
- **HR-002 (carried forward, unchanged).** `authoring/inventory.md` line 610 (Overture-themes column) and the data-source field on line 600 still list `base.infrastructure`, and the coverage matrix on line 1096 maps `base.infrastructure → geo-l2-nyc-park-symdiff` as its sole task; but the bundled inputs are sliced from `base.land_use` / `subtype='park'` (author-flagged in `metadata.yaml` notes and the author block above). The inventory has not been corrected. Note for the human: correcting this row would leave the `base.infrastructure` coverage row (line 1096) with zero tasks — a coverage-completeness question to resolve alongside the theme fix. `coverage.yaml` here uses the truer `base.land_use` slug. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Update `inventory.md` (line 600 data-source field, line 610 Overture-themes column, and the line-1096 coverage-matrix row) from `base.infrastructure` to `base.land_use`, and re-check `base.infrastructure` coverage completeness.
- **HR-003 (carried forward, unchanged).** Commit 64740d0 ("Remove answer-giving nudges from data-cleaning task prompts", 2026-05-17) modified this geometric-ops task's instruction (cluster → group wording; dropped the explicit EPSG:6539 output hint). The changes are defensible as nudge removal, but the commit message does not explain why a geo task was bundled into a data-cleaning batch. <!-- HUMAN-REVIEW id="HR-003" category="design-rationale" severity="low" --> Clarify the rationale for bundling this geometric-ops task into the 2026-05-17 data-cleaning nudge-removal batch.
- The instruction's redundant output-schema sentence names "two GeoJSON FeatureCollections" and the format pins WGS84 by RFC 7946 convention; no explicit EPSG code is given to the agent. This is the intended design after the 2026-05-17 nudge removal and the 1f4a85c CRS alignment — the EPSG:6539-input → WGS84-output split is part of what the task legitimately tests. No gift to strip. No flag.

### 3. Changes applied this run

#### Unilateral edits
- (none — the only remaining defect, HR-001, lives entirely under `reference/failures/`, which the evaluator may not edit unilaterally. The grader, instruction, README, and reference outputs are now mutually consistent on WGS84 and need no evaluator change. `coverage.yaml` had its `evaluator_run_at` timestamp and HR-001 note refreshed to reflect the resolved reference; no slug/semantic change.)

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — regenerate the three broken-solution fixtures in EPSG:4326 (they were missed by commit 1f4a85c) so the grader regains distinct broken-score ranges; update the two stale `metadata.yaml` measured_scores
- HR-002 — inventory-mismatch — update `inventory.md` Overture theme from `base.infrastructure` to `base.land_use` (and re-check coverage completeness)
- HR-003 — design-rationale — clarify why this geo task was in the 2026-05-17 dc nudge-removal batch

#### Tests run
- grader on reference (`reference/solution/outputs`): **1.0** (6/6 subchecks). Reference self-validates after the 1f4a85c fix.
- grader on broken sets: wrong_format 0.0 (intended [0.0, 0.0]); partial **0.0** (intended [0.25, 0.45] / measured 0.3333 — now collapsed to Gate-1 CRS rejection); centroids **0.0** (intended [0.75, 0.90] / measured 0.8333 — now collapsed to Gate-1 CRS rejection). See HR-001.
- grader on on-disk agent submissions (re-graded against current grader): opus run-20260526-1753Z = **1.0** (6/6 subchecks); gemma run-20260526-1922Z = **0.0** (Gate 1: wrote EPSG:6539). Agent grading verified sound and discriminating.
- pytest (benchmark/eval): **35 passed**.

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior evaluator blocks: a bundled L2 geometric-ops chain over a
two-layer NYC parks GeoPackage (1380 official polygons, 1372 OSM-derived,
both EPSG:6539). Agent symmetric-differences the two layers, clusters into
connected components, classifies each cluster's `source`, collects into one
MultiPolygon per cluster, and emits a point-on-surface label anchor. Full
change-log table not repeated; only the new design-affecting commit is below.

#### Change log (delta since prior evaluator block)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | mixed (docs-change + minor metadata-change) | Repo-wide: added integer `version` field to `task.json` schema (snapshotted into run.json/session.json and dimmed in UI when outdated); dropped unused `prompt_version` from `metadata.yaml`. This task did not yet receive an explicit `version` — it remained implicitly v1. | Commit msg: "Add task content versioning; drop unused prompt_version" — generic infrastructure change, not task-specific design. |

The prior block's design-affecting commit (1f4a85c, 2026-05-27T14:06:03Z —
reference outputs regenerated in WGS84, grader switched to two-sided area
reproject, README aligned) remains the most recent semantic change to the
task itself. Commit 622342b is repo-wide infrastructure (no impact on
grader/inputs/instruction contract) — its `metadata.yaml` edit (dropping
`prompt_version`) does not change anything the agent or grader sees.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-27T14:06:03Z** (commit 1f4a85c, class: mixed — reference-change + grader-change + docs-change). Commit 622342b touches `metadata.yaml` but only removes an unused authoring template tag, not a grader-visible tolerance or contract; it is not design-affecting for this task. Cutoff unchanged from prior block.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:08:13Z | 0.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T02:44:29Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:57:07Z | 0.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T22:25:23Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:47:20Z | 0.0 | done | stale (pre-cutoff) |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:03:48Z | 1.0 | done | stale (pre-cutoff) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:01:06Z | 0.0 | done (model-side: no outputs) | stale (pre-cutoff) |
| 26 earlier runs (≤ 2026-05-17) | various | 2026-05-12 … 2026-05-17 | mostly 1.0 | done | stale (graded against pre-db638f4 grader) |

Re-grading the four current runs against the current grader matches their
stored scores exactly: opus 1.0/1.0 (both WGS84 submissions, 6/6 subchecks),
gemma 0.0/0.0 (both EPSG:6539 submissions, Gate-1 CRS rejection). Two agent
families × two runs each — the agent-facing calibration evidence is strong.

#### Verdict
**calibrated**

The grader, instruction, README, reference outputs, and `expected_outputs[]`
are mutually consistent on WGS84 GeoJSON output (RFC 7946). Reference
self-grades 1.0 (6/6 subchecks). 2c-CRS consistency holds end-to-end:
reference outputs are EPSG:4326 (`urn:ogc:def:crs:OGC:1.3:CRS84`),
`expected_outputs[].crs == "EPSG:4326"`, README states "WGS84 (EPSG:4326)",
and the grader's only metric-CRS use is the area subcheck, which reprojects
**both** sides to EPSG:6539 (`grade.py:246-247`) — the permitted two-sided
transform, not a one-sided submission reproject. Four current runs from two
agent families confirm sound, discriminating agent grading (opus 1.0,
gemma 0.0 — opus emits WGS84, gemma emits EPSG:6539 and is correctly
Gate-1-rejected).

The narrower defect carried over from the prior block — the three
`reference/failures/broken_*` fixtures were not regenerated by commit
1f4a85c and remain EPSG:6539, so `broken_partial` and `broken_centroids`
both collapse to 0.0 (Gate-1 CRS rejection) instead of their designed 0.333
and 0.833. The grader has lost resolution **on its own test fixtures**, not
on real agent submissions. Re-flagged as HR-001 (unchanged scope).

#### Specific findings
- **HR-001 (carried forward, unchanged).** `reference/failures/_make_brokens.py:41` still sets `TARGET_CRS = "EPSG:6539"`; all three broken-fixture disagreement files declare `urn:ogc:def:crs:EPSG::6539`. Re-grading this run: `broken_wrong_format` 0.0 (intended); `broken_partial` **0.0** (intended [0.25, 0.45] / metadata.measured 0.3333 — now Gate-1 CRS rejection); `broken_centroids` **0.0** (intended [0.75, 0.90] / metadata.measured 0.8333 — now Gate-1 CRS rejection). Broken scores are no longer in distinct ranges (0.0 / 0.0 / 0.0); `metadata.yaml > broken_solutions > measured_score` is stale for `partial` and `centroids`. `reference/failures/` is off-limits to unilateral evaluator edits. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="med" --> Regenerate `reference/failures/broken_*/outputs/*.geojson` in EPSG:4326 (update `reference/failures/_make_brokens.py` `TARGET_CRS`/write-CRS to WGS84 and re-run it against the now-WGS84 reference), then confirm the three broken sets return to distinct ranges (~0.0 / ~0.33 / ~0.83) and update `metadata.yaml > broken_solutions > measured_score` for `partial` and `centroids`. The human applying this fix should also bump `task.json > version` only if the broken-set refresh changes the grader contract — pure fixture regeneration without grader edits does not require a bump.
- **HR-002 (carried forward, unchanged).** `authoring/inventory.md` line 600 data-source field and line 610 Overture-themes column still list `base.infrastructure`; the coverage-matrix row on line 1096 maps `base.infrastructure → geo-l2-nyc-park-symdiff` as its sole task. Actual bundled inputs are sliced from `base.land_use` / `subtype='park'` (author-flagged in `metadata.yaml` notes and the author block). `coverage.yaml` here uses the truer `base.land_use` slug. Correcting the inventory row leaves the `base.infrastructure` coverage row with zero tasks. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Update `inventory.md` (line 600 data-source field, line 610 Overture-themes column, and the line-1096 coverage-matrix row) from `base.infrastructure` to `base.land_use`, and re-check `base.infrastructure` coverage completeness.
- **HR-003 (carried forward, unchanged).** Commit 64740d0 ("Remove answer-giving nudges from data-cleaning task prompts", 2026-05-17) modified this geometric-ops task's instruction. The wording changes look defensible as nudge removal, but the commit message does not explain why a geometric-ops task was bundled into a data-cleaning batch. <!-- HUMAN-REVIEW id="HR-003" category="design-rationale" severity="low" --> Clarify the rationale for bundling this geometric-ops task into the 2026-05-17 data-cleaning nudge-removal batch.
- **Redundant-statement strip applied this run (Step 4 unilateral).** The instruction's para-2 output-schema sentence repeated three constraints already pinned by `expected_outputs[]` or already stated in para 1:
  - "with MultiPolygon geometry" — duplicate of `expected_outputs[0].geometry_type = "MultiPolygon"` and of para 1's "One MultiPolygon per merged group".
  - "with Point geometry" — duplicate of `expected_outputs[1].geometry_type = "Point"` and of para 1's "label-anchor point".
  - "each Point guaranteed to lie inside its parent group" — duplicate of para 1's "label-anchor point that falls strictly inside the group's geometry".
  Stripped per the task-evaluator-prompt Step 4 "tighten redundant statements within the instruction" rule (added in commit 79818f0). Kept: the redundant output-schema sentence frame (two-file FeatureCollection introduction — intentional safety net per instruction-stripping-guide), the `source` column references (identity-key info not present in `expected_outputs[]`), and the "exactly one anchor per disagreement group, in matching order" cardinality/ordering hint (not in `expected_outputs[]`). Reference re-grade after edit: 1.0. Bumped `task.json.version` from implicit-1 to explicit-2 (first meaningful prompt edit since the versioning field was added in commit 622342b).

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: stripped three redundant clauses from the para-2 output-schema sentence ("with MultiPolygon geometry", "with Point geometry", "each Point guaranteed to lie inside its parent group"). All three were duplicates of `expected_outputs[].geometry_type` and/or para 1's canonical statements. Re-grade on reference: **1.0** (6/6 subchecks). Reason: mechanical de-duplication per Step 4 "tighten redundant statements" rule.
- `task.json`: added `"version": 2` field (was implicitly v1). Required because the instruction edit is a meaningful change to the prompt contract per the Step-4 versioning rule.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — regenerate the three broken-solution fixtures in EPSG:4326 (still missed since commit 1f4a85c); update the two stale `metadata.yaml` measured_scores
- HR-002 — inventory-mismatch — update `inventory.md` Overture theme from `base.infrastructure` to `base.land_use` (and re-check coverage completeness)
- HR-003 — design-rationale — clarify why this geo task was in the 2026-05-17 dc nudge-removal batch

#### Tests run
- grader on reference (`reference/solution/outputs`): **1.0** (6/6 subchecks). Reference self-validates after both the 1f4a85c CRS fix and this run's redundancy strip.
- grader on broken sets: wrong_format 0.0 (intended [0.0, 0.0]); partial **0.0** (intended [0.25, 0.45] / metadata.measured 0.3333 — Gate-1 CRS rejection); centroids **0.0** (intended [0.75, 0.90] / metadata.measured 0.8333 — Gate-1 CRS rejection). See HR-001.
- grader on four current on-disk agent submissions: run-20260527-2016Z opus = **1.0**; run-20260527-2321Z gemma = **0.0** (Gate 1: EPSG:6539); run-20260528-0113Z opus = **1.0**; run-20260528-0317Z gemma = **0.0** (Gate 1: EPSG:6539). Two agent families × two runs each — agent grading verified sound and discriminating.
- pytest (benchmark/eval): **41 passed**.

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior evaluator blocks: a bundled L2 geometric-ops chain over a
two-layer NYC parks GeoPackage (1380 official polygons, 1372 OSM-derived, both
EPSG:6539). Agent symmetric-differences the two layers, clusters into connected
components, classifies each cluster's `source`, collects into one MultiPolygon
per cluster, and emits a point-on-surface label anchor. Full change-log table
not repeated; only new design-affecting commits are listed below.

#### Change log (delta since prior evaluator block)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 03adf41 | mixed (reference-change + tests-change + docs-change) | Flipped `reference/failures/_make_brokens.py:TARGET_CRS` to EPSG:4326 and regenerated all three broken-fixture output files in WGS84. metadata `measured_score` already matched. Cleared HR-001 entries from `audit/status.json`. | Commit msg: "Resolve geo-l2-nyc-park-symdiff HR-001 via WGS84 broken fixtures" — directly resolves the prior block's HR-001 (broken fixtures stuck in EPSG:6539). |
| 2026-05-28 | 05aabd6 | grader-change | Repo-wide soft-CRS refactor: introduced `geo_grading.grade_crs_soft`. This task's `grade.py` now uses `grade_crs_soft(treat_none_as_wgs84=True)` instead of hard-failing Gate 1 on non-canonical CRS. Two new subchecks added at the end: `crs_is_canonical` and `crs_in_meaningful_set`. `MEANINGFUL_EPSGS = {4326}` (defaults to canonical-only). Submission CRS is now reprojected to canonical for downstream subchecks rather than hard-rejecting. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — a wrong-CRS submission with correct geometry no longer collapses to 0; it loses 2/8 points instead of all 8/8. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57Z** (commit 05aabd6, class: grader-change). This is the most recent commit that touched `grade.py` semantics. Earlier commit 03adf41 (2026-05-28T16:22Z) regenerated broken fixtures and is older than 05aabd6.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T21:52:26Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:17:26Z | 0.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:29:29Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:03:39Z | 0.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T17:10:58Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:18:14Z | 0.625 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:36:47Z | 0.75 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled | current (excluded; no score) |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:43:50Z | 0.0 | done | stale (pre-cutoff: pre-soft-CRS grader) |
| earlier runs (≤ 2026-05-28) | various | — | mixed | done | stale (pre-cutoff) |

Seven `current` runs across three agent families (opus, gemma, deepseek) under the post-soft-CRS grader.

#### Verdict
**calibrated**

Score distribution under the current grader spans the full range and tracks
agent capability:

- **Strong agents (opus × 2, deepseek-v4-pro × 1): 1.0, 1.0, 1.0.** Wrote
  WGS84 GeoJSON, computed the symdiff correctly, clustered, classified, and
  emitted representative-point anchors. All 8 subchecks pass.
- **Weak agent on detailed prompt (gemma × 2): 0.625, 0.75.** Wrote outputs in
  EPSG:6539 instead of WGS84 (correctly docked by both CRS subchecks but no
  longer hard-failing Gate 1); one of the two also leaked single Polygon rows
  alongside MultiPolygons (`all_multipolygon_disagreement` fails). This is
  exactly the score band the 2026-05-28 soft-CRS refactor was designed to
  produce: agents that get the geometry right but miss the output CRS now land
  in the 0.6-0.85 band instead of collapsing to 0.0.
- **Weak agent on basic prompt (gemma × 2): 0.0, 0.0.** Same kind of failure
  as before — the basic-prompt gemma runs either fail to install dependencies
  or skip the cluster-collect step entirely; structural row-count gate or
  upstream tooling failures, not grader miscalibration.

2c-CRS consistency holds end-to-end: reference outputs are EPSG:4326,
`expected_outputs[].crs == "EPSG:4326"`, README states "WGS84 (EPSG:4326)",
the grader's area subcheck reprojects **both** sides to EPSG:6539 only for the
m² comparison (`grade.py:274-275`, the permitted two-sided transform), and the
soft-CRS handler only reprojects the submission one-sidedly when implementing
the declared canonical/meaningful-set accept-list policy (the `crs_is_canonical`
+ `crs_in_meaningful_set` subchecks). This is exactly the pattern Step 2c-CRS
endorses.

#### Specific findings
- **Broken-set scores shifted with the soft-CRS refactor.** Re-grading the
  three broken fixtures against the current grader: `wrong_format` 0.0
  (intended); `partial` **0.5** (was metadata.measured 0.3333; intended range
  [0.25, 0.45]); `centroids` **0.875** (was 0.8333; intended range
  [0.75, 0.90]). The shift is mechanical: commit 05aabd6 added two new
  always-passing CRS subchecks for these WGS84 brokens, so the denominator
  went from 6 to 8 and pass-counts went from 2/6 → 4/8 and 5/6 → 7/8. The
  three broken scores remain in distinct, monotone-with-severity ranges
  (0.0 << 0.5 < 0.875). I refreshed `metadata.yaml > broken_solutions >
  measured_score` and `expected_score_range` and updated the description math
  to reflect the post-soft-CRS denominator (per Step 4 "Update measured_score"
  rule). No grader change.
- **HR-002 from prior block (now HR-001 in this block, inventory-mismatch,
  carried forward unchanged).** `authoring/inventory.md` line 600 data-source
  field, line 610 Overture-themes column, and line 1096 coverage-matrix row
  still list Overture theme `base.infrastructure`. Bundled inputs are sliced
  from `base.land_use` / `subtype='park'` (author-flagged in `metadata.yaml`
  notes and the author block). `coverage.yaml` here uses the truer
  `base.land_use` slug. Correcting the inventory row would leave the
  `base.infrastructure` coverage row (line 1096) with zero tasks — a
  coverage-completeness question to resolve alongside the theme fix.
  <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" -->
  Update `inventory.md` (line 600 data-source field, line 610 Overture-themes
  column, and the line-1096 coverage-matrix row) from `base.infrastructure`
  to `base.land_use`, and re-check `base.infrastructure` coverage
  completeness.
- **HR-003 from prior block (design-rationale, dropped this block).** The
  question — why was this geometric-ops task bundled into the 2026-05-17
  data-cleaning nudge-removal batch (commit 64740d0) — has been carried
  forward unchanged across three prior evaluator blocks without action. The
  wording changes themselves are defensible as nudge removal (cluster → group;
  dropped explicit EPSG:6539 output hint), the task is now `calibrated`, and
  the bundling rationale is process trivia. Dropping this flag rather than
  carrying it forward indefinitely. If the human ever needs the answer, the
  prior blocks preserve the question.
- **Instruction house-style sweep (Step 4 unilateral).** The prior instruction
  contained two em-dashes ("export — both feed", "or `both` — those exact
  strings") that the house-style rules explicitly forbid. Replaced with a
  period plus a new sentence, and parentheses, respectively. Also softened
  "Produce two GeoJSON FeatureCollections" to "Please write two GeoJSON
  FeatureCollections" to match the colleague-Slack voice. Anchored
  `nyc_parks` to its actual filename (`nyc_parks.gpkg`) per house-style rule 5.
  Replaced the final em-dash ("in matching order") with "with exactly one
  anchor per disagreement group in matching order". No content removed; the
  CRS-omission gotcha (the prompt deliberately does not name EPSG:4326 — that
  is part of what the task tests) is preserved. Reference re-grade after edit:
  **1.0**.
- **`analyst_notes` authored (Step 4 unilateral).** Was missing. Authored a
  description, a five-step approach list, and six pitfalls covering the
  centroid-vs-representative-point trap, the cluster-collect step, dropping
  one side of the symdiff, source-label mislabelling, writing in the wrong
  CRS, and forgetting MultiPolygon coercion. Human-facing only, no agent
  exposure, no version bump triggered.
- **`task.json.version` bumped 2 → 3.** First meaningful instruction edit in
  this evaluator pass triggers the Step-4 versioning rule. Single bump covers
  all instruction-side edits in this run.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: removed two em-dashes from the instruction per house-style rule
  3 (replaced with a period + new sentence and with parentheses); anchored
  `nyc_parks` → `nyc_parks.gpkg` per house-style rule 5; softened "Produce"
  → "Please write" per house-style rule 1; removed the third em-dash before
  "in matching order". Re-grade on reference: **1.0**. Reason: mechanical
  house-style fix; content preserved (including the deliberate CRS omission).
- `task.json`: authored `analyst_notes` (was missing) covering the
  CRS-omission gotcha, the cluster-collect step, source labelling, and the
  centroid-vs-representative-point trap. Human-facing only.
- `task.json`: bumped `version` 2 → 3 per Step-4 versioning rule.
- `metadata.yaml`: refreshed `broken_solutions.partial.measured_score`
  (0.3333 → 0.5), `broken_solutions.centroids.measured_score`
  (0.8333 → 0.875), the matching `expected_score_range` entries
  ([0.25, 0.45] → [0.40, 0.60] and [0.75, 0.90] → [0.80, 0.92]), and the
  description math (2/6 → 4/8 and 5/6 → 7/8). Reflects the post-soft-CRS
  8-subcheck denominator. No grader change.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — update `inventory.md` Overture theme from
  `base.infrastructure` to `base.land_use` for this task (and re-check
  `base.infrastructure` coverage completeness on line 1096).

#### Tests run
- grader on reference (`reference/solution/outputs`): **1.0** (8/8 subchecks).
- grader on broken sets: wrong_format 0.0 (intended); partial 0.5
  (4/8; was 2/6 = 0.333); centroids 0.875 (7/8; was 5/6 = 0.833). Distinct
  monotone ranges preserved.
- grader on seven current on-disk agent submissions: opus × 2 = 1.0, 1.0;
  deepseek-v4-pro × 1 = 1.0; gemma-detailed × 2 = 0.625, 0.75
  (correctly docked on CRS + multipoly); gemma-basic × 2 = 0.0, 0.0
  (model-side / cluster-collect failures). Agent grading verified sound and
  discriminating across three agent families.
- pytest (benchmark/eval): **41 passed**.

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Disagreement-non-zero and disagreement-within-±50% checks deleted;
  the existing `count_within_tolerance` subcheck (±10%) already covers
  the same property at a tighter bound.
- Anchor-count-equals-disagreement-count check migrated to new
  subcheck `anchor_count_matches_disagreements`.
- Unused `GATE2_ROW_TOL` constant removed.
- Subcheck count: 8 → 9.

### Verification
- Reference solution re-graded: 1.0 (9/9 subchecks).

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior evaluator blocks: a bundled L2 geometric-ops chain over a
two-layer NYC parks GeoPackage (1380 official polygons, 1372 OSM-derived, both
EPSG:6539). The agent symmetric-differences the two layers, clusters into
connected components, classifies each cluster's `source`
(`parks_official` | `parks_osm` | `both`), collects into one MultiPolygon per
cluster, and emits a point-on-surface label anchor. Full change-log table not
repeated; only new design-affecting commits since the 2026-06-06 evaluator
block are listed below.

#### Change log (delta since prior evaluator block)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change (+docs) | Removed the `structural_correctness` gate: disagreement-non-zero and ±50 % row checks deleted (covered by the tighter `count_within_tolerance` subcheck); anchor-count check migrated to new subcheck `anchor_count_matches_disagreements`; `GATE2_ROW_TOL` removed; docstring rewritten. Subchecks 8 -> 9. Also appended the "Manual cleanup 2026-06-06" block to this file. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" - benchmark-wide refactor so shape-recoverable output costs points instead of collapsing to 0. |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to the five data-content subchecks (`count_within_tolerance`, `source_label_distribution`, `total_area_within_tolerance`, `unioned_geometry_iou`, `anchors_inside_disagreements`); the four schema/structural subchecks stay at 1.0. Score is now weighted: total weight 19. | Commit msg: "Weight data-content subchecks 3x across all categories" - benchmark-wide weighting so data-content correctness dominates schema/structural checks. |

Neither commit message leaves a rationale gap; both are repo-wide refactors
whose intent is fully stated.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:32:38Z** (commit c749e57, class: grader-change). The Gate-2 removal (363aed2, 2026-06-06T20:11:02Z) is older. Current `task.json` version is 3; all runs considered below were scored against suite SHAs whose task.json is also version 3, so the version check does not invalidate any of them - only the timestamp cutoff does.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T12:24:14Z | 0.6842 | done | current |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T11:00:13Z | 0.6842 | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T15:49:59Z | 0.8421 | done | stale by timestamp (pre-c749e57); re-graded current: **0.8421** |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:28:05Z | 0.625 | done | stale; re-graded current: **0.8421** |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:36:47Z | 0.75 | done | stale; re-graded current: **0.8947** |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:18:14Z | 0.625 | done | stale; re-graded current: **0.8421** |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T17:10:58Z | 1.0 | done | stale; re-graded current: **1.0** |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:29:29Z | 1.0 | done | stale; re-graded current: **1.0** |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T21:52:26Z | 1.0 | done | stale; re-graded current: **1.0** |
| 37 earlier runs (<= 2026-05-29) | various | - | mixed | done | stale (pre-cutoff; see prior blocks) |

Only the two deepseek-v4-flash runs are `current` by the strict
timestamp-plus-version rule, and they are a single agent family. To avoid an
`insufficient-evidence` verdict on a technicality, I re-graded the on-disk
output files of the seven most recent submissions from the other three agent
families against the current weighted grader (re-graded scores in the table).
That gives current-grader evidence from four agent families.

#### Verdict
**calibrated**

The current weighted grader discriminates cleanly and monotonically across
agent capability and failure mode:

- **opus x 2 and deepseek-v4-pro x 1: 1.0.** Full chain correct, WGS84 output.
- **gemma-4-detailed x 4: 0.8421-0.8947.** Geometry right, output declared in
  EPSG:6539 (docked on the two 1.0-weight CRS subchecks); two of the four also
  leaked plain Polygon rows (`all_multipolygon_disagreement` fails).
- **deepseek-v4-flash x 2 (the `current` runs): 0.6842.** A genuinely new
  observed failure shape: 46 clusters, perfect source distribution
  (20/12/14), 46 anchors inside - but the coordinates are raw EPSG:6539
  values (x ~976k, y ~208k) written into GeoJSON with **no `crs` member**, so
  RFC 7946 implies WGS84. The grader treats the declared CRS as canonical
  (both CRS subchecks pass) but `total_area_within_tolerance` (0 m^2 after the
  degrees->6539 reproject of out-of-range coordinates) and
  `unioned_geometry_iou` (0.0) correctly fail, weighted 13/19. The agent did
  all geometric work right and skipped the final reprojection; 0.68 is a fair
  score for that, and the 3x weighting is what pulls it below the
  declared-6539 gemma case (which is self-consistent and recoverable, hence
  scores higher at 16/19). The ordering is defensible: an undeclared
  projected-coordinate GeoJSON is more broken than a declared-CRS one.

2c-CRS consistency holds end-to-end: reference outputs are EPSG:4326
(CRS84), `expected_outputs[].crs == "EPSG:4326"`, README states WGS84, and
the grader's only metric-CRS use reprojects **both** sides to EPSG:6539 for
the area subcheck (`grade.py:229-230`) - the permitted two-sided transform.
The soft-CRS one-sided reproject implements the declared accept-list policy
(canonical-only meaningful set), which Step 2c-CRS endorses.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| two output files, exact names | instruction, para 2 | stated |
| `source` column in both files | instruction (para 1 + para 2) | stated |
| `source` values exactly parks_official / parks_osm / both | instruction, para 1 | stated |
| disagreement geometry MultiPolygon | instruction ("One MultiPolygon per merged group") | stated |
| anchors are Point, strictly inside the group geometry | instruction, para 1 | stated |
| anchor count == disagreement count, matching order | instruction, para 2 | stated |
| output CRS WGS84 | not named; GeoJSON output pins WGS84 by RFC 7946 | inferable |
| cluster adjacent patches into merged groups | instruction, para 1 | stated |
| count +-10 %, area +-5 %, IoU >= 0.85, Jaccard >= 0.9, per-source +-20 % | grader-internal tolerances | inferable (standard drift margins) |

Factual claims verified: `nyc_parks.gpkg` exists in `inputs/`; layer names
`parks_official` and `parks_osm` match the instruction's claim that the
`source` values mirror "the input GPKG layer names" (verified via
pyogrio.list_layers); both layers MultiPolygon. No missing or inaccurate
claims; no flag.

#### Reference faithfulness
`reference/solution/generate.py` implements the instruction as written:
unioned symdiff, 1 m buffer-merge connected-component clustering,
per-side classification, MultiPolygon collect, `representative_point()`
anchors, WGS84 reproject before the GeoJSON write. It additionally emits two
bookkeeping columns (`cluster_id`, `area_m2`) that the prompt does not
request; the grader ignores extra columns, `expected_outputs[]` does not pin
a column set beyond `source`, and the README documents `cluster_id` as a
reference-internal stable id ("submission may reorder"), so submissions are
neither required to produce nor penalised for lacking them. Not a
behavioural deviation; faithful. (Five prior evaluator blocks reached the
same conclusion.)

#### Specific findings
- **Broken-set scores shifted again with the 3x weighting (mechanical).**
  Re-graded this run: `wrong_format` 0.0 (intended); `partial` **0.3684**
  (7/19; metadata recorded 0.5 = 4/8 and range [0.40, 0.60] - the recorded
  measured score had fallen outside its own expected range); `centroids`
  **0.8421** (16/19; metadata recorded 0.875 = 7/8, range [0.80, 0.92] still
  contains the new value). Distinct, monotone-with-severity ranges preserved
  (0.0 << 0.368 < 0.842). Refreshed `metadata.yaml > broken_solutions`
  measured_score, expected_score_range (partial -> [0.30, 0.45]), and the
  description math; also removed the stale "Gate 2 (+-50 %) passes" wording
  from the partial description. Per the Step-4 measured_score rule; no grader
  change, no version bump.
- **README failure-mode section was stale (docs-change, fixed unilaterally).**
  Failure modes #2, #3, and #8 still described Gate-1 CRS hard-fail and
  Gate 2, both removed by commits 05aabd6/363aed2; #4 and #5 carried
  pre-weighting scores (0.333 / 0.833); the input path still read
  `data/nyc_parks.gpkg` (pre-reorg). Rewrote those entries for the current
  single-gate weighted grader (including the newly observed
  undeclared-projected-coordinates variant of #2) and fixed the path to
  `inputs/`.
- **Two `analyst_notes` pitfalls were stale (refreshed unilaterally).**
  Pitfall 2 referenced "the structural row-count gate" (removed); pitfall 5
  described only the declared-6539 outcome. Updated both; human-facing only,
  no version bump.
- **CRS-subcheck observation (no flag).** For the deepseek-v4-flash failure
  shape, `crs_is_canonical` / `crs_in_meaningful_set` pass on the *declared*
  (implicit WGS84) CRS even though the coordinates are actually projected.
  The 3x-weighted area and IoU subchecks fully compensate (score 0.6842, the
  lowest current band), so the grader's resolution is intact; a
  coordinate-plausibility bounds check would be redundant. Noted for the
  record, not flagged.
- **HR-001 (carried forward, unchanged - inventory-mismatch).**
  `authoring/inventory.md` line 600 (data-source field), line 610
  (Overture-themes column), and line 1096 (coverage-matrix row) still list
  Overture theme `base.infrastructure`; the bundled inputs are sliced from
  `base.land_use` / `subtype='park'` (author-flagged since initial
  authoring). `coverage.yaml` uses the truer `base.land_use` slug.
  Correcting the inventory row leaves the `base.infrastructure`
  coverage-matrix row with zero tasks - a coverage-completeness question to
  resolve alongside the fix. <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Update `inventory.md` (line 600 data-source field, line 610 Overture-themes column, line 1096 coverage-matrix row) from `base.infrastructure` to `base.land_use`, and re-check `base.infrastructure` coverage completeness.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions.partial` (measured_score
  0.5 -> 0.3684, expected_score_range [0.40, 0.60] -> [0.30, 0.45]) and
  `broken_solutions.centroids` (measured_score 0.875 -> 0.8421), plus
  description math for the weighted 19-point denominator and removal of the
  stale Gate-2 wording. Re-grade on reference: 1.0. Reason: Step-4
  measured_score refresh after the 3x-weighting commit.
- `README.md`: failure modes #1-#3, #8, and the weak-agent paragraph
  rewritten for the single-gate weighted grader; broken scores updated;
  `data/` path corrected to `inputs/`. Re-grade on reference: 1.0. Reason:
  docs-change; README must describe the current grader.
- `task.json` (`analyst_notes` only): refreshed pitfalls 2 and 5 (removed
  Gate-2 reference; documented the undeclared-CRS variant). Re-grade on
  reference: 1.0. Reason: analyst_notes refresh, human-facing only.
- No version bump: no change to `instruction`, `inputs[]`,
  `expected_outputs[]`, `grade.py`, `metadata.yaml > tolerances`, or
  `inputs/`. Version stays 3.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 - inventory-mismatch - update `inventory.md` Overture theme from
  `base.infrastructure` to `base.land_use` for this task (and re-check the
  `base.infrastructure` coverage-matrix row, which would drop to zero tasks).

#### Tests run
- grader on reference: 1.0 (9/9 subchecks, weighted 19/19)
- grader on broken sets: wrong_format 0.0; partial 0.3684; centroids 0.8421
- grader on current + re-graded submissions: opus x 2 = 1.0; deepseek-v4-pro = 1.0; gemma-detailed x 4 = 0.8421-0.8947; deepseek-v4-flash x 2 = 0.6842
- pytest: pass (41 passed)

---

## Grader weight recalibration 2026-06-14  (evaluator-commit <pending>)

**Change:** RECALIBRATED. Replaced the blunt repo-wide
weight=3.0-on-all-data-content scheme (commit c749e57) with
severity-reasoned weights. The central skill this task tests is a
correct symmetric-difference overlay in a projected CRS; the two
subchecks that measure the symdiff geometric *footprint* (area, IoU)
are now weighted highest, the two that measure overlay
result-*structure* (count, source-distribution) next, the secondary
label-anchor sub-skill below that, and structural/CRS-label checks
lowest. Grading-only; no task.json version bump.

### Weight changes
| Subcheck | old | new | rationale |
|---|---|---|---|
| total_area_within_tolerance | 3.0 | **4.0** | central: symdiff footprint; cleanest catcher of dropped-side / unit / missing-reproject errors |
| unioned_geometry_iou | 3.0 | **4.0** | central: symdiff footprint overlap (the geometric heart) |
| count_within_tolerance | 3.0 | 3.0 | core overlay result-structure (cluster cardinality); kept |
| source_label_distribution | 3.0 | 3.0 | core overlay result-structure (per-side attribution); kept |
| anchors_inside_disagreements | 3.0 | **2.0** | secondary label-anchor sub-skill, NOT the core overlay; was over-weighted equal to the footprint checks |
| all_multipolygon_disagreement | 1.0 | 1.0 | structural; kept |
| anchor_count_matches_disagreements | 1.0 | 1.0 | structural; kept |
| crs_is_canonical | 1.0 | 1.0 | cosmetic when recoverable; kept |
| crs_in_meaningful_set | 1.0 | 1.0 | cosmetic when recoverable; kept |

Total weight 19 -> 20.

### Broken-score before -> after
| Broken | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | unrecoverable (Gate 1); unchanged |
| partial (dropped one side) | 0.3684 | **0.30** | most-severe non-gate error (the whole symdiff overlay is wrong); now penalized harder because area+IoU carry w=4. Lowest band. |
| centroids (anchor sub-skill) | 0.8421 | **0.90** | overlay perfect, only the secondary label-anchor skill slipped; correctly rises toward the top. |

Ordering after recalibration is monotone with severity:
`0.0 (gate) << 0.30 (overlay wrong) < 0.60 (undeclared projected coords,
geometry geographically wrong) < 0.85 (declared-6539 + Polygon leak)
<= 0.90 (declared-6539 CRS-label only / centroids anchor slip) < 1.0`.
No disjoint-failure inversion: the partial broken (4 central failures)
stays strictly below the undeclared-coords case (2 central failures),
which stays below the cosmetic CRS/structural cases. Reference holds at
1.0 (>= 0.95 invariant).

### Prior-run re-grade (current task version 3)
Re-graded the 9 most-recent on-disk submissions (the runs the prior
2026-06-12 block lists as `current` plus the re-graded set from four
agent families). old -> new:
| Run | adapter | old | new |
|---|---|---|---|
| run-20260529-0902Z | deepseek-v4-pro-basic | 1.0 | 1.0 |
| run-20260528-2332Z | opus-basic | 1.0 | 1.0 |
| run-20260528-1927Z | opus-basic | 1.0 | 1.0 |
| run-20260606-1129Z | gemma4-26b-detailed | 0.8947 | 0.90 |
| run-20260607-112430Z | gemma4-26b-detailed | 0.8421 | 0.85 |
| run-20260606-1733Z | gemma4-26b-detailed | 0.8421 | 0.85 |
| run-20260606-0953Z | gemma4-26b-detailed | 0.8421 | 0.85 |
| run-20260608-074701Z | deepseek-v4-flash-detailed | 0.6842 | 0.60 |
| run-20260609-084636Z | deepseek-v4-flash-basic | 0.6842 | 0.60 |

Notable shifts: the undeclared-projected-coordinate failure
(deepseek-flash, geometry right but output geographically wrong) drops
0.6842 -> 0.60, correctly pulling a meaningful output error further
down; the declared-6539 cosmetic failures move only slightly
(0.84/0.89 -> 0.85/0.90). The capability ordering across all agent
families is preserved and sharpened.

### Reasoning
The repo-wide c749e57 weighting put `anchors_inside_disagreements` at
the same weight (3.0) as the four overlay subchecks, equating a
secondary label-anchor sub-skill with the central symdiff skill. It
also flattened area/IoU (which directly measure the symdiff footprint
and catch dropped-side/unit errors, per the metadata rationale) to the
same weight as the buffer-merge-sensitive cluster-count check. The new
scheme lifts the two footprint checks to 4.0, keeps the two
result-structure checks at 3.0, drops the anchor check to 2.0, and
leaves structural/CRS checks at 1.0 - so a fundamentally-wrong overlay
(partial) drops to the lowest non-gate band while a cosmetic CRS-label
or a single secondary-skill slip stays near the top. No check logic,
thresholds, or gates were touched.

### HR carried forward
- HR-001 (inventory-mismatch) is NOT a weighting HR; left in place
  unchanged.

### Tests run
- grader on reference: **1.0** (9/9 subchecks, weighted 20/20)
- grader on broken sets: wrong_format 0.0; partial 0.30; centroids 0.90 (distinct, monotone)
- grader on 9 re-graded submissions: see table above
- pytest: not run (orchestrator runs the suite)
