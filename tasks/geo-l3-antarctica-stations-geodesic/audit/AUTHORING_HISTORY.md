# Implementation notes — geo-l3-antarctica-stations-geodesic

## Status
completed

## Summary
L3 task exercising geodesic buffering, land-mask clipping, coalition union, and water/bathymetry intersection for Antarctic research stations fetched from Overture Maps.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - broken_wrong_crs: 0.0 (expected range [0.0, 0.0])
  - broken_no_coalition: 0.5 (expected range [0.3, 0.6])
  - broken_planar_buffer: 0.6 (expected range [0.4, 0.7])
- Second-run output match: identical attribute/count match (L3 against same Overture release)
- Library tests after task: pass

## Failure-mode coverage
- Planar buffer instead of geodesic: broken_planar_buffer
- Wrong output CRS: broken_wrong_crs
- No coalition detection: broken_no_coalition
- Station identification failure: broken_no_coalition (partial) + principled-reasoning (gate 2 minimum count)
- Missing land clip: principled-reasoning (area subcheck)
- Missing water overlap: principled-reasoning (water subchecks)
- No water/bathymetry attribution: principled-reasoning (water_source_attribution subcheck)

## Open issues
- [severity: low] — Overture places.place has no "research_station" category; station identification relies on name keyword filtering which is inherently fuzzy. The grader uses generous tolerances (±30% count, 60% name overlap) to accommodate this.
- [severity: low] — Some Overture POIs are misplaced (e.g. Taiwanese business appearing in Antarctica). Reference filters by category exclusion and proximity deduplication, but agents may find a slightly different station set.
- [severity: low] — The bathymetry layer has different columns than water/land (no names, no subtype, has depth instead). Reference handles this with separate fetch logic.

## Suggested prompt changes
Empty.

## Inventory change proposals
Empty.

## Library extensions
Empty.

## Runtime
~5 minutes (dominated by Overture S3 fetches for land/water/bathymetry layers)

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

The task was introduced as an L3 geometric-ops exercise probing geodesic buffering at polar latitudes, land-mask clipping against a complex Antarctic coastline, cascaded union to detect overlapping station "coalitions", and a separate over-water attribution against Overture `base.water` / `base.bathymetry`. The inventory row (line 619 of `benchmark/authoring/inventory.md`) declares: region Antarctica, primary op buffer (geodesic, large-extent — 200 km), secondaries clip + cascaded union, output CRS EPSG:3031 (Antarctic Polar Stereographic), output MultiPolygon GeoParquet, medium data scale, and a story-line for Dr. Ellis Whitford preparing a treaty-meeting submission. The grader's two gates plus ten subchecks were written to absorb the inherent fuzziness of identifying Antarctic stations from Overture `places.place` (no `research_station` category exists; reference uses keyword/category/proximity filters), with deliberately wide tolerances (count ±30 %, name overlap ≥60 %, total area ±40 %, mean area ±30 %, water station overlap ≥50 %, water area ±50 %). Three broken solutions seed the structural-gate, partial-credit, and planar-buffer failure modes.

#### Change log

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-11 | 9a1d43e | initial-authoring | First commit (later superseded). | Commit msg: "task: geo-l3-antarctica-stations-geodesic [completed]" (auto-generated). |
| 2026-05-12 | 33506b8 | initial-authoring | Re-landed final version of the task (grade.py, generate.py, metadata, README, reference outputs, three broken sets). | Commit msg states reference 1.0, three brokens 0.0/0.5/0.6, 35 lib tests pass. |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json` (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale). No prompt or grader change. | Commit msg: structured tags derived from inventory axes for filtering. |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" block listing exact column names, geometry types, value vocabulary for `water_source`. | Commit msg: declare exact output schema to match graders; no grader changes. |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/`. Path-only. | Commit msg: directory move. |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded the structured "Output schema:" bullets back into prose; preserved column names, geometry type, EPSG:3031, base.water/base.bathymetry literal vocabulary. | Commit msg: merge schema blocks into natural prose for 6 tasks; technical requirements preserved. |
| 2026-05-14 | f40e39e | prompt-change | Trivial wording: "Pull station points" → "Pull stations". | Commit msg: "Strip deducible information from GEO task instructions" — but the only diff here is `station points`→`stations`. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: commit message implies a broader strip, but the actual diff is one word; intent is partially supported. |
| 2026-05-15 | 6500d9a | prompt-change | Stripped the explicit "geodesic" requirement and the "project to EPSG:3031" + "clip to Antarctic landmass" + "union overlapping spheres" verbs from the body. Replaced with "geographically accurate at polar latitudes" and removed the procedural recipe. Output paragraph still says "in EPSG:3031". | Commit msg: "Strip deducible information from GEO task instructions (batch 2)" — consistent with diff (removes recipe-naming gifts). |
| 2026-05-17 | 64740d0 | prompt-change | Removed remaining nudges: replaced "geographically accurate at polar latitudes" with no qualifier, replaced "in EPSG:3031" output requirement with "an appropriate projected coordinate system for Antarctica", renamed "sphere" → "zone" in places. The grader still pins EPSG:3031 specifically. | Commit msg is titled "Remove answer-giving nudges from data-cleaning task prompts" but actually edits this GEO task. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Why: commit-message scope is "data-cleaning" tasks; including a GEO task is undocumented. The diff is internally consistent with the strip-deducible programme, but the mismatched commit message is the only documentation. |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path refactor) | Repo-wide reorg: `IMPLEMENTATION_NOTES.md`→`audit/AUTHORING_HISTORY.md`, `reference/{generate.py,outputs}` → `reference/solution/`, `tests/broken_*` → `reference/failures/broken_*`, `image*` → `assets/`. Grader's `REF_SPHERES`/`REF_WATER` paths updated. `TASK_DIR = HERE.parent.parent` in `generate.py`. Path-only — no semantic answer-key change. | Commit msg: layout reorganisation. |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: **2026-05-17T12:48:43Z** (commit `64740d0`, class: `prompt-change`).
- Later folder reorg `29a9ae3` (2026-05-26) is a path-only refactor that does not change instruction or grading; treated as `docs-change` for cutoff purposes (paths to ref outputs were updated in lockstep).

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:54:11Z | 1.0 | done | current (≈5 min after cutoff) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:24:31Z | 0.9 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:48:55Z | — | failed | current — model-side (max iterations exceeded, 100). Not evidence of task miscalibration. |

Stale (pre-cutoff, footnote only): runs from 2026-05-12 through 2026-05-17 06:14 span scores 0.0–1.0 across claude-code-{sonnet,opus}-basic and openrouter-deepseek-v4-flash-basic, with multiple failures (connect timeouts, max iterations, overload) and partial-credit dones at 0.6/0.7/0.9. Useful as historical context only.

#### Verdict

**calibrated**

Both current `done` runs hit the structural gates and the bulk of subchecks, with the deepseek-v4-flash run failing exactly one subcheck (`water_area_reasonable`: ratio 3.66 vs tolerance 0.50–1.50 → score 0.9). Both agents independently inferred EPSG:3031 and the need for geodesic buffering despite the instruction no longer naming either. The grader discriminates (one of the two runs is partially penalised) and the broken-solution set scores re-grade exactly as documented in `metadata.yaml > broken_solutions > measured_score` (0.0 / 0.5 / 0.6, matching expected ranges). The third current run failed with `RuntimeError: max iterations exceeded (100)` — a model-side failure on a Gemma model at agent-engineering, not a task problem.

#### Specific findings

- The instruction no longer names "geodesic", "EPSG:3031", or "Antarctic Polar Stereographic" explicitly; both observed competent agents still produced EPSG:3031 outputs with geodesic-area buffers within ±10 % of the reference mean. The CRS is inferable from the named region (Antarctica) and the format-table convention that GeoParquet does not pin a CRS by itself — agents must pick a projected CRS appropriate for the region. This is a legitimate L3 difficulty signal, not a prompt-grader inconsistency.
- The `water_source_attribution` subcheck and the literal vocabulary requirement (`base.water` / `base.bathymetry`) remain explicit in the prompt — necessary because the agent could otherwise label the source column with any string. Keep.
- One subcheck appearing in `score.json` for run-20260517-1424Z failed (`water_area_reasonable`, ratio 3.66 vs 0.50–1.50). The agent produced 3610 water-overlap features vs reference 2564 and ~3.66× the reference water area. Inspection of the score.json shows other subchecks (station_count 18 vs 16, water_station_overlap 66.67 %) within tolerance, so this is the grader correctly flagging an over-inflated water output rather than miscalibration. Not a flag.
- Inventory row matches current task contract (region antarctica, primary op buffer (geodesic, large-extent), secondaries clip + cascaded union, output CRS EPSG:3031, output GeoParquet MultiPolygon, medium scale). No inventory mismatch.
- The 17 May commit (`64740d0`) has a misleading commit message — its title is about data-cleaning tasks but the diff edits this GEO task. The change is internally consistent with the strip-deducible programme but is not explained by the commit message; flagged as `HR-002`. No action required other than recording the gap.
- The 14 May commit (`f40e39e`) is a one-word edit ("station points" → "stations") under a message claiming a broader strip; flagged as `HR-001` for design-rationale completeness.

### 3. Changes applied this run

#### Unilateral edits

- None. The task is calibrated and no instruction gift or grader miscalibration was identified.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — design-rationale — Commit `f40e39e` ("Strip deducible information from GEO task instructions") edits one word; commit message implies a wider intent than the diff supports. Low severity, no action required.
- HR-002 — design-rationale — Commit `64740d0` ("Remove answer-giving nudges from data-cleaning task prompts") edits this GEO task although the title scopes to data-cleaning. Diff is consistent with the strip-deducible programme; record only.

#### Tests run

- grader on reference: **1.0** (10/10 subchecks pass).
- broken-solution re-grade: `broken_wrong_crs` 0.0, `broken_no_coalition` 0.5, `broken_planar_buffer` 0.6 — all match `metadata.yaml > broken_solutions > measured_score`.
- pytest (benchmark/eval): **pass** (35 passed in 0.65s).

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

Re-audit of the L3 geometric-ops task. Original purpose unchanged from the prior review: probe geodesic buffering at extreme southern latitudes, land-mask clipping against the Antarctic coastline, cascaded union to detect overlapping station "coalitions", and a separate over-water attribution against Overture `base.water` / `base.bathymetry`. Inventory row (`benchmark/authoring/inventory.md:619`) declares region Antarctica, primary op buffer (geodesic, 200 km), secondaries clip + cascaded union, output CRS EPSG:3031, MultiPolygon GeoParquet, medium scale, persona Dr. Ellis Whitford (British Antarctic Survey) preparing a treaty-meeting submission. The grader is two gates + ten subchecks with wide L3 tolerances (count ±30 %, name overlap ≥60 %, total area ±40 %, mean area ±30 %, water-station overlap ≥50 %, water area ±50 %) to absorb the inherent fuzziness of identifying Antarctic stations from `places.place` (no `research_station` category; reference uses keyword + category-exclusion + 10 km proximity dedup). Three broken solutions seed the structural-gate, partial-credit, and planar-buffer failure modes.

#### Change log

The chronological commit history is unchanged from the 2026-05-26 review and is reproduced here for completeness; the only new commit since that review is the prior evaluator's own artefact commit (`68fc90d`), a docs-change.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-11 | 9a1d43e | initial-authoring | First commit (later superseded). | Commit msg: auto-generated "[completed]". |
| 2026-05-12 | 33506b8 | initial-authoring | Re-landed final task (grade.py, generate.py, metadata, README, reference outputs, three broken sets). | Commit msg: reference 1.0, brokens 0.0/0.5/0.6, 35 lib tests pass. |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json`. No prompt/grader change. | Commit msg: structured tags from inventory axes. |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" block. | Commit msg: declare exact output schema; no grader changes. |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/`. Path-only. | Commit msg: directory move. |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded "Output schema:" bullets back into prose; column names / geometry / EPSG:3031 / literal vocabulary preserved. | Commit msg: merge schema blocks into prose for 6 tasks. |
| 2026-05-14 | f40e39e | prompt-change | One-phrase wording: "Pull station points from" → "Pull stations from". Instruction still named geodesic, EPSG:3031, and the full procedural recipe at this point. | Commit msg: "Strip deducible information from GEO task instructions" — broader than the one-phrase diff. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: commit message implies a wider strip than the diff supports. |
| 2026-05-15 | 6500d9a | prompt-change | Stripped explicit "geodesic" requirement and the "project to EPSG:3031" / "clip to Antarctic landmass" / "union overlapping spheres" verbs; replaced with "geographically accurate at polar latitudes" and removed the recipe. Output paragraph still said "in EPSG:3031". | Commit msg: "Strip deducible information from GEO task instructions (batch 2)" — consistent with diff. |
| 2026-05-17 | 64740d0 | prompt-change | Removed remaining nudges: dropped "geographically accurate at polar latitudes", replaced "in EPSG:3031" with "an appropriate projected coordinate system for Antarctica", renamed "sphere" → "zone". Grader still pins EPSG:3031. | Commit msg titled "Remove answer-giving nudges from data-cleaning task prompts" but edits this GEO task. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Why: commit-message scope is "data-cleaning" tasks; including a GEO task is undocumented. Diff is internally consistent with the strip-deducible programme. |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path refactor) | Repo-wide reorg: `IMPLEMENTATION_NOTES.md`→`audit/AUTHORING_HISTORY.md`, `reference/{generate.py,outputs}`→`reference/solution/`, `tests/broken_*`→`reference/failures/broken_*`, `image*`→`assets/`; grader `REF_*` paths updated. Path-only. | Commit msg: layout reorganisation. |
| 2026-05-26 | 68fc90d | docs-change | Prior evaluator artefact commit (AUTHORING_HISTORY.md, coverage.yaml, status.json). No instruction/grader/reference change. | Commit msg: "Re-evaluate … calibrated, 2 low-severity design-rationale flags". |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: **2026-05-17T12:48:43Z** (commit `64740d0`, class: `prompt-change`).
- Later commits `29a9ae3` (path-only reorg, grader ref-paths updated in lockstep) and `68fc90d` (evaluator artefacts) are `docs-change` and do not invalidate runs. Unchanged from the prior review.

#### Runs considered

No new runs have appeared since the 2026-05-26 review; the same three current runs are re-examined. Per-task `started_at` (from each `run.json` task block) is used for validity, all after cutoff.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:50:44Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T17:54:29Z | 0.9 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:07:44Z | — | failed | current — model-side (`RuntimeError: max iterations exceeded (100)`, no outputs). Not task-miscalibration evidence. |

Stale (pre-cutoff, footnote only): runs from 2026-05-12 through 2026-05-17 06:14 span scores 0.0–1.0 across claude-code-{sonnet,opus}-basic and openrouter-deepseek-v4-flash-basic, with multiple connect-timeout / max-iterations / overload failures and partial dones (0.6/0.7/0.9). Historical context only.

#### Verdict

**calibrated**

Re-confirmed. Both current `done` runs clear both structural gates with matching output CRS (EPSG:3031), MultiPolygon geometry, and the full required column sets on both outputs; counts vary within the documented L3 tolerances (spheres 14 / 16-ref / 18; water 1370 / 2564-ref / 3610). The opus run scores 1.0 (10/10 subchecks); the deepseek run scores 0.9, failing exactly one subcheck (`water_area_reasonable`, ratio 3.66 vs 0.50–1.50) — the grader correctly flagging an over-inflated water output, demonstrating discrimination. Both agents independently produced EPSG:3031 and geodesic-magnitude buffers despite the instruction no longer naming either, which is the intended L3 difficulty signal (region Antarctica + GeoParquet-does-not-pin-CRS convention). The third current run is a model-side Gemma failure (agent-engineering), not a task problem. Reference re-grades 1.0 and the three broken solutions re-grade 0.0 / 0.5 / 0.6, exactly matching `metadata.yaml > broken_solutions > measured_score`. pytest passes (35/35).

#### Specific findings

- **CRS / format consistency (2c-CRS).** Reference output CRS = EPSG:3031 matches `expected_outputs[].crs` and the README ("EPSG:3031, MultiPolygon"). The grader reads submission and reference in their stored CRS (both EPSG:3031) and computes `.area` on both sides without reprojecting only one — no one-sided reprojection. The `crs_is_3031` subcheck validates the submission's CRS metadata directly. Fully consistent; no finding.
- The instruction no longer names "geodesic", "EPSG:3031", or "Antarctic Polar Stereographic"; competent agents still inferred both. Legitimate L3 difficulty, not a prompt-grader inconsistency.
- The literal `water_source` vocabulary (`base.water` / `base.bathymetry`) remains explicit in the prompt — necessary, since the agent could otherwise label that column arbitrarily. Keep.
- `water_area_reasonable` failing on the deepseek run is correct grader behaviour (3610 features / 3.66× ref water area), not miscalibration. Not a flag.
- Inventory row matches the current task contract on every axis. No inventory mismatch.
- Commits `f40e39e` and `64740d0` carry commit messages that under- / mis-describe their actual diffs; re-flagged as HR-001 and HR-002 for design-rationale completeness. No action beyond recording.

### 3. Changes applied this run

#### Unilateral edits

- None. The task is calibrated; no instruction gift or grader miscalibration was identified, so no edit to `task.json`, `grade.py`, or `metadata.yaml` is justified. The three broken `measured_score`s already match the live re-grade, so no metadata refresh is needed either.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — design-rationale — Commit `f40e39e` ("Strip deducible information from GEO task instructions") changed only one phrase ("Pull station points" → "Pull stations"); the message implies a broader strip than the diff supports. Low severity, no action required.
- HR-002 — design-rationale — Commit `64740d0` ("Remove answer-giving nudges from data-cleaning task prompts") edits this GEO task although its title scopes to data-cleaning. Diff aligns with the strip-deducible programme; only the commit message is mis-scoped. Record only.

#### Tests run

- grader on reference: **1.0** (10/10 subchecks pass).
- broken-solution re-grade: `broken_wrong_crs` 0.0, `broken_no_coalition` 0.5, `broken_planar_buffer` 0.6 — all match `metadata.yaml > broken_solutions > measured_score`.
- pytest (benchmark/eval): **pass** (35 passed in 0.61s).

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

Re-audit of the L3 geometric-ops task. Original purpose unchanged from prior reviews: probe geodesic buffering at extreme southern latitudes, land-mask clipping against the Antarctic coastline, cascaded union to detect overlapping station "coalitions", and a separate over-water attribution against Overture `base.water` / `base.bathymetry`. Inventory row (`benchmark/authoring/inventory.md:619`) declares region Antarctica, primary op buffer (geodesic, 200 km), secondaries clip + cascaded union, output CRS EPSG:3031, MultiPolygon GeoParquet, medium scale, persona Dr. Ellis Whitford (British Antarctic Survey). Grader: two gates + ten subchecks with wide L3 tolerances (count ±30 %, name overlap ≥60 %, total area ±40 %, mean area ±30 %, water-station overlap ≥50 %, water area ±50 %). Three broken solutions seed the structural-gate, partial-credit, and planar-buffer failure modes.

#### Change log

The chronological commit history is unchanged from the 2026-05-27 review. Two new commits since: the prior evaluator artefact commit (`d2aaab3`) and a global infra commit (`622342b`) that removed `prompt_version` from this task's `metadata.yaml`. Neither changes instruction/grader/inputs/reference for this task.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-11 | 9a1d43e | initial-authoring | First commit (later superseded). | Commit msg: auto-generated "[completed]". |
| 2026-05-12 | 33506b8 | initial-authoring | Re-landed final task (grade.py, generate.py, metadata, README, reference outputs, three broken sets). | Commit msg: reference 1.0, brokens 0.0/0.5/0.6, 35 lib tests pass. |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json`. No prompt/grader change. | Commit msg: structured tags from inventory axes. |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" block. | Commit msg: declare exact output schema; no grader changes. |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/`. Path-only. | Commit msg: directory move. |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded "Output schema:" bullets back into prose; column names / geometry / EPSG:3031 / literal vocabulary preserved. | Commit msg: merge schema blocks into prose for 6 tasks. |
| 2026-05-14 | f40e39e | prompt-change | One-phrase wording: "Pull station points from" → "Pull stations from". | Commit msg: "Strip deducible information from GEO task instructions" — broader than the diff. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: commit message implies a wider strip than the diff supports. |
| 2026-05-15 | 6500d9a | prompt-change | Stripped explicit "geodesic" requirement and the "project to EPSG:3031" / "clip to Antarctic landmass" / "union overlapping spheres" verbs; replaced with "geographically accurate at polar latitudes". Output paragraph still said "in EPSG:3031". | Commit msg: "Strip deducible information from GEO task instructions (batch 2)" — consistent with diff. |
| 2026-05-17 | 64740d0 | prompt-change | Removed remaining nudges: dropped "geographically accurate at polar latitudes", replaced "in EPSG:3031" with "an appropriate projected coordinate system for Antarctica", renamed "sphere" → "zone". Grader still pins EPSG:3031. | Commit msg titled "Remove answer-giving nudges from data-cleaning task prompts" but edits this GEO task. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Why: commit-message scope is "data-cleaning" tasks; including a GEO task is undocumented. Diff is internally consistent with the strip-deducible programme. |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path refactor) | Repo-wide reorg: `IMPLEMENTATION_NOTES.md`→`audit/AUTHORING_HISTORY.md`, `reference/{generate.py,outputs}`→`reference/solution/`, `tests/broken_*`→`reference/failures/broken_*`, `image*`→`assets/`; grader `REF_*` paths updated. Path-only. | Commit msg: layout reorganisation. |
| 2026-05-26 | 68fc90d | docs-change | Prior evaluator artefact commit. | Commit msg: "Re-evaluate … calibrated, 2 low-severity design-rationale flags". |
| 2026-05-27 | d2aaab3 | docs-change | Prior evaluator artefact commit (AUTHORING_HISTORY.md append, status.json refresh; no coverage.yaml diff). | Commit msg: "Re-evaluate … calibrated, no edits". |
| 2026-05-28 | 622342b | docs-change | Global infra commit: removed unused `prompt_version` line from this task's `metadata.yaml`; introduced repo-wide `task.json.version` semantics (this task has not yet had a meaningful unilateral edit, so `version` is still implicit v1). No instruction/grader/inputs/reference change. | Commit msg: "Add task content versioning; drop unused prompt_version". |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: **2026-05-17T12:48:43Z** (commit `64740d0`, class: `prompt-change`).
- Later commits `29a9ae3`, `68fc90d`, `d2aaab3`, and `622342b` are all `docs-change` (path-only reorg / evaluator artefacts / metadata-cleanup that drops an unused field) and do not invalidate runs.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:50:44Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T17:54:29Z | 0.9 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:07:44Z | — | failed | current — model-side (max iterations exceeded, no outputs). |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T22:33:05Z | 0.8 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:58:42Z | 0.0 | done | current — produced no outputs (model-side; Gate-1 reject). |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:46:40Z | 0.9 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:09:08Z | 0.0 | done | current — produced no outputs (model-side; Gate-1 reject). |

Stale (pre-cutoff, footnote only): runs from 2026-05-12 through 2026-05-17 06:14 span scores 0.0–1.0 across claude-code-{sonnet,opus}-basic and openrouter-deepseek-v4-flash-basic, with multiple connect-timeout / max-iterations / overload failures.

#### Verdict

**calibrated**

Reconfirmed. The grader continues to discriminate cleanly:
- claude-code-opus runs span 0.8–1.0 (one new opus run at 0.8 failed `station_name_overlap` and `water_station_overlap` after picking a 12.5 % / 8.33 % overlapping but largely disjoint station set — grader correctly penalising; another at 0.9 failed `water_area_reasonable` with ratio 4.05).
- openrouter-deepseek-v4-flash 0.9 (failed `water_area_reasonable` ratio 3.66).
- openrouter-gemma4-26b: three runs, all failed at the agent-engineering level (one max-iterations, two produced no `station_spheres.geoparquet` despite reaching `status: done`). These are model-side failures (Gemma is unable to drive the multi-step pipeline) and are correctly Gate-1-rejected — not task-miscalibration evidence.

Both gates clear for every competent attempt; coordinates are in EPSG:3031 metric range; subchecks land in the wide-but-meaningful tolerances. Reference re-grades 1.0 (10/10) and the three broken solutions re-grade 0.0 / 0.5 / 0.6, exactly matching `metadata.yaml > broken_solutions > measured_score`. pytest passes 41/41 (count grew from 35 → 41 with `prompt_version`-removal and versioning-infra tests; not task-specific).

#### Specific findings

- **CRS / format consistency (2c-CRS).** Reference output CRS = EPSG:3031 matches `expected_outputs[].crs` and the README ("EPSG:3031, MultiPolygon"). The grader reads submission and reference in their stored CRS (both EPSG:3031) and computes `.area` on both sides without one-sided reprojection. The `crs_is_3031` subcheck validates the submission's CRS metadata directly. Fully consistent; no finding.
- The instruction still does not name "geodesic", "EPSG:3031", or "Antarctic Polar Stereographic"; competent agents still produced EPSG:3031 and geodesic-magnitude buffers. Legitimate L3 difficulty, not a prompt-grader inconsistency.
- The literal `water_source` vocabulary (`base.water` / `base.bathymetry`) remains explicit in the prompt — necessary, since the agent could otherwise label that column arbitrarily. Keep.
- Subcheck failures on `water_area_reasonable` (opus 0.9, deepseek 0.9) and `station_name_overlap`/`water_station_overlap` (opus 0.8) are correct grader behaviour — over-inflated water outputs and a divergent station-identification choice. Not miscalibration.
- Inventory row matches the current task contract on every axis. No inventory mismatch.
- Two prior-review HR flags (HR-001, HR-002) re-recorded for design-rationale completeness; no action beyond recording.
- Task content versioning (`622342b`) introduces a `version` field on `task.json` but this task currently carries no explicit `version` (implicit v1). Since this evaluator run applies no unilateral edits that change prompt/grader/inputs, no version bump is owed.

### 3. Changes applied this run

#### Unilateral edits

- None. The task is calibrated; no instruction gift or grader miscalibration was identified. Broken `measured_score`s already match the live re-grade, so no metadata refresh is needed either. No version bump owed (no unilateral edit changes the prompt/grader/inputs contract).

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — design-rationale — Commit `f40e39e` ("Strip deducible information from GEO task instructions") changed only one phrase ("Pull station points" → "Pull stations"); the message implies a broader strip than the diff supports. Low severity, no action required.
- HR-002 — design-rationale — Commit `64740d0` ("Remove answer-giving nudges from data-cleaning task prompts") edits this GEO task although its title scopes to data-cleaning. Diff aligns with the strip-deducible programme; only the commit message is mis-scoped. Record only.

#### Tests run

- grader on reference: **1.0** (10/10 subchecks pass).
- broken-solution re-grade: `broken_wrong_crs` 0.0, `broken_no_coalition` 0.5, `broken_planar_buffer` 0.6 — all match `metadata.yaml > broken_solutions > measured_score`.
- pytest (benchmark/eval): **pass** (41 passed in 0.51s).

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

Re-audit of the L3 geometric-ops task. Original purpose unchanged from prior reviews: probe geodesic buffering at extreme southern latitudes, land-mask clipping against the Antarctic coastline, cascaded union to detect overlapping station "coalitions", and a separate over-water attribution against Overture `base.water` / `base.bathymetry`. Inventory row (`benchmark/authoring/inventory.md:619`) declares region Antarctica, primary op buffer (geodesic, 200 km), secondaries clip + cascaded union, output CRS EPSG:3031, MultiPolygon GeoParquet, medium scale, persona Dr. Ellis Whitford (British Antarctic Survey). Grader: two gates + ten subchecks with wide L3 tolerances (count ±30 %, name overlap ≥60 %, total area ±40 %, mean area ±30 %, water-station overlap ≥50 %, water area ±50 %). Three broken solutions seed the structural-gate, partial-credit, and planar-buffer failure modes.

#### Change log

Chronological history unchanged from the 2026-05-28 review. Two new global commits since (`05aabd6` soft-CRS refactor 2026-05-28, `bf9ccce` OGC:CRS84 accept 2026-05-29) did **not** touch this task's `grade.py` — this grader still uses the original `_is_epsg_3031` hard-fail-on-degrees Gate 2 plus the `crs_is_3031` subcheck; the soft-CRS helper was not adopted here (canonical EPSG:3031 stands; no meaningful CRS alternatives for Antarctica in the run record). No other commits touched this task between the last review and now.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-11 | 9a1d43e | initial-authoring | First commit (later superseded). | Commit msg: auto-generated "[completed]". |
| 2026-05-12 | 33506b8 | initial-authoring | Re-landed final task. | Commit msg: reference 1.0, brokens 0.0/0.5/0.6. |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json`. | Commit msg: structured tags from inventory axes. |
| 2026-05-13 | 1710715 | prompt-change | Added explicit "Output schema:" block. | Commit msg: declare exact output schema. |
| 2026-05-13 | a3a8d53 | docs-change | Path move `benchmark/eval/tasks/` → `benchmark/tasks/`. | Commit msg: directory move. |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded schema bullets back into prose. | Commit msg: merge schema blocks. |
| 2026-05-14 | f40e39e | prompt-change | One-phrase wording: "Pull station points" → "Pull stations". | Commit msg implies broader strip than diff supports. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: commit message implies a wider strip than the diff supports. |
| 2026-05-15 | 6500d9a | prompt-change | Stripped explicit "geodesic" / "project to EPSG:3031" / "clip to landmass" / "union overlapping spheres" verbs. | Commit msg: strip-deducible batch 2. |
| 2026-05-17 | 64740d0 | prompt-change | Dropped "geographically accurate at polar latitudes"; replaced "in EPSG:3031" with "an appropriate projected coordinate system for Antarctica"; renamed "sphere" → "zone". | Commit msg titled "Remove answer-giving nudges from data-cleaning task prompts" though this is a GEO task. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Why: commit-message scope is "data-cleaning" tasks; including this GEO task is undocumented. Diff is internally consistent with the strip-deducible programme. |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path refactor) | Repo-wide reorg; grader `REF_*` paths updated in lockstep. Path-only. | Commit msg: layout reorganisation. |
| 2026-05-26 | 68fc90d | docs-change | Prior evaluator artefact commit. | Commit msg: "Re-evaluate … calibrated, 2 low-severity design-rationale flags". |
| 2026-05-27 | d2aaab3 | docs-change | Prior evaluator artefact commit. | Commit msg: "Re-evaluate … calibrated, no edits". |
| 2026-05-28 | 622342b | docs-change | Global infra: removed unused `prompt_version` line; introduced repo-wide `task.json.version` semantics. | Commit msg: "Add task content versioning". |
| 2026-05-28 | a4b05ce | docs-change | Prior evaluator artefact commit. | Commit msg: "Re-evaluate … calibrated, no edits". |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: **2026-05-17T12:48:43Z** (commit `64740d0`, class: `prompt-change`).
- Later commits (`29a9ae3`, `68fc90d`, `d2aaab3`, `622342b`, `a4b05ce`) are all `docs-change` / path-only / metadata-cleanup / evaluator artefacts and do not invalidate runs. The global `05aabd6` soft-CRS refactor did not touch this grader, and `bf9ccce` only affects WGS84 / CRS84 normalisation (irrelevant here).

#### Runs considered

Many new current runs since the 2026-05-28 review. Per-task `started_at` from each `run.json` task block.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:50:44Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T17:54:29Z | 0.9 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:07:44Z | — | failed | current — model-side (max iterations exceeded). |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T22:33:05Z | 0.8 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:58:42Z | 0.0 | done | current — produced no outputs (model-side). |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:46:40Z | 0.9 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:09:08Z | 0.0 | done | current — no outputs (model-side). |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:46:02Z | 0.0 | done | current — no outputs (model-side). |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T21:54:55Z | 0.5 | done | current — 47 stations, 6.25 % name overlap (over-fetched POIs). |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:18:21Z | 0.0 | done | current — no outputs (model-side). |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:31:24Z | 0.9 | done | current — failed `station_name_overlap` 56.25 % (just under 60 %). |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:04:37Z | 0.0 | done | current — no outputs (model-side). |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T17:17:45Z | 1.0 | done | current. |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:23:18Z | 0.0 | done | current — no outputs (model-side). |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:41:33Z | 0.0 | done | current — produced only 2 stations (Gate 2 fail). |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled | current — orchestrator-cancelled. |

Stale (pre-cutoff, footnote only): 2026-05-12 → 2026-05-17 06:14 runs spanning 0.0–1.0 across claude-code-{sonnet,opus} and openrouter-deepseek-v4-flash with multiple timeouts; historical context only.

#### Verdict

**calibrated**

The grader continues to discriminate cleanly across three agent families:
- **claude-code-opus (5 current runs):** scores 0.5 / 0.8 / 0.9 / 0.9 / 1.0 — the 0.5 stems from over-fetching to 47 stations and 6.25 % name overlap (correct grader behaviour for an inflated POI set); the 0.9s fail one subcheck each (water-area or station-name boundary); the 1.0 is the clean reference-like solution. This is exactly the score spread a well-calibrated L3 task should produce.
- **openrouter-deepseek (2 current runs across V4-flash and V4-pro):** 0.9 and 1.0 — both clear all gates with 13–18 stations and area ratios near 1.0.
- **openrouter-gemma4-26b (7 current runs):** all model-side failures (either max-iterations, no outputs, or `only 2 stations` Gate-2 reject). Gemma cannot drive the multi-step pipeline; not task-miscalibration evidence.

Reference re-grades 1.0 (10/10) and the three broken solutions re-grade 0.0 / 0.5 / 0.6, exactly matching `metadata.yaml > broken_solutions > measured_score`. pytest passes 41/41.

#### Specific findings

- **CRS / format consistency (2c-CRS).** Reference output CRS = EPSG:3031 matches `expected_outputs[].crs` and the README ("EPSG:3031, MultiPolygon"). The grader reads submission and reference in their stored CRS (both EPSG:3031) and computes `.area` on both sides without one-sided reprojection. The `crs_is_3031` subcheck validates submission CRS directly. The global soft-CRS refactor (`05aabd6`) did not touch this grader; the hard-degree-range check in Gate 2 remains, but the run record contains zero parseable submissions in any non-canonical projected CRS — every current `done` run that cleared Gate 1 also landed on EPSG:3031. No `prompt-grader-inconsistent` here, and no CRS accept-list refactor is justified by the evidence. Fully consistent; no finding.
- The instruction still does not name "geodesic", "EPSG:3031", or "Antarctic Polar Stereographic"; competent agents (opus, deepseek-pro) still produced EPSG:3031 and geodesic-magnitude buffers. Legitimate L3 difficulty signal, not a prompt-grader inconsistency.
- The literal `water_source` vocabulary (`base.water` / `base.bathymetry`) remains explicit in the prompt — necessary, since the agent could otherwise label that column arbitrarily. Keep.
- Subcheck failures across runs (`station_name_overlap` 6.25 % / 56.25 %, `water_area_reasonable` 3.34 / 4.05, `station_count_tolerance` 47) are all correct grader behaviour, not miscalibration.
- Inventory row matches the current task contract on every axis. No inventory mismatch.
- Prior-review HR flags (HR-001, HR-002) are about pre-2026-05-17 commit messages whose scope under- or mis-describes the diff. Re-recorded for design-rationale completeness; no action beyond recording.

### 3. Changes applied this run

#### Unilateral edits

- `task.json` — house-style rewrite of the `instruction`. Removed the em-dash, rewrote the spec-grammar fragment "Second output:" into a full sentence, softened the opener from "Need to prepare" to "I need to put together". Preserved every factual constraint (200 km radius, south of -60 latitude, station_id / station_name / coalition columns, water_id / water_name / water_subtype / water_source literal vocabulary, GeoParquet + MultiPolygon + projected-CRS-for-Antarctica output schema, both filenames), the persona context (Antarctic Treaty consultative meeting), and the deliberate omissions (no "geodesic" word, no EPSG code, no "polar stereographic" mention). Re-grade on reference: 1.0.
- `task.json` — added `analyst_notes` (description / approach / pitfalls). Documents the hidden polar-distortion gotcha, the station-identification ambiguity from `places.place`, and the failure modes the grader catches. Human-facing only; not visible to the agent at run time.
- `task.json` — added explicit `version: 2` (was implicit v1). The house-style instruction rewrite is a meaningful prompt change per the version-bump rules; `analyst_notes` alone would not have required a bump.

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — design-rationale — Commit `f40e39e` ("Strip deducible information from GEO task instructions") changed only one phrase ("Pull station points" → "Pull stations"); the message implies a broader strip than the diff supports. Low severity, no action required.
- HR-002 — design-rationale — Commit `64740d0` ("Remove answer-giving nudges from data-cleaning task prompts") edits this GEO task although its title scopes to data-cleaning. Diff aligns with the strip-deducible programme; only the commit message is mis-scoped. Record only.

#### Tests run

- grader on reference: **1.0** (10/10 subchecks pass) — post-edit.
- broken-solution re-grade: `broken_wrong_crs` 0.0, `broken_no_coalition` 0.5, `broken_planar_buffer` 0.6 — all match `metadata.yaml > broken_solutions > measured_score`.
- pytest (benchmark/eval): **pass** (41 passed in 0.40s).

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Minimum-5-stations check migrated to new subcheck
  `min_station_count`.
- Sphere-geometry-types-Polygon/MultiPolygon check migrated to new
  subcheck `sphere_geometry_types`.
- Sphere-coords-in-projected-metre-range check migrated to new
  subcheck `sphere_coords_projected`.
- Subcheck count: 10 → 13.

### Verification
- Reference solution re-graded: 1.0 (13/13 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

Re-audit of the L3 geometric-ops task; original purpose unchanged from prior reviews. The task probes geodesic buffering at extreme southern latitudes (200 km radius where planar buffers are severely distorted), land-mask clipping against the Antarctic coastline, cascaded union into overlapping-station "coalitions", and over-water attribution against Overture `base.water` / `base.bathymetry`. Inventory row (`benchmark/authoring/inventory.md:619`) declares region Antarctica, primary op buffer (geodesic, large-extent), secondaries clip + cascaded union, output CRS EPSG:3031, MultiPolygon GeoParquet, medium scale, persona Dr. Ellis Whitford (British Antarctic Survey). The grader is now a single hard gate (`format_schema_valid`) plus 13 subchecks, six of which carry weight 3.0 (data-content checks), after two benchmark-wide grader refactors since the last review.

#### Change log

Pre-2026-06-06 history is unchanged from the 2026-06-06 review (see that block). New commits since the last evaluator pass:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | a249a39 | prompt-change (evaluator) | House-style instruction rewrite, `analyst_notes` added, `version` 1 -> 2. | Commit msg: prior evaluator pass (documented in the 2026-06-06 block). |
| 2026-06-06 | 363aed2 | grader-change | Removed Gate 2 (`structural_correctness`); its three checks (min 5 stations, Polygon/MultiPolygon types, projected-metre coordinate range) migrated to subchecks `min_station_count`, `sphere_geometry_types`, `sphere_coords_projected`. Subcheck count 10 -> 13. | Commit msg: benchmark-wide refactor to one hard gate; shape-recoverable output costs points instead of collapsing to 0. |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to the six data-content subchecks (`station_count_tolerance`, `station_name_overlap`, `buffer_area_reasonable`, `water_station_overlap`, `water_area_reasonable`, `geodesic_buffer_check`); schema/structural checks stay at 1.0. Total weight 25. | Commit msg: weight data-content subchecks 3x across all categories. |
| 2026-06-08 | fb24a1f | docs-change | Added `viz_globe: true` to `task.json` (eval-UI map rendering flag only; not seen by the agent, not used by the grader). | Commit msg: polar tasks unreadable in Web Mercator; opt-in globe projection for the run-task view. |

Neither grader-change commit bumped `task.json > version` (still 2), so the eval UI's version-based de-emphasis does not distinguish runs scored before vs. after the gate-removal/weighting refactors; only the timestamp cutoff catches it (see HR-002).

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: **2026-06-07T18:32:38Z** (commit `c749e57`, class: grader-change).
- `fb24a1f` (viz_globe) is a UI-only flag and does not invalidate runs.
- Version check: all candidate runs' `suite_git_sha` resolve to `task.json` version 2 (current), so validity is decided by the timestamp cutoff alone.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-09T06:53:17Z | 0.4 | done | current |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T14:30:16Z | 0.4 | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T15:51:45Z | 0.2 | done | stale (pre-weighting; scored under the unweighted 13-subcheck grader) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:31:21Z | 0.0 | done | stale (pre-gate-removal) |

Stale footnote: all earlier runs (2026-05-12 through 2026-06-06) predate the gate-removal and weighting refactors and are catalogued in the prior review blocks; under the old grader they spanned 0.0-1.0 across claude-opus, deepseek-flash/pro, and gemma families.

#### Verdict

**insufficient-evidence**

Both current runs come from a single agent family (deepseek-v4-flash, basic + gis_detailed prompt variants), which by the verdict rules is insufficient evidence on its own. What the two runs do show is consistent with prior calibration findings rather than against them: both scored 0.4 with the identical failure signature (station over-collection: 39 and 34 stations vs reference 16; name overlap 6.25% / 18.75%; inflated total buffer area 2.27x / 1.54x; inflated water area 7.75x / 6.88x) while passing the CRS, geodesic-mean-area, coalition, schema, and water-attribution checks. Existing `retrospective.json` analyses classify both as `model_error`: the detailed-variant run fetched Overture `division` features instead of `places.place` (outputs/solve.py line 25), and the basic-variant run identified candidate stations but skipped its own planned dedup/filter step, writing all 34 candidates through. These are station-identification failures the task is designed to test, not grader miscalibration. The grader discriminated correctly (geodesic mechanics earned the 3.0-weight `geodesic_buffer_check`; sloppy identification lost the four 3.0-weight count/area checks). No too-strict or too-easy signal; the static audits below also pass.

#### Prompt information audit

| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| two output filenames, GeoParquet | instruction, output paragraph | stated |
| sphere columns station_id/station_name/coalition | instruction | stated |
| water columns station_id/station_name/water_id/water_name/water_subtype/water_source | instruction | stated |
| water_source literal values base.water / base.bathymetry | instruction (literal Overture theme names) | stated |
| coalition column >1 distinct value | instruction ("has to take more than one distinct value") | stated |
| MultiPolygon geometry | instruction | stated |
| projected CRS, canonical EPSG:3031 | instruction names "an appropriate projected coordinate system for Antarctica"; EPSG:3031 inferable from regional convention (deliberate L3 omission; 1.0-weight subcheck, not a gate) | inferable |
| 200 km radius, south of -60 latitude | instruction | stated |
| geodesic (not planar) buffer | domain expertise at polar latitudes; mean-area subcheck ±30% | inferable |
| station count within ±30% of 16 | sensible research-station filtering + dedup of Overture places.place; wide L3 tolerance | inferable |
| station name overlap >=60% | carrying Overture primary names through as station_name | inferable |
| land clip / total area ±40%, water area ±50% | instruction asks for land-clipped zones and over-water portions; tolerances are standard drift margins | inferable |
| >=5 stations | dozens of Antarctic stations exist; any sensible set passes | inferable |

Factual claims verified: both filenames, all column names, the 200 km radius, the -60 latitude cutoff, and the `base.water`/`base.bathymetry` literals match `reference/solution/generate.py` and the reference output schemas. No inaccurate claim found. (No `inputs/` directory; the task is live-fetch by design.)

#### Reference faithfulness

`reference/solution/generate.py` implements the instruction as written: fetches `places.place` south of -60 with keyword + category-exclusion + 10 km proximity dedup to identify research stations (filtering is implied by "Each Antarctic research station"; the inherent ambiguity is absorbed by the documented wide tolerances), draws true geodesic 200 km buffers on the WGS84 ellipsoid (128-point), clips to `base.land`, assigns coalition ids via union-find over overlapping clipped spheres (per-station features retained, matching "every feature needs station_id and station_name"), computes over-water portions as buffer-minus-land intersected with water + bathymetry carrying the literal `water_source` theme names, and writes both outputs as EPSG:3031 MultiPolygon GeoParquet. Output CRS/format/geometry agree with `expected_outputs[]`, the README, and the inventory row. **Faithful.**

#### Specific findings

- **CRS / format consistency (2c-CRS).** Reference outputs are EPSG:3031, matching `expected_outputs[].crs` and the README. The grader compares submission and reference areas in their stored CRSes with no one-sided reprojection; both current submissions were EPSG:3031. Since the gate-2 removal, a defensible non-canonical projected CRS no longer hard-fails: it loses only the 1.0-weight `crs_is_3031` (and the ±40%/±30% area tolerances absorb polar-stereographic-family scale differences), which already gives the graceful degradation the CRS accept-list refactor aims for. No refactor needed; no finding.
- **Broken-set expected range now stale (HR-001).** Under the post-refactor grader, `broken_wrong_crs` re-grades at 0.56 against `expected_score_range: [0.0, 0.0]` (the range was authored when wrong-CRS output zero-scored at Gate 2). `broken_no_coalition` (0.48) and `broken_planar_buffer` (0.52) stay inside their ranges. `measured_score` values refreshed; the range mismatch needs a human call (bless a new range, or decide 0.56 is too lenient for a wrong-CRS submission and re-weight the CRS subchecks). Likely repeats in other tasks whose broken sets relied on Gate 2.
- **Version not bumped by global grader refactors (HR-002).** `363aed2` and `c749e57` changed grading semantics for every task without bumping `task.json > version`, so version-based run de-emphasis in the eval UI cannot distinguish pre/post-refactor runs. Recorded for the orchestrator; benchmark-wide process gap, not specific to this task.
- Stale Gate-2 references fixed: README failure modes 2 and 4 and `analyst_notes` pitfalls 2 and 4 still described Gate 2 / "structural gate" semantics; updated to name the migrated subchecks. Docs-only; no version bump owed.
- Prior-review design-rationale flags about pre-2026-05-17 commit messages (`f40e39e` one-word diff under a broad message; `64740d0` GEO edit under a data-cleaning-scoped title) re-recorded as HR-003 / HR-004; record-only, no action required.
- Inventory row matches the current task contract on every axis. No inventory mismatch.

### 3. Changes applied this run

#### Unilateral edits

- `metadata.yaml`: refreshed `broken_solutions > measured_score` to the current weighted grader (0.0 -> 0.56, 0.5 -> 0.48, 0.6 -> 0.52) and updated the stale `broken_wrong_crs` description ("fails structural gate" -> fails CRS/coordinate-range/area subchecks). Re-grade on reference: 1.0. Reason: gate-removal + weighting commits changed broken-set scores without refreshing metadata.
- `README.md`: failure modes 2 and 4 no longer reference the removed Gate 2; they now name `sphere_coords_projected` / `min_station_count`. Re-grade on reference: 1.0. Reason: stale docs after grader refactor.
- `task.json` (`analyst_notes` only): pitfalls 2 and 4 no longer claim a structural gate / Gate 2; reworded to subcheck semantics. Human-facing field; no version bump required. Re-grade on reference: 1.0.

No `version` bump owed: all edits are in the bump-exempt list (README, analyst_notes, measured_score refresh, audit artefacts).

#### Proposed but not applied (see HUMAN-REVIEW items)

- <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="med" --> HR-001 — grader-miscalibration-suspected — `broken_wrong_crs` measures 0.56 but `expected_score_range` is `[0.0, 0.0]`; the range predates the Gate-2 removal. Human must either bless a new range (measured behaviour is consistent with the deliberate one-hard-gate philosophy) or judge 0.56 too lenient for a wrong-CRS submission on a task whose core lesson is polar CRS choice and adjust subcheck weights. The same staleness plausibly affects other tasks' gate-dependent broken sets.
- <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> HR-002 — design-rationale — Global grader refactors `363aed2` (gate removal) and `c749e57` (3x weights) changed scoring semantics without bumping any task's `version`, so the eval UI's version check cannot de-emphasise pre-refactor runs; only the audit-time timestamp cutoff catches it. Benchmark-wide process question, recorded here.
- <!-- HUMAN-REVIEW id="HR-003" category="design-rationale" severity="low" --> HR-003 — design-rationale — Commit `f40e39e` changed one phrase under a message implying a broader strip (carried over from prior reviews; record only).
- <!-- HUMAN-REVIEW id="HR-004" category="design-rationale" severity="low" --> HR-004 — design-rationale — Commit `64740d0` edits this GEO task under a data-cleaning-scoped title (carried over from prior reviews; record only).

#### Tests run

- grader on reference: **1.0** (13/13 subchecks, weighted total 25/25) — re-run after each edit.
- broken-solution re-grade: `broken_wrong_crs` 0.56, `broken_no_coalition` 0.48, `broken_planar_buffer` 0.52 — `metadata.yaml` refreshed to match; `broken_wrong_crs` outside its expected range (HR-001).
- pytest (benchmark/eval): **pass** (41 passed).

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change this run

Per-task reasoned subcheck weights replace the blunt 05b389b / c749e57 "3x all
data-content subchecks" weighting. Weights now track how central each failure is
to what the task actually probes: the polar geodesic-buffer + correct-polar-CRS
skill is weighted highest, station-identification / water-attribution next, and
structural / cosmetic shape checks lowest. Grading-only change; no `task.json`
version bump (only `grade.py` weights, `metadata.yaml`, and this audit file).

### Weight changes (subcheck: old -> new)

| Subcheck | Old | New | Group |
|---|---|---|---|
| geodesic_buffer_check | 3.0 | 4.0 | central polar-geometry |
| buffer_area_reasonable | 3.0 | 4.0 | central polar-geometry |
| crs_is_3031 | 1.0 | 4.0 | central polar-geometry |
| sphere_coords_projected | 1.0 | 4.0 | central polar-geometry |
| station_count_tolerance | 3.0 | 2.0 | secondary (identification) |
| station_name_overlap | 3.0 | 2.0 | secondary (identification) |
| water_station_overlap | 3.0 | 2.0 | secondary (water attribution) |
| water_area_reasonable | 3.0 | 2.0 | secondary (water attribution) |
| coalition_exists | 1.0 | 1.0 | structural (unchanged) |
| water_output_present | 1.0 | 1.0 | structural (unchanged) |
| water_source_attribution | 1.0 | 1.0 | structural (unchanged) |
| min_station_count | 1.0 | 1.0 | structural (unchanged) |
| sphere_geometry_types | 1.0 | 1.0 | structural (unchanged) |

Total weight 25 -> 29. Reference still 1.0 (all 13 subchecks pass).

### Broken scores (before -> after)

| Broken | Before | After | Fails (new weights) | Severity note |
|---|---|---|---|---|
| broken_wrong_crs | 0.56 | 0.38 | buffer_area, crs_is_3031, water_area, geodesic_buffer, sphere_coords_projected | Most severe: wrong CRS breaks all geometry (areas + degree coords + CRS metadata). Now lowest. |
| broken_planar_buffer | 0.52 | 0.59 | buffer_area, water_station_overlap, water_area, geodesic_buffer | Core polar geodesic skill failed; CRS + station identity intact. Middle. |
| broken_no_coalition | 0.48 | 0.62 | station_count, station_name, coalition_exists, buffer_area, water_area | Polar geometry / CRS / geodesic correct; only identification + coalition slipped. Highest. |

Ordering is now sensible and monotone by central-skill severity:
**wrong_crs (0.38) < planar_buffer (0.59) < no_coalition (0.62)**. The wrong-CRS
case — the central geodesic/CRS gotcha — drops substantially from the previously
too-lenient 0.56; the planar-buffer geodesic failure also lands clearly in the
mid-range; the right-approach-wrong-station-set case sits highest. No
disjoint-failure inversion: pushing the geodesic family to 4.0 while easing the
identity checks to 2.0 keeps planar_buffer below no_coalition.

### Prior-run re-grade summary

Re-graded the current-version runs with outputs under final weights (old -> new):

| Run | Old | New | Note |
|---|---|---|---|
| run-20260608-074701Z (deepseek-v4-flash-detailed) | 0.40 | 0.59 | current; station over-collection, CRS+geodesic correct |
| run-20260609-084636Z (deepseek-v4-flash-basic) | 0.40 | 0.59 | current; same over-collection signature |
| run-20260529-0902Z (deepseek-v4-pro) | 1.00 | 1.00 | clean solution, unchanged |
| run-20260517-1254Z (claude-opus) | 1.00 | 1.00 | clean solution, unchanged |
| run-20260528-2332Z (claude-opus) | 0.90 | 0.93 | fails station_name_overlap only |
| run-20260517-1424Z (deepseek-v4-flash) | 0.90 | 0.93 | fails water_area_reasonable only |
| run-20260528-0113Z (claude-opus) | 0.90 | 0.93 | fails water_area_reasonable only |
| run-20260527-2016Z (claude-opus) | 0.80 | 0.86 | fails station_name + water_station overlap |
| run-20260528-1927Z (claude-opus, 47 stations) | 0.50 | 0.59 | over-fetch identification failure |

Notable shift: the two current deepseek runs rise 0.40 -> 0.59. This is intended:
their failures are station-identification (over-collection), not central-skill
failures — they produced correct EPSG:3031 geodesic-magnitude buffers — so under
the recalibrated weighting they should out-score the wrong-CRS broken (0.38),
which they now do. Clean solutions stay 1.0; single-subcheck slips stay near the
top (~0.93). No inversion against the broken set.

### Reasoning

The task's hidden gotcha (analyst_notes + README) is the polar geodesic buffer
and the matching polar projected CRS. Both the wrong-CRS and the planar-buffer
failures manifest through the same subcheck family: `geodesic_buffer_check`,
`buffer_area_reasonable`, plus (for wrong CRS) `crs_is_3031` and
`sphere_coords_projected`. The 05b389b/c749e57 blanket 3x weighting left
`crs_is_3031` and `sphere_coords_projected` at 1.0 — the two checks that most
directly detect the central gotcha — while triple-weighting station-identity
checks (`station_count_tolerance`, `station_name_overlap`, `water_station_overlap`)
that probe a secondary skill. That is precisely why wrong-CRS scored a too-lenient
0.56 (it kept the heavy identity checks). Raising the four central polar-geometry
checks to 4.0, easing the four identity/water-area checks to 2.0, and leaving
binary structural checks at 1.0 makes the score track error severity: getting the
polar geometry wrong now costs the most, and the broken ordering reflects which
brokens broke the central skill versus a secondary one.

### Threshold note (not changed)

No thresholds or check logic touched. One observation worth recording for a future
pass: `coalition_exists` is a binary presence check and `min_station_count` /
`sphere_geometry_types` are shape checks; they are intentionally left at 1.0. The
relatively narrow gap between planar_buffer (0.59) and no_coalition (0.62) is a
consequence of the wide L3 tolerances (which let no_coalition still pass several
checks despite halving the station set), not a weighting defect — the clear
separation that matters (wrong_crs sitting well below both) is achieved.

### Human-review items

- HR-001 (grader-miscalibration-suspected, `broken_wrong_crs` re-grade drift)
  **resolved and removed** from `status.json`: the wrong-CRS broken now scores
  0.38 under reasoned weights (down from the too-lenient 0.56), with a refreshed
  `expected_score_range` of [0.30, 0.45]. The central CRS gotcha is now weighted
  to drop the score substantially.
- HR-002, HR-003, HR-004 (all design-rationale) retained unchanged.

### Changes applied this run

- `grade.py`: subcheck `weight=` values only (table above). No logic / threshold /
  gate change.
- `metadata.yaml`: refreshed broken `measured_score` (0.56/0.48/0.52 ->
  0.38/0.62/0.59) and `expected_score_range`; added weight-arithmetic prose.
- `README.md`: no change needed (no stale score fractions present).

### Tests run

- grader on reference: **1.0** (13/13 subchecks, weighted total 29/29).
- broken-solution re-grade: `broken_wrong_crs` 0.38, `broken_planar_buffer` 0.59,
  `broken_no_coalition` 0.62 — monotone by central-skill severity; `metadata.yaml`
  refreshed to match.
- pytest: not run (orchestrator runs the suite).
