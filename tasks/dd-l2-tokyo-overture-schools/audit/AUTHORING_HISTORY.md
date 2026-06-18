# Implementation notes — dd-l2-tokyo-overture-schools

## Status
completed

## Summary
Bundled Overture `places.place` slice (Hive-bucketed across four
parquet partitions) plus a 23-wards bbox polygon; agent must
attribute-filter to `categories.primary == 'school'`, spatially crop
to the polygon, and write a GeoJSON with id / CJK name / confidence /
address fields preserved. 1456 schools in the reference answer.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.00, 0.00])
  - no_spatial_crop: 0.43 (expected range [0.35, 0.55])
  - dropped_attrs: 0.86 (expected range [0.80, 0.95])
- Second-run output match: bit-identical
- Library tests after task: pass (32/32)

## Failure-mode coverage
- Mode 1 (single-partition read): principled-reasoning (count + Jaccard subchecks)
- Mode 2 (skipped spatial crop): broken_no_spatial_crop
- Mode 3 (wrong output format): broken_wrong_format
- Mode 4 (stripped schema fields): broken_dropped_attrs
- Mode 5 (too-broad LIKE filter): principled-reasoning (school_only_filter subcheck)
- Mode 6 (CJK transliteration): principled-reasoning (cjk_names_preserved subcheck)
- Mode 7 (wrong CRS in output): principled-reasoning (Gate 2 coord window)
- Mode 8 (alternate-category confusion): principled-reasoning (school_only_filter subcheck)

## Open issues
- [severity: low] — DuckDB's spatial extension must be installed
  inside the agent's runtime environment to read GeoParquet's
  GEOMETRY column directly. Agents using GeoPandas/PyOGRIO will
  also work because pyogrio decodes GeoParquet WKB transparently.

## Suggested prompt changes
Empty.

## Inventory change proposals
Empty.

## Library extensions
Empty — used `count_within_tolerance` and `jaccard_similarity_set`
unchanged from `geo_grading.comparisons`.

## Runtime
~12 minutes (most of it Overture S3 fetches in the prepare-input
helper plus broken-solution generation).

---

# Evaluator review log

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Aiko Tanaka, a researcher at the Tokyo Metropolitan Government's Education
Bureau, needs every Overture `places.place` with primary category `school`
inside the 23-wards bbox polygon, exported as a GeoJSON in EPSG:4326 with
id / name (CJK preserved) / confidence / address freeform-locality-postcode
fields. The task probes partitioned-GeoParquet reading, attribute filtering
on a nested struct (`categories.primary`), spatial join (polygon contains
point), and GeoJSON output with non-ASCII text round-tripping. L2 difficulty
because it chains four bounded operations on bundled inputs. Reference
answer is 1456 schools; bbox crop removes ~286 features relative to a
plain attribute-only filter (1742), making "skipped spatial crop" a
distinguishable failure class.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | f2e3590 | initial-authoring | Initial task drop (README, IMPLEMENTATION_NOTES, task.json, grader, partitioned parquet, bbox, reference outputs, broken_* sets) | (initial) |
| 2026-05-13 | ce81529 | data-change | Added `tokyo_places.parquet` single-file alongside Hive-bucketed `tokyo_places/` partitions | Commit msg: "add tokyo_places.parquet input" — provides a non-partitioned twin (rationale not explicitly stated; <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: not stated in commit message) |
| 2026-05-13 | 1710715 | prompt-change | Added explicit `Required feature properties keys` block to instruction (column types, value vocab, output schema) and switched input URL to `tokyo_places.parquet` | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | 284b843 | docs-change (tags) | Added `tags` dictionary to task.json (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | 9b1fb11 | prompt-change | Collapsed dedicated schema block into prose; kept "exact keys" sentence with inline types | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped Overture `places.place`, Hive-bucketed parquet hint, geometry type and CRS hints from input description; pruned type annotations from properties list (kept `name (CJK preserved...)`) | Commit msg: "strip deducible information from DD task instructions" |
| 2026-05-17 | 88530c5 | prompt-change | Removed `(CJK preserved, no transliteration)` qualifier from `name` in the properties list | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" |
| 2026-05-18 | f0c244a | grader-change | Replaced local `_is_wgs84` with shared `is_wgs84_fc` from `geo_grading.comparisons` | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package" (semantics preserved) |
| 2026-05-26 | 29a9ae3 | mixed (paths + docs) | Folder reorg: `data/` → `inputs/`, `reference/` → `reference/solution/`, `tests/` → `reference/failures/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, image assets → `assets/`; `task.json` input URL updated to `inputs/tokyo_places.parquet`; grader path constants updated; broken-set script paths updated | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (commit 29a9ae3, class: mixed — task.json input URL and reference path constants changed)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:28:27Z | 0.00 | done | current |

26 earlier runs (run-20260512-1558Z … run-20260517-1424Z) all sit before the 2026-05-26 cutoff and are excluded as stale (the prompt was different and/or paths were different — agent-visible URLs changed).

#### Verdict
**insufficient-evidence**

Only one current run exists, and it is a model-side failure: the Gemma 4 26B agent under the `basic` prompt variant emitted 1736 features missing the `address_freeform`, `address_locality`, `address_postcode` keys (Gate 1 failed `format_schema_valid`, so structural-correctness was skipped and no subchecks ran). The agent also clobbered `name` to the bbox feature's name `"Tokyo 23 Special Wards (bbox)"` for every feature, indicating it joined or mis-labelled rather than reading place names from the parquet. Both are agent-engineering failures (weak coding on a 26B model) — not task miscalibration. The reference scores 1.0 (7/7 subchecks); pytest passes (35/35); the three broken sets land in their expected ranges per `metadata.yaml`. No grader bug observed.

#### Specific findings
- Reference solution still grades 1.0 after the 2026-05-26 folder reorg (paths in `grade.py`, `metadata.yaml > broken_solutions`, and `task.json.inputs[].url` are all consistent with the new `inputs/` and `reference/solution/` layout).
- Instruction stripping (2026-05-14 and 2026-05-17 commits) removed all explicit hints about CJK preservation, the Hive partitioning, the Overture theme name, the schema types, the input format, the geometry type, and explicit "CRS preservation"-style nudges — the instruction is now lean and the grader's `cjk_names_preserved` subcheck is a genuine principled-reasoning test rather than a follow-the-prompt check.
- Inventory row (`benchmark/authoring/inventory.md` line 130) lists Data quality issues as `—`, but `task.json.tags.quality_issues = ["non_latin_script"]` and the grader explicitly checks for CJK in submitted names. This is a minor inventory↔task disagreement: the grader does test a quality dimension. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Either add a CJK-text-preservation entry to the inventory row or remove the `non_latin_script` tag from task.json; not actionable unilaterally because the coverage vocabulary has no `non_latin_script` slug under `data_quality_issues` (vocabulary has only `encoding-issues` for Latin-1/UTF-8 mojibake — which is a *different* failure mode than CJK round-tripping).
- The 2026-05-13 commit (`ce81529`) added `tokyo_places.parquet` (single file) alongside the Hive-bucketed `tokyo_places/bucket=N/part.parquet` directories; subsequent prompt rewrites switched the agent-visible URL to the single-file form. The Hive-bucketed copy remains in `inputs/tokyo_places/` but is now effectively unreferenced by the agent (the task.json url points at `inputs/tokyo_places.parquet`, and the README still describes the bucketed schema). This is a low-severity dead-weight risk: it adds ~1.7 MB to the repo and a README↔task.json drift. <!-- HUMAN-REVIEW id="HR-003" category="design-rationale" severity="low" --> Decision needed: either drop the bucketed copy (and the README's bucketed-schema description and `_make_brokens.py`'s `PARQUET_GLOB`), or revert the URL to the bucketed dir (and keep the partitioned-read failure-mode #1 testable). Not unilateral because it touches `inputs/` and/or `reference/failures/_make_brokens.py`.
- Coverage axis check: `data_sources = bundled-local`, `difficulty = l2`, `operation_categories = data-discovery` — internally consistent with the inventory row.

### 3. Changes applied this run

#### Unilateral edits
- None. The grader is correct, the reference scores 1.0, the broken sets fall in their expected ranges, and the one current run failed model-side.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — design-rationale — Why ce81529 (`add tokyo_places.parquet`) was added is not stated in the commit message.
- HR-002 — inventory-mismatch — `task.json.tags.quality_issues = ["non_latin_script"]` disagrees with the inventory row (`Data quality issues: —`); the coverage vocabulary has no matching slug.
- HR-003 — design-rationale — Bucketed `inputs/tokyo_places/` is no longer referenced by `task.json` (which points at `inputs/tokyo_places.parquet`) but is still described as the input in `README.md` and still globbed by `reference/failures/_make_brokens.py`. Decide whether to drop the bucketed copy or restore the partitioned URL.

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- pytest: pass (35/35)

## Evaluator review 2026-05-26 (run 2)  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from the previous evaluator block above: Aiko Tanaka (Tokyo Metropolitan
Government Education Bureau) needs every Overture `places.place` flagged as a school
whose point lies inside the 23-wards bbox polygon, exported as GeoJSON (EPSG:4326)
with id / CJK name / confidence / three address fields. L2 — chains partitioned-read
→ nested-struct attribute filter → spatial-join crop → GeoJSON write. Reference answer
is 1456 places whose `categories.primary == 'school'` exactly.

#### Change log
No new task-directory commits since the previous evaluator block. The only commit since
that block is the previous evaluator's own artefact commit (`8ab9c40`, 2026-05-26T13:33Z),
which touched solely `audit/` + `coverage.yaml` and is a `docs-change` that does not move
the design-affecting cutoff. The full design history (initial authoring `f2e3590`
2026-05-08 through the folder reorg `29a9ae3` 2026-05-26T09:51:37Z) is reconstructed in
the previous block and is unchanged. Note: the directory-level `--follow` log misses the
pre-reorg path (`benchmark/eval/tasks/`); the slug-grep cross-check confirms the prior
block's `ce81529` / `1710715` / `284b843` commits are real and correctly classified.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae3, class: mixed — task.json
  input URL + grader/broken path constants changed in the folder reorg). The prior
  evaluator's own commit 8ab9c40 is docs-only and does not advance the cutoff.

#### Runs considered
| Run | Adapter | Started (task) | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:48:57Z | 0.5714 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:37:55Z | 0.5714 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:28:27Z | 0.00 | done | stale (task ran 08:28Z, before the 09:51Z cutoff) |

26 earlier runs (run-20260512-1558Z … run-20260517-1424Z) remain stale (pre-cutoff,
different prompt/paths) and are excluded, consistent with the prior block.

#### Verdict
**prompt-grader-inconsistent**

Two current runs from two different agent families (Claude-Code Opus and OpenRouter
Gemma 4 26B) both scored exactly 0.5714 and — independently — produced the *identical*
feature set: 1736 features, Jaccard 0.8387 against the reference, the same 280 ids not
in the reference, the same four subchecks (`count_within_tolerance`,
`feature_set_jaccard_high`, `school_only_filter`) failing and the same three passing
(`cjk_names_preserved`, `confidence_field_present`, `addresses_field_present`,
`bbox_crop_applied`). The reference's 1456 ids are a strict subset of each agent's 1736
ids (`reference/.../tokyo_schools.geojson` ⊂ both submissions). Both agents read the
instruction's phrase *"every place **flagged as a school**"* as "primary category, or any
alternate category, **contains** the substring `school`"; the reference uses strict
equality `categories.primary == 'school'`.

The discrepancy decomposes cleanly against the bundled slice (verified directly with
DuckDB on `inputs/tokyo_places.parquet`, inside the bbox):
- `categories.primary == 'school'` → 1456 (the reference)
- `categories.primary ILIKE '%school%'` → 1673 (+217)
- `primary OR alternate ILIKE '%school%'` → 1736 (+63 from alternate categories)

The +280 are NOT spurious non-schools: the primary-substring matches are
`elementary_school` (37), `preschool` (36), `dance_school` (27), `language_school` (26),
`specialty_school` (22), `high_school` (17), `music_school` (15), `private_school` (7),
`middle_school` (6), `medical_school` (2), `driving_school` (2), etc. Overture's place
taxonomy is hierarchical: `elementary_school` / `high_school` / `middle_school` /
`preschool` / `private_school` / `medical_school` / `vocational_and_technical_school`
are subtype categories of `school`. Restricting to genuine educational-institution
subtypes (excluding the lesson-business cases dance/language/driving/cooking/cosmetology)
yields 1565 inside the bbox — i.e. ~109 features that are unambiguously schools yet are
dropped by the reference's bare-string-`school`-only filter.

This is a genuine prompt-vs-grader ambiguity, NOT a model-side failure: the instruction
("flagged as a school") admits at least two defensible readings — strict bare-`school`
equality vs. the school category family — and two independent agents converged on the
broader, arguably-more-complete one. Per the prompt's rule for `prompt-grader-inconsistent`
("if both readings are defensible, flag"), I flag rather than edit. I cannot resolve it
unilaterally: tightening the instruction to name the exact predicate (`categories.primary
== 'school'`) gifts the agent the filter and changes the persona-level semantics, and
fixing the reference to include subtype schools touches `reference/solution/generate.py`
+ `inputs/outputs` — both forbidden. The convergence of two agent families on the same
0.57 makes this stronger than the prior block's `insufficient-evidence`.

Mechanically the grader is healthy: reference scores 1.0 (7/7), the three broken sets
land in their declared ranges (wrong_format 0.0, no_spatial_crop 0.4286, dropped_attrs
0.8571), and pytest passes (35/35). The grader is correctly enforcing *a* reading; the
problem is which reading.

#### Specific findings
- The instruction's "flagged as a school" vs. the reference's strict
  `categories.primary == 'school'` is the core mismatch. Two independent agent families
  both produced 1736 vs. the reference 1456, scoring 0.57. The reference excludes
  Overture school subtypes (`elementary_school`, `high_school`, `middle_school`,
  `preschool`, `private_school`, `medical_school`, `vocational_and_technical_school`) that
  are genuine schools. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decide the intended filter semantics. Options: (a) keep strict `primary == 'school'` and add an explicit clarifying constraint to the instruction (note: borderline gift); (b) broaden the reference to include the school-category family (touches `reference/solution/generate.py` + `outputs/` + `_make_brokens.py` — author/data edit, not unilateral); (c) loosen the grader's `school_only_filter` / `count_within_tolerance` to accept either reading (changes the answer contract). All three change ground truth or persona semantics, so none is unilateral.
- `count_within_tolerance` (±5 %) and `school_only_filter` (≤5 % spurious) and the
  Jaccard ≥ 0.9 subcheck are each individually well-formed, but together they hard-reject
  the broad reading: 280/1736 = 16 % spurious by the strict definition, well over every
  threshold. The subchecks are doing exactly what `metadata.yaml` says they do; the
  question is whether the reference set they compare against is the intended one. Folded
  into HR-001.
- The bundled-input twin drift from the prior block persists: `task.json.inputs[].url`
  serves the single file `inputs/tokyo_places.parquet`, but `reference/solution/generate.py`
  and `reference/failures/_make_brokens.py` both read the Hive-bucketed
  `inputs/tokyo_places/**/*.parquet`, and `README.md` still describes the partitioned
  schema as the agent-visible input. The two parquet forms are content-equivalent (both
  13402 rows; identical 1456/1673/1736 school counts inside the bbox), so the reference
  answer is unaffected — but README failure-mode #1 ("agent reads only one parquet
  partition") is no longer reachable by the agent, which now receives a single file.
  <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Decide whether to (a) revert the agent-visible URL to the bucketed directory (restores the partitioned-read test; touches task.json — would need re-grade) or (b) drop the bucketed copy + the partitioned-read failure mode from README and re-point generate.py/_make_brokens.py at the single file (touches inputs/ + reference/failures/ — not unilateral). Carried forward from the prior block's HR-001/HR-003.
- The `task.json.tags.quality_issues = ["non_latin_script"]` vs. inventory `Data quality
  issues: —` disagreement from the prior block also persists, and the coverage vocabulary
  still has no `non_latin_script`-equivalent slug under `data_quality_issues`
  (`encoding-issues` is Latin-1/UTF-8 mojibake, a different mode than CJK round-tripping).
  <!-- HUMAN-REVIEW id="HR-003" category="coverage-vocabulary-gap" severity="low" --> The grader's `cjk_names_preserved` subcheck genuinely tests CJK preservation, but there is no controlled slug to record it; `coverage.yaml > data_quality_issues` stays empty with a free-text note. Either add a CJK/non-Latin-script-preservation entry to the thesis `<data-quality-table>` + vocabulary, or drop the `non_latin_script` task tag. Carried forward from the prior block's HR-002.

### 3. Changes applied this run

#### Unilateral edits
- None. The only substantive finding (HR-001, the filter-semantics ambiguity) requires
  either a reference/data edit or a persona-semantics instruction change, both outside the
  unilateral authority. The grader mechanically passes all health checks (reference 1.0,
  broken sets in range, pytest 35/35), so there is nothing to loosen/tighten in good faith
  without first deciding the intended ground truth.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (med) — "flagged as a school" admits two defensible
  readings; two agent families converged on the broad one and scored 0.57. Decide intended
  filter semantics.
- HR-002 — design-rationale (low) — agent-visible single-file parquet vs. generate.py /
  _make_brokens.py / README still on the bucketed dir; partitioned-read failure mode no
  longer reachable by the agent.
- HR-003 — coverage-vocabulary-gap (low) — `non_latin_script` task tag / CJK-preservation
  subcheck has no matching `data_quality_issues` slug.

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- broken sets: wrong_format 0.0, no_spatial_crop 0.4286, dropped_attrs 0.8571 (all in range)
- pytest: pass (35/35)

## Evaluator review 2026-05-27 (run 3)  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from the two prior evaluator blocks: Aiko Tanaka (Tokyo Metropolitan
Government Education Bureau) needs every Overture `places.place` flagged as a school
whose point lies inside the 23-wards bbox polygon, exported as GeoJSON (EPSG:4326) with
id / CJK name / confidence / three address fields. L2 — chains partitioned-read →
nested-struct attribute filter → spatial-join crop → GeoJSON write. Reference answer is
1456 places whose `categories.primary == 'school'` exactly.

#### Change log
No new task-directory commits since the previous evaluator block. `git log
127dddd..HEAD -- benchmark/tasks/dd-l2-tokyo-overture-schools/` is empty: the only
commits after the run-2 block (`127dddd`, 2026-05-26T20:27:52Z) are unrelated
other-task evaluator artefact commits from the in-flight sweep. The full design history
(initial authoring `f2e3590` 2026-05-08 → folder reorg `29a9ae3` 2026-05-26T09:51:37Z)
reconstructed in the first block stands unchanged; the slug-grep cross-check
(`ce81529`, `1710715`, `284b843`) re-confirms it.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae3, class: mixed — task.json
  input URL + grader/broken path constants changed in the folder reorg). Unchanged from
  run 2. The two prior evaluator artefact commits (8ab9c40, 127dddd) are docs-only and do
  not advance the cutoff.

#### Runs considered
| Run | Adapter | Started (task) | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:48:57Z | 0.5714 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:37:55Z | 0.5714 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:28:27Z | 0.00 | done | stale (task ran 08:28Z, pre-09:51Z cutoff) |

No new runs have been recorded since the run-2 block (the three `*0526*` run directories
are byte-for-byte the same set). 26 earlier runs (run-20260512-1558Z … run-20260517-1424Z)
remain stale (pre-cutoff, different prompt/paths) and are excluded.

#### Verdict
**prompt-grader-inconsistent** (re-confirmed; no new evidence since run 2)

Re-verified directly from the committed run artefacts. Both current runs' `score.json`
files show score 0.5714, 1736 submitted features, Jaccard 0.8387 against the reference's
1456, the same 280 ids not in the reference, and the same subcheck split: the four
spatial/count subchecks `count_within_tolerance`, `feature_set_jaccard_high`,
`school_only_filter` fail (note `feature_set_jaccard_high` + `count_within_tolerance` +
`school_only_filter` = three failing, four passing → 4/7 = 0.5714) while
`cjk_names_preserved`, `confidence_field_present`, `addresses_field_present`, and
`bbox_crop_applied` all pass. The reference's 1456 ids are a strict subset of each agent's
1736. Two independent agent families (Claude-Code Opus, OpenRouter Gemma 4 26B) converged
on the broader "primary OR alternate category contains the substring `school`" reading of
the instruction's *"every place flagged as a school"*, whereas the reference uses strict
`categories.primary == 'school'`. The +280 are not spurious non-schools — they include
genuine Overture school subtypes (`elementary_school`, `high_school`, `middle_school`,
`preschool`, `private_school`, etc.) per the run-2 DuckDB decomposition, which I did not
need to re-run as the run artefacts are unchanged.

Mechanically the grader is healthy and re-verified this pass: reference scores 1.0 (7/7
subchecks), the three broken sets land in their declared ranges (wrong_format 0.0,
no_spatial_crop 0.4286, dropped_attrs 0.8571), and pytest passes (35/35). The
output-CRS/format consistency check (Step 2c-CRS) passes: reference output CRS84,
`expected_outputs[]` EPSG:4326, README EPSG:4326, agent submissions EPSG::4326 — all WGS84;
the grader's `is_wgs84_fc` accepts both URN forms and performs no one-sided reprojection
(it compares ids and uses the bbox polygon in the same WGS84 frame). The grader is
correctly enforcing *a* reading; the open question remains which reading is intended.

This is the third consecutive pass to reach this verdict with no new run evidence and no
new task-directory commits. The flags are carried forward unchanged.

#### Specific findings
- The instruction's "flagged as a school" vs. the reference's strict
  `categories.primary == 'school'` remains the core mismatch (two agent families both at
  0.5714, 1736 vs. 1456). Resolution is non-unilateral (reference/data edit, or a
  persona-semantics instruction change that would gift the exact predicate). Carried
  forward as HR-001. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decide the intended filter semantics: (a) keep strict `primary == 'school'` and add an explicit clarifying constraint (borderline gift); (b) broaden the reference to the school-category family (touches `reference/solution/generate.py` + `outputs/` + `_make_brokens.py`); (c) loosen the grader to accept either reading (changes the answer contract). None is unilateral.
- Bundled-input twin drift persists: `task.json.inputs[].url` serves the single file
  `inputs/tokyo_places.parquet`, but `reference/solution/generate.py` and
  `reference/failures/_make_brokens.py` read the Hive-bucketed `inputs/tokyo_places/**/*.parquet`,
  and `README.md` still describes the partitioned schema as the agent-visible input. The
  two parquet forms are content-equivalent (both 13402 rows; identical school counts), so
  the answer is unaffected, but README failure-mode #1 ("agent reads only one parquet
  partition") is no longer reachable by the agent. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Decide whether to (a) revert the agent-visible URL to the bucketed directory (touches task.json — would need re-grade) or (b) drop the bucketed copy + the partitioned-read failure mode and re-point generate.py/_make_brokens.py at the single file (touches inputs/ + reference/failures/ — not unilateral). Carried forward from run-2 HR-002.
- `task.json.tags.quality_issues = ["non_latin_script"]` (CJK round-tripping, checked by
  the grader's `cjk_names_preserved` subcheck) has no matching slug under
  `coverage-vocabulary.yaml > data_quality_issues`, and the thesis `<data-quality-table>`
  itself has no non-Latin-script / CJK-round-tripping row (15 rows, all present in the
  vocabulary — `encoding-issues` is Latin-1/UTF-8 mojibake, a different mode). The gap is
  in the thesis table, not a thesis↔vocabulary discrepancy, so it is not additively fixable
  by the evaluator; `coverage.yaml > data_quality_issues` stays empty with a free-text note.
  <!-- HUMAN-REVIEW id="HR-003" category="coverage-vocabulary-gap" severity="low" --> Either add a CJK/non-Latin-script-preservation row to the thesis `<data-quality-table>` (and the vocabulary in the same commit), or drop the `non_latin_script` task tag. Carried forward from run-2 HR-003.
- Coverage axis cross-check: `data_sources = bundled-local`, `difficulty = l2`,
  `operation_categories = data-discovery` — internally consistent with the inventory row
  (line 130). Unchanged.

### 3. Changes applied this run

#### Unilateral edits
- None. No new evidence or commits since run 2; the grader passes all mechanical health
  checks (reference 1.0, broken sets in range, pytest 35/35). The only substantive finding
  (HR-001) requires a reference/data edit or a persona-semantics instruction change, both
  outside unilateral authority. There is nothing to loosen or tighten in good faith without
  first deciding the intended ground truth.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (med) — "flagged as a school" admits two defensible
  readings; two agent families converged on the broad one and scored 0.57. Decide intended
  filter semantics.
- HR-002 — design-rationale (low) — agent-visible single-file parquet vs. generate.py /
  _make_brokens.py / README still on the bucketed dir; partitioned-read failure mode no
  longer reachable by the agent.
- HR-003 — coverage-vocabulary-gap (low) — `non_latin_script` task tag / CJK-preservation
  subcheck has no matching `data_quality_issues` slug (gap is in the thesis table itself).

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- broken sets: wrong_format 0.0, no_spatial_crop 0.4286, dropped_attrs 0.8571 (all in range)
- pytest: pass (35/35)

## Evaluator review 2026-05-28  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from the four prior evaluator blocks above: Aiko Tanaka (Tokyo
Metropolitan Government Education Bureau) needs every Overture `places.place`
relevant to children aged 8–14 whose point lies inside the 23-wards bbox polygon,
exported as GeoJSON with id / CJK name / confidence / three address fields.
L2 — chains partitioned-read → nested-struct attribute filter → spatial-join
crop → GeoJSON write.

#### Change log
Three new commits since the run-3 block (`91d531e`, 2026-05-27T15:28:53Z):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | mixed (cross-repo + docs) | Added project-wide `task.json.version` field machinery; dropped unused `prompt_version` from every metadata.yaml; this task's metadata.yaml lost the `prompt_version: 1` line | Commit msg: "Add task content versioning; drop unused prompt_version" — introduces the v-field for evaluator/UI use. |
| 2026-05-28 | 2cf1b96 | mixed (prompt + grader + reference + data) | HR-001 redesign — prompt now names the 8–14 age range; reference broadened from strict `categories.primary == 'school'` to the full accept-list {school, elementary_school, middle_school, private_school, public_school} (1456 → 1506); grader gains `school_category_selection` subcheck and restricts count + Jaccard to the `categories.primary == 'school'` subset on both sides; broken_strict_school_only added; broken_no_spatial_crop regenerated against the new reference; metadata.yaml gets a design_note; README rewrites failure modes (now 10) | Commit msg: "Resolve dd-l2-tokyo-overture-schools HR-001 via taxonomic-judgment redesign" — addresses the prompt-grader inconsistency flagged by runs 2 + 3. |
| 2026-05-28 | fbb3596 | docs-change | Cleared resolved HR-001 entry from audit/status.json (administrative drain by the review-queue skill) | Commit msg: "review-queue: clear resolved-HR entries; bundle status.json into Resolve commits going forward" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T10:38:48Z (commit 2cf1b96, class: mixed — prompt + grader + reference + data all changed in the HR-001 redesign). The 622342b commit changed metadata.yaml (`prompt_version` removal — does not affect what the agent sees or how it is graded; docs-class for this task) so it does not advance the cutoff. fbb3596 is docs-only.

#### Runs considered
| Run | Adapter | Started (task) | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T20:57:40Z | 1.00   | done | stale (pre-cutoff; against old strict-`school` reference) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:49:49Z | 0.4286 | done | stale (pre-cutoff) |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T02:06:19Z | 0.5714 | done | stale (pre-cutoff) |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:40:15Z | 0.5714 | done | stale (pre-cutoff) |

All 29 earlier runs (run-20260512-1558Z … run-20260526-1922Z) plus the four `*0527`/`*0528` runs above sit *before* the 2026-05-28T10:38 cutoff and are stale. The HR-001 redesign changed the prompt (now 8–14 age framing), the answer set (1456 → 1506), and the grader (added `school_category_selection`, restricted count + Jaccard to the `school`-subset) — none of these runs is informative about the redesigned task.

#### Verdict
**insufficient-evidence**

Zero current runs exist against the v2 task. The redesign is fresh (2026-05-28T10:38Z) and no sweep has been recorded against it. Mechanically the task is healthy: reference scores 1.0 (7/7), brokens land in their declared ranges (wrong_format 0.00, no_spatial_crop 0.5714, strict_school_only 0.8571, dropped_attrs 0.8571), pytest passes (41/41). The Step 2c-CRS check passes: reference output uses CRS84 (= WGS84), `expected_outputs[].crs = EPSG:4326`, README EPSG:4326, grader `is_wgs84_fc` accepts both URN forms and performs no one-sided reprojection. No grader bug observed; await a fresh sweep.

#### Specific findings
- One unilateral edit applies under Step 4's "Strip any CRS mention when the output is GeoJSON" rule: the instruction said `tokyo_schools.geojson in EPSG:4326`. GeoJSON pins WGS84 by RFC 7946 and the grader's `is_wgs84_fc` already enforces this. The ` in EPSG:4326` is redundant and is stripped this pass; the `expected_outputs[].crs = EPSG:4326` contract is unchanged. Bumped `task.json.version` 1 → 2.
- The HR-001 redesign (commit 2cf1b96) resolves the long-standing prompt-grader inconsistency flagged in runs 2 + 3. The new prompt frames target categories via the 8–14 age range (Japan's compulsory-education years 小学校 + 中学校); the broadened reference accept-list ({school, elementary_school, middle_school, private_school, public_school}) lets an agent that reads the framing correctly score 1.0, and the new `school_category_selection` Jaccard subcheck decouples category-quality from pipeline correctness. Cross-checked against `metadata.yaml > broken_solutions`: the four declared ranges match the grader's current scores exactly.
- Bundled-input twin drift (carried HR-002 from runs 1/2/3) was *not* resolved by the HR-001 redesign: `task.json.inputs[].url` still serves the single file `inputs/tokyo_places.parquet`, while `reference/solution/generate.py` and `reference/failures/_make_brokens.py` still read the Hive-bucketed `inputs/tokyo_places/**/*.parquet`, and `README.md` (now post-redesign) still describes the partitioned schema as the agent-visible input. The two parquet forms are content-equivalent so the answer is unaffected, but README failure-mode #1 (single-partition read) is still unreachable by the agent. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Decide whether to (a) revert the agent-visible URL to the bucketed directory (touches task.json — would need a re-grade and is a prompt-change), or (b) drop the bucketed copy + the partitioned-read failure mode from README and re-point generate.py/_make_brokens.py at the single file (touches inputs/ + reference/failures/ — not unilateral). The human applying (b) must also bump `version`. Carried forward from run-3 HR-002.
- `task.json.tags.quality_issues = ["non_latin_script"]` (CJK round-tripping, verified by the grader's `cjk_names_preserved` subcheck) still has no matching slug under `coverage-vocabulary.yaml > data_quality_issues`, and the thesis `<data-quality-table>` itself has no non-Latin-script / CJK-round-tripping row (15 rows, all present in the vocabulary — `encoding-issues` is Latin-1/UTF-8 mojibake, a different mode). The gap is in the thesis table, not a thesis↔vocabulary discrepancy; not additively fixable by the evaluator. `coverage.yaml > data_quality_issues` stays empty with a free-text note. <!-- HUMAN-REVIEW id="HR-002" category="coverage-vocabulary-gap" severity="low" --> Either add a CJK / non-Latin-script-preservation row to the thesis `<data-quality-table>` (and the vocabulary in the same commit) or drop the `non_latin_script` task tag. Carried forward from run-3 HR-003.
- Coverage axis cross-check: `data_sources = bundled-local`, `difficulty = l2`, `operation_categories = data-discovery`, `overture_themes = places.place`, `regions = tokyo` — internally consistent with the inventory row (line 130). Note: the inventory row still describes the *pre-redesign* spec (`primary == 'school'` only, 1456 features, "every place whose primary category is `school`") — the inventory text has not been updated to match the post-HR-001 redesign. Not flagged as an HR because the inventory is an authoring snapshot, not a runtime contract; the evaluator's `coverage.yaml` reflects the *current* task and remains internally consistent.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: stripped redundant ` in EPSG:4326` from the instruction (GeoJSON pins WGS84 by RFC 7946; the grader's `is_wgs84_fc` already enforces it). Bumped `version: 1 → 2` (first unilateral prompt-change since the redesign). Re-grade on reference: 1.0 (7/7). Reason: Step 4 "Strip any CRS mention when the output is GeoJSON" — mechanical, not a judgment call.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale (low) — bundled-input twin drift between `task.json.inputs[].url` (single file) and `reference/solution/generate.py` / `_make_brokens.py` / `README.md` (Hive-bucketed dir); README failure-mode #1 (single-partition read) is not reachable by the agent.
- HR-002 — coverage-vocabulary-gap (low) — `non_latin_script` task tag / `cjk_names_preserved` subcheck has no matching `data_quality_issues` slug (gap is in the thesis table itself).

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- broken sets: wrong_format 0.0, no_spatial_crop 0.5714, strict_school_only 0.8571, dropped_attrs 0.8571 (all in declared ranges)
- pytest: pass (41/41)

## Evaluator review 2026-06-06  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from the five prior evaluator blocks: Aiko Tanaka (Tokyo Metropolitan Government Education Bureau) needs every Overture `places.place` relevant to children aged 8–14 whose point lies inside the 23-wards bbox polygon, exported as GeoJSON with id / CJK name / confidence / three address fields. L2 — chains partitioned-read → nested-struct attribute filter → spatial-join crop → GeoJSON write. Post-HR-001 redesign (commit 2cf1b96, 2026-05-28T10:38:48Z) widened the answer to the compulsory-education accept-list ({school, elementary_school, middle_school, private_school, public_school}) and added the `school_category_selection` Jaccard subcheck.

#### Change log
No new task-directory commits since the previous evaluator block. `git log 2728f51^..HEAD -- benchmark/tasks/dd-l2-tokyo-overture-schools/` returns only the prior evaluator artefact commit (`2728f51`, 2026-05-28T14:15:45Z, docs-only). The full design history reconstructed in the earlier blocks (initial authoring `f2e3590` 2026-05-08 → folder reorg `29a9ae3` 2026-05-26T09:51:37Z → versioning `622342b` 2026-05-28T07:07:03Z → HR-001 taxonomic redesign `2cf1b96` 2026-05-28T10:38:48Z) stands unchanged.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T10:38:48Z (commit 2cf1b96, class: mixed — prompt + grader + reference + data changed in the HR-001 redesign). Unchanged from the run-4 block. The prior evaluator commit (`2728f51`) was a docs-class write that bumped `task.json.version 1 → 2` and stripped a redundant `in EPSG:4326` from the instruction; the bump itself is metadata-only and the EPSG strip is mechanical per Step 4. I treat that commit as `docs-change` for cutoff purposes (the grader does not change behaviour on the prompt edit, and runs across the version boundary remain comparable).

#### Runs considered
| Run | Adapter | Started (task) | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:19:09Z | 0.5714 | done | current |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T20:20:27Z | 0.5714 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:03:07Z | 0.00 | done | current (model-side: wrote `tokyo_places_in_wards.geojson`, wrong filename) |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-28T23:58:33Z | 0.7142 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:30:28Z | 0.00 | done | current (model-side: 1271/1428 features have null geometry) |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T12:02:35Z | 0.5714 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:51:05Z | 0.00 | done | current (model-side: did not write output) |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:03:23Z | — | failed | current (adapter-side UnicodeDecodeError; excluded from the diagnostic) |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled | current (excluded — cancelled) |

Earlier runs (2026-05-12 … 2026-05-28T03:40Z) all sit before the 2026-05-28T10:38Z cutoff and are stale.

#### Verdict
**calibrated**

Six scoring `current` runs across three agent families (Claude Code Opus, OpenRouter Gemma 4 26B, OpenRouter DeepSeek V4 Pro) span a sensible range: 0.00 (three model-side failures: wrong filename, null-geometry encoding error, missing output), 0.5714 (three pipeline-correct submissions that picked a too-narrow or too-broad category set or missed partitions), and 0.7142 (one Opus run that picked only the labeled subtypes and skipped the bare `school` catch-all). No run scored 1.0 and no run scored close to 1.0 except as a model-side fluke. The grader's two-dimensional design (category-selection Jaccard decoupled from pipeline count + id-Jaccard via the `school`-subset filter) is functioning as designed: each failing run's `score.json` localises the failure to a specific subcheck and the failure modes match the README catalogue.

Inspecting the three pipeline-correct 0.5714 runs:
- **run-20260528-1624Z (Gemma)** submitted 43 features total with categories `{elementary_school, middle_school}`. `school_category_selection` fails (Jaccard 2/5 = 0.4) and `count`/`feature_set_jaccard_high` fail because the agent's `school`-subset is empty. This is README failure-mode #6 (overshoot / undershoot the age range — here, undershoot) combined with a partition read that may also be off. Four subchecks pass.
- **run-20260528-1927Z (Opus)** submitted 221 features with `{bus_station, elementary_school, high_school, middle_school, private_school, school, transportation}`. The category Jaccard is 4/8 = 0.5 (fails ≥ 0.6 by including bus_station + transportation + high_school). `count` and `feature_set_jaccard_high` also fail because the agent only got 162 `school`-subset features versus the reference 1456, indicating a partition-read failure (README failure-mode #1). This run hits two distinct failure modes at once and the grader correctly flags both axes.
- **run-20260529-0902Z (DeepSeek)** submitted 162 features with `{school}` (strict). `school_category_selection` fails Jaccard 1/5 = 0.2 (README failure-mode #6, strict-school-only undershoot — exactly what `broken_strict_school_only` is designed to mimic, except the partition read also slipped: 162 versus the expected 1456). The grader fails three subchecks, four pass.

run-20260528-2332Z (Opus, 0.7142) is the interesting one: agent picked `{elementary_school, middle_school, private_school}` — passing the category Jaccard (3/5 = 0.6) but skipping the bare `school` catch-all and submitting only 50 features. `count_within_tolerance` and `feature_set_jaccard_high` on the `school`-subset both fail (agent's `school`-subset is empty vs. reference 1456). The remaining five subchecks pass, yielding 5/7 = 0.7142. This is a defensible-but-narrow reading of the persona's "schools for 8–14" — the agent reasoned that bare `school` is too generic and stuck to explicitly-labeled levels — and the grader correctly registers it as a partial success: category-selection axis passed, pipeline-completeness axis failed. The current `metadata.yaml` design rationale states `school` "is the one category every reasonable answer must include" because it is the bundled slice's dominant primary tag (1456 of 1506 reference features). A human could argue the grader should accept this reading as fully correct since the agent's category set is a subset of the accept-list, but doing so would either require widening the accept-list (already done) or removing the pipeline-count subcheck (loses the partitioned-read detector). The 5/7 partial credit is a reasonable middle ground and the verdict here is `calibrated` rather than `prompt-grader-inconsistent`: the grader is signalling the right thing, and the partial score correctly distinguishes this from a fully-correct submission. If two more independent runs converge on the "labeled-subtypes-only" reading, that converts to `prompt-vs-grader-judgment` and gets flagged; one Opus instance is not enough.

Mechanical health checks all pass: reference scores 1.0 (7/7), the four broken sets land in their declared ranges (wrong_format 0.00, no_spatial_crop 0.5714, strict_school_only 0.8571, dropped_attrs 0.8571), and pytest passes (41/41). Step 2c-CRS check: reference output uses CRS84, `expected_outputs[].crs = EPSG:4326`, README EPSG:4326, grader `is_wgs84_fc` accepts both URN forms and performs no one-sided reprojection — consistent.

#### Specific findings
- The HR-001 redesign is working as intended on real run evidence. Three agent families produce three different failure signatures and the grader localises each one to the correct subcheck. No grader miscalibration observed.
- The "labeled-subtypes-only" reading (run-20260528-2332Z) scores 0.71 by design — `school_category_selection` Jaccard sits exactly at the 0.6 threshold (3/5). This is borderline and worth a second look if it recurs across agents; for now, one occurrence is not evidence of miscalibration.
- Bundled-input twin drift (carried HR-001 from the prior block) persists: `task.json.inputs[].url` serves the single file `inputs/tokyo_places.parquet`, while `reference/solution/generate.py` and `reference/failures/_make_brokens.py` read the Hive-bucketed `inputs/tokyo_places/**/*.parquet`. The DeepSeek 0.5714 run (162 `school`-subset features vs. expected 1456) is consistent with the partitioned-read failure mode the README documents — but the agent in fact received only the single file `tokyo_places.parquet`, which contains all 13402 rows, so the 162-vs-1456 gap is *not* a partitioned-read miss in the sense the README describes; it is some other filter mistake. The README's failure-mode #1 ("agent reads only one parquet partition") remains unreachable as a *partition* failure because the agent's URL points to a single file. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Decide whether to (a) revert `task.json.inputs[].url` to the bucketed directory (touches task.json — prompt-change, needs `version` bump and re-grade) or (b) drop the bucketed copy + retarget generate.py/_make_brokens.py at the single file and rewrite README failure-mode #1 (touches inputs/ + reference/failures/ — not unilateral; the human applying (b) must also bump `version`). Carried forward from the prior block's HR-001.
- `task.json.tags.quality_issues = ["non_latin_script"]` (CJK round-tripping, verified by the grader's `cjk_names_preserved` subcheck) still has no matching slug under `coverage-vocabulary.yaml > data_quality_issues`, and the thesis `<data-quality-table>` itself has no non-Latin-script row. Not additively fixable by the evaluator; `coverage.yaml > data_quality_issues` stays empty with a free-text note. <!-- HUMAN-REVIEW id="HR-002" category="coverage-vocabulary-gap" severity="low" --> Either add a CJK / non-Latin-script-preservation row to the thesis `<data-quality-table>` (and the vocabulary in the same commit) or drop the `non_latin_script` task tag. Carried forward from the prior block's HR-002.
- `analyst_notes` was missing from `task.json` and is added this pass per Step 4. Reflects the post-redesign category-selection-plus-pipeline framing, lists the eight catalogued failure modes from README in plain prose, and matches the house-style rules. Does not require a `version` bump (analyst_notes is human-facing and not seen by the agent).
- The inventory row (line 130) still describes the *pre-redesign* spec ("every place whose primary category is `school`", 1456 features). The post-redesign accept-list is not reflected. Not flagged as an HR because the inventory is an authoring snapshot, not a runtime contract.
- Coverage axis cross-check: `data_sources = bundled-local`, `difficulty = l2`, `operation_categories = data-discovery`, `overture_themes = places.place`, `regions = tokyo` — internally consistent with the inventory row.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `analyst_notes` (description + 5-step approach + 8 pitfalls). Re-grade on reference: 1.0 (7/7). Reason: Step 4 "Author or refresh `analyst_notes` in `task.json`" — field was missing; reflects the post-HR-001 redesign framing. No `version` bump required (Step 4 explicitly excludes `analyst_notes` authoring from the bump list; the field is human-facing only).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale (low) — bundled-input twin drift between `task.json.inputs[].url` (single file) and `reference/solution/generate.py` / `_make_brokens.py` / `README.md` (Hive-bucketed dir); README failure-mode #1 (single-partition read) is not reachable by the agent.
- HR-002 — coverage-vocabulary-gap (low) — `non_latin_script` task tag / `cjk_names_preserved` subcheck has no matching `data_quality_issues` slug (gap is in the thesis table itself).

#### Tests run
- grader on reference: 1.0 (7/7 subchecks)
- broken sets: wrong_format 0.00, no_spatial_crop 0.5714, strict_school_only 0.8571, dropped_attrs 0.8571 (all in declared ranges)
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
- Old Gate-2 id-type check ("every feature has a non-empty string id")
  migrated to a new `ids_are_strings` subcheck.
- Old Gate-2 coordinate-range check ("every feature is inside the
  generous Tokyo metropolis window") migrated to a new
  `coords_in_tokyo_window` subcheck. This is distinct from the
  existing `bbox_crop_applied` subcheck, which uses the tighter
  23-wards bbox polygon.
- Subcheck count: 7 → 9.

### Verification
- Reference solution re-graded: 1.0 (9/9 subchecks).

## Evaluator review 2026-06-12  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from the six prior evaluator blocks: Aiko Tanaka (Tokyo Metropolitan
Government Education Bureau) needs every Overture `places.place` relevant to
children aged 8–14 whose point lies inside the 23-wards bbox polygon, exported
as GeoJSON with id / CJK name / confidence / three address fields. L2 — chains
partitioned-read → nested-struct attribute filter → spatial-join crop →
GeoJSON write. Post-HR-001 redesign (commit 2cf1b96, 2026-05-28) grades two
orthogonal axes: category-selection (Jaccard vs the compulsory-education
accept-list) and pipeline correctness (count + id-Jaccard restricted to the
`categories.primary == 'school'` subset).

#### Change log
Three new commits since the previous evaluator block (`a92c5d1`,
2026-06-06T15:05:05Z, docs-class evaluator artefacts + analyst_notes):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change | Removed `Gate("structural_correctness", ...)` and its early-return; migrated the id-type check to a new `ids_are_strings` subcheck and the Tokyo coordinate-window check to a new `coords_in_tokyo_window` subcheck (7 → 9 subchecks). Same-commit AUTHORING_HISTORY append ("Manual cleanup 2026-06-06") re-verified reference at 1.0 (9/9). | Commit msg: the second gate was inconsistent across the 36 graders (34 effectively hard); benchmark-wide refactor to one hard gate + salvageable checks as subchecks. |
| 2026-06-07 | 632ad1a | grader-change | Added `weight=3.0` to the five data-content subchecks (`school_category_selection`, `count_within_tolerance`, `feature_set_jaccard_high`, `cjk_names_preserved`, `bbox_crop_applied`); the four schema/structural subchecks stay weight 1.0. Total weight 5×3 + 4×1 = 19. | Commit msg: schema-clean but data-wrong submissions should score visibly lower than data-correct ones with minor schema drift. |
| 2026-06-07 | 501e9a6 | (out of scope) | Touches `geo_grading` for CRS accept-lists in other tasks; no change to this task's files. | Commit msg: Accept multi-EPSG canonical sets in grade_crs_soft. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:28:21Z (commit 632ad1a, class:
  grader-change — subcheck weighting). 363aed2 (2026-06-06T20:11:02Z,
  grader-change) is superseded as cutoff by 632ad1a.

#### Runs considered
| Run | Adapter | Started (task) | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:17:51Z | 0.6842 | done | current (suite 6510297, task v2) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:25:07Z | 0.6842 | done | current (suite ec540aa, task v2) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T13:40:32Z | 0.8421 | done | stale (started pre-cutoff; recorded score is 16/19, i.e. regraded under the weighted grader, so it is quoted below as supporting context only) |

Footnote: all runs from 2026-05-12 through 2026-06-06 (the 6 runs the
2026-06-06 block treated as current, plus 29 older ones) now sit before the
2026-06-07T18:28Z grader-change cutoff and are stale for calibration purposes.
Two of them (run-20260528-1927Z Opus, run-20260529-0902Z DeepSeek V4 Pro) are
cited below because their output signature (exactly 162 `school`-subset
features) matches the two current runs.

#### Verdict
**insufficient-evidence**

Only two current runs exist and both come from one agent family (DeepSeek V4
Flash, basic + detailed prompt variants), which fails the two-family
requirement for a calibration verdict. Mechanically the task is healthy under
the new weighted grader: reference scores 1.0 (9/9), the four broken sets land
at 0.00 / 0.5263 / 0.8421 / 0.9474, pytest passes (41/41), and the Step 2c-CRS
check is unchanged (reference CRS84 = `expected_outputs[].crs` EPSG:4326 =
README; no one-sided reprojection in the grader).

Per-run inspection: both current runs pass the hard gate (parseable WGS84
FeatureCollection, all Points, all six property keys), pass
`school_category_selection` (chosen sets {elementary_school, middle_school,
private_school, school} and the same plus high_school → Jaccard 0.8 / 0.667),
pass CJK, bbox-crop, confidence, addresses, ids, and coord-window — but
submitted only 209/218 features against the reference 1506, with exactly 162
features in the `categories.primary == 'school'` subset vs the reference 1456,
failing `count_within_tolerance` and `feature_set_jaccard_high` (weight 3
each): 13/19 = 0.6842.

#### The 162-feature convergence (tripwire from the 2026-06-06 block)
Diagnosed against the bundled input: the 162 submitted bare-`school` rows are
*exactly* the in-bbox bare-`school` rows whose `categories.alternate` carries
an explicit school-level tag (elementary_school / middle_school /
private_school / public_school / high_school) — 162 of 275 such rows in the
slice fall inside the bbox, and the submissions contain all 162 and none of
the other 1294 bare-`school` rows. So the agents demanded an explicit
age-level signal in *some* category slot instead of keeping the whole bare
`school` catch-all. The same 162-row signature appears in the stale
run-20260528-1927Z (Opus) and run-20260529-0902Z (DeepSeek V4 Pro), and the
labeled-subtypes-only variant appeared in run-20260528-2332Z (Opus). The
2026-06-06 block pre-registered: "If two more independent runs converge on
the 'labeled-subtypes-only' reading, that converts to
`prompt-vs-grader-judgment` and gets flagged." That condition is now met —
four runs across three agent families converge on requiring an explicit
age-level signal. The narrow reading has independent merit: among the
excluded bare-`school` rows, 212 carry the alternate (education,
college_university), i.e. plausibly *not* age-8–14 institutions, so an agent
reasoning carefully about the persona's age framing can defensibly refuse
the catch-all. The grader, however, prices that reading at 13/19 = 0.68
because the reference keeps every `primary='school'` row.
<!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" -->
Decide whether (a) the bare-`school`-catch-all judgment stays the intended
hidden gotcha and 0.68 is the designed partial credit (no change), (b) the
instruction should tell the agent that most schools in the data carry only
the generic tag and must be kept (adds information — not unilateral; needs a
`version` bump), or (c) the school-subset count/Jaccard subchecks should be
softened for submissions whose school-subset is a clean signal-bearing
subset of the reference. Evidence: 4 runs / 3 families converge on the
narrow reading; 212 excluded rows carry college_university alternates,
which makes the narrow reading independently defensible.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output filename `tokyo_schools.geojson` | instruction | stated |
| GeoJSON FeatureCollection, WGS84 | instruction names GeoJSON; RFC 7946 pins WGS84 | inferable |
| Point geometry | input data is all Points | inferable |
| six exact property keys | instruction, schema sentence | stated |
| bbox crop against `tokyo_23wards_bbox` | instruction ("sits inside the wards rectangle") | stated |
| category accept-list (Jaccard ≥ 0.6) | age-8–14 framing → compulsory-education family | inferable (by design) |
| keep the bare `school` catch-all (count ±5 %, id-Jaccard ≥ 0.9 on the school-subset) | data inspection (1456 of 1506 in-bbox family rows carry only the generic tag) | borderline-inferable → HR-001 |
| CJK names preserved | data (names are CJK) + persona ("R visualisation") | inferable |
| confidence numeric in [0, 1] | key stated; range from data | inferable |
| ids non-empty strings | data | inferable |
| coords in Tokyo window | data + GeoJSON convention | inferable |

Factual claims verified: both input names exist with the stated content
(`tokyo_places` 13402 rows, `tokyo_23wards_bbox` one rectangle), the six
property keys match the reference schema, and the output filename matches
`expected_outputs[]`. No inaccurate claims found.

#### Reference faithfulness
`reference/solution/generate.py` implements the instruction as written:
accept-list category filter, within-polygon crop, six-key schema, hand-written
UTF-8 GeoJSON, stable sort for determinism. The only deviation is the known
bundled-input twin drift: it reads the Hive-bucketed
`inputs/tokyo_places/**/*.parquet` while the agent-visible
`task.json.inputs[].url` serves the content-equivalent single file
`inputs/tokyo_places.parquet`. Carried as HR-002 below; no new
reference-prompt-mismatch flag.

#### Specific findings
- The two new grader commits (Gate-2 drop, 3x data-content weighting) shifted
  every broken-set score; `metadata.yaml > broken_solutions` and the README
  score quotes were stale and are doc-synced this pass (see section 3).
  `broken_dropped_attrs` moved from 0.8571 to 0.9474, *outside* its declared
  [0.80, 0.90] range — that movement is the explicit intent of commit 632ad1a
  (data-correct, schema-drifted submissions lose little), so the range is
  updated to [0.90, 0.98] alongside the measured score rather than flagged.
- Four runs across three families converge on the explicit-age-signal reading
  of the category filter → HR-001 (prompt-vs-grader-judgment, med), per the
  tripwire pre-registered in the 2026-06-06 block.
- Bundled-input twin drift persists (single-file URL vs bucketed reference
  read; README failure-mode #1 unreachable as a *partition* failure).
  <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" -->
  Decide whether to (a) point `task.json.inputs[].url` back at the bucketed
  directory (prompt-change, needs `version` bump and re-grade) or (b) drop the
  bucketed copy, retarget generate.py/_make_brokens.py at the single file, and
  rewrite README failure-mode #1 (touches inputs/ + reference/failures/ — not
  unilateral; the human applying (b) must also bump `version`). Carried
  forward from the 2026-06-06 block's HR-001.
- `task.json.tags.quality_issues = ["non_latin_script"]` still has no matching
  slug under `coverage-vocabulary.yaml > data_quality_issues`, and the thesis
  `<data-quality-table>` has no non-Latin-script row, so the gap is not
  additively fixable by the evaluator.
  <!-- HUMAN-REVIEW id="HR-003" category="coverage-vocabulary-gap" severity="low" -->
  Either add a CJK / non-Latin-script-preservation row to the thesis
  `<data-quality-table>` (and the vocabulary in the same commit) or drop the
  `non_latin_script` task tag. Carried forward from the 2026-06-06 block's
  HR-002.
- README failure-mode #9 still described the removed Gate 2 as the detector
  for metric-CRS reprojection; rewritten to name the `coords_in_tokyo_window`
  subcheck (docs-change). The matching `analyst_notes` pitfall said
  "coordinate-window gate" and now says "coordinate-window check".
- Coverage axes unchanged from the prior block and still internally
  consistent (bundled-local + l2 + data-discovery + places.place + tokyo).

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` under the
  weighted grader (no_spatial_crop 0.5714 → 0.5263, strict_school_only
  0.8571 → 0.8421, dropped_attrs 0.8571 → 0.9474, wrong_format 0.0
  unchanged); updated the stale "x / 7" score math in the descriptions to the
  19-point weighted scale; moved dropped_attrs `expected_score_range`
  [0.80, 0.90] → [0.90, 0.98] to match the deliberate 632ad1a weighting
  policy. Re-grade on reference: 1.0. Reason: Step 4 measured_score refresh +
  doc-sync after a benchmark-wide grader-policy commit; no tolerance changed,
  so no `version` bump.
- `README.md`: broken-set scores 0.57 → 0.53, 0.86 → 0.84 (strict filter),
  0.86 → 0.95 (dropped attrs); failure-mode #9 detector rewritten from
  "Gate 2" to the `coords_in_tokyo_window` subcheck; weak-agent expected
  scores ~0.57/~0.86 → ~0.53/~0.84. Re-grade on reference: 1.0. Reason:
  docs-change; README must agree with the current grader.
- `task.json` (`analyst_notes` only): pitfall wording "coordinate-window
  gate" → "coordinate-window check" after the Gate-2 removal. Re-grade on
  reference: 1.0. Reason: analyst_notes refresh (human-facing; no `version`
  bump required).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (med) — four runs across three families
  converge on requiring an explicit age-level category signal instead of
  keeping the bare `school` catch-all; decide prompt nudge vs grader
  softening vs status quo.
- HR-002 — design-rationale (low) — bundled-input twin drift (single-file
  agent URL vs Hive-bucketed reference read); carried forward.
- HR-003 — coverage-vocabulary-gap (low) — `non_latin_script` tag has no
  vocabulary slug; gap is in the thesis table itself; carried forward.

#### Tests run
- grader on reference: 1.0 (9/9 subchecks, weighted total 19/19)
- broken sets: wrong_format 0.0, no_spatial_crop 0.5263, strict_school_only
  0.8421, dropped_attrs 0.9474 (all within the declared ranges after the
  dropped_attrs range update)
- pytest: pass (41/41)

## Evaluator review 2026-06-14 — subcheck-weight severity recalibration  (evaluator-commit <pending>)

**One-line statement:** RECALIBRATED — replaced the blunt repo-wide
2026-06-07 weighting (five data-content subchecks flat at 3.0, four at 1.0,
total 19) with severity-ordered weights reasoned from what this data-delivery
task actually tests; reference stays 1.0, broken ordering stays monotone and
is now better separated. Grading-only change; no `version` bump.

### Rationale
This is a data-delivery task whose central skills are (1) extracting the
right feature set (partitioned read + attribute filter + spatial crop) and
(2) round-tripping CJK / non-Latin place names intact — the latter is the
task's explicitly-tagged quality concern (`non_latin_script`). The blunt
3.0/1.0 split miscalibrated two severities:
  - **CJK-mangling tied a defensible category narrowing** (both single
    weight-3 checks → 0.842). But transliterating/stripping every Japanese
    name delivers a corrupted dataset to the persona's R-viz colleague,
    whereas the strict-`school` narrowing is the task's *most defensible*
    miss (standing HR-001). CJK should outrank it on severity.
  - **A metric-CRS reprojection priced as cheaply as a nulled metadata
    field** (`coords_in_tokyo_window` at weight 1 → 0.947, same as
    dropped_attrs). Coordinates in the millions of metres make the whole
    deliverable geographically useless — that is not cosmetic.
Fix: keep the true data-correctness checks highest, raise the named
non-Latin concern to match, lift coordinate-validity above cosmetic, and
de-weight the checks that *correlate* with feature-set Jaccard (count,
bbox-crop) so one underlying error (skipped crop / partition miss) is not
triple-counted. Category-selection drops to 2.0 because the narrow reading
is independently defensible (HR-001) and must not score below a broken
deliverable.

### Weight changes
| Subcheck | old | new | reason |
|---|---|---|---|
| feature_set_jaccard_high | 3.0 | 3.0 | core "right features" id-set check (unchanged, highest) |
| cjk_names_preserved | 3.0 | 3.0 | named non-Latin data-quality concern (unchanged, highest) |
| school_category_selection | 3.0 | 2.0 | central axis, but strict-`school` narrowing is the most defensible single-axis miss (HR-001) |
| count_within_tolerance | 3.0 | 2.0 | correlates with feature-set Jaccard; held at 2 to avoid double-counting |
| bbox_crop_applied | 3.0 | 2.0 | correlates with count/Jaccard on a skipped crop; held at 2 |
| coords_in_tokyo_window | 1.0 | 2.0 | metric-CRS reprojection makes the deliverable geographically useless — above cosmetic |
| confidence_field_present | 1.0 | 1.0 | schema plumbing (cosmetic) |
| addresses_field_present | 1.0 | 1.0 | key-presence only (cosmetic) |
| ids_are_strings | 1.0 | 1.0 | structural sanity (cosmetic) |

Total weight 19 → 17.

### Broken scores before → after
| Broken | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.0000 | 0.0000 | catastrophic — gate fail (unchanged) |
| no_spatial_crop | 0.5263 | 0.5882 | severe — corrupted feature set (count+jaccard+bbox flip); most-penalised covered broken |
| strict_school_only | 0.8421 | 0.8824 | mildest non-cosmetic miss — defensible taxonomic narrowing (HR-001) |
| dropped_attrs | 0.9474 | 0.9412 | cosmetic — data perfect, one schema field nulled; lightest non-zero drop |

Ordering: 0.0000 < 0.5882 < 0.8824 < 0.9412 — strictly monotone, and the
gaps now read as severity (broken deliverable << defensible narrowing <
cosmetic drift). Uncovered-mode severity sanity (simulated): CJK-mangle
0.824 and wrong-CRS 0.882 are now both penalised as broken deliverables,
with CJK correctly more severe than the defensible strict-`school` narrowing
(0.882) — the two miscalibrations the old weighting introduced are fixed. No
disjoint-failure inversion: the most-severe covered broken (no_crop, 0.588)
stays below every single-axis miss.

### Prior-run re-grade summary
| Run | old | new |
|---|---|---|
| run-20260608-074701Z (DeepSeek V4 Flash, current v2) | 0.6842 | 0.7059 |
| run-20260609-084636Z (DeepSeek V4 Flash, current v2) | 0.6842 | 0.7059 |
| run-20260607-112430Z (Gemma 4 26B, cited) | 0.8421 | 0.8824 |
| run-20260606-1733Z | 0.8571* | 0.8824 |
| run-20260528-1927Z (Opus, signature match) | 0.5714* | 0.5882 |
| run-20260529-0902Z (DeepSeek V4 Pro, signature match) | 0.5714* | 0.5882 |
| run-20260528-2332Z (Opus, labeled-subtypes) | 0.7143* | 0.7059 |

(* recorded under an earlier grader; quoted as context.) Shifts are small
and sensible: the two current DeepSeek runs rise from 0.68 to 0.71 because
their failure is the correlated count+jaccard pair, now de-weighted to avoid
double-counting one feature-set error. No inversions, no run crosses a
qualitative boundary.

### Changes applied this run
#### Unilateral edits
- `grade.py` — subcheck `weight=` values only (table above); no logic,
  threshold, or gate change.
- `metadata.yaml` — refreshed broken `measured_score` (no_spatial_crop
  0.5263→0.5882, strict_school_only 0.8421→0.8824, dropped_attrs
  0.9474→0.9412); updated `expected_score_range` for no_spatial_crop
  ([0.50,0.65]→[0.52,0.66]) and strict_school_only ([0.80,0.90]→[0.84,0.92]);
  rewrote the per-broken weight arithmetic to the 17-point scale; added a
  `weighting:` rationale block.
- `README.md` — refreshed stale broken-score fractions (0.53→0.59, 0.84→0.88,
  0.95→0.94) and the weak-agent expected scores.

#### HR items
- No weighting HR exists for this task; HR-001 (prompt-vs-grader-judgment),
  HR-002 (design-rationale, bundled-input twin drift), HR-003
  (coverage-vocabulary-gap) are all retained unchanged — none is a weighting
  HR.

#### Tests run
- grader on reference: 1.0 (9/9 subchecks, weighted total 17/17)
- broken sets: wrong_format 0.0000, no_spatial_crop 0.5882, strict_school_only
  0.8824, dropped_attrs 0.9412 (all within the updated declared ranges)
- pytest: not-run (orchestrator runs the suite)

## Operator resolution 2026-06-14 — HR-001 catch-all rescue

Resolves HR-001 (prompt-vs-grader-judgment, med): four runs across three
agent families converged on dropping the generic `school` catch-all and
keeping only the bare-`school` rows that carry an explicit school-level
`categories.alternate` tag. The pre-2026-06-14 grader priced that reading at
13/19 ~ 0.68 because `count_within_tolerance` (w2) and
`feature_set_jaccard_high` (w3) compared the agent's narrowed `school`-subset
against the full 1456-row reference subset.

### Operator decision
Option (c) from the HR, refined: the grader now only *slightly* reduces the
score when the generic category is omitted. The operator's stance is that a
correct answer should keep the catch-all (most generically-tagged schools do
serve the 8-14 age range), so the reference stays at 1.0 and dropping the
catch-all is a one-point ding rather than a 5-point pipeline-failure cost.

### Grader change (`grade.py`, grader-class — no `task.json.version` bump)
- Added `school`-subset precision / recall. A submission whose `school`-subset
  is a clean high-purity subset of the reference (`precision >= 0.95` and
  `recall < 0.9`) is the dropped-catch-all signature, not a pipeline fault.
- For that signature, `count_within_tolerance` and `feature_set_jaccard_high`
  are rescued (they still fire on over-inclusion: a skipped crop or junk
  filter drops precision below 0.95).
- Added a new weight-1 `generic_school_retained` subcheck that flips exactly
  when the catch-all is dropped. Subcheck count 9 -> 10; total weight 17 -> 18.
- Consequence (documented): a hypothetical partition miss also yields a clean
  subset and is now lightly penalised. This is unreachable in practice — the
  agent-visible input is a single file (bundled-input twin drift, separate
  carried item), so there is no partition to miss.

### Files touched
- `grade.py` — precision/recall + clean-subset rescue + `generic_school_retained`.
- `reference/failures/_make_brokens.py` — added `make_dropped_catch_all()`.
- `reference/failures/broken_dropped_catch_all/` — new fixture (265 features).
- `metadata.yaml` — new broken entry; refreshed weighting (total 18) and all
  measured scores to the 18-point scale; tolerances note on the rescue.
- `README.md` — new failure-mode #11; refreshed broken-score fractions and
  weak-agent expected scores; updated mode #1 (partition-miss now rescued).
- `audit/status.json` — dropped HR-001.

### Tests run
- grader on reference: 1.0 (10/10 subchecks, weighted 18/18)
- broken sets: wrong_format 0.0000, no_spatial_crop 0.6111, strict_school_only
  0.8889, dropped_attrs 0.9444, dropped_catch_all 0.9444 (all within declared
  ranges)
