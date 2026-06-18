# Implementation notes — dc-l2-cairo-invalid-dedup

## Status
completed

## Summary
L2 data-cleaning chain on a hand-crafted Cairo parcels fixture
(EPSG:22992) — 290 input features collapse to 210 canonical
GeoParquet rows after make_valid + sliver removal + dedup +
Polygon→MultiPolygon coercion + area_m2 recompute. Reference,
grader, and three broken solutions built and verified inside the
project Docker container.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - no_make_valid: 0.625 (expected range [0.55, 0.7])
  - no_coerce: 0.875 (expected range [0.8, 0.95])
- Second-run output match: bit-identical (verified via `cp` + `diff -q`
  on `parcels_canonical.geoparquet`)
- Library tests after task: pass (32/32)

## Failure-mode coverage
- Skip make_valid: broken_no_make_valid
- Skip Polygon→MultiPolygon coercion: broken_no_coerce
- Output in the wrong CRS: broken_wrong_format
- Skip dedup: principled — Gate 2 ±5 % count tolerance
  + `no_exact_duplicate_geometries` WKB-uniqueness subcheck
- Skip sliver removal: principled — Gate 2 count tolerance
  + `no_slivers` area-threshold subcheck
- Dedup keep-rule inverted (`keep="last"`): principled —
  `parcel_id_set_matches_reference` Jaccard
  + `identifying_attributes_match_reference` (the surviving 900_000+
  ids share zero keys with the reference)
- Skip area_m2 recompute: principled — `area_m2_recomputed` subcheck
  (column vs own geometry.area)
- Wrong sliver filter (e.g., on stale area_m2): principled — Gate 2
  count + `no_slivers` subcheck

## Open issues
- [severity: low] — Bundled fixture is hand-crafted in EPSG:22992 metres
  on a 14×15 grid centred at (640000, 815000), not sliced from
  Overture. Justification: the task is intrinsically about deliberately
  corrupted parcel data — bowtie self-intersections, exact-duplicate
  geometries with conflicting attributes, sub-1 m² slivers — none of
  which Overture or OSM ships. The hand-crafted policy matches
  `crs-l2-fiji-antimeridian` and `fio-l2-cairo-mixedgeom-split`.
- [severity: low] — The bowtie I chose (swap diagonal vertices of a
  rectangle) repairs into a 2-triangle MultiPolygon under
  `shapely.make_valid`. This means a correct pipeline produces a
  MultiPolygon for those 20 parcels regardless of whether the agent
  remembered the explicit Polygon→MultiPolygon coercion step. The
  `all_multipolygon` subcheck still requires *every* feature to be
  MultiPolygon (so the 160 single-part parcels test the coercion
  step), and `broken_no_coerce` confirms a 50/210-multipolygon
  result correctly scores 7/8 = 0.875.

## Suggested prompt changes
(none)

## Inventory change proposals
(none — the inventory row also lists "Dissolve" as a secondary op,
but on second reading the persona's instruction does not describe a
group-by-dissolve — duplicates collapse by exact geometry equality,
not by attribute aggregation. I treated "deduplicate" as the central
operation and left a true `dissolve` step out, since adding it would
make the canonical answer ambiguous (which attribute drives the
group?). The persona's keep-earliest-record + recompute-area rule is
fully realised by `drop_duplicates(subset=[wkb], keep="first")`. If
the orchestrator wants a dissolve step in this task, the inventory
needs a clarifying line on the grouping key.)

## Library extensions
(none — the task uses only existing primitives:
`attribute_match`, `count_within_tolerance`,
`feature_set_equality_by_id`, `iou_with_tolerance`. Validity,
sliver, MultiPolygon-coercion, and WKB-uniqueness checks are
inline because the underlying logic is one-liners over
GeoPandas/Shapely; promoting them to the shared library felt
premature with only one task currently exercising them.)

## Runtime
~25 minutes wall-clock for authoring inside the Docker container
(input prep, reference, grader, brokens, manual inspection,
documentation). Reference output is bit-stable across reruns,
grader scores reference 1.0, brokens score 0.0 / 0.625 / 0.875,
pytest 32/32 pass.

---

## Evaluator review 2026-05-26  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

A four-step data-cleaning chain on a hand-crafted Cairo parcel
snapshot in Egypt Red Belt (EPSG:22992): make-valid, sliver removal
(<1 m²), exact-geometry dedup (keep earliest `record_seq`), and
Polygon→MultiPolygon coercion, plus an implicit `area_m2`
recompute. 290 input features collapse to 210 canonical
GeoParquet rows. The grader has two gates (format/schema, count
+ geom-type structural) and eight binary subchecks targeting each
step independently so partial pipelines land in distinct score
ranges. Inventory row (`benchmark/authoring/inventory.md` line 878)
and the README story (Reem Farouk at Egypt's Land Registry
Authority) are consistent with the author block.

#### Change log

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | ce98f1f | initial-authoring | Initial task: bundled GeoJSON fixture (290 features), generate.py, grade.py with 2 gates + 8 subchecks, 3 broken solutions (wrong_format / no_make_valid / no_coerce), README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change | Path move under benchmark/{authoring,eval} split | Commit msg: split repo layout |
| 2026-05-13 | a3a8d53 | docs-change | Path move benchmark/eval/tasks → benchmark/tasks | Commit msg: tasks: move benchmark/eval/tasks/ to benchmark/tasks/ |
| 2026-05-13 | 8915010 | docs-change | Added assets/image-prompt.md | Commit msg: add image-prompt.md to all 36 task directories |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: generate image.webp for all 36 task directories |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Commit msg: regenerate all 36 task card images |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Commit msg: regenerate task card images |
| 2026-05-13 | 9e79176 | prompt-change | Folded structured "Output schema:" bullet list into concluding prose paragraph (no semantic change) | Commit msg: merge output schema blocks into prose |
| 2026-05-14 | f5d1e91 | prompt-change | Stripped the "Egypt Red Belt throughout" line + the detailed "bundle is a mess: self-intersections / duplicates / Polygon/MultiPolygon mix / sliver scraps" enumeration; left the requested outcomes | Commit msg: strip deducible information from DC task instructions |
| 2026-05-15 | a78a513 | prompt-change | Removed "and recomputing `area_m2` from the surviving geometry" and the second-paragraph repeat of "coerce single-part Polygons to MultiPolygon" / "as a numeric value recomputed from the kept geometry" | Commit msg: strip deducible information (round 2) |
| 2026-05-16 | 9d83681 | grader-change | Made Gate 2 (structural_correctness) a soft gate — failures no longer short-circuit subchecks, so partial pipelines get proportional credit | Commit msg: make Gate 2 a soft gate for partial credit |
| 2026-05-16 | 7c812d6 | prompt-change | Tightened "exact duplicates collapsed" to "exact-duplicate geometries collapsed (by WKB equality)" to remove ambiguity over attribute-vs-geometry dedup | Commit msg: fix ambiguous task instructions — specify geometry-based (WKB) dedup |
| 2026-05-17 | 64740d0 | prompt-change | Rewrote instruction from naming defect classes ("every geometry valid, every feature a MultiPolygon, slivers below 1 m² dropped, exact-duplicate geometries collapsed (by WKB equality) keeping the earliest record_seq") to symptom-driven prose ("data is messy — produce one canonical record per parcel with clean geometry, no duplicates, and no artifact polygons. Every feature must be a MultiPolygon. When duplicates exist, keep the earliest record_seq. Discard any polygon fragments smaller than 1 m²") | Commit msg: remove answer-giving nudges — describe symptoms and desired outcomes instead of naming specific operations |
| 2026-05-17 | ca8994d | prompt-change | Dropped the trailing "EPSG:22992" from the output line in the instruction; kept the EPSG in tags and expected_outputs | Commit msg: remove remaining EPSG codes — models should infer CRS from file metadata or context |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorganization — moved data/→inputs/, reference/{generate.py,outputs}/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image artefacts→assets/. task.json input URL path updated and grade.py REFERENCE_OUT path updated. No semantic change to instruction or grader logic. | Commit msg: reorganize task folder layout |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:52:19Z (commit `ca8994d`, class: prompt-change — last prompt edit; subsequent commit 29a9ae3 is a pure folder-rename with no instruction or grader semantic change).

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:09:49Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:43:39Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:17:35Z | 0.875 | done | current |

26 earlier runs (2026-05-12 through 2026-05-17 pre-cutoff) exist but are stale relative to the post-ca8994d instruction and are not used as evidence.

#### Verdict

**calibrated**

Three current runs across three different model families (Claude Opus, DeepSeek V4 Flash, Gemma 4 26B) span 0.875–1.0, which is a sensible range for an L2 task: the two stronger models implement the chain perfectly and the weaker model executes 7 of 8 subchecks correctly. The 0.875 result is not a grader miscalibration — inspection of `runs/run-20260526-0748Z/.../outputs/parcels_canonical.geoparquet` shows the 20 bowtie parcels were "repaired" by keeping only one of the two triangles the bowtie should resolve into (area 300 m² vs reference 600 m²), producing a 6 000 m² shortfall in union area (IoU 0.9752, just under the 0.99 subcheck threshold). That is a real, observable defect in the bowtie-repair step, exactly what `geometric_extent_preserved` is designed to catch; the other 7 subchecks correctly award credit for everything the agent did do right. The grader's `try/except` around `iou_with_tolerance` (`grade.py:238–252`) also correctly handles the documented `no_make_valid` failure mode where `unary_union` raises on invalid geometries.

The prompt-stripping rounds (f5d1e91 → a78a513 → 64740d0) progressively reduced the instruction from a structured-bullet "output schema" recipe to symptom-driven prose. The current instruction still tells the agent the four output constraints (every feature MultiPolygon, no duplicates, drop fragments <1 m², keep earliest `record_seq`) — these are the *contract* the deliverable must satisfy, not the algorithmic recipe. Calling out `MultiPolygon`, the 1 m² threshold, and the keep-rule is borderline (`prompt-vs-grader-judgment`): an extremely strict reading would strip these too, but the author's choice to keep them as output expectations rather than algorithm steps is defensible and matches the persona's voice (a data steward specifying what she needs delivered).

The reference grader on the reference output scores 1.0 (all subchecks pass). pytest passes 35/35. Brokens were originally measured at 0.0 / 0.625 / 0.875 and the soft-Gate-2 change (9d83681) does not alter those for the existing brokens (no broken violates Gate 2 — wrong_format fails Gate 1; no_make_valid and no_coerce both produce 210 features of the right geometry types).

#### Specific findings

- The IoU≥0.99 subcheck `geometric_extent_preserved` correctly distinguishes a full bowtie repair (2 triangles, ~600 m² total) from a half-repair (1 triangle, ~300 m²). Calibrated.
- The instruction still names the four output constraints (MultiPolygon, drop <1 m² fragments, dedup keep earliest record_seq, recompute area implied). Per Step 2d this is borderline — the persona-voice framing keeps them as deliverable expectations rather than algorithm steps, but a sharper stripping round would push them into the README as expected-output schema only. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether the current instruction's enumeration of "every feature must be a MultiPolygon" / "keep the earliest record_seq" / "Discard any polygon fragments smaller than 1 m²" counts as legitimate output-contract framing or as an answer-giving nudge that should be stripped further. Author already did two strip rounds; current state appears to be the intentional landing point.
- `metadata.yaml` and `task.json` tag `data_scale: medium`, and the inventory coverage matrix (line 1136) lists this task under "Medium (~10⁴–10⁵ features)". The actual fixture has 290 input / 210 output features — that's ~10², which the vocabulary calls `small`. The inventory row itself (line 893) says "~10⁴ parcels" which contradicts the README's documented 290-feature fixture. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> The fixture cannot be enlarged to ~10⁴ without touching `inputs/`, which the evaluator is not permitted to edit. The task as built is small-scale; the inventory's "Medium" tag and the matrix-line membership are the items that disagree with reality.

### 3. Changes applied this run

#### Unilateral edits

(none — both findings are flagged for human review.)

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — prompt-vs-grader-judgment — borderline call on whether the current instruction's output-contract clauses (MultiPolygon, keep earliest record_seq, drop <1 m² fragments) should be stripped further.
- HR-002 — inventory-mismatch — `data_scale: medium` in `metadata.yaml` / `task.json` / inventory disagrees with the actual ~290-feature fixture (which is `small`). Resolving requires either retagging or enlarging the fixture; the latter touches `inputs/` so is out of evaluator scope.

#### Tests run

- grader on reference: 1.0 (all 8 subchecks pass, both gates pass)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

A four-step data-cleaning chain on a hand-crafted Cairo parcel snapshot
in Egypt Red Belt (EPSG:22992): make-valid, sliver removal (<1 m²),
exact-geometry dedup (keep earliest `record_seq`), and
Polygon→MultiPolygon coercion, plus an implicit `area_m2` recompute.
290 input features collapse to 210 canonical GeoParquet rows. The
grader has two gates (format/schema, count + geom-type structural) and
eight binary subchecks targeting each step independently so partial
pipelines land in distinct score ranges. The inventory row
(`benchmark/authoring/inventory.md` line 878) and the README story
(Reem Farouk at Egypt's Land Registry Authority) are consistent with
the author block.

#### Change log

This re-evaluation re-ran `git log --follow` over the task directory.
No new task-directory commits have landed since the prior evaluator
block (2026-05-26): the only commit after the folder reorganization
(`29a9ae3`) is the prior evaluator's own artefact commit `700bf69`
(class: docs-change — appended `audit/AUTHORING_HISTORY.md`,
`audit/status.json`, `coverage.yaml`; no instruction or grader change).
The full design-affecting history is unchanged from the prior block and
is reproduced below for self-containment.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | ce98f1f | initial-authoring | Initial task: bundled GeoJSON fixture (290 features), generate.py, grade.py with 2 gates + 8 subchecks, 3 broken solutions (wrong_format / no_make_valid / no_coerce), README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change | Path move under benchmark/{authoring,eval} split | Commit msg: split repo layout |
| 2026-05-13 | a3a8d53 | docs-change | Path move benchmark/eval/tasks → benchmark/tasks | Commit msg: move benchmark/eval/tasks/ to benchmark/tasks/ |
| 2026-05-13 | 8915010 | docs-change | Added assets/image-prompt.md | Commit msg: add image-prompt.md to all 36 task directories |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: generate image.webp for all 36 task directories |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Commit msg: regenerate all 36 task card images |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Commit msg: regenerate task card images |
| 2026-05-13 | 9e79176 | prompt-change | Folded structured "Output schema:" bullet list into concluding prose paragraph (no semantic change) | Commit msg: merge output schema blocks into prose |
| 2026-05-14 | f5d1e91 | prompt-change | Stripped "Egypt Red Belt throughout" + the detailed defect enumeration; left the requested outcomes | Commit msg: strip deducible information from DC task instructions |
| 2026-05-15 | a78a513 | prompt-change | Removed "and recomputing area_m2 from the surviving geometry" and a second-paragraph repeat of the coercion sentence | Commit msg: strip deducible information (round 2) |
| 2026-05-16 | 9d83681 | grader-change | Made Gate 2 (structural_correctness) a soft gate — failures no longer short-circuit subchecks | Commit msg: make Gate 2 a soft gate for partial credit |
| 2026-05-16 | 7c812d6 | prompt-change | Tightened "exact duplicates collapsed" to specify geometry-based (WKB) dedup | Commit msg: fix ambiguous task instructions — specify geometry-based (WKB) dedup |
| 2026-05-17 | 64740d0 | prompt-change | Rewrote instruction from naming defect classes to symptom-driven prose | Commit msg: remove answer-giving nudges — describe symptoms and desired outcomes |
| 2026-05-17 | ca8994d | prompt-change | Dropped trailing "EPSG:22992" from the output line; kept EPSG in tags and expected_outputs | Commit msg: remove remaining EPSG codes — models should infer CRS from file metadata |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorganization (data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image artefacts→assets/); task.json input URL + grade.py REFERENCE_OUT paths updated. No instruction/grader semantic change | Commit msg: reorganize task folder layout |
| 2026-05-26 | 700bf69 | docs-change | Prior evaluator artefacts (audit/AUTHORING_HISTORY.md review block, audit/status.json, coverage.yaml) | Commit msg: Re-evaluate dc-l2-cairo-invalid-dedup: calibrated (2 low-severity flags) |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:52:19Z (commit `ca8994d`, class: prompt-change — last prompt edit; unchanged from the prior block. Commits `29a9ae3` and `700bf69` are both docs-change and do not invalidate runs.)

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:09:49Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:43:39Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:17:35Z | 0.875 | done | current |

No new runs have been recorded since the prior evaluation (the latest is still run-20260526-0748Z). 26 earlier runs (2026-05-12 through 2026-05-17 pre-cutoff) are stale relative to the post-`ca8994d` instruction and are not used as evidence.

#### Verdict

**calibrated**

This re-evaluation independently re-ran the grader on the reference, the
three broken solutions, the gemma 0.875 submission, and pytest, and
reproduces the prior block's findings exactly. Three current runs across
three model families (Claude Opus, DeepSeek V4 Flash, Gemma 4 26B) span
0.875–1.0 — a sensible L2 gradient. The reference scores 1.0 (8/8
subchecks, both gates). The brokens score 0.0 (wrong_format),
0.625 (no_make_valid), 0.875 (no_coerce) — distinct ranges matching the
declared `metadata.yaml` `measured_score` values, so no metadata update
is needed.

Re-grading `runs/run-20260526-0748Z/.../outputs/parcels_canonical.geoparquet`
confirms the 0.875 result fails only `geometric_extent_preserved`
(union IoU 0.9752 < 0.99 threshold, `grade.py:241`); the other seven
subchecks pass. This is a real, observable bowtie-repair defect (the
agent kept one of the two triangles a bowtie should resolve into),
exactly what the IoU subcheck is designed to catch — not a grader
miscalibration.

Output-CRS / format consistency (Step 2c-CRS): the reference output is
EPSG:22992 GeoParquet, all-MultiPolygon; `expected_outputs[]`,
`task.json` tags, the README, and the inventory all agree. CRS in ==
CRS out == 22992 (no reprojection in the pipeline). The grader's Gate 1
checks `crs.to_epsg() == 22992` and its IoU computes `unary_union` on
submission and reference in the same metric CRS — no one-sided
reprojection. Clean.

The two prior HUMAN-REVIEW items (HR-001 prompt-vs-grader-judgment on
the surviving output-contract clauses; HR-002 inventory-mismatch on
`data_scale: medium` vs the actual ~290-feature `small` fixture) remain
valid and unresolved. They are re-raised here so the orchestrator's
status handoff stays current. Both are out of unilateral scope:
HR-001 is borderline by Step 2d's own definition; HR-002 can only be
fixed by retagging the inventory (outside the task dir) or enlarging the
fixture (touches `inputs/`, forbidden).

#### Specific findings

- The IoU≥0.99 subcheck `geometric_extent_preserved` (`grade.py:241`) correctly distinguishes a full bowtie repair (2 triangles, ~600 m²) from a half-repair (1 triangle, ~300 m²). Calibrated. No change.
- The instruction still names four output constraints (every feature MultiPolygon, keep earliest `record_seq`, discard fragments <1 m², no duplicates). Per Step 2d this is borderline output-contract framing vs answer-giving nudge; the author ran two strip rounds (`64740d0`, `ca8994d`) and the current state appears intentional. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether these output-contract clauses count as legitimate deliverable framing or as nudges that should be stripped further.
- `task.json` tags, `metadata.yaml`, and the inventory coverage matrix (line 1136) tag this task `data_scale: medium`, but the hand-crafted fixture has 290 input / 210 output features (~10²), which the vocabulary calls `small`. The inventory row (line 893) also says "~10⁴ parcels", contradicting the documented 290-feature fixture. `coverage.yaml` records the truthful `small`. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Resolving the tags requires retagging the inventory (outside the task dir) or enlarging the fixture (touches `inputs/`); both are out of evaluator scope.

### 3. Changes applied this run

#### Unilateral edits

(none — both findings are borderline / out-of-scope and flagged for human review. Reference grades 1.0, brokens match declared ranges, and pytest passes, so no tolerance, gift-strip, subcheck-tighten, or measured-score update is warranted.)

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — prompt-vs-grader-judgment — borderline call on whether the current instruction's output-contract clauses (MultiPolygon, keep earliest record_seq, drop <1 m² fragments) should be stripped further.
- HR-002 — inventory-mismatch — `data_scale: medium` in `metadata.yaml` / `task.json` / inventory disagrees with the actual ~290-feature fixture (`small`).

#### Tests run

- grader on reference: 1.0 (all 8 subchecks pass, both gates pass)
- grader on brokens: wrong_format 0.0, no_make_valid 0.625, no_coerce 0.875 (all in declared ranges, distinct)
- grader on run-20260526-0748Z: 0.875 (only geometric_extent_preserved fails, IoU 0.9752)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

A four-step data-cleaning chain on a hand-crafted Cairo parcel snapshot
in Egypt Red Belt (EPSG:22992): make-valid, sliver removal (<1 m²),
exact-geometry dedup (keep earliest `record_seq`), and
Polygon→MultiPolygon coercion, plus an implicit `area_m2` recompute.
290 input features collapse to 210 canonical GeoParquet rows. The
grader has two gates (format/schema, count + geom-type structural) and
eight binary subchecks targeting each step independently so partial
pipelines land in distinct score ranges. The inventory row
(`benchmark/authoring/inventory.md` line 878) and the README story
(Reem Farouk at Egypt's Land Registry Authority) are consistent with
the author block.

#### Change log

This re-evaluation re-ran `git log --follow` over the task directory.
Two new commits land since the prior evaluator block (2026-05-27):
`87f9521` (the prior evaluator's own artefact commit — docs-change) and
`622342b` (a repo-wide change adding the `task.json.version` field and
dropping the unused `metadata.yaml.prompt_version` field). The
`622342b` diff for this task is exactly the deletion of one line
(`prompt_version: 2026-05-08-a`) from `metadata.yaml`; it touches no
prompt, grader logic, tolerance, broken, or input. Per the new
evaluator prompt's bump rules (a `metadata.yaml` change that is not a
tolerance edit does not require a version bump), this is a
docs-change with no effect on the design-affecting cutoff. The full
history is reproduced for self-containment.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | ce98f1f | initial-authoring | Initial task: bundled GeoJSON fixture (290 features), generate.py, grade.py with 2 gates + 8 subchecks, 3 broken solutions (wrong_format / no_make_valid / no_coerce), README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change | Path move under benchmark/{authoring,eval} split | Commit msg: split repo layout |
| 2026-05-13 | a3a8d53 | docs-change | Path move benchmark/eval/tasks → benchmark/tasks | Commit msg: move benchmark/eval/tasks/ to benchmark/tasks/ |
| 2026-05-13 | 8915010 | docs-change | Added assets/image-prompt.md | Commit msg: add image-prompt.md to all 36 task directories |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: generate image.webp for all 36 task directories |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Commit msg: regenerate all 36 task card images |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Commit msg: regenerate task card images |
| 2026-05-13 | 9e79176 | prompt-change | Folded structured "Output schema:" bullet list into concluding prose paragraph (no semantic change) | Commit msg: merge output schema blocks into prose |
| 2026-05-14 | f5d1e91 | prompt-change | Stripped "Egypt Red Belt throughout" + the detailed defect enumeration; left the requested outcomes | Commit msg: strip deducible information from DC task instructions |
| 2026-05-15 | a78a513 | prompt-change | Removed "and recomputing area_m2 from the surviving geometry" and a second-paragraph repeat of the coercion sentence | Commit msg: strip deducible information (round 2) |
| 2026-05-16 | 9d83681 | grader-change | Made Gate 2 (structural_correctness) a soft gate — failures no longer short-circuit subchecks | Commit msg: make Gate 2 a soft gate for partial credit |
| 2026-05-16 | 7c812d6 | prompt-change | Tightened "exact duplicates collapsed" to specify geometry-based (WKB) dedup | Commit msg: fix ambiguous task instructions — specify geometry-based (WKB) dedup |
| 2026-05-17 | 64740d0 | prompt-change | Rewrote instruction from naming defect classes to symptom-driven prose | Commit msg: remove answer-giving nudges — describe symptoms and desired outcomes |
| 2026-05-17 | ca8994d | prompt-change | Dropped trailing "EPSG:22992" from the output line; kept EPSG in tags and expected_outputs | Commit msg: remove remaining EPSG codes — models should infer CRS from file metadata |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorganization (data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image artefacts→assets/); task.json input URL + grade.py REFERENCE_OUT paths updated. No instruction/grader semantic change | Commit msg: reorganize task folder layout |
| 2026-05-26 | 700bf69 | docs-change | Prior evaluator artefacts (audit/AUTHORING_HISTORY.md review block, audit/status.json, coverage.yaml) | Commit msg: Re-evaluate dc-l2-cairo-invalid-dedup: calibrated (2 low-severity flags) |
| 2026-05-27 | 87f9521 | docs-change | Second evaluator-review block appended to audit/AUTHORING_HISTORY.md; audit/status.json + coverage.yaml timestamps refreshed | Commit msg: Re-evaluate dc-l2-cairo-invalid-dedup: calibrated (2 low-severity flags) |
| 2026-05-28 | 622342b | docs-change | Repo-wide: dropped one `prompt_version: 2026-05-08-a` line from metadata.yaml (authoring-template tag with no runtime relevance). No prompt/grader/tolerance/input change. | Commit msg: Add task content versioning; drop unused prompt_version |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:52:19Z (commit `ca8994d`, class: prompt-change — last instruction edit; unchanged from prior blocks. Commits `29a9ae3`, `700bf69`, `87f9521`, and `622342b` are all docs-change and do not invalidate runs.)

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:09:49Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:43:39Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:17:35Z | 0.875 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:37:12Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:37:43Z | 0.75 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T01:36:04Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:26:03Z | 0.875 | done | current |

26 earlier runs (2026-05-12 through 2026-05-17 pre-cutoff) remain stale relative to the post-`ca8994d` instruction and are not used as evidence.

#### Verdict

**calibrated**

Seven current runs now span 0.75–1.0 across three model families. The two strong models (claude-opus-4-6, claude-opus-4-7, deepseek-v4-flash) score 1.0 across four runs; the weaker gemma-4-26b model produces 0.75 / 0.875 / 0.875 across three runs, each diagnosed by a distinct, principled subcheck failure. That is the L2 score gradient the grader was designed to produce.

Inspection of the new gemma runs:

- `run-20260527-2321Z` (score 0.75): the submission has 190 features (vs reference 210). The 20 missing parcel_ids cover the bowtie-affected base parcels (parcel_id 7, 17, 23, 35, 41, …). The agent either filtered out invalid bowties before make_valid or its sliver step dropped the half-repaired triangles, leading to 20 dropped parcels. Gate 2 (count tolerance ±5%) fires (190 vs 210 = ~9.5% short), and `geometric_extent_preserved` fires (IoU 0.9505 — geometry of 20 parcels missing). The other six subchecks (validity, all-MultiPolygon, no-slivers, no-dups, parcel_id Jaccard 0.9048 ≥ 0.95 fails, area-recompute, attributes) — five pass, parcel_id Jaccard fails because 20/210 missing ids = Jaccard 0.9048 < 0.95. So 6/8 subchecks pass — 0.75. This is a real, observable agent defect (dropping bowties instead of repairing them), exactly what the chain of subchecks is designed to catch.
- `run-20260528-0317Z` (score 0.875): same bowtie half-repair pattern as `run-20260526-0748Z` — only `geometric_extent_preserved` fails (IoU 0.9752 < 0.99). All other subchecks pass.
- `run-20260527-2016Z` and `run-20260528-0113Z` (claude-opus-4-7, both 1.0): full chain implemented correctly.

The grader continues to discriminate cleanly between full-correct, half-bowtie-repair, dropped-bowtie, and other failure modes. No subcheck is over- or under-firing.

Re-grading the reference: score 1.0 (8/8 subchecks pass, both gates pass). Re-grading the three brokens: wrong_format 0.0, no_make_valid 0.625, no_coerce 0.875 — all match the `metadata.yaml.broken_solutions.measured_score` values exactly, no measured-score refresh needed. pytest passes 41/41.

Output-CRS / format consistency (Step 2c-CRS): the reference output is EPSG:22992 GeoParquet, all-MultiPolygon; `expected_outputs[]`, `task.json` tags, the README, and the inventory all agree. CRS in == CRS out == 22992 (no reprojection in the pipeline). The grader's Gate 1 checks `crs.to_epsg() == 22992` and its IoU computes `unary_union` on submission and reference in the same metric CRS — no one-sided reprojection. Clean.

Versioning: `task.json` carries no `version` field (implicitly v1 per the new versioning rule in `622342b`). This evaluator pass makes no unilateral edit to the prompt/grader/inputs contract, so no version bump is required.

The two prior HUMAN-REVIEW items (HR-001 prompt-vs-grader-judgment on the surviving output-contract clauses; HR-002 inventory-mismatch on `data_scale: medium` vs the actual ~290-feature `small` fixture) remain valid and unresolved. They are re-raised here so the orchestrator's status handoff stays current. Both are out of unilateral scope: HR-001 is borderline by Step 2d's own definition (the author ran two strip rounds already and stopped here intentionally); HR-002 can only be fixed by retagging the inventory (outside the task dir) or enlarging the fixture (touches `inputs/`, forbidden).

The instruction has a borderline duplication between para 1 ("no duplicates, and no artifact polygons") and para 2 ("no duplicate geometries, and no artifact slivers"). I considered applying Step 4's "Tighten redundant statements" rule, but the two paragraphs are not a clean mechanical duplicate: para 1 phrases the constraints as story-level outcomes for the data steward persona, while para 2 enumerates them as schema-level invariants the deliverable must satisfy. Either alone would be defensible, but choosing which to keep is a judgment call already covered by HR-001 (the broader prompt-vs-grader-judgment flag on this task). Leaving the wording as-is rather than re-opening a settled judgment call.

#### Specific findings

- The IoU≥0.99 subcheck `geometric_extent_preserved` (`grade.py:241`) discriminates cleanly between (a) full bowtie repair (1.0), (b) half bowtie repair → 1 triangle of 2 (~0.9752), and (c) dropped bowties → 20 parcels missing (~0.9505). Calibrated. No change.
- Gate 2 (count tolerance ±5%) fires correctly on a 20-parcel drop (190 vs 210 = ~9.5% short). The soft-Gate-2 design (`9d83681`) means this does not zero the score; the surviving subchecks award partial credit. Calibrated.
- The instruction still names four output constraints (every feature MultiPolygon, keep earliest `record_seq`, discard fragments <1 m², no duplicates). Per Step 2d this is borderline output-contract framing vs answer-giving nudge; the author ran two strip rounds (`64740d0`, `ca8994d`) and the current state appears intentional. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether these output-contract clauses count as legitimate deliverable framing or as nudges that should be stripped further.
- `task.json` tags, `metadata.yaml`, and the inventory coverage matrix (line 1136) tag this task `data_scale: medium`, but the hand-crafted fixture has 290 input / 210 output features (~10²), which the vocabulary calls `small`. The inventory row (line 893) also says "~10⁴ parcels", contradicting the documented 290-feature fixture. `coverage.yaml` records the truthful `small`. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Resolving the tags requires retagging the inventory (outside the task dir) or enlarging the fixture (touches `inputs/`); both are out of evaluator scope.

### 3. Changes applied this run

#### Unilateral edits

(none — both findings are borderline / out-of-scope and flagged for human review. Reference grades 1.0, brokens match declared ranges, and pytest passes, so no tolerance, gift-strip, subcheck-tighten, measured-score update, or version bump is warranted.)

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — prompt-vs-grader-judgment — borderline call on whether the current instruction's output-contract clauses (MultiPolygon, keep earliest record_seq, drop <1 m² fragments) should be stripped further.
- HR-002 — inventory-mismatch — `data_scale: medium` in `metadata.yaml` / `task.json` / inventory disagrees with the actual ~290-feature fixture (`small`).

#### Tests run

- grader on reference: 1.0 (all 8 subchecks pass, both gates pass)
- grader on brokens: wrong_format 0.0, no_make_valid 0.625, no_coerce 0.875 (all match declared `measured_score`)
- grader on run-20260527-2321Z (new gemma 0.75): 0.75 (Gate 2 fail + `parcel_id_set_matches_reference` Jaccard 0.9048 fail + `geometric_extent_preserved` IoU 0.9505 fail; 6/8 subchecks pass — the soft-Gate-2 design correctly awards partial credit for dropping 20 bowtie parcels)
- grader on run-20260528-0317Z (new gemma 0.875): 0.875 (only `geometric_extent_preserved` IoU 0.9752 fails — same bowtie half-repair as run-20260526-0748Z)
- pytest: pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <to-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

A four-step data-cleaning chain on a hand-crafted Cairo parcel snapshot
in Egypt Red Belt (EPSG:22992): make-valid, sliver removal (<1 m²),
exact-geometry dedup (keep earliest `record_seq`), and
Polygon→MultiPolygon coercion, plus an implicit `area_m2` recompute.
290 input features collapse to 210 canonical GeoParquet rows. The
grader has two gates (format/schema, count + geom-type structural) and
a checklist of binary subchecks targeting each step independently so
partial pipelines land in distinct score ranges. The inventory row
(`benchmark/authoring/inventory.md` line 878) and the README story
(Reem Farouk at Egypt's Land Registry Authority) are consistent with
the author block.

#### Change log

One new commit lands since the prior evaluator block (2026-05-28
13:46): `05aabd6` — a repo-wide grader-change that softened the CRS
hard-fail on 21 graders (this one included) to two subchecks. Per the
new policy, Gate 1 only fails when no CRS can be parsed; a
wrong-but-parseable CRS is docked via `crs_is_canonical` and
`crs_in_meaningful_set`. For this task the grader gained
`CANONICAL_EPSG = 22992` and `MEANINGFUL_EPSGS = {22992}` module
constants, swapped the old `crs.to_epsg() == 22992` check for a call
to `geo_grading.grade_crs_soft`, and appended the two CRS subchecks
to the report. The full design-affecting history is reproduced for
self-containment.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | ce98f1f | initial-authoring | Initial task: bundled GeoJSON fixture (290 features), generate.py, grade.py with 2 gates + 8 subchecks, 3 broken solutions (wrong_format / no_make_valid / no_coerce), README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change | Path move under benchmark/{authoring,eval} split | Commit msg: split repo layout |
| 2026-05-13 | a3a8d53 | docs-change | Path move benchmark/eval/tasks → benchmark/tasks | Commit msg: move benchmark/eval/tasks/ to benchmark/tasks/ |
| 2026-05-13 | 8915010 | docs-change | Added assets/image-prompt.md | Commit msg: add image-prompt.md to all 36 task directories |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: generate image.webp for all 36 task directories |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX schnell | Commit msg: regenerate all 36 task card images |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Commit msg: regenerate task card images |
| 2026-05-13 | 9e79176 | prompt-change | Folded structured "Output schema:" bullet list into concluding prose paragraph (no semantic change) | Commit msg: merge output schema blocks into prose |
| 2026-05-14 | f5d1e91 | prompt-change | Stripped "Egypt Red Belt throughout" + the detailed defect enumeration; left the requested outcomes | Commit msg: strip deducible information from DC task instructions |
| 2026-05-15 | a78a513 | prompt-change | Removed "and recomputing area_m2 from the surviving geometry" and a second-paragraph repeat of the coercion sentence | Commit msg: strip deducible information (round 2) |
| 2026-05-16 | 9d83681 | grader-change | Made Gate 2 (structural_correctness) a soft gate — failures no longer short-circuit subchecks | Commit msg: make Gate 2 a soft gate for partial credit |
| 2026-05-16 | 7c812d6 | prompt-change | Tightened "exact duplicates collapsed" to specify geometry-based (WKB) dedup | Commit msg: fix ambiguous task instructions — specify geometry-based (WKB) dedup |
| 2026-05-17 | 64740d0 | prompt-change | Rewrote instruction from naming defect classes to symptom-driven prose | Commit msg: remove answer-giving nudges — describe symptoms and desired outcomes |
| 2026-05-17 | ca8994d | prompt-change | Dropped trailing "EPSG:22992" from the output line; kept EPSG in tags and expected_outputs | Commit msg: remove remaining EPSG codes — models should infer CRS from file metadata |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorganization (data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image artefacts→assets/); task.json input URL + grade.py REFERENCE_OUT paths updated. No instruction/grader semantic change | Commit msg: reorganize task folder layout |
| 2026-05-26 | 700bf69 | docs-change | Prior evaluator artefacts | Commit msg: Re-evaluate dc-l2-cairo-invalid-dedup |
| 2026-05-27 | 87f9521 | docs-change | Second evaluator-review block + status.json + coverage.yaml refresh | Commit msg: Re-evaluate dc-l2-cairo-invalid-dedup |
| 2026-05-28 | 622342b | docs-change | Dropped one `prompt_version: 2026-05-08-a` line from metadata.yaml (no runtime effect) | Commit msg: Add task content versioning; drop unused prompt_version |
| 2026-05-28 | 50e109e | docs-change | Third evaluator-review block + status.json + coverage.yaml refresh | Commit msg: Re-evaluate dc-l2-cairo-invalid-dedup |
| 2026-05-28 | 05aabd6 | grader-change | Soft-CRS policy: Gate 1 no longer hard-fails on CRS mismatch. Added `CANONICAL_EPSG = 22992`, `MEANINGFUL_EPSGS = {22992}`, call to `grade_crs_soft`, and two CRS subchecks (`crs_is_canonical`, `crs_in_meaningful_set`). Subcheck count went from 8 to 10 | Commit msg: Soften CRS hard-fail to subcheck deductions across 21 graders |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-28T19:02:57Z (commit `05aabd6`, class: grader-change — the soft-CRS refactor). The cutoff advanced from `ca8994d` (the last instruction edit) to this grader-change because subcheck count and broken scores moved. All earlier evaluator-artefact commits remain docs-change and do not bound the cutoff.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T19:44:08Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:35:33Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-28T23:45:41Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:22:37Z | 0.9 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T10:13:06Z | 1.0 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:41:51Z | 1.0 | done | current |

Runs from `run-20260527-2016Z` through `run-20260528-0317Z` (4 runs, scores 0.75–1.0) are now stale relative to the post-`05aabd6` grader and are not used as evidence. They scored against the 8-subcheck grader; the current grader has 10 subchecks, and the wrong-CRS path returns a fundamentally different score (0.8 instead of 0). Earlier pre-cutoff runs remain stale for the same reason as in prior blocks.

Two model-side runs (`run-20260606-0953Z` failed, `run-20260606-1334Z` cancelled) are noted but not used as evidence.

#### Verdict

**calibrated**

Six current runs across three model families (Claude Opus, Gemma 4 26B, DeepSeek V4 Pro) span 0.9–1.0. Five score 1.0 — including both Claude Opus runs, the DeepSeek run, one Gemma basic run, and the new Gemma detailed run — and one Gemma run scores 0.9, indicating the soft-CRS grader is no longer over-penalising the wrong-CRS failure mode and the chain itself is now well-implemented by every model family in the sweep. The score distribution is narrow, but the grader continues to discriminate cleanly on the broken solutions (0.7 / 0.8 / 0.9 across the three brokens after the refactor), and one current run still lands below 1.0, so this is not a candidate for `too-easy`.

Inspection of `run-20260529-0109Z` (gemma 0.9): all geometric subchecks and CRS subchecks pass; only `geometric_extent_preserved` fails (IoU 0.9752 < 0.99). This is the same bowtie half-repair pattern documented in prior blocks for older Gemma runs — a real, observable defect, exactly what the IoU subcheck is designed to catch. The score moved from 0.875 under the old 8-subcheck grader to 0.9 under the new 10-subcheck grader (8/10 vs 7/8), which is the arithmetic effect of adding two CRS subchecks the agent passes.

Re-grading the reference output: 1.0 (10/10 subchecks pass, both gates pass). Re-grading the three brokens under the soft-CRS grader gave 0.8 / 0.7 / 0.9 (wrong_format / no_make_valid / no_coerce), which differs from the values recorded in `metadata.yaml.broken_solutions.measured_score` (still 0.0 / 0.625 / 0.875). This evaluator pass refreshes the `measured_score` and `expected_score_range` values to the post-`05aabd6` reality, and refreshes the corresponding broken-solution descriptions to explain the new CRS subcheck behaviour. pytest passes 41/41.

The README's failure-mode section also still cites the pre-soft-CRS Gate 1 behaviour ("Gate 1's `crs.to_epsg() == 22992` check rejects the file") and the pre-refactor broken scores (0.625, 0.875, 0.0). This evaluator pass updates the README's failure-mode 3 narrative and the score numbers throughout. The `metadata.yaml` note on Gate 1 is similarly stale and is refreshed.

Output-CRS / format consistency (Step 2c-CRS): the reference output is EPSG:22992 GeoParquet, all-MultiPolygon; `expected_outputs[]`, `task.json` tags, the README, and the inventory all agree. CRS in == CRS out == 22992. The grader's soft-CRS policy now reprojects a submission with a parseable-but-wrong CRS back to 22992 before the geometric subchecks, which is a both-sides-same-transform (the reference is already in 22992), not a one-sided paper-over. Clean.

Versioning: `task.json` carries no `version` field (implicitly v1). This evaluator pass does not change the prompt, the inputs, or the grader logic — the only `task.json` edit is adding `analyst_notes` (human-facing, not bump-required) and the only grader-side change is the upstream `05aabd6` commit, which already updated the grader and which is part of the design-affecting cutoff. No version bump is required from this evaluator pass.

Authoring `analyst_notes`: previously missing. Added per Step 4. The note describes the chain's hidden gotcha (bowtie polygons report shapely .area of 0, so a naive area-based sliver filter silently deletes them rather than triggering a repair), enumerates the five pipeline steps in plain prose, and lists five pitfalls covering the bowtie filter, half-bowtie repair, dedup keep-rule inversion, stale area_m2 carry-over, and wrong-CRS output.

The two prior HUMAN-REVIEW items (HR-001 prompt-vs-grader-judgment on the surviving output-contract clauses; HR-002 inventory-mismatch on `data_scale: medium` vs the actual ~290-feature `small` fixture) remain valid and unresolved. They are re-raised so the orchestrator's status handoff stays current. Both are out of unilateral scope: HR-001 is borderline by Step 2d's own definition (the author ran two strip rounds already and stopped here intentionally); HR-002 can only be fixed by retagging the inventory (outside the task dir) or enlarging the fixture (touches `inputs/`, forbidden).

#### Specific findings

- The soft-CRS refactor (commit `05aabd6`) changed the broken-solution scores: wrong_format 0.0 → 0.8, no_make_valid 0.625 → 0.7, no_coerce 0.875 → 0.9. `metadata.yaml.broken_solutions.measured_score` and `expected_score_range` updated this pass. Broken descriptions rewritten to explain the new soft-CRS path.
- README failure-mode 3 (wrong CRS) cited the now-stale `Gate 1's crs.to_epsg() == 22992` reject path; rewritten to describe the soft-CRS reprojection + two-subcheck deduction. Failure-mode 1 and 2 broken scores updated (0.625 → 0.7, 0.875 → 0.9). "Expected weak-agent failure mode" score line updated to 0.7 and the calibration triangle (1.0 / 0.0 / 0.875) updated to (1.0 / 0.8 / 0.9).
- `metadata.yaml` Gate 1 note updated to mention the soft-CRS policy and the `crs_is_canonical` / `crs_in_meaningful_set` subchecks.
- `task.json.analyst_notes` authored (was missing).
- The instruction still names four output constraints (every feature MultiPolygon, keep earliest `record_seq`, discard fragments <1 m², no duplicates). Per Step 2d this is borderline output-contract framing vs answer-giving nudge; the author ran two strip rounds (`64740d0`, `ca8994d`) and the current state appears intentional. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether these output-contract clauses count as legitimate deliverable framing or as nudges that should be stripped further.
- `task.json` tags, `metadata.yaml`, and the inventory coverage matrix (line 1136) tag this task `data_scale: medium`, but the hand-crafted fixture has 290 input / 210 output features (~10²), which the vocabulary calls `small`. The inventory row (line 893) also says "~10⁴ parcels", contradicting the documented 290-feature fixture. `coverage.yaml` records the truthful `small`. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Resolving the tags requires retagging the inventory (outside the task dir) or enlarging the fixture (touches `inputs/`); both are out of evaluator scope.

### 3. Changes applied this run

#### Unilateral edits

- `metadata.yaml`: refreshed `broken_solutions.measured_score` and `expected_score_range` for all three brokens to match the post-`05aabd6` grader (0.8 / 0.7 / 0.9), and rewrote the three description blocks plus the Gate 1 note to explain the soft-CRS subcheck deductions. Re-grade on reference: 1.0. Reason: explicit Step 4 item ("Update `metadata.yaml > broken_solutions > measured_score` to the current grader's score on each broken set, with one re-run").
- `README.md`: rewrote failure-mode 3 (wrong CRS) to describe the soft-CRS reprojection + two-subcheck deduction instead of the now-stale Gate 1 reject, updated failure-mode 1 and 2 broken-solution scores (0.625 → 0.7, 0.875 → 0.9), and updated the "Expected weak-agent failure mode" calibration line to 0.7 and the (1.0 / 0.8 / 0.9) triangle. Re-grade on reference: 1.0. Reason: README documented the pre-refactor behaviour; this is a docs-only refresh.
- `task.json`: authored `analyst_notes` (description + 6-step approach + 5 pitfalls covering the bowtie sliver-filter gotcha, half-bowtie repair, dedup keep-rule, stale area_m2, and wrong-CRS output). Re-grade on reference: 1.0. Reason: explicit Step 4 item ("Author or refresh `analyst_notes` in `task.json`. If the field is missing, write it.") — human-facing only, no version bump required.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp; slugs unchanged from prior pass.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — prompt-vs-grader-judgment — borderline call on whether the current instruction's output-contract clauses (MultiPolygon, keep earliest record_seq, drop <1 m² fragments) should be stripped further.
- HR-002 — inventory-mismatch — `data_scale: medium` in `metadata.yaml` / `task.json` / inventory disagrees with the actual ~290-feature fixture (`small`).

#### Tests run

- grader on reference: 1.0 (10/10 subchecks pass, both gates pass)
- grader on brokens (post-refactor): wrong_format 0.8, no_make_valid 0.7, no_coerce 0.9 (now matches the refreshed `measured_score` values)
- grader on run-20260529-0109Z (gemma 0.9): 0.9 (only `geometric_extent_preserved` IoU 0.9752 fails — same bowtie half-repair pattern, scored 0.875 under the old grader and 0.9 under the new one due to two added passing CRS subchecks)
- pytest: pass (41/41)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)`. (Gate 2 here did not
  early-return — subchecks already ran — but the gate still collapsed
  the score to 0.)
- Feature-count tolerance (±5%) migrated to a new
  `feature_count_within_tolerance` subcheck.
- Geometry-type uniformity (Polygon/MultiPolygon) migrated to a new
  `geometry_type_polygonal` subcheck. (The stricter `all_multipolygon`
  subcheck is kept as a separate signal.)
- Null/empty-geometry check migrated to a new `no_null_or_empty_geometry`
  subcheck.
- Subcheck total: 10 → 13.

### Verification
- Reference solution re-graded: 1.0 (13/13 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

A four-step data-cleaning chain on a hand-crafted Cairo parcel snapshot
in Egypt Red Belt (EPSG:22992): make-valid, sliver removal (<1 m²),
exact-geometry dedup (keep earliest `record_seq`), and
Polygon→MultiPolygon coercion, plus an implicit `area_m2` recompute.
290 input features collapse to 210 canonical GeoParquet rows. Since the
gate-2 removal the grader has one hard gate (`format_schema_valid`) and
13 subchecks targeting each step independently so partial pipelines
land in distinct score ranges. The inventory row
(`benchmark/authoring/inventory.md` line 878) and the README story
(Reem Farouk at Egypt's Land Registry Authority) are consistent with
the author block.

#### Change log

Two design-affecting commits land since the prior evaluator block
(2026-06-06 14:52): `363aed2` (repo-wide gate-2 removal, documented in
the "Manual cleanup" section above) and `c749e57` (repo-wide 3x
weighting of data-content subchecks). Earlier history is unchanged from
the prior blocks; only the new commits are tabulated here.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | b17a541 | docs-change | Fourth evaluator-review block; metadata broken-score refresh to soft-CRS values (0.8/0.7/0.9); analyst_notes authored; README soft-CRS refresh | Commit msg: Re-evaluate dc-l2-cairo-invalid-dedup: refresh broken scores + analyst_notes after soft-CRS refactor |
| 2026-06-06 | 363aed2 | grader-change | Removed `Gate("structural_correctness", ...)`; count tolerance, polygonal-type uniformity, and null/empty-geometry checks migrated to subchecks (`feature_count_within_tolerance`, `geometry_type_polygonal`, `no_null_or_empty_geometry`). Subcheck total 10 → 13 | Commit msg: Drop Gate 2 from graders; one hard gate, rest are subchecks |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to 8 data-content subchecks (count, null/empty, slivers, dup-WKB, parcel-id set, area-recompute, attributes, extent IoU); 5 structural/CRS subchecks stay weight 1. Score = passed weight / total weight (29) | Commit msg: Weight data-content subchecks 3x across all categories |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-06-07T18:32:38Z (commit `c749e57`, class: grader-change - the 3x weighting changes every score, so all earlier runs are stale evidence for calibration).

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T09:20:58Z | 1.0 | done | current |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:07:08Z | 1.0 | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T13:22:23Z | 0.690 | done | stale (pre-cutoff; score.json regenerated under the weighted grader) |

All 43 earlier runs are stale relative to the post-`c749e57` grader. The stale gemma run is still informative as a footnote: its submission skipped dedup entirely (260 features, 50 duplicate WKB groups, parcel_id Jaccard 0.81), and the weighted grader prices that at 20/29 ≈ 0.69 - the count, dup-WKB, and id-set subchecks (3 weight points each) all fire. Both runs in this evaluator pass's table predate the v1 → v2 instruction rewrite applied below, so they will read as version-stale in the UI going forward; they were scored against the identical grader and contract, only the prompt register changed.

#### Verdict

**insufficient-evidence**

Only two post-cutoff runs exist and both come from one model family
(deepseek-v4-flash, basic + detailed prompt variants), both scoring
1.0 with byte-level-correct outputs (210 features, all checks pass).
The grader itself still discriminates on the broken sets (0.86 / 0.93
/ 0.97, distinct failure signatures), and the stale-but-rescored gemma
run shows a skip-dedup pipeline landing at 0.69, so there is no
concrete sign of miscalibration - there is simply not yet a
multi-family evidence base under the weighted grader.

#### Prompt information audit

| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `parcels_canonical.geoparquet` (GeoParquet) | instruction, output paragraph | stated |
| required columns parcel_id, parcel_class, district, area_m2 | instruction ("exactly these columns") | stated (but see HR-003: reference keeps `record_seq` too) |
| output CRS EPSG:22992 (canonical + meaningful-set subchecks) | not stated; input file is EPSG:22992 and GeoParquet round-trips CRS | inferable (preserve-input-CRS convention; deliberate omission per `ca8994d`) |
| every feature MultiPolygon | instruction | stated |
| no invalid geometries | instruction | stated |
| no null/empty geometries | instruction | stated |
| no duplicate WKB geometries | instruction ("no duplicate geometries") | stated |
| dedup keep-rule: earliest `record_seq` | instruction | stated |
| no fragments < 1 m² | instruction | stated |
| feature count within ±5% of 210 | follows from doing the three drop/collapse steps right | inferable |
| parcel_id set ≈ reference (Jaccard ≥ 0.95) | follows from keep-earliest rule (originals carry the real ids) | inferable |
| area_m2 ≈ own geometry.area (≥95% rows, 1e-3 rel) | not stated since `a78a513`; a canonical record's stored area must agree with its repaired geometry | inferable (domain expertise; deliberately stripped as deducible) |
| attributes match reference per parcel_id | follows from keep-earliest rule | inferable |
| union IoU ≥ 0.99 vs reference | non-mutation invariant (clean, don't move geometry) | inferable |

Factual claims checked: `cairo_parcels_legacy.geojson` exists in
`inputs/` with columns parcel_id, record_seq, parcel_class, district,
area_m2 (EPSG:22992, 290 features, Polygon+MultiPolygon mix) -
matches the instruction's filename, the `record_seq` reference, and
the requested output columns. One mismatch: the instruction's
"exactly these columns" contradicts the reference output schema
(HR-003 below).

#### Reference faithfulness

`reference/solution/generate.py` implements the requested chain
(make-valid keeping polygonal parts, sliver drop at 1 m², WKB dedup
keeping lowest `record_seq`, MultiPolygon coercion, area recompute,
CRS preserved) - faithful on the operations. One schema deviation:
the instruction says the output "must contain exactly these columns:
parcel_id (the join key), parcel_class, district, and area_m2", but
`generate.py:128-130` emits `record_seq` as a fifth attribute column,
and the README's output section ("Schema preserved") documents that
five-column schema. The "exactly" wording entered at `9e79176`
(2026-05-13, a supposedly no-semantic-change prose merge of the
original "Required columns:" bullet); the reference was never
regenerated to match. The grader only checks the four required
columns as a subset (`grade.py:39,81`), so both an agent that follows
the prompt literally (drops `record_seq`) and one that mirrors the
reference score identically - no run has ever been mis-scored by
this - but reference and prompt disagree on the contract.
<!-- HUMAN-REVIEW id="HR-003" category="reference-prompt-mismatch" severity="med" -->
Decide which side is canonical: (a) regenerate
`reference/solution/outputs/` without `record_seq` (edit
`generate.py:128-130`, re-run `_make_brokens.py`, update the README
schema line, re-measure broken scores, bump `version`), or (b) drop
the word "exactly" from the instruction so extra carried-over columns
are permitted (prompt edit, bump `version`). If "exactly" stays, a
grader subcheck enforcing the exact column set would make the claim
real; today it is unenforced.

#### Specific findings

- The two new grader commits (`363aed2`, `c749e57`) left the reference at 1.0 but moved the broken scores from the documented 0.8 / 0.7 / 0.9 to 0.931 (wrong_format) / 0.862 (no_make_valid) / 0.966 (no_coerce). `metadata.yaml` measured_score / expected_score_range and descriptions refreshed this pass; README failure-mode scores refreshed.
- Part of the no_make_valid move is environment drift, not just weighting: under GEOS 3.13.1 (shapely 2.1.2) `unary_union` no longer raises TopologyException on the invalid bowties - it resolves the self-intersections, so `geometric_extent_preserved` now passes (union IoU 1.0000) for the skip-make-valid broken. The skip-make-valid detectors are now `all_geometries_valid` (weight 1) and `no_slivers` (weight 3). metadata note and README updated to record both behaviours.
- The 3x weighting inverted part of this task's price list: the chain's headline skills sit in weight-1 subchecks (`all_geometries_valid`, `all_multipolygon`, the two CRS checks) while their downstream symptoms sit in weight-3 subchecks. Skipping the entire make-valid step now costs 4/29 ≈ 0.14 (was 3/10), and skipping coercion costs 1/29 ≈ 0.03. The brokens still order correctly and distinctly, but the band compressed to 0.86–0.97. <!-- HUMAN-REVIEW id="HR-004" category="grader-miscalibration-suspected" severity="low" --> Decide whether the weight-1 status of `all_geometries_valid` / `all_multipolygon` under the repo-wide 3x data-content policy under-prices this task's central skills (a no-coerce submission now scores 0.97). Evidence is structural, not run-based - no current run has been mis-ranked - hence low severity.
- Instruction rewritten to house style this pass: dropped the em-dash, the bare `parcels_canonical.geoparquet.` fragment, and the para-1/para-2 duplication of the no-duplicates/no-slivers constraints; named the input by its actual filename (`cairo_parcels_legacy.geojson`); added a one-sentence purpose opener consistent with the README story. All constraints preserved verbatim (earliest `record_seq`, 1 m² threshold, MultiPolygon, exact-columns list, no-null/invalid/duplicate/sliver invariants); the deliberate CRS omission is preserved. `version` 1 → 2.
- The instruction still names four output constraints (every feature MultiPolygon, keep earliest `record_seq`, discard fragments <1 m², no duplicates). Per Step 2d this is borderline output-contract framing vs answer-giving nudge; the author ran two strip rounds (`64740d0`, `ca8994d`) and the current state appears intentional. The house-style rewrite preserved them unchanged. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Decide whether these output-contract clauses count as legitimate deliverable framing or as nudges that should be stripped further.
- `task.json` tags, `metadata.yaml`, and the inventory coverage matrix tag this task `data_scale: medium`, but the hand-crafted fixture has 290 input / 210 output features (~10²), which the vocabulary calls `small`. The inventory row also says "~10⁴ parcels". `coverage.yaml` records the truthful `small`. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Resolving the tags requires retagging the inventory (outside the task dir) or enlarging the fixture (touches `inputs/`); both are out of evaluator scope.

### 3. Changes applied this run

#### Unilateral edits

- `task.json`: house-style instruction rewrite (purpose-then-ask opener, full sentences, no em-dash, real filename, duplication tightened; all constraints and the deliberate CRS omission preserved) and `version: 2` added. Re-grade on reference: 1.0. Reason: Step 4 house-style rule.
- `metadata.yaml`: refreshed `broken_solutions` measured_score / expected_score_range to the weighted-grader values (0.931 / 0.862 / 0.966), rewrote the three descriptions with weight arithmetic, and updated the `iou_with_tolerance` note for the GEOS ≥ 3.13 union behaviour. Re-grade on reference: 1.0. Reason: explicit Step 4 measured-score refresh.
- `README.md`: failure-mode scores and detection narratives updated for the weighted grader and GEOS 3.13 (no TopologyException path); "breaches Gate 2" wording replaced with the post-`363aed2` subcheck names; stale `data/` input path corrected to `inputs/`. Reason: docs were stale against two repo-wide grader refactors.
- `coverage.yaml`: refreshed `evaluator_run_at`; slugs unchanged.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 - prompt-vs-grader-judgment - borderline call on whether the output-contract clauses should be stripped further.
- HR-002 - inventory-mismatch - `data_scale: medium` tags vs the actual ~290-feature `small` fixture.
- HR-003 - reference-prompt-mismatch - instruction says "exactly these columns" (4 attributes) but the reference output and README schema keep `record_seq` as a fifth; pick a side, regenerate or reword, and bump `version`.
- HR-004 - grader-miscalibration-suspected - repo-wide 3x weighting leaves this task's central skills (make-valid, coercion, CRS) in weight-1 subchecks, compressing broken scores to 0.86–0.97.

#### Tests run

- grader on reference: 1.0 (gate passes, 13/13 subchecks, after all edits)
- grader on brokens (weighted): wrong_format 0.931, no_make_valid 0.862, no_coerce 0.966 (recorded in metadata.yaml)
- pytest: pass (41/41)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent

A four-step data-cleaning chain on a hand-crafted Cairo parcel snapshot
in Egypt Red Belt (EPSG:22992): make-valid, sliver removal (<1 m2),
exact-geometry dedup (keep earliest `record_seq`), and
Polygon -> MultiPolygon coercion, plus an implicit `area_m2` recompute.
290 input features collapse to 210 canonical GeoParquet rows. The grader
has one hard gate (`format_schema_valid`) and 13 subchecks targeting
each step independently so partial pipelines land in distinct score
ranges.

#### Change in this block

Per-task reasoned subcheck weights replace the repo-wide blunt 3x
data-content weighting (05b389b / c749e57). That one-size-fits-all
policy left this task's central cleaning skills
(`all_geometries_valid`, `all_multipolygon`, both CRS checks) stranded
at weight 1 while their downstream symptoms sat at weight 3 - the
HR-004 inversion. The new weights price each subcheck by how central
the operation it detects is to the task. Grading-only change: no
task.json version bump, no check-logic / threshold / gate change, only
`weight=` values in grade.py.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff unchanged: 2026-06-07T18:32:38Z (commit
  `c749e57`). This weight recalibration is a grading-only change at the
  current task version (v2), so the two post-cutoff runs stay
  comparable and are re-graded below.

#### Weight changes (subcheck: old -> new)

| Subcheck | Old | New | Rationale |
|---|---|---|---|
| all_geometries_valid | 1.0 | 4.0 | Central: primary detector of the make-valid step. Was stranded at weight 1 (HR-004). |
| all_multipolygon | 1.0 | 4.0 | Central: the Polygon->MultiPolygon coercion, one of the four named ops. Was weight 1 (HR-004) so skipping coercion cost ~0.03. |
| no_slivers | 3.0 | 4.0 | Central: sliver-removal op. |
| no_exact_duplicate_geometries | 3.0 | 4.0 | Central: primary detector of the dedup op. |
| no_null_or_empty_geometry | 3.0 | 2.0 | Supporting geometry-integrity invariant; a correct pipeline never emits these. |
| area_m2_recomputed | 3.0 | 2.0 | Implicit attribute-recompute step; real but secondary to geometry. |
| feature_count_within_tolerance | 3.0 | 3.0 | Unchanged: broad symptom detector for a skipped drop/collapse step. |
| parcel_id_set_matches_reference | 3.0 | 3.0 | Unchanged: dedup keep-rule correctness. |
| identifying_attributes_match_reference | 3.0 | 3.0 | Unchanged: dedup keep-rule (keep-earliest) correctness. |
| geometric_extent_preserved | 3.0 | 3.0 | Unchanged: non-mutation invariant (no buffer/simplify/half-repair). |
| geometry_type_polygonal | 1.0 | 1.0 | Unchanged: structural stray-type guard, subsumed by all_multipolygon. |
| crs_is_canonical | 1.0 | 1.0 | Unchanged: cosmetic; CRS is reprojectable, geometry work intact. |
| crs_in_meaningful_set | 1.0 | 1.0 | Unchanged: cosmetic. |

Total weight: 29 -> 35.

#### Broken scores (before -> after)

| Broken | Before | After | Fails | Severity note |
|---|---|---|---|---|
| wrong_format | 0.931 | 0.943 | crs_is_canonical, crs_in_meaningful_set | Cosmetic: only the output projection is wrong; all geometric cleaning correct. Correctly the highest broken. |
| no_coerce | 0.966 | 0.886 | all_multipolygon | Skips a central output op. Was a near-free 0.97; now a meaningful ~0.11 drop (fixes the core HR-004 symptom). |
| no_make_valid | 0.862 | 0.771 | all_geometries_valid, no_slivers | Skips the central make-valid step (two central detectors fire). Correctly the lowest broken. |

Ordering is now sensible and tracks error severity: cosmetic CRS slip
(0.94) > one central op skipped, symptom-limited (no_coerce 0.89) >
central op skipped with multiple detectors (no_make_valid 0.77).
Reference stays 1.0.

I also verified the disjoint-failure ordering for the README's
uncovered failure modes (no broken solution, computed by hand under
the new weights): skip-dedup 0.80, skip-sliver 0.80, dedup keep="last"
0.83, skip-area-recompute 0.94, half-bowtie-repair 0.91, the
weak-agent drop-bowtie pattern 0.74. No up-weighting inverted the
ordering; central-operation failures sit below cosmetic/attribute
slips throughout.

#### Prior runs re-graded

The two current (post-cutoff) runs both re-grade identically because
both submissions pass all 13 subchecks:

| Run | Adapter | Old score | New score |
|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 1.0 | 1.0 |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 1.0 | 1.0 |

No notable shifts: a weight change only moves a run's score if the run
fails some subcheck, and both current runs are perfect. (Stale
pre-cutoff runs were not re-graded; the only stale-but-informative
run, the gemma skip-dedup at 0.69, would land at 0.80 under the new
weights, consistent with the disjoint-failure table above.)

#### Reasoning

The task's contract is a four-operation cleaning chain plus an implicit
area recompute. The subchecks that directly detect failure of those
central operations - `all_geometries_valid` (make-valid),
`no_slivers` (sliver drop), `no_exact_duplicate_geometries` (dedup),
`all_multipolygon` (coercion) - now carry the highest weight (4). The
dedup keep-rule and non-mutation correctness checks
(`parcel_id_set_matches_reference`, `identifying_attributes_match_reference`,
`geometric_extent_preserved`) and the broad count detector stay at
weight 3. The implicit attribute recompute and the
never-should-happen null/empty guard are medium (2). The structural
stray-type guard and the two reprojectable-CRS checks are cosmetic
(1). This makes a submission that skips a central cleaning step drop
substantially while a wrong-but-reprojectable CRS only dents the
score - the calibration HR-004 asked for.

### 3. Changes applied this run

#### Unilateral edits

- `grade.py`: subcheck `weight=` values only (table above). No
  check logic, threshold, or gate touched. Re-grade on reference: 1.0.
- `metadata.yaml`: refreshed the three `broken_solutions`
  `measured_score` / `expected_score_range` (0.943 / 0.771 / 0.886) and
  rewrote the weight-arithmetic prose in each description to the new
  per-task weights.
- `README.md`: refreshed the four stale broken/weak-agent score
  fractions (0.94 / 0.89 / 0.77 / ~0.74) and the calibration triangle;
  added a one-line note that ordering now tracks severity.
- `audit/status.json`: removed HR-004; recorded this block's edits.

#### Human-review items

- HR-004 (grader-miscalibration-suspected, the 3x-weighting flag):
  RESOLVED and removed - the per-task weights replace the blunt 3x
  policy for this task.
- HR-001, HR-002, HR-003: retained, unchanged, out of scope for a
  grading-only weight pass.

#### Tests run

- grader on reference: 1.0 (gate passes, 13/13 subchecks, after edits)
- grader on brokens (per-task weighted): wrong_format 0.943,
  no_make_valid 0.771, no_coerce 0.886
- grader on current runs: run-20260608-074701Z 1.0,
  run-20260609-084636Z 1.0
- pytest: not run (orchestrator runs the suite)

## Review-queue resolution 2026-06-14 — HR-003 (reference-prompt-mismatch)

#### Decision

The instruction claimed the output must have "exactly these columns:
parcel_id, parcel_class, district, area_m2" (a closed 4-column set),
but the reference solution (`generate.py` emits
`parcel_id, record_seq, parcel_class, district, area_m2, geometry`),
the README ("Schema preserved"), and the grader
(`REQUIRED_COLUMNS` checked as a subset, `record_seq` never read)
all treat `record_seq` as a legitimately retained provenance column.
The instruction's "exactly" was the lone outlier and the only
artifact making a closed-set claim. Resolved by rewording the prompt
to drop the closed-set assertion — Option A, mirroring the
`crs-l2-fiji-antimeridian` HR-001 prompt-rewording resolution. No
score impact (the grader never enforced "exactly"); reference and
brokens untouched, no recalibration.

#### Changes in this run

- `task.json`: instruction "with exactly these columns:" →
  "including these columns:"; `version` 2 → 3.
- `audit/status.json`: removed HR-003; appended `task.json` to
  `unilateral_edits`.

#### Human-review items

- HR-003: RESOLVED and removed.
- HR-001, HR-002: retained, unchanged, out of scope for this prompt pass.

#### Tests run

- pytest: no task-specific suite under `benchmark/eval/tests/`.
- re-grade: not run — prompt-only edit, grader and reference unchanged.
