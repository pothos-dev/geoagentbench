# Implementation notes — geo-l1-cairo-multipoint-hull

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 geometric-operation task: 20 Cairo Metro stations as MultiPoint
geometries of street-level entrances → per-station convex hull
Polygons, bilingual `station_name_en` / `station_name_ar` preserved.
Reference, grader, and three broken solutions built and verified
inside the project Docker container.

## Verification results
- Reference grader score: 1.00 (6 / 6 subchecks pass).
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    (CSV-WKT cannot parse as GeoJSON).
  - bbox_instead_of_hull: 0.833 (expected range [0.78, 0.90]) — 5 / 6
    pass; only `hull_iou_against_reference` fails (mean per-station
    IoU ≈ 0.7 between bbox and hull).
  - empty_arabic: 0.667 (expected range [0.55, 0.75]) — 4 / 6 pass;
    `station_name_ar_populated` and `arabic_names_match` both fail.
- Second-run output match: bit-identical (verified with `diff -q` on
  `reference/outputs/cairo_metro_hulls.geojson` before / after a
  second `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Output not GeoJSON (CSV/Parquet/raw WKT): broken_wrong_format
- Bounding box returned instead of convex hull: broken_bbox_instead_of_hull
- Arabic name column blanked: broken_empty_arabic
- Global hull instead of per-row: principled — Gate 2 row-count check
- Reprojection to metric CRS without converting back: principled —
  Gate 1 CRS check
- Buffered points instead of convex hull: principled —
  `hull_iou_against_reference`
- Sort-mismatch pairing wrong attributes with wrong hull: principled —
  `hull_contains_input_points`
- No operation applied (output still MultiPoint): principled — Gate 2
  geometry-type check

## Open issues
- [severity: low] Bundled input is hand-crafted rather than sliced
  from Overture or fetched from OSM. Rationale: Overture has no
  `subway_entrance` feature, and OSM's `railway=subway_entrance`
  nodes do not consistently expose a parent-station link, so neither
  source can produce the persona's "one MultiPoint per station,
  bilingual names" inventory cleanly. The 20 stations and their
  WGS84 centres are real Cairo Metro stations; the per-station
  entrance offsets are seeded synthetic values.

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — the grader uses `Gate`, `Subcheck`, `ScoreReport`,
`feature_set_equality_by_id`, and `iou_with_tolerance`. Per-station
IoU is computed by looping `iou_with_tolerance` over matched
station_name_en pairs.)

## Runtime
~10 minutes (no Overture fetch; all generation and verification local
in Docker).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row (Category: geometric_ops, L1, Region: Cairo, Primary
op: Convex hull, MultiPoint → Polygon, GeoJSON in/out, EPSG:4326 in/out,
OSM tag `railway=subway_entrance`) and the first commit's README, the
task probes per-feature convex hull on MultiPoint geometries plus
attribute carry-through (`station_name_en` and `station_name_ar`). The
twist tested is per-row vs. global hull and not losing the bilingual
attribute columns; no projection, no fetching, no chained transforms.
Bundled-local input (hand-crafted because neither Overture nor OSM
supplies the persona's per-station-MultiPoint inventory cleanly), 20
real Cairo Metro stations with seeded synthetic 3–5 entrance offsets.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 391238ef | initial-authoring | Initial task: README, prepare script, input GeoJSON, grade.py, metadata.yaml, reference generate.py + outputs, three broken solutions, task.json | (initial) |
| 2026-05-12 | ca819c84 | docs-change | Added visualize.py (tippecanoe pmtiles for UI) | Commit msg: shared visualisation helper across all geometry-producing tasks |
| 2026-05-13 | 1710715e | prompt-change | Added explicit "Output schema:" bullet block (filename, EPSG, required columns, geometry-type) to instruction | Commit msg: "declare exact output schema in prompts to match graders. No grader changes; no subchecks loosened." |
| 2026-05-13 | 284b8436 | docs-change | Added `tags` dictionary (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) to task.json | Commit msg: derived from inventory axes; for benchmark filtering, not seen by agent |
| 2026-05-13 | 89150101 | docs-change | Added image-prompt.md (task card image generation prompt) | Commit msg: 36-task batch addition |
| 2026-05-13 | 1b8dda17 | docs-change | Added image.webp (task card image) | Commit msg: 36-task batch generation via fal.ai FLUX schnell |
| 2026-05-13 | a3a8d535 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: directory split between authoring and eval subtrees |
| 2026-05-13 | 3c653731 | docs-change | Regenerated image.webp (FLUX schnell batch) | Commit msg: 36-task batch |
| 2026-05-13 | cfbdc7c6 | docs-change | Regenerated image.webp (nano-banana-2, 0.5K, 3:2) | Commit msg: regen with different generator |
| 2026-05-13 | 9e79176a | prompt-change | Folded the structured "Output schema:" bullet list back into a fluent paragraph: "Every row must carry `station_name_en` and `station_name_ar`, both non-empty, with the original Arabic strings and diacritics preserved … Each feature's geometry should be a Polygon — one row per station, no other geometry types." | Commit msg: stylistic — merge bullet list into prose for 6 tasks |
| 2026-05-14 | f40e39e9 | prompt-change | Removed "as a MultiPoint of its street-level entrances" → "has each Metro station's street-level entrances" (drops the explicit MultiPoint hint) | Commit msg: "Strip deducible information from GEO task instructions" |
| 2026-05-18 | f0c244a6 | grader-change | Replaced inline `sub.crs is not None and sub.crs.to_epsg() == 4326` with shared `is_wgs84(sub.crs)` helper | Commit msg: consolidate WGS84 CRS checks into shared `geo_grading` package; behaviour preserved |
| 2026-05-26 | 29a9ae32 | mixed (path-refactor: grade.py + task.json input URL; rename data/ → inputs/, reference/outputs → reference/solution/outputs, tests/ → reference/failures/; IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md) | Layout migration; INPUT and REFERENCE_OUT paths in grade.py updated to match; task.json input URL updated | Commit msg: cleaner layout separating audience concerns; mechanical path-rewrite, no semantic change |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (commit 29a9ae32, class: mixed — path refactor in grade.py + task.json). The cutoff is conservative; the substantive prompt cutoff is 2026-05-14T15:53:08Z (f40e39e9) and the substantive grader cutoff is 2026-05-18T06:35:57Z (f0c244a6 — `is_wgs84` is behaviour-equivalent to the inline check).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:48:55Z | 1.0 | done | current (post-cutoff) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:24:31Z | 1.0 | done | stale (pre-cutoff, post-stripping) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:54:11Z | 1.0 | done | stale |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T06:14:49Z | 1.0 | done | stale |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T03:04:41Z | 1.0 | done | stale |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T01:34:10Z | 1.0 | done | stale |
| run-20260516-2248Z | claude-code-opus-basic | 2026-05-16T22:48:39Z | 1.0 | done | stale |
| run-20260516-1130Z | claude-code-opus-basic | 2026-05-16T11:30:39Z | 1.0 | done | stale |
| run-20260516-0743Z | claude-code-opus-basic | 2026-05-16T07:43:12Z | 1.0 | done | stale |
| run-20260515-2053Z | claude-code-opus-basic | 2026-05-15T20:53:19Z | 1.0 | done | stale |
| run-20260515-0926Z | openrouter-deepseek-v4-flash-basic | 2026-05-15T09:26:19Z | 1.0 | done | stale |
| run-20260515-0624Z | claude-code-opus-basic | 2026-05-15T06:24:12Z | 1.0 | done | stale |
| run-20260514-1554Z | claude-code-opus-basic | 2026-05-14T15:54:15Z | 1.0 | done | stale (just-post-stripping) |
| run-20260514-1245Z | claude-code-opus-basic | 2026-05-14T12:45:40Z | 1.0 | done | stale (pre-stripping prompt) |
| run-20260514-0946Z | claude-code-opus-basic | 2026-05-14T09:46:23Z | 1.0 | done | stale |
| run-20260513-0943Z | openrouter-hy3-preview-basic | 2026-05-13T09:43:44Z | 1.0 | done | stale |
| (4) run-20260513-{0922,0926,0928,0937}Z | openrouter-gemma4-26b-basic | 2026-05-13 | null | failed | stale; harness error: "ConnectError: All connection attempts failed" — infra, not task |
| run-20260513-0108Z / 20260512-2314Z / 20260512-1753Z / 20260512-1618Z | claude-code-sonnet-basic / openrouter-deepseek-v4-flash | 2026-05-12/13 | 1.0 | done | stale |
| run-20260512-0832Z / 20260512-0833Z | claude-code-haiku-basic | 2026-05-12T08:32:47Z / 08:33:46Z | 1.0 | done | stale |
| run-20260512-0704Z / 20260512-0706Z | claude-code-haiku-basic | 2026-05-12T07:04:51Z / 07:06:12Z | 0.0 | done | stale; output file never created (model-side: haiku copied input only). Gate 1 reject. Not task miscalibration. |

#### Verdict
**insufficient-evidence**

Only one run started after the 2026-05-26 layout-refactor cutoff
(openrouter-gemma4-26b-basic, score 1.0, all 6 subchecks pass on 20/20
stations). All output features are Polygon, EPSG:4326, with correct
Arabic-script `station_name_ar` preserved (e.g. "الشهداء"). Reference
grader re-grades 1.00; broken-solution grades match the documented
[0.0, 0.833, 0.667] expected values exactly (`grade.py` on the three
`reference/failures/broken_*/outputs/` directories — see §3).
With only one post-cutoff agent, the bar for `calibrated` is not met.
The 18 stale post-stripping runs (from 2026-05-14 onwards) all scored
1.0 across claude-opus, claude-sonnet, openrouter-deepseek-v4-flash,
openrouter-hy3-preview, and openrouter-gemma4-26b — five agents from
three families — which is suggestive evidence that the L1 task is
correctly easy but not over-easy: the only two zero-scoring stale runs
(haiku at 0704Z/0706Z) failed by not producing the output file at all
(model-side failure, not task miscalibration). The 4 null-score gemma
runs at 0922–0937Z were a harness connection failure, not a task
problem. The instruction-stripping commit f40e39e9 removed the
"MultiPoint" hint cleanly; the remaining instruction names the operation
("convex hull") because the task IS the convex-hull operation (L1
single-op tasks legitimately name their operation per the
instruction-stripping guide §"L1 — single operation, bundled data").
The output CRS (EPSG:4326) is part of the output contract and stays.

#### Specific findings
- The current post-stripping prompt is consistent with the L1 stripping rules in `authoring/instruction-stripping-guide.md`: operation named (allowed for L1), output CRS stated (output contract), bilingual-preservation rule kept (business rule the agent cannot deduce from a GeoJSON output schema).
- The grader matches the metadata's documented broken-solution scores exactly (0.0 / 0.833 / 0.667). No miscalibration evidence.
- The single current run scored 1.0; needs at least one more current run from a different agent family to upgrade verdict from `insufficient-evidence` to `calibrated`. No proposed change — this is a sweep-pacing issue, not a task issue.
- The reorg commit's grade.py edit was a path-only rewrite (`INPUT` and `REFERENCE_OUT` constants updated to the new `inputs/` and `reference/solution/outputs/` paths). The grader's logic and tolerances are unchanged from the post-stripping period, so the stale-but-post-stripping runs (2026-05-14 onwards) are reliable indicators of agent behaviour even though they are formally pre-cutoff.

### 3. Changes applied this run

#### Unilateral edits
- None.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.00 (6/6 subchecks pass)
- grader on `reference/failures/broken_wrong_format/outputs`: 0.0 (matches expected [0.0, 0.0])
- grader on `reference/failures/broken_bbox_instead_of_hull/outputs`: 0.833 (matches expected [0.78, 0.90])
- grader on `reference/failures/broken_empty_arabic/outputs`: 0.667 (matches expected [0.55, 0.75])
- pytest (benchmark/eval): pass (35/35)

---

## Evaluator review 2026-05-26 (re-run)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the prior evaluator-review block: per the inventory row
(geometric_ops, L1, Cairo, primary op Convex hull, MultiPoint → Polygon,
GeoJSON in/out, EPSG:4326 in/out, OSM tag `railway=subway_entrance`) and
the first commit, the task probes per-feature convex hull on MultiPoint
geometries plus bilingual attribute carry-through. The tested twist is
per-row vs. global hull and not dropping `station_name_en` /
`station_name_ar`. Bundled-local hand-crafted input (20 real Cairo Metro
stations, seeded synthetic 3–5 entrance offsets), no projection, no fetch.

#### Change log
No new commits touch the task directory since the prior evaluator block.
The git history is unchanged through 29a9ae32 (the 2026-05-26 layout
refactor) plus the prior evaluator's own commit 516d5fba ("Re-evaluate
geo-l1-cairo-multipoint-hull: insufficient-evidence"), a docs-change that
wrote only the three audit artefacts and does not affect the answer key
or instruction. See the prior block's change-log table for the full
chronology — it is accurate and not repeated here.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (= 09:51:37Z) (commit 29a9ae32, class: mixed — path refactor in grade.py + task.json). Unchanged from the prior block; the prior evaluator's commit 516d5fba is a docs-change and does not move the cutoff.

#### Runs considered
This re-run revisits the same cutoff with two additional post-cutoff runs
that were added after the prior evaluation. Only post-cutoff (`current`)
runs are listed; the 25 pre-cutoff runs are documented in the prior block
and are treated as stale.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic (claude-code / claude-opus-4-7) | 2026-05-26T19:00:32Z | 1.0 | done | current (post-cutoff) |
| run-20260526-1922Z | openrouter-gemma4-26b-basic (openrouter / gemma-4-26b) | 2026-05-26T19:42:58Z | 1.0 | done | current (post-cutoff) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (openrouter / gemma-4-26b) | 2026-05-26T08:58:59Z | 1.0 | done | current (post-cutoff) |

Three current runs across two agent families (claude-code, openrouter).
All three produced `cairo_metro_hulls.geojson` matching the reference
schema exactly: 20 Polygon features, CRS84/EPSG:4326, both
`station_name_en` and `station_name_ar` present with Arabic script
preserved (e.g. "الشهداء"). All 6 subchecks pass on every run
(en/ar populated 20/20, English Jaccard 1.0, Arabic match 20/20, hull
contains input 20/20, mean per-station IoU 1.0).

#### Verdict
**calibrated**

The prior block's `insufficient-evidence` rested solely on having only one
post-cutoff run. There are now three current runs spanning two families
(claude-opus-4-7 and gemma-4-26b), clearing the ≥2-runs / >1-family bar.
The verdict is `calibrated`, not `too-easy`: this is an L1 single-op task,
which the design intends to be easy, and the two agents are of very
different capability (frontier Opus vs. a small open Gemma). The Gemma
run's `solve.py`
(`benchmark/eval/runs/run-20260526-1922Z/geo-l1-cairo-multipoint-hull/outputs/solve.py`)
shows genuine independent reasoning — it groups per station, reprojects to
UTM 36N to compute the hull, projects the result back to WGS84, and
explicitly handles the degenerate (non-Polygon) hull case — i.e. it
solved the per-row-hull twist on its own rather than transcribing a
hand-held recipe. That is the signature of a correctly-easy L1 task, not
an over-specified one. Per `instruction-stripping-guide.md` §"L1 — single
operation, bundled data", naming the operation ("convex hull") is allowed
for L1 (the task IS the operation); the output CRS is part of the output
contract and stays; the bilingual-preservation rule is a persona business
constraint the agent cannot deduce from a GeoJSON output schema. The
"MultiPoint" hint was already stripped in f40e39e9. No gift remains to
strip. Grader re-grades reference 1.00 and the three broken sets at
0.0 / 0.833 / 0.667, matching `metadata.yaml` exactly — no grader
miscalibration.

#### Specific findings
- Verdict upgraded `insufficient-evidence` → `calibrated` purely on the strength of the two newly-added post-cutoff runs; no task content changed since the prior evaluation.
- Both agent families solve the task cleanly with correct schema, CRS, geometry type, and preserved Arabic strings. The weaker model (Gemma) still arrives at the per-row hull independently, confirming the L1 difficulty is appropriate rather than over-easy.
- Grader on reference = 1.00; broken-set scores 0.0 / 0.833 / 0.667 match `metadata.yaml > broken_solutions > measured_score` exactly. pytest 35/35. No miscalibration evidence; no edits warranted.

### 3. Changes applied this run

#### Unilateral edits
- None.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.00 (6/6 subchecks pass)
- grader on `reference/failures/broken_wrong_format/outputs`: 0.0 (matches expected [0.0, 0.0])
- grader on `reference/failures/broken_bbox_instead_of_hull/outputs`: 0.833 (matches expected [0.78, 0.90])
- grader on `reference/failures/broken_empty_arabic/outputs`: 0.667 (matches expected [0.55, 0.75])
- pytest (benchmark/eval): pass (35/35)

---

## Evaluator review 2026-05-27 (sweep re-confirm)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the prior two evaluator-review blocks: per the inventory row
(geometric_ops, L1, Cairo, primary op Convex hull, MultiPoint → Polygon,
GeoJSON in/out, EPSG:4326 in/out, OSM tag `railway=subway_entrance`) and the
initial-authoring commit 391238ef, the task probes per-feature convex hull on
MultiPoint geometries plus bilingual attribute carry-through. The tested twist
is per-row vs. global hull and not dropping `station_name_en` /
`station_name_ar`. Bundled-local hand-crafted input (20 real Cairo Metro
stations along Lines 1 and 2, seeded synthetic 3–5 entrance offsets, 78
entrance points total), no projection, no fetch.

#### Change log
No new commits touch the task directory since the prior `calibrated`
evaluator block. `git log 9fd23b71..HEAD -- benchmark/tasks/geo-l1-cairo-multipoint-hull/`
is empty; the prior evaluator's own commit 9fd23b71 ("Re-evaluate …:
calibrated") was a docs-change writing only the three audit artefacts and does
not affect the answer key or instruction. The full chronology through
29a9ae32 (2026-05-26 layout refactor) is documented in the first
evaluator-review block's change-log table and is accurate; it is not repeated
here. `git log --follow` on the directory misses the initial-authoring commit
391238ef (a directory-level `--follow` limitation); the slug-mention search
confirms 391238ef is the genesis commit, consistent with the prior blocks.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (= 2026-05-26T11:51:37+02:00) (commit 29a9ae32, class: mixed — path refactor in grade.py + task.json input URL). Unchanged from both prior blocks. The prior evaluator commits 516d5fba and 9fd23b71 are docs-changes and do not move the cutoff.

#### Runs considered
No new runs have been added since the prior `calibrated` block; the same three
post-cutoff (`current`) runs apply. The 27 pre-cutoff runs are documented in
the first evaluator block and treated as stale.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic (claude-code / claude-opus-4-7) | 2026-05-26T19:00:32Z | 1.0 | done | current (post-cutoff) |
| run-20260526-1922Z | openrouter-gemma4-26b-basic (openrouter / google/gemma-4-26b-a4b-it) | 2026-05-26T19:42:58Z | 1.0 | done | current (post-cutoff) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (openrouter / google/gemma-4-26b-a4b-it) | 2026-05-26T08:58:59Z | 1.0 | done | current (post-cutoff) |

All three current runs produced `cairo_metro_hulls.geojson` matching the
reference schema exactly: 20 Polygon features, CRS84/EPSG:4326, exactly the two
columns `station_name_en` and `station_name_ar`, Arabic script preserved
(verified directly: feature[0] `station_name_ar` = "الشهداء" in all three
outputs). Output-CRS / format consistency (Step 2c-CRS) holds: the reference
output, `expected_outputs[]`, and the README all declare GeoJSON + EPSG:4326,
and the grader's `is_wgs84` gate is applied to the submission only as a gate
(no one-sided reprojection — the IoU subcheck compares both sides in the same
WGS84 frame).

#### Verdict
**calibrated**

Re-confirms the prior block's `calibrated` verdict with no new evidence. Three
current runs span two agent families (frontier Opus vs. the small open Gemma
4-26b); both solve the per-row-hull task cleanly. This is the intended L1
difficulty — easy by design, but not over-specified: the operation name
("convex hull") is permitted for L1 per `instruction-stripping-guide.md`
(the task IS the operation), the output CRS is part of the output contract,
and the bilingual-preservation rule is a persona business constraint the agent
cannot deduce from a bare GeoJSON output schema. The "MultiPoint" hint was
already stripped in f40e39e9. No gift remains to strip. Grader re-grades the
reference 1.00 (6/6 subchecks) and the three broken sets at 0.0 / 0.833 /
0.667, matching `metadata.yaml > broken_solutions > measured_score` exactly —
no grader miscalibration. pytest 35/35.

#### Specific findings
- No task content changed since the prior `calibrated` evaluation; the directory has had no commits since 9fd23b71 and no new runs. This pass is a sweep re-confirmation.
- Grader on reference = 1.00; broken-set scores 0.0 / 0.833 / 0.667 reproduce `metadata.yaml` exactly. No miscalibration evidence.
- `coverage.yaml` axes all validate against `coverage-vocabulary.yaml`; cross-axis checks are consistent (L1 ⇒ bundled-local; railway OSM tag family, no Overture theme since the input is hand-crafted per the metadata rationale). Only the `evaluator_run_at` timestamp was refreshed.
- No unilateral edits warranted; no HUMAN-REVIEW items.

### 3. Changes applied this run

#### Unilateral edits
- None.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.00 (6/6 subchecks pass)
- grader on `reference/failures/broken_wrong_format/outputs`: 0.0 (matches expected [0.0, 0.0])
- grader on `reference/failures/broken_bbox_instead_of_hull/outputs`: 0.833 (matches expected [0.78, 0.90])
- grader on `reference/failures/broken_empty_arabic/outputs`: 0.667 (matches expected [0.55, 0.75])
- pytest (benchmark/eval): pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the three prior evaluator-review blocks: per the inventory row
(geometric_ops, L1, Cairo, primary op Convex hull, MultiPoint → Polygon,
GeoJSON in/out, EPSG:4326 in/out, OSM tag `railway=subway_entrance`) and the
initial-authoring commit 391238ef, the task probes per-feature convex hull on
MultiPoint geometries plus bilingual attribute carry-through. The tested twist
is per-row vs. global hull and not dropping `station_name_en` /
`station_name_ar`. Bundled-local hand-crafted input (20 real Cairo Metro
stations along Lines 1 and 2, seeded synthetic 3–5 entrance offsets, 78
entrance points total), no projection, no fetch.

#### Change log
One new commit touches the task directory since the prior `calibrated`
sweep-re-confirm block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342be | docs-change | Dropped the unused `prompt_version: 2026-05-08-a` line from `metadata.yaml` (one-line deletion, metadata-only; the repo-wide commit also adds task-content versioning infra outside this task dir) | Commit msg: `prompt_version` "tagged the orchestrator's authoring template, not the task content, and has no runtime relevance. Git history gives us authoring-template age when we need it." |

`metadata.yaml > tolerances`, `metadata.yaml > broken_solutions`,
`task.json` (instruction, inputs, expected_outputs, tags), `grade.py`,
`inputs/`, `reference/`, and the broken-solution fixtures are all unchanged
since the prior block. The dropped field is purely a docs marker, so 622342be
classifies as `docs-change` and does not move the design-affecting cutoff.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (= 2026-05-26T11:51:37+02:00) (commit 29a9ae32, class: mixed — path refactor in grade.py + task.json input URL). Unchanged from all three prior blocks. The new docs-change 622342be does not move the cutoff.

#### Runs considered
Four new post-cutoff runs were added since the prior block. The three runs
from the prior `calibrated` block remain current. Pre-cutoff runs are listed
in the first evaluator block and treated as stale.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic (openrouter / google/gemma-4-26b-a4b-it) | 2026-05-28T04:05:58Z | 1.0 | done | current (post-cutoff) |
| run-20260528-0113Z | claude-code-opus-basic (claude-code / claude-opus-4-7) | 2026-05-28T02:40:38Z | 1.0 | done | current (post-cutoff) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic (openrouter / google/gemma-4-26b-a4b-it) | 2026-05-28T00:53:54Z | 1.0 | done | current (post-cutoff) |
| run-20260527-2016Z | claude-code-opus-basic (claude-code / claude-opus-4-7) | 2026-05-27T22:18:18Z | 1.0 | done | current (post-cutoff) |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:42:58Z | 1.0 | done | current (post-cutoff) |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:00:32Z | 1.0 | done | current (post-cutoff) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:58:59Z | 1.0 | done | current (post-cutoff) |

Seven current runs across two agent families (claude-code, openrouter). All
seven produced `cairo_metro_hulls.geojson` matching the reference schema
exactly: 20 Polygon features, CRS84/EPSG:4326, both columns `station_name_en`
and `station_name_ar` present and non-empty, Arabic script preserved (verified
directly: feature[0] `station_name_ar` = "الشهداء" in all four new outputs).
Output-CRS / format consistency (Step 2c-CRS) holds: the reference output,
`expected_outputs[]`, and the README all declare GeoJSON + EPSG:4326, and the
grader's `is_wgs84` gate runs on the submission as a gate (no one-sided
reprojection; the IoU subcheck compares both sides in the same WGS84 frame).

#### Verdict
**calibrated**

Re-confirms the prior block's `calibrated` verdict, now with more than double
the post-cutoff evidence (7 current runs across the two families, all 1.0).
The two new claude-opus-4-7 runs and two new gemma-4-26b runs continue to
solve the per-row-hull cleanly. This is the intended L1 difficulty — easy by
design, but not over-specified: the operation name ("convex hull") is
permitted for L1 per `instruction-stripping-guide.md` (the task IS the
operation), the output CRS is part of the output contract, and the
bilingual-preservation rule is a persona business constraint the agent cannot
deduce from a bare GeoJSON output schema. The "MultiPoint" hint was already
stripped in f40e39e9. No gift remains to strip. Grader re-grades the reference
1.00 (6/6 subchecks) and the three broken sets at 0.0 / 0.833 / 0.667,
matching `metadata.yaml > broken_solutions > measured_score` exactly — no
grader miscalibration. pytest 41/41 (the test count grew from 35 with the
`geo_grading` CRS accept-list tests landed earlier in the sweep).

#### Specific findings
- No task content changed since the prior `calibrated` evaluation; the only commit touching the directory is the metadata-only docs-change 622342be (`prompt_version` field removed), which does not affect the agent's input or the grader.
- The new task-content versioning infra introduced in 622342be is not yet exercised on this task: `task.json` does not carry an explicit `version` field yet (the prompt's "implicit v1" rule applies). The first future unilateral edit that changes prompt / grader / tolerances / inputs must add `version: 2`; this evaluator pass made no such edit, so no version bump.
- Grader on reference = 1.00; broken-set scores 0.0 / 0.833 / 0.667 reproduce `metadata.yaml` exactly. No miscalibration evidence.
- `coverage.yaml` axes all validate against `coverage-vocabulary.yaml`; cross-axis checks remain consistent (L1 ⇒ bundled-local; railway OSM tag family, no Overture theme since the input is hand-crafted per the metadata rationale). Only the `evaluator_run_at` timestamp was refreshed.
- No unilateral edits warranted; no HUMAN-REVIEW items.

### 3. Changes applied this run

#### Unilateral edits
- None.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.00 (6/6 subchecks pass)
- grader on `reference/failures/broken_wrong_format/outputs`: 0.0 (matches expected [0.0, 0.0])
- grader on `reference/failures/broken_bbox_instead_of_hull/outputs`: 0.833 (matches expected [0.78, 0.90])
- grader on `reference/failures/broken_empty_arabic/outputs`: 0.667 (matches expected [0.55, 0.75])
- pytest (benchmark/eval): pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the four prior evaluator-review blocks: per the inventory row
(geometric_ops, L1, Cairo, primary op Convex hull, MultiPoint → Polygon,
GeoJSON in/out, EPSG:4326 in/out, OSM tag `railway=subway_entrance`) and
initial-authoring commit 391238ef, the task probes per-feature convex hull on
MultiPoint geometries plus bilingual attribute carry-through. The tested twist
is per-row vs. global hull and not dropping `station_name_en` /
`station_name_ar`. Bundled-local hand-crafted input (20 real Cairo Metro
stations along Lines 1 and 2, seeded synthetic 3–5 entrance offsets, 78
entrance points total), no projection, no fetch.

#### Change log
One new commit touches the task directory since the prior `calibrated` block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 05aabd64 | grader-change | Replaced the hard `is_wgs84(sub.crs)` gate with `grade_crs_soft(...)`. CRS mismatch no longer Gate-1-fails; instead the submission is reprojected to canonical and two new subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) dock points. Module-level `CANONICAL_EPSG = 4326`, `MEANINGFUL_EPSGS = {4326}`. Grader denominator rises from 6 to 8 subchecks. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — over-penalisation of recoverable wrong-CRS submissions across the sweep; reproject and dock instead of zero out. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T19:02:57Z (commit 05aabd64, class: grader-change). Moves from the prior 2026-05-26T09:51:37Z cutoff because the CRS-soften touches grader logic and changes the subcheck denominator. All seven post-cutoff runs are new evidence under the new grader; the seven runs documented in the prior block were graded under the pre-soften grader and are now stale.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1129Z | openrouter-gemma4-26b-detailed (openrouter / google/gemma-4-26b-a4b-it) | 2026-06-06T12:31:04Z | 1.0 | done | current (post-cutoff) |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed (openrouter / google/gemma-4-26b-a4b-it) | 2026-06-06T10:13:41Z | 1.0 | done | current (post-cutoff) |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic (openrouter / deepseek-v4-pro) | 2026-05-31T17:04:18Z | 1.0 | done | current (post-cutoff) |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:00:42Z | 1.0 | done | current (post-cutoff) |
| run-20260528-2332Z | claude-code-opus-basic (claude-code / claude-opus-4-7) | 2026-05-29T00:25:25Z | 1.0 | done | current (post-cutoff) |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:15:00Z | 1.0 | done | current (post-cutoff) |
| run-20260528-1927Z | claude-code-opus-basic (claude-code / claude-opus-4-7) | 2026-05-28T21:49:09Z | 1.0 | done | current (post-cutoff) |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | null | cancelled | current; user-cancelled before completion, not task-related |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:40:59Z | 1.0 | done | stale (pre-soften, ~80 min before the cutoff commit) |

Seven completed current runs across three agent families (claude-code,
openrouter-gemma, openrouter-deepseek). All seven produced
`cairo_metro_hulls.geojson` matching the reference schema exactly: 20 Polygon
features, EPSG:4326 (verified directly: `crs=EPSG:4326`, columns
`['station_name_en', 'station_name_ar', 'geometry']`, geometry types
`{'Polygon'}`, Arabic script preserved — feature[0] `station_name_ar` =
"الشهداء" in the deepseek run, same in the others). All eight subchecks pass
on every run (en/ar populated 20/20, English Jaccard 1.0, Arabic match 20/20,
hull contains input 20/20, mean per-station IoU 1.0, `crs_is_canonical` and
`crs_in_meaningful_set` both pass — agents stayed in EPSG:4326). Output-CRS /
format consistency (Step 2c-CRS) holds: the reference output,
`expected_outputs[]`, and the README all declare GeoJSON + EPSG:4326; the
new `grade_crs_soft` does reproject the submission to canonical for downstream
subchecks, but the reference is in the same canonical CRS already, so no
one-sided reprojection papers over a contract mismatch.

#### Verdict
**calibrated**

Re-confirms the prior `calibrated` verdict under the new CRS-soft grader. Seven
current runs across three agent families (claude-opus-4-7, gemma-4-26b,
deepseek-v4-pro), all 1.0. This is the intended L1 difficulty — easy by
design, but not over-specified: the operation name ("convex hull") is allowed
for L1 per `instruction-stripping-guide.md` (the task IS the operation), the
output CRS is part of the output contract, and the bilingual-preservation
rule is a persona business constraint the agent cannot deduce from a bare
GeoJSON output schema. The "MultiPoint" hint was stripped in f40e39e9. No
gift remains to strip. Grader re-grades the reference 1.00 (8/8 subchecks).
Broken-set scores shift on the new denominator (5/6 → 7/8 = 0.875 for
`bbox_instead_of_hull`; 4/6 → 6/8 = 0.75 for `empty_arabic`; 0.0 unchanged
for `wrong_format`) — both still fall inside the documented
`expected_score_range` (`[0.78, 0.90]` and `[0.55, 0.75]`), so the CRS-soften
calibrated the broken-set arithmetic without breaking the grader's discrimination
between failure modes. `measured_score` values were refreshed (see §3).
pytest 41/41.

#### Specific findings
- Grader semantics drift on the broken sets is benign: `bbox_instead_of_hull` 0.833 → 0.875 and `empty_arabic` 0.667 → 0.75 because the two new CRS subchecks pass on broken outputs that kept EPSG:4326 (the broken-solution scripts only break the named failure mode, not CRS). Both new scores stay inside the documented `expected_score_range`. Refreshed `measured_score` in `metadata.yaml`; expected ranges left unchanged.
- The descriptions in `metadata.yaml > broken_solutions > {bbox_instead_of_hull, empty_arabic}` previously stated "5/6 ≈ 0.833" and "4/6 ≈ 0.667" — refreshed to "7/8 = 0.875" and "6/8 = 0.75" to match the new grader.
- `task.json.analyst_notes` was missing (the field landed across the sweep recently). Authored it now: persona-style description of what the task tests (per-row hull + bilingual carry-through), high-level approach steps, and a pitfalls list led by the hidden gotchas (global-hull collapse, `unary_union` dropping attributes, Arabic encoding round-trip).
- `task.json` does not yet carry an explicit `version` field. The two edits this pass are `analyst_notes` authoring and `metadata.yaml > broken_solutions > measured_score` refresh — neither requires a version bump (the prompt explicitly exempts both). The implicit `version: 1` continues to apply.
- `coverage.yaml` axes still validate against `coverage-vocabulary.yaml`; cross-axis checks remain consistent (L1 ⇒ bundled-local; railway OSM tag family, no Overture theme since the input is hand-crafted per the metadata rationale). Only `evaluator_run_at` refreshed.
- No HUMAN-REVIEW items.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions.bbox_instead_of_hull.measured_score` 0.833 → 0.875 and its description "5/6 ≈ 0.833" → "7/8 = 0.875". Reason: CRS-soften grader (05aabd64) added two subchecks, denominator went 6 → 8; broken-set kept EPSG:4326 so the two new subchecks pass and the score lifts.
- `metadata.yaml`: refreshed `broken_solutions.empty_arabic.measured_score` 0.667 → 0.75 and its description "4/6 ≈ 0.667" → "6/8 = 0.75". Same reason.
- `task.json`: authored `analyst_notes` (description + approach + pitfalls). Reason: field was missing; added per Step 4. No version bump required.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.00 (8/8 subchecks pass)
- grader on `reference/failures/broken_wrong_format/outputs`: 0.0 (matches expected [0.0, 0.0])
- grader on `reference/failures/broken_bbox_instead_of_hull/outputs`: 0.875 (in expected [0.78, 0.90])
- grader on `reference/failures/broken_empty_arabic/outputs`: 0.75 (in expected [0.55, 0.75])
- pytest (benchmark/eval): pass (41/41)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geometry-type-is-Polygon check migrated to new subcheck
  `geometry_types_polygon`.
- Row-count-within-±5% check migrated to new subcheck
  `row_count_within_tolerance`.
- Subcheck count: 8 → 10.

### Verification
- Reference solution re-graded: 1.0 (10/10 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the five prior evaluator-review blocks: per the inventory row
(geometric_ops, L1, Cairo, primary op Convex hull, MultiPoint -> Polygon,
GeoJSON in/out, EPSG:4326 in/out, OSM tag `railway=subway_entrance`) and
initial-authoring commit 391238ef, the task probes per-feature convex hull on
MultiPoint geometries plus bilingual attribute carry-through. The tested twist
is per-row vs. global hull and not dropping `station_name_en` /
`station_name_ar`. Bundled-local hand-crafted input (20 real Cairo Metro
stations along Lines 1 and 2, seeded synthetic 3-5 entrance offsets, 78
entrance points total), no projection, no fetch.

#### Change log
Three new commits touch the task directory since the prior evaluator block
(4dee1ffa, itself a docs-change writing only the audit artefacts):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 4dee1ffa | docs-change | Prior evaluator artefacts (AUTHORING_HISTORY block, coverage.yaml timestamp, status.json) plus the measured_score / analyst_notes refreshes documented there | Commit msg: re-evaluation, calibrated |
| 2026-06-06 | 363aed21 | grader-change | Dropped `Gate("structural_correctness", ...)`; geometry-type-is-Polygon and row-count-within-5% migrated to subchecks `geometry_types_polygon` / `row_count_within_tolerance`; subcheck count 8 -> 10; docstring rewritten | Commit msg: Gate 2 was inconsistent across the 36 graders (34 effectively hard, 2 soft); single hard `format_schema_valid` gate, salvageable checks become one-point subchecks |
| 2026-06-07 | c749e57b | grader-change | Added `weight=3.0` to the five data-content subchecks (`station_name_en_set_preserved`, `arabic_names_match`, `hull_contains_input_points`, `hull_iou_against_reference`, `row_count_within_tolerance`); schema/CRS checks stay weight 1; score is now weighted (denominator 20) | Commit msg: weight data-content subchecks 3x across all categories; schema/structural stay 1.0 |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38Z (commit c749e57b, class: grader-change). Moves from the prior 2026-05-28 cutoff because both the gate-2 drop (363aed21, 2026-06-06T20:11:02Z) and the 3x weighting change the score arithmetic. All runs graded before the weighting commit are stale.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-06-09T12:21:05Z | 1.0 | done | current (post-cutoff, version 1 = current contract at run time) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed (deepseek/deepseek-v4-flash) | 2026-06-08T10:54:14Z | 1.0 | done | current (post-cutoff) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T15:41:37Z | 1.0 | done | stale (post gate-2 drop but pre 3x-weighting cutoff) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:23:15Z | 1.0 | done | stale (pre gate-2 drop) |

The 7 runs from the 2026-06-06 block and the ~27 earlier runs are stale under
the new cutoff and are documented in the prior blocks. Both current runs
produced `cairo_metro_hulls.geojson` matching the reference schema exactly:
20 Polygon features, EPSG:4326, columns `station_name_en` /
`station_name_ar` / `geometry`, Arabic script preserved (feature[0]
`station_name_ar` = "الشهداء" in both). Re-graded both under the
current weighted grader: 1.0, no failed subchecks. Note both current runs
predate this pass's instruction rewrite (they saw the v1 prompt, which
contained strictly more information), so their 1.0 scores remain valid
upper-bound evidence for the v2 prompt but will be version-stale for the
next evaluator.

Output-CRS / format consistency (Step 2c-CRS) holds: reference output,
`expected_outputs[]`, and README all declare GeoJSON + EPSG:4326;
`grade_crs_soft` reprojects the submission to canonical only as the declared
accept-list policy (MEANINGFUL_EPSGS = {4326}), and the reference is already
canonical, so no one-sided reprojection papers over a contract mismatch.

#### Verdict
**insufficient-evidence**

Only two runs postdate the 3x-weighting cutoff and both come from one agent
family (deepseek-v4-flash, basic + gis_detailed prompt variants), so the
formal bar for `calibrated` (>= 2 runs, > 1 family) is not met. There is no
countervailing evidence of a problem: both current runs score 1.0 with clean
schema, the reference re-grades 1.0 (10 subchecks, weighted denominator 20),
and the broken sets re-grade 0.0 / 0.85 / 0.80, preserving the grader's
discrimination between failure modes. The long stale history (30+ runs over
five families, essentially all 1.0 except model-side no-output failures)
continues to suggest a correctly-easy L1 task. Expect `calibrated` once a
second family lands a post-cutoff, post-v2 run.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `cairo_metro_hulls.geojson`, GeoJSON | instruction | stated |
| columns `station_name_en` / `station_name_ar`, non-empty (gate + subchecks 1-2) | instruction | stated |
| English-name set Jaccard >= 0.95 vs reference | instruction ("every row must carry", names preserved) | inferable (preserve-verbatim implies set equality) |
| Arabic strings exact match (>= 99 %) | instruction ("preserved exactly as they appear in the input") | stated |
| hull contains input MultiPoint vertices | definition of convex hull | inferable |
| per-station IoU >= 0.95 vs reference | hull of a fixed point set is deterministic | inferable |
| geometry Polygon only | instruction ("one Polygon per station") | stated |
| row count within 5 % (20 rows) | instruction ("one Polygon per station") + input has 20 stations | stated/inferable |
| CRS canonical EPSG:4326 (`crs_is_canonical`, `crs_in_meaningful_set`) | GeoJSON output pins WGS84 per RFC 7946 | inferable (the v2 prompt deliberately drops the explicit EPSG mention) |

Factual claims verified: `cairo_metro_stations.geojson` exists in `inputs/`
(20 MultiPoint features, both name columns); output filename, column names,
and geometry type match the reference output schema. No missing or inaccurate
claims.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: per-row `convex_hull`, both
name columns carried verbatim, written as GeoJSON in EPSG:4326. The only
unrequested operation is a stable re-sort by `station_name_en`, which is a
verified no-op (the input is already sorted by that key; input and output
row orders are identical), kept as a determinism guard. Not flagged: it
cannot change output content.

#### Specific findings
- The two grader refactors (gate-2 drop, 3x weighting) shifted the broken-set arithmetic: `bbox_instead_of_hull` 0.875 -> 0.85 (17/20) and `empty_arabic` 0.75 -> 0.80 (16/20). `bbox` stays inside its authored `expected_score_range` [0.78, 0.90]; `empty_arabic` now lands ABOVE its authored range [0.55, 0.75]. Refreshed both `measured_score` values and descriptions; the range itself is the author's design assertion and is not on the unilateral-edit list.
<!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="low" -->
HR-001: `broken_empty_arabic` now scores 0.80, above its authored `expected_score_range` [0.55, 0.75]. This is a mechanical consequence of the repo-wide 3x data-content weighting (the failure loses weights 1 + 3 of 20 instead of 2 of 8). A human should either re-author the range (e.g. [0.70, 0.85]) to ratify the new weighting policy for this failure class, or decide that blanking a persona-critical bilingual column should cost more than 0.20 and adjust subcheck weights. No version bump needed for a range-only re-authoring.
- The instruction contained a trailing `EPSG:4326` although the output is GeoJSON (RFC 7946 pins WGS84); per the GeoJSON-CRS strip rule this is mechanically redundant and was removed as part of a house-style rewrite (see §3). The rewrite also removed two em-dashes, the breezy "Quick favour" opener, the duplicate attribute-preservation statement (kept the concrete schema-paragraph version), the duplicate geometry-type statement (kept "one Polygon per station"; `expected_outputs[].geometry_type` pins Polygon), and now references the input by its actual filename `cairo_metro_stations.geojson`. All factual constraints, the accessibility-report framing, and the deliberate omissions (input MultiPoint type, now also output CRS) are preserved. `version` bumped 1 -> 2.
- README had drifted from the post-gate-2 grader: failure modes 4/5/8 cited "Gate 2" / "Gate 1 CRS reject" detectors that no longer exist, broken-set scores were the pre-weighting 0.833/0.667, and the input path still said `data/`. Fixed (docs-change).
- `analyst_notes` refreshed to match the v2 prompt (CRS now deliberately implicit) and the current grader (row-count gate -> weighted subcheck).
- `coverage.yaml` axes re-validated against `coverage-vocabulary.yaml`; all slugs still valid and cross-axis consistent (L1 => bundled-local; railway OSM family; no Overture theme since input is hand-crafted). Only `evaluator_run_at` refreshed.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style rewrite of `instruction` (strip GeoJSON-redundant `EPSG:4326`, remove em-dashes and breezy opener, dedupe attribute/geometry constraints, use actual input filename); added `version: 2`; refreshed `analyst_notes`. Re-grade on reference: 1.0. Reason: GeoJSON-CRS strip rule + house-style rules are mechanical unilateral edits.
- `metadata.yaml`: refreshed `broken_solutions.bbox_instead_of_hull.measured_score` 0.875 -> 0.85 and `broken_solutions.empty_arabic.measured_score` 0.75 -> 0.8, with descriptions updated to the weighted 17/20 / 16/20 arithmetic and a NOTE pointing at HR-001. Reason: gate-2 drop + 3x weighting changed the denominator to 20.
- `README.md`: replaced stale Gate-2 / CRS-hard-fail detector references with the current subcheck names, refreshed broken-set scores, fixed `data/` -> `inputs/` path. Reason: docs drifted behind two grader refactors.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — grader-miscalibration-suspected (low) — `empty_arabic` broken-set score 0.80 exceeds its authored expected_score_range [0.55, 0.75] after the repo-wide 3x weighting; human to re-author the range or revisit weights.

#### Tests run
- grader on reference: 1.0 (10/10 subchecks, weighted denominator 20)
- grader on `reference/failures/broken_wrong_format/outputs`: 0.0 (in expected [0.0, 0.0])
- grader on `reference/failures/broken_bbox_instead_of_hull/outputs`: 0.85 (in expected [0.78, 0.90])
- grader on `reference/failures/broken_empty_arabic/outputs`: 0.80 (ABOVE expected [0.55, 0.75] — HR-001)
- grader on current-run outputs run-20260608-074701Z / run-20260609-084636Z: 1.0 / 1.0
- pytest (benchmark/eval): pass (41/41)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Summary
Per-task reasoned subcheck weights replace the blunt repo-wide 3x data-content
weighting (05b389b / c749e57). Weights now reflect error severity for THIS
task: the central skill is correct per-row convex-hull construction, so the
subchecks that detect a wrong hull carry the highest weight; bilingual-name
data checks are high but below the hull; structural co-detectors are medium;
presence-only and CRS checks (recoverable / cosmetic for an all-WGS84 task) are
lowest. Grading-only change; no task.json version bump.

### 1. Design history
Unchanged from the prior blocks: geometric_ops, L1, Cairo, primary op convex
hull (MultiPoint -> Polygon), GeoJSON in/out, EPSG:4326. The task probes
per-feature convex hull plus bilingual attribute carry-through; the tested
twist is per-row vs. global hull and not dropping `station_name_en` /
`station_name_ar`. No new commits touch the answer key or instruction since the
prior block; this pass edits subcheck weights only.

### 2. Weight changes (subcheck: old -> new)
| Subcheck | old | new | tier / rationale |
|---|---|---|---|
| `hull_iou_against_reference` | 3.0 | 5.0 | central hull skill — wrong hull shape (bbox/buffer) is THE failure this task probes |
| `hull_contains_input_points` | 3.0 | 4.0 | central hull skill — wrong-station pairing / no-op hull |
| `arabic_names_match` | 3.0 | 3.0 | bilingual data — persona-required, but not the central hull skill (unchanged) |
| `station_name_en_set_preserved` | 3.0 | 3.0 | bilingual data (unchanged) |
| `row_count_within_tolerance` | 3.0 | 3.0 | per-row vs global twist — a collapse co-fails the per-station checks (unchanged) |
| `geometry_types_polygon` | 1.0 | 2.0 | structural — non-Polygon output signals no-op (co-detected by IoU) |
| `station_name_en_populated` | 1.0 | 1.0 | presence-only (content caught by the `*_set`/`*_match` checks) |
| `station_name_ar_populated` | 1.0 | 1.0 | presence-only |
| `crs_is_canonical` | 1.0 | 0.5 | cosmetic — wrong CRS is recoverable (reprojected); all-WGS84 task |
| `crs_in_meaningful_set` | 1.0 | 0.5 | cosmetic |

Denominator: 20 -> 23 (5+4+3+3+3+2+1+1+0.5+0.5).

### 3. Broken-score before -> after
| Broken | before | after | severity note |
|---|---|---|---|
| `wrong_format` | 0.0 | 0.0 | Gate-1 reject (non-GeoJSON) — most severe, unchanged |
| `bbox_instead_of_hull` | 0.85 | 0.783 | central hull-skill failure (wrong hull shape) — now the lowest non-gate broken, as it should be |
| `empty_arabic` | 0.80 | 0.826 | geometry perfect, Arabic name blanked — a data slip, less severe than a wrong hull |

Ordering is now sensible and monotone by severity: 0.0 (gate) < 0.783 (wrong
hull, central skill) < 0.826 (blanked name, perfect geometry) < 1.0 (reference).
The two non-zero brokens fail disjoint subcheck groups (hull group vs. name
group); weighting the hull group highest deliberately places the hull-skill
failure below the data slip, matching "central skill highest." A hypothetical
wrong-CRS-only submission would lose only 1/23 -> 0.957 (cosmetic), and a
global-hull collapse or no-op would lose the row-count/IoU/contains group and
drop far lower — both consistent with the severity ordering.

### 4. Prior-run re-grade summary
All prior version-current runs are perfect submissions with zero failed
subchecks, so reweighting cannot move them. The two runs the prior block flagged
as `current` (run-20260608-074701Z, run-20260609-084636Z) re-grade 1.0 -> 1.0;
spot-checked recent runs (run-20260607-112430Z, run-20260606-1733Z,
run-20260606-1129Z, run-20260606-0953Z) likewise 1.0 -> 1.0. No significant
shifts.

### 5. Reasoning
The 05b389b / c749e57 change applied weight=3.0 to every "data-content" subcheck
uniformly, which on this task lumped the central hull checks together with the
bilingual-name checks and the row-count check, and left the no-op-detecting
geometry-type check at weight 1. That flattened severity: a wrong hull (the
headline skill failing) and a blanked attribute column scored almost the same.
The per-task weights restore a severity gradient anchored on the task's actual
probe — correct per-row hull construction. `hull_iou` (wrong shape) and
`hull_contains_input_points` (wrong-station pairing / no-op) are the
highest-weighted because they detect the central skill failing. Name checks stay
high (the persona requires both names) but below the hull, so a perfect-geometry
submission that blanks a name scores above a submission that botched the hull.
The CRS pair is down-weighted to 0.5 each because `grade_crs_soft` already
reprojects a wrong-CRS submission to canonical before the geometric subchecks
run, so a CRS slip is recoverable and cosmetic on this all-WGS84 task.

NOTE (no change made): the `*_populated` checks are presence-only and partly
redundant with the `*_set_preserved` / `*_match` content checks; kept at weight 1
rather than dropped so a schema-shaped-but-empty column still registers. Not a
miscalibration, just flagged for transparency.

### 6. Changes applied this run
#### Unilateral edits
- `grade.py`: subcheck `weight=` values only (table in §2). No check logic,
  thresholds, or gates changed.
- `metadata.yaml`: refreshed `broken_solutions.{bbox_instead_of_hull,empty_arabic}`
  `measured_score` + `expected_score_range` to the new weighted values, and the
  weight-arithmetic prose in their descriptions.
- `README.md`: refreshed the two stale broken-set score fractions (0.85 -> 0.783,
  0.80 -> 0.826).
- `audit/status.json`: removed HR-001; recorded edits; status -> completed.

#### Human-review items
- HR-001 retired: the `empty_arabic` out-of-range concern is resolved by the
  per-task weighting + re-authored range. No open HR items.

#### Tests run
- grader on reference: 1.0 (10/10 subchecks, weighted denominator 23)
- grader on `reference/failures/broken_wrong_format/outputs`: 0.0 (in expected [0.0, 0.0])
- grader on `reference/failures/broken_bbox_instead_of_hull/outputs`: 0.783 (in expected [0.72, 0.84])
- grader on `reference/failures/broken_empty_arabic/outputs`: 0.826 (in expected [0.76, 0.88])
- grader on current-run outputs run-20260608-074701Z / run-20260609-084636Z: 1.0 / 1.0
- pytest: not run (orchestrator runs the suite)
