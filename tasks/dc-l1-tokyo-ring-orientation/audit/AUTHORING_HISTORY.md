# Implementation notes — dc-l1-tokyo-ring-orientation

## Status
completed

## Summary
L1 data-cleaning task: 100 Tokyo building footprints sliced from
Overture release 2026-04-15.0 with rings deliberately reversed to OGC
orientation (exterior CW, interior CCW) → RFC 7946 §3.1.6 GeoJSON
(exterior CCW, interior CW), every attribute and the geometric shape
preserved. Reference, grader, and three broken solutions built and
verified inside the project Docker container.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - wrong_orientation: 0.7142857142857143 (expected range [0.65, 0.78])
  - partial_orientation: 0.8571428571428571 (expected range [0.8, 0.9])
- Second-run output match: bit-identical (verified via `cp` + `diff -q`)
- Library tests after task: pass

## Failure-mode coverage
- Forget to fix orientation — pass the file through unchanged: broken_wrong_orientation
- Fix exteriors but forget interiors: broken_partial_orientation
- Drop one of the required attribute columns: broken_wrong_format
- Drop interior rings while fixing orientation: principled —
  `polygons_with_holes_preserved` subcheck (count of polygons with
  interior rings must match reference)
- Re-orient correctly but simplify / buffer geometry: principled —
  `per_feature_geometry_preserved` subcheck (per-id IoU ≥ 0.99)
- Re-orient and accidentally change CRS: principled — Gate 1's
  `crs.to_epsg() == 4326` check
- Drop or duplicate features: principled — Gate 2 ±5 % count tolerance
  + `feature_id_set_preserved` Jaccard subcheck
- Re-encode via Shapefile intermediate (silent column truncation,
  ring-orientation flip on round-trip): not covered by a broken
  solution; the column gate + orientation subchecks both bite

## Open issues
- [severity: low] — Synthetic interior rings injected into 5 of 100
  buildings at authoring time. Real Overture buildings rarely have
  natural holes (a sample of the bbox returned zero), but a meaningful
  test of RFC 7946 §3.1.6 must exercise both orientation rules. The
  injection is documented in `data/_prepare_input.py`'s docstring and
  `metadata.yaml > notes`. The synthetic holes are tiny axis-aligned
  squares placed near each footprint's centroid; coordinates are a
  closed-form function of feature index (deterministic).

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — task uses only existing primitives: `attribute_match`,
`count_within_tolerance`, `feature_set_equality_by_id`,
`iou_with_tolerance`. Ring-orientation checking is implemented inline
because it is intrinsic to one task family and adding a
`rings_oriented_per_rfc7946` primitive feels premature given only one
task currently needs it.)

## Runtime
~25 minutes on the original 2026-05-06-a authoring pass (initial
Overture HTTPS path was rejected by DuckDB — switched to S3 with
anonymous secret, matching the `crs-l1-london-laea-areas` peer task;
otherwise everything ran locally in the project Docker image).
Re-verified 2026-05-07 against prompt_version 2026-05-07-a: reference
output bit-identical, grader on reference scores 1.0, brokens score
0.0 / 0.714 / 0.857 (all in declared ranges), pytest 32/32 pass —
~3 minutes wall-clock for the re-verification.

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
A pure data-cleaning L1 task: 100 Tokyo building footprints (sliced from Overture release 2026-04-15.0, Shibuya/Yoyogi bbox) were bundled as GeoJSON with rings deliberately re-serialised in OGC orientation (exterior CW, interior CCW), with five fixed feature_ids carrying synthetic interior rings so the grader can score the interior-orientation rule on a non-trivial sample. The agent, voiced as Kenji Yamamoto (volunteer at OSM Japan), must rewrite the file in RFC 7946 §3.1.6 orientation (exterior CCW, interior CW), preserving every attribute and the exact geometry; output is `tokyo_buildings_rfc7946.geojson` in EPSG:4326. The original `task.json` instruction explicitly named RFC 7946 §3.1.6, the OGC/RFC orientations, and the EPSG code; subsequent commits progressively stripped those gifts to make the task probe symptom→cause reasoning instead of standard-recall.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 1dc50196 | initial-authoring | Initial scaffold: task.json, README, grade.py, metadata.yaml, reference/, tests/, data/_prepare_input.py, IMPLEMENTATION_NOTES.md (committed alongside 4 other L1 tasks in the first overnight run) | Commit msg: initial benchmark scaffold + first overnight run |
| 2026-05-07 | d29dd7d4 | prompt-change | Tightened instruction voice — removed self-introduction ("I'm Kenji…"), persona-voice carried by register and word choice instead | Commit msg: persona writes the task; persona doesn't introduce themselves |
| 2026-05-07 | a50a77e8 | docs-change | IMPLEMENTATION_NOTES.md Runtime section appended with re-verification note; metadata.yaml date/prompt_version bumped to 2026-05-07-a | Commit msg: task: dc-l1-tokyo-ring-orientation [completed] |
| 2026-05-08 | fbd20f2a | mixed (path-only, docs+grader+ref+data+tests) | Repo restructure: tasks/ → benchmark/tasks/ (later eval/tasks/) | Commit msg: restructure: split repo into thesis/ benchmark/ references/ |
| 2026-05-08 | 001e459b | mixed (path-only) | Move under benchmark/eval/tasks/ | Commit msg: benchmark: split into authoring/ and eval/ subtrees |
| 2026-05-12 | ca819c84 | docs-change | Added visualize.py | Commit msg: eval: add visualize.py for every geometry-producing task |
| 2026-05-13 | 1710715e | prompt-change | Appended explicit "Output schema:" bullet block to instruction (CRS, geometry type, required columns, join key) | Commit msg: declare exact output schema in prompts to match graders |
| 2026-05-13 | 284b8436 | prompt-change | Added `tags` dict to task.json (region, data_source, formats, crs, geometry_type, operations, themes, quality_issues, scale) | Commit msg: add structured tags to all 36 task.json files |
| 2026-05-13 | 1b8dda17/89150101/3c653731/cfbdc7c6 | docs-change | image-prompt.md + image.webp regenerations | Commit msgs: task card image generation iterations |
| 2026-05-13 | 9e79176a | prompt-change | Folded structured "Output schema:" bullets into a fluent prose paragraph | Commit msg: merge output schema blocks into prose for 6 task instructions |
| 2026-05-14 | f5d1e919 | prompt-change | Stripped "(exterior CW, holes CCW)" parenthetical and inline column listing — agent must read the file to discover orientations and columns | Commit msg: strip deducible information from DC task instructions |
| 2026-05-15 | a78a5139 | prompt-change | Replaced "Rewrite as RFC 7946 §3.1.6 — exterior CCW, holes CW — attributes untouched" with "Rewrite ring orientations to be RFC 7946 §3.1.6 compliant, attributes untouched" — stops giving the explicit target orientation | Commit msg: strip deducible information from DC task instructions (round 2) |
| 2026-05-17 | 64740d0a | prompt-change | Replaced RFC-7946 naming + ring-orientation operation hint with a pure symptoms description: web viewers shade interiors as exterior, tile-server rejects features. Agent must diagnose the defect from symptoms. | Commit msg: remove answer-giving nudges from data-cleaning task prompts |
| 2026-05-17 | ca8994df | prompt-change | Stripped `EPSG:4326` from the instruction — agent infers WGS84 from format conventions (GeoJSON RFC 7946) or from the input file metadata | Commit msg: remove remaining EPSG codes from task instruction fields |
| 2026-05-18 | f0c244a6 | grader-change | Replaced inline `sub.crs.to_epsg() == 4326` with shared `is_wgs84(sub.crs)` helper. Semantic: also accepts `None` CRS (per RFC 7946). | Commit msg: consolidate WGS 84 CRS checks into shared geo_grading package |
| 2026-05-26 | 29a9ae32 | mixed (path-only refactor of grader+reference+data+tests+docs) | Folder reorg: data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image*→assets/. Updated path constants in grade.py, _make_brokens.py, _prepare.py, task.json input URL. No semantic change. | Commit msg: reorganize task folder layout |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae32, class: mixed — grader path constant + task.json input URL changed). The previous semantically-meaningful cutoff is the 2026-05-18 grader consolidation (f0c244a6) at 2026-05-18T06:35:57Z.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:16:04Z | 1.0 | done | current |
| run-20260517-1424Z and earlier (24 runs) | various | 2026-05-12 – 2026-05-17 | — | — | stale (pre-cutoff) |

Stale runs are not used as evidence. The 24 stale runs predate at least one prompt-change (the 2026-05-17 nudges-removal), and several predate the 2026-05-15 round-2 strip; using them would conflate calibration of older instructions with the current one.

#### Verdict
**insufficient-evidence**

Only one current run exists (openrouter-gemma4-26b-basic, score 1.0), from a single adapter family. The task is structurally sound: the grader on the reference solution scores 1.0/1.0 with all 7 subchecks passing, broken-solution scores (0.0 / 0.714 / 0.857) sit inside their declared ranges (re-verified at authoring time, no design changes since that would shift them — the 2026-05-18 `is_wgs84` swap is semantically-broader-not-narrower and would not change any broken-solution score that already passed Gate 1). The current instruction (post-64740d0a / ca8994df) avoids RFC 7946 naming and EPSG numerals entirely; it describes only symptoms (interiors shaded as exterior, tile-server geometry warnings) and requires the agent to diagnose ring orientation as the defect — a calibrated test of agent reasoning rather than standard-recall. Without runs from at least one capability-distinct adapter, however, I cannot rule out task-too-easy.

#### Specific findings
- The output filename `tokyo_buildings_rfc7946.geojson` still contains the standard's identifier ("rfc7946"). On strict reading this is a gift — an agent that grepped for "rfc7946" could resolve the defect without reading the file. The filename has been stable since initial authoring and matches the persona's natural file-naming style (he asks the agent to produce a file he can name in the README story); changing it would also alter `expected_outputs[]` which the prompt forbids editing unilaterally. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether the explicit standard-name in the output filename undermines the symptoms-only instruction enough to warrant renaming the output (and the matching reference/broken-solution/grader constants).
- Only one current run is available, all from the same OpenRouter adapter family. Re-running across at least one Claude Code adapter and one stronger OpenRouter adapter would clarify whether the symptoms-only instruction is calibrated or too easy. <!-- HUMAN-REVIEW id="HR-002" category="task-too-easy-suspected" severity="low" --> Re-run the task with two more adapters before reading task-too-easy off this 1.0 score.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — Output filename still names RFC 7946; renaming would require touching `expected_outputs[]` which the evaluator may not edit unilaterally.
- HR-002 — task-too-easy-suspected — One current run from one adapter family is not enough evidence to call too-easy; flag for the orchestrator to schedule more runs.

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-26 (second pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new design-affecting commits since the prior evaluator pass. The only commit touching the task directory since then is `829e7443` (the prior evaluator's own artefact commit, 2026-05-26T12:57:06Z), which is `docs-change` (audit/AUTHORING_HISTORY.md, audit/status.json, coverage.yaml only) and does not shift the design-affecting cutoff. The full change log reconstructed in the first-pass block above remains accurate and is not restated here; it was verified against `git log --follow` for the directory and the `1dc50196` initial-authoring commit.

### 2. Current-state review

This pass exists because the orchestrator scheduled the cross-family runs that the prior pass's HR-002 asked for. With those in hand the diagnostic can move off `insufficient-evidence`.

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae32, class: mixed — grader path constant + task.json input URL changed; path-only, no semantic change). Unchanged from the prior pass. The prior pass's "current" gemma run (run-20260526-0748Z, started 08:16:04Z) actually predates this cutoff by ~95 minutes and is therefore re-classified **stale** here. Because 29a9ae32 was path-only, that run's 1.0 is corroborating but not load-bearing.

#### Runs considered
| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | claude-code | 2026-05-26T18:38:17Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T19:27:26Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T08:16:04Z | 1.0 | done | stale (pre-cutoff by ~95 min; path-only commit, so corroborating only) |
| run-20260517-1424Z and earlier (24 runs) | various | various | 2026-05-12 – 2026-05-17 | — | — | stale (predate ≥1 prompt-change) |

Two **current** runs from two distinct agent families (Claude Code / Opus and OpenRouter / Gemma 4 26B). Both scored 1.0/1.0 with all 7 subchecks passing (verified from each run's `score.json`).

#### Per-run output inspection
- Both runs produced exactly `tokyo_buildings_rfc7946.geojson` (the single declared output). No extra spatial outputs beyond helper `.py` scripts left in the session dir.
- Both: 100 Polygon features, columns `feature_id, overture_id, name_primary, building_class, height` (matches REQUIRED_COLUMNS), WGS84, geometry type `Polygon` only, 5 polygons-with-holes preserved, exterior 100/100 CCW, interior 5/5 CW. Light comparison against `reference/solution/outputs/tokyo_buildings_rfc7946.geojson` matches on every dimension the grader reports.

#### Transcript evidence (read because the all-1.0 result requires ruling out gift-exploitation, per Step 2d)
- **Opus (run-1753Z):** wrote an inspection script, empirically found exterior CW / interior CCW, diagnosed it as the inverse of RFC 7946, reversed every ring with a hand-rolled `LinearRing.is_ccw` check, and self-verified that vertex sets and shape (`symmetric_difference.area ≈ 0`) were unchanged. Did **not** grep the filename for "rfc7946" to shortcut the diagnosis — the reasoning ran symptom → data inspection → winding fix.
- **Gemma (run-1922Z):** reasoned from the symptom text ("holes appear filled and exteriors render as empty space ... sounds like the ring orientation / winding order"), applied `shapely.ops.orient(sign=1.0)`, then independently verified hole count (5/5) and attribute keys preserved. Used a defensive `make_valid` + keep-largest-MultiPolygon path that would have dropped holes had it triggered, but the input was already valid so it was a no-op — and `polygons_with_holes_preserved` would have caught it otherwise.
- Conclusion: both agents solved the task by the intended symptom→cause reasoning chain, not by reading the standard name off the output filename. The symptoms-only instruction is doing its job.

#### Verdict
**calibrated**

The task discriminates correctly and the all-1.0 result on two current runs is the expected L1 calibration outcome, not a defect:
- The instruction (`task.json` instruction field) names no EPSG code, no RFC standard, no "ring orientation", and no library function — it is a pure symptoms description. Step 2d's `too-easy` requires *both* (a) all current runs ≥ 0.95 across capability-distinct agents *and* (b) an instruction that over-specifies the answer. (a) holds, but (b) does **not**: there are no answer-giving gifts in the prompt body. Two agents of clearly different capability (Opus vs. a 26B open model) both had to *diagnose* the defect, and both did. An L1 single-op task that a competent agent solves cleanly is exactly the L1 ≫ L2 ≫ L3 gradient the benchmark targets.
- The grader cleanly separates the failure space: reference 1.0, brokens 0.0 / 0.714 / 0.857 (re-measured this pass, all inside declared ranges), and the seven subchecks each detect a distinct failure mode (orientation x2, id-set, extent IoU, hole-count, attributes, per-id IoU). No subcheck is dead code: the gemma run's defensive hole-dropping path shows the `polygons_with_holes_preserved` subcheck has a live target.
- No `too-strict` or `prompt-grader-inconsistent` signal: every correct-looking output scored 1.0, and the grader's WGS84/RFC-7946 expectations are pinned by GeoJSON convention (RFC 7946), which the instruction's GeoJSON output and the input file's `OGC:CRS84` member both supply — the agent is not asked to know a CRS it cannot infer.

The prior pass's HR-002 (need cross-family runs before reading too-easy off a single 1.0) is now **resolved by the evidence** and is not carried forward.

#### Specific findings
- The output filename `tokyo_buildings_rfc7946.geojson` still embeds the standard's identifier. On a strict reading this is a residual gift — an agent could in principle infer "fix ring orientation per RFC 7946" from the filename alone without reading the file. The two current transcripts show neither agent actually did this (both diagnosed from symptoms + data), so it is not currently defeating the test, but it remains a latent over-specification. Renaming would require editing `expected_outputs[]` (and the matching reference / broken-solution / grader path constants), which the evaluator may not change unilaterally. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether the standard-name in the output filename should be replaced with a neutral name (e.g. `tokyo_buildings_fixed.geojson`) to remove the latent gift; if so a human must update `task.json > expected_outputs`, `grade.py` `OUTPUT_NAME`/`REFERENCE_OUT`, `reference/solution/generate.py`, and all three `reference/failures/broken_*/outputs/` filenames in one coordinated change.

### 3. Changes applied this run

#### Unilateral edits
- (none) — the verdict is `calibrated`; no tolerance, gift, or subcheck change is warranted. `coverage.yaml` re-validated against the current vocabulary (all slugs valid) and only its `evaluator_run_at` timestamp refreshed.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — output filename still names RFC 7946; renaming touches `expected_outputs[]` and reference/broken/grader constants, outside the evaluator's unilateral scope.

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- broken solutions: wrong_format 0.0, wrong_orientation 0.714, partial_orientation 0.857 (all in declared ranges)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27 (third pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new design-affecting commits since the prior (second-pass) evaluator block. The only commit touching this task directory since then is `dc88173b` (the second pass's own artefact commit, 2026-05-26T20:18:39Z, `docs-change`: audit/AUTHORING_HISTORY.md, coverage.yaml, audit/status.json only). All commits between `dc88173b` and the current `HEAD` (`de913d9`) are other tasks' evaluator artefact commits and touch nothing under `benchmark/tasks/dc-l1-tokyo-ring-orientation/` (verified with `git log dc88173b..HEAD -- benchmark/tasks/dc-l1-tokyo-ring-orientation/`, which returns empty). The full change log reconstructed in the first-pass block remains accurate and is not restated; it was re-verified against `git log --follow` for the directory plus the prior-path forms (`benchmark/eval/tasks/`, `tasks/`) and the `1dc50196` initial-authoring commit.

### 2. Current-state review

This pass is a sweep re-run; no new runs, commits, or design changes have appeared since the second pass reached `calibrated`. The diagnostic is re-confirmed from the same two current cross-family runs.

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae32, class: mixed — grader path constant + task.json input URL changed; path-only, no semantic change). Unchanged from the prior two passes.

#### Runs considered
| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | claude-code | 2026-05-26T18:38:17Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T19:27:26Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T08:16:04Z | 1.0 | done | stale (pre-cutoff by ~95 min; path-only commit, corroborating only) |
| run-20260517-1424Z and earlier (24 runs) | various | various | 2026-05-12 – 2026-05-17 | — | — | stale (predate ≥1 prompt-change) |

Two **current** runs from two distinct agent families (Claude Code / Opus reported as `claude-opus-4-7`, and OpenRouter / `google/gemma-4-26b-a4b-it`). Both scored 1.0/1.0 with all 7 subchecks passing (re-read from each run's `score.json` this pass). No new runs have been added since the second pass.

#### Per-run output inspection
- Both run output dirs contain exactly one declared output, `tokyo_buildings_rfc7946.geojson` (plus helper `solve.py` / `check_holes.py` / a copied `tokyo_buildings_legacy.geojson` — none of which match the `expected_outputs[]` contract, so they are ignored).
- Light comparison vs `reference/solution/outputs/tokyo_buildings_rfc7946.geojson`: REF / 1753Z / 1922Z all = 100 features, columns `{building_class, feature_id, geometry, height, name_primary, overture_id}`, CRS EPSG:4326, geometry types `{Polygon}`. Identical on every dimension the grader reports.

#### Output-CRS and format consistency (2c-CRS)
- Agent output CRS (4326) == reference output CRS (4326). `grade.py` performs no one-sided reprojection: the orientation subchecks read `is_ccw` directly, and `iou_with_tolerance` is applied symmetrically to both submission and reference (both already WGS84). Clean.
- Reference output CRS/format (EPSG:4326, GeoJSON) == `expected_outputs[]` (`crs: EPSG:4326`, `format: geojson`). Match.
- README's stated output (EPSG:4326, GeoJSON) == reference. Match.

#### Verdict
**calibrated**

Re-confirmed, no new evidence. The state is byte-for-byte the same as the second pass evaluated: reference grader 1.0 (7/7), brokens 0.0 / 0.714 / 0.857 (all re-measured this pass, all inside their declared ranges in `metadata.yaml`), pytest 35/35. The two current cross-family runs both score 1.0 — the expected L1 outcome — and the instruction (`task.json` instruction field) still names no EPSG code, no RFC standard, no "ring orientation", and no library function. Step 2d's `too-easy` requires both all-current-runs ≥ 0.95 *and* an over-specifying instruction; only the first holds, so the verdict is not `too-easy`. The transcript-level rebuttal of gift-exploitation was established in the second pass and is unchanged; no new `too-strict` or `prompt-grader-inconsistent` signal exists (every correct-looking output scored 1.0; the WGS84/RFC-7946 expectations are pinned by GeoJSON convention and the input's `OGC:CRS84` member, which the agent can read).

#### Specific findings
- Carried forward unchanged from the second pass: the output filename `tokyo_buildings_rfc7946.geojson` embeds the standard's identifier, a latent gift. The two current transcripts (documented in the second-pass block) show neither agent exploited it; renaming would require editing `expected_outputs[]` plus the matching reference / broken-solution / grader path constants, which the evaluator may not change unilaterally. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether the standard-name in the output filename should be replaced with a neutral name (e.g. `tokyo_buildings_fixed.geojson`); if so a human must update `task.json > expected_outputs`, `grade.py` `OUTPUT_NAME`/`REFERENCE_OUT`, `reference/solution/generate.py`, and all three `reference/failures/broken_*/outputs/` filenames in one coordinated change.

### 3. Changes applied this run

#### Unilateral edits
- (none) — verdict is `calibrated`; no tolerance, gift, or subcheck change warranted. `coverage.yaml` re-validated against the current vocabulary (every slug present) and only its `evaluator_run_at` timestamp refreshed.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — output filename still names RFC 7946; renaming touches `expected_outputs[]` and reference/broken/grader constants, outside the evaluator's unilateral scope.

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- broken solutions: wrong_format 0.0, wrong_orientation 0.714, partial_orientation 0.857 (all in declared ranges)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

Two new commits touch the task directory since the prior (third) pass:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342be | mixed (docs-change for this task; framework-wide) | Removed the `prompt_version` line from `metadata.yaml`; no task.json/grader/data change for this task. Framework-wide commit introducing the integer `task.json.version` field and the version-bump rule in `task-evaluator-prompt.md`. | Commit msg: "Add task content versioning; drop unused prompt_version." Sets up the v1→v2 contract; this task was implicit-v1 going into the rename below. |
| 2026-05-28 | b32486bc | mixed (prompt-change + grader-change + reference-change + data-change + tests-change + docs-change) | Resolved HR-001 from the second/third passes by (a) renaming the output filename `tokyo_buildings_rfc7946.geojson` → `tokyo_buildings_fixed.geojson` (touches `task.json > expected_outputs`, `grade.py` `OUTPUT_NAME`/`REFERENCE_OUT`, `reference/solution/generate.py`, `reference/failures/_make_brokens.py`, `visualize.py`, README, and 4 fixture .geojson files — 1 reference + 3 broken sets, regenerated so the inner FeatureCollection `name` matches the new filename) and (b) stripping the redundant attributes clause from the schema paragraph of the instruction ("Carry over all attributes verbatim from the input"), because the persona-paragraph "Attributes must be untouched." already states the constraint. Also bumped `task.json.version` 1 → 2 (the first contract-changing edit since 622342b introduced versioning) and added a `metadata.yaml > design_note` recording the rename. | Commit msg: "Resolve dc-l1-tokyo-ring-orientation HR-001 via output-filename rename + redundant-attributes strip" — explicitly applies HR-001 (carried across three prior evaluator passes) plus the new "tighten redundant statements" rule from `task-evaluator-prompt.md`. |

The full change log reconstructed in the first-pass block remains accurate for everything prior to these two commits and is not restated.

### 2. Current-state review

This pass is the first re-evaluation under the new prompt+filename contract (v2). The design-affecting cutoff jumps from 2026-05-26T09:51:37Z (the prior path-only refactor) to 2026-05-28T12:46:39Z (the rename + attributes strip), invalidating every prior `current` run for evidence purposes.

#### Cutoff
- design-affecting cutoff: **2026-05-28T12:46:39Z** (commit `b32486bc`, class: mixed — prompt-change + grader-change + reference-change + data-change + tests-change; output filename and FeatureCollection `name` both changed; instruction text shortened). The 622342be docs-change at 2026-05-28T07:07:03Z dropped `prompt_version` only and does not push the cutoff.

#### Runs considered
| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-28T03:24:58Z | 1.0 | done | stale (pre-cutoff by ~9h; produced old filename `tokyo_buildings_rfc7946.geojson`) |
| run-20260528-0113Z | claude-code-opus-basic | claude-code | 2026-05-28T01:34:07Z | 1.0 | done | stale (pre-cutoff by ~11h; produced old filename) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-27T23:37:08Z | 1.0 | done | stale (pre-cutoff by ~13h; produced old filename) |
| run-20260527-2016Z | claude-code-opus-basic | claude-code | 2026-05-27T20:35:23Z | 1.0 | done | stale (pre-cutoff by ~16h; produced old filename) |
| 27 earlier runs (run-20260526-1922Z and back through 2026-05-12) | various | various | 2026-05-12 – 2026-05-26 | mixed | various | stale (predate ≥1 prior prompt/path-change cutoff in addition to the b32486b rename) |

All 31 historical runs predate the b32486b cutoff. Spot-checked output dirs of the four most recent runs (2026-05-27/28): each contains `tokyo_buildings_rfc7946.geojson` — the pre-rename filename — which the current `grade.py` would reject at Gate 1 (`missing output file: tokyo_buildings_fixed.geojson`). The prior 1.0 scores are therefore not transportable across the rename.

**No `current` runs available.**

#### Output-CRS and format consistency (2c-CRS)
Re-checked under the v2 contract:
- `expected_outputs[0]` is `{format: geojson, crs: EPSG:4326, geometry_type: Polygon, name: tokyo_buildings_fixed.geojson}`.
- `reference/solution/outputs/tokyo_buildings_fixed.geojson` (regenerated by the b32486b commit) reads back as EPSG:4326, geometry types `{Polygon}`, 100 features with the 5 declared columns plus geometry — matches the contract.
- README (`## Output` section) states EPSG:4326 GeoJSON with the new filename and the same schema — matches the reference.
- `grade.py` applies `is_wgs84` and `iou_with_tolerance` symmetrically to submission and reference (both already 4326) — no one-sided reprojection, no CRS asymmetry.

Clean.

#### Verdict
**insufficient-evidence**

No `current` runs exist under the v2 contract. The task is structurally sound this pass (grader on reference 7/7 = 1.0; broken-solution scores re-measured 0.0 / 0.714 / 0.857, all inside their declared ranges in `metadata.yaml`; pytest 41/41), but Step 2d requires ≥ 2 current runs from capability-distinct adapters before a calibration verdict can be issued. Per the workflow rule, the absence of `current` runs alone — without other concrete reason to suspect a problem — is not itself a flag, but it does pin the diagnostic at `insufficient-evidence` until the orchestrator schedules a fresh sweep under v2. The previously-resolved HR-001 (filename gift) and the new attributes-clause de-duplication are both reflected in v2 and need no further action.

#### Specific findings
- No `current` runs (all prior runs are pre-rename and produced `tokyo_buildings_rfc7946.geojson`, which the v2 grader rejects). Not flagged — the workflow explicitly says "no current runs available" without other suspect signals is not a HUMAN-REVIEW item; the orchestrator's next cross-family sweep will lift this state.
- Instruction body re-checked for redundant statements per the new evaluator rule: attribute preservation appears once (persona paragraph: "Attributes must be untouched."); geometry type / hole preservation is a non-mutation invariant ("Every feature must remain a Polygon with interior rings and holes preserved exactly as they are — do not flatten them") that the schema's `geometry_type: Polygon` alone does not encode and must stay; filename and identity-key are each stated once; no CRS/EPSG/WGS84 phrasing exists to strip (GeoJSON convention covers it). No further redundancy to tighten.
- Coverage axes re-validated against the current `coverage-vocabulary.yaml`: every slug present (`data-cleaning`, `l1`, `geojson`, `wgs84`, `bundled-local`, `wrong-ring-orientation`, `polygon`, `buildings.building`, `building`, `tokyo`, `small`). Inventory row still names `Wrong ring orientation` as the sole data-quality issue and `Polygon` as the geometry type; cross-check holds.

### 3. Changes applied this run

#### Unilateral edits
- (none) — verdict is `insufficient-evidence`; no tolerance, gift, or subcheck change warranted. `coverage.yaml` re-validated against the current vocabulary (every slug present) and only its `evaluator_run_at` timestamp refreshed. No `task.json.version` bump (this pass applies no contract change).

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- pytest: pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

One new commit touches the task directory since the prior (fourth) pass:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 05aabd64 | grader-change | Softened CRS hard-fail to two soft subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) across 21 graders. For this task: added `grade_crs_soft` import, dropped `is_wgs84` import, added `CANONICAL_EPSG = 4326` and `MEANINGFUL_EPSGS = {4326}` module constants, replaced the inline `is_wgs84(sub.crs)` gate with `grade_crs_soft(..., treat_none_as_wgs84=True)`, and appended the two new CRS subchecks. Subcheck count rose 7 → 9. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — explains the policy and shows aggregate +0.040 on Gemma run from recovering CRS-only failures. |

The full change log reconstructed in the first-pass block remains accurate for everything prior. The prior-pass cutoff was 2026-05-28T12:46:39Z (b32486bc rename); the new cutoff is the 05aabd64 grader-change at 2026-05-28T19:02:57Z, invalidating every run started before that timestamp.

### 2. Current-state review

This pass is the first re-evaluation under the post-soft-CRS grader. Five new `current` runs across three capability-distinct adapter families are now available, all scoring 1.0.

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57Z** (commit `05aabd64`, class: grader-change — soft CRS subchecks added, subcheck count 7 → 9, score denominators change).

#### Runs considered
| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic | claude-code | 2026-05-28T19:42:43Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-28T22:34:13Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | claude-code | 2026-05-28T23:44:32Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-29T01:21:02Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | openrouter | 2026-05-29T09:48:03Z | 1.0 | done | current |
| run-20260528-1624Z and earlier | various | various | up to 2026-05-28T16:47:15Z | mixed | various | stale (pre-cutoff) |

Five **current** runs from three capability-distinct adapters: Claude Code / Opus 4-7, OpenRouter / Gemma 4 26B, and OpenRouter / DeepSeek V4 Pro. All five score 1.0 with all 9 subchecks passing (re-read from each run's `score.json`). One stale outlier worth noting: `run-20260528-0113Z` (Opus, pre-cutoff) scored 0.0 — that is the only non-1.0 outcome in any post-rename run. Spot-checked: it produced the new filename but with a Gate 1 / column-set issue; the post-soft-CRS grader's outcome on the same submission would not change because the failure mode was structural, not CRS. Not used as evidence either way (pre-cutoff).

#### Per-run output inspection
- All five current runs produced `tokyo_buildings_fixed.geojson` (plus helper `solve.py` / inspection scripts; none of which match `expected_outputs[]` and are ignored).
- Each: 9/9 subchecks pass, including both new CRS subchecks (`crs_is_canonical`, `crs_in_meaningful_set`). Light comparison vs reference: 100 features, columns `{building_class, feature_id, geometry, height, name_primary, overture_id}`, CRS EPSG:4326, geometry types `{Polygon}` only — matches on every dimension the grader reports.

#### Output-CRS and format consistency (2c-CRS)
- Agent output CRS (4326) == reference output CRS (4326). No one-sided reprojection: `grade_crs_soft` normalises only the submission (reprojecting to canonical for downstream subchecks) but does not touch the reference, which is already canonical; orientation subchecks read `is_ccw` from the submission's geometry post-normalisation, which is a safe no-op when the submission is already 4326. Clean.
- Reference output CRS/format (EPSG:4326, GeoJSON) == `expected_outputs[]`. Match.
- README's stated output (EPSG:4326, GeoJSON) == reference. Match.

#### Verdict
**calibrated**

The task discriminates correctly under the new soft-CRS grader:
- Reference scores 9/9 = 1.0. Broken-solution scores re-measured this pass: `wrong_format` 0.0 (Gate 1 reject on the dropped `overture_id`), `wrong_orientation` 7/9 ≈ 0.778 (both orientation subchecks fail, the seven preservation + CRS subchecks all pass), `partial_orientation` 8/9 ≈ 0.889 (only `interior_rings_cw` fails). All three sit inside the declared ranges in `metadata.yaml` (`[0.0, 0.0]`, `[0.65, 0.78]`, `[0.8, 0.9]`).
- Five current runs across three capability-distinct adapter families all scored 1.0. The instruction body still names no EPSG code, no RFC standard, no "ring orientation", and no library function — Step 2d's `too-easy` requires both all-1.0 *and* an over-specifying instruction; the second criterion does not hold, so the verdict is not `too-easy`. The transcript-level rebuttal of gift-exploitation was established in the second pass and is unchanged by the CRS softening.
- No `too-strict` or `prompt-grader-inconsistent` signal: every correct-looking output scored 1.0; the soft-CRS policy only relaxes a previously-strict gate, so any sample that passed under the old grader still passes here. Pytest 41/41.

The `wrong_orientation` and `partial_orientation` `measured_score` values in `metadata.yaml` were stale from the v1 (7-subcheck) grader (0.714, 0.857) — refreshed this pass to the v2 (9-subcheck) values (0.778, 0.889). The declared `expected_score_range` brackets remain valid: 0.778 < 0.78 and 0.889 < 0.9.

#### Specific findings
- README failure mode #6 ("Re-orient and accidentally change CRS") described Gate 1's `crs.to_epsg() == 4326` as the detector, which is no longer accurate after the soft-CRS softening — Gate 1 now passes for any parseable CRS, and the two soft CRS subchecks dock points instead. Refreshed unilaterally (docs-change; no version bump).
- `task.json` had no `analyst_notes` field. Authored this pass per the evaluator-prompt rule ("Author `analyst_notes` if it is missing"). Human-facing only, no version bump.
- Coverage axes re-validated against the current `coverage-vocabulary.yaml`: every slug present (`data-cleaning`, `l1`, `geojson`, `wgs84`, `bundled-local`, `wrong-ring-orientation`, `polygon`, `buildings.building`, `building`, `tokyo`, `small`).

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `analyst_notes` (description + approach + pitfalls). Re-grade on reference: 1.0 (9/9). Reason: required by the evaluator prompt when missing; human-facing only, no `version` bump per spec.
- `metadata.yaml`: refreshed `broken_solutions.wrong_orientation.measured_score` 0.7143 → 0.7778 and `partial_orientation.measured_score` 0.8571 → 0.8889 to match the 9-subcheck grader; also updated the `description` text from "5/7" / "6/7" to "7/9" / "8/9" so the rationale lines up with the new measured values. Reason: explicit non-bump edit allowed by spec ("Update `metadata.yaml > broken_solutions > measured_score` to the current grader's score on each broken set").
- `README.md`: refreshed failure mode #6 to describe the soft-CRS subcheck deduction policy instead of the obsolete Gate 1 EPSG-equality reject. Reason: docs-change, README was stale post-05aabd64; no version bump.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp only; every slug re-validated against current vocabulary.

No `task.json.version` bump this pass: the only `task.json` edit is `analyst_notes` (human-facing, explicitly excluded from the bump list); README and `metadata.yaml > broken_solutions.measured_score` and `coverage.yaml` are all excluded from the bump list as well.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (9/9 subchecks)
- broken solutions: wrong_format 0.0, wrong_orientation 0.778, partial_orientation 0.889 (all in declared ranges)
- pytest: pass (41/41)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geometry-type uniformity (Polygon) migrated to a new
  `geometry_type_polygon_only` subcheck.
- Feature-count tolerance (±5%) migrated to a new
  `feature_count_within_tolerance` subcheck.
- Subcheck total: 9 → 11.

### Verification
- Reference solution re-graded: 1.0 (11/11 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

Two new commits touch the task directory since the prior (2026-06-06) evaluator pass and the manual gate-2 cleanup note:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed21 | grader-change | Removed `Gate("structural_correctness", ...)` and its early-return; geometry-type uniformity and the ±5% feature-count window migrated to two new salvageable subchecks (`geometry_type_polygon_only`, `feature_count_within_tolerance`). Subcheck total 9 → 11. Docstring rewritten to describe the single-gate model. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" - benchmark-wide consistency refactor; shape-recoverable outputs now cost points instead of collapsing to 0. |
| 2026-06-07 | c749e57b | grader-change | Added `weight=3.0` to the eight data-content subchecks (count, both orientation checks, id-set, extent IoU, holes, attributes, per-feature IoU); `geometry_type_polygon_only` and the two CRS subchecks stay at weight 1. Weighted total 27. | Commit msg: "Weight data-content subchecks 3x across all categories" - benchmark-wide policy; score is now sum(weight passed)/sum(weight). |

The full change log reconstructed in the first-pass block remains accurate for everything prior. Cross-checked the `weight=3.0` placement against sibling dc/fio graders: count-tolerance subchecks carry weight 3.0 there too, so this task is consistent with the benchmark-wide policy.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:32:38Z** (commit `c749e57b`, class: grader-change - subcheck weighting). The prior cutoff was 2026-05-28T19:02:57Z (05aabd64 soft-CRS).

#### Runs considered
| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | openrouter / deepseek | 2026-06-09T10:06:16Z | 1.0 | done | current (suite ec540aa contains c749e57; task_version 2 == then-current) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | openrouter / deepseek | 2026-06-08T09:18:24Z | 1.0 | done | current (suite 6510297 contains c749e57; task_version 2 == then-current) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | openrouter | 2026-06-07T13:19:28Z | 1.0 | done | stale (pre-weighting cutoff by ~5h) |
| run-20260606-1733Z / -1129Z | openrouter-gemma4-26b-detailed | openrouter | 2026-06-06 | 1.0 | done | stale (pre-cutoff) |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | openrouter | 2026-06-06T09:55:11Z | - | failed | stale; model-side (max iterations exceeded (50)), not task evidence |
| run-20260606-1334Z / run-20260607-112405Z | openrouter-gemma4-26b-detailed | openrouter | 2026-06-06/07 | - | cancelled | stale; cancelled, not evidence |
| 37 earlier runs (2026-05-12 - 2026-05-29) | various incl. claude-code-opus, gemma4-26b, deepseek-v4-pro | various | pre-cutoff | mixed | various | stale (predate the 363aed21/c749e57b grader changes; the five 2026-05-28/29 runs across three families all scored 1.0 under the 9-subcheck grader) |

#### Per-run output inspection
- Both current runs produced exactly `tokyo_buildings_fixed.geojson` (plus a helper `solve.py` and a copied `tokyo_buildings_legacy.geojson`, neither of which matches `expected_outputs[]`).
- Both: 100 features, columns `{building_class, feature_id, geometry, height, name_primary, overture_id}`, CRS EPSG:4326, geometry types `{Polygon}` only, 100/100 exterior rings CCW, 5/5 polygons-with-holes, 5/5 interior rings CW. score.json shows 11/11 subchecks passing with the new weights persisted (eight at 3.0, three at 1.0).

#### Output-CRS and format consistency (2c-CRS)
- Agent output CRS (4326) == reference output CRS (4326). `grade_crs_soft` normalises only the submission and only as a declared accept-list policy (`MEANINGFUL_EPSGS = {4326}`, canonical 4326, `treat_none_as_wgs84=True` per RFC 7946); no one-sided reprojection papering over a mismatch.
- Reference output (EPSG:4326 GeoJSON, Polygon) == `expected_outputs[]`. Match.
- README's stated output (EPSG:4326 GeoJSON) == reference. Match.

#### Prompt information audit (2c-INFO)
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output filename `tokyo_buildings_fixed.geojson` | instruction | stated |
| readable GeoJSON output | instruction (filename + "GeoJSON web viewers") | stated |
| CRS WGS84 (soft subchecks; gate accepts any parseable CRS) | GeoJSON convention (RFC 7946) + input file's CRS84 member | inferable |
| required columns (feature_id, overture_id, name_primary, building_class, height) | "Attributes must be untouched" + input schema | inferable |
| Polygon-only geometry | instruction ("must remain a Polygon") | stated |
| exterior CCW / interior CW (the central skill) | diagnosed from symptoms + RFC 7946 domain knowledge | inferable (by design; the deliberate gotcha) |
| feature count ±5% / feature_id set preserved | "Attributes must be untouched", "feature_id is the join key", fix-not-filter framing | inferable |
| extent and per-feature IoU >= 0.99 | "holes preserved exactly as they are", fix-only-geometry framing | inferable |
| polygons-with-holes count preserved | instruction ("interior rings and holes preserved exactly") | stated |

Factual claims verified: input filename `tokyo_buildings_legacy.geojson` exists in `inputs/`; the symptoms description matches the data (all 100 exteriors CW, all 5 interiors CCW in the legacy file, the inverse of RFC 7946); output filename matches `expected_outputs[]`; `feature_id` exists and is a unique integer key. No missing or inaccurate claim.

#### Reference faithfulness (2c-REF)
`reference/solution/generate.py` reads the bundled file, applies `shapely orient(sign=1.0)` per feature (exterior CCW, interior CW), preserves all attributes (NaN -> null normalisation only, a JSON-serialisation necessity), keeps CRS84/WGS84, and writes deterministic GeoJSON. The `feature_id` sort is a determinism measure, not a semantic deviation. Faithful; no unrequested operations, no skipped steps, CRS choice pinned by the format.

#### Verdict
**insufficient-evidence**

Only two `current` runs exist and both come from the same model family (DeepSeek V4 Flash, basic + detailed prompt variants), so Step 2d's one-family rule pins the verdict at insufficient-evidence. The corroborating evidence nonetheless points firmly at calibrated: (a) both grader changes since the last calibrated verdict (gate-2 removal, 3x weighting) are score-preserving for any run in which every subcheck passes, so the five pre-cutoff 1.0 runs across three capability-distinct families (Opus 4-7, Gemma 4 26B, DeepSeek V4 Pro) transport to 1.0 under the current grader deterministically; (b) both current runs scored 1.0 with clean 11/11 subchecks; (c) broken sets re-measured this pass at 0.0 / 0.778 (21/27) / 0.889 (24/27), all inside the declared ranges (the weighted ratios coincide numerically with the old 7/9 and 8/9, so `measured_score` values were already accurate); (d) the instruction still names no EPSG code, no RFC standard, no "ring orientation", and no library function, so the too-easy criterion's over-specification arm does not hold. No too-strict or prompt-grader-inconsistent signal. The one failed June run (gemma, max-iterations) is a model-side failure, not task evidence. Note: this pass's house-style instruction edit bumps `version` 2 -> 3, so the two current runs become version-stale for future passes; the edit is punctuation/register only and cannot change task semantics.

#### Specific findings
- The instruction contained two em-dashes and referenced the input as `tokyo_buildings_legacy` instead of its actual filename, plus the jargon tail "join key for feature identity". Fixed unilaterally under the house-style rule (content unchanged, no facts added or removed); `version` bumped 2 -> 3. Re-grade on reference: 1.0.
- `analyst_notes` contained three em-dashes; reworded per the analyst-notes house-style rule (no version bump, human-facing only).
- `metadata.yaml > broken_solutions` descriptions still framed scores as "7/9" / "8/9" and cited "Gate 1"; refreshed to the weighted 21/27 / 24/27 framing and the single `format_schema_valid` gate. `measured_score` values re-measured and numerically unchanged (0.778 / 0.889 / 0.0).
- README was stale after the gate-2 removal and weighting commits: broken scores 0.714/0.857 (now 0.778/0.889), "Gate 2's count tolerance" (now the `feature_count_within_tolerance` subcheck), "Gate 1" naming, and a pre-reorg `data/` path. Refreshed (docs-change).
- `grade.py` had one stale comment referencing "Gate 2's count window"; reworded (comment-only, no logic change; covered by this pass's single version bump).
- Inventory row still lists the pre-rename output filename `tokyo_buildings_rfc7946.geojson`. This divergence is the deliberate, fully documented HR-001 resolution (commit b32486bc, `metadata.yaml > design_note`), so it is recorded here as a known intentional divergence rather than flagged as inventory-mismatch.
- Coverage axes re-validated against `coverage-vocabulary.yaml`: every slug present (`data-cleaning`, `l1`, `geojson`, `wgs84`, `bundled-local`, `wrong-ring-orientation`, `polygon`, `buildings.building`, `building`, `tokyo`, `small`).

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style instruction rewrite (em-dashes removed, actual input filename, jargon tail dropped), analyst_notes em-dashes removed, `version` 2 -> 3. Re-grade on reference: 1.0. Reason: house-style rules (no em-dashes, reference files by filename) applied mechanically; no content change.
- `grade.py`: comment-only fix of a stale "Gate 2" reference. Re-grade on reference: 1.0. Reason: gate 2 no longer exists; no logic change.
- `metadata.yaml`: broken-solution descriptions refreshed to the weighted 21/27 / 24/27 framing and single-gate naming; `measured_score` values re-measured (numerically unchanged). Reason: stale after 363aed21/c749e57b; explicit non-bump edit.
- `README.md`: refreshed broken scores, gate naming, count-subcheck detection, and the stale `data/` input path. Reason: docs-change, stale post-refactors.
- `coverage.yaml`: `evaluator_run_at` timestamp refreshed; all slugs re-validated.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (11/11 subchecks, weighted 27/27)
- broken solutions: wrong_format 0.0, wrong_orientation 0.778, partial_orientation 0.889 (all in declared ranges)
- pytest: pass (41/41)

---

## Grader weight recalibration 2026-06-14  (evaluator-commit <pending>)

### Change
**RECALIBRATED.** Replaced the blunt benchmark-wide weighting (commit c749e57: every "data-content" subcheck at weight 3.0, everything else at 1.0) with severity-tiered weights reasoned from what this task actually tests. The central skill is RFC 7946 §3.1.6 ring-orientation repair, so the two orientation subchecks now carry the top weight; structural-identity preservation sits one tier below; geometric-drift guards below that; geometry-type and CRS stay cosmetic. Grading-only change: no logic, threshold, or gate was touched, and `task.json.version` is unchanged (3).

### Weight changes
| Subcheck | Old | New | Tier / rationale |
|---|---|---|---|
| `exterior_rings_ccw` | 3.0 | **5.0** | Central skill (RFC 7946 §3.1.6, clause 1) |
| `interior_rings_cw` | 3.0 | **5.0** | Central skill (RFC 7946 §3.1.6, clause 2) |
| `feature_id_set_preserved` | 3.0 | 3.0 | Structural identity (unchanged) |
| `polygons_with_holes_preserved` | 3.0 | 3.0 | Structural identity (unchanged) |
| `attributes_preserved` | 3.0 | 3.0 | Structural identity (unchanged) |
| `feature_count_within_tolerance` | 3.0 | **2.0** | Geometric-drift guard (coarse row drop/dup) |
| `geometric_extent_preserved` | 3.0 | **2.0** | Geometric-drift guard (stray simplify/buffer) |
| `per_feature_geometry_preserved` | 3.0 | **2.0** | Geometric-drift guard (per-feature vertex edit) |
| `geometry_type_polygon_only` | 1.0 | 1.0 | Cosmetic (unchanged) |
| `crs_is_canonical` | 1.0 | 1.0 | Cosmetic / soft CRS (unchanged) |
| `crs_in_meaningful_set` | 1.0 | 1.0 | Cosmetic / soft CRS (unchanged) |

Weighted denominator: 27 → 28.

Rationale: under the old scheme the central orientation checks carried the **same** weight (3.0) as six preservation/guard subchecks, so doing the entire requested job and doing nothing-but-preserve-everything were only ~0.22 apart. The new tiers make the central-skill failure bite (a do-nothing pass-through drops to 0.643, clearly failing) while a cosmetic CRS slip only docks to 0.964. Geometric-drift guards (count, extent IoU, per-feature IoU) detect side-effects of a bad fix rather than the fix itself, so they sit at weight 2 between structural-identity loss (weight 3, unrecoverable corruption: a dropped column, a lost hole, a missing id) and the cosmetic tier.

### Broken-score before → after
| Broken | Before | After | Severity note |
|---|---|---|---|
| `wrong_format` | 0.0 | 0.0 | Gate fail (dropped `overture_id`); weighting cannot touch a gated-out submission |
| `wrong_orientation` | 0.778 | **0.643** | Most severe non-gate failure: central skill not performed at all (both orientation checks fail) |
| `partial_orientation` | 0.889 | **0.821** | Less severe: exteriors fixed, only the interior clause missed (one orientation check fails) |

Ordering: monotone and defensible — 0.0 < 0.643 < 0.821 < 1.0. The two brokens fail nested subsets of the orientation checks (partial ⊂ wrong), so up-weighting orientation cannot invert their order; no disjoint-failure trap. Single-failure severity sweep confirms the four tiers separate cleanly (orientation 0.821 < structural-identity 0.893 < geom-drift 0.929 < cosmetic 0.964 for any single subcheck).

### Prior-run re-grade summary
Re-graded the version-3 / post-c749e57 runs. The 2026-06-11 block lists the `current` runs as run-20260608-074701Z and run-20260609-084636Z (DeepSeek V4 Flash, basic + detailed); also re-checked run-20260607-112430Z (stale, pre-weighting) and two June-06 gemma runs. All five scored 1.0 before and 1.0 after — perfect submissions are weight-invariant, so the recalibration moves no passing run. The discriminating evidence is on the broken sets (above), which is where weighting matters. No notable shifts among real runs.

### HR
No human-review items existed (empty list); none invented.

### Threshold note
No threshold or check-logic concern surfaced. The strict 100% orientation pass and the 0.99 IoU / 0.95 Jaccard floors remain appropriate for this fully-bundled, no-drift fixture (per the metadata `tolerances.rationale`); they were left untouched as required.

### Tests run
- grader on reference: 1.0 (weighted 28/28)
- broken solutions: wrong_format 0.0, wrong_orientation 0.643, partial_orientation 0.821 (all in refreshed declared ranges)
- pytest: not run (orchestrator runs the suite)
