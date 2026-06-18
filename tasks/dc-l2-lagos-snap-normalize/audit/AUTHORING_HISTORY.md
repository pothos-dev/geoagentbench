# Implementation notes — dc-l2-lagos-snap-normalize

## Status
completed

## Summary
Five-step data-cleaning chain on a 10 080-feature synthetic Lagos
zoning GPKG: 1 mm vertex snap, zero-area drop, class-vocabulary
normalisation, blank-row filter, per-class dissolve with area
recompute. Reference scores 1.0; three brokens land at 0.0, 0.75,
0.875.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.0 (expected range [0.0, 0.0])
  - no_snap: 0.75 (expected range [0.65, 0.85])
  - wrong_canonical: 0.875 (expected range [0.8, 0.95])
- Second-run output match: bit-identical
- Library tests after task: pass

## Failure-mode coverage
- Skip 1 mm snap: broken_no_snap
- Wrong output CRS: broken_wrong_format
- Wrong canonical casing: broken_wrong_canonical
- Skip blank-row filter: principled-reasoning (count gate +
  no_blank_class_rows subcheck)
- Skip zero-area drop: principled-reasoning (per_class_area +
  IoU subchecks)
- Skip per-class dissolve: principled-reasoning (count gate)
- Coarser snap tolerance: not-handled (tolerances ≥ 30 µm all
  produce the same output by construction; deliberately accepted)
- Emit MultiPolygon throughout: principled-reasoning
  (geometry_type_polygon_only subcheck)

## Open issues
- [severity: low] Snap-tolerance robustness is wider than the
  persona's "1 mm" — any tolerance from ~30 µm to ~10 cm produces
  the same output because the grid pitch (10 m) is much larger
  than the perturbation magnitude (≤ 30 µm). Tightening this would
  require perturbations within an order of magnitude of the
  declared tolerance, which makes the fixture more fragile to
  GEOS-version differences. Accepted as low severity.

## Suggested prompt changes
None.

## Inventory change proposals
None.

## Library extensions
None.

## Runtime
~30 minutes.

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

The task was authored 2026-05-08 (commit `124f6b4`) as an L2 data-cleaning chain
on a hand-crafted Lagos zoning fixture (10 080 features, EPSG:26331). Per the
inventory row and the original README, the persona Tunde Adeyemi must run a
five-step pipeline: 1 mm vertex snap, zero-area drop, attribute normalisation to
four canonical TitleCase classes, blank-row filter, and per-class spatial
aggregation with `area_m2` recompute. Output is a single GPKG
(`zoning_aggregated.gpkg`) of four single-part Polygons (500 m × 500 m each,
250 000 m²). The author block above documents three broken variants targeting
common failure modes (no-snap → 0.75, wrong-canonical-casing → 0.875,
wrong-CRS → 0.0); the grader has eight subchecks each independently observable.

#### Change log

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 124f6b4 | initial-authoring | Initial task: README, IMPLEMENTATION_NOTES, data/_prepare_input.py, lagos_zoning_legacy.gpkg, grade.py, metadata.yaml, reference/generate.py + outputs, task.json, tests/_make_brokens.py + 3 broken outputs | (initial) |
| 2026-05-08 | 001e459 | docs-change | Move benchmark/ into authoring/+eval/ subtrees | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Move benchmark/eval/tasks/ -> benchmark/tasks/ | Commit msg only renames |
| 2026-05-13 | 8915010 | docs-change | Add image-prompt.md to task | Commit msg: image-prompt for all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Add image.webp | Commit msg: generated card images |
| 2026-05-13 | 3c65373 | docs-change | Regenerate image.webp via FLUX schnell | Commit msg only |
| 2026-05-13 | cfbdc7c | docs-change | Regenerate image.webp via nano-banana-2 | Commit msg only |
| 2026-05-13 | 9e79176 | prompt-change | Fold structured "Output schema:" bullet list into prose paragraph in task.json instruction; drop "Polygon geometry" trailing phrase | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | f5d1e91 | prompt-change | Strip explicit `RESIDENTIAL`/`Residential`/`residential`/`Resi.` enumeration, "everything dissolves into slivers / zero-area ghosts crash the dissolve" diagnosis, "drop the zero-area features", "with a recomputed area_m2", and the schema-row hints (interior-holes ban, single-part Polygon, recomputed numeric) | Commit msg: "Strip deducible information from DC task instructions" |
| 2026-05-15 | a78a513 | prompt-change | Further strip: drop "then aggregate per class with a recomputed `area_m2`" and remove "recomputed from the surviving geometry" qualifier | Commit msg: "Strip deducible information from DC task instructions (round 2)" |
| 2026-05-17 | 64740d0 | prompt-change | Rewrite instruction to describe symptoms ("mixed casing, spelling variations, blank entries, tiny gaps and overlaps") and desired outcomes ("clean up the class names to consistent canonical TitleCase values, drop blank rows, fix the vertex precision problems, produce one merged geometry per canonical zoning class") instead of naming the snap operation, the zero-area-drop step, the dissolve step, or the four canonical class identities | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" |
| 2026-05-17 | ca8994d | prompt-change | Remove "EPSG:26331" suffix from instruction (model infers CRS from GPKG metadata) | Commit msg: "Remove remaining EPSG codes from task instruction fields" |
| 2026-05-26 | 29a9ae3 | docs-change | Reorganize folder layout: data/ -> inputs/, reference/ -> reference/solution/, tests/ -> reference/failures/, IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, image* -> assets/. Path references updated in grade.py / generate.py / _make_brokens.py / _prepare.py | Commit msg: layout reorganisation, no semantic change |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:52:19+00:00 (commit `ca8994d`, class: prompt-change)
- The 2026-05-26 `29a9ae3` reorganisation is a docs/layout move (paths updated, content unchanged in grade.py / generate.py / _make_brokens.py / metadata.yaml) — does NOT shift the cutoff.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:10:40Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:47:03Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:18:30Z | 0.0 | done | current (model-side failure) |

Stale runs (pre-cutoff, considered but excluded): 28 earlier runs from
2026-05-12 through 2026-05-17 09:46Z under earlier instruction wordings.

#### Verdict

**calibrated** (with low-confidence caveat — see findings)

The two `current` capable-model runs (Opus, DeepSeek V4 Flash) both achieved
1.0 with every gate and every subcheck passing — same canonical class set,
exact 250 000 m² per quadrant, IoU 1.0, no holes, single-part Polygons. The
Gemma run scored 0.0 because the model wrote the output as
`lagos_zoning_cleaned.gpkg` even though its own generated code initially used
`output_file = 'zoning_aggregated.gpkg'` (transcript shows the model edited
the filename mid-flight). The instruction explicitly names `zoning_aggregated.gpkg`
twice — this is a model-side bug (filename hallucination), not a task issue.
The grader's gate 1 correctly rejects the missing file.

The current instruction has been aggressively stripped over three rounds
(2026-05-14 f5d1e91, 2026-05-15 a78a513, 2026-05-17 64740d0+ca8994d) — it
no longer enumerates the four canonical class identities, no longer names
"snap", "dissolve", "zero-area drop", or "aggregate per class", and no
longer specifies EPSG:26331. The model must infer all of these from the data.
Two of three current models still solve it perfectly; one (Gemma) failed on
a non-task-related filename issue. This is what an L2 task should look like.

#### Specific findings

- Instruction stripping has been thorough through 2026-05-17 and aligns with
  the design-prompt's "strip deducible information" rule. The remaining
  hints ("canonical TitleCase", "drop rows with blank or whitespace-only
  classes", "fix the vertex precision problems") are arguably persona
  guidance the agent could otherwise miss (TitleCase is the persona's house
  style, not derivable from the data — variants include ALL-CAPS, lowercase,
  TitleCase, and abbreviations). No further unilateral stripping is warranted.
- The grader's `canonical_class_vocabulary` subcheck requires exactly
  `{Residential, Commercial, Industrial, Agricultural}` while the instruction
  no longer enumerates those four names. The agent must infer them from the
  variant spellings in the data (e.g. `Resi.` → `Residential`). The wrong-canonical
  broken (ALL-CAPS) intentionally lands at 0.875 to give partial credit when
  only the casing is off. This is a deliberate, principled judgement call by
  the author; the per-class-area subcheck case-folds so does not double-penalise
  casing. No flag.
- Only 3 current runs and they cluster as {pass, pass, model-side-fail}. The
  evidence is thin but consistent. Not flagged because (a) the two passes are
  from different model families/labs and both produce identical output, and
  (b) the failure is mechanically a filename hallucination unrelated to the
  task's intended difficulty axis.
- `metadata.yaml > broken_solutions > measured_score` values (0.0, 0.75, 0.875)
  match the descriptions in the IMPLEMENTATION_NOTES author block; broken
  outputs are present on disk under `reference/failures/broken_*/outputs/`.
  No re-measurement performed — none of the design-affecting commits since
  initial-authoring touched the grader or reference outputs, and the
  reorganisation only renamed paths.

### 3. Changes applied this run

#### Unilateral edits

None. The task is calibrated and the instruction stripping is already at the
level the design-prompt and the May 14/15/17 commits established. No grader
tolerance loosening is justified (the two passing runs hit exact 0.000 %
deviation), no further gift removal is justified (remaining hints are
persona-style requirements).

#### Proposed but not applied (see HUMAN-REVIEW items)

None.

#### Tests run

- grader on reference: 1.00 (8/8 subchecks, both gates pass)
- pytest: pass (35 passed in 0.60s)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

The task was authored 2026-05-08 (commit `124f6b4`) as an L2 data-cleaning chain
on a hand-crafted Lagos zoning fixture (10 080 features, EPSG:26331). Per the
inventory row and the original README, persona Tunde Adeyemi runs a five-step
pipeline: 1 mm vertex snap, zero-area drop, attribute normalisation to four
canonical TitleCase classes, blank-row filter, and per-class spatial aggregation
with `area_m2` recompute. Output is a single GPKG (`zoning_aggregated.gpkg`) of
four single-part Polygons (500 m × 500 m each, 250 000 m²). The author block
above documents three broken variants (no-snap → 0.75, wrong-canonical-casing →
0.875, wrong-CRS → 0.0); the grader scores two gates plus eight independently
observable subchecks.

#### Change log

This is the second evaluator pass. The git history is unchanged since the prior
evaluator review (2026-05-26); the only new commit is the prior evaluator's own
`e775a84` (docs-change — appended its review block + wrote coverage.yaml/status.json).
The reconstructed history below is consistent with that block and re-verified
against `git log --follow` and `git show` on the design-affecting commits.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 124f6b4 | initial-authoring | Initial task: README, IMPLEMENTATION_NOTES, data/_prepare_input.py, lagos_zoning_legacy.gpkg, grade.py, metadata.yaml, reference/generate.py + outputs, task.json, tests/_make_brokens.py + 3 broken outputs | (initial) |
| 2026-05-08 | 001e459 | docs-change | Move benchmark/ into authoring/+eval/ subtrees | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Move benchmark/eval/tasks/ -> benchmark/tasks/ | Commit msg only renames |
| 2026-05-13 | 8915010 | docs-change | Add image-prompt.md to task | Commit msg: image-prompt for all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Add image.webp | Commit msg: generated card images |
| 2026-05-13 | 3c65373 | docs-change | Regenerate image.webp via FLUX schnell | Commit msg only |
| 2026-05-13 | cfbdc7c | docs-change | Regenerate image.webp via nano-banana-2 | Commit msg only |
| 2026-05-13 | 9e79176 | prompt-change | Fold structured "Output schema:" bullet list into prose paragraph in task.json instruction; drop "Polygon geometry" trailing phrase | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | f5d1e91 | prompt-change | Strip explicit `RESIDENTIAL`/`Residential`/`residential`/`Resi.` enumeration, the sliver/ghost-crash diagnosis, "drop the zero-area features", "with a recomputed area_m2", and schema-row hints | Commit msg: "Strip deducible information from DC task instructions" |
| 2026-05-15 | a78a513 | prompt-change | Further strip: drop "then aggregate per class with a recomputed `area_m2`" and the "recomputed from the surviving geometry" qualifier | Commit msg: "Strip deducible information from DC task instructions (round 2)" |
| 2026-05-17 | 64740d0 | prompt-change | Rewrite instruction to describe symptoms + desired outcomes instead of naming snap / zero-area-drop / dissolve steps or the four canonical class identities | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" |
| 2026-05-17 | ca8994d | prompt-change | Remove "EPSG:26331" suffix from instruction (model infers CRS from GPKG metadata) | Commit msg: "Remove remaining EPSG codes from task instruction fields" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder layout reorg: data/ -> inputs/, reference/ -> reference/solution/, tests/ -> reference/failures/, IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, image* -> assets/. Only path references updated in grade.py / generate.py / _make_brokens.py / _prepare.py | Commit msg: layout reorganisation, no semantic change |
| 2026-05-26 | e775a84 | docs-change | Prior evaluator review: appended review block, wrote coverage.yaml + audit/status.json (verdict calibrated, no edits) | Commit msg: "Re-evaluate ...: calibrated, no edits" |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:52:19+00:00 (commit `ca8994d`, class: prompt-change).
- Re-confirmed: `29a9ae3` (folder reorg) and `e775a84` (prior evaluator) are both
  docs-change and do not move the cutoff. `git show 29a9ae3` shows the touched
  code files (grade.py +2/-2, generate.py +4/-4, _make_brokens.py +8, _prepare.py +2)
  are pure path renames, no answer-key or instruction change.

#### Runs considered

Same three current runs as the prior pass; no new runs have been recorded since.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:10:40Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:47:03Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:18:30Z | 0.0 | done | current (model-side failure) |

Stale runs (pre-cutoff, considered but excluded): 26 earlier runs from
2026-05-12 through 2026-05-17 06:14Z under earlier instruction wordings.

#### Verdict

**calibrated**

The two `current` capable-model runs (Opus, DeepSeek V4 Flash) — different model
families/labs — both scored 1.0 with both gates and all eight subchecks passing.
Independent re-inspection of their output GPKGs confirms each is byte-equivalent
to the reference in structure: 4 features, columns `[zoning_class, area_m2,
geometry]`, CRS EPSG:26331, single-part Polygons, the four canonical classes,
exact 250 000.0 m² per quadrant (per_class Δ=0.000 %, union IoU 1.0000, 0 interior
holes). The Gemma run scored 0.0 because it wrote its (cleaned) output to
`lagos_zoning_cleaned.gpkg` rather than the instruction-named
`zoning_aggregated.gpkg` (its outputs/ dir contains `lagos_zoning_cleaned.gpkg`
plus the untouched input copy, but no `zoning_aggregated.gpkg`). The instruction
names `zoning_aggregated.gpkg` explicitly — this is a model-side filename
hallucination, not a task defect, and Gate 1 rejects it correctly. Per the
prompt's "model-side failures are not task problems" rule, it is not evidence of
mis-calibration.

Re-grading the reference and the three brokens this pass reproduces the
documented spectrum exactly: reference 1.0; `broken_wrong_format` 0.0 (Gate 1 CRS
reject); `broken_no_snap` 0.75 (fails `no_interior_holes` + `geometry_type_polygon_only`);
`broken_wrong_canonical` 0.875 (fails only `canonical_class_vocabulary`). The
`metadata.yaml > broken_solutions > measured_score` values (0.0 / 0.75 / 0.875)
are therefore still accurate — no update required.

#### Specific findings

- Output-CRS / format consistency (2c-CRS) holds: `expected_outputs[].crs`
  EPSG:26331 == reference output CRS (26331) == README's stated output CRS
  (26331). The grader's `crs.to_epsg() == 26331` Gate-1 check is symmetric (it
  rejects the file, it does not silently reproject one side); the IoU subcheck
  compares submission and reference in their shared native CRS. No CRS finding.
- Instruction stripping is mature (four prompt-change rounds through 2026-05-17).
  The remaining hints — "canonical TitleCase", "drop rows with blank or
  whitespace-only classes", "fix the vertex precision problems" — are persona
  house-style / desired-outcome statements the agent cannot infer from the data
  alone (the data carries ALL-CAPS, lowercase, TitleCase, and abbreviation
  variants, so TitleCase is a stipulation, not a deduction). No further unilateral
  stripping warranted.
- The `canonical_class_vocabulary` subcheck requires exactly
  `{Residential, Commercial, Industrial, Agricultural}` while the instruction no
  longer enumerates them; the agent infers the four families from the variant
  spellings. `per_class_area_matches_reference` case-folds, so wrong casing is
  penalised once (the deliberate `wrong_canonical` → 0.875 design), not twice.
  This is a principled author judgement; no flag.
- Evidence is thin (3 current runs, clustering {pass, pass, model-side-fail}) but
  consistent and drawn from two different model families. Not flagged: the two
  passes produce identical correct output and the single failure is mechanically
  a filename issue unrelated to the task's difficulty axis.

### 3. Changes applied this run

#### Unilateral edits

None. The task is calibrated; the prior evaluator already reached the same
conclusion and the design state is unchanged since. No tolerance loosening is
justified (both passing runs hit exact 0.000 % deviation), no further gift removal
is warranted (remaining hints are persona-style requirements), and the broken
`measured_score` values re-verified exactly so no metadata update is needed.

#### Proposed but not applied (see HUMAN-REVIEW items)

None.

#### Tests run

- grader on reference: 1.00 (8/8 subchecks, both gates pass)
- pytest: pass (35 passed in 1.07s)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

The task was authored 2026-05-08 (commit `124f6b4`) as an L2 data-cleaning chain on
a hand-crafted Lagos zoning fixture (10 080 features, EPSG:26331). Persona Tunde
Adeyemi runs a five-step pipeline: 1 mm vertex snap, zero-area drop, attribute
normalisation to four canonical TitleCase classes, blank-row filter, and per-class
spatial aggregation with `area_m2` recompute. Output is a single GPKG
(`zoning_aggregated.gpkg`) of four single-part Polygons (500 m × 500 m each,
250 000 m²). Author block documents three broken variants (no-snap → 0.75,
wrong-canonical-casing → 0.875, wrong-CRS → 0.0); the grader has two gates plus
eight independently observable subchecks.

#### Change log

Third evaluator pass. One new design-neutral commit since the last review
(`622342b`, 2026-05-28 — repo-wide `prompt_version` drop from metadata.yaml; no
semantic change to grader / inputs / reference / instruction). Prior change-log
rows re-verified against `git show` and remain accurate.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 124f6b4 | initial-authoring | Initial task: README, IMPLEMENTATION_NOTES, data/_prepare_input.py, lagos_zoning_legacy.gpkg, grade.py, metadata.yaml, reference/generate.py + outputs, task.json, tests/_make_brokens.py + 3 broken outputs | (initial) |
| 2026-05-08 | 001e459 | docs-change | Move benchmark/ into authoring/+eval/ subtrees | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Move benchmark/eval/tasks/ -> benchmark/tasks/ | Commit msg only renames |
| 2026-05-13 | 8915010 | docs-change | Add image-prompt.md to task | Commit msg: image-prompt for all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Add image.webp | Commit msg: generated card images |
| 2026-05-13 | 3c65373 | docs-change | Regenerate image.webp via FLUX schnell | Commit msg only |
| 2026-05-13 | cfbdc7c | docs-change | Regenerate image.webp via nano-banana-2 | Commit msg only |
| 2026-05-13 | 9e79176 | prompt-change | Fold structured "Output schema:" bullet list into prose paragraph in task.json instruction; drop "Polygon geometry" trailing phrase | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | f5d1e91 | prompt-change | Strip explicit `RESIDENTIAL`/`Residential`/`residential`/`Resi.` enumeration, sliver/ghost-crash diagnosis, "drop the zero-area features", "with a recomputed area_m2", and schema-row hints | Commit msg: "Strip deducible information from DC task instructions" |
| 2026-05-15 | a78a513 | prompt-change | Drop "then aggregate per class with a recomputed `area_m2`" and the "recomputed from the surviving geometry" qualifier | Commit msg: "Strip deducible information from DC task instructions (round 2)" |
| 2026-05-17 | 64740d0 | prompt-change | Rewrite instruction to describe symptoms + desired outcomes instead of naming snap / zero-area-drop / dissolve steps or the four canonical class identities | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" |
| 2026-05-17 | ca8994d | prompt-change | Remove "EPSG:26331" suffix from instruction (model infers CRS from GPKG metadata) | Commit msg: "Remove remaining EPSG codes from task instruction fields" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder layout reorg: data/ -> inputs/, reference/ -> reference/solution/, tests/ -> reference/failures/, IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, image* -> assets/. Only path references updated in code | Commit msg: layout reorganisation, no semantic change |
| 2026-05-26 | e775a84 | docs-change | Prior evaluator (1st pass): appended review block, wrote coverage.yaml + audit/status.json (verdict calibrated, no edits) | Commit msg: "Re-evaluate ...: calibrated, no edits" |
| 2026-05-27 | 93af65a | docs-change | Prior evaluator (2nd pass): appended review block, refreshed coverage.yaml + audit/status.json (verdict calibrated, no edits) | Commit msg: "Re-evaluate ...: calibrated, no edits" |
| 2026-05-28 | 622342b | docs-change | Repo-wide `prompt_version` field drop (metadata.yaml -1 line); task content untouched | Commit msg: "Add task content versioning; drop unused prompt_version" |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-17T12:52:19+00:00 (commit `ca8994d`, class: prompt-change).
- Unchanged from prior passes. `622342b` only drops the legacy `prompt_version`
  string from `metadata.yaml`; nothing the grader / instruction / inputs depend on.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:10:40Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:47:03Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:18:30Z | 0.0 | done | current (model-side filename hallucination) |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:40:05Z | 0.875 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:38:31Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T01:41:40Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:26:56Z | 1.0 | done | current |

Stale runs (pre-cutoff, considered but excluded): 26 earlier runs from
2026-05-12 through 2026-05-17 06:14Z under earlier instruction wordings.

#### Verdict

**calibrated**

Seven current runs span three model families (Claude Opus 4.6 / 4.7, DeepSeek V4
Flash, Gemma 4 26B). Five of seven land at 1.0, one at 0.875, one at 0.0. The
0.875 (Opus 4.7, `run-20260527-2016Z`) is a clean MultiPolygon-throughout
submission: every subcheck passes except `geometry_type_polygon_only` — exactly
the principled detector for failure mode #8 in the README (the agent did every
step correctly but wrapped each per-class result as a MultiPolygon; the dissolve
output is still a single 500 m × 500 m polygon by area / IoU / hole-count, so
this is what the strict-Polygon subcheck is *for*). The 0.0 (Gemma,
`run-20260526-0748Z`) wrote the output as `lagos_zoning_cleaned.gpkg` instead of
the instruction-named `zoning_aggregated.gpkg` — a model-side filename
hallucination, correctly Gate-1-rejected; not a task defect. The two later
Gemma runs (2026-05-27 and 2026-05-28) hit 1.0, confirming the prior Gemma
failure was transient model behaviour, not a task barrier.

Re-grading the reference and the three brokens this pass reproduces the
documented spectrum exactly: reference 1.0; `broken_wrong_format` 0.0;
`broken_no_snap` 0.75; `broken_wrong_canonical` 0.875. `metadata.yaml >
broken_solutions > measured_score` values stay accurate.

2c-CRS consistency: `expected_outputs[].crs` EPSG:26331 == reference output CRS
(26331) == README's stated output CRS (26331). The grader's Gate-1 `crs.to_epsg()
== 26331` is symmetric (rejects the file outright; no one-sided reprojection),
and the IoU subcheck compares submission vs. reference in their shared native
CRS. No CRS finding.

#### Specific findings

- Instruction had a duplicate-axis "canonical TitleCase" hint: para 1 says
  "Clean up the class names to consistent canonical TitleCase values" and the
  schema sentence in para 2 said "zoning_class (canonical TitleCase) and
  area_m2 as a numeric value". Per the unilateral *tighten-redundant-statements*
  rule, stripped the para-2 parenthetical "(canonical TitleCase)" — the persona
  voice in para 1 is the canonical statement of the casing constraint; the
  parenthetical is pure duplication and the `canonical_class_vocabulary` subcheck
  already pins the exact label set. Reference still scores 1.0 (8/8). Applied
  unilaterally; bumped `task.json.version` 1 → 2.
- The score distribution {1.0 × 5, 0.875 × 1, 0.0 × 1} demonstrates the grader's
  intended resolution: a fully correct pipeline scores 1.0, a MultiPolygon-only
  flaw scores 0.875 (one of eight subchecks), and a missing-output / wrong-CRS
  failure scores 0.0 at Gate 1. This is exactly what the metadata's broken-solution
  spectrum (0.0 / 0.75 / 0.875 / 1.0) predicts agents to encounter. No flag.
- The `canonical_class_vocabulary` subcheck requires exactly `{Residential,
  Commercial, Industrial, Agricultural}` while the instruction no longer
  enumerates them; the agent infers the four families from the variant spellings.
  `per_class_area_matches_reference` case-folds so wrong casing is penalised once
  only (the `wrong_canonical` → 0.875 design). Principled author judgement; no flag.

### 3. Changes applied this run

#### Unilateral edits

- `task.json`: stripped redundant "(canonical TitleCase)" parenthetical from the
  output-schema sentence; bumped `version` 1 → 2. Re-grade on reference: 1.00.
  Reason: tighten-redundant-statements rule (the persona paragraph already
  establishes "canonical TitleCase values"; schema repetition adds nothing).

#### Proposed but not applied (see HUMAN-REVIEW items)

None.

#### Tests run

- grader on reference: 1.00 (8/8 subchecks, both gates pass)
- pytest: pass (41 passed in 0.81s)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

The task was authored 2026-05-08 (commit `124f6b4`) as an L2 data-cleaning chain
on a hand-crafted Lagos zoning fixture (10 080 features, EPSG:26331). Persona
Tunde Adeyemi runs a five-step pipeline: 1 mm vertex snap, zero-area drop,
attribute normalisation to four canonical TitleCase classes, blank-row filter,
and per-class spatial aggregation with `area_m2` recompute. Output is a single
GPKG (`zoning_aggregated.gpkg`) of four single-part Polygons (500 m × 500 m
each, 250 000 m²). The author block documents three broken variants targeting
the principal failure modes.

#### Change log

Fourth evaluator pass. One new design-affecting commit since the last review:
`05aabd6` (2026-05-28T19:02:57Z) — repo-wide grader-policy change softening the
CRS hard-fail into two subcheck deductions, applied uniformly to 21 task graders
including this one. The shape of the grader changes for this task: was 2 gates +
8 subchecks; now 2 gates + 10 subchecks (gates unchanged in semantics, but the
old CRS hard-fail at Gate 1 is replaced by the soft `grade_crs_soft` helper that
reprojects the submission to the canonical CRS and adds `crs_is_canonical` and
`crs_in_meaningful_set` as docking subchecks).

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 124f6b4 | initial-authoring | Initial task: README, IMPLEMENTATION_NOTES, data/_prepare_input.py, lagos_zoning_legacy.gpkg, grade.py, metadata.yaml, reference/generate.py + outputs, task.json, tests/_make_brokens.py + 3 broken outputs | (initial) |
| 2026-05-08 | 001e459 | docs-change | Move benchmark/ into authoring/+eval/ subtrees | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Move benchmark/eval/tasks/ -> benchmark/tasks/ | Commit msg only renames |
| 2026-05-13 | 8915010 | docs-change | Add image-prompt.md to task | Commit msg: image-prompt for all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Add image.webp | Commit msg: generated card images |
| 2026-05-13 | 3c65373 | docs-change | Regenerate image.webp via FLUX schnell | Commit msg only |
| 2026-05-13 | cfbdc7c | docs-change | Regenerate image.webp via nano-banana-2 | Commit msg only |
| 2026-05-13 | 9e79176 | prompt-change | Fold structured "Output schema:" bullet list into prose paragraph in task.json instruction; drop "Polygon geometry" trailing phrase | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | f5d1e91 | prompt-change | Strip explicit `RESIDENTIAL`/`Residential`/`residential`/`Resi.` enumeration, sliver/ghost-crash diagnosis, "drop the zero-area features", "with a recomputed area_m2", and schema-row hints | Commit msg: "Strip deducible information from DC task instructions" |
| 2026-05-15 | a78a513 | prompt-change | Drop "then aggregate per class with a recomputed `area_m2`" and the "recomputed from the surviving geometry" qualifier | Commit msg: "Strip deducible information from DC task instructions (round 2)" |
| 2026-05-17 | 64740d0 | prompt-change | Rewrite instruction to describe symptoms + desired outcomes instead of naming snap / zero-area-drop / dissolve steps or the four canonical class identities | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" |
| 2026-05-17 | ca8994d | prompt-change | Remove "EPSG:26331" suffix from instruction (model infers CRS from GPKG metadata) | Commit msg: "Remove remaining EPSG codes from task instruction fields" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder layout reorg: data/ -> inputs/, reference/ -> reference/solution/, tests/ -> reference/failures/, IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, image* -> assets/. Only path references updated in code | Commit msg: layout reorganisation, no semantic change |
| 2026-05-26 | e775a84 | docs-change | Prior evaluator (1st pass): appended review block, wrote coverage.yaml + audit/status.json (verdict calibrated, no edits) | Commit msg: "Re-evaluate ...: calibrated, no edits" |
| 2026-05-27 | 93af65a | docs-change | Prior evaluator (2nd pass): appended review block, refreshed coverage.yaml + audit/status.json (verdict calibrated, no edits) | Commit msg: "Re-evaluate ...: calibrated, no edits" |
| 2026-05-28 | 622342b | docs-change | Repo-wide `prompt_version` field drop (metadata.yaml -1 line); task content untouched | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | c5f4981 | prompt-change | Prior evaluator (3rd pass): stripped redundant "(canonical TitleCase)" parenthetical from para-2 schema sentence; bumped task.json.version 1 → 2 | Commit msg: "Re-evaluate ...: tighten redundant TitleCase hint" |
| 2026-05-28 | 05aabd6 | grader-change | Repo-wide soft-CRS policy: replaced Gate-1 CRS hard-fail with `grade_crs_soft` helper, added `crs_is_canonical` + `crs_in_meaningful_set` subchecks (8 → 10 subchecks). Per-task config: `CANONICAL_EPSG = 26331`, `MEANINGFUL_EPSGS = {26331}`. Same policy applied uniformly to 21 graders | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-28T19:02:57+00:00 (commit `05aabd6`, class: grader-change).
- The repo-wide CRS-softening commit changes the grader for this task; any run before it scored under the old 8-subcheck schema. Pre-cutoff runs are stale.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T19:45:59Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:36:30Z | 0.0 | done | current (model-side: GeometryCollection output) |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T23:49:18Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:23:36Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T10:27:11Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:56:44Z | 0.8 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:42:48Z | 0.0 | done | current (model-side: skipped class normalisation, 8 rows out) |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled | current (no submission) |

Stale runs (pre-cutoff, considered but excluded): all 33 runs from 2026-05-12 through 2026-05-28 03:17Z; these scored under the prior 8-subcheck schema (and most also pre-date the May-17 instruction stripping).

#### Verdict

**calibrated**

Seven current scored runs from three model families (Claude Opus 4.7, DeepSeek V4 Pro, Gemma 4 26B IT). Four of seven land at 1.0 (every gate, every subcheck passing). One Gemma `detailed`-prompt run hits 0.8 — the principled no-snap pattern: every step right except the snap, so `no_interior_holes` and `geometry_type_polygon_only` fail; the geometric and area subchecks all pass on the un-snapped MultiPolygons; CRS subchecks pass (26331 native). This is exactly what failure mode #1 in the README predicts the no-snap broken to look like, and matches `broken_no_snap` measured at 0.8 this pass.

Two 0.0 runs are both Gemma model-side failures: `run-20260528-2225Z` wrote GeometryCollections instead of Polygons (Gate 2 reject) and `run-20260606-1129Z` skipped the class normalisation step entirely and emitted eight rows (Gate 2 count reject). Per the prompt's "model-side failures are not task problems" rule, these are not evidence of mis-calibration. The cancelled `run-20260606-1334Z` produced no submission.

Re-grading the reference and the three brokens this pass under the new 10-subcheck schema:
- reference: 1.0 (10/10)
- `broken_wrong_format`: 0.8 (was 0.0; soft-CRS reprojection now lets the geometric subchecks pass on an otherwise-correct pipeline; only `crs_is_canonical` and `crs_in_meaningful_set` fail)
- `broken_no_snap`: 0.8 (was 0.75; same two subchecks fail as before — `no_interior_holes`, `geometry_type_polygon_only` — but the denominator grew 8 → 10)
- `broken_wrong_canonical`: 0.9 (was 0.875; only `canonical_class_vocabulary` fails; denominator 8 → 10)

The `metadata.yaml > broken_solutions > measured_score` values (0.0 / 0.75 / 0.875) and the wrong_format `expected_score_range: [0.0, 0.0]` are now stale and rewritten this pass to (0.8 / 0.8 / 0.9) with widened ranges and refreshed descriptions documenting the soft-CRS deduction shape. The README's failure-mode bullets are also refreshed.

2c-CRS consistency: `expected_outputs[].crs` EPSG:26331 == reference output CRS (26331) == README's stated output CRS (26331). The grader now soft-handles CRS mismatches by reprojecting the submission to canonical for the geometric subchecks (symmetric in the sense that the reference is read in its native 26331 and the submission is brought to 26331 before comparison; the IoU and area math run in the canonical CRS for both sides). No CRS finding.

#### Specific findings

- The soft-CRS commit (`05aabd6`) compresses the score spread from {0.0, 0.75, 0.875, 1.0} to {0.8, 0.8, 0.9, 1.0} on this task's brokens. Notably the wrong-format and no-snap brokens both land at 0.8, even though they fail for completely different reasons (CRS subchecks vs. snap/holes subchecks). This is a deliberate consequence of the new policy and the natural shape for a grader with two CRS-deduct subchecks: a fully-correct-but-wrong-CRS pipeline scores the same as a correct-CRS-but-no-snap pipeline. The score distribution still spans 0.8–1.0 across distinct failure modes, and the `score.json` subcheck pass/fail trail tells a reviewer which failure mode produced the 0.8. No flag.
- Instruction stripping remains mature. No further unilateral stripping warranted (remaining hints are persona-style desired-outcome statements the agent cannot infer from the data alone).
- `analyst_notes` was missing; authored this pass per the Step 4 unilateral-edit rule.
- Coverage tags re-validated against `authoring/coverage-vocabulary.yaml`; all slugs match. `evaluator_run_at` refreshed.
- Evidence base is broader than prior passes: seven current scored runs across three model families, with the failure modes mapping cleanly onto the principled detector subchecks. The task continues to behave as designed.

### 3. Changes applied this run

#### Unilateral edits

- `metadata.yaml`: refreshed `broken_solutions.measured_score` for all three brokens to track the new 10-subcheck schema (wrong_format 0.0 → 0.8, no_snap 0.75 → 0.8, wrong_canonical 0.875 → 0.9). Widened the corresponding `expected_score_range` values and rewrote the descriptions to document the soft-CRS-deduction shape. Re-grade on reference: 1.00. Reason: prior-evaluator-allowed `measured_score` refresh after the repo-wide grader-change (commit 05aabd6) shifted the broken scores; the description / range refresh is required to keep `metadata.yaml` internally coherent with the new scores.
- `README.md`: updated failure-mode #1 / #2 / #3 score callouts (0.75 → 0.8, 0 → 0.8, 0.875 → 0.9) and the weak-agent-failure-mode paragraph to reflect the new grader's score spectrum. Reason: docs alignment with the soft-CRS grader; mechanical.
- `task.json`: added `analyst_notes` (`description` + `approach` + `pitfalls`). Reason: field was missing; authored per the Step 4 "author analyst_notes if missing" rule.

No `task.json.version` bump: `analyst_notes` is human-facing only (eval UI), not seen by the agent at run time; per the version-bump rules it does not require a bump. `metadata.yaml > broken_solutions > measured_score` refreshes are explicitly listed as not requiring a bump. README is docs-only.

#### Proposed but not applied (see HUMAN-REVIEW items)

None.

#### Tests run

- grader on reference: 1.00 (10/10 subchecks, both gates pass)
- pytest: pass (41 passed in 0.88s)


---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geometry-type uniformity (Polygon/MultiPolygon) migrated to a new
  `geometry_type_polygonal` subcheck. (The stricter
  `geometry_type_polygon_only` subcheck is kept as a separate signal.)
- Null/empty-geometry check migrated to a new
  `no_null_or_empty_geometry` subcheck.
- Row-count tolerance (±5%) migrated to a new
  `feature_count_within_tolerance` subcheck.
- Subcheck total: 10 → 13.

### Verification
- Reference solution re-graded: 1.0 (13/13 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

The task was authored 2026-05-08 (commit `124f6b4`) as an L2 data-cleaning chain
on a hand-crafted Lagos zoning fixture (10 080 features, EPSG:26331). Persona
Tunde Adeyemi runs a five-step pipeline: 1 mm vertex snap, zero-area drop,
attribute normalisation to four canonical TitleCase classes, blank-row filter,
and per-class spatial aggregation with `area_m2` recompute. Output is a single
GPKG (`zoning_aggregated.gpkg`) of four single-part Polygons (500 m x 500 m
each, 250 000 m^2). Three broken variants target the principal failure modes.

#### Change log

Fifth evaluator pass. Two new design-affecting commits since the last review
(both repo-wide grader-policy changes); prior change-log rows re-verified via
`git show` and unchanged. Only the new rows are listed; see the 2026-06-06
block for the full history through `9fb12e7`.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 9fb12e7 | docs-change | Prior evaluator (4th pass): refreshed broken measured_scores for soft-CRS policy, authored analyst_notes, updated README score callouts | Commit msg: "Re-evaluate ...: refresh broken scores for soft-CRS policy" |
| 2026-06-06 | 363aed2 | grader-change | Dropped the `structural_correctness` gate; geometry-type uniformity, null/empty-geometry, and row-count checks migrated to subchecks (`geometry_type_polygonal`, `no_null_or_empty_geometry`, `feature_count_within_tolerance`). Subcheck total 10 -> 13 | Commit msg: repo-wide one-hard-gate refactor; shape-recoverable outputs cost points instead of zeroing |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to eight data-content subchecks (`no_null_or_empty_geometry`, `feature_count_within_tolerance`, `canonical_class_vocabulary`, `no_blank_class_rows`, `no_zero_area_geometries`, `area_m2_recomputed`, `per_class_area_matches_reference`, `geometric_extent_matches_reference`); five checks stay weight 1 (`geometry_type_polygonal`, `no_interior_holes`, `geometry_type_polygon_only`, `crs_is_canonical`, `crs_in_meaningful_set`). Total weight 29 | Commit msg: repo-wide 3x weighting of data-content subchecks; schema/structural stay 1.0 |

The 363aed2 gate-2 removal was already documented in the "Manual cleanup
2026-06-06" section above; the c749e57 weighting was not documented per-task
until this pass.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-06-07T18:32:38+00:00 (commit `c749e57`, class: grader-change).
- Any run started before the weighting commit was scored under a different
  denominator (13 unweighted subchecks, or the pre-gate-2-removal schema) and
  is stale.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T09:39:34Z | 1.0 | done | current (task v2, suite 6510297) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:08:34Z | 1.0 | done | current (task v2, suite ec540aa) |

Stale runs (pre-cutoff, considered but excluded): 44 runs from 2026-05-12
through 2026-06-07T13:24Z. The two most recent stale runs
(`run-20260606-1733Z`, `run-20260607-112430Z`, both Gemma 4 26B detailed)
scored 1.0 under the unweighted 13-subcheck schema; the full pre-cutoff
distribution across model families is summarised in the 2026-05-28 and
2026-06-06 blocks above.

#### Verdict

**insufficient-evidence**

Only two runs post-date the c749e57 weighting cutoff and both come from the
same model family (DeepSeek V4 Flash, basic and detailed prompt variants).
Both scored 1.0; their outputs are structurally identical to the reference
(4 features, columns `[zoning_class, area_m2, geometry]`, CRS EPSG:26331,
single-part Polygons, four canonical TitleCase classes, exactly 250 000 m^2
per quadrant). Per the verdict rules, a single-family evidence base is
insufficient on its own. Nothing in the static checks or the (re-graded)
broken spectrum suggests a calibration problem: the weighting commit only
changes the denominator, not which checks pass, and the long pre-cutoff
history across Claude Opus, DeepSeek, and Gemma matched the designed failure
modes exactly. No grader-miscalibration flag from runs.

Re-grading reference and brokens under the current weighted grader:
- reference: 1.0 (13/13)
- `broken_no_snap`: 0.931 (27/29; fails weight-1 `no_interior_holes` + `geometry_type_polygon_only`)
- `broken_wrong_format`: 0.931 (27/29; fails weight-1 `crs_is_canonical` + `crs_in_meaningful_set`)
- `broken_wrong_canonical`: 0.897 (26/29; fails weight-3 `canonical_class_vocabulary`)

The `metadata.yaml > broken_solutions` blocks (previously 0.8 / 0.8 / 0.9
under the unweighted 10-subcheck schema) were stale and are refreshed this
pass, as are the README failure-mode score callouts.

2c-CRS consistency: `expected_outputs[].crs` EPSG:26331 == reference output
CRS (26331) == README's stated output CRS (26331). The soft-CRS policy
reprojects the submission to the canonical CRS before the geometric subchecks
(declared accept-list policy, not a papering-over) and docks
`crs_is_canonical` / `crs_in_meaningful_set` for non-26331 originals. No CRS
finding.

#### Prompt information audit

| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `zoning_aggregated.gpkg`, GPKG | instruction | stated |
| columns `zoning_class`, `area_m2` (numeric) | instruction | stated |
| CRS EPSG:26331 (canonical + meaningful set) | input GPKG metadata; nothing suggests reprojection | inferable |
| four canonical classes, TitleCase | instruction stipulates TitleCase; the four families are inferable from the variant spellings in the data | stated + inferable |
| no blank/whitespace class rows | instruction | stated |
| no zero-area output geometries | trivially satisfied by any per-class dissolve; ghosts in the input are discoverable by inspection | inferable |
| `area_m2` consistent with geometry (max(1 m^2, 1e-3 rel)) | "a numeric area_m2" on a merged-geometry row implies recompute; summing the per-parcel nominals also happens to land on 250 000 | inferable |
| per-class area within 0.5 % of 250 000 m^2 | grader-internal tolerance | inferable (do the cleanup correctly) |
| union IoU >= 0.99 | grader-internal tolerance | inferable |
| zero interior holes, single-part Polygon | "fix the vertex precision problems" + "one merged geometry per canonical zoning class" | inferable |
| row count within 5 % of 4 | one merged geometry per class | inferable |

Factual claims verified: `lagos_zoning_legacy.gpkg` exists in `inputs/`;
mixed casing / spelling variants / blank entries and sub-mm vertex offsets all
present in the fixture; output schema matches the reference
(`zoning_class`, `area_m2`, geometry). One house-style defect found and fixed
(see findings): the instruction referenced the input as bare
"lagos_zoning_legacy", contained em-dashes, and dropped the output filename
as a bare sentence fragment ("... for the state portal. zoning_aggregated.gpkg.").
No missing or inaccurate constraint.

#### Reference faithfulness

`reference/solution/generate.py` is faithful: 1 mm snap via
`shapely.set_precision`, zero-area/non-polygonal drop, prefix-table class
normalisation to the four TitleCase canonicals, blank filter, per-class
unary_union with `area_m2` recomputed from the merged geometry in EPSG:26331
metres, written as GPKG in the input CRS. The only operations the prompt does
not name are determinism conveniences (stable alphabetical sort, area rounded
to 4 decimal places, pinned GPKG timestamp); rounding at 1e-4 m^2 is five
orders of magnitude inside the grader tolerance and the sort is
order-irrelevant to every subcheck. Faithful; no flag.

#### Specific findings

- The c749e57 weighting demotes this task's titular gotcha: skipping the 1 mm
  snap (the central skill, detected by weight-1 `no_interior_holes` +
  `geometry_type_polygon_only`) now costs 2/29 (score 0.931), while a cosmetic
  ALL-CAPS casing slip costs 3/29 (score 0.897). The snap-detection subchecks
  were classified "structural" by the repo-wide commit, but for this task they
  are the data-content evidence of the primary operation; the penalty ordering
  is arguably inverted. Whether to locally re-weight them to 3.0 (or accept
  the repo-wide classification for cross-task consistency) is a policy call.
  <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="med" -->
  A human should decide whether `no_interior_holes` and
  `geometry_type_polygon_only` should carry weight 3.0 in this task's grader
  so that the no-snap failure mode scores below the wrong-casing one;
  applying that change requires a `version` bump and a broken-score refresh.
- Instruction violated house style: em-dashes, a bare "zoning_aggregated.gpkg."
  sentence fragment, and the input referenced without its `.gpkg` extension.
  Rewrote per the house-style rules (purpose first, full sentences, actual
  filename, parentheses instead of em-dashes), preserving every constraint,
  the state-portal framing, and every deliberate omission (no CRS mention, no
  enumeration of the four classes, no naming of snap/dissolve operations).
  Reference re-grade: 1.0. Version bumped 2 -> 3.
- `metadata.yaml` broken measured_scores and README score callouts were stale
  against the weighted schema; refreshed (no version bump required for these).
- `analyst_notes` reviewed against the rewritten instruction and current
  grader: description, approach, and pitfalls all remain accurate (pitfalls
  reference subcheck names, not numeric scores). No refresh needed.
- README input path still said `data/lagos_zoning_legacy.gpkg` from the
  pre-reorg layout; fixed to `inputs/` (docs-change).
- Coverage slugs re-validated against `authoring/coverage-vocabulary.yaml`;
  all match; `evaluator_run_at` refreshed.

### 3. Changes applied this run

#### Unilateral edits

- `task.json`: house-style rewrite of the instruction (em-dashes removed,
  fragment sentence folded into a full sentence, input referenced as
  `lagos_zoning_legacy.gpkg`); bumped `version` 2 -> 3. Re-grade on
  reference: 1.00. Reason: Step 4 house-style rule; content, constraints, and
  deliberate omissions preserved.
- `metadata.yaml`: refreshed `broken_solutions` measured_scores for the
  weighted schema (wrong_format 0.8 -> 0.93, no_snap 0.8 -> 0.93,
  wrong_canonical 0.9 -> 0.90), adjusted expected_score_range for the two
  0.93 brokens, rewrote descriptions to document the 29-point weighted
  denominator. Reason: allowed measured_score refresh after the repo-wide
  grader-change c749e57.
- `README.md`: failure-mode score callouts and weak-agent paragraph updated
  to the weighted scores; input path `data/` -> `inputs/`. Reason: docs
  alignment; mechanical.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 - grader-miscalibration-suspected - weight inversion: no-snap (0.931)
  now outscores wrong-casing (0.897); consider weighting the two
  snap-detection subchecks 3.0.

#### Tests run

- grader on reference: 1.00 (13/13 subchecks, gate passes)
- grader on brokens: no_snap 0.931, wrong_format 0.931, wrong_canonical 0.897
- pytest: pass (41 passed)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change in one line

Replaced the repo-wide 05b389b / c749e57 one-size-fits-all 3x "data-content"
weighting with per-task reasoned subcheck weights, fixing the snap-vs-casing
inversion: the central 1 mm-snap gotcha now drops the score more than a cosmetic
ALL-CAPS casing slip. Grading-only change (weights only); no version bump, no
edits to task.json / inputs / reference / failures.

### Reasoning

This is a data-cleaning task whose titular, central skill is the 1 mm
snap/normalize step (README failure mode #1, "expected weak-agent failure
mode"). The c749e57 commit had classified the two subchecks that detect a
skipped snap (`no_interior_holes`, `geometry_type_polygon_only`) as
"structural" and left them at weight 1, while applying weight 3 uniformly to
eight "data-content" subchecks - including `canonical_class_vocabulary`, which
catches only the persona's TitleCase house-style (a cosmetic slip; the
per-class-area check already case-folds so casing is never double-penalised).
That inverted severity: skipping the central operation scored 0.931 while a
cosmetic casing slip scored 0.897 (HR-001).

Per-task reweighting:
- The two snap-detection subchecks are this task's primary data-content
  evidence (an unsnapped dissolve yields MultiPolygons riddled with sub-mm
  interior holes). Weighted UP to 3.0 each.
- `canonical_class_vocabulary` (casing) is cosmetic house-style. Weighted
  DOWN to 1.0.
- The genuine pipeline-correctness data-content checks (no_blank_class_rows,
  no_zero_area_geometries, area_m2_recomputed, per_class_area_matches_reference,
  geometric_extent_matches_reference, no_null_or_empty_geometry,
  feature_count_within_tolerance) stay meaningful at weight 2.0.
- Structural / CRS / loose-polygonal checks (geometry_type_polygonal,
  crs_is_canonical, crs_in_meaningful_set) stay at weight 1.0.

Total weight 29 -> 24.

### Weight changes (subcheck: old -> new)

| Subcheck | old | new |
|---|---|---|
| geometry_type_polygonal | 1.0 | 1.0 (unchanged) |
| no_null_or_empty_geometry | 3.0 | 2.0 |
| feature_count_within_tolerance | 3.0 | 2.0 |
| canonical_class_vocabulary | 3.0 | 1.0 |
| no_blank_class_rows | 3.0 | 2.0 |
| no_zero_area_geometries | 3.0 | 2.0 |
| area_m2_recomputed | 3.0 | 2.0 |
| per_class_area_matches_reference | 3.0 | 2.0 |
| geometric_extent_matches_reference | 3.0 | 2.0 |
| no_interior_holes | 1.0 | 3.0 |
| geometry_type_polygon_only | 1.0 | 3.0 |
| crs_is_canonical | 1.0 | 1.0 (unchanged) |
| crs_in_meaningful_set | 1.0 | 1.0 (unchanged) |

### Broken scores (before -> after)

| Broken | before | after | severity note |
|---|---|---|---|
| no_snap | 0.931 | 0.750 | central gotcha (skipped 1 mm snap) - largest drop, as it should be |
| wrong_format | 0.931 | 0.917 | wrong output CRS - structural; mid drop |
| wrong_canonical | 0.897 | 0.958 | cosmetic ALL-CAPS casing - smallest drop |

Inversion fixed: no_snap (0.750) now scores BELOW wrong_canonical (0.958).
Full ordering is monotone and matches severity:
no_snap 0.750 < wrong_format 0.917 < wrong_canonical 0.958 < reference 1.0.

### Prior-run re-grade summary

The two `current` runs at the current task version (post-c749e57 cutoff) per
the prior review block - run-20260608-074701Z and run-20260609-084636Z, both
DeepSeek V4 Flash - were re-graded under the new weights. Both were 1.0 and
remain 1.0: every subcheck passes, so reweighting does not move them. No prior
run shifted (all pre-cutoff runs are stale; no current run had any failing
subcheck). None significant.

### Tests run

- grader on reference: 1.00 (13/13 subchecks, gate passes)
- grader on brokens: no_snap 0.750, wrong_format 0.917, wrong_canonical 0.958
- pytest: not run (orchestrator runs the suite)

### Notes / non-changes

- No threshold, gate, or check logic changed; only `weight=` values.
- No miscalibrated threshold suspected. The snap-tolerance robustness caveat
  (any tolerance >= ~30 um produces the same output) remains an accepted
  low-severity design property, not a grading defect.
