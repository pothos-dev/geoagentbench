# Implementation notes — crs-l3-tokyo-jgd-crossings

## Status
completed

## Summary
First L3 CRS-reprojection task: a live OSM Overpass fetch for Tokyo's 23 special wards and the drivable highway network in their bbox, full reproject -> crosses -> buffer -> intersect -> density -> reproject pipeline emitting a five-layer GPKG with mixed per-layer CRSes (four engineering layers in EPSG:6677, dashboard density layer in EPSG:4326). Three broken solutions cover gate-1 failure, full reprojection skip, and a density-metric bug, with measured scores at 0.00 / 0.46 / 0.85.

## Verification results
- Reference grader score: 1.00 (13/13 subchecks)
- Broken-solution scores:
  - wrong_format: 0.0000 (expected range [0.0, 0.0])
  - unprojected_pipeline: 0.4615 (expected range [0.35, 0.55])
  - wrong_density_metric: 0.8462 (expected range [0.75, 0.95])
- Second-run output match: differs-explained-by-drift. Two consecutive reference runs against live Overpass produce GPKG files that differ at the byte level (SQLite internal metadata) but agree on every per-feature geometry and attribute (counts, density values, top-N rankings all identical between runs that landed seconds apart). Realistic OSM drift over weeks/months would shift the highway count by ~1% and the crossing count by similar magnitude; the grader's +-15% tolerance windows absorb this.
- Library tests after task: pass (32/32)

## Failure-mode coverage
- Skipped reprojection / buffer in degrees: broken_unprojected_pipeline
- Wrong density metric (count not density): broken_wrong_density_metric
- Wrong output format: broken_wrong_format
- Density layer left in EPSG:6677: principled-reasoning (covered by `crs_match_ward_crossing_density_wgs84` + `density_layer_in_wgs84_envelope` subchecks)
- Buffer applied to highways instead of crossing points: principled-reasoning (covered by `crossing_count_within_tolerance` + `buffer_mean_area_is_planar_50m` subchecks)
- Wrong CRS metadata stamped without actual reprojection: principled-reasoning (covered by `wards_jgd_in_plane_ix_envelope` + `buffer_mean_area_is_planar_50m` subchecks)
- `intersects` instead of `crosses` predicate: principled-reasoning (covered by `crossing_count_within_tolerance`)

## Open issues
- [severity: low] — The reference filters the Overpass `highway=*` query to drivable + residential road classes (excludes footway/cycleway/path/service). The inventory row says `highway=*` without restriction. A literal-minded agent that fetches every highway tag may exceed Overpass' practical response time and either retry with a narrower filter (still grades well, since the count tolerance is +-15% and the dominant crossings are still drivable) or fail entirely. The README documents this; flagged here so the orchestrator can audit.
- [severity: low] — `gpd.unary_union` deprecation warning in `fetch_highways`; functional, but should migrate to `union_all()` in a future cleanup.
- [severity: low] — Agent submissions that use a different `quad_segs` value when buffering may shift the mean buffer area by a fraction of a percent; the +-30% band accommodates this.

## Suggested prompt changes
*(empty)*

## Inventory change proposals
*(empty)*

## Library extensions
*(empty — the task uses only existing primitives `count_within_tolerance` and `jaccard_similarity_set`; the per-ward Spearman rank correlation is a one-line pandas helper inlined in `grade.py` rather than added to the library because no peer task currently needs it)*

## Runtime
~25 minutes (most spent on Overpass response time and waiting for the multi-layer GPKG writes to complete).

---

# Evaluator review log

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
The original inventory row for `crs-l3-tokyo-jgd-crossings` (authoring/inventory.md L464–487) frames an L3 CRS-reprojection round-trip exercise over live OSM Overpass: fetch Tokyo's 23 special wards (`admin_level=7 boundary=administrative`) and the highway network in their bbox, reproject WGS84 → JGD2011 Plane IX (EPSG:6677) for honest metric work, identify highway×ward-boundary crossings, build planar 50 m buffers, intersect each buffer with the producing ward, aggregate per-ward density, then reproject the dashboard layer back to WGS84 — all emitted as a five-layer GPKG that mixes two CRSes in one container. The initial commit (09b975e9, 2026-05-08) shipped the reference, broken solutions (`wrong_format`, `unprojected_pipeline`, `wrong_density_metric`), and a 13-subcheck grader that pairs principled-bound coordinate-envelope checks (catching "stamped CRS but never reprojected") with drift-tolerant count windows and a Spearman rank floor on the density ranking.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 09b975e9 | initial-authoring | Initial task: task.json, grade.py (368 LOC, 13 subchecks), metadata.yaml, README, reference + 3 broken solutions | (initial) |
| 2026-05-08 | 001e459b | mixed (paths only) | Moved task tree under `benchmark/eval/tasks/` as part of authoring/eval subtree split | Commit msg: "split into authoring/ and eval/ subtrees" — repo reorg, no semantic change |
| 2026-05-13 | a3a8d535 | mixed (paths only) | Moved `benchmark/eval/tasks/` to `benchmark/tasks/` | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" — promotion to top-level, no semantic change |
| 2026-05-13 | 89150101 | docs-change | Added `image-prompt.md` | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda17 | docs-change | Added `image.webp` | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c653731 | docs-change | Regenerated card image | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c6 | docs-change | Regenerated card image | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | d5c283d5 | prompt-change | Trimmed redundant detail — stripped ward-bearing-layer column enumeration (kept output schema) | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-15 | 7ac5fbe1 | prompt-change | Restructured instruction into two paragraphs; reduced inline EPSG annotation on each layer to a single statement; dropped the prose "national grid" rationale clause | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-17 | b4583b4a | prompt-change | Removed all explicit `EPSG:6677` and `EPSG:4326` mentions from the instruction. Now phrased as "the region's standard metric coordinate system" and "geographic coordinates for web display". Also dropped per-layer geometry-type annotations (still in expected_outputs schema). | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae32 | mixed (paths only) | Folder reorg: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md; reference/{generate.py,outputs/} → reference/solution/; tests/ → reference/failures/; image.webp/prompt → assets/. grade.py & generators updated for paths only. | Commit msg: "Reorganize task folder layout" — repo-wide refactor, no semantic change |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit b4583b4a, class: prompt-change — stripped explicit EPSG codes from the instruction).

#### Runs considered
| Run | Adapter / Model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | google/gemma-4-26b-a4b-it | 2026-05-26T07:52Z | 0.0 | done — gate 2 fail (wards_jgd has 2 rows; expected 23) | current |
| run-20260517-1424Z | deepseek/deepseek-v4-flash | 2026-05-17T14:31Z | 0.0 | done — gate 1 fail (no output file produced; 452 s run) | current |
| run-20260517-1254Z | claude-opus-4-6 | 2026-05-17T12:57Z | 0.923 | done — 12/13 subchecks; failed `crossing_count_within_tolerance` (sub=7143 ref=5406, +32%) | current |
| run-20260517-0614Z | deepseek/deepseek-v4-flash | 2026-05-17T06:21Z | 0.846 | done | stale (pre-cutoff) |
| run-20260517-0304Z | deepseek/deepseek-v4-flash | 2026-05-17T03:12Z | 0.0 | done | stale |
| run-20260517-0134Z | claude-opus-4-6 | 2026-05-17T01:37Z | 0.923 | done | stale |
| run-20260516-2248Z | claude-opus-4-6 | 2026-05-16T22:51Z | 0.923 | done | stale |
| run-20260516-1130Z | claude-opus-4-6 | 2026-05-16T19:46Z | 0.769 | done | stale |
| run-20260516-0743Z | claude-opus-4-6 | 2026-05-16T07:46Z | 0.923 | done | stale |
| run-20260515-2053Z | claude-opus-4-6 | 2026-05-15T20:56Z | 0.923 | done | stale |
| run-20260515-0926Z | deepseek/deepseek-v4-flash | 2026-05-15T09:40Z | 0.846 | done | stale |
| run-20260515-0624Z | claude-opus-4-6 | 2026-05-15T06:27Z | 0.923 | done | stale |
| run-20260514-1554Z | claude-opus-4-6 | 2026-05-14T15:57Z | 0.846 | done | stale |
| run-20260514-1245Z | claude-opus-4-6 | 2026-05-14T12:48Z | 0.846 | done | stale |
| run-20260514-0946Z | claude-opus-4-6 | 2026-05-14T09:49Z | 0.846 | done | stale |

#### Verdict
**insufficient-evidence (leaning calibrated)**

Only one of the three `current` runs produced a complete output and scored 0.923 (Opus 4.6, missing only `crossing_count_within_tolerance` at +32% over the reference because the agent fetched a broader highway tag set than the reference). The other two `current` runs are model-side failures — gemma-4-26b-a4b-it only assembled 2 ward polygons of the required 23, and deepseek-v4-flash never produced any output file. Both failure modes are agent-engineering problems (Overpass query sizing, multi-layer GPKG handling), not task calibration issues. The stale runs (n=12) show a stable spread of 0.77–0.92 for capable agents on the pre-strip prompt, which is consistent with calibrated behaviour, but they cannot be used as evidence for the current (post-strip) prompt. Re-grading the canonical reference scores 13/13 = 1.0, broken solutions match their measured scores from `metadata.yaml` within the wide tolerances, and `pytest` reports 35/35 green.

#### Specific findings
- The single `current` capable-agent run (Opus, 0.923) failed only on `crossing_count_within_tolerance` because it queried a broader highway tag set than the reference's drivable-highway filter, yielding 7143 crossings vs 5406 reference (+32%, outside the ±15% window). This is a real signal — the count tolerance is also designed to catch the "intersects vs crosses" failure mode — and the open issue in the author block already calls this out as low-severity. Not a grader bug; not a prompt bug. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> The instruction now says "highway network" without restricting tag values, so a literal-minded agent that fetches *every* `highway=*` (footways/cycleways/paths/services) is technically conforming. The author block flags this as expected, and the +-15% tolerance plus rank-correlation grading absorbs most of it. Keeping as-is is defensible; widening to ±25% to absorb this realistic agent variance would also be defensible. Recommendation: leave alone until at least 2 capable post-cutoff runs are available; flag for human judgement.
- The 2026-05-17 prompt strip (commit b4583b4a) removed explicit EPSG:6677 and EPSG:4326 from the instruction. The strip is appropriate per `instruction-stripping-guide.md` (CRS choice is one of the things the task is meant to test). No `current` run hit a CRS-mismatch failure, so we have no calibration evidence that the strip introduced over-difficulty — only the gemma run which failed for an unrelated reason.
- All 13 subchecks of the grader passed on the freshly graded reference outputs (`reference/solution/outputs/`). The broken-solution `measured_score` values in `metadata.yaml` (0.0 / 0.4615 / 0.8462) are consistent with the design intent.
- Inventory row mostly aligns with current task; the inventory still lists `EPSG:6677` and `EPSG:4326` under CRS in/out, which is appropriate since the inventory is the design spec, not the agent-visible prompt.
- The task does not bundle inputs (live Overpass, as designed for L3). No `inputs/` directory, which is correct for this category.

### 3. Changes applied this run

#### Unilateral edits
*(none — the single full-completion `current` run scored 0.923 with one near-miss subcheck that has principled design justification; the other current runs are model-side failures; reference grades 13/13. Not enough current evidence to justify any unilateral tolerance change.)*

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — ±15% crossing-count tolerance may be tight for the post-strip instruction; consider widening to ±25% once more current-cutoff runs are observed.

#### Tests run
- grader on reference: 1.0 (13/13)
- pytest: pass (35/35)

## Evaluator review 2026-05-26 (re-run, new runs)  (evaluator-commit <pending>)

### 1. Design history

No design-affecting commits since the prior evaluator review. `git log` over the task tree shows exactly one new commit since that review — `4615e8cb` (2026-05-26T12:42:55Z, "Re-evaluate crs-l3-tokyo-jgd-crossings: insufficient-evidence (1 flag)") — which touched only `audit/AUTHORING_HISTORY.md`, `coverage.yaml`, and `audit/status.json` (class: `docs-change`, not design-affecting). The full change log from the prior review block stands unchanged; the design-affecting cutoff is still commit `b4583b4a` (2026-05-17T12:48:37+00:00, prompt-change — stripped explicit EPSG codes).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit b4583b4a, class: prompt-change). Unchanged from prior review.

#### Runs considered
Re-evaluation triggered by two fresh runs added for this task (one opus, one gemma). Both use the `basic` prompt variant. Updated current-run table:

| Run | Adapter / Model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-26T19:22Z | 0.0 | done — gate 1 fail (no GPKG produced; only solve.py; 205 s run) | current — model-side |
| run-20260526-1753Z | claude-opus-4-7 (basic) | 2026-05-26T17:54Z | null | failed — `claude exited with code 143` after 2600 s; no output | current — model-side |
| run-20260526-0748Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-26T07:52Z | 0.0 | done — gate 2 fail (wards_jgd has 2 rows; expected 23) | current — model-side |
| run-20260517-1424Z | deepseek/deepseek-v4-flash | 2026-05-17T14:31Z | 0.0 | done — gate 1 fail (no output file; 452 s run) | current — model-side |
| run-20260517-1254Z | claude-opus-4-6 | 2026-05-17T12:57Z | 0.923 | done — 12/13 subchecks; failed `crossing_count_within_tolerance` (sub=7143 ref=5406, +32%) | current |

Footnote — stale (pre-cutoff) runs unchanged from prior review: opus-4-6 and deepseek-v4-flash spread 0.77–0.92 over 2026-05-14…2026-05-17 morning, plus sonnet-4-6 / deepseek at 0.77–0.92 on 2026-05-12…13. Not evidence for the post-strip prompt.

#### Verdict
**insufficient-evidence (leaning calibrated)**

The three new/re-considered model failures add no new calibration signal. (a) opus-4-7 (run-1753Z) was killed with exit 143 after ~43 min and produced nothing — a model-side timeout, treated as model-side per orchestrator note, not a task problem. (b) gemma-4-26b (run-1922Z) gave up after ~3.5 min with no GPKG (gate-1 fail). (c) gemma-4-26b (run-0748Z) queried `area["name"="Tokyo"]` with `relation["admin_level"="8"]` — wrong admin level (Tokyo's 23 special wards are admin_level=7 per metadata) and a non-`name:en` area match — so it only assembled 2 ward polygons (gate-2 fail). All three are agent-engineering / domain-knowledge failures (Overpass query sizing, admin-level selection, multi-layer GPKG handling), not grader or instruction miscalibration. The only complete, scoring, capable-agent current run is still the single Opus 4.6 at 0.923 (run-1254Z). With exactly one full-completion current run, evidence remains insufficient to upgrade to a firm `calibrated`, but nothing in the new runs contradicts calibration. Reference re-grades 13/13 = 1.0; pytest 35/35 green.

#### Specific findings
- No grader bug. Both gemma failures are caught correctly by the gates (gate-1 "no GPKG" and gate-2 "wards != 23"), which is the intended behaviour. The gate-2 check for exactly 23 wards correctly rejects the agent that selected the wrong admin_level. This is the gate doing its job, not over-strictness.
- The opus-4-7 exit-143 timeout is a model/harness-side failure (the live Overpass fetch of ~85k highway segments plus the full pipeline is the agent's responsibility to size within the 1200 s deadline; the run actually ran ~2600 s before SIGTERM, suggesting harness-level kill). Not a task design problem; recorded in the runs table.
- HR-001 from the prior review (±15% crossing-count tolerance possibly tight for the post-strip "highway network" wording) still stands. The new current runs produced no completed output that exercised this subcheck, so there is still no additional evidence to resolve it either way. Re-flagging at the same severity. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Instruction says "highway network" without restricting OSM highway sub-tags; the one completed current run (Opus 4.6) fetched a broader tag set than the reference and overshot crossing count by +32%, just outside ±15%. Keeping as-is is defensible (agent must choose a realistic drivable filter); widening to ±25% is also defensible. Recommend leaving alone until ≥2 capable post-cutoff completed runs exist.
- coverage.yaml validated against the vocabulary; no changes needed (only timestamp refreshed).

### 3. Changes applied this run

#### Unilateral edits
*(none — no design-affecting change since prior review; the new runs are all model-side failures and add no calibration evidence; reference re-grades 13/13.)*

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — ±15% crossing-count tolerance may be tight for the post-strip instruction; reconsider once ≥2 capable post-cutoff completed runs exist.

#### Tests run
- grader on reference: 1.0 (13/13)
- pytest: pass (35/35)

## Evaluator review 2026-05-27  (evaluator-commit <pending>)

### 1. Design history

No design-affecting commits since the prior two evaluator reviews. `git log --follow` over the task tree shows only two commits after the 2026-05-26 reviews, both of which are evaluator-artefact-only (class: `docs-change`):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-26 | 4615e8cb | docs-change | Wrote first evaluator-review block + initial `coverage.yaml`/`status.json` | Commit msg: "Re-evaluate crs-l3-tokyo-jgd-crossings: insufficient-evidence (1 flag)" |
| 2026-05-26 | bcb984ae | docs-change | Appended second (re-run) evaluator-review block; refreshed `status.json`/`coverage.yaml` timestamp | Commit msg: "Re-evaluate crs-l3-tokyo-jgd-crossings: insufficient-evidence (1 flag)" |

`git show --stat` confirms each touched only `audit/AUTHORING_HISTORY.md`, `audit/status.json`, and `coverage.yaml`. The design-affecting cutoff is therefore still commit `b4583b4a` (2026-05-17T12:48:37+00:00, prompt-change — stripped explicit EPSG codes). The full change log from the first review block stands unchanged.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37+00:00 (commit b4583b4a, class: prompt-change). Unchanged from the prior two reviews.

#### Runs considered
No new runs since the 2026-05-26 reviews. `benchmark/eval/runs/*/crs-l3-tokyo-jgd-crossings/` enumerates 27 run dirs; the most recent is `run-20260526-1922Z` (already in the prior table). The current-run set is therefore identical to the second review block:

| Run | Adapter / Model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-26T19:22Z | 0.0 | done — gate 1 fail (no GPKG; 205 s run) | current — model-side |
| run-20260526-1753Z | claude-opus-4-7 (basic) | 2026-05-26T17:54Z | null | failed — `claude exited with code 143` after 2600 s; no output | current — model-side |
| run-20260526-0748Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-26T07:52Z | 0.0 | done — gate 2 fail (wards_jgd has 2 rows; expected 23) | current — model-side |
| run-20260517-1424Z | deepseek/deepseek-v4-flash | 2026-05-17T14:31Z | 0.0 | done — gate 1 fail (no output file; 452 s run) | current — model-side |
| run-20260517-1254Z | claude-opus-4-6 (basic) | 2026-05-17T12:57Z | 0.923 | done — 12/13 subchecks; failed `crossing_count_within_tolerance` (sub=7143 ref=5406, +32%) | current |

Footnote — stale (pre-cutoff) runs unchanged: opus-4-6 / deepseek-v4-flash spread 0.77–0.92 over 2026-05-14…2026-05-17 morning, plus sonnet-4-6 / deepseek at 0.77–0.92 on 2026-05-12…13. Not evidence for the post-strip prompt.

#### Verdict
**insufficient-evidence (leaning calibrated)**

Nothing changed since the prior review: no design-affecting commits, no new runs. The only complete, scoring, capable-agent current run remains the single Opus 4.6 at 0.923 (run-1254Z), which missed only `crossing_count_within_tolerance` (+32% over the reference because it fetched a broader highway tag set than the reference's drivable filter). The four other current runs are model-side failures (two gemma gate failures, one deepseek gate-1 no-output, one opus-4-7 exit-143 timeout) and carry no calibration signal. With exactly one full-completion capable current run, evidence is still insufficient to upgrade to a firm `calibrated`, but nothing contradicts calibration. Re-grading the canonical reference scores 13/13 = 1.0 (verified this run: `crossing_count` ref=5406, buffer mean area 7841.37 m² within the π·50² band, density Spearman=1.0, top-5 Jaccard=1.0). `pytest` reports 35/35 green.

#### Output-CRS and format consistency (Step 2c-CRS)
Verified the three-way agreement and the no-one-sided-reprojection rule:
- Reference GPKG: `wards_jgd`/`crossing_points`/`crossing_buffers_50m`/`buffer_ward_intersection` at EPSG:6677; `ward_crossing_density_wgs84` at EPSG:4326 — matches the README layer table and `expected_outputs[]` (headline `crs: EPSG:6677`, `geometry_type: Mixed`, single multi-layer GPKG). All three agree.
- The grader never reprojects only the submission to match the reference. The `buffer_mean_area_is_planar_50m` and `intersection_mean_area_below_buffer` subchecks reproject the *submission* to EPSG:6677 only as a fallback when its CRS is mis-stamped, and they compare against an **absolute** principled target (π·50² m²), not against a reprojected reference — so there is no silent papering-over of a contract mismatch. The density rank-correlation and top-5 subchecks compare scalar `crossings_per_km2` values, no geometry transform. No `prompt-grader-inconsistent` CRS finding.

#### Specific findings
- No grader bug; no prompt bug. The gates behave as designed (gate-1 "no GPKG", gate-2 "wards != 23" both fire correctly on the gemma runs). The Opus 4.6 0.923 near-miss is the intended discriminator behaviour, not over-strictness.
- HR-001 (carried from both prior reviews) still stands. No new completed current run exercised the `crossing_count_within_tolerance` subcheck, so there is still no additional evidence to resolve it either way. Re-flagging at the same severity. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> The post-strip instruction says "highway network" without restricting OSM highway sub-tags; the one completed current run (Opus 4.6) fetched a broader tag set than the reference's drivable filter and overshot crossing count by +32%, just outside the ±15% window. Keeping ±15% is defensible (the agent must choose a realistic drivable filter, and the tolerance also catches the "intersects vs crosses" failure mode); widening to ±25% to absorb realistic agent tag-set variance is also defensible. Recommend leaving alone until ≥2 capable post-cutoff completed runs exist.
- `coverage.yaml` re-validated slug-by-slug against `authoring/coverage-vocabulary.yaml`: every entry (operation_categories, geometric_ops, spatial_analysis_ops, formats, crs_variants, data_sources, data_quality_issues, geometry_types, osm_tag_families, regions, data_scale) is a verbatim vocabulary slug. No coverage-vocabulary gap. Only the `evaluator_run_at` timestamp refreshed this run.
- Inventory row (authoring/inventory.md L464–487) still aligns with the current task; it lists EPSG:6677/EPSG:4326 under CRS in/out, which is correct for the design spec even though those codes were stripped from the agent-visible prompt.

### 3. Changes applied this run

#### Unilateral edits
*(none — no design-affecting change and no new runs since the prior review; the single full-completion current run scored 0.923 with one principled near-miss subcheck; reference re-grades 13/13.)*

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — ±15% crossing-count tolerance may be tight for the post-strip "highway network" wording; reconsider once ≥2 capable post-cutoff completed runs exist.

#### Tests run
- grader on reference: 1.0 (13/13)
- pytest: pass (35/35)

## Evaluator review 2026-05-28  (evaluator-commit <pending>)

### 1. Design history

New design-affecting commit since the prior review. `git log --follow` over the task tree shows two new commits:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342be | mixed (repo-wide) | Removed unused `prompt_version: 2026-05-08-a` line from `metadata.yaml` as part of repo-wide cleanup; introduced `task.json.version` field (not added to this task's `task.json`). | Commit msg: "Add task content versioning; drop unused prompt_version" — non-design-affecting for this task (`metadata.yaml` `prompt_version` was inert; no tolerances or grader logic touched). |
| 2026-05-28 | 7c38b0b1 | prompt-change | Tightened `task.json.instruction` from "the highway network" to "the drivable road network (excluding service roads)"; updated metadata `notes` to record the rationale and the resolution of prior HR-001. | Commit msg: "Resolve crs-l3-tokyo-jgd-crossings HR-001 via 'drivable road network (excluding service roads)' prompt tightening" — explicitly resolves HR-001 from the three prior evaluator reviews. |

The full pre-existing change log from the first review block stands unchanged. The 7c38b0b prompt-change pins the OSM highway-tag slice (rules out footway/cycleway/path as "non-drivable" and service explicitly), targeting the reference filter that the ±15% count tolerance is calibrated against.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T12:36:01+00:00 (commit 7c38b0b1, class: prompt-change — tightened "highway network" → "drivable road network (excluding service roads)"). Supersedes the prior b4583b4a cutoff.

#### Runs considered

`benchmark/eval/runs/*/crs-l3-tokyo-jgd-crossings/` now enumerates 31 run dirs. Under the new cutoff, every existing run is `stale` — no completed run started after 2026-05-28T12:36:01Z. The four most recent post-prior-cutoff runs (run-20260527-2016Z … run-20260528-0317Z) were `current` under the prior review and are now `stale` because they ran against the pre-tightening prompt.

| Run | Adapter / Model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| (none) | — | — | — | — | no current runs against the new cutoff |

Footnote — stale runs (selection of the most recent, useful as historical context only; full list below):

| Run | Adapter / Model | Started | Score | Status |
|---|---|---|---|---|
| run-20260528-0317Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-28T03:19Z | 0.769 | done — 10/13 subchecks; failed `crossing_count_within_tolerance` (sub=32, ref=5406), `density_rank_correlation_with_reference` (0 matched wards), `top5_densest_wards_match` (Jaccard=0) |
| run-20260528-0113Z | claude-opus-4-7 (basic) | 2026-05-28T01:22Z | 0.769 | done — 10/13 subchecks; failed `crossing_count_within_tolerance` (sub=2267, ref=5406, −58%), `density_rank_correlation` (Spearman=0.776 < 0.8), `top5_densest_wards` (Jaccard=0.43) |
| run-20260527-2321Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-27T23:24Z | 0.615 | done — 8/13; agent stamped CRS metadata but produced geometries in EPSG:3857 / nonsense lon/lat — caught by envelope checks |
| run-20260527-2016Z | claude-opus-4-7 (basic) | 2026-05-27T20:24Z | 0.769 | done — 10/13; same failure mode as 0113Z (trunk-only filter, sub=2258, −58%) |
| run-20260526-1922Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-26T19:22Z | 0.0   | done — gate 1 fail (no GPKG) |
| run-20260526-1753Z | claude-opus-4-7 (basic) | 2026-05-26T17:54Z | null  | failed — exit 143 after 2600 s |
| run-20260526-0748Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-26T07:52Z | 0.0   | done — gate 2 fail (2 wards) |
| run-20260517-1424Z | deepseek/deepseek-v4-flash | 2026-05-17T14:31Z | 0.0   | done — gate 1 fail (no output) |
| run-20260517-1254Z | claude-opus-4-6 (basic) | 2026-05-17T12:57Z | 0.923 | done — 12/13; missed only `crossing_count_within_tolerance` (+32%, drivable+service) |

(Plus 12 pre-2026-05-14 stale runs at 0.77–0.92 from the first review block — recorded there, not repeated.)

#### Verdict
**insufficient-evidence**

No `current` runs exist against the new 2026-05-28T12:36:01Z cutoff (the prompt tightening that resolves prior HR-001). The most recent stale runs are useful for predicting how the tightening will land: two Opus 4.7 runs and one gemma run on the *pre-tightening* prompt all converged on a trunk-only highway slice (sub≈2258 / 2267 / 32 vs ref=5406, i.e. −58% / −58% / −99% on the count subcheck), confirming the design-history rationale that the pre-tightening prompt admitted three defensible slices and that the trunk-only edge was the modal weak-agent interpretation. Under the new "drivable road network (excluding service roads)" wording, an agent that still picks trunk-only is mis-reading the prompt (trunk-only is not "the drivable road network"). Whether the tightening is sufficient to drive capable agents onto the reference slice is the open question; only post-cutoff capable runs can settle it. Reference re-grades 13/13 = 1.0; pytest 41/41 green.

#### Output-CRS and format consistency (Step 2c-CRS)
Unchanged from prior review and re-verified:
- Reference GPKG layer CRSes (EPSG:6677 for the four engineering layers; EPSG:4326 for the density layer) match the README layer table and `expected_outputs[]` (headline `crs: EPSG:6677`, `geometry_type: Mixed`, single multi-layer GPKG). Three-way agreement holds.
- The grader does not reproject only the submission to match the reference. The `buffer_mean_area_is_planar_50m` and `intersection_mean_area_below_buffer` subchecks reproject the submission to EPSG:6677 only as a fallback when the layer CRS is mis-stamped, and compare against an absolute principled target (π·50² m²), not against the reference. The density rank-correlation and top-5 subchecks compare scalar `crossings_per_km2` values without geometry transforms. No `prompt-grader-inconsistent` CRS finding.

#### Specific findings
- No grader bug; no prompt bug. The pattern across stale recent runs (Opus 4.7 settling on trunk-only, gemma producing nonsense CRS metadata, agents missing the wgs84-vs-jgd round-trip nuance) is exactly what the grader is designed to discriminate. The 7c38b0b prompt tightening directly addresses the HR-001 concern from the prior three reviews; whether it actually drives capable agents onto the reference slice will be visible in the next post-cutoff sweep.
- HR-001 (carried across three prior reviews — "±15% crossing-count tolerance possibly tight for the post-strip 'highway network' wording") is now **resolved upstream** by commit 7c38b0b. Not re-flagging.
- `task.json` has no `version` field. Per the new versioning rules introduced in commit 622342be, an evaluator that meaningfully changes `task.json.instruction` must bump `version` (implicit `1` → explicit `2`). The HR-001 resolution commit 7c38b0b made a meaningful prompt change but did not add `version: 2`. This is a single-line oversight in an external commit; I am not making any unilateral edit to prompt/grader/inputs in this evaluator pass, so I do not apply the bump here. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Decide whether the version bump from `1` (implicit) → `2` (explicit) should be retroactively added to `task.json` to reflect the 2026-05-28 prompt tightening, so that all prior runs are correctly flagged outdated in the UI. The cleanest fix is a one-line `"version": 2,` addition just below `"task_id"` in `task.json`; no semantic change. Low severity because the UI fallback (no `version` ⇒ v1 ⇒ runs without `task_version` are already shown outdated) gives the right visual outcome today.
- `coverage.yaml` re-validated slug-by-slug against `authoring/coverage-vocabulary.yaml`: every entry is a verbatim vocabulary slug. No coverage-vocabulary gap. Only the `evaluator_run_at` timestamp refreshed this run.
- Inventory row (authoring/inventory.md L464–487) still aligns with the current task. The inventory's CRS in/out lists EPSG:6677 / EPSG:4326 (design spec — correct even though the agent-visible prompt has them stripped) and its highway-tag note matches the new "drivable + minor" reference slice.

### 3. Changes applied this run

#### Unilateral edits
*(none — the HR-001 from the three prior reviews was resolved upstream by commit 7c38b0b before this evaluator pass; reference re-grades 13/13; no current runs to motivate any further tolerance or prompt edit.)*

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — `task.json` is missing an explicit `version: 2` after the 2026-05-28 prompt tightening; one-line retroactive bump suggested.

#### Tests run
- grader on reference: 1.0 (13/13)
- pytest: pass (41/41)

## Evaluator review 2026-06-06  (evaluator-commit <pending>)

### 1. Design history

No design-affecting commits since the prior review. `git log` over the task tree shows no new commits at all since the prior evaluator review block (commit `3ec90b20`, 2026-05-28T13:27:33Z). The design-affecting cutoff therefore remains commit `7c38b0b1` (2026-05-28T12:36:01+00:00, prompt-change — "drivable road network (excluding service roads)" tightening).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T12:36:01+00:00 (commit 7c38b0b1, class: prompt-change). Unchanged from the prior review.

#### Runs considered
`benchmark/eval/runs/*/crs-l3-tokyo-jgd-crossings/` now enumerates several runs started after the new cutoff. The prior review noted "no current runs against the new cutoff"; that gap is now closed.

| Run | Adapter / Model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1334Z | google/gemma-4-26b-a4b-it (gis_detailed) | 2026-06-06T13:43Z | null | cancelled — no score | current — model-side |
| run-20260606-1129Z | google/gemma-4-26b-a4b-it (gis_detailed) | 2026-06-06T11:36Z | 0.0 | done — gate 1 fail (no GPKG produced) | current — model-side |
| run-20260606-0953Z | google/gemma-4-26b-a4b-it (gis_detailed) | 2026-06-06T09:53Z | null | failed — max iterations exceeded (50) | current — model-side |
| run-20260529-0902Z | deepseek/deepseek-v4-pro (basic) | 2026-05-29T09:13Z | 1.0 | done — 13/13 | current |
| run-20260529-0109Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-29T01:12Z | 0.0 | done — gate 1 fail (no GPKG produced) | current — model-side |
| run-20260528-2332Z | opus (claude-opus-4-7, basic) | 2026-05-28T23:36Z | 1.0 | done — 13/13 | current |
| run-20260528-2225Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-28T22:27Z | 0.0 | done — gate 2 fail (wards_jgd has 2 rows; expected 23) | current — model-side |
| run-20260528-1927Z | opus (claude-opus-4-7, basic) | 2026-05-28T19:31Z | 1.0 | done — 13/13 | current |
| run-20260528-1624Z | google/gemma-4-26b-a4b-it (basic) | 2026-05-28T16:28Z | 0.615 | done — 8/13 (CRS metadata stamped without reproject; wards bounds in EPSG:3857-shaped numbers, density layer in lat≈36 N belt — caught by both envelope checks; count subcheck sub=46 vs ref=5406; rank/top-5 fail on 0 matched wards) | current |

Footnote — stale (pre-cutoff) runs unchanged from prior reviews. Most-recent stale runs all clustered around 0.769 (10/13) on the pre-tightening prompt, missing `crossing_count_within_tolerance` due to the open-ended "highway network" wording — which is the failure mode commit 7c38b0b1 was authored to resolve.

#### Verdict
**calibrated**

Three current capable-agent runs completed end-to-end and all scored 1.0 (opus 4.7 twice on 2026-05-28, deepseek-v4-pro once on 2026-05-29). The prompt tightening introduced in commit 7c38b0b1 successfully landed: under the previous wording, capable agents clustered at 0.769 because they picked a defensible-but-non-reference highway slice that the ±15% count tolerance could not absorb; under the new "drivable road network (excluding service roads)" wording, the same model family lands on the reference slice and scores full marks. The five gemma current runs are all model-side failures (gate-1 no-output, gate-2 two-ward, max-iterations, or cancelled) and add no calibration signal beyond confirming that the gates fire correctly on weak-agent failure modes. The one current sub-1.0 completed run (gemma 0.615) was caught by the envelope subchecks for stamping CRS metadata without reprojecting — exactly the intended discriminator behaviour. Reference re-grades 13/13 = 1.0; pytest 41/41 green.

Risk that the three full-marks runs reflect *over*-easiness: low. The instruction still strips the explicit EPSG codes (the agent must infer that JGD2011 Plane IX is "the region's standard metric coordinate system"), it does not name the spatial predicate (must pick `crosses`, not `intersects`), it does not name the geometric operation order (must reproject before buffering), and it requires writing a five-layer GPKG with mixed per-layer CRSes. Capable agents (opus 4.7, deepseek-v4-pro) cleared all those tests on three independent runs; weak/mid-tier agents (gemma 4-26b) did not. That is exactly the calibration shape expected of an L3 task.

#### Output-CRS and format consistency (Step 2c-CRS)
Unchanged from prior review and re-verified:
- Reference GPKG: `wards_jgd`/`crossing_points`/`crossing_buffers_50m`/`buffer_ward_intersection` at EPSG:6677; `ward_crossing_density_wgs84` at EPSG:4326 — matches the README layer table and `expected_outputs[]` (headline `crs: EPSG:6677`, `geometry_type: Mixed`, single multi-layer GPKG). Three-way agreement.
- The grader never reprojects only the submission to match the reference. Buffer/intersection area subchecks reproject the submission to EPSG:6677 only as a fallback when its CRS metadata is mis-stamped, and they compare against an absolute principled target (π·50² m²), not against the reference. The density rank-correlation and top-5 subchecks compare scalar `crossings_per_km2` values without any geometry transform. No `prompt-grader-inconsistent` finding.

#### Specific findings
- HR-001 from the prior review (retroactive `task.json.version` bump after the 2026-05-28 prompt tightening) — **resolved this run** by adding `version: 2` to `task.json` directly under `task_id`. This is a one-line metadata fix with no semantic effect on what the agent sees or how it is scored; it brings the task into compliance with the versioning rule that any meaningful instruction edit must bump `version`. Per the evaluator prompt's bump-required list, the bump is technically demanded by the prior commit 7c38b0b1 (instruction edit) that never carried it; applying it here makes the UI flag all pre-tightening runs as outdated.
- `analyst_notes` was missing from `task.json`. Authored this run per the Step 4 schema; covers the hidden gotcha (planar buffers must run in the projected frame, not after a `set_crs`), the canonical Tokyo-specific pitfalls (admin_level=7 vs 8, name vs name:en, the highway tag-slice that drives the ±15% count tolerance), and the dashboard-layer round-trip back to WGS84. Not a `version` bump trigger (the field is human-facing only).
- `coverage.yaml` re-validated slug-by-slug against `authoring/coverage-vocabulary.yaml`: every entry remains a verbatim vocabulary slug. The vocabulary has no slug for "non-Latin script" so the kanji ward names are not represented under `data_quality_issues`, which is consistent with the prior review's choice; the regional anchor for non-Latin script is captured by `regions: [tokyo]`. Only the `evaluator_run_at` timestamp was refreshed.
- Inventory row (authoring/inventory.md L464–487) still aligns. CRS in/out lists EPSG:6677/EPSG:4326 (correct for the design spec, even though the agent-visible prompt has them stripped) and the highway-tag note matches the post-tightening reference slice.
- No grader bug; no prompt bug. Three capable current runs at 1.0, one sub-1.0 current run that hit the intended envelope discriminators, and five model-side current failures correctly bounced by the gates.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `"version": 2` directly under `task_id`, retroactively recording that the 2026-05-28 prompt tightening (commit 7c38b0b1) changed the agent-visible instruction. Re-grade on reference: 1.0 (13/13). Reason: resolve prior HR-001 (design-rationale, low) by aligning `task.json` with the versioning rule; UI now correctly flags pre-tightening runs as outdated.
- `task.json`: authored `analyst_notes` (`description`, `approach` with six steps, `pitfalls` with eight entries). Re-grade on reference: 1.0 (13/13). Reason: Step 4 mandates authoring `analyst_notes` when the field is missing; surfaced in the eval UI as a reviewer's note alongside the prompt. Not seen by the agent at run time; no `version` bump required for this edit.

#### Proposed but not applied (see HUMAN-REVIEW items)
*(none)*

#### Tests run
- grader on reference: 1.0 (13/13)
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
- Ward-count-exactly-23 check migrated from Gate 2 to a new
  `wards_jgd_row_count_is_23` subcheck.
- Subcheck count grew from 13 to 14.

### Verification
- Reference solution re-graded: 1.0 (14/14 subchecks).

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the first review block: an L3 CRS round-trip exercise over live Overpass data (Tokyo's 23 special wards + drivable highway network, WGS84 -> EPSG:6677 -> analysis -> EPSG:4326 dashboard layer, five-layer mixed-CRS GPKG). See the 2026-05-26 block for the full reconstruction.

#### Change log (commits since the prior review block, commit ef8f4b25)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 6a7113d6 | mixed (paths/slug only) | Renamed task dir and every internal reference from `crs-l3-tokyo-jgd-densification` to `crs-l3-tokyo-jgd-crossings`; also updated inventory.md and two cross-referencing audit logs. No prompt/grader/data semantics changed. | Commit msg: slug was a misnomer ("nothing is actually densified"); new name reflects the primary spatial op. |
| 2026-06-06 | 0feef95e | prompt-change | House-style rewrite of `task.json.instruction` (persona opener, bulleted layer list, no em-dashes; CRS hint level unchanged, still no EPSG named); `analyst_notes` refreshed to name EPSG:6677 for human reviewers; `version` 2 -> 3. | Commit msg: applied house style; deliberate CRS omission preserved; version bumped per the instruction-edit rule. |
| 2026-06-06 | 363aed21 | grader-change | Dropped the `structural_correctness` gate; ward-count-exactly-23 migrated to subcheck `wards_jgd_row_count_is_23`; subcheck count 13 -> 14. | Commit msg: benchmark-wide refactor — one hard gate, salvageable checks become subchecks. |
| 2026-06-07 | 05b389bc | grader-change | Re-tagged five data-content subchecks (`crossing_count_within_tolerance`, `buffer_mean_area_is_planar_50m`, `intersection_mean_area_below_buffer`, `density_rank_correlation_with_reference`, `top5_densest_wards_match`) with `weight=3.0`; total weight now 24 (9x1 + 5x3). | Commit msg: clean-schema-wrong-data submissions should score visibly lower than correct-data slightly-off-schema ones. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:28:18+00:00 (commit 05b389bc, class: grader-change — 3x weighting of data-content subchecks). Supersedes the prior 7c38b0b1 cutoff.

#### Runs considered
`benchmark/eval/runs/*/crs-l3-tokyo-jgd-crossings/` enumerates 45 run dirs (the rename also moved the old-slug run dirs under the new slug). Runs started after the cutoff:

| Run | Adapter / Model | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | deepseek/deepseek-v4-flash (basic) | 2026-06-09T08:59Z | null | failed — max iterations exceeded (75); gate-1 fail on the empty outputs | current — model-side |
| run-20260608-074701Z | deepseek/deepseek-v4-flash (gis_detailed) | 2026-06-08T08:08Z | 0.875 | done — 13/14 subchecks; failed only `crossing_count_within_tolerance` (sub=8067 ref=5406, +49%, w=3) | current |
| run-20260607-112430Z | google/gemma-4-26b-a4b-it (gis_detailed) | 2026-06-07T12:04Z | 0.625 | done — failed `crossing_count_within_tolerance` (sub=2), `density_rank_correlation` (0 matched wards), `top5` (0.0) | stale by timestamp (pre-18:28Z); task_version 3; score.json reflects the weighted grader (re-graded post-hoc) |
| run-20260606-1733Z | google/gemma-4-26b-a4b-it (gis_detailed) | 2026-06-06T17:41Z | 0.385 | done | stale (task_version 2, pre-rewrite) |

Footnote — all 41 older runs are stale (task_version <= 2 and/or pre-cutoff); their analysis is recorded in the 2026-05-26/27/28 and 2026-06-06 review blocks and is not repeated here. The version-2 era ended with three capable-agent runs at 1.0 (opus-4-7 x2, deepseek-v4-pro x1) after the 2026-05-28 "drivable road network" tightening.

#### Verdict
**insufficient-evidence (leaning calibrated)**

Only two runs postdate the 05b389bc weighting commit and both come from the same agent family (deepseek-v4-flash), which by rule caps the verdict at insufficient-evidence. Nothing in them contradicts calibration. The completed run (0.875) produced a structurally perfect five-layer GPKG with correct per-layer CRSes, honest 50 m planar buffers (mean area 7841 m²), Spearman 0.96 on density and 2-of-3 top-5 overlap, and lost only the 3x-weighted crossing-count subcheck at +49% over the reference (8067 vs 5406) — an over-broad highway slice despite the prompt's "drivable... skip service roads", i.e. the discriminator working as intended, not over-strictness (+49% is far outside any defensible tolerance widening). The failed 06-09 run is a model-side max-iterations failure. The two grader changes since the last review redistribute weight but do not change the answer key; the reference still grades 1.0 (14/14) and both broken sets re-measure inside their expected ranges under the new weighting (unprojected 0.5417 in [0.35, 0.55]; wrong_density 0.75 in [0.75, 0.95]).

#### Output-CRS and format consistency (Step 2c-CRS)
Re-verified post-rewrite: reference GPKG layer CRSes (EPSG:6677 x4, EPSG:4326 for the density layer) match the README layer table and `expected_outputs[]` (headline `crs: EPSG:6677`, `geometry_type: Mixed`). The grader's only submission-side reprojection is the documented fallback in the buffer/intersection area subchecks (mis-stamped CRS metadata), compared against the absolute pi*50^2 target, not the reference. No one-sided papering-over. The instruction's "regional metric coordinate system" phrasing admits alternatives in principle, but the grader does **not** Gate-1-reject a non-canonical pick: a defensible JGD2011 UTM 54N submission would lose the four CRS subchecks plus the envelope check (scoring ~19/24 = 0.79), and a JGD2000 Plane IX pick only the CRS subchecks (~20/24 = 0.83) — graded degradation consistent with the accept-list policy's intent, so no Step-4 refactor is needed.

#### Prompt information audit (Step 2c-INFO)
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| single GPKG `tokyo_crossings.gpkg`, five named layers (gate) | instruction, bulleted list | stated |
| wards_jgd has exactly 23 rows | instruction ("the 23 ward boundaries") | stated |
| engineering layers in EPSG:6677 + JGD envelope | "the regional metric coordinate system" | inferable (deliberate omission — the test itself) |
| density layer in EPSG:4326 + WGS84 envelope | instruction ("it goes in WGS84") | stated |
| crossing count within ±15% of reference | "drivable road network... skip service roads" pins the tag slice; tolerance is grader-internal | inferable (standard drift margin given the pinned slice) |
| buffer mean area ~ pi*50^2 | instruction ("a 50 m buffer") | stated |
| intersection mean area <= buffer area | instruction ("clipped to the ward") | stated |
| `ward_id`, `crossing_count`, `crossings_per_km2` columns on density layer | instruction | stated |
| density rank correlation / top-5 vs reference | correct arithmetic | inferable |

Factual claims verified: layer names match grader `LAYERS`; density columns match the reference schema; `ward_id` = OSM relation id matches the reference; "23 special wards" is true of OSM admin_level=7 in Tokyo. One leniency noted: the prompt requires `ward_area_km2` on the density layer but the grader never checks that column — harmless over-asking on the prompt side, not a missing-information defect.

#### Reference faithfulness (Step 2c-REF)
One deviation found. The instruction (current and all prior wordings) asks to "carry the English and native ward names as `ward_name_en` and `ward_name` on every layer that's tied to a specific ward", but `reference/solution/generate.py` carries only `ward_name_en` on `crossing_points`, `crossing_buffers_50m`, and `buffer_ward_intersection` (the native `ward_name` appears only on `wards_jgd` and the density layer; README layer table documents the reference behaviour, contradicting the prompt). The 06-08 deepseek submission followed the prompt and carried `ward_name` on all five layers; the grader checks none of these columns, so no run has ever been scored on the discrepancy.
<!-- HUMAN-REVIEW id="HR-001" category="reference-prompt-mismatch" severity="med" -->
The reference skips a requested attribute: `ward_name` is missing from the three crossing-derived layers although the instruction requires both name columns on every ward-tied layer. Two possible fixes: (a) regenerate the reference carrying `ward_name` on `crossing_points` / `crossing_buffers_50m` / `buffer_ward_intersection` and update the README schema table, or (b) reword the instruction to require the two name columns only on the wards and density layers. Whoever applies fix (a) must regenerate `reference/solution/outputs/`, re-check the broken sets' measured scores, and bump `version`; fix (b) is an instruction edit and also requires a `version` bump. No grader change is needed under either fix (the grader does not check these columns).

#### Specific findings
- `metadata.yaml > broken_solutions > measured_score` was stale after the two grader changes: re-measured this run as wrong_format 0.0 (unchanged), unprojected_pipeline 0.4615 -> 0.5417, wrong_density_metric 0.8462 -> 0.75. Both remain inside their `expected_score_range`; the wrong_density score now sits exactly on the range's lower bound, which is worth watching if weights shift again. Updated unilaterally with descriptions adjusted to the weighted arithmetic.
- `analyst_notes.description` claimed the grader "Gate-1-rejects any other choice" of CRS — never literally true and doubly wrong after the Gate-2 drop (CRS mismatches cost subchecks). Pitfall 8 referenced the removed "structural gate". Both refreshed unilaterally (human-facing field, no version bump).
- README's "Expected weak-agent failure mode" still claimed "the persona's prompt names the target CRS twice" — stale since the 2026-05-17 EPSG strip (b4583b4a) and missed by prior reviews. Fixed unilaterally (docs-change).
- Inventory row (authoring/inventory.md L464-487) was renamed in 6a7113d6 and still matches the design; its `highway=*` OSM-tag shorthand vs the reference's drivable slice remains the known low-severity looseness recorded in the author block since authoring. Not re-flagged (design-spec level, documented in metadata notes).
- `coverage.yaml` re-validated slug-by-slug against `authoring/coverage-vocabulary.yaml`: all slugs verbatim. The kanji ward names still have no data-quality slug (the thesis `<data-quality-table>` has no non-Latin-script row either, so the vocabulary is not missing a thesis variant — no gap to flag, consistent with prior reviews). Timestamp refreshed only.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions.*.measured_score` to the current weighted grader (0.0 / 0.5417 / 0.75), adjusted the two stale subcheck-count descriptions, and added a re-measurement note. Re-grade on reference: 1.0. Reason: scores were measured under the pre-2026-06-06 equal-weight 13-subcheck grader.
- `task.json` (`analyst_notes` only): corrected the "Gate-1-rejects" claim to the per-layer CRS + envelope subcheck reality and replaced the "structural gate" pitfall reference with the ward-count subcheck. Re-grade on reference: 1.0. Reason: keep the human-facing notes accurate after the Gate-2 removal; no version bump required for `analyst_notes`.
- `README.md`: fixed the stale "prompt names the target CRS twice" sentence to reflect the post-strip prompt. Re-grade on reference: 1.0. Reason: README contradicted the agent-visible instruction.
- `coverage.yaml`: timestamp refresh only.

No `version` bump: none of the edits touch the instruction, grader logic, tolerances, or inputs (measured_score refreshes, `analyst_notes`, and README edits are all in the no-bump list).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-prompt-mismatch — reference omits the requested `ward_name` column on the three crossing-derived layers; fix via reference regeneration or instruction reword, either way with a `version` bump.

#### Tests run
- grader on reference: 1.0 (14/14, weighted 24/24)
- broken sets: wrong_format 0.0, unprojected_pipeline 0.5417, wrong_density_metric 0.75 — all within expected ranges
- pytest: pass (41/41)

## Evaluator review 2026-06-14 — subcheck reweighting  (evaluator-commit <pending>)

### Change
Replaced the blunt repo-wide 2026-06-07 weighting (commit 05b389b, which
slapped `weight=3.0` on five "data-content" subchecks and left everything
else at 1.0, total 24) with per-task weights reasoned from what this task
actually tests. Grading-only change: only `weight=` values in `grade.py`
were touched — no check logic, thresholds, or gates changed.

#### What the task tests, and how weight follows
This is a CRS-L3 round-trip task. Two things are central: (1) that the
WGS84 -> JGD2011 Plane IX reprojection **actually happened** (not merely
that the right EPSG label was stamped), and (2) the spatial computation
(crosses-count, planar buffering, per-ward density metric). The weighting
makes the proof-of-reprojection checks (coordinate-envelope, planar
buffer area, intersection ceiling) and the central spatial signals heavy,
and pushes the five `crs_match_*` **metadata-label** subchecks down to
0.25: a file that declares EPSG:6677 but never transformed its
coordinates must not out-leverage the checks that prove transformation.

#### Weight changes (subcheck: old -> new)
| Subcheck | old | new |
|---|---|---|
| crs_match_wards_jgd | 1.0 | 0.25 |
| crs_match_crossing_points | 1.0 | 0.25 |
| crs_match_crossing_buffers_50m | 1.0 | 0.25 |
| crs_match_buffer_ward_intersection | 1.0 | 0.25 |
| crs_match_ward_crossing_density_wgs84 | 1.0 | 0.25 |
| wards_jgd_in_plane_ix_envelope | 1.0 | 3.0 |
| density_layer_in_wgs84_envelope | 1.0 | 2.0 |
| intersection_mean_area_below_buffer | 3.0 | 2.0 |
| top5_densest_wards_match | 3.0 | 1.5 |
| (unchanged) crossing_count_within_tolerance | 3.0 | 3.0 |
| (unchanged) buffer_mean_area_is_planar_50m | 3.0 | 3.0 |
| (unchanged) density_rank_correlation_with_reference | 3.0 | 3.0 |
| (unchanged) wards_jgd_row_count_is_23 | 1.0 | 1.0 |
| (unchanged) density_layer_has_crossings_per_km2 | 1.0 | 1.0 |

Total weight: 24 -> 20.75.

#### Broken / canonical scores (before -> after)
| Class | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | gate fail (wrong container) — floor, unchanged |
| unprojected_pipeline | 0.5417 | 0.5663 | most-severe completed broken: never reprojected, the headline CRS failure; loses both proof-of-reprojection blocks |
| wrong_density_metric | 0.75 | 0.7831 | mild: engineering layers all correct, only the dashboard density column mis-computed |
| reference | 1.0 | 1.0 | all pass |

Ordering is now sensible and monotone in severity:
`wrong_format 0.0 < unprojected 0.5663 < wrong_density 0.7831 < reference 1.0`.
The honestly-unprojected file sits well below the file that only fumbles
the density metric, which is the intended severity gradient.

#### Prior-run re-grade summary (task_version 3 runs)
| Run | Model | old -> new | fails |
|---|---|---|---|
| run-20260607-112430Z | gemma-4-26b-a4b-it | 0.625 -> 0.6386 | crossing-count, density-rank, top5 |
| run-20260608-074701Z | deepseek-v4-flash | 0.875 -> 0.8554 | crossing-count only (+49% over-broad slice) |
| run-20260609-084636Z | deepseek-v4-flash | 0.0 -> 0.0 | gate fail (max-iterations, empty outputs) |

No significant shifts (all within ~0.02 of the old equal-vs-3x scores).
The 0.625 run (multiple central failures) still scores below the 0.875
run (single near-miss), preserving the existing capable-vs-weak ordering.
These three are the version-3 runs; the 06-11 review block lists
run-0608 and run-0609 as `current` (run-0607 is stale-by-timestamp but
version 3).

### Reasoning notes / flags
- **Structural limit on the metadata-liar principle (NOTE, not fixed —
  would require check-logic change, out of scope).** A hypothetical file
  that stamps EPSG:6677 metadata but leaves coordinates in lon/lat passes
  all five `crs_match_*` labels yet fails the three proof checks (wards
  envelope, buffer area, intersection). The honestly-unprojected file
  fails those same three proof checks *plus* the four engineering
  `crs_match_*` labels (it left CRS=4326). So the liar will always score
  exactly `4 * 0.25 / 20.75 ≈ 0.048` above the honest file under any
  positive crs_match weight, because no subcheck exists that the liar
  fails but the honest file passes. Driving crs_match to 0.25 shrinks
  that gap to ~0.048 (within the task's own drift tolerance) without
  zeroing the legitimately-useful `crs_match_ward_crossing_density_wgs84`
  check (failure mode #4, "forgot to reproject dashboard back to WGS84").
  Fully eliminating the gap would need a new check that compares declared
  CRS against the coordinate envelope per layer — a logic change, not a
  weight change — so it is flagged here rather than applied.
- crossing_count, buffer-area, and density-rank-correlation kept at 3.0:
  these are the highest-leverage discriminators (the crosses computation,
  the planar-buffering gotcha, and the density-metric correctness). top-5
  dropped to 1.5 because it is corroborating evidence for the same
  density-metric failure that density-rank already catches at 3.0 —
  keeping both at 3.0 double-counted one failure mode.
- HR-001 (reference-prompt-mismatch, `ward_name` missing on three
  crossing-derived layers) is unrelated to weighting and is left intact.

### Changes applied this run
#### Unilateral edits
- `grade.py`: subcheck `weight=` values only (table above).
- `metadata.yaml`: refreshed `broken_solutions.*.measured_score` and
  `expected_score_range`, rewrote the weight-arithmetic prose in the
  descriptions and notes.
- `audit/status.json`: removed the grader-miscalibration-suspected HR
  about the 3x content weighting (if present); kept HR-001.

#### Tests run
- grader on reference: 1.0 (14/14, weighted 20.75/20.75)
- broken sets: wrong_format 0.0, unprojected_pipeline 0.5663,
  wrong_density_metric 0.7831 — all within refreshed expected ranges
- pytest: not run (orchestrator runs the suite)

---

## HR-001 resolution 2026-06-14 — `ward_name` added to crossing-derived layers

**Item:** HR-001 (reference-prompt-mismatch, med). The instruction requires
both `ward_name_en` and `ward_name` on *every* layer tied to a specific ward,
but the reference carried only `ward_name_en` on `crossing_points`,
`crossing_buffers_50m`, and `buffer_ward_intersection` (README documented that
narrower behaviour; the grader checks neither name column, so no run was
mis-scored).

**Decision (operator):** regenerate the reference to match the instruction
rather than narrow the prompt — `ward_name` now ships on all five ward-tied
layers.

**How applied without a live re-fetch:** `reference/solution/generate.py`
live-fetches Overpass, so re-running it months on would drift the ~5400
crossing counts and invalidate the broken `measured_score` calibration. Instead
the committed `outputs/tokyo_crossings.gpkg` was patched in place — `ward_name`
joined from `wards_jgd` by `ward_id` onto the three engineering layers
(inserted right after `ward_name_en`), every geometry and row count preserved
(5406 crossings / 23 wards). `generate.py` was edited to emit the column too,
so any future clean regen reproduces the patched schema.

**Files touched:** `reference/solution/generate.py` (compute_crossings +
buffer_ward_intersection row dicts), `reference/solution/outputs/tokyo_crossings.gpkg`
(patched in place), `README.md` (crossing_points schema row),
`task.json` (version 3 -> 4), `audit/status.json` (HR-001 dropped).

**Verification:** self-grade of the patched reference = 1.0, 14/14 subchecks.
Broken `measured_score` values unchanged (grader does not weight name columns).
Visualizations (`*.pmtiles`) not regenerated — geometry unchanged, attribute-only edit.
