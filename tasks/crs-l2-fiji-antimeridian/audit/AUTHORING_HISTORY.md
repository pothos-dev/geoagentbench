# Implementation notes — crs-l2-fiji-antimeridian

## Status
completed

## Summary
L2 CRS-reprojection task on a hand-crafted GeoJSON of 30 Fiji reef-
transect tracks, 10 of which cross the antimeridian with longitudes
encoded in violation of RFC 7946 §3.1.9. The reference splits each
crossing LineString at ±180°, reprojects parts to EPSG:3460 (Fiji
Map Grid), assembles the output as MultiLineString-per-transect, and
computes `length_m` in the projected CRS.

## Verification results
- Reference grader score: 1.00 (7/7 subchecks)
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0])
  - wrong_crs_metadata_only: 0.286 (expected range [0.2, 0.4])
  - wrong_attributes: 0.857 (expected range [0.8, 0.95])
- Second-run output match: bit-identical (re-ran `reference/generate.py`
  inside Docker; `diff` against pre-run snapshot returned no output)
- Library tests after task: pass (32/32 via `uv run pytest`)

## Failure-mode coverage
- Forgot to reproject / no length_m: broken_wrong_format
- Stamped CRS as 3460 without reprojecting + degree-valued length_m +
  no Multi assembly: broken_wrong_crs_metadata_only
- Dropped vessel / survey_date attributes: broken_wrong_attributes
- Reproject without splitting at antimeridian: principled —
  `antimeridian_crossings_split_into_multi_parts` subcheck (PROJ's
  internal lon-wrap masks the bug at length-computation time, so this
  topology subcheck is the only catch)
- Wrong target CRS (e.g., UTM 60S): principled — Gate 1 EPSG-equality
- One feature per part instead of per transect: principled — Gate 2
  count tolerance + `geometry_type_is_multilinestring` subcheck
- length_m computed in degrees: principled — per-id length match +
  total length subchecks

## Open issues
- [low] OVERTURE_REFERENCE.md's example DuckDB query uses an HTTPS
  Azure blob URL with a `*.parquet` glob. With current DuckDB (1.5.2)
  that path errors out; the s3://overturemaps-us-west-2 path works
  only with an anonymous SECRET block. Same issue flagged by peer CRS
  / FIO / DC tasks. (This task's input is hand-crafted so the issue
  did not bite directly.)

## Suggested prompt changes
- [low] `prompts/task-design-prompt.md`'s "L1/L2 → bundled defaults to
  Overture" guidance is the right default but obscures the legitimate
  "task is intrinsically about a malformed input" exception. The
  current prompt covers the exception adequately (line "Hand-craft a
  file only when the task is *about* a malformed / artificial input")
  but it would help future authors if the antimeridian-crossing case
  were named explicitly alongside mixed-geometry / encoding-issue
  examples.

## Inventory change proposals
(none)

## Library extensions
(none — task uses only existing primitives:
`feature_set_equality_by_id`, `attribute_match`, `count_within_tolerance`)

## Runtime
~30 minutes (input synthesis design, reference pipeline,
broken-solution iteration to land three distinct score ranges,
metadata + README + notes).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The original inventory row defines this task as an L2 CRS-reprojection probe on a hand-crafted GeoJSON of 30 Fiji reef-survey transects, 10 of which cross the antimeridian with vertex pairs jumping +179°→-179° in violation of RFC 7946 §3.1.9. The agent must split the crossings at ±180°, reproject to EPSG:3460 (Fiji 1986 / Fiji Map Grid), re-assemble each transect as one MultiLineString, and compute `length_m` in the projected CRS. The initial-authoring commit (faf98707, 2026-05-08) named the target as "Fiji Map Grid (EPSG:3460)" and bundled the structured output schema as prose plus an "Output schema" bullet block. The README, metadata, broken-solution scores (0.0 / 0.286 / 0.857), and the seven-subcheck grader all date to this first commit.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | faf98707 | initial-authoring | Initial task: instruction, inputs, reference solution, three broken sets, grader, metadata, README. | (initial) |
| 2026-05-08 | 001e459b | docs-change | Path move from `benchmark/` reorg into authoring/ + eval/ subtrees; task files untouched in content. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d535 | docs-change | Path move `benchmark/eval/tasks/` → `benchmark/tasks/`; only path constants. | Commit msg: "tasks are not eval-specific, promote to top-level subdir" |
| 2026-05-13 | 4f0cfc0a | prompt-change | Rewrote instruction: folded the "Output schema:" bullet block into prose. Still named EPSG:3460 and "Fiji Map Grid"; technical content preserved. | Commit msg: "Merge output schema blocks into prose for 6 task instructions, preserving all technical requirements" |
| 2026-05-13 | 89150101 / 1b8dda17 / 3c653731 / cfbdc7c6 | docs-change | Added `image-prompt.md`; generated and regenerated `image.webp` (fal.ai / nano-banana). | Commit msgs cover image-only changes; not design-affecting. |
| 2026-05-14 | d5c283d5 | prompt-change | Stripped input-CRS mention ("WGS84"), the per-vertex jump description ("coordinates jump straight from +179 to -179 on the same vertex pair"), and the column enumeration ("transect_id, vessel, survey_date"). Output CRS, target name "Fiji Map Grid (EPSG:3460)", and output schema preserved. | Commit msg: "Remove input CRS mentions, geometry type descriptions, input column enumerations, and data value examples from 6 CRS task instruction fields. Output requirements are preserved." |
| 2026-05-15 | 7ac5fbe1 | prompt-change | Softened verbs: "Cut the date-line crossings" → "Handle the antimeridian crossings"; dropped "give me each transect back" → "give me each transect"; trimmed "with an honest length_m measured in metres in the projected CRS" → "with a length_m attribute in metres". Target name and EPSG code still present. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-17 | b4583b4a | prompt-change | Replaced "Some lines cross the date line and our previous tooling drew them as 359-degree arcs around the planet" → "Some of these survey lines render as arcs spanning the entire globe instead of short local segments" (dropped explicit "date line" diagnosis). Replaced "Handle the antimeridian crossings properly, project to Fiji Map Grid (EPSG:3460)" → "Fix the geometries so they render correctly, convert them to Fiji's national metric grid" (dropped both the named projection "Fiji Map Grid" and the EPSG code, dropped the explicit "antimeridian" diagnostic noun). Dropped "in EPSG:3460" from filename clause. Replaced "Transects that cross the antimeridian must end up as multi-part geometries with two or more parts after splitting at the date line" → "Problematic transects must end up as multi-part geometries that faithfully represent the actual survey path" (dropped the named technique "splitting at the date line"). | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change | Folder layout reorg: `IMPLEMENTATION_NOTES.md`→`audit/AUTHORING_HISTORY.md`, `data/`→`inputs/`, `reference/{generate.py,outputs}`→`reference/solution/...`, `tests/`→`reference/failures/`, `image.*`→`assets/`. Only path strings inside files; task content unchanged. | Commit msg: "Reorganize task folder layout — separates audience concerns" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit b4583b4, class: prompt-change). Later commit 29a9ae3 (2026-05-26) is a folder layout reorg only — paths inside files, no answer-key or instruction content change — so it does not advance the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T12:55:43Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:27:49Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T07:51:19Z | 0.0 | done | current |

Stale runs (pre-cutoff, not used as evidence): 24 earlier runs spanning 2026-05-12 to 2026-05-17 (before 12:48Z), all pre-date the most recent prompt-strip and were grading an earlier, less-stripped instruction. Listed for completeness only.

#### Verdict
**calibrated**

Scores span the expected range across agents of varying capability: two strong models (Opus 4.6, DeepSeek V4 Flash) land 1.0 with all seven subchecks passing; one weaker model (Gemma 4 26B) lands 0.0 at Gate 1. Inspection of the Gemma transcript (ev 4 / ev 8 of `run-20260526-0748Z/.../transcript.json`) shows the agent looked up "Fiji's national metric grid", confidently asserted "EPSG:2978 (Fiji Redefined / Fiji Grid)", and wrote the output stamped as EPSG:2978. EPSG:2978 is actually "NAD83(NSRS2007) / California zone 4" — a model-knowledge error, not a prompt-ambiguity error. The stronger models correctly inferred Fiji Map Grid = EPSG:3460. This is exactly the kind of capability the post-strip prompt is designed to discriminate. The grader correctly rejected EPSG:2978 at the Gate 1 EPSG-equality check (grade.py:66, README failure mode #5 "Reproject into the wrong target CRS").

No `current` run produced an output that looked correct but scored 0; no `current` run scored 1.0 trivially without exercising the full pipeline. Per-id length, total length, antimeridian split count, and FMG envelope all distinguished correct from broken outputs as designed. The grader on `reference/solution/outputs/` reproduces 7/7 with bit-identical numbers to the recorded broken-set baselines.

#### Specific findings
- The post-strip instruction ("Fiji's national metric grid", no EPSG code, no "Fiji Map Grid" name) is more aggressive than the instruction-stripping guide's "Named projections stay when they ARE the answer" rule would suggest for a CRS-reprojection task. The current instruction reads as a `geometric_ops`-flavoured framing ("fix the geometries", "convert to a grid") rather than a CRS-reprojection one. Both strong agents inferred the EPSG code from general Fiji knowledge, so the task remains solvable, and the Gate 1 EPSG-equality requirement still principally catches the wrong-CRS class. But the prompt as currently worded is borderline against the published stripping guide. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decide whether to restore "Fiji Map Grid (EPSG:3460)" in the instruction (per the stripping-guide carve-out for CRS-reprojection tasks where the target CRS *is* the goal) or to keep the current stripped wording (which the commit message labels a deliberate "nudge removal"). The current behavior is defensible either way; flagging rather than reverting unilaterally.
- The dropped "antimeridian" diagnostic noun (replaced by "render as arcs spanning the entire globe") is a stronger strip — it forces the agent to recognise the cause from the symptom, which is the L2 failure-recognition step. This is well-aligned with the task's stated purpose (README "What this task probes" #1: "Recognise that the input violates RFC 7946 §3.1.9") and should stay.
- Gemma's failure is a textbook model-side knowledge error (wrong EPSG code from confused recall). Per the evaluator-prompt's "Model-side failures are not task problems" rule, this is not evidence the task is mis-calibrated and no task change is proposed for it.
- Two pre-cutoff runs (run-20260514 and run-20260515 windows) hit the task before the 17-May strip; their scores are not used because they evaluated a different instruction.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — Current instruction strips both "Fiji Map Grid" and "EPSG:3460" in tension with the instruction-stripping guide's "Named projections stay when they ARE the answer" carve-out for CRS-reprojection tasks. Restore-vs-keep is a design call.

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row, this is an L2 CRS-reprojection probe on a hand-crafted GeoJSON of 30 Fiji reef-survey transects, 10 of which cross the antimeridian with consecutive vertices hopping +179°→-179° in violation of RFC 7946 §3.1.9. The agent must split the crossings at ±180°, reproject to EPSG:3460 (Fiji 1986 / Fiji Map Grid), re-assemble each transect as one MultiLineString, and compute `length_m` in the projected CRS. The initial-authoring commit (faf98707, 2026-05-08) shipped the instruction, hand-crafted input, reference solution, three broken sets, the seven-subcheck grader, metadata (tolerances + broken scores 0.0 / 0.286 / 0.857), and README.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | faf98707 | initial-authoring | Initial task: instruction, inputs, reference solution, three broken sets, grader, metadata, README. | (initial) |
| 2026-05-08 | 001e459b | docs-change | Repo reorg: split `benchmark/` into authoring/ + eval/ subtrees; task content untouched. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d535 | docs-change | Path move `benchmark/eval/tasks/` → `benchmark/tasks/`; path constants only. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 89150101 / 1b8dda17 / 3c653731 / cfbdc7c6 | docs-change | Added `image-prompt.md`; generated/regenerated `image.webp`. | Commit msgs cover image-only changes; not design-affecting. |
| 2026-05-13 | 4f0cfc0a | prompt-change | Folded the "Output schema:" bullet block into prose; still named EPSG:3460 and "Fiji Map Grid"; technical content preserved. | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d5 | prompt-change | Stripped input-CRS mention ("WGS84"), the per-vertex jump description, and the column enumeration. Output CRS, "Fiji Map Grid (EPSG:3460)", and output schema preserved. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-15 | 7ac5fbe1 | prompt-change | Softened verbs; trimmed "honest length_m measured in metres in the projected CRS" → "length_m attribute in metres". Target name and EPSG code still present. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-17 | b4583b4a | prompt-change | Dropped the named projection "Fiji Map Grid" and the EPSG code (→ "Fiji's national metric grid"), dropped the explicit "antimeridian"/"date line" diagnostic nouns (→ symptom-only "render as arcs spanning the entire globe"), dropped the named technique "splitting at the date line". | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change | Folder layout reorg (`IMPLEMENTATION_NOTES.md`→`audit/AUTHORING_HISTORY.md`, `data/`→`inputs/`, `reference/{generate.py,outputs}`→`reference/solution/...`, `tests/`→`reference/failures/`, `image.*`→`assets/`). Path strings only. | Commit msg: "Reorganize task folder layout — separates audience concerns" |
| 2026-05-26 | 32aa3f4e | docs-change | Prior evaluator review (AUTHORING_HISTORY append, coverage.yaml, status.json). | Commit msg: "Re-evaluate crs-l2-fiji-antimeridian: calibrated; 1 med flag on stripped CRS name" |

This re-evaluation confirms the prior evaluator's (2026-05-26) reconstruction: no design-affecting commit has touched the task since b4583b4a. The working tree for the task dir is clean and no commit since 32aa3f4e touches the task directory.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit b4583b4a, class: prompt-change). All later commits (29a9ae3 folder reorg, 32aa3f4 prior evaluator artefacts) are docs-change and do not advance the cutoff. Unchanged from the prior review.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T12:55:43Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-05-17T14:27:49Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T07:51:19Z | 0.0 | done | current |

No new runs have touched this task since the prior review; the three `current` runs are identical to those it considered. Stale runs (pre-cutoff, not used as evidence): 24 earlier runs spanning 2026-05-12 to 2026-05-17 (before 12:48Z), all grading a less-stripped instruction. Listed for completeness only.

#### Output / CRS consistency
- Reference output CRS = EPSG:3460; `expected_outputs[].crs` = EPSG:3460; README "Output" section = EPSG:3460. All three agree.
- The grader reprojects **neither** side: it gates on `sub.crs.to_epsg() == 3460` (grade.py:66) and compares lengths each computed in its own already-metric 3460 CRS. No one-sided reprojection — Step 2c-CRS satisfied.
- Verified outputs directly: Opus 4.6 and DeepSeek both emit 30 MultiLineStrings in EPSG:3460 with total length 6,109,536.5 m and bounds identical to the reference. Gemma stamped EPSG:2978 (NAD83(NSRS2007)/California zone 4 — not a Fiji CRS), bounds ≈(-4.46e6, 7.34e6 … -3.47e6, 7.76e6) far outside the FMG envelope; Gate 1 EPSG-equality rejected it → 0.0.

#### Verdict
**calibrated**

Scores span a sensible range across agents of varying capability. Two strong models (Opus 4.6, DeepSeek V4 Flash) reach 1.0 with all seven subchecks passing and outputs numerically identical to the reference; one weaker model (Gemma 4 26B) lands 0.0 at Gate 1 because it recalled the wrong EPSG code (2978) for "Fiji's national metric grid". That is a model-knowledge error, not a prompt-ambiguity error — exactly the discrimination the post-strip instruction is designed to produce, and exactly the wrong-target-CRS class the Gate 1 EPSG-equality check (README failure mode #5) is built to catch. No `current` run produced a correct-looking output that scored low, and no run scored 1.0 without exercising the full split→reproject→assemble→measure pipeline. Re-grading the reference reproduces 7/7 with bit-identical numbers, and the three broken sets reproduce their recorded scores (0.0 / 0.286 / 0.857), confirming the grader still discriminates cleanly across the range.

#### Specific findings
- The post-strip instruction names neither the projection ("Fiji Map Grid") nor the EPSG code, leaving only "Fiji's national metric grid". For a CRS-reprojection task where the target CRS *is* the deliverable, that is more aggressive than the May prompt-strip guidance's "named projection stays when it IS the answer" carve-out for CRS tasks. Both strong agents still inferred EPSG:3460 from general Fiji knowledge, so the task remains solvable and Gate 1 still catches the wrong-CRS class — but restore-vs-keep is a genuine design call, not an evaluator call. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decide whether to restore "Fiji Map Grid (EPSG:3460)" in the instruction (per the CRS-task carve-out where the target CRS is the goal) or keep the current stripped wording (commit b4583b4a deliberately labels this a "nudge removal"). Defensible either way; flagging rather than reverting unilaterally. (Re-raise of the prior review's HR-001 — unchanged.)
- The dropped "antimeridian"/"date line" diagnostic noun (replaced by the symptom "render as arcs spanning the entire globe") is the intended L2 failure-recognition step and aligns with the README's "What this task probes" #1. It should stay.
- Gemma's 0.0 is a textbook model-side knowledge error; per the evaluator-prompt "Model-side failures are not task problems" rule it is not evidence of mis-calibration and no task change is proposed for it.
- coverage.yaml axes re-validated against coverage-vocabulary.yaml and the inventory row: all slugs valid, no vocabulary gap. EPSG:3460 (Fiji Map Grid, transverse Mercator) → `conformal`; "MultiLineString assembly" → `collect`; antimeridian crossings captured by `crs_variants: [antimeridian-crossing]` (no `split` slug exists, which is correct — splitting is the Axis-4 variant, not a geometric op). No change needed.

### 3. Changes applied this run

#### Unilateral edits
- (none) — task state is unchanged since the prior review; grader and pytest both green; nothing met the unilateral-edit bar.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — Current instruction strips both "Fiji Map Grid" and "EPSG:3460" in tension with the CRS-task carve-out where the target CRS is the goal. Restore-vs-keep is a design call. (Re-raise of prior HR-001; still med, still unresolved.)

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- broken sets re-graded: wrong_format 0.0, wrong_crs_metadata_only 0.286, wrong_attributes 0.857 (match metadata)
- pytest: pass (35/35)

---

## Review pass — 2026-05-28 (HR-001 resolution via CRS accept-list refactor)

Operator decision on the standing HR-001 (re-raised through three prior passes): apply the same CRS accept-list refactor pattern as `spa-l3-paris-emergency-routing` (commit 377a593) and `spa-l2-lagos-hotspot-overlaps` (commit 0888e6f) instead of restoring the explicit EPSG name. The current instruction wording ("Fiji's national metric grid") already matches the category-hint doctrine introduced in 0888e6f; what was missing was the matching grader softening.

### Changes applied
- `grade.py`:
  - Imported `check_and_normalize_crs`.
  - Added `OFFICIAL_CRS_EPSG = 3460` and `ACCEPTED_CRS_EPSGS = {3460, 32760}` module constants.
  - Replaced the hand-rolled Gate-1 CRS hard-check (`sub.crs.to_epsg() == 3460`) with one helper call; submissions in UTM 60S are reprojected into Fiji Map Grid before any spatial subcheck runs.
  - Inserted new subcheck 0 `official_crs_used` that rewards the regional canonical (EPSG:3460); the remaining seven subchecks are unchanged.
- `metadata.yaml`: rationale block extended to document the accept-list and the antimeridian-topology argument (UTM 60S submissions still have to deal with the +180° wrap); `broken_solutions` measured scores refreshed under the eight-subcheck grader (`wrong_format` 0.0 → 0.0, `wrong_crs_metadata_only` 0.286 → 0.375, `wrong_attributes` 0.857 → 0.875); expected_score_ranges shifted to match.
- `README.md`: failure-mode #5 rewritten — UTM 60S is now an accepted-but-non-canonical pick scored 7/8, not a Gate-1 reject. Weak-agent failure mode score updated from 6/7 ≈ 0.857 to 7/8 = 0.875, with a note about the 6/8 case for the combined UTM-60S-plus-no-split path.
- `task.json`: `version` 1 → 2 (grade.py change requires bump under the 622342b versioning policy). Instruction text unchanged.
- `audit/status.json`: verdict `calibrated`, `human_review_items: []`.

### Verification
- Reference: 1.0 (8/8).
- Brokens (current grader): `wrong_format` 0.0, `wrong_crs_metadata_only` 0.375 (3/8), `wrong_attributes` 0.875 (7/8).
- Smoke test: a UTM-60S copy of the reference (built via `to_crs(32760)`) grades 0.875 (7/8) — fails only `official_crs_used`. Confirms the (N-1)/N partial-credit shape: a defensible-but-non-canonical pick is no longer collapsed to 0.0 at Gate 1.
- pytest: pass (33/33 on `tests/test_comparisons.py`).

### Doctrine note
HR-001 sat for three passes because two policies overlapped at this task. The instruction-stripping guide line 43 ("Named projections stay when they ARE the answer") argued for restoring "Fiji Map Grid (EPSG:3460)"; the freshly-tightened CRS-accept-list doctrine (introduced in 0888e6f) argued for a category-level hint ("the national grid") plus a softened Gate 1. The accept-list refactor lets both doctrines coexist: the prompt stays at the category hint, Gate 1 stops being a knowledge-trivia check, and `official_crs_used` continues to reward the canonical pick. Follow-up candidates flagged for the same treatment: `crs-l1-nyc-webmercator-cycleways`, `crs-l1-paris-lambert93`, `crs-l2-svalbard-polar-areas`, `crs-l3-tokyo-jgd-crossings` — all stripped by the same b4583b4 commit.

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row, this is an L2 CRS-reprojection probe on a hand-crafted GeoJSON of 30 Fiji reef-survey transects, 10 of which cross the antimeridian with consecutive vertices hopping +179°→-179° in violation of RFC 7946 §3.1.9. The agent must split the crossings at ±180°, reproject to a Fiji-appropriate metric CRS (regional canonical: EPSG:3460 / Fiji 1986 / Fiji Map Grid; UTM 60S also accepted), re-assemble each transect as one MultiLineString, and compute `length_m` in the projected CRS. The initial-authoring commit (faf98707, 2026-05-08) shipped the instruction, hand-crafted input, reference solution, three broken sets, the seven-subcheck grader, metadata (tolerances + broken scores 0.0 / 0.286 / 0.857), and README; the task has since been stripped (b4583b4, 2026-05-17) and softened on the grader side (e8a5308, 2026-05-28) into its current eight-subcheck form.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | faf98707 | initial-authoring | Initial task: instruction, inputs, reference solution, three broken sets, grader, metadata, README. | (initial) |
| 2026-05-08 | 001e459b | docs-change | Repo reorg: `benchmark/` split into authoring/ + eval/ subtrees; task content untouched. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d535 | docs-change | Path move `benchmark/eval/tasks/` → `benchmark/tasks/`; path constants only. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 89150101 / 1b8dda17 / 3c653731 / cfbdc7c6 | docs-change | Added `image-prompt.md`; generated/regenerated `image.webp`. | Commit msgs cover image-only changes; not design-affecting. |
| 2026-05-13 | 4f0cfc0a | prompt-change | Folded the "Output schema:" bullet block into prose; still named EPSG:3460 and "Fiji Map Grid". | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d5 | prompt-change | Stripped input-CRS mention ("WGS84"), the per-vertex jump description, and the column enumeration. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-15 | 7ac5fbe1 | prompt-change | Softened verbs; trimmed "honest length_m measured in metres in the projected CRS" → "length_m attribute in metres". Target name and EPSG code still present. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-17 | b4583b4a | prompt-change | Dropped the named projection "Fiji Map Grid" and the EPSG code (→ "Fiji's national metric grid"); dropped the "antimeridian"/"date line" diagnostic nouns; dropped the named technique "splitting at the date line". | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change | Folder layout reorg (`IMPLEMENTATION_NOTES.md`→`audit/AUTHORING_HISTORY.md`, `data/`→`inputs/`, `reference/{generate.py,outputs}`→`reference/solution/...`, `tests/`→`reference/failures/`, `image.*`→`assets/`). Path strings only. | Commit msg: "Reorganize task folder layout — separates audience concerns" |
| 2026-05-26 | 32aa3f4e | docs-change | Prior evaluator review (AUTHORING_HISTORY append, coverage.yaml, status.json). | Commit msg: "Re-evaluate crs-l2-fiji-antimeridian: calibrated; 1 med flag on stripped CRS name" |
| 2026-05-27 | 4ceea9c1 | docs-change | Second evaluator pass; HR-001 re-raised, no edits. | Commit msg: "Re-evaluate crs-l2-fiji-antimeridian: calibrated, no edits, 1 med flag re-raised" |
| 2026-05-28 | 622342be | (repo-wide, no task content change) | Added `version` field to `task.json` schema; this task initialised at `version: 1`. | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | e8a53085 | grader-change (+ prompt-change touching task.json, docs-change) | Resolved standing HR-001 via the CRS accept-list refactor: Gate 1 now accepts {3460, 32760} and reprojects UTM 60S submissions into Fiji Map Grid; new `official_crs_used` subcheck (slot 0) rewards the canonical pick (8 subchecks total); `metadata.yaml` rationale extended; broken `measured_score`s refreshed (0.286→0.375, 0.857→0.875); README failure-mode #5 rewritten; `task.json` version 1→2 (instruction text unchanged). | Commit msg: "Resolve crs-l2-fiji HR-001 via CRS accept-list refactor" |

No new commits have touched this task directory since e8a53085.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T07:52:01+00:00** (commit e8a53085, class: grader-change with task.json/instruction-contract touches via the version bump). This advances the cutoff from the prior review's 2026-05-17 value because grade.py gained an accept-list helper and a new subcheck, and `task.json.version` bumped 1→2 — both invalidate any run scored under the seven-subcheck grader. The intervening 622342be is a repo-wide schema addition (introduces the `version` field) and does not by itself change what the agent sees or how it is scored.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T01:17:09Z | 1.0 | done | stale (pre-cutoff; graded by the 7-subcheck grader) |
| run-20260528-0317Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T03:18:59Z | 0.0 | done | stale (pre-cutoff) |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:18:56Z | 1.0 | done | stale (pre-cutoff) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:22:49Z | 0.0 | done | stale (pre-cutoff) |
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T12:55:43Z | 1.0 | done | stale (pre-cutoff) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:27:49Z | 1.0 | done | stale (pre-cutoff) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:51:19Z | 0.0 | done | stale (pre-cutoff) |

**No `current` runs exist** for the new (post-e8a5308) eight-subcheck grader. All 31 runs in `benchmark/eval/runs/*/crs-l2-fiji-antimeridian/` predate 2026-05-28T07:52Z and were scored against the seven-subcheck grader. The orchestrator's next sweep will produce current evidence; until then, the verdict has to rest on the in-repo verification documented in the e8a5308 commit (8/8 reference, brokens reproducible, UTM-60S smoke 7/8) rather than on independent agent runs.

#### Output / CRS consistency (2c-CRS)
- Reference output CRS = EPSG:3460; `task.json.expected_outputs[].crs` = EPSG:3460; README "Output" section = EPSG:3460; coverage.yaml `crs_variants` = [wgs84, conformal, antimeridian-crossing]. All consistent.
- Gate 1 accepts EPSG ∈ {3460, 32760}. A 32760 submission is reprojected into 3460 via `check_and_normalize_crs` before any spatial subcheck runs — one-sided reprojection of the submission **into** the canonical CRS, implementing the declared accept-list policy. This is explicitly the shape Step 2c-CRS permits ("One-sided reprojection of the submission into the canonical CRS is also fine when it implements a declared accept-list policy"). Reference output stays in 3460; no reference-side reprojection.
- `official_crs_used` rewards the canonical EPSG:3460 pick separately from the spatial subchecks, giving a (N-1)/N partial-credit shape rather than a Gate-1 collapse.

#### Verdict
**insufficient-evidence**

No `current` runs are available after the 2026-05-28T07:52Z cutoff, so the eight-subcheck grader has not yet been exercised end-to-end by any system under test. The in-repo verification recorded with e8a5308 (reference 1.0 = 8/8, brokens 0.0 / 0.375 / 0.875, UTM-60S smoke 0.875) reproduces locally on the current tree and is consistent with the metadata, README, and broken-set fixtures; pytest is green (41/41); and the prior evaluator's analysis of the seven-subcheck grader's calibration (two strong models at 1.0, one weak at 0.0 on a textbook model-side EPSG-recall error, no false negatives among correct-looking outputs) remains the best available proxy for what the new grader will see. But because the new official_crs_used subcheck has only ever been exercised on the locally-built UTM-60S smoke copy — not on a real agent submission in UTM 60S — there is no independent evidence that the (N-1)/N partial-credit shape actually fires on a non-canonical-but-defensible pick in practice. That is a `insufficient-evidence` situation by the verdict rubric; the orchestrator's next sweep should be enough to upgrade it.

#### Specific findings
- The 2c-CRS check is satisfied under the new accept-list policy (see above); no `prompt-grader-inconsistent` finding.
- coverage.yaml axes re-validated against coverage-vocabulary.yaml: `crs-reprojection`, `l2`, `collect`, `geojson`, `wgs84` + `conformal` + `antimeridian-crossing`, `bundled-local`, `linestring` + `multilinestring`, `fiji`, `small` — all slugs valid. No vocabulary gap.
- Tolerances re-read against the new metadata.yaml rationale block. The accept-list extension does not change any tolerance — it only adds the `official_crs_used` reward channel — so the count_pct=0.05 / jaccard_min=0.95 / length_pct=0.01 trio inherited from the original review still applies and remains principled for a deterministic PROJ-driven reprojection.
- Refreshed broken `measured_score`s (0.0 / 0.375 / 0.875) reproduce on the current tree under `cd benchmark/eval && uv run python ../tasks/crs-l2-fiji-antimeridian/grade.py ../tasks/crs-l2-fiji-antimeridian/reference/failures/broken_<class>/outputs`; ranges in metadata.yaml ([0.0, 0.0], [0.3, 0.45], [0.85, 0.95]) bracket each refreshed score. No range-shift drift.
- HR-001 from the prior three passes has been retired by e8a5308. No new HR-NNN markers raised this pass.

### 3. Changes applied this run

#### Unilateral edits
- (none) — task state is unchanged since the e8a5308 HR-001 resolution; grader and pytest both green; nothing met the unilateral-edit bar.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none) — HR-001 was resolved by e8a5308; no new flags raised.

#### Tests run
- grader on reference: 1.0 (8/8 subchecks)
- pytest: pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row, this is an L2 CRS-reprojection probe on a hand-crafted GeoJSON of 30 Fiji reef-survey transects, 10 of which cross the antimeridian with consecutive vertices jumping +179°→-179° in violation of RFC 7946 §3.1.9. The agent must split the crossings at ±180°, reproject to a Fiji-appropriate metric CRS (regional canonical EPSG:3460 / Fiji 1986 / Fiji Map Grid; UTM 60S also accepted by the post-e8a5308 grader), re-assemble each transect as one MultiLineString, and compute `length_m` in the projected CRS. The initial-authoring commit (faf98707, 2026-05-08) shipped instruction, hand-crafted input, reference solution, three broken sets, the seven-subcheck grader, metadata, and README. Subsequent passes stripped the instruction (b4583b4), softened the grader to an accept-list with `official_crs_used` (e8a5308), then softened again repo-wide to the soft-CRS / `grade_crs_soft` policy that replaced `official_crs_used` with two subchecks (`crs_is_canonical`, `crs_in_meaningful_set`, 05aabd64).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | faf98707 | initial-authoring | Initial task: instruction, inputs, reference solution, three broken sets, grader, metadata, README. | (initial) |
| 2026-05-08 | 001e459b | docs-change | Repo reorg: `benchmark/` split into authoring/ + eval/ subtrees; task content untouched. | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d535 | docs-change | Path move `benchmark/eval/tasks/` → `benchmark/tasks/`; path constants only. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 89150101 / 1b8dda17 / 3c653731 / cfbdc7c6 | docs-change | Added `image-prompt.md`; generated/regenerated `image.webp`. | Commit msgs cover image-only changes; not design-affecting. |
| 2026-05-13 | 4f0cfc0a | prompt-change | Folded the "Output schema:" bullet block into prose; still named EPSG:3460 and "Fiji Map Grid". | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d5 | prompt-change | Stripped input-CRS mention, per-vertex jump description, column enumeration. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-15 | 7ac5fbe1 | prompt-change | Softened verbs; trimmed length_m phrasing. Target name and EPSG still present. | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-17 | b4583b4a | prompt-change | Dropped named projection "Fiji Map Grid" and EPSG code (→ "Fiji's national metric grid"); dropped "antimeridian"/"date line" nouns. | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change | Folder layout reorg; path strings only. | Commit msg: "Reorganize task folder layout — separates audience concerns" |
| 2026-05-26 | 32aa3f4e | docs-change | Prior evaluator review (AUTHORING_HISTORY append, coverage.yaml, status.json). | Commit msg: "Re-evaluate crs-l2-fiji-antimeridian: calibrated; 1 med flag on stripped CRS name" |
| 2026-05-27 | 4ceea9c1 | docs-change | Second evaluator pass; HR-001 re-raised, no edits. | Commit msg: "Re-evaluate crs-l2-fiji-antimeridian: calibrated, no edits, 1 med flag re-raised" |
| 2026-05-28 | 622342be | (repo-wide, no task content change) | Added `version` field to `task.json` schema; this task initialised at `version: 1`. | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | e8a53085 | grader-change (+ task.json version bump) | Resolved standing HR-001 via the CRS accept-list refactor: Gate 1 accepts {3460, 32760} and reprojects 32760 into 3460; new `official_crs_used` subcheck rewards canonical; broken `measured_score`s refreshed; task.json version 1→2. | Commit msg: "Resolve crs-l2-fiji HR-001 via CRS accept-list refactor" |
| 2026-05-28 | ea1e0be9 | docs-change | Third evaluator pass; insufficient-evidence verdict because no current runs against e8a5308 grader. | Commit msg: "Re-evaluate crs-l2-fiji-antimeridian: insufficient-evidence on new 8-subcheck grader; no unilateral edits" |
| 2026-05-28 | 05aabd64 | grader-change | Repo-wide soft-CRS refactor: `grade_crs_soft` helper, Gate 1 only hard-fails on unparseable CRS, otherwise reprojects to canonical for spatial subchecks and docks via two new subchecks (`crs_is_canonical`, `crs_in_meaningful_set`). For this task the existing accept-list {3460, 32760} carried over; `official_crs_used` renamed to `crs_is_canonical`. Total subchecks now 9. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" |

No new commits have touched this task directory since 05aabd64.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57+00:00** (commit 05aabd64, class: grader-change). The soft-CRS refactor renamed the CRS subcheck, added a second CRS subcheck, and changed the gate-1 policy from hard accept-list to soft reproject; it advances the cutoff past e8a5308. The repo-wide 622342b is a schema-only addition and does not advance the cutoff on its own.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic (opus / claude-opus-4-7) | 2026-05-28T19:28:57Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:26:09Z | 0.556 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (opus / claude-opus-4-7) | 2026-05-28T23:34:21Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:10:48Z | 0.667 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T09:07:34Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:53:06Z | 0.444 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:32:32Z | 0.556 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:37:46Z | failed | (model-side: max iterations exceeded, 75) | current |

Stale runs (pre-cutoff, not used as evidence): 23 earlier runs spanning 2026-05-12 to 2026-05-28T16:26Z, listed for completeness.

#### Output / CRS consistency (2c-CRS)
- Reference output CRS = EPSG:3460; `task.json.expected_outputs[].crs` = EPSG:3460; README "Output" section = EPSG:3460; coverage.yaml `crs_variants` = [wgs84, conformal, antimeridian-crossing]. All consistent.
- Gate 1 is soft (`grade_crs_soft`): any parseable CRS passes, the submission is reprojected into 3460 for spatial subchecks, and the two CRS subchecks dock the agent's pick. One-sided reprojection of the submission **into** the canonical CRS, implementing a declared accept-list / canonical-reward policy. Explicitly permitted by Step 2c-CRS ("One-sided reprojection of the submission into the canonical CRS is also fine when it implements a declared accept-list policy").
- Reference stays in 3460; no reference-side reprojection.

#### Verdict
**calibrated**

Scores span a sensible range across agents of varying capability:
- Three strong-model runs (Opus 4.7 x2, DeepSeek V4 Pro) land 1.0 with 9/9 subchecks. Their outputs are numerically identical to the reference.
- Five Gemma 4 26B runs land between 0.444 and 0.667. Inspection of run-20260606-1129Z's output shows EPSG:2977 stamped (Tahaa 54 / UTM zone 5S — French Polynesia, not Fiji) — a textbook model-side EPSG-recall error. Coordinates are nonetheless in 2977 metres, so the soft-CRS reprojection lands them in the FMG envelope and the spatial subchecks largely pass; the two CRS subchecks correctly fail. This is exactly the (N-2)/N shape the soft-CRS policy is designed to produce for "geometry correct, CRS wrong" outputs.
- One Gemma run failed with `max iterations exceeded (75)` — model-side iteration-budget exhaustion, not a task problem.

No `current` run produced a correct-looking output that scored 0 (the soft-CRS policy explicitly precludes this — the only way to score 0 now is to fail Gate 1 entirely, which requires no usable CRS at all or a missing length_m / transect_id). Re-grading the reference reproduces 9/9 with bit-identical numbers. Re-grading a synthesised UTM-60S copy of the reference scores 8/9 ≈ 0.889 — `crs_is_canonical` is the single failing subcheck, confirming the canonical-vs-meaningful partial-credit shape works end-to-end. The 0.556 / 0.667 Gemma scores represent realistic L2-failure paths (wrong CRS family + partial topology / length issues), which is the discrimination the task is built to produce.

#### Specific findings
- The README and metadata.yaml prose still referred to the pre-05aabd64 grader (`official_crs_used` subcheck name; 7/8 and 6/8 score denominators; "3/8 = 0.375", "7/8 = 0.875" in broken-set descriptions). These are documentation drift from the soft-CRS rename and have been refreshed in this pass. Broken-set `measured_score` values shifted under the new 9-subcheck grader: `wrong_crs_metadata_only` 0.375 → 0.444 (4/9), `wrong_attributes` 0.875 → 0.889 (8/9). Both refreshed values remain inside their stored `expected_score_range`, so the ranges did not need to widen.
- `task.json` was missing the human-facing `analyst_notes` field; added in this pass per the evaluator-prompt schema. Covers the antimeridian-encoding gotcha first, then mundane attribute / length / EPSG-recall failure modes.
- coverage.yaml axes re-validated against coverage-vocabulary.yaml. All slugs still valid: `crs-reprojection`, `l2`, `collect`, `geojson`, `wgs84` + `conformal` + `antimeridian-crossing`, `bundled-local`, `linestring` + `multilinestring`, `fiji`, `small`. No vocabulary gap; only the `evaluator_run_at` timestamp was bumped.
- Tolerances re-read against the metadata.yaml rationale block. The soft-CRS refactor changes the gate-1 policy but not the spatial tolerances (count_pct=0.05 / jaccard_min=0.95 / length_pct=0.01) — those still apply unchanged and remain principled for a deterministic PROJ-driven reprojection.
- The "Gemma's max-iterations failure" is model-side per the evaluator-prompt "Model-side failures are not task problems" rule and is not evidence of mis-calibration.

### 3. Changes applied this run

#### Unilateral edits
- `README.md`: Updated failure-mode #5 and the weak-agent failure-mode prose to reflect the soft-CRS grader (renamed subcheck `official_crs_used` → `crs_is_canonical`; corrected denominators 7/8 → 8/9, 6/8 → 7/9; documented that out-of-meaningful-set CRSes no longer Gate-1-fail but lose both CRS subchecks). Re-grade on reference: 1.0 (9/9). Reason: doc drift from commit 05aabd64.
- `metadata.yaml`: Rewrote the rationale block's accept-list paragraph to describe the soft-CRS / two-subcheck shape, refreshed `broken_solutions[].description` prose for all three sets, and updated `measured_score` values (wrong_crs_metadata_only 0.375 → 0.444, wrong_attributes 0.875 → 0.889). Ranges unchanged (refreshed scores remain bracketed). Re-grade on reference: 1.0 (9/9). Reason: doc drift; `measured_score` refresh is explicitly allowed without version bump.
- `task.json`: Added `analyst_notes` with description, approach, and pitfalls; instruction text unchanged; no `version` bump (analyst_notes is human-facing only). Re-grade on reference: 1.0 (9/9).
- `coverage.yaml`: bumped `evaluator_run_at` to 2026-06-06. No axis changes.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none) — all findings were either refreshable doc drift or already-resolved by upstream commits.

#### Tests run
- grader on reference: 1.0 (9/9 subchecks)
- broken sets re-graded: wrong_format 0.0 (0/0 — gate fails on missing length_m), wrong_crs_metadata_only 0.444 (4/9), wrong_attributes 0.889 (8/9). UTM-60S smoke (reproject reference to 32760) scores 0.889 (8/9, fails only `crs_is_canonical`).
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
- Geom-type LineString-family check from Gate 2 dropped — already
  covered (more strictly) by the existing
  `geometry_type_is_multilinestring` subcheck.
- Feature-count-within-5%-of-reference migrated from Gate 2 to a new
  `feature_count_within_5_percent` subcheck.
- Subcheck count grew from 9 to 10.

### Verification
- Reference solution re-graded: 1.0 (10/10 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row, this is an L2 CRS-reprojection probe on a hand-crafted GeoJSON of 30 Fiji reef-survey transects, 10 of which cross the antimeridian with consecutive vertices jumping +179° to -179° in violation of RFC 7946 §3.1.9. The agent must split the crossings at ±180°, reproject to a Fiji-appropriate metric CRS (regional canonical EPSG:3460 / Fiji 1986 / Fiji Map Grid; UTM 60S accepted as the defensible generic pick), re-assemble each transect as one MultiLineString, and compute `length_m` in the projected CRS. The history through 2026-06-06 is reconstructed in the four prior evaluator blocks and is confirmed unchanged; this block covers the two design-affecting commits since.

#### Change log (since prior evaluator block of 2026-06-06)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | d9d90e09 | docs-change | Prior evaluator pass: README/metadata soft-CRS doc refresh, analyst_notes added, coverage timestamp. | Commit msg: "Re-evaluate crs-l2-fiji-antimeridian: calibrated; refresh soft-CRS docs and add analyst_notes" |
| 2026-06-06 | 363aed21 | grader-change | Dropped the `structural_correctness` gate; geom-type gate check removed (already covered more strictly by `geometry_type_is_multilinestring`); count-within-5% migrated from Gate 2 to a new `feature_count_within_5_percent` subcheck; subchecks 9 → 10. Documented in the "Manual cleanup 2026-06-06" block above. | Commit msg: benchmark-wide "Drop Gate 2 from graders; one hard gate, rest are subchecks" |
| 2026-06-07 | 05b389bc | grader-change | Six data-content subchecks (feature count, transect_id set, per-transect length, total length, antimeridian split, identifying attributes) re-tagged `weight=3.0`; the four schema/CRS subchecks (geometry type, FMG envelope, crs_is_canonical, crs_in_meaningful_set) stay weight 1.0. Total weight 22. | Commit msg: "Weight data-content subchecks 3x in CRS graders" — so a clean-schema-wrong-data submission scores visibly lower than a correct-data slightly-off-schema one. |

Note: neither 363aed21 nor 05b389bc bumped `task.json.version` (stayed at 2) although both change scoring. The timestamp cutoff covers run validity; this pass's version bump (2 → 3, for the instruction edit below) also fingerprints the new grader generation.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:28:18+00:00 (commit 05b389bc, class: grader-change). The Gate-2 removal (363aed21, 2026-06-06T20:11:02Z) is the penultimate design-affecting commit; d9d90e09 and later doc-only commits do not advance the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T07:55:34Z | 1.0 | done | current (suite sha 6510297 contains 05b389bc; version 2 = pre-edit current) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T08:53:43Z | 1.0 | done | current (suite sha ec540aa; version 2) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T11:28:20Z | 0.636 | failed (model-side: max iterations exceeded, 75) | stale (pre-cutoff) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T17:39:55Z | 0.556 | done | stale (pre-cutoff) |

Stale footnote: 40 further runs from 2026-05-12 through 2026-06-06T13:37Z predate the cutoff (they were graded by the unweighted 9-/10-subcheck or earlier graders) and were considered only as background; the 2026-06-06 evaluator block analyses them in detail.

#### Output / CRS consistency (2c-CRS)
- Reference output CRS = EPSG:3460; `task.json.expected_outputs[].crs` = EPSG:3460; README Output section = EPSG:3460. All agree.
- Gate 1 is soft (`grade_crs_soft`): any parseable CRS passes the gate and the submission is reprojected into 3460 before spatial subchecks; the two weight-1 CRS subchecks dock the pick. One-sided reprojection of the submission into the canonical CRS implementing a declared accept-list policy — the shape Step 2c-CRS explicitly permits. Reference is never reprojected.

#### Per-run output inspection
Both current runs emit `fiji_transects_fmg.geojson` with 30 MultiLineString features in EPSG:3460, all four reference columns plus the input's `crosses_antimeridian_flag` carried through (consistent with "keep the original attributes"; the grader does not penalise extra columns), total length 6,109,536.5 m identical to the reference, and all 10 crossing transects split into ≥2 parts. Both scored 1.0 (10/10 weighted subchecks).

#### Verdict
**insufficient-evidence**

Only two runs postdate the 05b389bc cutoff and both come from the same agent family (DeepSeek V4 Flash, basic + detailed prompt variants), which the rubric classifies as insufficient evidence regardless of their scores. What evidence exists is consistent with continued calibration: both DeepSeek runs reproduce the reference exactly (1.0), the reference re-grades 1.0 (10/10), the three broken sets land 0.0 / 0.5 / 0.864 in clearly separated bands, and a UTM-60S smoke copy of the reference grades 21/22 ≈ 0.955 failing only `crs_is_canonical`, confirming the accept-list partial-credit shape survives the weighting change. The weighting commit preserves score ordering across all known failure shapes (it widens the gap between data errors and schema errors), so the 2026-06-06 block's `calibrated` verdict has no reason to have degraded; it simply has not yet been re-demonstrated across agent families.

#### Prompt information audit (2c-INFO)
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output filename fiji_transects_fmg.geojson, GeoJSON | instruction | stated |
| canonical CRS EPSG:3460 | "Fiji's national metric grid" category hint | inferable (regional convention; UTM 60S accepted at 21/22) |
| length_m column, metres | instruction | stated |
| MultiLineString throughout, ≥2 parts for crossing transects | instruction ("one MultiLineString feature", "do not leave any transects as plain LineString", "multi-part geometries that faithfully represent the actual survey path") | stated |
| transect_id identity key | instruction ("key field") | stated |
| vessel / survey_date preserved | instruction ("keep the original attributes") | stated |
| feature count 30 / id set Jaccard ≥ 0.95 | input data | inferable |
| 1% length tolerance, FMG envelope | grader-internal | inferable (deterministic PROJ pipeline) |

Factual claims checked: input filename matches `inputs/`; output filename and format match `expected_outputs[]`; column names and units match the reference schema. No inaccurate claim found.

#### Reference faithfulness (2c-REF)
`reference/solution/generate.py` implements split-at-±180° → reproject to 3460 → assemble MultiLineString per transect → length in projected CRS, exactly as asked, with one deviation: the instruction says "keep the original attributes", but the reference rebuilds the GeoDataFrame from only `transect_id`, `vessel`, `survey_date` (+ `length_m`), silently dropping the input's fourth column `crosses_antimeridian_flag` (generate.py:129-138). The README frames the flag as a self-describing convenience the agent "does not need to read", and the grader is neutral (it checks only vessel/survey_date and ignores extra columns — both DeepSeek runs kept the flag and scored 1.0), but the reference as written does not do what the prompt says.
<!-- HUMAN-REVIEW id="HR-001" category="reference-prompt-mismatch" severity="med" -->
Decide whether the reference should carry `crosses_antimeridian_flag` through (regenerate `reference/solution/outputs/`, re-check the three broken sets, and bump `version`) or whether the instruction/README should explicitly except the flag (instruction edit = prompt-vs-grader call, also version bump). Scoring is currently unaffected either way because the grader ignores extra columns and only asserts vessel/survey_date.

#### Specific findings
- README and metadata.yaml still carried the pre-363aed21/05b389bc arithmetic (Gate-2 references, "Gate 1 fails on crs.to_epsg() != 3460", 8/9 and 7/9 denominators, measured scores 0.444/0.889) and the stale `data/` input path. Refreshed unilaterally; re-measured broken scores 0.0 / 0.5 / 0.864 (wrong_crs_metadata_only moved outside its stored [0.3, 0.45] range, which was re-bracketed to [0.45, 0.55] to match the weighted grader).
- The instruction contained two em-dashes, a spec-grammar opener ("fiji_transects — Some of these…"), a sentence fragment ("GeoJSON named fiji_transects_fmg.geojson."), and three duplicated constraints (attribute preservation, length_m column, MultiLineString requirement each stated twice). Rewritten to house style preserving every constraint and both deliberate omissions (no EPSG code, no "antimeridian"/"date line" noun; the "Fiji's national metric grid" category hint kept verbatim). Reference re-grade 1.0.
- analyst_notes pitfall referencing "the count tolerance at Gate 2" updated for the gate-2 removal.
- Inventory "Authoring assumptions" #2 (inventory.md:1173) states the antimeridian fixture is built by pulling real Overture `transportation.segment` features and rejoining them into broken cross-meridian LineStrings; the actual input is fully synthetic (`inputs/_prepare.py`, SEED 20260508, no Overture data). The deviation is well-justified in metadata notes (no real source ships this corruption) but the inventory was never amended, and four prior evaluator passes did not record it.
<!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
Decide whether to amend inventory.md authoring assumption #2 to record the synthetic-fixture decision, or to request an Overture-derived fixture rebuild (which would be a reference-and-data edit with a version bump). The task functions as designed either way.
- coverage.yaml axes re-validated against coverage-vocabulary.yaml: `crs-reprojection`, `l2`, `collect`, `geojson` in/out, `wgs84`+`conformal`+`antimeridian-crossing`, `bundled-local`, `linestring`+`multilinestring`, `fiji`, `small` — all slugs valid, axes cross-consistent (bundled-local ↔ l2). Only the timestamp bumped.
- The version field stayed at 2 across three scoring-affecting commits (05aabd64, 363aed21, 05b389bc); this pass's bump to 3 restores the fingerprint. Recorded here rather than flagged: the timestamp cutoff already handles run validity, and repo-wide grader sweeps appear to deliberately rely on it.

### 3. Changes applied this run

#### Unilateral edits
- task.json: house-style instruction rewrite (em-dashes removed, fragments to full sentences, duplicated attribute/length_m/MultiLineString constraints stated once, input referenced by actual filename); analyst_notes pitfall updated for gate-2 removal; version 2 → 3. Re-grade on reference: 1.0. Reason: house-style mandate; instruction edit requires the bump.
- metadata.yaml: broken measured_scores refreshed under the weighted grader (wrong_crs_metadata_only 0.444 → 0.5, wrong_attributes 0.889 → 0.864), wrong_crs_metadata_only expected_score_range re-bracketed [0.3, 0.45] → [0.45, 0.55], descriptions and rationale rewritten with weighted 11/22 / 19/22 / 21/22 arithmetic. Re-grade on reference: 1.0. Reason: doc drift from 363aed21 + 05b389bc.
- README.md: failure modes #1/#5/#6 and the weak-agent section refreshed for the soft-CRS gate and weighted denominators (21/22 ≈ 0.955, 20/22 ≈ 0.909, 19/22 ≈ 0.864, 18/22 ≈ 0.818, metadata-only 0.5); `data/` path corrected to `inputs/`. Re-grade on reference: 1.0. Reason: doc drift.
- coverage.yaml: evaluator_run_at bumped; no axis changes.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-prompt-mismatch — Reference drops the input's `crosses_antimeridian_flag` column although the instruction says to keep the original attributes; human must pick reference-regeneration or an explicit instruction/README exception (both with version bump).
- HR-002 — inventory-mismatch — inventory.md authoring assumption #2 describes an Overture-derived fixture; the actual fixture is fully synthetic. Amend the inventory or request a fixture rebuild.

#### Tests run
- grader on reference: 1.0 (10/10 weighted subchecks, total weight 22)
- broken sets re-graded: wrong_format 0.0, wrong_crs_metadata_only 0.5, wrong_attributes 0.864; UTM-60S smoke 0.955 (fails only crs_is_canonical)
- pytest: pass (41/41)

---

## Grader weight recalibration 2026-06-14  (evaluator-commit <pending>)

Per-task reasoned subcheck weights replacing the blunt 05b389b 3x
data-content weighting. Grading-only change: only `weight=` values in
grade.py were touched (no check logic, thresholds, or gates; no
task.json version bump). Weights are reasoned from what the task
actually tests — the central gotcha is antimeridian topology, and where
CRS matters the checks that prove the reprojection ACTUALLY HAPPENED
(envelope / per-transect length / total length) are weighted over the
CRS-metadata-label checks.

### Weight changes (total weight 22 -> 17)
| Subcheck | old | new | rationale |
|---|---|---|---|
| antimeridian_crossings_split_into_multi_parts | 3.0 | 4.0 | central, task-defining skill (the L2 gotcha) — top weight |
| per_transect_length_matches | 3.0 | 3.0 | proves reprojection happened, per-feature — unchanged |
| coordinates_within_fmg_fiji_envelope | 1.0 | 2.0 | direct "did you transform the coordinates" detector; was under-weighted |
| total_length_within_1_percent | 3.0 | 2.0 | proves reprojection (aggregate), partly redundant with per-transect |
| transect_id_set_preserved | 3.0 | 1.5 | identity bookkeeping |
| feature_count_within_5_percent | 3.0 | 1.0 | structural bookkeeping |
| identifying_attributes_preserved | 3.0 | 1.0 | cosmetic string carry-through |
| geometry_type_is_multilinestring | 1.0 | 1.0 | cosmetic upcast — unchanged |
| crs_in_meaningful_set | 1.0 | 1.0 | CRS sanity — unchanged |
| crs_is_canonical | 1.0 | 0.5 | cosmetic CRS-label, soft — least central |

### Broken / smoke scores before -> after
| Case | before | after | severity note |
|---|---|---|---|
| reference | 1.0 | 1.0 | correct — stays at ceiling (>= 0.95) |
| broken_wrong_format | 0.0 | 0.0 | gate fail (no length_m) — unchanged |
| broken_wrong_crs_metadata_only | 0.5 | 0.294 | declares 3460 but never transforms coords; loses every reprojection-proof channel + central skill — most severe non-zero |
| broken_wrong_attributes | 0.864 | 0.941 | correct pipeline, drops 2 cosmetic string columns — light dock, near top |
| UTM-60S smoke (correct, non-canonical CRS) | 0.955 | 0.971 | correct pipeline, cosmetic CRS-label only |
| no-split smoke (central-skill miss, upcast Multi) | 0.864 | 0.765 | reproject without splitting the antimeridian — the defining failure |

Ordering is now monotone and defensible:
1.0 (reference) > 0.971 (correct/non-canonical CRS) > 0.941 (cosmetic
attr drop) > 0.765 (central antimeridian-skill miss) > 0.294
(declare-but-never-transform fraud) > 0.0 (format fail). The key fix:
under the old 3x scheme a central-skill miss (no-split, 0.864) scored
*identical* to a cosmetic attribute drop (0.864); the reasoned weights
now separate them (0.765 vs 0.941), so failing the defining gotcha
costs meaningfully more than losing two string columns. The
metadata-only fraud that declares the right CRS but never transforms
coordinates (0.294) sits far below every honest pipeline, satisfying
the invariant that a relabel-only file must not out-score real work.

### Prior-run re-grade summary
Re-graded all version-2 / weighted-grader runs under benchmark/eval/runs/.
The two runs the prior AUTHORING_HISTORY block lists as `current`
(run-20260608-074701Z, run-20260609-084636Z; both DeepSeek V4 Flash)
were correct solutions and stay 1.0 -> 1.0. Recent Gemma runs
(stale, pre-cutoff, background only) shift modestly: run-20260607-112430Z
0.636 -> 0.618, run-20260606-1733Z 0.556 -> 0.618, run-20260606-1129Z
0.556 -> 0.618, run-20260606-0953Z 0.5 -> 0.382. All shifts reflect the
reduced weight on bookkeeping and increased weight on the central
antimeridian/length skills those weak runs failed. No correct-looking
run dropped; no broken/weak run inverted relative to a better one.

### Reasoning
The task is a CRS-category probe whose central skill is antimeridian
handling, not CRS pick. The 05b389b commit blindly set all six
"data-content" subchecks to 3.0 and left the rest at 1.0, which
(a) left `coordinates_within_fmg_fiji_envelope` — the direct proof the
coordinates were actually transformed — at weight 1.0 while mundane
feature-count and attribute carry-through sat at 3.0, and (b) gave the
defining antimeridian-split check the same weight as bookkeeping, so a
central-skill miss scored the same as a cosmetic attribute drop. The
reasoned weights elevate the antimeridian topology (4.0) and the
reprojection-proof checks (envelope 2.0, per-transect length 3.0, total
length 2.0) above identity/structural bookkeeping (1.0-1.5) and the
soft cosmetic CRS-label (crs_is_canonical 0.5), so error severity now
maps to score drop.

### Changes applied this run
- grade.py: subcheck `weight=` values only (table above). No logic, threshold, or gate change.
- metadata.yaml: rationale weight-arithmetic prose rewritten for the reasoned weights; broken measured_score / expected_score_range refreshed (wrong_crs_metadata_only 0.5 -> 0.294 range [0.25,0.35]; wrong_attributes 0.864 -> 0.941 range [0.9,0.97]; wrong_format unchanged).
- README.md: failure-mode #5/#6 and weak-agent-failure-mode score fractions refreshed to the 17-weight denominators.
- audit/status.json: edited files added to unilateral_edits; grader_score_after_edits 1.0; pytest_status not-run; evaluator_finished_at 2026-06-14; status completed-with-flags (HR-001, HR-002 remain — neither is a weighting HR).

### Threshold note (not changed)
No threshold or gate was altered. One observation for a future pass: the
metadata-only fraud now scores 0.294, which is below an *honestly
unprojected file that kept its schema* would score if such a fixture
existed — but the existing `broken_wrong_format` honest-unprojected
fixture also drops length_m and so fails the gate at 0.0. The
invariant ("relabel-only must not out-score honest work") holds within
the spatial subchecks because the fraud zeroes every reprojection-proof
channel; flagging for awareness only, no change made.

### Tests run
- grader on reference: 1.0 (total weight 17)
- broken sets re-graded: wrong_format 0.0, wrong_crs_metadata_only 0.294, wrong_attributes 0.941; UTM-60S smoke 0.971 (fails only crs_is_canonical); no-split smoke 0.765
- pytest: not run (orchestrator runs the suite)

## Review pass — 2026-06-14 (HR-001 resolution: align instruction with output contract)

### Change applied
HR-001 flagged that the instruction's "Keep the original attributes" implies
carrying all four input columns (transect_id, vessel, survey_date,
crosses_antimeridian_flag), but the reference, README output schema, and grader
all encode a three-attribute output (transect_id key + vessel + survey_date +
length_m), dropping crosses_antimeridian_flag. The README already documents the
flag as render-only metadata "the agent does not need to read"; only the prompt
sentence was the loose end.

Reworded the prompt's closing sentence (task.json) to name the carry-through
attributes explicitly:

  before: "Keep the original attributes, use transect_id as the key field, ..."
  after:  "Carry the survey attributes (vessel and survey_date) through
           unchanged, use transect_id as the key field, ..."

This drops the all-attributes implication without naming the antimeridian
gotcha, so the hidden-skill design is unchanged. No reference regen, no broken
re-check (the grader and reference output schema already match the new wording).
task.json.version bumped 3 -> 4.

### Files touched
- task.json: instruction final sentence reworded; version 3 -> 4.
- audit/status.json: HR-001 dropped from human_review_items (HR-002 remains).

### Verification
- No grader or reference change; existing reference still scores 1.0 against the
  unchanged grader. pytest: not run (orchestrator runs the suite).
