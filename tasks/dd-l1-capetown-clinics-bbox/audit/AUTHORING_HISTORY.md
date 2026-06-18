# Implementation notes — dd-l1-capetown-clinics-bbox

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 data-discovery task: a CSV-with-WKT clinic export for Cape Town →
small JSON inventory with `count`, `bbox`, and `count_per_subdistrict`.
Reference, grader, and three broken solutions built and verified inside
the project Docker container.

## Verification results
- Reference grader score: 1.00 (8 / 8 subchecks pass)
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 cannot
    parse the CSV body as a JSON object, so no subcheck runs.
  - wrong_bbox: 0.500 (expected range [0.45, 0.55]) — 4 / 8 subchecks
    pass: count_correct, subdistrict_keys_match,
    subdistrict_counts_match, count_equals_subdistrict_sum. The four
    bbox componentwise subchecks all fail because the [ymin, xmin,
    ymax, xmax] swap puts each component ~ 52° away from its target.
  - wrong_attributes: 0.875 (expected range [0.85, 0.95]) — 7 / 8
    subchecks pass; only `subdistrict_counts_match` fails (the equal
    split 8 × 10 = 80 happens to hit the right keys and the right
    total but six of eight per-key values are wrong).
- Second-run output match: bit-identical (verified via `cp` + `diff -q`
  on `reference/outputs/clinic_inventory.json` before/after a second
  `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32)

## Failure-mode coverage
- Lat / lon swap in the bbox: broken_wrong_bbox
- Equal-split guess for `count_per_subdistrict`: broken_wrong_attributes
- Wrong output format (CSV instead of JSON, or missing required keys):
  broken_wrong_format
- Missing or extra subdistricts: principled — `subdistrict_keys_match`
- Off-by-one count (header counted as row, parse error drop):
  principled — `count_correct` + `count_equals_subdistrict_sum`
- Bbox computed over a subset of rows: principled — four componentwise
  bbox subchecks
- Bbox in the wrong CRS (e.g. reprojected to EPSG:3857): principled —
  four componentwise bbox subchecks (deltas would be ~ 10⁶× the
  tolerance)
- Internal inconsistency between count and per-subdistrict sum:
  principled — `count_equals_subdistrict_sum`

## Open issues
- [severity: low] — Bundled input is hand-crafted rather than sliced
  from Overture. AUTHOR_CONTEXT.md and OVERTURE_REFERENCE.md both
  permit hand-crafting when the inventory anchors on an OSM tag family
  (`amenity=clinic`) with no clean Overture `places.place` equivalent.
  Cape Town clinic-style POIs are scattered across several health-
  related Overture categories with inconsistent labelling and sparse
  coverage, so a deterministic ~80-row slice is not feasible. The task
  is *about* CSV-with-WKT parsing + count + bbox + group-by, not about
  the realism of the underlying point set; the persona has explicitly
  handed the agent a legacy CSV export. Per-subdistrict counts are
  intentionally non-uniform (12, 12, 11, 10, 10, 9, 8, 8) so an "equal
  split" guess is a clean, distinguishable failure mode.

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — the grader uses only `Gate`, `Subcheck`, and `ScoreReport`
from `geo_grading`. Bbox componentwise checks and dict-equality checks
are computed inline because they are simple JSON-shape comparisons,
not geometric primitives.)

## Runtime
~15 minutes (no network fetch; all work was local Docker runs).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row (`benchmark/authoring/inventory.md` L80–103) and the
original author block above, the task is an L1 data-discovery exercise
anchored on a single primary skill: parse a CSV export whose geometry is
stored as a `wkt_geom` column and produce a small JSON inventory (`count`,
`bbox`, `count_per_subdistrict`) over a fully bundled, deterministic
80-row fixture of Cape Town clinics. The persona is Naledi Mokoena at
the City of Cape Town Health Department; the deliverable is meant to be
the kind of three-line inventory a real analyst would compute before
ingesting an export into a case-management pipeline. The author's stated
expected weak-agent failure is a lat / lon swap in the bbox flat-list.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 555e88e | initial-authoring | First commit: task.json, metadata.yaml, grade.py, README.md, IMPLEMENTATION_NOTES.md, data/_prepare_input.py, data/capetown_clinics.csv (80 rows), reference/generate.py + reference/outputs/clinic_inventory.json, tests/_make_brokens.py + 3 broken sets. | Commit msg: "task: dd-l1-capetown-clinics-bbox [completed]" (initial authoring). |
| 2026-05-08 | fbd20f2 | docs-change | Repo-level restructure: `tasks/` → `benchmark/tasks/`. No task-file content changes. | Commit msg: "restructure: split repo into thesis/ benchmark/ references/". |
| 2026-05-08 | 001e459 | docs-change | `benchmark/tasks/` → `benchmark/eval/tasks/`. Path-only move. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees". |
| 2026-05-13 | 284b843 | prompt-change | Added structured `tags` dict (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) to `task.json`. `instruction` text unchanged in this commit. | Commit msg: "eval tasks: add structured tags to all 36 task.json files … for filtering". Pure metadata addition; not a real prompt change for the agent (tags are not in the instruction string), but classified as touching task.json for completeness. |
| 2026-05-13 | a3a8d53 | docs-change | `benchmark/eval/tasks/` → `benchmark/tasks/`. Path-only move. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/". |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md`. | Commit msg: "tasks: add image-prompt.md to all 36 task directories". |
| 2026-05-13 | 1b8dda1 | docs-change | Added `image.webp` (FLUX schnell). | Commit msg: "tasks: generate image.webp for all 36 task directories". |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` (FLUX schnell pass 2). | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell". |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` (nano-banana-2). | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)". |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "is a CSV with a wkt_geom column for the clinic locations and a subdistrict column" from the instruction; kept `bbox as [xmin, ymin, xmax, ymax] in EPSG:4326`. | Commit msg: "strip deducible information from DD task instructions — Remove input CRS, geometry types, column names, format descriptions, data hints, and encoding specifics from 6 DD task instruction texts. Output requirements and narrative framing preserved." |
| 2026-05-17 | 88530c5 | prompt-change | Replaced `bbox as [xmin, ymin, xmax, ymax] in EPSG:4326` with `bbox as a 4-element array following the standard GeoJSON bbox convention`. | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts." |
| 2026-05-26 | 29a9ae3 | docs-change | Repo-wide task layout reorganisation (IMPLEMENTATION_NOTES → audit/AUTHORING_HISTORY, data/ → inputs/, reference/ → reference/solution/, tests/ → reference/failures/, image* → assets/). `grade.py` reference path updated to match. No semantic changes to instruction, grader logic, reference, or fixture. | Commit msg: "Reorganize task folder layout — Migrate every benchmark task to a clearer layout that separates audience concerns." |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T12:48:47+00:00** (commit `88530c5`, class: prompt-change). The 29a9ae3 layout reorganisation is `docs-change`-equivalent (path moves only; grader still scores reference 8/8 today), so it does not invalidate runs started after the 88530c5 prompt change.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:17:38Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:18:23Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (gemma-4-26b-a4b-it) | 2026-05-26T08:24:50Z | 1.00 | done | current |

Pre-cutoff runs (stale, not used as evidence): 21 runs between 2026-05-12 and 2026-05-17T03:04Z. They predate the 88530c5 instruction edit that swapped explicit `[xmin, ymin, xmax, ymax]` order for the "standard GeoJSON bbox convention" wording, so they cannot speak to the current prompt.

#### Verdict
**too-easy-suspected** (flagged, not unilaterally fixed)

All three `current` runs scored 1.0 across a deliberately wide capability spread (frontier Claude Opus 4.6, a mid-tier OpenRouter DeepSeek V4 Flash, and a small Gemma 4 26B). Each produced a `clinic_inventory.json` that grades 8/8: correct count (80), bbox in `[xmin, ymin, xmax, ymax]` order to 6 decimals, and the full non-uniform subdistrict count map. None tripped the lat / lon swap that the grader and `broken_wrong_bbox` set were designed to catch — including the smallest model in the set.

The current instruction reads `bbox as a 4-element array following the standard GeoJSON bbox convention` (`task.json:14`). RFC 7946 §5 pins the GeoJSON `bbox` member to `[west, south, east, north]` order, i.e. `[xmin, ymin, xmax, ymax]` in WGS84. Naming "GeoJSON bbox convention" explicitly is therefore semantically equivalent to telling the agent the order outright — it tells the agent both the lat/lon ordering and the CRS via a one-line spec lookup, and so functionally defeats the lat/lon-swap failure mode that the four bbox componentwise subchecks were designed to detect and partially credit.

This is borderline against the L1 stripping guide. `expected_outputs[].format` is `json` (non-spatial JSON), not `geojson`, so the GeoJSON bbox convention is not pinned by the output schema — the instruction is in fact the only place that names it. A weaker instruction would be `bbox as a 4-element flat array` (no order, no convention name), which would actually exercise the wrong_bbox broken case across real agents. The current wording is arguably "necessary information the agent cannot infer" since the output schema is just `json`, not GeoJSON; but it is also arguably "a gift that defeats the test" since the agent could equally well have been given a bbox object with named keys (`{xmin, ymin, xmax, ymax}`) for the same disambiguation without the convention-naming. I do not have authority to resolve this borderline call unilaterally per the prompt — flagging as `prompt-vs-grader-judgment`.

Additional context: the b04e9f0 commit (2026-05-14) already correctly stripped the input-side hints (`is a CSV with a wkt_geom column …`). The follow-up 88530c5 commit (2026-05-17) was meant to remove CRS/operation/encoding nudges per its message; it swapped an explicit-order EPSG hint for the GeoJSON-convention wording, which is a defensible authoring choice (avoid naming an EPSG; the convention covers both order and CRS). Whether the resulting wording is too informative is a per-task judgment that should be made by the human author.

#### Specific findings
- The grader is correctly designed (8 independent subchecks, 4 of which are bbox componentwise) and would distinguish the lat/lon-swap, equal-split, and wrong-format failure modes if any agent committed them. Reference still scores 1.0 on today's grader (verified: 8/8). No grader change recommended.
- The fixture (80 rows, non-uniform 12/12/11/10/10/9/8/8 per subdistrict) is preserved across all layout moves and is correct on inspection of `inputs/capetown_clinics.csv` and the reference output. No data change recommended (and I have no authority to edit `inputs/` anyway).
- <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" -->
  The current instruction names the "standard GeoJSON bbox convention" — RFC 7946 pins both the `[xmin, ymin, xmax, ymax]` order and the WGS84 CRS, so the wording effectively gives the agent the bbox order. All three post-cutoff runs (Opus, DeepSeek, Gemma) scored 1.0 and none hit the lat/lon-swap that `broken_wrong_bbox` (score 0.500) was designed to catch. Human author should decide whether to (a) keep the current wording (the output format is `json`, not `geojson`, so the convention name carries real disambiguation value), or (b) replace with `bbox as a 4-element flat array` and re-rerun, accepting that the wrong_bbox broken case becomes a more probable real-agent failure.
- <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" -->
  Commit 88530c5 swapped explicit `[xmin, ymin, xmax, ymax] in EPSG:4326` for the GeoJSON-convention wording; the commit message ("Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts") states the *category* of change but not why the convention-name was chosen over a plainer alternative (e.g. a bbox dict with named keys, or a no-name flat-list). Why is not stated in the commit message at the per-task level; the human author should record the rationale if they keep the current wording (related to HR-001).

### 3. Changes applied this run

#### Unilateral edits
- (none — only borderline / human-review-only findings; no clear-cut tolerance loosening, no obvious gift removable without judgment, no clearly-broken broken-set re-measurement.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — "Standard GeoJSON bbox convention" wording in the instruction effectively pins bbox order; all current runs score 1.0; human decides whether to weaken further or keep.
- HR-002 — design-rationale — Commit 88530c5 message states the *category* of the prompt edit but not why the GeoJSON-convention phrasing was chosen over a plainer alternative.

#### Tests run
- grader on reference: 1.0 (8/8 subchecks)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row (`benchmark/authoring/inventory.md` L80–103) and the
original author block above, this is an L1 data-discovery task anchored on a
single primary skill: parse a CSV export whose geometry is stored as a
`wkt_geom` column (`POINT(lon lat)`) and emit a small JSON inventory —
`count`, overall `bbox`, and a `count_per_subdistrict` roll-up — over a fully
bundled, deterministic 80-row fixture of Cape Town clinics. Persona: Naledi
Mokoena, a City of Cape Town Health Department analyst doing a pre-ingest
sanity check before pushing the export into a case-management pipeline. The
per-subdistrict counts are intentionally non-uniform (12/12/11/10/10/9/8/8)
so an "equal split" guess is a distinguishable failure; the author's stated
expected weak-agent failure is a lat/lon swap in the flat-list bbox.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 555e88e | initial-authoring | First commit: task.json, metadata.yaml, grade.py, README.md, IMPLEMENTATION_NOTES.md, data/_prepare_input.py, data/capetown_clinics.csv (80 rows), reference/generate.py + reference/outputs/clinic_inventory.json, tests/_make_brokens.py + 3 broken sets. | Commit msg: "task: dd-l1-capetown-clinics-bbox [completed]" (initial authoring). |
| 2026-05-08 | fbd20f2 | docs-change | Repo restructure `tasks/` → `benchmark/tasks/`. Path-only move. | Commit msg: "restructure: split repo into thesis/ benchmark/ references/". |
| 2026-05-08 | 001e459 | docs-change | `benchmark/tasks/` → `benchmark/eval/tasks/`. Path-only move. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees". |
| 2026-05-13 | a3a8d53 | docs-change | `benchmark/eval/tasks/` → `benchmark/tasks/`. Path-only move. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/". |
| 2026-05-13 | 8915010, 1b8dda1, 3c65373, cfbdc7c | docs-change | Added/regenerated `image-prompt.md` and `image.webp` (asset only). | Commit msgs: image-generation passes (FLUX schnell, nano-banana-2). |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "is a CSV with a wkt_geom column for the clinic locations and a subdistrict column" from `instruction`; kept `bbox as [xmin, ymin, xmax, ymax] in EPSG:4326`. | Commit msg: "strip deducible information from DD task instructions — Remove input CRS, geometry types, column names, format descriptions, data hints, and encoding specifics." |
| 2026-05-17 | 88530c5 | prompt-change | Replaced `bbox as [xmin, ymin, xmax, ymax] in EPSG:4326` with `bbox as a 4-element array following the standard GeoJSON bbox convention`. | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts." Category of change stated; per-task rationale for the convention-name phrasing not stated. |
| 2026-05-26 | 29a9ae3 | docs-change (effective) | Layout reorg: `data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, IMPLEMENTATION_NOTES → `audit/AUTHORING_HISTORY.md`, image* → `assets/`. Verified diff touches only the `url` path in task.json and the `REFERENCE_OUT` path in grade.py — both pure path moves tracking the rename; no content/contract change. | Commit msg: "Reorganize task folder layout". |
| 2026-05-26 | e1bbd8b | docs-change | Prior evaluator review: appended evaluator block, wrote coverage.yaml + status.json. No task-content edits. | Commit msg: "Re-evaluate dd-l1-capetown-clinics-bbox: too-easy suspected; 'GeoJSON bbox convention' wording flagged". |

(Note: this directory-level history matches the prior evaluator's reconstruction; the two prompt-change diffs (b04e9f0, 88530c5) and the 29a9ae3 path-only diff were re-verified directly from `git show` this run.)

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T12:48:47+00:00** (commit `88530c5`, class: prompt-change). 29a9ae3 (2026-05-26) edits the `inputs[].url` string, but the diff is a pure path move tracking the directory rename (`data/` → `inputs/`); it does not change the input contract or the answer key (reference still grades 8/8 on today's grader), so it is treated as docs-change-equivalent and does not advance the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:17:38Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic (deepseek-v4-flash) | 2026-05-17T15:18:23Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (gemma-4-26b-a4b-it) | 2026-05-26T08:24:50Z | 1.0 | done | current |

Pre-cutoff runs (stale, not used as evidence): 22 run dirs between 2026-05-12 and 2026-05-17T08:19Z (haiku, sonnet, hy3-preview, opus, deepseek-v4-flash — all scored 1.0 where they completed; several gemma runs failed/cancelled for model-side or env reasons: ConnectError, missing OPENROUTER_API_KEY, cancelled). All predate the 88530c5 instruction edit, so they cannot speak to the current prompt wording.

#### Verdict
**too-easy**

All three `current` runs scored 1.0 across a deliberately wide capability spread — frontier Claude Opus 4.6, mid-tier OpenRouter DeepSeek V4 Flash, and a small Gemma 4 26B. Each produced a `clinic_inventory.json` byte-equivalent (modulo dict key order, which the grader does not enforce) to the reference: `count` 80, `bbox` `[18.380309, -34.073855, 18.819549, -33.701317]` in `[xmin, ymin, xmax, ymax]` order, and the full non-uniform subdistrict map. None — not even the smallest model — tripped the lat/lon swap that the four bbox componentwise subchecks and `broken_wrong_bbox` (0.500) were built to catch.

The proximate cause is the instruction wording (`task.json:14`): `bbox as a 4-element array following the standard GeoJSON bbox convention`. RFC 7946 §5 pins the GeoJSON `bbox` member to `[west, south, east, north]` = `[xmin, ymin, xmax, ymax]` in WGS84, so naming the convention is functionally equivalent to telling the agent the axis order outright, which defeats the failure mode the bbox subchecks were designed to exercise. This is genuinely borderline, however: `expected_outputs[].format` is plain `json` (not `geojson`), so the array order is **not** pinned by the output schema — the instruction is the only place the agent could learn it, and *some* disambiguation is legitimately necessary (the agent cannot infer flat-array element order from "a 4-element array" alone). A plainer alternative (a bbox object with named keys `{xmin, ymin, xmax, ymax}`, or `a 4-element flat array` with no order at all) would either disambiguate without naming the convention, or would deliberately leave the swap exercisable. Choosing among these is a per-task authoring judgment the evaluator may not resolve unilaterally (prompt-design-prompt: no procedural gifts, but also keep "necessary information the agent cannot infer"). I therefore flag the call rather than strip the wording, matching the prior evaluator's disposition.

**CRS / format consistency (2c-CRS).** Reference output, `expected_outputs[]` (`format: json`, `crs: EPSG:4326`), and README all agree: bbox in degrees (EPSG:4326), output is non-spatial JSON. The grader compares the submission's bbox against the reference bbox value-for-value with a `1e-6°` per-component tolerance and performs **no** reprojection of either side. No one-sided reprojection, no CRS/format disagreement. Clean.

#### Specific findings
- Grader is well-designed: 8 independent subchecks (4 of them bbox componentwise) give resolution across the three documented failure classes. Re-verified this run: reference 1.0 (8/8); `broken_wrong_format` 0.0, `broken_wrong_bbox` 0.5, `broken_wrong_attributes` 0.875 — exactly the declared ranges and three distinct buckets. No grader change recommended.
- Fixture (80 rows, non-uniform 12/12/11/10/10/9/8/8) is intact across all layout moves and consistent with the reference output. No data change recommended (and editing `inputs/` is out of authority anyway).
- <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" -->
  The instruction names the "standard GeoJSON bbox convention", which by RFC 7946 pins both `[xmin, ymin, xmax, ymax]` order and WGS84 — effectively handing the agent the bbox axis order. All three post-cutoff runs (Opus, DeepSeek V4 Flash, Gemma 4 26B) scored 1.0 and none hit the lat/lon swap `broken_wrong_bbox` (0.500) was designed to catch. Human author decides: (a) keep the wording — output is `json` not `geojson`, so the convention name carries real disambiguation value the agent cannot infer; or (b) replace with a plainer form (`a 4-element flat array`, or a named-key bbox object) and re-run, accepting the wrong_bbox case becomes a more probable real-agent failure. Borderline; not resolved unilaterally.
- <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" -->
  Commit 88530c5 swapped explicit `[xmin, ymin, xmax, ymax] in EPSG:4326` for the GeoJSON-convention wording; the commit message states the *category* of change ("Remove CRS, operation, and encoding nudges") but not why the convention-name phrasing was chosen over a plainer alternative at the per-task level. Why: not stated in the commit message. Human author should record the rationale if the current wording is kept (directly related to HR-001).

### 3. Changes applied this run

#### Unilateral edits
- (none — the only findings are borderline / human-review-only. Grader is sound (reference 8/8, brokens 0.0/0.5/0.875 match metadata), no clear-cut tolerance loosening is warranted, and the one candidate gift (the bbox-convention wording) is a borderline prompt-vs-grader call I may not resolve myself.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — "Standard GeoJSON bbox convention" wording effectively pins bbox order; all current runs score 1.0; human decides whether to weaken or keep.
- HR-002 — design-rationale — Commit 88530c5 message states the change category but not why the convention-name phrasing was chosen over a plainer alternative.

#### Tests run
- grader on reference: 1.0 (8/8 subchecks)
- broken solutions: wrong_format 0.0, wrong_bbox 0.5, wrong_attributes 0.875 (all match metadata)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row (`benchmark/authoring/inventory.md` L80–103) and the
original author block above, this is an L1 data-discovery task anchored on a
single primary skill: parse a CSV-with-WKT clinic export (`POINT(lon lat)` in
EPSG:4326) and emit a small JSON inventory — `count`, overall `bbox`, and a
`count_per_subdistrict` roll-up — over a fully bundled, deterministic 80-row
fixture of Cape Town clinics. Persona: Naledi Mokoena, a City of Cape Town
Health Department analyst performing a pre-ingest sanity check before pushing
the export into a case-management pipeline. Per-subdistrict counts are
intentionally non-uniform (12/12/11/10/10/9/8/8) so an "equal split" guess
is a distinguishable failure; the author's stated expected weak-agent failure
is a lat/lon swap in the flat-list bbox.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 555e88e | initial-authoring | First commit: task.json, metadata.yaml, grade.py, README.md, IMPLEMENTATION_NOTES.md, data/_prepare_input.py, data/capetown_clinics.csv (80 rows), reference/generate.py + reference/outputs/clinic_inventory.json, tests/_make_brokens.py + 3 broken sets. | Commit msg: "task: dd-l1-capetown-clinics-bbox [completed]" (initial authoring). |
| 2026-05-08 | fbd20f2 | docs-change | Repo restructure `tasks/` → `benchmark/tasks/`. Path-only move. | Commit msg: "restructure: split repo into thesis/ benchmark/ references/". |
| 2026-05-08 | 001e459 | docs-change | `benchmark/tasks/` → `benchmark/eval/tasks/`. Path-only move. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees". |
| 2026-05-13 | a3a8d53 | docs-change | `benchmark/eval/tasks/` → `benchmark/tasks/`. Path-only move. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/". |
| 2026-05-13 | 8915010, 1b8dda1, 3c65373, cfbdc7c | docs-change | Added/regenerated `image-prompt.md` and `image.webp` (asset only). | Commit msgs: image-generation passes (FLUX schnell, nano-banana-2). |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "is a CSV with a wkt_geom column for the clinic locations and a subdistrict column" from `instruction`; kept `bbox as [xmin, ymin, xmax, ymax] in EPSG:4326`. | Commit msg: "strip deducible information from DD task instructions — Remove input CRS, geometry types, column names, format descriptions, data hints, and encoding specifics." |
| 2026-05-17 | 88530c5 | prompt-change | Replaced `bbox as [xmin, ymin, xmax, ymax] in EPSG:4326` with `bbox as a 4-element array following the standard GeoJSON bbox convention`. | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts." Category of change stated; per-task rationale for the convention-name phrasing not stated. |
| 2026-05-26 | 29a9ae3 | docs-change (effective) | Layout reorg: `data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, IMPLEMENTATION_NOTES → `audit/AUTHORING_HISTORY.md`, image* → `assets/`. Pure path moves; no content/contract change. | Commit msg: "Reorganize task folder layout". |
| 2026-05-26 | e1bbd8b | docs-change | Prior evaluator review (1st pass): appended evaluator block, wrote coverage.yaml + status.json. No task-content edits. | Commit msg: "Re-evaluate dd-l1-capetown-clinics-bbox: too-easy suspected; 'GeoJSON bbox convention' wording flagged". |
| 2026-05-27 | e629ffb | docs-change | Prior evaluator review (2nd pass): appended evaluator block + status.json refresh. No task-content edits. | Commit msg: "Re-evaluate dd-l1-capetown-clinics-bbox: too-easy; GeoJSON-bbox-convention wording flagged". |
| 2026-05-28 | 622342b | docs-change (this task) | Repo-wide: introduced integer `task.json.version` field; dropped `prompt_version` from `metadata.yaml`. This task's diff is the single removal of `prompt_version: 2026-05-08-a` from `metadata.yaml`; `task.json` itself was not touched and remains implicitly v1. | Commit msg: "Add task content versioning; drop unused prompt_version". `metadata` field rename only — does not change the prompt the agent sees, the grader, or the input. |
| 2026-05-28 | bdc9e35 | prompt-change | Resolved HR-001: replaced `bbox as a 4-element array following the standard GeoJSON bbox convention` with inline cardinal-direction order `bounding box (west, south, east, north) of all the points`; trailing `; bbox as a 4-element array following the standard GeoJSON bbox convention` suffix dropped. Also added a `design_note` block to `metadata.yaml` explaining the trim. | Commit msg explains: the prior wording named RFC 7946 by reference, which pins both axis order and WGS84 — too explicit a hint for an L1 task whose broken_wrong_bbox fixture targets exactly the lat/lon swap. Cardinal-direction form preserves enough disambiguation for the json-not-geojson output while dropping the array-shape and convention-name hints. |
| 2026-05-28 | fbb3596 | docs-change | Repo-wide review-queue cleanup: removed the resolved HR-001 entry from this task's `audit/status.json`. No task-content edits. | Commit msg: "review-queue: clear resolved-HR entries". |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T09:57:28+00:00** (commit `bdc9e35`, class: prompt-change). The 622342b versioning commit and the fbb3596 queue-cleanup commit are docs-change-equivalent (no change to instruction, grader, tolerances, or input bundle) and do not advance the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic (gemma-4-26b-a4b-it) | 2026-05-28T03:35:16Z | 1.0 | done | stale (pre-cutoff) |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:01:44Z | 1.0 | done | stale (pre-cutoff) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:46:19Z | 1.0 | done | stale (pre-cutoff) |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:53:28Z | 1.0 | done | stale (pre-cutoff) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:24:50Z | 1.0 | done | stale (pre-cutoff) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:18:23Z | 1.0 | done | stale (pre-cutoff) |
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:17:38Z | 1.0 | done | stale (pre-cutoff) |

No `current` runs available. The 24+ pre-cutoff runs all predate the bdc9e35 cardinal-direction prompt edit and therefore cannot speak to the current wording (they were all scored against the now-superseded "standard GeoJSON bbox convention" instruction).

#### Verdict
**insufficient-evidence**

The HR-001 resolution (bdc9e35, 2026-05-28T09:57:28+00:00) trimmed the instruction's bbox wording from the convention-name form to inline cardinal directions; this is exactly the kind of change that invalidates prior runs as evidence for the current state of the task. No post-cutoff runs exist yet, so the central question — does the trimmed wording surface the lat/lon swap on weaker agents, or do all agents still infer the order from "(west, south, east, north)"? — cannot be answered from current evidence. The grader and fixture themselves are sound (verified this run: reference 8/8 → 1.0; pytest 41/41 pass). Recommendation: re-evaluate after the next sweep produces ≥ 2 post-cutoff runs across distinct capability tiers.

**CRS / format consistency (2c-CRS).** Reference output, `expected_outputs[]` (`format: json`, `crs: EPSG:4326`), and README all agree: bbox values in degrees (EPSG:4326), output is non-spatial JSON. The grader compares submission bbox against reference bbox value-for-value with a `1e-6°` per-component tolerance and performs **no** reprojection of either side. No one-sided reprojection, no CRS/format disagreement. Clean.

#### Specific findings
- Grader is correctly designed and stable across all layout / prompt edits: 8 independent subchecks (4 of them bbox componentwise), the reference still grades 1.0 (8/8) on today's code, and pytest passes 41/41. No grader change recommended.
- Fixture (80 rows, non-uniform 12/12/11/10/10/9/8/8 per subdistrict) intact across all layout moves and consistent with the reference output. No data change recommended.
- The HR-001 prior-evaluator concern is now resolved (commit bdc9e35); HR-002 (request for per-task rationale on commit 88530c5's convention-name phrasing) was a low-severity design-rationale flag and is moot now that the convention-name wording itself has been removed in favour of inline cardinal directions. The metadata.yaml `design_note` block added by bdc9e35 also records the rationale that HR-002 was asking for. I am therefore not re-raising HR-002 in this block; the prior block remains in this file as historical record.
- No new findings this run. The task is in a clean post-resolution state awaiting fresh runs to confirm whether the trimmed wording actually exercises the lat/lon-swap failure mode the broken_wrong_bbox fixture was built for.

### 3. Changes applied this run

#### Unilateral edits
- (none — the task is in a clean post-resolution state. No tolerance loosening warranted (reference scores 1.0; brokens 0.0 / 0.5 / 0.875 are still well-separated). No prompt gift removable without judgment (the cardinal-direction wording was already trimmed in bdc9e35; further trimming to "a 4-element flat array" with no order at all would be a borderline prompt-vs-grader call I may not resolve unilaterally). No clearly-broken broken-set re-measurement; no missing vocabulary slugs.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none — no new HR items this run.)

#### Tests run
- grader on reference: 1.0 (8/8 subchecks)
- pytest: pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row (`benchmark/authoring/inventory.md` L80–103) and the
original author block above, this is an L1 data-discovery task anchored on a
single primary skill: parse a CSV-with-WKT clinic export (`POINT(lon lat)` in
EPSG:4326) and emit a small JSON inventory — `count`, overall `bbox`, and a
`count_per_subdistrict` roll-up — over a fully bundled, deterministic 80-row
fixture of Cape Town clinics. Persona: Naledi Mokoena, a City of Cape Town
Health Department analyst performing a pre-ingest sanity check before pushing
the export into a case-management pipeline. Per-subdistrict counts are
intentionally non-uniform (12/12/11/10/10/9/8/8) so an "equal split" guess
is a distinguishable failure; the author's stated expected weak-agent failure
is a lat/lon swap in the flat-list bbox.

#### Change log
Prior commits are documented in the earlier evaluator-review blocks. New since the 2026-05-28 review:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 6d352c1 | prompt-change | Tightened bbox shape disambiguation in the instruction: `(west, south, east, north)` parenthetical replaced with `([west, south, east, north])` so the list shape is explicit. | Commit msg: "Disambiguate bbox shape in dd-l1-capetown-clinics-bbox instruction — Gemma run produced semantically correct data but encoded bbox as a dict matching the parenthetical key-list reading of "(west, south, east, north)". Grader requires a 4-number list. Switch to ([west, south, east, north]) so the list shape is explicit." Diff confirms the single instruction-string change. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T18:34:00+00:00** (commit `6d352c1`, class: prompt-change). This is the most recent commit that touches the instruction; everything before is now stale.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T20:17:12Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic (gemma-4-26b-a4b-it) | 2026-05-28T22:58:33Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T23:55:16Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic (gemma-4-26b-a4b-it) | 2026-05-29T01:26:53Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic (deepseek-v4-pro) | 2026-05-29T10:55:55Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed (gemma-4-26b-a4b-it) | 2026-06-06T09:58:15Z | 1.0 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed (gemma-4-26b-a4b-it) | 2026-06-06T11:47:54Z | 1.0 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled | current (no score) |

Stale runs (pre-cutoff, not used as evidence): 28+ pre-2026-05-28T18:34 runs across opus, deepseek-v4-flash, gemma 4 26b, haiku, sonnet, hy3-preview — most scored 1.0 against the older "GeoJSON bbox convention" or "(west, south, east, north)" wording. They predate the bracket-list tightening so they cannot speak to the current prompt directly.

#### Verdict
**too-easy**

All seven scored `current` runs landed at 1.0 across a deliberately wide capability spread — frontier Claude Opus 4.7, mid-tier DeepSeek V4 Pro, and small Gemma 4 26B on both `basic` and `detailed` prompt variants. None hit the lat/lon swap that the four bbox componentwise subchecks and `broken_wrong_bbox` (0.500) were designed to surface. The proximate cause is the current instruction (`task.json:14`): `the overall bounding box ([west, south, east, north]) of all the points` names both the list shape and the cardinal-direction order explicitly, which is functionally equivalent to telling the agent the `[xmin, ymin, xmax, ymax]` layout outright. This is genuinely borderline: the output format is plain `json` (not `geojson`), so the array order is not pinned by the output schema — some disambiguation is legitimately necessary, and the 6d352c1 commit chose the bracket-list form specifically to fix a Gemma failure mode (a dict-shaped bbox derived from the prior parenthetical wording). Further trimming (e.g. dropping the cardinal-direction words and leaving just `a 4-element flat array`) would re-open the lat/lon-swap failure mode but is a prompt-vs-grader-judgment call the evaluator may not resolve unilaterally.

**CRS / format consistency (2c-CRS).** Reference output, `expected_outputs[]` (`format: json`, `crs: EPSG:4326`), and README all agree: bbox values in degrees (EPSG:4326), output is non-spatial JSON. The grader compares submission bbox against reference bbox value-for-value with a `1e-6°` per-component tolerance and performs no reprojection of either side. No one-sided reprojection, no CRS/format disagreement. Clean.

#### Specific findings
- Grader is correctly designed and stable: 8 independent subchecks (4 of them bbox componentwise), the reference still grades 1.0 (8/8) on today's code, and the three broken sets still score 0.0 / 0.5 / 0.875 matching `metadata.yaml > broken_solutions > measured_score`. No grader change recommended.
- Fixture (80 rows, non-uniform 12/12/11/10/10/9/8/8 per subdistrict) intact across all layout moves and consistent with the reference output. No data change recommended (editing `inputs/` is out of authority anyway).
- House-style audit: the instruction opened with `Quick sanity check before I push this through to case-management.` — a breezy opener that the project's house-style rules (and the `feedback_task_prompt_style` note) explicitly call out as not the desired voice. Rewritten this run to the purpose-then-ask pattern while preserving the persona, the bbox-shape disambiguation `[west, south, east, north]`, the explicit filename and key names, and every factual constraint. No new content added; voice only. Reference still grades 1.0 (8/8) on the unchanged grader.
- `analyst_notes` was missing. Authored this run per the schema in `task-evaluator-prompt.md`, with the hidden lat/lon-swap gotcha named first in `pitfalls` and the metric-CRS reprojection failure (which would explode the bbox by ~10⁶×) named second.
- `version` field was missing (implicitly v1). Bumped to `2` to mark the instruction rewrite + analyst_notes addition as the second generation of this task.
- <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" -->
  The current instruction explicitly states `[west, south, east, north]` for the bbox, which pins both the list shape and the cardinal order. All seven post-cutoff scored runs (Opus 4.7, DeepSeek V4 Pro, Gemma 4 26B basic and detailed) landed at 1.0 — the `broken_wrong_bbox` failure mode (0.500) is no longer triggerable by any reasonable agent on the current wording. The 6d352c1 commit deliberately tightened this disambiguation to avoid a Gemma dict-shape failure, so weakening it again would re-introduce that failure path. Human author decides whether to (a) keep the current wording (the output is `json` not `geojson`, the disambiguation has documented authoring rationale, and the task still tests CSV-WKT parsing + count + groupby cleanly even if the bbox subchecks have effectively become a tautology), or (b) trim further (e.g. to a 4-element flat array with no order at all, accepting that some agents will produce dict-shaped output and fail Gate 2 instead of the lat/lon-swap subchecks). Borderline; not resolved unilaterally.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: rewrote `instruction` for house style — replaced the breezy "Quick sanity check before I push this through" opener with the purpose-then-ask pattern ("I'm about to push... and I want a quick inventory check first. Can you..."). Preserved persona, bbox-shape disambiguation, filename, and key names. Re-grade on reference: 1.0 (8/8). Reason: the prior opener violated the project's house-style rules.
- `task.json`: added `version: 2` (was implicitly v1) to mark the instruction rewrite. Reason: required by Step 4's version-bump rules for any `instruction` change.
- `task.json`: authored `analyst_notes` (description / approach / pitfalls) per the evaluator-prompt schema, with the hidden lat/lon-swap gotcha named first in pitfalls. Reason: field was missing; refresh is appropriate after the house-style rewrite.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — explicit `[west, south, east, north]` bbox wording effectively pins the order; all seven current runs score 1.0; lat/lon-swap broken case no longer triggerable. Human decides whether to keep the documented disambiguation or trim further.

#### Tests run
- grader on reference: 1.0 (8/8 subchecks)
- broken solutions: wrong_format 0.0, wrong_bbox 0.5, wrong_attributes 0.875 (all match metadata)
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
- Old Gate-2 shape checks (`count` is int, `bbox` is list of 4 numbers,
  `count_per_subdistrict` is `dict[str, int]`) are now absorbed into
  defensive coercion inside each affected subcheck via new
  `_coerce_int` / `_coerce_bbox` helpers. A wrong-typed value now
  costs the relevant subcheck instead of zeroing the score; a
  dict-shaped bbox (with xmin/ymin/xmax/ymax-style keys) is recovered.
- No new subchecks added; subcheck count unchanged at 8.

### Verification
- Reference solution re-graded: 1.0 (8/8 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior reconstructions (see the 2026-05-26 / 2026-06-06 blocks):
an L1 data-discovery task that hands the agent a fully bundled, deterministic
80-row CSV-with-WKT clinic export for Cape Town (`POINT(lon lat)`, EPSG:4326)
and asks for a three-line pre-ingest inventory JSON (`count`, `bbox`,
`count_per_subdistrict`). Persona: Naledi Mokoena, City of Cape Town Health
Department analyst. Per-subdistrict counts are intentionally non-uniform
(12/12/11/10/10/9/8/8); the designed weak-agent failure is a lat/lon swap in
the flat-list bbox.

#### Change log
Prior commits are documented in the earlier evaluator-review blocks. New since
the 2026-06-06 review (commit adab85d):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 411f363 | prompt-change | Instruction: `the overall bounding box (\`[west, south, east, north]\`) of all the points` -> `the overall bounding box as a bbox array`; `analyst_notes` description/approach refreshed to match; `version` 2 -> 3. | Commit msg: "Make dd-l1-capetown-clinics-bbox harder by hiding bbox order — Order now implicit; lat/lon-swap failure mode reachable again." Resolves the 2026-06-06 block's HR-001. |
| 2026-06-06 | 363aed2 | grader-change | Benchmark-wide Gate-2 removal applied to this grader: dropped the `structural_correctness` gate and its early-return; added `_coerce_int` / `_coerce_bbox` so wrong-typed values (string counts, dict-shaped bboxes with xmin/minx/west/left key families) cost the affected subcheck instead of zeroing the score. Subcheck count unchanged at 8. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" — the gate was inconsistently hard across the 36 graders and duplicated subcheck logic. |
| 2026-06-07 | 632ad1a | grader-change | Added `weight=3.0` to the seven data-content subchecks (`count_correct`, four `bbox_*_correct`, `subdistrict_keys_match`, `subdistrict_counts_match`); `count_equals_subdistrict_sum` stays at the default 1.0. Total weight 8 -> 22. | Commit msg: "Weight data-content subchecks 3x in dd graders" — schema-clean-but-data-wrong submissions should score visibly lower than data-correct ones with minor schema drift. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:28:21+00:00** (commit `632ad1a`, class: grader-change). The most recent prompt-change is 411f363 (2026-06-06T17:12:58Z, version 3); the two later grader commits advance the cutoff past it.

#### Runs considered
| Run | Adapter / model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter (deepseek-v4-flash) | 2026-06-09T10:22:35Z | 1.0 | done | current (task_version 3) |
| run-20260608-074701Z | openrouter (deepseek-v4-flash) | 2026-06-08T10:14:18Z | 1.0 | done | current (task_version 3) |
| run-20260607-112430Z | openrouter (gemma-4-26b-a4b-it) | 2026-06-07T13:35:54Z | 1.0 | done | stale by timestamp (pre-632ad1a); task_version 3; re-graded with today's grader: **1.0** |
| run-20260606-1733Z | openrouter (gemma-4-26b-a4b-it) | 2026-06-06T18:14:16Z | 1.0 | done | stale by timestamp (pre-632ad1a); task_version 3; re-graded with today's grader: **1.0** |

Footnote: 38 further run dirs from 2026-05-12 through 2026-06-06T13:34Z were considered and marked stale — they predate the 411f363 version-3 prompt (task_version <= 2) and so cannot speak to the current wording. Among them is run-20260528-1624Z (gemma, 0.0), the dict-shaped-bbox failure that motivated the 6d352c1 disambiguation; under today's grader (post-Gate-2 `_coerce_bbox`) a dict-shaped bbox with cardinal keys would now be recovered rather than zeroed.

The two timestamp-stale-but-version-3 gemma runs saw the byte-identical version-3 instruction and input bundle; only the grader changed after them (Gate-2 removal, then weighting). Re-grading their on-disk outputs with today's grader (both 1.0) makes them valid output-level evidence for the current task, analogous to the re-grade provision in the CRS accept-list rule. With them, current evidence spans two model families (gemma-4-26b small tier, deepseek-v4-flash mid tier).

#### Verdict
**calibrated**

All four valid evidence points (2 strictly-current deepseek runs + 2 re-graded version-3 gemma runs) score 1.0 under the version-3 prompt, which deliberately hides the bbox component order ("as a bbox array"). The `too-easy` verdict does not apply: it requires the instruction to over-specify the answer, and the one remaining gift was already stripped in 411f363 precisely to re-open the lat/lon-swap failure mode. Nothing strippable is left — the filename, the three key names, and the word "bbox" are necessary contract information the agent cannot infer, and the order/CRS are now fully implicit. That small and mid-tier models still infer `[xmin, ymin, xmax, ymax]` from the word "bbox" is a fact about model knowledge, not a task defect; the grader retains full discrimination if the swap ever occurs (wrong_bbox broken set scores 0.455, cleanly separated from 0.0 / 0.864 / 1.0). An L1 floor task on which competent agents converge to 1.0 while the broken fixtures stay well-separated is operating as designed. No frontier-model run exists post-version-3, but a frontier model passing an L1 task all smaller models already pass would not change the verdict.

**CRS / format consistency (2c-CRS).** Reference output, `expected_outputs[]` (`format: json`, `crs: EPSG:4326`), and README agree: bbox values in degrees, output is non-spatial JSON. The grader compares submission bbox to reference bbox componentwise at `1e-6` deg with no reprojection of either side. Clean.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `clinic_inventory.json` | instruction (stated) | stated |
| JSON object with keys `count`, `bbox`, `count_per_subdistrict` (hard gate) | instruction (stated) | stated |
| `count` == 80 strict | derived from `capetown_clinics.csv` (80 rows) | inferable |
| bbox order `[xmin, ymin, xmax, ymax]` | "bbox array" + industry/GeoJSON convention | inferable (deliberately implicit since 411f363) |
| bbox in degrees (no reprojection), 1e-6 deg per component | input WKT is lon/lat; no reprojection requested | inferable |
| subdistrict keys verbatim from input column | input data | inferable |
| per-subdistrict values exact | input data | inferable |
| sum(per-subdistrict) == count | internal consistency, basic arithmetic | inferable |

Factual claims checked: `capetown_clinics.csv` exists in `inputs/` and matches the harness `inputs[].url`; the three key names match the reference output schema; "every health subdistrict" is consistent with the eight-subdistrict fixture. No inaccurate claims; no missing constraints.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads the CSV, parses `wkt_geom` as EPSG:4326 Points, counts rows, takes `total_bounds` (which is `[xmin, ymin, xmax, ymax]`), groups by `subdistrict`, and writes exactly the three requested keys with no extra operations, no rounding, no reprojection. Output agrees with `expected_outputs[]` and the README. No deviations.

#### Specific findings
- `metadata.yaml > broken_solutions > measured_score` was stale after the 632ad1a weighting commit: wrong_bbox now measures 0.455 (was 0.500) and wrong_attributes 0.864 (was 0.875); wrong_format unchanged at 0.0. All three remain inside their declared `expected_score_range`. Updated measured_score and the per-class arithmetic in the descriptions (unilateral, allowed; no version bump required).
- `README.md` carried two stalenesses: the input path still read `data/capetown_clinics.csv` (layout was renamed to `inputs/` in 29a9ae3) and the failure-mode/score prose still quoted the unweighted 8-subcheck arithmetic (0.500 / 0.875). Fixed both (docs-change).
- Grader behaviour after the two benchmark-wide refactors verified end-to-end this run: reference 1.0 (8/8 subchecks, total weight 22), brokens 0.0 / 0.455 / 0.864, pytest 41/41. The new `_coerce_bbox` correctly recovers dict-shaped bboxes (xmin/minx/west/left key families), so the 2026-05-28 Gemma dict-bbox failure mode now degrades gracefully instead of zeroing.
- `analyst_notes` (refreshed in 411f363) accurately describes the version-3 prompt, including the hidden-order gotcha. No refresh needed.
- Coverage tags re-validated against `coverage-vocabulary.yaml`; all slugs valid and unchanged. `coverage.yaml` timestamp refreshed.
- No new HUMAN-REVIEW items: the three new commits since the last review all carry complete rationale in their messages, and the prior HR-001 (bbox-order gift) is resolved by 411f363.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` (wrong_bbox 0.500 -> 0.455, wrong_attributes 0.875 -> 0.864) and the description arithmetic to the weighted 22-point scale. Re-grade on reference: 1.0. Reason: scores were measured before the 632ad1a subcheck-weighting commit.
- `README.md`: fixed stale `data/` input path (now `inputs/`) and updated the failure-mode score prose to the weighted values. Reason: docs drifted behind the 29a9ae3 layout move and the 632ad1a weighting change.

No `version` bump: neither edit touches the instruction, the grader, tolerances, or the input bundle.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (8/8 subchecks, weighted 22/22)
- broken solutions: wrong_format 0.0, wrong_bbox 0.455, wrong_attributes 0.864 (all inside declared ranges; measured_score refreshed)
- re-graded version-3 run outputs: 4/4 score 1.0 under today's grader
- pytest: pass (41/41)

---

## Evaluator review 2026-06-14 — weight recalibration sweep  (evaluator-commit <pending>)

**Statement of change: reviewed subcheck weights, found ALREADY CALIBRATED. No weight edits.**

### Scope
Targeted weight-only review prompted by the repo-wide 632ad1a commit, which
bluntly applied `weight=3.0` to all seven "data-content" subchecks and left
`count_equals_subdistrict_sum` at the default 1.0. Question: does that
one-size-fits-all weighting give a defensible severity ordering for *this*
data-delivery task, or does it need per-task reasoning?

### Reasoning
The central skill is parsing the CSV-with-WKT export and emitting the
three-line inventory. The three deliverables — `count`, `bbox` (4 components),
and `count_per_subdistrict` (keys + values) — are **co-equal data answers**;
none is structural or cosmetic. The only subcheck that is *not* an independent
data answer is `count_equals_subdistrict_sum`: it is a derived internal-
consistency cross-check (it passes automatically when count and the per-
subdistrict map are both right), so it is correctly the lowest weight (1.0).

So the current split already follows the required principle: central data-
content checks highest (3.0), the derived/structural consistency check lowest
(1.0). The blunt 632ad1a weighting happens to be correct here precisely because
every one of the seven 3.0-weighted subchecks is a genuine, co-equal data
answer — there is no schema-presence / CRS-metadata / geometry-type subcheck in
this grader to push down (Gate-2 shape checks were folded into coercion in
363aed2), so there is no cosmetic check sitting at an inflated 3.0.

The bbox carries 4 of the 7 weighted subchecks (12/22 of total weight). That
weighting is appropriate, not an artifact: (a) the bbox is the spatial-extent
deliverable and the designed weak-agent failure mode (lat/lon swap) lives there;
(b) the four-way componentwise split is deliberate so a *partial* bbox error
(one extreme shifted by a dropped row) is partially credited rather than
collapsed.

### Weight-change table
| Subcheck | Old | New |
|---|---|---|
| (all eight) | unchanged | unchanged |

No weights changed.

### Broken-score before -> after
| Class | Before | After | Severity note |
|---|---|---|---|
| wrong_format | 0.000 | 0.000 | unusable output (gate); most severe |
| wrong_bbox | 0.455 | 0.455 | whole bbox deliverable wrong (lat/lon swap) — meaningful drop (~0.55) |
| wrong_attributes | 0.864 | 0.864 | per-subdistrict values mis-counted; keys + count + bbox + consistency all right — light drop (~0.14) |
| reference | 1.000 | 1.000 | correct |

### Ordering check
Monotone and defensible: 0.000 < 0.455 < 0.864 < 1.000. A central deliverable
fully wrong (bbox) scores well below a within-group value miscount
(wrong_attributes), which is the intended severity. No disjoint-failure
inversion: a bbox failure loses 12/22 vs a subdistrict-values failure losing
3/22, so up-weighting bbox (already the heaviest) cannot invert the ordering.

### Prior-run re-grade summary
Re-graded the four `current` (task_version 3, post-632ad1a cutoff) run outputs
listed in the prior block — run-20260609-084636Z, run-20260608-074701Z,
run-20260607-112430Z, run-20260606-1733Z. All recorded 1.0; all re-grade 1.0
under the (unchanged) current weights. No shifts (expected — no weight edit, and
each passes every subcheck).

### Changes applied this run
- (none — weights already calibrated; no edits to grade.py, metadata.yaml, or
  README.md. status.json untouched: no edits made, empty HR list stays empty.)
