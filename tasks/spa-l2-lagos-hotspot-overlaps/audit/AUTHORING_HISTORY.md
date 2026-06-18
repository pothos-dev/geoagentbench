# Implementation notes — spa-l2-lagos-hotspot-overlaps

## Status
completed

## Summary
L2 spatial-analysis task: per-hex area-weighted mean of `pop_density`
over overlapping land-use polygons after filtering sub-100 m² slivers,
top 10% ranked, emitted as both GeoParquet (geometry) and Parquet
(table). Bundled inputs slice Overture `base.land_use` over Lagos plus
3 000 seeded synthetic slivers + a 1 km hex grid in EPSG:26331.
Reference grader scores 1.0 on its own outputs and 0.0 / 0.5 / 0.83 on
three distinct broken classes.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.0 (expected range [0.0, 0.0])
  - no_sliver_filter: 0.5 (expected range [0.45, 0.55])
  - wrong_density_values: 0.833 (expected range [0.78, 0.88])
- Second-run output match: bit-identical
- Library tests after task: pass (32/32)

## Failure-mode coverage
- Wrong output format: broken_wrong_format
- Slivers not filtered: broken_no_sliver_filter
- Wrong reduction / wrong unit on density: broken_wrong_density_values
- Area filter applied in wrong CRS: principled-reasoning (manifests
  as broken_no_sliver_filter — same subchecks fail)
- Hex geometries emitted in wrong CRS: principled-reasoning (Gate 1
  CRS check + `hex_geometries_match` IoU subcheck)
- Top-N count off by arbitrary fraction: principled-reasoning
  (Gate 2 row count tolerance ±5%)
- Rank column inconsistent with density: principled-reasoning
  (`rank_consistent_with_density` subcheck)

## Open issues
- [severity: low] `pop_density` is synthetic (deterministic hash on
  Overture polygon id, range 500-50 000 ppl/km²) rather than derived
  from a real census dataset. This isolates the task to the geometric
  pipeline (area-weighted aggregation) and keeps it deterministic and
  region-independent. Real Lagos density data would require external
  census joins outside Overture.
- [severity: low] The 100 m² sliver threshold is hardcoded into the
  task instruction (the persona names it explicitly). Slivers are
  injected as synthetic equilateral triangles in EPSG:26331 with
  area in [1.0, 99.0] m²; real "alignment-artefact" slivers in
  Overture are sparser and harder to surface deterministically at
  authoring time.

## Suggested prompt changes


## Inventory change proposals


## Library extensions


## Runtime
~7 minutes (Overture S3 fetch + overlay computation + broken-solution
generation).

---

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
The task originated 2026-05-08 (commit 817bf188) as an L2 spatial-analysis exercise for a Lagos housing-policy persona. The agent must reproject WGS84 inputs to a Lagos-appropriate metric CRS, filter sub-100 m² sliver artefacts, compute an overlap-aware area-weighted mean of `pop_density` per hex cell, rank the top 10 %, and emit two outputs: a GeoParquet of hex polygons and a plain Parquet ranking table. Bundled inputs slice Overture `base.land_use` plus 3 000 seeded synthetic slivers and a 1 km flat-topped hex grid generated in EPSG:26331. The author block records reference-score 1.0 and three broken-solution classes (wrong_format, no_sliver_filter, wrong_density_values) covering format-emission, sliver-filter step, and reduction/unit failure modes. Inventory row (authoring/inventory.md L749) corroborates the design.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 817bf188 | initial-authoring | Initial task drop (task.json, grade.py, data, reference, broken-solution scripts, IMPLEMENTATION_NOTES, README) | Initial authoring |
| 2026-05-08 | 001e459b | docs-change | Repo split into authoring/ and eval/ subtrees | Commit msg: reorganize benchmark/ |
| 2026-05-13 | 09:44 a3a8d535 | docs-change | Move benchmark/eval/tasks/ to benchmark/tasks/ | Commit msg: tasks not eval-specific |
| 2026-05-13 | 07:53 89150101 | docs-change | Add image-prompt.md | Commit msg: image-prompt for card |
| 2026-05-13 | 07:58 1b8dda17 | docs-change | Add image.webp | Commit msg: generate image.webp |
| 2026-05-13 | 08:51 3c653731 | docs-change | Regenerate task card images via FLUX schnell | Commit msg: regenerate via fal.ai |
| 2026-05-13 | 08:58 cfbdc7c6 | docs-change | Regenerate task card images via nano-banana-2 | Commit msg: better card images |
| 2026-05-13 | 13:13 9b1fb119 | prompt-change | Merge the explicit "Output schema:" bullet block into the prose body of the instruction (no semantic change to required columns/CRS/format) | Commit msg: merge output schema blocks into prose |
| 2026-05-14 | 1bc112e1 | prompt-change | Strip explicit EPSG:26331 hint, polygon "1 km grid", "Adjacent polygons overlap each other from imperfect alignment", "littered with sliver artefacts" framing; replaced with "compute area in a suitable projected CRS" | Commit msg: strip deducible information; remove input CRS mentions and feature counts |
| 2026-05-15 | e8ea3e18 | prompt-change | Further strip "Drop sliver polygons under 100 m² (compute area in a suitable projected CRS)..." procedural language; replaced with "the top 10 % of hex cells ranked by area-weighted mean population density..." and "Sliver polygons under 100 m² should be excluded." | Commit msg: strip deducible information |
| 2026-05-17 | 12:49 7f31f98d | prompt-change | Final nudge removal: removed explicit `EPSG:26331` from output schema (now "region's standard metric CRS") and softened "Sliver polygons under 100 m²" → "Tiny polygons under 100 m² are noise" | Commit msg: remove CRS codes and operation names |
| 2026-05-17 | 19:17 db638f4f | mixed (grader-change + task.json tag change) | Grader accepts EPSG:32631 OR legacy EPSG:26331 in Gate 1; reprojects submission to reference CRS before comparison; adds new partial-credit subcheck `uses_modern_crs` rewarding EPSG:32631. `task.json > expected_outputs[0].crs` and `tags.crs` updated from EPSG:26331 to EPSG:32631. | Commit msg: fix graders that regressed after nudge removal; partial credit for modern datum |
| 2026-05-26 | 29a9ae32 | docs-change | Folder reorg: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, data/ → inputs/, reference/ → reference/solution/, tests/ → reference/failures/; grader path constant updated to reference/solution/outputs/ | Commit msg: clearer audience-separated layout |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T19:17:27+00:00 (commit db638f4f, class: grader-change + minor prompt-change)

#### Runs considered
| Run | Adapter | Task started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:17:27Z | 0.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:59:32Z | 1.0 | done | stale (pre-cutoff by ~18 min) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T14:14:37Z | 0.0 | done | stale |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T12:19:34Z | 1.0 | done | stale |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T06:06:27Z | 0.833 | done | stale |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T03:00:04Z | 1.0 | done | stale |
| (earlier 16-run history May 12–16) | various | — | — | done/failed | stale |

Only one run started after the cutoff: run-20260526-0748Z (Gemma 4 26B). It produced no output files at all — `score.json` shows Gate 1 fail (`missing hotspots.geoparquet; missing hotspot_ranking.parquet`). The output directory contains only copies of the input files. This is a model-side failure (the small open model did not even attempt the output write), not a task-design problem.

#### Verdict
**insufficient-evidence**

Only one current run exists, from a single adapter (Gemma 4 26B) that failed to produce any output. Per the prompt's "model-side failures are not task problems" rule, this gives no signal about task calibration after the 2026-05-17 grader change. The stale 26-run history (pre-cutoff) shows the task was well-calibrated under the old grader: Claude Opus consistently 1.0, DeepSeek V4 Flash mixed 0.0/0.83/1.0, Gemma 4 26B consistently failing to produce output, Hunyuan 0.0. That pre-cutoff signal supports the design but does not validate the post-2026-05-17 grader.

However, running the grader against the on-disk reference now reveals a **grader-vs-reference inconsistency** introduced by db638f4: the reference solution emits EPSG:26331 (matches README and `reference/solution/generate.py:51`) while the grader's new `uses_modern_crs` subcheck rewards EPSG:32631. The reference therefore now scores 6/7 = 0.857, not the 1.0 documented in the author block of this file and in metadata.yaml's rationale. The expected_score_range bounds and measured_score values in metadata.yaml > broken_solutions are also stale (each broken inherits the reference's legacy CRS, so each loses 1/7).

This is a partial-credit subcheck — it does not break the task (a fully-correct agent in modern CRS still scores 1.0; the reference still scores well above 0). But it makes the metadata.yaml documentation inaccurate and creates an asymmetry: agents who follow the README literally and pick EPSG:26331 are penalized by ~1/7 score versus those who pick EPSG:32631. Both are defensible choices for Lagos (datum-shift difference only).

#### Specific findings
- Reference grader score is now 0.857 (was 1.0 pre-db638f4). Metadata.yaml `tolerances.rationale` and broken_solutions.measured_score entries are stale — fixed unilaterally below.
- The `uses_modern_crs` subcheck rewards EPSG:32631 but the reference emits EPSG:26331. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> The author intended a partial-credit nudge toward the modern datum but did not re-run the grader on the reference after db638f4 (the documented `Verification results > Reference grader score: 1.00` is stale). Decision needed: either (a) regenerate `reference/solution/outputs/` with `METRIC_CRS = "EPSG:32631"` in `reference/solution/generate.py:51` and the `to_parquet` step so the reference scores 1.0 again, or (b) remove the `uses_modern_crs` subcheck entirely since the canonical reference itself fails it, or (c) accept the design and live with reference at 0.857. Option (a) is a `reference-or-data-edit` and option (b) is a `grader-change`; both are out of evaluator scope to apply unilaterally.
- Prompt currently says "in the region's standard metric CRS" — ambiguous between EPSG:26331 (older Minna datum, formally still in use in Nigerian geodesy) and EPSG:32631 (WGS84/UTM 31N, modern). <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Whether "standard" should be read as "modern" or "Nigerian-authority canonical" is a judgment call; the README documents EPSG:26331 as the design choice but the grader prefers 32631. Either keep current ambiguity (testing CRS judgment) or pin the instruction.
- One current run (Gemma 4 26B) produced no outputs — model-side failure, not task signal. No other current runs available to validate the task post-cutoff.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: updated `tolerances.rationale` to reflect that the reference now scores 6/7 = 0.857 (not 1.0) because of the new `uses_modern_crs` subcheck. Re-grade on reference: 0.857. Reason: documentation accuracy after db638f4.
- `metadata.yaml`: updated `broken_solutions.no_sliver_filter.measured_score` to 0.42857 (was 0.5) and `expected_score_range` to [0.40, 0.50]; updated description to mention legacy-CRS subcheck inheritance. Reason: re-measure under current grader (allowed by "update measured_score" rule).
- `metadata.yaml`: updated `broken_solutions.wrong_density_values.measured_score` to 0.71429 (was 0.833) and `expected_score_range` to [0.65, 0.75]; updated description to mention legacy-CRS subcheck inheritance. Reason: re-measure under current grader.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — regenerate reference in EPSG:32631 OR remove the `uses_modern_crs` subcheck (both require editing protected files)
- HR-002 — design-rationale — whether the instruction's "region's standard metric CRS" should pin to 32631 or stay ambiguous

#### Tests run
- grader on reference: 0.857 (6/7 subchecks pass; `uses_modern_crs` fails because reference uses legacy EPSG:26331)
- grader on broken_wrong_format: 0.0
- grader on broken_no_sliver_filter: 0.42857
- grader on broken_wrong_density_values: 0.71429
- pytest: pass (35/35)

## Evaluator review 2026-05-26b  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from the prior block. The task remains an L2 spatial-analysis exercise
(Lagos housing-density persona): reproject WGS84 inputs to a Lagos metric CRS,
filter sub-100 m² sliver artefacts, compute an overlap-aware area-weighted mean of
`pop_density` per hex cell, rank the top 10 %, and emit a GeoParquet of hex polygons
plus a plain Parquet ranking table. Inventory row (`authoring/inventory.md` L749)
and the thesis region table (`thesis/thesis.typ` L408) both name **EPSG:26331
(Minna / Nigeria West Belt)** as the canonical Lagos metric CRS; the README and
`reference/solution/generate.py:51` (`METRIC_CRS = "EPSG:26331"`) match.

#### Change log
No new design-affecting commits since the prior evaluator block. The only commits
touching the task directory since 2026-05-17 are 29a9ae32 (folder reorg, docs-change)
and 7a100062 (the prior evaluator's audit commit). The design-affecting cutoff is
therefore still db638f4f (2026-05-17T19:17:27Z), which added the `uses_modern_crs`
partial-credit subcheck and changed `task.json > expected_outputs[0].crs` from
EPSG:26331 to EPSG:32631 — **without regenerating the reference**, leaving the
reference at EPSG:26331. See the prior block's change-log table for the full history.

### 2. Current-state review

This re-run was triggered by two fresh runs added after the prior evaluation
(opus + gemma). They change the evidence picture decisively: there are now **two
current runs from two adapter families**, so the prior `insufficient-evidence`
verdict no longer holds.

#### Cutoff
- design-affecting cutoff: 2026-05-17T19:17:27+00:00 (commit db638f4f, class: grader-change + task.json CRS-contract change). Unchanged from prior block.

#### Runs considered
| Run | Adapter | Task started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-26T19:05:42Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:48:25Z | 0.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:17:27Z | 0.0 | done | current (model-side no-output) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:59:32Z | 1.0 | done | stale (pre-cutoff by ~18 min) |
| (earlier 25-run history May 12–17) | various | — | — | done/failed | stale |

#### Per-run inspection (current runs)
- **opus (1.0).** Emitted both files, **CRS = EPSG:32631**, 104 rows. Every subcheck
  passes (`uses_modern_crs` True; hex_id Jaccard 1.0000; density 104/104; ranks
  monotone+unique+start-at-1; overlap 104/104; sliver 104/104; geometry IoU 104/104).
  Opus reproduced the reference answer exactly while choosing the *modern* datum;
  the grader's reproject-before-compare step makes the geometric subchecks agree.
- **gemma run-1922 (0.0).** Emitted both files, CRS = EPSG:32631, **178 rows**.
  Gate 1 passes (schema valid); Gate 2 fails: row count 178 not within 5 % of the
  reference's 104. `outputs/solve.py` shows the cause — gemma took `int(len(full_hex_grid)
  * 0.10)` after a *left* merge that kept all 1 782 grid cells (zero-filled the
  non-overlapping ones), so its "top 10 %" base is 1 782 → 178, instead of the ~1 030
  *eligible* (≥1 kept-polygon overlap) cells → 104. This is README failure-mode #6
  ("top-N count off"), a genuine GIS-reasoning error, **not** a model-side infra
  failure. The grader caught it correctly at the structural gate.
- **gemma run-0748 (0.0).** Produced no output files at all (only echoed the inputs) —
  model-side no-output failure. No task signal; recorded for completeness.

#### Verdict
**prompt-grader-inconsistent**

The two current runs show the task discriminates correctly between a capable agent
(opus, 1.0) and a weaker one (gemma, 0.0 on a real top-N reasoning error). The
semantic pipeline is sound and well-calibrated. **However**, running the current
grader on the canonical reference (`reference/solution/outputs/`) yields **0.857
(6/7)** — the reference fails its own `uses_modern_crs` subcheck because it emits
EPSG:26331 while the subcheck rewards EPSG:32631. This is below the 0.95 acceptance
threshold that the design prompt requires the reference to clear, and it is a direct
inconsistency between the grader/`task.json` (which were changed to EPSG:32631 in
db638f4) and the reference/README/inventory/thesis (all EPSG:26331, unchanged). An
agent that follows the README's documented design choice (26331) is silently
penalised ~1/7 (≈0.143) relative to one that picks 32631, even though both are
correct, equal-validity conformal UTM-31N projections for Lagos and the geometric
result is identical after reprojection. The defect was introduced when db638f4 added
the modern-datum reward and flipped the `task.json` CRS contract but did not
regenerate the reference; the commit's documented `Reference grader score: 1.00`
is stale.

#### Specific findings
- Reference scores 0.857 (6/7) on the current grader; opus (32631) scores 1.0; the
  only differentiator is `uses_modern_crs`. The fix is unambiguous in *direction*
  (the reference must score ≥ 0.95) but ambiguous in *which file to change*, and all
  candidate fixes touch protected files — see HR-001.
- The grader/`task.json` say EPSG:32631; the reference/README/inventory/thesis say
  EPSG:26331. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Decision needed: either (a) regenerate `reference/solution/` in EPSG:32631 so the canonical answer matches the now-canonical 32631 contract (a `reference/solution/generate.py` + outputs edit — forbidden to the evaluator); or (b) drop / neutralise the `uses_modern_crs` subcheck and revert `task.json`/README/grader to EPSG:26331 to match the design spec (a `grader-change` + `expected_outputs` CRS-contract change — also out of evaluator scope, since changing `expected_outputs[].crs` is explicitly disallowed). Both are out of the evaluator's unilateral authority, so this is flagged rather than fixed. Default recommendation: option (a), because db638f4 already moved the public CRS contract (`task.json`) to 32631 and the modern datum is the better real-world default; regenerating the reference to 32631 restores reference→1.0 and makes 26331 the (still-accepted) legacy path.
- Instruction says "in the region's standard metric CRS" — deliberately ambiguous
  between 26331 (Nigerian-authority legacy) and 32631 (modern WGS84/UTM-31N).
  <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> This ambiguity is defensible as a CRS-judgment test, but it currently interacts with HR-001 to create the scoring asymmetry. If HR-001 is resolved by pinning to 32631, consider whether the instruction should keep the soft phrasing or name the datum.
- Verdict upgraded from the prior block's `insufficient-evidence` to
  `prompt-grader-inconsistent`: there are now two current runs from two adapter
  families (opus + gemma), and inspecting the reference against the current grader
  surfaces the concrete inconsistency rather than merely suspecting it.
- Broken-solution scores re-measured under the current grader and still match
  metadata: wrong_format 0.0, no_sliver_filter 0.42857, wrong_density_values 0.71429.
  The three ranges remain distinct; the grader retains resolution.

### 3. Changes applied this run

#### Unilateral edits
- None. The reference-vs-grader CRS inconsistency is real but every viable fix edits
  a protected file (`reference/solution/generate.py` + its outputs, or
  `task.json > expected_outputs[].crs`). Per the evaluator contract these are
  flagged, not applied. `metadata.yaml` was already corrected by the prior evaluator
  (rationale + broken measured_scores reflect the 0.857 reference and re-measured
  brokens); re-running confirms those numbers are still accurate, so no edit needed.
  `coverage.yaml` updated only in `evaluator_run_at` (no slug changes).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (med) — reference (EPSG:26331) fails the grader's `uses_modern_crs` subcheck → reference scores 0.857 < 0.95 acceptance floor; resolve by regenerating reference in 32631 (preferred) or reverting the CRS contract+subcheck to 26331. Both touch protected files.
- HR-002 — design-rationale (low) — whether the instruction's "region's standard metric CRS" should be pinned (to 32631) once HR-001 is resolved.

#### Tests run
- grader on reference: 0.857 (6/7; `uses_modern_crs` fails on legacy EPSG:26331)
- grader on broken_wrong_format: 0.0
- grader on broken_no_sliver_filter: 0.42857
- grader on broken_wrong_density_values: 0.71429
- pytest: pass (35/35)

## Evaluator review 2026-05-27  (evaluator-commit eecb6b87)

### 1. Design history

#### Initial design intent
Unchanged from the prior two blocks. The task is an L2 spatial-analysis exercise for
the Lagos housing-density persona: reproject WGS84 inputs to a Lagos metric CRS, filter
sub-100 m² sliver artefacts, compute an overlap-aware area-weighted mean of `pop_density`
per hex cell, rank the top 10 %, and emit a GeoParquet of hex polygons plus a plain
Parquet ranking table. Inventory row (`authoring/inventory.md` L749) and the thesis
region table (`thesis/thesis.typ` L408) both name **EPSG:26331 (Minna / Nigeria West
Belt)** as the canonical Lagos metric CRS; the README and `reference/solution/generate.py:51`
(`METRIC_CRS = "EPSG:26331"`) match. The `task.json > expected_outputs[0].crs` and grader,
however, were moved to EPSG:32631 in db638f4f.

#### Change log
No new design-affecting commits since the prior evaluator blocks. The only commits
touching the task directory after the cutoff are `7a100062` and `8f574ead` (the prior
two evaluator audit commits, both docs-change). The design-affecting cutoff is therefore
still **db638f4f (2026-05-17T19:17:27Z)** — the commit that added the `uses_modern_crs`
partial-credit subcheck, made the grader reproject the submission to the reference CRS,
and flipped `task.json > expected_outputs[0].crs` and `tags.crs` from EPSG:26331 to
EPSG:32631 **without regenerating the reference**. See the first evaluator block's
change-log table for the full per-commit history.

### 2. Current-state review

This is a 3rd-pass re-evaluation triggered by the orchestrator sweep. No new runs and no
new design-affecting commits have appeared since the 2026-05-26b block, so the evidence
picture and the verdict are unchanged.

#### Cutoff
- design-affecting cutoff: 2026-05-17T19:17:27+00:00 (commit db638f4f, class: grader-change + task.json CRS-contract change). Unchanged.

#### Runs considered
| Run | Adapter | Task started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-26T19:05:42Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:48:25Z | 0.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:17:27Z | 0.0 | done | current (model-side no-output) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:59:32Z | 1.0 | done | stale (pre-cutoff by ~18 min) |
| (earlier 25-run history May 12–17) | various | — | — | done/failed | stale |

#### Per-run inspection (current runs) — re-verified this pass
- **opus (1.0).** Re-inspected on disk: both files present, **CRS = EPSG:32631**, 104 rows.
  All 7 subchecks pass (`uses_modern_crs` True; hex_id Jaccard 1.0000; density 104/104;
  ranks monotone+unique+start-at-1; overlap 104/104; sliver 104/104; geometry IoU 104/104).
  Opus reproduced the reference answer exactly while choosing the modern datum.
- **gemma run-1922 (0.0).** Re-inspected: both files present, CRS = EPSG:32631, **178 rows**;
  Gate 1 passes, Gate 2 fails on `row count 178 not within 5% of reference 104`. This is the
  README failure-mode #6 (top-N base computed over all 1 782 grid cells instead of the ~1 030
  eligible cells) — a genuine GIS-reasoning error, not a model-side infra failure.
- **gemma run-0748 (0.0).** No output files (echoed inputs only) — model-side no-output. No
  task signal.

#### Verdict
**prompt-grader-inconsistent**

Re-confirmed unchanged. The current runs show the task discriminates correctly (opus 1.0,
gemma 0.0 on a real top-N error) and the semantic pipeline is sound. But running the
current grader on the canonical reference (`reference/solution/outputs/`) still yields
**0.857 (6/7)** — the reference fails its own `uses_modern_crs` subcheck because it emits
EPSG:26331 while the subcheck rewards EPSG:32631. This is below the 0.95 acceptance floor
the design prompt requires the reference to clear, and is a direct inconsistency between
the grader/`task.json` (EPSG:32631 since db638f4) and the reference/README/inventory/thesis
(all EPSG:26331). The grader also reprojects only the submission to the reference CRS
(`grade.py:192–195`) — a one-sided reprojection that papers over the contract mismatch
(prompt Step 2c-CRS). An agent that follows the README's documented 26331 choice is
silently penalised ~1/7 (≈0.143) relative to one that picks 32631, even though both are
equally-valid conformal UTM-31N projections for Lagos and the geometric result is identical
after reprojection. Every viable fix touches a protected file, so this remains flagged, not
fixed.

#### Specific findings
- Reference scores 0.857 (6/7) on the current grader; opus (32631) scores 1.0; the only
  differentiator is `uses_modern_crs`. Re-confirmed on disk this pass.
  <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> The grader/`task.json` say EPSG:32631 while the reference/README/inventory/thesis say EPSG:26331. Decision needed: either (a) regenerate `reference/solution/` in EPSG:32631 so the canonical answer matches the now-canonical 32631 contract (a `reference/solution/generate.py` + outputs edit — forbidden to the evaluator); or (b) drop / neutralise the `uses_modern_crs` subcheck and revert `task.json`/README/grader to EPSG:26331 to match the design spec (a `grader-change` + `expected_outputs` CRS-contract change — also out of evaluator scope). Default recommendation: option (a) — db638f4 already moved the public `task.json` contract to 32631 and the modern datum is the better real-world default; regenerating the reference to 32631 restores reference→1.0 and keeps 26331 as the still-accepted legacy path.
- Instruction says "in the region's standard metric CRS" — deliberately ambiguous between
  26331 (Nigerian-authority legacy) and 32631 (modern WGS84/UTM-31N).
  <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Defensible as a CRS-judgment test, but it interacts with HR-001 to create the scoring asymmetry. If HR-001 is resolved by pinning to 32631, decide whether to keep the soft phrasing or name the datum.
- Broken-solution scores re-measured under the current grader and still match metadata:
  wrong_format 0.0, no_sliver_filter 0.42857 (3/7), wrong_density_values 0.71429 (5/7).
  The three ranges remain distinct; the grader retains resolution.
- No new runs or design-affecting commits since the 2026-05-26b block — the verdict is a
  re-confirmation, not a new finding.

### 3. Changes applied this run

#### Unilateral edits
- None. The reference-vs-grader CRS inconsistency is real but every viable fix edits a
  protected file (`reference/solution/generate.py` + its outputs, or
  `task.json > expected_outputs[].crs`). Per the evaluator contract these are flagged, not
  applied. `metadata.yaml` was already corrected by the first evaluator (rationale + broken
  measured_scores reflect the 0.857 reference and re-measured brokens); re-running this pass
  confirms those numbers are still accurate, so no edit needed. `coverage.yaml` updated only
  in `evaluator_run_at` (no slug changes).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (med) — reference (EPSG:26331) fails the grader's `uses_modern_crs` subcheck → reference scores 0.857 < 0.95 acceptance floor; resolve by regenerating reference in 32631 (preferred) or reverting the CRS contract+subcheck to 26331. Both touch protected files.
- HR-002 — design-rationale (low) — whether the instruction's "region's standard metric CRS" should be pinned (to 32631) once HR-001 is resolved.

#### Tests run
- grader on reference: 0.857 (6/7; `uses_modern_crs` fails on legacy EPSG:26331)
- grader on broken_wrong_format: 0.0
- grader on broken_no_sliver_filter: 0.42857
- grader on broken_wrong_density_values: 0.71429
- pytest: pass (35/35)

## Evaluator review 2026-05-28  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from prior blocks. L2 spatial-analysis exercise for the Lagos
housing-density persona: reproject WGS84 inputs to a Lagos metric CRS, filter
sub-100 m² sliver artefacts, compute an overlap-aware area-weighted mean of
`pop_density` per hex cell, rank the top 10 %, and emit a GeoParquet of hex
polygons plus a plain Parquet ranking table. Inventory (L749) and the thesis
region table both name **EPSG:26331 (Minna / Nigeria West Belt)** as the
canonical Lagos metric CRS.

#### Change log
Two new commits touch the task directory since the prior block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342be | mixed (task.json + metadata.yaml) | Repo-wide: introduces integer `task.json.version` field (implicit v1 ⇒ explicit on next meaningful edit); drops `prompt_version` from `task.json`/`metadata.yaml` | Commit msg: "Add task content versioning; drop unused prompt_version" — wire run-time snapshotting + UI dimming of stale runs |
| 2026-05-28 | 0888e6fe | mixed (prompt-change + grader-change + reference-CRS contract) | CRS accept-list refactor resolving HR-001/HR-002: `task.json` instruction "region's standard metric CRS" → "Nigeria's national grid"; `expected_outputs[0].crs` 32631 → 26331; `version: 2`; grade.py uses `geo_grading.check_and_normalize_crs({26331, 32631}, 26331)` and renames subcheck `uses_modern_crs` → `official_crs_used` (rewards 26331 as the regional canonical). Metadata rationale + broken `measured_score` refreshed. | Commit msg: applies the prompt's "CRS accept-list refactor" remediation — restores reference→1.0 by aligning the contract with the canonical reference rather than the modern-datum nudge |

Both are design-affecting (they change either the grader, the prompt,
or `expected_outputs[]`).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T07:31:27+00:00** (commit 0888e6fe, class: mixed prompt-change + grader-change + expected_outputs CRS contract). Supersedes the prior db638f4f cutoff.

#### Runs considered
| Run | Adapter | Task started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:17:33Z | 0.0 | done | stale (pre-cutoff by ~4 h) |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T01:13:49Z | 0.0 | done | stale (pre-cutoff by ~6 h) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:21:16Z | 0.0 | failed | stale |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T20:16:18Z | 1.0 | done | stale |
| (earlier 29-run history May 12–26) | various | — | — | done/failed | stale |

**No current runs exist after the 2026-05-28T07:31:27Z cutoff.** All four
post-May-27 runs predate the HR-001 resolution by 4–11 hours; their
`score.json` shows the old `uses_modern_crs` subcheck name (where any
subchecks ran at all). The earlier 29-run history is all far pre-cutoff.

#### Per-run inspection
Skipped — no current runs. The stale runs were inspected in the prior
evaluator block and are not retroactive evidence for the post-0888e6fe
task. For reference (recorded so the next evaluator does not redo the
work): the 2026-05-28-0113Z opus run produced 179 rows under the old
contract and was Gate-2-rejected — failure-mode #6 (top-N row count
off), a genuine GIS-reasoning error; the 2026-05-28-0317Z gemma run
produced no outputs (model-side); the 2026-05-27-2016Z opus run scored
1.0 cleanly under the old grader.

#### 2c-CRS consistency check
Verified clean under the new contract:
- `task.json > expected_outputs[0].crs` = **EPSG:26331**.
- `reference/solution/outputs/hotspots.geoparquet` CRS = **EPSG:26331**
  (confirmed via the grader's CRS report: "submission CRS is EPSG:26331;
  official is EPSG:26331").
- `README.md > Output` block states EPSG:26331 ("top 10% hex cells (104
  rows) in EPSG:26331").
- Grader Gate-1 accept-list = {EPSG:26331, EPSG:32631}; submissions in
  32631 are reprojected to 26331 before the geometric subchecks (this
  is a declared accept-list policy, **not** a one-sided paper-over —
  the canonical reference is itself in 26331, and the `official_crs_used`
  subcheck makes the 32631 path score (N-1)/N rather than 0). Permitted
  under the prompt's Step 2c-CRS rules.
- Instruction phrasing "in Nigeria's national grid" is a **category-level
  hint** (not the EPSG, not the datum name "Minna") that lets a
  knowledgeable agent infer EPSG:26331 from regional convention while
  not enumerating the alternatives. Conforms to the updated Step 4
  CRS-accept-list refactor doctrine.

No CRS/format inconsistency remains.

#### Verdict
**insufficient-evidence**

No `current` runs exist (the cutoff moved 11 days forward when 0888e6fe
landed earlier today, invalidating every prior run). The grader and
reference are internally consistent: reference scores 7/7 = 1.0, brokens
score 0.0 / 0.5714 / 0.8571 (all inside their declared
`expected_score_range`), and pytest is 41/41 green. There is no reason
to suspect a problem from offline inspection — the prior verdict's
inconsistency (reference 0.857 < 0.95) has been resolved by the
accept-list refactor. The orchestrator should re-run the sweep against
this task to gather new evidence; the next evaluator pass will have
runs to grade and can pronounce calibrated / too-strict / too-easy with
concrete signal.

#### Specific findings
- Reference grader 1.0 (7/7), brokens 0.0 / 0.5714 / 0.8571 — all within
  their `expected_score_range`. No regressions versus the metadata as
  rewritten in 0888e6fe.
- No current runs available; verdict is `insufficient-evidence` per the
  prompt's "fewer than 2 current runs" rule. Transient state expected
  immediately after a CRS-contract change; not a defect.
- No prompt/grader/reference/CRS inconsistency to flag. HR-001 and
  HR-002 from prior blocks were closed in 0888e6fe; that commit's
  `status.json` write set verdict `calibrated` with no
  `human_review_items`. The present block reverts the verdict to
  `insufficient-evidence` only because no post-cutoff runs exist yet —
  not because anything is broken.
- Coverage tags re-validated against `coverage-vocabulary.yaml`: all
  slugs verbatim. Removed the stale HR-001 note from the prior block's
  `coverage.yaml > notes` since the inconsistency it described is
  fixed; kept the Overture provenance note because it still applies.

### 3. Changes applied this run

#### Unilateral edits
- `coverage.yaml`: bumped `evaluator_run_at` and removed the stale
  "Output CRS per task.json is EPSG:32631 ... See HR-001" note (the
  contract now agrees with the reference; both are EPSG:26331). No
  slug changes. Not a `task.json`/grader/inputs edit → no `version`
  bump required.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (7/7)
- grader on broken_wrong_format: 0.0
- grader on broken_no_sliver_filter: 0.5714 (4/7)
- grader on broken_wrong_density_values: 0.8571 (6/7)
- pytest: pass (41/41)

## Evaluator review 2026-06-06  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from prior blocks. L2 spatial-analysis exercise for the Lagos
housing-density persona: reproject WGS84 inputs to a Lagos metric CRS,
filter sub-100 m² sliver artefacts, compute an overlap-aware
area-weighted mean of `pop_density` per hex cell, rank the top 10 %,
and emit a GeoParquet of hex polygons plus a plain Parquet ranking
table.

#### Change log
One new design-affecting commit touches the task directory since the
prior block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 05aabd64 | grader-change | Repo-wide soften-CRS refactor: grader switched from `check_and_normalize_crs` (Gate-1 accept-list of {26331, 32631}) to `grade_crs_soft` (hard-fail only on unparseable CRS; reproject any parseable CRS into canonical for spatial subchecks). `official_crs_used` subcheck split into `crs_is_canonical` (=26331) + `crs_in_meaningful_set` (∈ {26331, 32631}). Subcheck count grew from 7 to 8. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — over-penalising a recoverable failure mode |

This is design-affecting (grader-change), so it supersedes the prior
cutoff.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57+00:00** (commit 05aabd64, class: grader-change). Supersedes the prior 0888e6fe cutoff.

#### Runs considered
| Run | Adapter | Task started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T22:11:26Z | 0.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:24:47Z | 0.875 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:52:38Z | 0.75 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:13:09Z | — | failed | current (model-side: max iterations) |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T18:10:19Z | 0.75 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:35:31Z | — | failed | current (model-side: max iterations) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:54:33Z | — | cancelled | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T18:03:57Z | 0.0 | done | stale (pre-cutoff by ~1 h) |
| (earlier 30-run history May 12–28) | various | — | — | done/failed | stale |

#### Per-run inspection (current runs)
- **opus run-1927 (0.0).** Emitted both files but **179 rows**. Gate 1 passes; Gate 2 fails on `row count 179 not within 5% of reference 104`. Same top-N-base error as the gemma run-1922 in the prior block (top-10 % computed over all 1 782 grid cells, not the ~1 030 eligible cells). Genuine GIS-reasoning error, not model-side.
- **gemma4 run-2225 (0.875).** 104 rows, **CRS = EPSG:32631** (generic UTM 31N). All six geometric/tabular subchecks pass (Jaccard 0.9904, density 103/103, etc.); `crs_is_canonical` fails (32631 ≠ 26331), `crs_in_meaningful_set` passes (32631 ∈ {26331, 26391, 32631}). 7/8 = 0.875 reflects the partial-credit policy for the meaningful-but-generic pick.
- **opus run-2332 (0.75).** 104 rows, **CRS = EPSG:26391** (literal "Minna / Nigeria West Belt" — same Minna datum as 26331 but different false-origin convention). All six geometric subchecks pass after reprojection. Under the grader as committed in 05aabd64 (`MEANINGFUL_EPSGS = {26331, 32631}`), `crs_in_meaningful_set` failed and the score landed at 6/8 = 0.75 — but the score was recorded before this pass widened the meaningful set. Re-grading on disk this pass with `MEANINGFUL_EPSGS = {26331, 26391, 32631}` lifts the score to 7/8 = 0.875 (the cached `score.json` was written under the old grader and is now slightly out-of-date; the next eval-pass re-grade will correct it).
- **deepseek run-0902 (0.75).** Same shape as opus run-2332: 104 rows, CRS = EPSG:26391, all geometric subchecks pass after reprojection. Re-grading on disk this pass scores 7/8 = 0.875.
- **gemma4 run-0109 (failed).** `RuntimeError: max iterations exceeded (100)` — model-side infra failure, no task signal.
- **gemma4 detailed-prompt runs (0953Z, 1129Z, 1334Z).** Two cancelled, one max-iterations failure. Model-side.

#### 2c-CRS consistency check
Verified clean:
- `task.json > expected_outputs[0].crs` = **EPSG:26331**.
- `reference/solution/outputs/hotspots.geoparquet` CRS = **EPSG:26331** (matches contract).
- `README.md > Output` block states **EPSG:26331**.
- Grader Gate-1 policy is "any parseable CRS"; submissions are reprojected to **EPSG:26331** before geometric subchecks (declared accept-list policy under Step 4 CRS-accept-list refactor — both sides end up in the same metric CRS for IoU and area work, so this is a permitted one-sided reprojection).
- Instruction phrasing **"in Nigeria's national grid"** is the family-level hint per Step 4 doctrine (does not name the EPSG, does not enumerate alternatives, does not name the Minna datum).

No CRS/format inconsistency remains.

#### Verdict
**calibrated**

Five `current` non-infra runs from three adapter families (claude-opus, openrouter-gemma4, openrouter-deepseek). The score distribution spans 0.0 (opus structural failure on top-N base), 0.75–0.875 (opus + deepseek + gemma4 on a defensible-but-non-canonical CRS pick), with full credit available for an agent that picks the canonical Minna grid. The grader discriminates correctly: a real GIS-reasoning error (wrong top-N denominator) zeros the score; valid geometry with a meaningful-but-generic CRS scores partial credit; only the regionally idiomatic pick gets full marks. After widening `MEANINGFUL_EPSGS` to include EPSG:26391 (the literal "Minna / Nigeria West Belt" zone — two independent runs picked it, and it is at least as regionally defensible as 26331), the partial-credit ladder reads cleanly: 26331 → 1.0, 26391 or 32631 → 0.875, anything else parseable → 0.75 or lower. The semantic pipeline is sound and the calibration is faithful to the prompt's "CRS-accept-list" doctrine.

#### Specific findings
- Reference grader: 1.0 (8/8) after the meaningful-set widening; brokens 0.0 / 0.625 / 0.875 (all within the refreshed `expected_score_range` in metadata.yaml). No regressions.
- Subcheck count grew 7 → 8 in commit 05aabd64; this pass refreshes the broken `measured_score` values (0.5714 → 0.625 and 0.8571 → 0.875) to match the current grader. Allowed unilaterally under Step 4.
- `MEANINGFUL_EPSGS` widened from {26331, 32631} to {26331, 26391, 32631}. EPSG:26391 is the literal "Minna / Nigeria West Belt" registry entry (same Minna datum as 26331). Two independent runs (opus + deepseek) chose 26391 — when an agent that reads "Nigeria's national grid" literally lands on 26391, that pick is at least as defensible as 26331 (which is now labelled "Minna / UTM zone 31N" in the registry). Canonical stays 26331 to match the reference, README, inventory, and thesis. This is a permitted Step 4 CRS-accept-list refactor.
- `analyst_notes` was missing from `task.json`; authored this pass.
- `task.json.version` bumped 2 → 3 (grader edit).
- No prompt/grader/reference/CRS inconsistency to flag.

### 3. Changes applied this run

#### Unilateral edits
- `grade.py`: widened `MEANINGFUL_EPSGS` from `{26331, 32631}` to `{26331, 26391, 32631}`; updated the module-level rationale comment and the subcheck-8 docstring to mention EPSG:26391 (literal "Minna / Nigeria West Belt", same Minna datum, different false-origin convention than 26331). Re-grade on reference: 1.0 (8/8). Reason: two independent post-cutoff runs (opus + deepseek) both picked EPSG:26391, which is at least as regionally defensible as 26331 given the prompt's "Nigeria's national grid" phrasing; this is a Step 4 CRS-accept-list expansion with concrete evidence.
- `task.json`: bumped `version` 2 → 3 (grader edit triggers the bump). Re-grade on reference: 1.0. Reason: grader contract changed.
- `task.json`: authored `analyst_notes` (description, approach, pitfalls). Reason: field was missing; no version bump needed for `analyst_notes` per Step 4 rules.
- `metadata.yaml`: updated `tolerances.rationale` to reflect the 3-EPSG meaningful set and the 8-subcheck grader. Reason: documentation accuracy after the 05aabd64 grader refactor.
- `metadata.yaml`: refreshed `broken_solutions.no_sliver_filter.measured_score` 0.5714 → 0.625 (5/8) and `expected_score_range` to [0.55, 0.70]; refreshed `broken_solutions.wrong_density_values.measured_score` 0.8571 → 0.875 (7/8) and `expected_score_range` to [0.82, 0.92]. Reason: re-measurement under the current grader (allowed by Step 4 "update measured_score" rule); subcheck count grew 7 → 8 in 05aabd64 so the brokens that inherit the reference's canonical CRS each gain one passing subcheck.
- `coverage.yaml`: bumped `evaluator_run_at`. No slug changes.

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (8/8)
- grader on broken_wrong_format: 0.0
- grader on broken_no_sliver_filter: 0.625 (5/8)
- grader on broken_wrong_density_values: 0.875 (7/8)
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
- Row-count ±5% check deleted: already covered by the stricter
  `hex_id_set_jaccard_vs_reference` (≥0.85) subcheck.
- Cross-file hex_id set equality (GeoParquet vs Parquet) migrated to a
  new `cross_file_hex_id_set_matches` subcheck.
- Removed the now-unused `ROW_COUNT_PCT` constant.
- Subchecks now total 9 (was 8).

### Verification
- Reference solution re-graded: 1.0 (9/9 subchecks).

## Evaluator review 2026-06-12  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Unchanged from prior blocks. L2 spatial-analysis exercise for the Lagos
housing-density persona: reproject WGS84 inputs to a metric Nigerian
CRS, filter sub-100 m² sliver artefacts, compute an overlap-aware
area-weighted mean of `pop_density` per hex cell, rank the top 10 %,
and emit a GeoParquet of hex polygons plus a plain Parquet ranking
table.

#### Change log
Three new design-affecting commits touch the task directory since the
2026-06-06 evaluator block (all grader-only; prompt, inputs, and
reference are untouched):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed21 | grader-change | Benchmark-wide Gate-2 drop: removed the `structural_correctness` gate and its early return; row-count ±5% check deleted (covered by the stricter hex_id Jaccard subcheck); cross-file hex_id equality migrated to a new `cross_file_hex_id_set_matches` subcheck; subchecks 8 -> 9. Already documented in the "Manual cleanup 2026-06-06" block above. | Commit msg: gate was inconsistent across graders; one hard gate, salvageable checks become subchecks |
| 2026-06-07 | c749e57b | grader-change | Benchmark-wide weighting: the six data-content subchecks (hex_id Jaccard, cross-file set, density, overlap counts, sliver counts, geometry IoU) tagged weight=3.0; rank consistency and the two CRS subchecks stay 1.0; total weight 21. | Commit msg: weight data-content subchecks 3x; schema/structural stay 1.0 |
| 2026-06-09 | 501e9a60 | grader-change | `grade_crs_soft` now accepts a canonical *set*; this grader pins `CANONICAL_EPSGS = {26331, 26391}` so both Minna-datum picks score `crs_is_canonical = True`; mislabelled comments corrected (26331 is "Minna / UTM zone 31N", 26391 is the literal "Minna / Nigeria West Belt"); reprojection target stays min(set) = 26331. | Commit msg: prompt says only "Nigeria's national grid"; 26391 is the literal registry match for Lagos's belt, equally legitimate |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-09T12:37:43Z** (commit 501e9a60, class: grader-change). Supersedes the prior 05aabd64 cutoff. The last prompt/inputs-affecting commit remains 0888e6fe (2026-05-28); every run below saw the current instruction and inputs.

#### Runs considered
| Run | Adapter | Task started | Recorded score | Re-grade (current grader) | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T12:38:07Z | 0.7143 (score.json; run.json index shows null) | 0.7143 | done | current |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-09T07:40:20Z | 0.9524 | **1.0** | done | stale by ~5 h (pre-501e9a60); re-graded |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T16:53:04Z | 0.7143 | 0.7143 | done | stale (pre-501e9a60); re-graded |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T18:10:19Z | 0.75 | **1.0** | done | stale; re-graded |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:52:38Z | 0.75 | **1.0** | done | stale; re-graded |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:24:47Z | 0.875 | 0.9524 | done | stale; re-graded |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T22:11:26Z | 0.0 | 0.8571 | done | stale; re-graded |
| run-20260529-0109Z / 20260606-0953Z / 1129Z / 1334Z | gemma4 variants | — | — | — | failed/cancelled | model-side (max iterations / cancelled), no task signal |
| (earlier 30-run history May 12-28) | various | — | — | — | done/failed | stale (pre-prompt-change 0888e6fe) |

All three June runs carry `task_version: 3`, matching the current `task.json`
version (the three post-block commits were grader-only and did not bump it),
so the version check passes; only the timestamp cutoff marks them stale.
Since every design-affecting commit after 0888e6fe is grader-only, the
on-disk outputs of all seven completed post-prompt runs remain valid agent
behaviour, and re-grading them under the current grader (same doctrine as
Step 4's accept-list re-grade) yields current-equivalent evidence. The
re-grade column above is from this pass, on disk.

#### Per-run inspection (post-prompt runs)
- **deepseek-flash basic run-084636Z (0.7143).** 179 rows (top-10 % over the
  full 1 782-cell grid), Jaccard 0.0443, density 0/12 on the tiny overlap;
  ranks, counts, geometries, CRS (26391, canonical) all pass. Two weight-3
  fails = 15/21. Genuine GIS-reasoning error (wrong top-N base plus a wrong
  density reduction). Note: the parent `run.json` per-task block shows
  `score: null` while `score.json` holds 0.7143 with the current grader's
  detail strings; a runs-index sync quirk outside the task dir, flagged to
  infra informally, not a task defect.
- **deepseek-flash detailed run-074701Z (re-grade 1.0).** 104/104 on
  everything; original CRS EPSG:26391. Recorded 0.9524 only because it ran
  5 h before 501e9a60 made 26391 canonical; this run is the motivating case
  named in that commit's message.
- **gemma4 detailed run-112430Z (0.7143).** 178 rows (wrong top-N base,
  Jaccard 0.5843) and sliver counts 0/104 (did not count filtered slivers
  per hex); density and geometry on shared cells correct; CRS 26331.
- **opus run-1927Z (re-grade 0.8571).** 179 rows; only the weight-3 Jaccard
  subcheck fails now that Gate 2 is gone (was a hard 0.0). Everything else,
  including per-cell densities and counts, matches the reference.
- **opus run-2332Z, deepseek-pro run-0902Z (re-grade 1.0).** Both picked
  EPSG:26391 and match the reference exactly; lifted from 0.75 by the
  canonical-set widening plus the gate-2/weights refactors.
- **gemma4 run-2225Z (re-grade 0.9524).** Perfect geometry/table in
  EPSG:32631; loses only `crs_is_canonical` (20/21).

#### 2c-CRS consistency check
Verified clean:
- `task.json > expected_outputs[0].crs` = EPSG:26331; reference GeoParquet
  CRS = EPSG:26331 (Minna / UTM zone 31N, confirmed on disk); README Output
  block states EPSG:26331. All three agree.
- Grader hard-fails only an unparseable/missing CRS; any parseable CRS is
  reprojected to min(CANONICAL_EPSGS) = 26331 (the reference frame) before
  spatial subchecks; the original pick is graded by `crs_is_canonical`
  ({26331, 26391}) and `crs_in_meaningful_set` (+32631). Declared
  accept-list policy per Step 4 doctrine, not a paper-over.
- Instruction phrasing "Nigeria's national grid" remains the category-level
  hint; with 501e9a60 both defensible Minna readings now score full, which
  removes the registry-name-vs-convention coin flip the 2026-06-06 block
  had to resolve by widening the meaningful set only.

#### Verdict
**calibrated**

Seven completed runs saw the current prompt; under the current grader they
span 0.71 / 0.71 / 0.86 / 0.95 / 1.0 / 1.0 / 1.0 across four adapter
families (claude-opus, gemma4, deepseek-flash, deepseek-pro). Full marks
require the complete pipeline plus a canonical Minna-datum CRS; a generic
UTM pick costs exactly 1/21; a wrong top-N base costs a weight-3 subcheck
(0.857 when everything else is right); compounding errors (missed sliver
accounting, wrong density reduction) drop runs to 0.71. The strict
timestamp cutoff leaves only one current run, but the re-graded evidence is
decisive and consistent. One deliberate calibration shift worth recording:
the gate-2 drop (363aed21) softened the wrong-top-N-base failure from a
hard 0.0 to 0.86/0.71 partial credit; that is benchmark-wide policy, not a
task quirk.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| two files `hotspots.geoparquet` + `hotspot_ranking.parquet`, formats | instruction, output paragraph | stated |
| GeoParquet columns hex_id/rank/area_weighted_density/geometry, Polygon or MultiPolygon | instruction | stated |
| Parquet columns + integer dtypes for the two counts | instruction | stated |
| same hex_id set in both files | instruction ("share exactly the same set") | stated |
| rank unique, starts at 1, ascending rank = descending density | instruction | stated |
| output CRS: canonical set {26331, 26391} | "Nigeria's national grid" category hint + regional convention | inferable |
| 100 m² sliver exclusion | instruction | stated |
| metric-CRS area computation for the threshold | inferable (m² threshold is meaningless in degrees) | inferable |
| top-N base = cells overlapping >= 1 kept polygon | inferable (cells with no overlap have undefined mean density) | inferable |
| area-weighted (not unweighted) mean | instruction ("area-weighted mean population density") | stated |
| density ±5 %, count matches >= 90 %, Jaccard >= 0.85, IoU >= 0.95 | grader-internal tolerances | inferable (standard drift margins) |

Factual claims checked: `lagos_landuse.geojson` (5 542 features, EPSG:4326,
columns id/class/pop_density) and `lagos_hex_grid.geojson` (1 782 features,
hex_id) verified on disk; output column names/dtypes verified against the
reference outputs (104 rows, int64 counts). No missing or inaccurate claim.

#### Reference faithfulness
Faithful, re-verified this pass. `reference/solution/generate.py` is
unchanged since authoring: reprojects both inputs to EPSG:26331, filters
< 100 m² polygons, counts per-hex sliver intersections, overlays kept
polygons with the grid, computes the intersection-area-weighted mean,
drops zero-overlap cells, ranks descending with hex_id tie-break, takes
ceil(10 % of eligible) = 104, and writes both files in EPSG:26331. The
4-decimal density rounding is well inside the grader's ±5 % tolerance.
No unrequested operations, no skipped steps, no CRS concerns.

#### Specific findings
- `metadata.yaml` rationale and broken `measured_score` values were stale
  (written for the pre-weights 8-subcheck grader: "8/8", 0.625, 0.875).
  Re-measured under the current weighted 9-subcheck grader:
  no_sliver_filter 12/21 = 0.5714, wrong_density_values 18/21 = 0.8571;
  both still inside their declared `expected_score_range`. Fixed
  unilaterally (measured_score refresh + rationale accuracy).
- `README.md` failure modes 5 and 6 referenced the removed Gate 2 and the
  old hard CRS rejection; broken scores 0.5/0.83 were stale. Fixed
  unilaterally (docs-change).
- `task.json > analyst_notes` pitfalls 3 and 5 referenced the removed
  "structural gate". Refreshed to name the weighted subchecks (no version
  bump needed for analyst_notes).
- `run-20260609-084636Z`: parent `run.json` per-task `score` is null while
  the task's `score.json` holds 0.7143 from the current grader. Runs-index
  sync quirk outside the task directory; not a task defect and not
  evaluator-editable. Recorded here for the infra backlog.
- No HUMAN-REVIEW items this pass.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: rewrote `tolerances.rationale` for the weighted
  9-subcheck grader (total weight 21, canonical set {26331, 26391}, gate-2
  removal note); refreshed `broken_solutions` measured scores 0.625 ->
  0.5714 and 0.875 -> 0.8571 with updated descriptions. Re-grade on
  reference: 1.0. Reason: documentation accuracy after 363aed21/c749e57b/
  501e9a60; measured_score refresh is a Step 4 unilateral action.
- `README.md`: updated failure modes 5/6 (gate-2 and hard-CRS references),
  broken scores, and the "What this task probes" CRS bullet to mention the
  26331/26391 canonical pair. Re-grade on reference: 1.0. Reason: stale
  docs after the grader refactors (docs-change, no version bump).
- `task.json`: refreshed `analyst_notes` pitfalls 3 and 5 ("structural
  gate" -> weighted subchecks). Re-grade on reference: 1.0. Reason:
  analyst_notes accuracy; exempt from version bump per Step 4 rules.
- `coverage.yaml`: bumped `evaluator_run_at`. No slug changes.

No `version` bump this pass: no instruction, grader, inputs, or tolerance
value changed (version stays 3, keeping the June runs' version validity).

#### Proposed but not applied (see HUMAN-REVIEW items)
- None.

#### Tests run
- grader on reference: 1.0 (weight 21/21)
- grader on broken_wrong_format: 0.0
- grader on broken_no_sliver_filter: 0.5714 (12/21)
- grader on broken_wrong_density_values: 0.8571 (18/21)
- pytest: pass (41/41)

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Summary
**RECALIBRATED** — replaced the blunt repo-wide "data-content = weight 3.0,
everything else = 1.0" scheme (commit c749e57b) with a severity-tiered
weighting that separates the persona's *answer* from supporting-correctness
diagnostics and cosmetic structure. Grading-only change; no task.json
version bump.

### Why the uniform scheme was miscalibrated
The persona's actual question is "which cells are the hotspots, and how dense
are they?". Under the old scheme, all six data-content subchecks carried the
same weight (3.0), so a **wrong-answer** failure (wrong top-N cell set, Jaccard
< 0.85) cost the same 3/21 as a diagnostic count mismatch or a per-cell sliver
provenance count. The result: an agent that emitted the **wrong hotspot cells**
(run-1927, 179 rows) scored 0.857, while an agent that picked a
cosmetically-different-but-geometrically-identical CRS (run-2225, EPSG:32631
instead of 26331) scored 0.952 — a gap of only 0.095 between a central-answer
error and a cosmetic label slip. A meaningful mistake was not causing a
meaningful drop.

### Weight changes
| Subcheck | old | new | tier / rationale |
|---|---|---|---|
| hex_id_set_jaccard_vs_reference | 3.0 | **4.0** | Tier 1 — the answer: which cells are the hotspots |
| density_values_match_reference | 3.0 | **4.0** | Tier 1 — the answer: the ranked area-weighted metric |
| cross_file_hex_id_set_matches | 3.0 | **2.0** | Tier 2 — output consistency / hygiene |
| overlap_count_matches_reference | 3.0 | **2.0** | Tier 2 — overlay diagnostic count |
| sliver_count_matches_reference | 3.0 | **2.0** | Tier 2 — sliver-filter traceability count |
| hex_geometries_match | 3.0 | **2.0** | Tier 2 — geometry carrier, not the answer |
| rank_consistent_with_density | 1.0 | 1.0 | Tier 3 — structural (unchanged) |
| crs_is_canonical | 1.0 | 1.0 | Tier 3 — cosmetic CRS label (unchanged) |
| crs_in_meaningful_set | 1.0 | 1.0 | Tier 3 — cosmetic CRS label (unchanged) |

Total weight 21 → **19**. A Tier-1 failure now costs 4/19 ≈ 0.21 (was
3/21 ≈ 0.14); a cosmetic CRS-label slip still costs only 1/19 ≈ 0.05.

### Broken / reference scores before → after
| Case | before | after | severity note |
|---|---|---|---|
| reference | 1.0000 | 1.0000 | stays at ceiling (≥ 0.95) |
| wrong_format | 0.0000 | 0.0000 | gate fail — no answer (most severe) |
| no_sliver_filter | 0.5714 | 0.5789 | skipped the named central step: wrong cells + wrong overlap + wrong sliver counts |
| wrong_density_values | 0.8571 | **0.7895** | one half of the answer (ranked metric) wrong — now a meaningful drop, not a near-pass |

### Ordering check
Monotone and defensible (severe → light):
`wrong_format 0.0 < no_sliver_filter 0.579 ≈ run-084636 0.579 (wrong cells +
wrong density) < run-112430 0.684 (wrong cells + 1 diagnostic) <
wrong_density 0.789 ≈ run-1927 0.789 (one answer-half wrong) < run-2225 0.947
(cosmetic CRS) < reference 1.0`. No disjoint-failure inversions: because
Tier-1 Jaccard is the heaviest single check, every wrong-cells case stays
below the single-half-answer cases despite the Tier-2 down-weighting, and the
cosmetic-CRS case stays at the top.

### Prior-run re-grade (current task version, 9-subcheck grader)
7 completed post-prompt runs re-graded on disk; old (uniform w3) → new (tiered):
| Run | old | new |
|---|---|---|
| run-20260609-084636Z (deepseek-flash; wrong topN + wrong density) | 0.7143 | **0.5789** |
| run-20260608-074701Z (deepseek-flash; perfect, 26391) | 1.0000 | 1.0000 |
| run-20260607-112430Z (gemma4; wrong topN + sliver0) | 0.7143 | 0.6842 |
| run-20260529-0902Z (deepseek-pro; perfect, 26391) | 1.0000 | 1.0000 |
| run-20260528-2332Z (opus; perfect, 26391) | 1.0000 | 1.0000 |
| run-20260528-2225Z (gemma4; perfect geometry, 32631) | 0.8750 | 0.9474 |
| run-20260528-1927Z (opus; wrong topN base) | 0.8571 | 0.7895 |
Notable shifts: the compound-error run-084636 (wrong cells **and** wrong
density) drops the most (0.714 → 0.579), correctly reflecting that both halves
of the answer are wrong; the cosmetic-CRS run-2225 *rises* (0.875 → 0.947) as
the only failing check is now down-weighted relative to the data-content
total. Perfect runs stay at 1.0.

### Reasoning
The two Tier-1 subchecks (cell set + density) are literally the persona's
deliverable; everything else either verifies the pipeline produced that answer
correctly (Tier 2) or is presentation/provenance (Tier 3). The sliver and
overlap counts are kept at Tier 2 rather than demoted to Tier 1-level because
the sliver filter is a named central operation, but they are diagnostics
alongside the answer rather than the answer itself. CRS-label and rank checks
stay at weight 1.0: a valid-but-non-canonical UTM pick is geometrically
identical after reprojection and should cost almost nothing.

### Changes applied
- `grade.py`: weight= edits only (Tier-1 → 4.0, Tier-2 → 2.0, Tier-3 stays 1.0);
  added per-subcheck tier comments and a Weighting block in the module docstring.
  No check logic, thresholds, or gates touched.
- `metadata.yaml`: rewrote the weight-arithmetic prose (total 21 → 19, tier
  table); refreshed broken `measured_score` 0.5714 → 0.5789 and 0.8571 →
  0.7895 with new `expected_score_range` ([0.52, 0.65] and [0.74, 0.84]).
- `README.md`: refreshed stale score fractions (0.57 → 0.58, 0.86 → 0.79,
  ~0.86 → ~0.79) and the weight-3 → Tier-1 (weight-4) / Tier-2 (weight-2)
  subcheck labels.

### Tests run
- grader on reference: 1.0 (weight 19/19)
- grader on broken_wrong_format: 0.0
- grader on broken_no_sliver_filter: 0.5789 (11/19)
- grader on broken_wrong_density_values: 0.7895 (15/19)
- pytest: not-run (orchestrator runs the suite)
