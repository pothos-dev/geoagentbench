# Implementation notes — crs-l2-svalbard-polar-areas

## Status
completed

## Summary
L2 CRS-reprojection task built on a 169-feature slice of named Svalbard glacier polygons from Overture release 2026-04-15.0. Reference reprojects to EPSG:3995, ranks the top 20 by projected area, and emits a 6-column CSV. Three broken solutions cover gate-1 failure, partial reprojection failure, and a top-N membership failure with distinct measured scores.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - no_reprojection: 0.375 (expected range [0.25, 0.5])
  - offset_topN: 0.75 (expected range [0.6, 0.85])
- Second-run output match: bit-identical
- Library tests after task: pass

## Failure-mode coverage
- Skipped reprojection (area in degrees²): broken_no_reprojection
- Wrong projection (Web Mercator at 78°N): principled-reasoning (covered by `bbox_within_polar_svalbard_envelope` + `per_glacier_area_matches` subchecks)
- Off-by-N ranking / wrong top-N membership: broken_offset_topN
- Wrong output format: broken_wrong_format
- Unsorted output: principled-reasoning (covered by `sorted_by_area_desc` subcheck)
- Bbox computed in WGS84: principled-reasoning (covered by `bbox_within_polar_svalbard_envelope` + `per_glacier_bbox_matches` subchecks)
- Swapped bbox min/max columns: principled-reasoning (covered by `bbox_min_less_than_max` subcheck)

## Open issues
- [severity: low] — Overture's `id` and `name` are stable across releases for the named subset, but the *unnamed* glacier polygons (which we drop at authoring time) are more volatile. If a future Overture release introduces a name for a previously-unnamed glacier larger than the current top-20 cutoff (~38 km²), the bundled slice would shift. The bundled GPKG is committed, so this only affects re-running `data/_prepare_input.py`, not grading.

## Suggested prompt changes
*(empty)*

## Inventory change proposals
*(empty)*

## Library extensions
*(empty)*

## Runtime
~15 minutes (most spent on the initial Overture probe).

---

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent

A bundled L2 CRS-reprojection task that exercises an agent's awareness that
high-latitude area calculations require a polar projection, not a cylindrical
one. 169 named Svalbard glacier polygons (sliced from Overture release
2026-04-15.0) are provided in WGS84; the reference reprojects to EPSG:3995
(Arctic Polar Stereographic), computes per-feature area and bbox in projected
metres, and emits the top 20 ranked by area as a 6-column CSV. The inventory
row pinned EPSG:3995 specifically, and the initial task.json instruction
named EPSG:3995 explicitly in the persona text.

#### Change log

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | f60034b | initial-authoring | Initial task: task.json, grade.py, metadata.yaml, reference solution + outputs, broken_no_reprojection / broken_offset_topN / broken_wrong_format, README. Instruction names EPSG:3995 and describes Svalbard at 78°N. | Commit msg: "task: crs-l2-svalbard-polar-areas [completed]" |
| 2026-05-08 | 001e459 | docs-change | Split benchmark tree into authoring/ and eval/ subtrees (path-only). | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Move benchmark/eval/tasks/ -> benchmark/tasks/ (path-only). | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Add image-prompt.md (assets only). | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Add image.webp via FLUX schnell (assets only). | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerate image.webp via fal.ai FLUX schnell (assets only). | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerate image.webp via nano-banana-2 (assets only). | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | d5c283d | prompt-change | Strip "named glacier polygons over Svalbard, currently sitting in WGS84. At 78°N" from instruction; keep EPSG:3995 mention. | Commit msg: "Strip deducible information from CRS task instructions" (removes input CRS / geometry-type / column hints; keeps target CRS) |
| 2026-05-15 | 7ac5fbe | prompt-change | Strip "anything cylindrical exaggerates area at these latitudes" from instruction; keep EPSG:3995 mention. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-17 | b4583b4 | prompt-change | Replace explicit "EPSG:3995" target with "Pick an appropriate polar projection". Also drops the redundant "in same projected metres as the area" framing of bboxes — wait, that text is kept. The change is the EPSG removal. | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg only (IMPLEMENTATION_NOTES->audit/AUTHORING_HISTORY, data/->inputs/, reference/->reference/solution/, tests/->reference/failures/, image moved to assets/). grade.py reference path adjusted; task.json input URL adjusted. No semantic change. | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:48:37Z (commit b4583b4, class: prompt-change). The 2026-05-26 reorg (commit 29a9ae3) only renamed paths and did not change instruction, grader semantics, inputs, reference outputs, or failures; runs post-2026-05-17 remain valid.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:31:03Z | 0.5 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:52:02Z | 0.75 | done | current |

Stale runs: 25 earlier runs (run-20260512* through run-20260517-0614Z) pre-cutoff; not used as evidence. (run-20260517-1254Z also pre-cutoff: 12:54Z, ~5 minutes after the cutoff commit but with task.json that had already been re-deployed; treated as borderline and excluded.)

#### Verdict

**prompt-grader-inconsistent**

The instruction was stripped on 2026-05-17 (b4583b4) to "Pick an appropriate polar projection" — no longer naming EPSG:3995. But the grader's `bbox_within_polar_svalbard_envelope` check pins coordinates to the EPSG:3995 envelope (`x in [100000, 800000]`, `y in [-1700000, -700000]`), and `per_glacier_bbox_matches` compares bbox values numerically to the EPSG:3995 reference. The agent does not see `expected_outputs[].crs` (the runner only forwards `task.instruction`; see `benchmark/eval/eval/core/runner.py:251`), so the agent has no path to learn EPSG:3995 is required.

Both post-cutoff runs picked a legitimate polar/equal-area projection (Gemma: EPSG:3413 NSIDC North Polar Stereographic; DeepSeek: custom LAEA centered at lat 78°N lon 18°E) and both got correct top-20 names (Jaccard 1.0). Gemma's per-glacier areas even matched within 1% (EPSG:3413 and EPSG:3995 are very close in area at Svalbard latitudes, both being polar stereographic with origin at the Pole). Both failed `bbox_within_polar_svalbard_envelope` because their projection origins differ from EPSG:3995's, giving bbox coordinates outside the hardcoded EPSG:3995 envelope.

This is borderline as a unilateral fix: per `instruction-stripping-guide.md` §3 ("Named projections stay when they ARE the answer. In a CRS-reprojection task where the whole point is 'reproject to Lambert-93', the target CRS is the goal, not the method"), the EPSG:3995 hint should not have been stripped — it is the answer, not the method. The metadata.yaml author-block already records that "the inventory pinned 3995 specifically." But commit b4583b4 explicitly removed it as part of a 5-task sweep titled "Remove CRS/operation nudges from 5 CRS task prompts", so the human ran a deliberate experiment to make agents pick the polar CRS independently. Restoring "EPSG:3995" would undo that experimental decision; flagging instead.

#### Specific findings

- The grader's bbox envelope check is hardcoded to EPSG:3995 (`grade.py:44-45`) while the instruction allows the agent to pick any polar projection. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decide between: (a) restore explicit "EPSG:3995" in the instruction per the stripping-guide rule "named projections stay when they ARE the answer"; (b) broaden the grader to accept any polar-stereographic-origin-at-pole CRS by reprojecting submitted bboxes to EPSG:3995 before envelope-checking; (c) accept the current behaviour as "the agent must guess EPSG:3995 from the output filename `_top20.csv` and the bbox column names `bbox_*_polar`" — which Gemma and DeepSeek demonstrably did not do. Option (a) matches the documented design intent in `metadata.yaml` ("the inventory pinned 3995 specifically").
- The redundant output-schema sentence at the end of the instruction ("File: svalbard_glaciers_top20.csv.") does not restate the CRS as `instruction-stripping-guide.md` §6 ("Check the redundant output-schema sentence") implies it should. Tied to HR-001; resolving (a) above would naturally fix this.
- The instruction phrase "true geographic area, not the distorted values you'd get from raw lat/lon coordinates" is the persona's framing of the area-honesty requirement; it does not name a technique. Keep as-is.

### 3. Changes applied this run

#### Unilateral edits

None. The single flagged issue (HR-001) is borderline by the prompt's own definition (Step 4: "Make any change classified as borderline in Step 2 — flag `prompt-vs-grader-judgment`").

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — prompt-vs-grader-judgment — Decide whether instruction must name EPSG:3995 (restoring the pre-b4583b4 wording) or whether the grader should accept any polar-stereographic CRS centered at the North Pole.

#### Tests run

- grader on reference: 1.00 (8/8 subchecks pass, both gates pass)
- pytest: pass (35 passed)

---

## Evaluator review 2026-05-26b  (evaluator-commit <pending>)

Re-evaluation triggered by two fresh runs (opus-4-7 + gemma-4-26b) added after the
prior review. No design-affecting commit has landed since the prior block, so the
Step-1 design history is unchanged; this block focuses on the strengthened Step-2
evidence and re-confirms the open flag.

### 1. Design history

No new commits touch the task directory since the prior evaluator review
(`git log` head for the dir is the prior evaluator commit `4bbc2c7`, dated
2026-05-26T12:38Z, whose only payload was the three evaluator artefacts —
class `docs-change`, non-design-affecting). The change log in the prior block
(initial-authoring `f60034b` 2026-05-08 → prompt-strip sweep `b4583b4`
2026-05-17 → folder reorg `29a9ae3` 2026-05-26) remains the authoritative
journal. The design-affecting cutoff is therefore unchanged.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:48:37Z (commit b4583b4, class: prompt-change —
  replaced explicit "EPSG:3995" target with "Pick an appropriate polar projection").
  The 2026-05-26 reorg (29a9ae3) and the prior evaluator commit (4bbc2c7) are both
  path/docs-only and do not invalidate runs.

#### Runs considered

| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (opus-4-6) | claude-code | 2026-05-17T12:56:51Z | 0.5 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | openrouter | 2026-05-17T14:31:03Z | 0.5 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T07:52:02Z | 0.75 | done | current |
| run-20260526-1753Z | claude-code-opus-basic (opus-4-7) | claude-code | 2026-05-26T17:53:31Z | 0.75 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T19:22:26Z | 0.75 | done | current |

Five current runs across two agent families (claude-code, openrouter). The prior
block excluded run-20260517-1254Z (opus-4-6) as "borderline" because it started
~5 min after the cutoff commit; on re-inspection its session received the
post-strip instruction (no EPSG:3995 named — the agent picked UTM 33N), so it is
a valid current run and is now included. Stale runs: 24 earlier runs
(run-20260512* through run-20260517-0614Z) pre-cutoff; not used as evidence.

#### Per-run output inspection

All five produced a readable 20-row CSV with the six required columns, sorted
descending, passing both gates and the `row_count_is_20`, `top20_name_set_matches`
(Jaccard 1.0000), `sorted_by_area_desc`, and `bbox_min_less_than_max` subchecks.
The chosen projection and the resulting subcheck pattern:

| Run | CRS picked | area subchecks | bbox subchecks | score |
|---|---|---|---|---|
| 1254Z (opus-4-6) | EPSG:32633 (UTM 33N) | FAIL (cylindrical UTM distorts area at 78°N) | FAIL | 0.5 |
| 1424Z (deepseek) | custom LAEA `+lat_0=78 +lon_0=18` | FAIL (LAEA areas differ ~3.9% from stereographic ref) | FAIL | 0.5 |
| 0748Z (gemma) | EPSG:3413 (NSIDC N polar stereo) | PASS (rate 1.0; total diff 0.60%) | FAIL | 0.75 |
| 1753Z (opus-4-7) | EPSG:3413 | PASS (rate 1.0; total diff 0.60%) | FAIL | 0.75 |
| 1922Z (gemma) | EPSG:3413 | PASS (rate 1.0; total diff 0.60%) | FAIL | 0.75 |

The three EPSG:3413 runs produced bit-identical numbers (sub total 9344.09 km²,
x∈[955924,1173314], y∈[-675330,-211860]). EPSG:3413 is a textbook, standard
Arctic polar-stereographic CRS in metres; its per-glacier areas match the
EPSG:3995 reference within 1% because both are polar stereographic with origin
at the North Pole, so the area-honesty goal of the task is fully met. They lose
exactly two subchecks — `bbox_within_polar_svalbard_envelope` and
`per_glacier_bbox_matches` — purely because EPSG:3413's central meridian (-45°)
and standard parallel differ from EPSG:3995's, shifting the bbox coordinates
out of the hardcoded EPSG:3995 envelope and away from the EPSG:3995 reference
bbox values. No path exists for the agent to learn EPSG:3995 specifically: the
runner forwards only `task.instruction` (`benchmark/eval/eval/core/runner.py:251`),
not `expected_outputs[].crs`, and the instruction says only "Pick an appropriate
polar projection".

#### Verdict

**prompt-grader-inconsistent**

Re-confirmed and now backed by airtight evidence rather than the prior block's
two-run, one-borderline basis. Across five current runs from two agent families,
**no run reached 1.0**; the ceiling is a hard 0.75 for any solution that picks a
correct polar projection other than EPSG:3995. The instruction commits the agent
only to "an appropriate polar projection" (and the area-honesty goal), but two of
the eight subchecks — `bbox_within_polar_svalbard_envelope` (grade.py:44-45,
199-218) and `per_glacier_bbox_matches` (grade.py:220-256) — silently require the
single CRS EPSG:3995, which the agent has no way to know. Three runs that picked
the standard Arctic CRS EPSG:3413 produced areas correct to within 0.6% yet were
capped at 0.75. The instruction-stripping-guide is explicit that this hint should
not have been stripped: §3 line 42 "Output CRS always stays — it's part of the
output contract" and line 43 "Named projections stay when they ARE the answer …
the target CRS is the goal, not the method." The `expected_outputs[].crs` is
EPSG:3995 and `metadata.yaml` records "the inventory pinned 3995 specifically", so
the design contract does want EPSG:3995 — but commit b4583b4 stripped it from the
only channel the agent can read.

The remaining ambiguity is *which* of two defensible fixes the author wants, which
keeps this a `prompt-vs-grader-judgment` flag rather than a unilateral edit:

- (a) Restore explicit "EPSG:3995" to `task.json` instruction (revert the b4583b4
  strip for this one clause). Matches the stripping-guide rules above and the
  recorded design intent. But b4583b4 was a deliberate human 5-task sweep
  ("Remove CRS/operation nudges from 5 CRS task prompts"); restoring reverses that
  experiment, which is a design-rationale call the evaluator may not make alone.
- (b) Broaden `grade.py` to accept any North-Pole-origin polar-stereographic CRS,
  e.g. reproject the submitted bbox corners into EPSG:3995 before the envelope and
  per-glacier comparison (or replace the absolute envelope with a check that the
  submitted bbox, when reprojected to WGS84, lands over the Svalbard lon/lat box).
  This preserves the b4583b4 experiment but redesigns two subchecks and changes
  what the task discriminates (EPSG:3413 vs EPSG:32633 would both pass bbox).

Either is a substantive change that reverses a deliberate decision or restructures
grader semantics; per the evaluator prompt Step 4 ("Make any change classified as
borderline in Step 2 — flag"), I flag rather than apply. Severity raised
considerations below; held at `med` (per-task scoring quirk, not a cross-task
framework bug — does not warrant stopping the sweep per the orchestrator-handoff
rule reserving `high` for compounding/framework-wide problems).

Not a task-too-easy or model-side concern: scores span 0.5–0.75 sensibly with
capability (UTM/LAEA pickers score 0.5; correct-polar pickers 0.75), and no run
failed for timeout/context/oversized-query reasons.

#### Specific findings

- Two subchecks pin the answer to EPSG:3995 while the instruction allows any
  appropriate polar projection, capping all five current runs at ≤0.75 with zero
  1.0 scores; EPSG:3413 solutions are area-correct (within 0.6%) yet fail both
  bbox subchecks. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decide between (a) restoring explicit "EPSG:3995" in `task.json` instruction (per instruction-stripping-guide §3 lines 42-43: output CRS / named-projection-as-answer must stay) or (b) broadening `grade.py` bbox subchecks to accept any North-Pole-origin polar-stereographic CRS by reprojecting submitted bboxes into EPSG:3995 before comparison. Option (a) matches the recorded design intent ("the inventory pinned 3995 specifically") but reverses the deliberate b4583b4 strip; option (b) preserves the strip but changes what the task discriminates.
- The redundant output-schema tail of the instruction ("File: svalbard_glaciers_top20.csv.") does not restate the output CRS, so even a careful agent cannot recover EPSG:3995 from the contract. Tied to HR-001; resolving (a) fixes it.
- The instruction phrase "true geographic area, not the distorted values you'd get from raw lat/lon coordinates" frames the area-honesty requirement without naming a technique — keep as-is (correctly survived stripping).
- Provenance note (low, no flag): `metadata.yaml`/`README` say the slice is from Overture (theme=base, type=land, subtype=glacier) while `inventory.md` labels it OSM `natural=glacier`. Data is bundled either way, so `data_sources: [bundled-local]` is correct; coverage keeps `osm_tag_families: [natural]` to match the inventory's coverage assignment. Cosmetic only.

### 3. Changes applied this run

#### Unilateral edits

None. The single flagged issue (HR-001) is borderline by the prompt's own
definition: choosing between fix (a) and fix (b) reverses either a deliberate human
experiment or the grader's discriminating power, which Step 4 reserves for human
review.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — prompt-vs-grader-judgment — Resolve the EPSG:3995-pinned bbox subchecks
  vs the "pick an appropriate polar projection" instruction. Now corroborated by
  five current runs (two families) all capped ≤0.75; three correct-polar (EPSG:3413)
  runs cap at exactly 0.75.

#### Tests run

- grader on reference: 1.00 (8/8 subchecks pass, both gates pass)
- pytest: pass (35 passed)

---

## Evaluator review 2026-05-27  (evaluator-commit <pending>)

Re-evaluation pass. No design-affecting commit and no new run has landed since the
prior block (2026-05-26b), so the Step-1 journal and the Step-2 evidence base are
unchanged. This block re-confirms the standing flag and refreshes the artefacts.

### 1. Design history

No new commits touch the task directory since the prior evaluator review. The only
new commit on the directory is the prior evaluator's own commit `a8b25d6`
(2026-05-26T20:07:10Z), whose payload is exactly the three evaluator artefacts
(`audit/AUTHORING_HISTORY.md` +152 lines, `audit/status.json`, `coverage.yaml`) —
class `docs-change`, non-design-affecting (`git show --stat a8b25d6`). The change
log in the first evaluator block (initial-authoring `f60034b` 2026-05-08 →
prompt-strip sweep `b4583b4` 2026-05-17 → folder reorg `29a9ae3` 2026-05-26 → two
evaluator artefact commits `4bbc2c7`, `a8b25d6` 2026-05-26) remains the
authoritative journal. The design-affecting cutoff is unchanged.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:48:37Z (commit b4583b4, class: prompt-change —
  replaced explicit "EPSG:3995" target with "Pick an appropriate polar projection";
  verified the diff this run: `git show b4583b4 -- .../task.json`). The 2026-05-26
  reorg (29a9ae3) and the two evaluator artefact commits (4bbc2c7, a8b25d6) are all
  path/docs-only and do not invalidate runs.

#### Runs considered

Unchanged from the prior block — same five current runs, no new run directory has
appeared (latest is run-20260526-1922Z; total 29 dirs, 24 stale pre-cutoff). Scores
re-extracted from each `run.json > tasks["crs-l2-svalbard-polar-areas"]` this run.

| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (opus-4-6) | claude-code | 2026-05-17T12:56:51Z | 0.5 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | openrouter | 2026-05-17T14:31:03Z | 0.5 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T07:52:02Z | 0.75 | done | current |
| run-20260526-1753Z | claude-code-opus-basic (opus-4-7) | claude-code | 2026-05-26T17:53:31Z | 0.75 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-26T19:22:26Z | 0.75 | done | current |

Five current runs across two agent families; 24 stale runs (run-20260512* through
run-20260517-0614Z) pre-cutoff, not used as evidence.

#### Per-run output inspection

Re-verified the opus-4-7 run's score breakdown directly this run
(`runs/run-20260526-1753Z/.../score.json`): the EPSG:3413 (NSIDC North Polar
Stereographic, central meridian -45°) solution passes `row_count_is_20`,
`top20_name_set_matches` (Jaccard 1.0000), `per_glacier_area_matches` (rate 1.0000),
`total_top20_area_within_1_percent` (rel diff 0.5976%), `sorted_by_area_desc`, and
`bbox_min_less_than_max`, but fails exactly the two EPSG:3995-pinned bbox subchecks:
`bbox_within_polar_svalbard_envelope` (x∈[955924,1173314] vs expected [100000,800000])
and `per_glacier_bbox_matches` (all four match rates 0.000). Net 0.75. This is the
hard ceiling for any correct-polar solution that is not EPSG:3995; the area-honesty
goal of the task is fully met, only the absolute bbox frame differs.

#### Output-CRS / format consistency (Step 2c-CRS)

Consistent: `reference/solution/outputs/` is EPSG:3995, `expected_outputs[].crs` is
EPSG:3995, and the README states EPSG:3995. The grader compares CSV numeric values
directly with **no one-sided reprojection** (both reference and submission are read
as already-projected metres). The inconsistency is solely that the instruction does
not name EPSG:3995 — captured by HR-001, not a grader-reprojection bug.

#### Verdict

**prompt-grader-inconsistent**

Re-confirmed, unchanged. Across five current runs from two agent families no run
reaches 1.0; the ceiling is a hard 0.75 for any correct polar projection other than
EPSG:3995. Two of eight subchecks — `bbox_within_polar_svalbard_envelope`
(grade.py:44-45, 199-218) and `per_glacier_bbox_matches` (grade.py:220-256) —
silently require the single CRS EPSG:3995, which the agent cannot learn: the runner
forwards only `task.instruction` (`benchmark/eval/eval/core/runner.py:251`), and the
instruction says only "Pick an appropriate polar projection". The fix remains a
two-way judgment call ((a) restore "EPSG:3995" in the instruction per the
instruction-stripping-guide "output CRS / named-projection-as-answer stays" rule,
reversing the deliberate b4583b4 strip, vs (b) broaden the grader to accept any
North-Pole-origin polar-stereographic CRS), so it stays a `prompt-vs-grader-judgment`
flag rather than a unilateral edit (Step 4: borderline → flag). Held at `med`: a
per-task scoring quirk, not a cross-task framework bug.

Not too-easy (scores span 0.5–0.75 with capability), not too-strict in the
"correct output scored ~0" sense (the capped runs are genuinely missing the
EPSG:3995 bbox frame the contract wants), and no model-side failures among the
current runs.

#### Specific findings

- Two subchecks pin the answer to EPSG:3995 while the instruction allows any
  appropriate polar projection, capping all five current runs at ≤0.75 with zero
  1.0 scores; three EPSG:3413 runs are area-correct (within 0.6%) yet fail both
  bbox subchecks. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decide between (a) restoring explicit "EPSG:3995" in `task.json` instruction (per instruction-stripping-guide §3: output CRS / named-projection-as-answer stays; matches recorded design intent "the inventory pinned 3995 specifically" but reverses the deliberate b4583b4 strip) or (b) broadening `grade.py` bbox subchecks to accept any North-Pole-origin polar-stereographic CRS by reprojecting submitted bboxes into EPSG:3995 before comparison (preserves the strip but changes what the task discriminates).
- The redundant output-schema tail of the instruction ("File: svalbard_glaciers_top20.csv.") does not restate the output CRS, so even a careful agent cannot recover EPSG:3995 from the contract. Tied to HR-001; resolving (a) fixes it.
- Provenance note (low, no flag): `metadata.yaml`/`README` Story say the slice is OSM-derived while the README Input section and `metadata.yaml` notes say Overture (theme=base/type=land/subtype=glacier); `inventory.md` labels it OSM `natural=glacier`. Data is bundled either way, so `data_sources: [bundled-local]` is correct and `osm_tag_families: [natural]` matches the inventory coverage assignment. Cosmetic provenance wording only; carried unchanged.

### 3. Changes applied this run

#### Unilateral edits

None. The single flagged issue (HR-001) is borderline by the prompt's own definition;
choosing fix (a) or (b) reverses either a deliberate human experiment or the grader's
discriminating power, which Step 4 reserves for human review.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — prompt-vs-grader-judgment — Resolve the EPSG:3995-pinned bbox subchecks
  vs the "pick an appropriate polar projection" instruction. Corroborated by five
  current runs (two families) all capped ≤0.75; three correct-polar (EPSG:3413) runs
  cap at exactly 0.75.

#### Tests run

- grader on reference: 1.00 (8/8 subchecks pass, both gates pass)
- pytest: pass (35 passed)

---

## Review pass — 2026-05-28 (HR-001 resolution: output-CRS schema column + tiered accept-list)

HR-001 had been a standing flag across three evaluator passes: the instruction left CRS choice open ("Pick an appropriate polar projection") but the grader was hardcoded to the EPSG:3995 coordinate frame via `bbox_within_polar_svalbard_envelope` and `per_glacier_bbox_matches`. Five current runs scored ≤0.75 with zero 1.0s; three EPSG:3413 picks were per-glacier-area-correct but capped at 0.75.

Operator decision (after design discussion): close the design hole by making the agent's CRS choice machine-readable. Add a required `crs_epsg` integer column to the CSV schema; the grader reads it, validates it's in a North-Pole-origin polar-projection accept-list, reprojects the source gpkg into the declared CRS at grading time, and grades in the agent's frame. The fiji/lagos/paris `official_crs_used` subcheck pattern is replaced here by `equal_area_crs_used` because (a) Svalbard has no single canonical CRS (Norway's actual official is UTM 33N, which the instruction's "polar" wording excludes) and (b) the instruction asks for "true geographic area", which is exact only under equal-area projections.

### Changes applied

- **`task.json`**:
  - Instruction: "Pick an appropriate polar projection" → "Pick **the most appropriate coordinate system for measuring area at these latitudes**" — a nudge toward equal-area without naming the technique.
  - Output schema: added `crs_epsg` column (integer EPSG of the CRS used).
  - `expected_outputs[].crs`: `EPSG:3995` → `EPSG:3575` (the new canonical equal-area pick).
  - `tags.crs`: `[4326, 3995]` → `[4326, 3575]`.
  - `version`: `1` → `2` (per the 622342b versioning policy — grade.py change requires a bump).
- **`grade.py`** (full refactor):
  - `ACCEPTED_POLAR_EPSGS = {3413, 3573, 3574, 3575, 3576, 3995, 6931}` — WGS-84-datum North-Pole-origin projected CRSes (5 LAEA + 2 Polar Stereographic).
  - `EQUAL_AREA_EPSGS = {3573, 3574, 3575, 3576, 6931}` — LAEA subset.
  - Gate 1 reads `sub["crs_epsg"]`, validates it's a single integer in the accept-list.
  - Per-glacier reference areas and bboxes recomputed from `inputs/svalbard_glaciers_wgs84.gpkg` at grading time by reprojecting to the declared CRS — apples-to-apples comparison in the agent's frame.
  - New subcheck `equal_area_crs_used` rewards LAEA picks.
  - Dropped subcheck `bbox_within_polar_svalbard_envelope` (made redundant by the per-glacier match in the declared frame).
  - 8 subchecks total (was 8; one swapped, one added, two removed-but-folded).
- **`reference/solution/generate.py`**: target CRS `3995` → `3575`; emits `crs_epsg=3575` column. Also fixed a pre-existing path bug — `TASK_DIR = HERE.parent.parent.parent` was one level too high after the 29a9ae3 layout reorg; corrected to `.parent.parent`.
- **`reference/solution/outputs/svalbard_glaciers_top20.csv`**: regenerated in EPSG:3575 with the new column.
- **`reference/failures/_make_brokens.py`**: same path-bug fix. Reworked broken set:
  - `broken_wrong_format` (unchanged in spirit): GeoJSON under .csv name → 0.0.
  - `broken_no_reprojection` (refactored): honestly declares `crs_epsg=4326`, areas in degrees². Gate 1 rejects 4326 from the accept-list with a clear reason → 0.0.
  - `broken_conformal_pick` (NEW): EPSG:3995 with correct per-glacier work. Accepted at Gate 1, passes 7 subchecks, fails only `equal_area_crs_used` → 7/8 = 0.875.
  - `broken_offset_topN` (refactored): EPSG:3575, correct per-row work, but ranks 6–25. Fails `top20_name_set_matches` (Jaccard 0.60) and `total_top20_area_within_1_percent` (~87% sum shortfall) → 6/8 = 0.75.
- **`metadata.yaml`**: rationale rewritten under the accept-list. Broken `measured_score` refreshed.
- **`README.md`**: comprehensive rewrite — story updated; new "Accepted projections" table; failure modes 1–8 under the new schema; weak-agent failure mode updated to the conformal-vs-LAEA discrimination.
- **`audit/status.json`**: verdict `prompt-grader-inconsistent` → `calibrated`; HR-001 cleared.

### Verification

- Reference: 1.0 (8/8) — passes both gates and all eight subchecks including `equal_area_crs_used`.
- Brokens (current grader):
  - `broken_wrong_format`: 0.0 (Gate 1, CSV-unreadable).
  - `broken_no_reprojection`: 0.0 (Gate 1, "declared crs_epsg=EPSG:4326 is not a North-Pole-origin projected CRS; accepted set is [3413, 3573, 3574, 3575, 3576, 3995, 6931]").
  - `broken_conformal_pick`: 0.875 (7/8 — fails only `equal_area_crs_used`).
  - `broken_offset_topN`: 0.75 (6/8 — fails `top20_name_set_matches` and `total_top20_area_within_1_percent`).
- Score spread now 0/0/0.75/0.875/1.0 — discriminates across all the documented failure modes plus the new equal-area-vs-conformal axis.
- pytest: pass (41/41 on `tests/`).

### Doctrine note

This task is the first CRS-output task where adding a self-describing CRS column to the output schema was the right design fix. fiji-antimeridian's output is GeoJSON with CRS metadata in-file, so the `check_and_normalize_crs` helper could read it; spa-l3-paris and spa-l2-lagos similarly have GeoParquet outputs. Svalbard's CSV output had no way for the agent to declare their CRS, so the grader was reduced to inferring from coordinate ranges — which was fragile and capped legitimately-correct picks. The `crs_epsg` column closes that hole and would be a portable pattern for any future CSV-output CRS-target task.

The instruction nudge "the most appropriate coordinate system for measuring area" is borderline under the strip-guide ("technique names don't stay"; "named statistical measures stay") — it pushes toward equal-area without naming LAEA. That trade-off was the operator's call and is recorded here for future reference.

---

## Evaluator review 2026-05-28b  (evaluator-commit <pending>)

Re-evaluation pass after the 2026-05-28T08:55:21Z HR-001 resolution (commit
`72759765`). Confirms the new accept-list grader is calibrated against the
existing failure-mode set on the reference and broken solutions; no current
agent runs exist yet under v2 so the diagnostic verdict rests on grader/broken
behaviour rather than fresh transcripts.

### 1. Design history

One new commit on the task directory since the prior evaluator review:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | mixed (tests-change [meta] + docs) | Repo-wide: added integer `task.json.version` field stamped into runs; dropped unused `prompt_version` from `metadata.yaml`. For this task the only diff is `metadata.yaml`'s `prompt_version: '1.0'` line removed. | Commit msg: introduces task-content versioning so runs against stale task definitions are visible in the UI; `prompt_version` had no runtime relevance. Non-design-affecting for this task (no instruction, grader, input, or reference change). |
| 2026-05-28 | 72759765 | mixed (prompt-change + grader-change + reference-change + tests-change + docs-change) | HR-001 resolution: added `crs_epsg` integer column to CSV schema; grader refactored to a 7-EPSG North-Pole-origin accept-list, reprojects source GPKG into the declared CRS at grading time, adds `equal_area_crs_used` subcheck, drops hardcoded `bbox_within_polar_svalbard_envelope`; canonical reference CRS migrated EPSG:3995 → EPSG:3575 (LAEA Europe); brokens refactored with new `broken_conformal_pick` (7/8 = 0.875); instruction rephrased "Pick an appropriate polar projection" → "Pick the most appropriate coordinate system for measuring area at these latitudes"; `task.json.version` 1 → 2. | Commit msg: closes the three-pass HR-001 standing flag — instruction left CRS choice open but grader was pinned to EPSG:3995; CSV had no in-file CRS metadata so the grader needs the agent to declare their frame. New design pattern documented as portable for future CSV-output CRS-target tasks. |

The cumulative change-log journal (from the first evaluator block onward):
`f60034b` 2026-05-08 initial-authoring → `b4583b4` 2026-05-17 prompt-strip
(EPSG:3995 removed) → `29a9ae3` 2026-05-26 folder reorg → three evaluator
artefact commits 2026-05-26..27 (`4bbc2c7`, `a8b25d6`, `902a0f9`) → `622342b`
2026-05-28 version-field rollout (non-design-affecting for this task) →
`72759765` 2026-05-28 HR-001 resolution.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-28T08:55:21Z (commit `72759765`, class:
  mixed — prompt + grader + reference + tests). Verified via
  `git log -1 --format=%cI 72759765` and the commit's diff stats
  (`README.md`, `audit/AUTHORING_HISTORY.md`, `audit/status.json`, `grade.py`,
  `metadata.yaml`, `reference/failures/_make_brokens.py`, three broken outputs,
  `reference/solution/generate.py`, `reference/solution/outputs/...csv`,
  `task.json`). The earlier `622342b` versioning commit's diff for this task
  is `metadata.yaml` only (one `prompt_version` line removed) and per the
  evaluator prompt Step 4 does **not** require a version bump (metadata-yaml
  non-tolerance edit is in the "not required" list); it is non-design-affecting
  here.

#### Runs considered

Enumerated all 33 run directories under `benchmark/eval/runs/*/crs-l2-svalbard-polar-areas/`.
The four newest are still pre-cutoff (latest `run-20260528-0317Z` started
2026-05-28T03:19:31Z, ~5.5 h before the cutoff commit), so every existing
run is **stale** under the new v2 schema. All scores below were computed
against the pre-resolution grader (with `bbox_within_polar_svalbard_envelope`
and EPSG:3995-pinned `per_glacier_bbox_matches`) and against the
pre-resolution instruction; they do not measure v2.

| Run | Adapter | Family | Started | Score (v1 grader) | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260527-2016Z | claude-code-opus-basic (opus-4-7) | claude-code | 2026-05-27T20:23:34Z | 0.5 | done | stale |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-27T23:23:58Z | 0.625 | done | stale |
| run-20260528-0113Z | claude-code-opus-basic (opus-4-7) | claude-code | 2026-05-28T01:21:48Z | 0.5 | done | stale |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | openrouter | 2026-05-28T03:19:31Z | 0.75 | done | stale |

All 29 earlier runs (run-20260512* through run-20260526-1922Z) were already
flagged stale in the prior evaluator blocks; they remain stale and are not
re-listed here. No `current` runs exist for v2.

#### Per-run output inspection

Not applicable — no current runs. The four post-2026-05-26 pre-cutoff runs
above are noted only to confirm that the four new run directories the
orchestrator may surface in the UI are all pre-resolution. Their CSVs lack
the required `crs_epsg` column added in v2; under the current grader they
would Gate-1-fail on missing columns (this is the expected "stale" behaviour,
not a calibration concern).

#### Output-CRS / format consistency (Step 2c-CRS)

Consistent under v2.

- Reference output CRS: `EPSG:3575` (LAEA Europe). Verified by reading
  `reference/solution/outputs/svalbard_glaciers_top20.csv` `crs_epsg`
  column — all 20 rows declare 3575.
- `expected_outputs[].crs`: `EPSG:3575` in `task.json`.
- README "Accepted projections" table lists 3575 as the canonical row and
  marks the seven-EPSG accept-list explicitly.
- Grader behaviour: reads the submission's declared `crs_epsg`, validates
  against the seven-EPSG set, and reprojects the source GPKG (in
  EPSG:4326) into the *submission's* declared CRS for the per-glacier
  area / bbox comparisons. This is the legitimate **both-sides-same-way**
  reprojection pattern called out in the evaluator prompt's 2c-CRS bullet
  ("Transforming both sides the same way … is fine"). No one-sided
  reprojection to paper over a contract mismatch.
- The README and `metadata.yaml` both correctly state that 3573/3574/3576/6931
  LAEA variants give bit-identical areas (central meridian only rotates the
  bbox), and that 3413/3995 conformal variants pass the area subchecks but
  lose `equal_area_crs_used`.

#### Verdict

**calibrated**

Reasoning: the v2 design closes the HR-001 hole that capped legitimate polar
picks at 0.75 by giving the agent a machine-readable `crs_epsg` declaration
channel and grading per-glacier values in the agent's frame. Discrimination
across the documented failure-mode space, measured against the current grader
on the bundled reference + four broken solutions:

| Solution | Score | Discriminates |
|---|---|---|
| `reference/solution/outputs/` (LAEA Europe 3575) | 1.000 (8/8) | The textbook-correct equal-area pick scores the ceiling. |
| `broken_offset_topN` (LAEA 3575, ranks 6–25) | 0.750 (6/8) | Catches off-by-N top-N pickers — fails `top20_name_set_matches` and `total_top20_area_within_1_percent`. |
| `broken_conformal_pick` (Polar Stereographic 3995) | 0.875 (7/8) | Distinguishes equal-area-correct (textbook) from area-correct-within-tolerance-but-conformal. |
| `broken_no_reprojection` (declares 4326, areas in deg²) | 0.000 (Gate 1) | Caught at the accept-list gate. |
| `broken_wrong_format` (GeoJSON under .csv name) | 0.000 (Gate 1) | CSV-unreadable. |

Score spread 0 / 0 / 0.75 / 0.875 / 1.0 — five distinct outcomes covering
the documented modes plus the new equal-area-vs-conformal axis. The grader's
both-sides-same-way reprojection means an LAEA-Canada / LAEA-Russia /
LAEA-NSIDC pick would also score 1.0 (central meridian rotation does not
change LAEA areas), and either Polar Stereographic variant scores 0.875. The
instruction nudge ("most appropriate coordinate system for measuring area")
is preserved as-is from the v2 commit; it is documented as borderline under
the strip-guide in the prior block and was the operator's call. No further
unilateral edit is justified before fresh v2 agent runs land.

The verdict rests on grader/broken behaviour rather than fresh transcripts
because there are zero current runs (every run pre-dates the cutoff). The
evaluator-prompt 2b rule for missing current runs is "record 'no current runs
available' and stop the diagnostic part of Step 2 … unless you have other
concrete reason to suspect a problem"; the broken-solution spread provides
that other evidence and is sufficient for a `calibrated` verdict here.

Not too-easy (the broken set spans 0–0.875, not all 1.0), not too-strict
(reference + the documented conformal-pick path both hit their intended
ceilings), not prompt-grader-inconsistent (the v2 commit explicitly closed
that prior finding), not insufficient-evidence in the agent-runs sense but
worth noting that the next sweep should produce v2 runs before this can be
called confirmed by transcripts.

#### Specific findings

- Coverage axis nudge (no flag, applied below). The v2 grader accepts the
  LAEA family explicitly via `EQUAL_AREA_EPSGS = {3573, 3574, 3575, 3576, 6931}`
  and rewards it with `equal_area_crs_used`; the canonical reference is now
  EPSG:3575 (LAEA Europe). The coverage `crs_variants` list previously had
  only `[wgs84, polar]` (matching the pre-v2 reference's Polar Stereographic
  pick); under v2 the canonical CRS is equal-area, and the grader explicitly
  distinguishes equal-area from polar-stereographic. Add `equal-area` to
  `crs_variants` to reflect the canonical pick and the new discriminator;
  keep `polar` (the seven-EPSG accept-list still covers both Polar
  Stereographic variants) and `wgs84` (the input CRS). This is a mechanical
  coverage update, not a unilateral grader/prompt edit, so it does not
  trigger a version bump.
- Provenance note (low, no flag): `metadata.yaml`/`README` Story say the
  slice is OSM-derived while the README Input section and `metadata.yaml`
  notes say Overture (theme=base/type=land/subtype=glacier);
  `inventory.md` labels it OSM `natural=glacier`. Data is bundled either
  way, so `data_sources: [bundled-local]` is correct and `osm_tag_families:
  [natural]` matches the inventory's coverage assignment. Cosmetic
  provenance wording only; carried unchanged.
- No current runs against v2 exist — once the next sweep lands, re-confirm
  the verdict against fresh transcripts. Not a flag because the broken-set
  spread is sufficient evidence for `calibrated` standing.

### 3. Changes applied this run

#### Unilateral edits

- `coverage.yaml`: added `equal-area` to `crs_variants` to reflect the v2
  canonical reference (EPSG:3575, LAEA Europe) and the grader's
  `equal_area_crs_used` discriminator. No grader/prompt/input contract
  change; no version bump.

#### Proposed but not applied (see HUMAN-REVIEW items)

None.

#### Tests run

- grader on reference: 1.00 (8/8 — passes both gates plus `equal_area_crs_used`,
  `row_count_is_20`, `top20_name_set_matches`, `per_glacier_area_matches`,
  `total_top20_area_within_1_percent`, `sorted_by_area_desc`,
  `per_glacier_bbox_matches`, `bbox_min_less_than_max`).
- pytest: pass (41/41).

---

## Evaluator review 2026-06-06  (evaluator-commit <pending>)

Re-evaluation pass after two new grader commits (the repo-wide CRS soft-gate
refactor on 2026-05-28 and the canonical-subcheck removal on 2026-05-29).
Confirms the v3 grader is still calibrated, refreshes the broken_no_reprojection
metadata that drifted under the soft-gate change, aligns the README failure-mode
table with the 9-subcheck grader, and adds `analyst_notes` (previously missing).

### 1. Design history

Two new commits on the task directory since the prior evaluator block
(2026-05-28b):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 05aabd6 | grader-change | Repo-wide CRS soft-gate refactor: Gate 1 no longer hard-fails a non-canonical EPSG; only an unparseable EPSG hard-fails. The submission is graded in its declared frame, and two soft subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) dock points. For this task: `ACCEPTED_POLAR_EPSGS` renamed `MEANINGFUL_EPSGS`, `CANONICAL_EPSG = 3575` added, the Gate-1 "not in accepted set" branch replaced with a `pyproj.CRS.from_epsg` parseability check, and two soft CRS subchecks appended. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — over-penalises a recoverable failure mode (correct geometry in the wrong CRS); aggregate Gemma run mean moved 0.639 -> 0.680 across 21 graders. |
| 2026-05-29 | 9a985b2 | grader-change | Drops the `crs_is_canonical` subcheck and the `CANONICAL_EPSG` constant. Now 9 subchecks (was 10). LAEA pick scores 9/9 = 1.0; Polar Stereographic 8/9 = 0.889. Broken-solution metadata `measured_score` refreshed for `conformal_pick` (0.875 -> 0.889) and `offset_topN` (0.75 -> 0.778); broken `no_reprojection` was not refreshed in this commit. | Commit msg: rewarding EPSG:3575 over the four other LAEA variants was a coin-flip penalty against bit-identically-correct solutions, contradicting the metadata's own statement that they are equivalent. |

Cumulative journal: `f60034b` 2026-05-08 initial-authoring -> `b4583b4`
2026-05-17 prompt-strip -> `29a9ae3` 2026-05-26 folder reorg -> evaluator
artefact commits (`4bbc2c7`, `a8b25d6`, `902a0f9`) -> `622342b` 2026-05-28
version-field rollout -> `72759765` 2026-05-28 HR-001 resolution (crs_epsg
column + tiered accept-list) -> `2e3beae` 2026-05-28 evaluator artefact ->
`05aabd6` 2026-05-28 CRS soft-gate -> `9a985b2` 2026-05-29 canonical-subcheck
removal.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-29T11:37:01Z (commit `9a985b2`, class:
  grader-change — removed the `crs_is_canonical` subcheck). Verified via
  `git log -1 --format=%cI 9a985b2`.

#### Runs considered

Enumerated `benchmark/eval/runs/*/crs-l2-svalbard-polar-areas/`. Of the 38
run directories total, three started after the cutoff:

| Run | Adapter | Family | Started | Score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | openrouter | 2026-06-06T09:53:19Z | n/a | failed (UnicodeDecodeError reading input) | current — model-side |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | openrouter | 2026-06-06T11:35:18Z | 0.667 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | openrouter | 2026-06-06T13:43:28Z | n/a | failed (BadRequestError: 1.78M-token context overflow) | current — model-side |

All earlier 35 runs are pre-cutoff (latest stale is `run-20260529-0902Z` at
2026-05-29T09:12:26Z, ~2.5 h before the cutoff commit) and not used as
evidence. Only one current run produced a score; the other two are
model-side failures per the evaluator-prompt rule (timeouts / oversized
queries / context overflow are model issues, not task calibration
evidence).

#### Per-run output inspection

`run-20260606-1129Z` (Gemma, gis_detailed prompt) produced
`svalbard_glaciers_top20.csv` declaring `crs_epsg=3031` — Antarctic Polar
Stereographic, the wrong hemisphere for Svalbard. Both CRS subchecks fail
(`equal_area_crs_used` and `crs_in_meaningful_set`), and the projected
total area lands at 1.35e8 km² (over a thousand times the real Svalbard
glacier total of ~9770 km²) because Svalbard is far from EPSG:3031's South
Pole origin where the stereographic scale distortion explodes. The grader
recomputes the reference in EPSG:3031 as well, so per-glacier areas and
bboxes still match by ratio in the same broken frame and pass their
subchecks (the apples-to-apples logic intended for the Northern polar
variants). `top20_name_set_matches` fails (Jaccard 0.8182) because the
ranking by Antarctic-stereographic-projected area for Svalbard glaciers is
different from the ranking by a true area calculation: the projection's
extreme scale distortion magnifies some polygons more than others.

Score: 6/9 = 0.667. Three subchecks fail (the two CRS subchecks plus
`top20_name_set_matches`); six pass. The discrimination still works in
spirit — the run is meaningfully worse than the 0.778 offset-topN broken
and the 0.889 conformal-pick broken, and clearly below the 1.0 LAEA
ceiling.

Note: this run exposes a latent grader behaviour worth noting (not a
flag). Because the grader reprojects the reference into the submission's
declared frame, an absurd CRS pick (Antarctic when the data is Arctic)
still passes the per-glacier area/bbox subchecks. The CRS-quality and
ranking subchecks are what catch it. This is by design under the v2/v3
contract — `equal_area_crs_used` + `crs_in_meaningful_set` are the
intended discriminators for the agent's CRS judgement — but worth noting
that an analyst reading just the per-glacier subchecks would mistakenly
think the projected work was fine.

#### Output-CRS / format consistency (Step 2c-CRS)

Consistent under v3.

- Reference output CRS: `EPSG:3575` (LAEA Europe). `expected_outputs[].crs`:
  `EPSG:3575`. README "Accepted projections" lists 3575 as the canonical row.
- Grader behaviour: reads the submission's declared `crs_epsg`, validates
  parseability, and reprojects the source GPKG into the submission's declared
  CRS for per-glacier comparisons. Legitimate both-sides-same-way reprojection
  per the evaluator prompt's 2c-CRS bullet; no one-sided reprojection to paper
  over a contract mismatch.

#### Verdict

**calibrated**

Reasoning. The v3 grader's score gradient on the reference + brokens, measured
this run:

| Solution | Score | Comment |
|---|---|---|
| `reference/solution/outputs/` (LAEA Europe 3575) | 1.000 (9/9) | Textbook ceiling. |
| `broken_conformal_pick` (Polar Stereo 3995) | 0.889 (8/9) | Loses only `equal_area_crs_used`. |
| `broken_offset_topN` (LAEA 3575, ranks 6-25) | 0.778 (7/9) | Loses `top20_name_set_matches` and `total_top20_area_within_1_percent`. |
| `broken_no_reprojection` (declares 4326, deg² area) | 0.444 (4/9) | Loses both CRS subchecks + both area subchecks + name-set. Was 0.0 under the pre-05aabd6 hard gate; metadata refreshed below. |
| `broken_wrong_format` (GeoJSON under .csv name) | 0.000 (Gate 1) | CSV-unreadable. |
| current Gemma run (EPSG:3031, wrong hemisphere) | 0.667 (6/9) | Loses both CRS subchecks + name-set. |

Six distinct outcomes (0 / 0.444 / 0.667 / 0.778 / 0.889 / 1.0) spanning the
documented failure modes plus the new soft-gate behaviour for non-meaningful
CRS picks. The grader still rewards the textbook LAEA-for-area answer with the
ceiling, discriminates conformal-but-polar (0.889) from off-by-N (0.778), and
soft-grades catastrophic CRS picks (0.444 for honest 4326, 0.667 for an
Antarctic stereographic pick) instead of zeroing them. The Gemma EPSG:3031 run
also confirms the soft-gate change behaves sensibly: a clearly-wrong CRS pick
gets partial credit for whatever else is right but cannot reach 1.0.

Not too-easy (no run scored >= 0.95 except the reference; current Gemma is
0.667), not too-strict (the reference scores 1.0 with no drift), not
prompt-grader-inconsistent (the v2 commit closed that hole, and the v3 soft
gate did not reopen one). Insufficient-evidence is the closest alternative,
since only one current done-run exists and from a single agent family; the
broken-set spread provides the bulk of the calibration evidence.

#### Specific findings

- `broken_no_reprojection` measured score drifted from 0.0 (pre-05aabd6) to
  0.444 (post-05aabd6) when the CRS hard gate was softened. `metadata.yaml`
  still claimed `measured_score: 0.0`, `expected_score_range: [0.0, 0.0]`,
  and the description said "Gate 1 rejects 4326 ... scores 0", which is now
  factually wrong. Refreshed unilaterally below (the prompt's Step 4 lists
  `broken_solutions > measured_score` updates as an explicit allowed edit).
- README's `Failure modes` table and `Accepted projections` final paragraph
  still claimed Gate-1 rejections and 7/8 = 0.875 for conformal picks, both
  obsolete after 05aabd6 and 9a985b2. Aligned with the current grader as a
  docs-only edit (no version bump).
- `task.json` had no `analyst_notes` field. Authored fresh under the v3
  schema. No version bump (the field is human-facing-only).
- Instruction is in slightly off-house-style territory ("svalbard_glaciers —"
  prefix opener with em-dash, "columns ... — bboxes ..." em-dash list,
  trailing "File: ..." fragment). A house-style rewrite is in scope per
  Step 4, but the current instruction is the carefully-tuned outcome of the
  HR-001 resolution discussion ("the operator's call" per the 2026-05-28
  block); rewriting it risks reopening the equal-area-versus-conformal nudge
  calibration. Leaving in place. Worth a separate dedicated review pass if
  the operator wants a house-style sweep of legacy CRS prompts.
- One latent grader behaviour worth noting (no flag): the apples-to-apples
  reprojection design means a hemispherically-wrong CRS pick (Antarctic for
  Svalbard, per the Gemma run) still passes the per-glacier area/bbox
  subchecks because both sides are computed in the same broken frame. The
  CRS subchecks and `top20_name_set_matches` are the intended catch. This is
  by design but is non-obvious from the score breakdown alone.
- Provenance note (low, no flag, carried from prior block): `metadata.yaml`/
  `README` Story say OSM-derived; the README Input section and `metadata.yaml`
  notes say Overture (theme=base/type=land/subtype=glacier); `inventory.md`
  labels it OSM `natural=glacier`. Cosmetic only; coverage assignment is
  `data_sources: [bundled-local]` and `osm_tag_families: [natural]` either
  way.

### 3. Changes applied this run

#### Unilateral edits

- `metadata.yaml`: refreshed `broken_solutions.no_reprojection.measured_score`
  from 0.0 to 0.444, updated `expected_score_range` to `[0.4, 0.5]`, and
  rewrote the description to reflect the post-soft-gate reality. Step 4
  permits `broken_solutions.measured_score` refreshes without a version
  bump.
- `README.md`: rewrote `Failure modes` 1-4 and the `Accepted projections`
  closing paragraph to align with the 9-subcheck v3 grader (Gate 1 no longer
  hard-rejects parseable EPSGs; conformal pick is 8/9 = 0.889; off-by-N is
  7/9 = 0.778; no_reprojection is 4/9 = 0.444). Docs-only; no version bump.
- `task.json`: added `analyst_notes` (description, approach, pitfalls). The
  field is human-facing-only and per Step 4's bump-required list, authoring
  `analyst_notes` does not require a version bump.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp. No axis changes.

#### Proposed but not applied (see HUMAN-REVIEW items)

None.

#### Tests run

- grader on reference: 1.00 (9/9 — passes both gates and all nine subchecks).
- grader on brokens: `wrong_format` 0.0, `no_reprojection` 0.444,
  `conformal_pick` 0.889, `offset_topN` 0.778. All within the refreshed
  expected ranges.
- pytest: pass (41/41).

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Row-count-within-5%-of-reference check from Gate 2 dropped — already
  covered (strictly) by the existing `row_count_is_20` subcheck.
- Removed now-unused `count_within_tolerance` import.
- Subcheck count unchanged at 9.

### Verification
- Reference solution re-graded: 1.0 (9/9 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <pending>)

Re-evaluation pass after two repo-wide grader commits landed post the 2026-06-06
block: the Gate-2 removal (363aed2, already documented in the manual-cleanup
block above) and the 3x data-content subcheck weighting (05b389b). The weighting
changed every score fraction (the grader now totals 17 weighted points, not 9
unit points), which left metadata.yaml measured scores and README fractions
stale. Three fresh post-cutoff agent runs exist and are used as evidence.

### 1. Design history

Two new commits on the task directory since the 2026-06-06 evaluator block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change | Removed the `structural_correctness` gate and its early-returns; dropped the now-unused `count_within_tolerance` import. Row-count-within-5% Gate-2 check dropped (already covered strictly by `row_count_is_20`). Subcheck count unchanged at 9. | Commit msg: Gate 2 was inconsistent across the 36 graders (34 effectively hard, 2 soft); library now has one hard `format_schema_valid` gate, everything coercible is a subcheck. |
| 2026-06-07 | 05b389b | grader-change | Added `weight=3.0` to the four data-content subchecks (`top20_name_set_matches`, `per_glacier_area_matches`, `total_top20_area_within_1_percent`, `per_glacier_bbox_matches`). Five schema/structural subchecks stay weight 1. Weighted total is now 17 points. | Commit msg: clean-schema-wrong-data submissions should score visibly lower than correct-data slightly-off-schema ones; CRS-metadata/structural checks keep weight 1. |

Neither commit bumped `task.json.version` (still 2); both are repo-wide manual
sweeps, not evaluator edits, and the version-bump policy binds evaluator passes.
Cumulative journal: `f60034b` 2026-05-08 initial-authoring -> `b4583b4`
2026-05-17 prompt-strip -> `29a9ae3` 2026-05-26 folder reorg -> evaluator
artefact commits -> `622342b` 2026-05-28 version-field rollout -> `72759765`
2026-05-28 HR-001 resolution (crs_epsg column + accept-list) -> `05aabd6`
2026-05-28 CRS soft-gate -> `9a985b2` 2026-05-29 canonical-subcheck removal ->
`91c0ad6` 2026-06-06 evaluator artefact -> `363aed2` 2026-06-06 Gate-2 removal
-> `05b389b` 2026-06-07 3x data-content weighting.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-06-07T18:28:18Z (commit `05b389b`, class:
  grader-change — 3x weighting). Verified via `git log -1 --format=%cI`.

#### Runs considered

42 run directories enumerated under `benchmark/eval/runs/*/crs-l2-svalbard-polar-areas/`;
three started after the cutoff and pass the version check
(`run.json` records `task_version: 2`, current `task.json.version` is 2):

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T18:54:52Z | 0.941 | done | current |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T08:06:29Z | 0.941 | done | current |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T08:57:53Z | 1.0 | done | current |

Note on run-20260607-112430Z: its `invocation.suite_git_sha` (06fd6c0) predates
the weighting commit because the sweep started 11:24Z, but this task's session
started 18:54Z (post-cutoff) and its `score.json` records the weight-3.0
subchecks, proving it was graded by the current grader; version check passes,
so it counts as current. Stale runs: the other 39 directories
(run-20260512* through run-20260606-1733Z) pre-date the cutoff; itemised in
the prior evaluator blocks, not re-listed.

#### Per-run output inspection

All three produced `svalbard_glaciers_top20.csv` with 20 rows, all seven
required columns, sorted descending, Jaccard 1.0000 on the top-20 name set,
per-glacier area and bbox match rates 1.000 in their declared frames, and
`bbox_min_less_than_max` passing:

| Run | CRS picked | equal_area_crs_used | score |
|---|---|---|---|
| 112430Z (gemma detailed) | EPSG:3413 (NSIDC Polar Stereo) | FAIL | 16/17 = 0.941 |
| 074701Z (deepseek detailed) | EPSG:3995 (Arctic Polar Stereo) | FAIL | 16/17 = 0.941 |
| 084636Z (deepseek basic) | EPSG:6931 (EASE-Grid 2.0 LAEA) | PASS | 17/17 = 1.0 |

The equal-area-versus-conformal discriminator demonstrably separates real
agent behaviour: two conformal picks cap at 0.941, the LAEA pick reaches the
ceiling. All three runs are from the openrouter adapter family (the only
family the harness still supports post-PR3), but from two distinct model
vendors (Google Gemma, DeepSeek).

#### Output-CRS / format consistency (Step 2c-CRS)

Consistent, unchanged from the prior block: reference output declares
`crs_epsg=3575` on all rows, `expected_outputs[].crs` is EPSG:3575, README
canonical row is 3575. The grader reprojects the source GPKG into the
submission's declared CRS for per-glacier comparisons — the legitimate
both-sides-same-way pattern; no one-sided papering-over.

#### Prompt information audit

| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `svalbard_glaciers_top20.csv` | instruction ("File: ...") | stated |
| seven columns incl. `crs_epsg` | instruction (column list) | stated |
| `crs_epsg` integer, single value per file | instruction ("the integer EPSG code of the CRS you used") | stated |
| 20 rows | instruction ("top 20") | stated |
| sorted by area_km2 descending | instruction | stated |
| area in km² | instruction (column `area_km2`) | stated |
| bbox in projected metres of the chosen CRS | instruction ("bboxes in the same projected metres as the area") | stated |
| equal-area CRS scores higher than conformal | "true geographic area" + "most appropriate coordinate system for measuring area at these latitudes" | inferable (deliberate design nudge) |
| 1% area/bbox tolerance | grader-internal | inferable (deterministic reprojection + area) |
| bbox min < max | convention | inferable |

Factual claims verified: input name `svalbard_glaciers` matches
`task.json.inputs[].name`; column names and units match the reference output
schema; no inaccurate claims found.

#### Reference faithfulness

Faithful. `reference/solution/generate.py` reads the bundled GPKG, reprojects
to EPSG:3575 (equal-area, central meridian aligned with Svalbard), computes
area in km² and per-feature bbox in projected metres, sorts descending with a
deterministic tie-break, keeps the top 20, and writes exactly the seven
contract columns with `crs_epsg=3575`. No unrequested operations, no skipped
steps, and the CRS choice is the textbook-correct equal-area pick.

#### Verdict

**calibrated**

Three current runs span 0.941–1.0 with the intended discriminator (equal-area
vs conformal) doing the separating, and the broken-solution spread under the
current weighted grader is 0 / 0.353 / 0.647 / 0.941 / 1.0
(`wrong_format` / `no_reprojection` / `offset_topN` / `conformal_pick` /
reference), re-measured this run. Not too-easy: two of three current runs
score 0.941 < 0.95 and the instruction does not name any EPSG or algorithm.
Not too-strict: no correct-looking output scored near 0. Not
prompt-grader-inconsistent: every scored constraint is stated or inferable
(table above).

#### Specific findings

- The 3x weighting (05b389b) silently changed all score fractions: the
  grader now totals 17 weighted points. `metadata.yaml` measured scores
  (`no_reprojection` 0.444 -> 0.353, `conformal_pick` 0.889 -> 0.941,
  `offset_topN` 0.778 -> 0.647) and the README fractions were stale;
  `no_reprojection`'s recorded `expected_score_range` [0.4, 0.5] no longer
  bracketed the measured 0.353. Refreshed unilaterally (Step 4 permits
  `measured_score` refreshes; docs-only README alignment).
- Side-effect of the weighting worth noting (no flag): the conformal-pick
  penalty shrank from 1/9 (0.111) to 1/17 (0.059), so a Polar Stereographic
  pick now scores 0.941 — just under the 0.95 too-easy line. This is the
  deliberate outcome of the repo-wide weighting decision (CRS-judgment checks
  keep weight 1); flagging it would re-litigate commit 05b389b.
- The inventory row for this task still describes the pre-resolution design:
  `CRS out: EPSG:3995 (Arctic Polar Stereographic)`, a 6-column output schema
  without `crs_epsg`, and a story that pins "the Arctic Polar Stereographic
  CRS". Since commit 72759765 the canonical CRS is EPSG:3575 (LAEA), the
  schema has seven columns, and the CRS choice is open with an accept-list.
  <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" -->
  The human should refresh the `crs-l2-svalbard-polar-areas` row in
  `benchmark/authoring/inventory.md` (CRS out, output-artifact column list,
  story wording) to match the v2 design; the task itself is correct and the
  deviation is the documented operator decision of 2026-05-28, so no task
  edit is needed.
- Instruction still carries two em-dashes and a trailing "File: ..."
  fragment (off house style). Carried unchanged, same reasoning as the
  2026-06-06 block: the wording is the operator-tuned HR-001 resolution and
  an instruction edit would force a version bump that invalidates the three
  fresh, well-calibrated runs for a purely stylistic gain.
- Provenance note (low, no flag, carried): metadata/README say Overture
  base/land/glacier; inventory says OSM `natural=glacier`. Cosmetic;
  coverage keeps `data_sources: [bundled-local]`, `osm_tag_families: [natural]`.

### 3. Changes applied this run

#### Unilateral edits

- `metadata.yaml`: refreshed `broken_solutions` measured scores to the
  weighted grader (`no_reprojection` 0.444 -> 0.353 with range [0.4,0.5] ->
  [0.3,0.45]; `conformal_pick` 0.889 -> 0.941; `offset_topN` 0.778 -> 0.647)
  and noted the weight arithmetic in each description. Re-grade on reference:
  1.0. Reason: commit 05b389b changed the score denominators; no bump needed
  for measured-score refreshes.
- `README.md`: updated all score fractions to the 17-point weighted scale and
  documented the weighting in the Accepted projections section. Docs-only;
  no version bump.
- `coverage.yaml`: refreshed `evaluator_run_at`. No axis changes (all slugs
  re-validated against the vocabulary).

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — inventory-mismatch — `inventory.md` row still describes the
  pre-72759765 design (EPSG:3995 pinned, 6-column schema, no crs_epsg);
  refresh it to the v2 accept-list design.

#### Tests run

- grader on reference: 1.0 (gate passes, 9/9 subchecks, 17/17 weighted points)
- grader on brokens: wrong_format 0.0, no_reprojection 0.353,
  conformal_pick 0.941, offset_topN 0.647 — all inside refreshed ranges
- pytest: pass (41 passed)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

**Reviewed the subcheck weighting for severity-calibration; found it already
calibrated. No weight edits.**

Targeted pass to check whether the repo-wide 3x data-content weighting
(05b389b) gives a sensible severity-ordering for this CRS task, or whether it
was a one-size-fits-all miscalibration. Conclusion: the current weights are
correct for what this task tests, and one specific anti-pattern invariant
(declares-right-CRS-but-never-transformed must not out-score honest-unprojected)
is satisfied with margin. Left grade.py / metadata.yaml / README.md unchanged.

### Weights reviewed (no change)

| Subcheck | Weight | Severity role |
|---|---|---|
| `equal_area_crs_used` | 1 | LAEA-vs-conformal cue — central discriminator, but deliberately light: the conformal pick is a *defensible, cosmetic* miss (<1% area distortion) that must score near the top, so a low weight here is correct. Up-weighting would wrongly turn a defensible CRS choice into a meaningful penalty. |
| `crs_in_meaningful_set` | 1 | polar accept-list sanity (CRS label) |
| `top20_name_set_matches` | 3 | proves the metric-area ranking happened |
| `per_glacier_area_matches` | 3 | proves per-glacier reprojection happened |
| `total_top20_area_within_1_percent` | 3 | catches scale errors / top-N drops |
| `per_glacier_bbox_matches` | 3 | proves coordinates were transformed (degrees vs metres) |
| `row_count_is_20` | 1 | structural |
| `sorted_by_area_desc` | 1 | structural |
| `bbox_min_less_than_max` | 1 | structural |

The four weight-3 checks are exactly the "prove the reprojection actually
happened" group the calibration brief asks to weight over the CRS-label checks.
They are load-bearing here, not a blunt sweep artefact.

### Broken scores (unchanged — no weight edit)

| Broken | Score | Severity tier — ordering note |
|---|---|---|
| `wrong_format` | 0.000 | unrecoverable (gate fail) — floor |
| `no_reprojection` (honest 4326, deg² area) | 0.353 | **central** failure (whole task skill skipped) — largest non-zero drop |
| `offset_topN` (correct CRS+frame, ranks 6–25) | 0.647 | **meaningful** (CRS skill demonstrated, wrong deliverable set) — mid |
| `conformal_pick` (3995, all data correct) | 0.941 | **cosmetic** (defensible conformal CRS) — near top |
| reference (3575 LAEA) | 1.000 | ceiling |

Ordering 0.0 < 0.353 < 0.647 < 0.941 < 1.0 is monotone and the magnitudes
track severity: cosmetic slip costs ~0.06, the wrong-deliverable error costs
~0.35, the skipped-reprojection error costs ~0.65. No disjoint-failure
inversion: up-weighting any single group does not reward a worse broken.

### Anti-pattern invariant (verified directly)

The brief's invariant — "a file that declares the right CRS but never
transformed the coordinates must never score higher than an honestly-unprojected
file" — holds with margin. Synthesised the adversarial case (the
`no_reprojection` degree-valued CSV relabelled `crs_epsg=3575`) and graded it:
**0.294**, *below* the honest 4326 file's 0.353. The liar gains the two weight-1
CRS-label checks for declaring 3575 but loses the weight-3
`per_glacier_bbox_matches` that the honest file keeps (degree bbox values match
the reference reprojected into 4326, not into 3575). The weight-3
area/bbox/name checks are precisely what punishes the liar harder. This is the
strongest evidence the data-content weighting is correctly placed for a CRS
task: it rewards proof-of-reprojection over CRS-metadata-declaration.

### Prior-run re-grade

Three current runs (v2, post-05b389b) re-graded under the unchanged weights:

| Run | CRS | recorded | regraded |
|---|---|---|---|
| run-20260607-112430Z (gemma) | 3413 conformal | 0.941 | 0.941 |
| run-20260608-074701Z (deepseek) | 3995 conformal | 0.941 | 0.941 |
| run-20260609-084636Z (deepseek) | 6931 LAEA | 1.000 | 1.000 |

No shifts (no weight change). The equal-area-vs-conformal discriminator
separates real agent behaviour as intended.

### Reasoning

This is a CRS task where (a) the reprojection-proof checks are already at
weight 3 and (b) the equal-area-vs-conformal discriminator is deliberately
light because the conformal pick is a defensible near-top miss. Both choices
are correct for the documented design intent. The verified anti-pattern result
(liar 0.294 < honest 0.353) shows the weighting punishes
declared-but-not-transformed CRSes correctly. No reweighting improves the
severity-ordering, so no edit is warranted.

### Changes applied this run

#### Unilateral edits

None. Reviewed and confirmed calibrated; per the calibration brief Step 11,
no edits to grade.py / metadata.yaml / README.md and no change to status.json
(HR-001 here is inventory-mismatch, not a weighting HR).

#### Tests run

- grader on reference: 1.0 (gate passes, 9/9 subchecks, 17/17 weighted points)
- grader on brokens: wrong_format 0.0, no_reprojection 0.353,
  conformal_pick 0.941, offset_topN 0.647 — all inside recorded ranges
- adversarial liar (declare 3575, coords in degrees): 0.294 (< honest 0.353)
- pytest: not run (orchestrator runs the suite)
