# Implementation notes — dc-l3-vienna-overpass-historical

## Status
completed

## Summary
L3 data-cleaning task comparing Vienna's current and 2014-01-01 administrative district boundaries from Overpass, with name normalisation, per-district symmetric difference, and touches_changed adjacency flagging.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.0 (expected range [0.0, 0.0])
  - wrong_geometry: 0.6 (expected range [0.3, 0.7])
  - wrong_attributes: 0.9 (expected range [0.8, 1.0])
- Second-run output match: bit-identical (both runs fetched within minutes; long-term drift is expected on the current-side snapshot)
- Library tests after task: pass (35/35)

## Failure-mode coverage
- No historical query / wrong date: broken_wrong_geometry (unchanged_area_dominates + per_type_count)
- Name normalisation skipped: principled-reasoning (district_name_set_overlap + unchanged_area_dominates)
- Wrong geometry type: principled-reasoning (Gate 2 rejects non-polygonal)
- Missing required properties: broken_wrong_format (Gate 1 rejects)
- Non-Vienna districts included: principled-reasoning (total_feature_count + district_name_set_overlap)
- Wrong CRS: principled-reasoning (crs_is_wgs84 + coordinates_in_vienna_envelope)
- touches_changed always False: broken_wrong_attributes (touches_changed_accuracy)

## Open issues
- [severity: low] — All 69 reference features have touches_changed=True because every district has at least one micro-sliver of boundary change. This means the flag has no discriminative power in the reference output. A stronger test would require a scenario where some districts have no boundary changes at all, but Vienna's 23 Bezirke all show OSM editing drift.
- [severity: low] — The Gerasdorf bei Wien filtering uses a 50% area overlap threshold, which is heuristic. A more robust filter would cross-reference against a known list of Vienna Bezirke names, but this would be fragile against future OSM name changes.

## Suggested prompt changes
Empty.

## Inventory change proposals
Empty.

## Library extensions
Empty.

## Runtime
~8 minutes (including two reference runs with Overpass API waits)

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
A data-cleaning L3 task probing live Overpass acquisition with the attic
(`[date:...]`) directive, plus attribute-value normalisation across
historical snapshots, per-district symmetric difference, and a touches-based
spatial join. The original instruction (commit `6cbfffa`) named operations
explicitly ("symmetric difference", "cascaded union") and pointed at
`admin_level=9` plus the exact date directive. The README's story (Dr.
Magdalena Reiter, statistical-office historian preparing a 10-year
retrospective) and the inventory row both frame the deliverable as a single
GeoJSON with `added_since_2014` / `removed_since_2014` / `unchanged`
fragments plus a `touches_changed` adjacency flag.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-12 | 6cbfffa | initial-authoring | Initial task (task.json + grader + reference outputs + 3 broken sets + IMPLEMENTATION_NOTES) | Commit msg: introduces the task, reports reference 1.0 and broken scores 0.0/0.6/0.9 |
| 2026-05-13 | 1710715 | prompt-change | Added explicit normalisation recipe to the instruction (strip `Wien` prefix, district numbers, `Bezirk` filler — with worked examples) | Commit msg: "declare exact output schema in prompts to match graders" (schema-and-canonical-vocab sweep across all tasks) |
| 2026-05-13 | 284b843 | docs-change | Added structured `tags` block to `task.json` (region, data_source, formats, crs, geometry_type, operations, themes, quality_issues, scale) | Commit msg: "add structured tags to all 36 task.json files" — derived from inventory axes |
| 2026-05-13 | a3a8d53 | docs-change | Move `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: "Tasks are not eval-specific; promote to top-level benchmark/" |
| 2026-05-13 | 89150101 | docs-change | Added `image-prompt.md` | Commit msg: card-image prompt sweep |
| 2026-05-13 | 1b8dda1 | docs-change | Added `image.webp` (FLUX schnell) | Commit msg: card-image generation sweep |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` via FLUX schnell | Commit msg: image regen sweep |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` via nano-banana-2 | Commit msg: image regen sweep |
| 2026-05-14 | f5d1e91 | prompt-change | Removed worked normalisation recipe from instruction; replaced with a more terse "strip common prefixes, district numbers, and filler words" hint | Commit msg: "Strip deducible information from DC task instructions" (round 1) |
| 2026-05-15 | a78a513 | prompt-change | Further stripped: removed `boundary=administrative` tag, `admin_level=9` hint, the date-directive syntax `[date:...]`, the cascaded-union procedure for `unchanged`, the explicit Wien-prefix examples, and the "filter out non-Vienna municipalities" cue; tightened persona-voice | Commit msg: "Strip deducible information from DC task instructions (round 2)" |
| 2026-05-17 | 6474005 | prompt-change | Rewrote instruction to describe symptoms / desired outcomes rather than named ops; dropped explicit `added_since_2014` / `removed_since_2014` / `unchanged` enum from the instruction | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" |
| 2026-05-17 | db638f4 | prompt-change | Restored explicit `added_since_2014` / `removed_since_2014` / `unchanged` enum values in the instruction (other parts of the nudge removal kept) | Commit msg: "Fix graders and prompts for 6 tasks that regressed after nudge removal — Vienna: restore explicit change_type enum values" |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `to_epsg() == 4326` CRS check with shared `geo_grading.is_wgs84` helper | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package" |
| 2026-05-26 | 29a9ae3 | mixed (docs + grader path) | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`; `reference/` → `reference/solution/`; broken-sets → `reference/failures/`; image assets → `assets/`. Grader updated to reference the new `reference/solution/outputs/` path; no scoring-logic change | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- Strict design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae3, class: mixed — grader path-only). The instruction text and grader semantics have been unchanged since 2026-05-17T19:17:27Z (db638f4); the post-db638f4 commits (f0c244a, 29a9ae3) are mechanical refactors that do not change scoring on identical submitted outputs. Using the strict cutoff, only run-20260526-0748Z (2026-05-26T08:24:02Z) is post-instruction-fix and grader-semantically current.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:24:02Z | 0.0 | done (model-side fail: malformed JSON tool args, never wrote output) | current (post-final-prompt-fix; pre-folder-reorg by ~1h but identical grader semantics) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:11:15Z | 0.0 | done (Gate 2 rejected `added`/`removed`/`unchanged` enum without `_since_2014` suffix) | stale (started ~6h before db638f4 prompt fix restored the suffixed enum) |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T08:00:08Z | 0.0 | done (missing output) | stale (pre-prompt fix; also model-side fail) |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T01:51:18Z | 1.0 | done | stale |
| run-20260516-2248Z | claude-code-opus-basic | 2026-05-16T23:35:57Z | 0.8 | done (district_name jaccard=0 and touches_changed_accuracy=0 — name-normalisation drift) | stale |
| run-20260516-1130Z | claude-code-opus-basic | 2026-05-16T20:03:15Z | 1.0 | done | stale |
| run-20260516-0743Z | claude-code-opus-basic | 2026-05-16T08:00:40Z | 1.0 | done | stale |
| run-20260515-2053Z | claude-code-opus-basic | 2026-05-16T06:18:50Z | 0.9 | done (Vienna envelope just outside on north edge) | stale |
| run-20260515-0926Z | openrouter-deepseek-v4-flash-basic | 2026-05-15T11:01:50Z | 0.0 | done | stale |
| run-20260515-0624Z | claude-code-opus-basic | 2026-05-15T07:02:30Z | 0.8 | done | stale |
| run-20260514-1554Z | claude-code-opus-basic | 2026-05-14T16:10:13Z | 0.8 | done | stale |
| run-20260514-1245Z | claude-code-opus-basic | 2026-05-14T13:02:14Z | 0.7 | done (per_type and touches_changed_accuracy both partial) | stale |
| run-20260514-0946Z | claude-code-opus-basic | 2026-05-14T09:57:44Z | 1.0 | done | stale |
| run-20260513-0022Z | claude-code-sonnet-basic | 2026-05-13T00:22:51Z | 0.0 | done | stale |
| run-20260512-2227Z | claude-code-sonnet-basic | 2026-05-12T22:27:52Z | 1.0 | done | stale |
| run-20260512-2050Z | openrouter-deepseek-v4-flash-basic | 2026-05-12T20:50:39Z | 1.0 | done | stale |
| run-20260512-1843Z | claude-code-sonnet-basic | 2026-05-12T18:43:00Z | 0.8 | done | stale |
| run-20260512-1716Z | openrouter-deepseek-v4-flash-basic | 2026-05-12T17:16:18Z | failed | model-side max-iterations | stale |
| run-20260512-1537Z | claude-code-sonnet-basic | 2026-05-12T15:37:53Z | 1.0 | done | stale |
| run-20260517-0304Z, run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17 | failed | model-side max-iterations | stale (and model-side anyway) |

(Stale entries are listed for completeness; only the run-20260526 row is `current` evidence.)

#### Verdict
**insufficient-evidence**

The strict design-affecting cutoff (2026-05-26T09:51Z) leaves only a single
post-cutoff run — run-20260526-0748Z, openrouter-gemma4-26b-basic — and that
run is a model-side failure (the model emitted malformed JSON for a `Write`
tool call and never produced an output file; transcript ends after 10 events).
That is not evidence the task is mis-calibrated. The stale run history
nonetheless shows the right shape: capable agents (Claude Opus / Sonnet)
land 0.7-1.0 on the post-db638f4 instruction, with the partial-credit
subchecks falling on real defects (name-normalisation drift,
touches_changed mismatches, Vienna envelope overshoot). The reference
re-grades 1.0; the three broken sets re-grade 0.0 / 0.6 / 0.9 exactly as
the metadata claims. Gates and subchecks behave sensibly.

Two structural observations worth flagging for the human reviewer:

#### Specific findings
- Reference re-grades cleanly at 1.0 (10/10 subchecks). All three broken sets
  re-grade exactly at their `metadata.yaml > measured_score`
  (`wrong_format` 0.0, `wrong_geometry` 0.6, `wrong_attributes` 0.9). The
  grader is internally consistent.
- The grader computes feature areas in geographic (EPSG:4326) coordinates and
  emits geopandas `UserWarning`s on every run ("Geometry is in a geographic
  CRS. Results from 'area' are likely incorrect."). For this task the area
  ratios (`unchanged_area_dominates`, `changed_area_is_small`) are
  scale-invariant — they only compare proportions of the same set, so the
  geographic-area distortion cancels. This is a working but non-best-practice
  choice; the existing author note explicitly says the unchanged-dominance
  check is principled because Vienna's Bezirke have not changed since 1955.
  Not a bug, but human reviewers should know it's intentional.
  <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="low" -->
  Should the area-based subchecks reproject to a projected CRS for a tighter
  numerical interpretation, or is the current scale-invariant approach (which
  produces user warnings on every grader invocation) preferred? Functionally
  the checks pass on the reference and correctly distinguish broken outputs,
  so this is preference / cleanliness, not correctness.
- The task.json tag `"scale": "medium"` and the inventory row
  ("Data scale: Medium (~10² administrative polygons across the comparison)")
  contradict the thesis `data-scale-table`, which defines `medium` as
  10⁴-10⁵ features. The reference output has 69 features (23 districts × 3
  change_types), which is `small` (10²) by the thesis definition. The
  inventory row internally contradicts itself ("Medium" vs "~10²"). My
  `coverage.yaml` uses the thesis-correct `small` slug.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  The inventory row labels this task "Medium" but quantifies it as ~10² —
  matching the thesis `small` band. Either the inventory label should be
  corrected to "Small", or the scale axis interpretation should be
  documented as "scale of the input universe (all admin features in both
  snapshots before differencing)" rather than the output. Coverage.yaml is
  written with `small` to match the thesis table; please confirm.
- Single-run evidence under the strict cutoff is insufficient to make a
  calibration claim. The only post-cutoff run is a model-side
  malformed-tool-args failure (Gemma 4 26B unable to emit valid JSON for a
  large `Write` call). Per task-evaluator-prompt.md §2d, model-side failures
  are not task problems and do not motivate task changes. No flag.
- Instruction is calibrated relative to the design rules: output schema
  (filename + CRS + geometry type + property names + enum values) is stated
  explicitly per the schema-in-prompt convention; named operations
  (symmetric difference, cascaded union, spatial-join touches) and the
  `admin_level=9` / `[date:...]` syntax have been deliberately stripped.
  No further gifts to remove. No further hints to add.

### 3. Changes applied this run

#### Unilateral edits
- None. The grader scores cleanly, broken-set scores match `metadata.yaml`
  exactly, and the only post-cutoff run was a model-side failure with no
  output, so there is no task-side defect to fix.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — grader-miscalibration-suspected — area subchecks run in EPSG:4326
  and emit per-run geopandas warnings; scale-invariant by construction but
  cosmetically noisy. Decision: leave alone (changes grader semantics).
- HR-002 — inventory-mismatch — inventory says "Medium" with "~10²"; thesis
  `data-scale-table` says `medium` is 10⁴-10⁵. Coverage written as `small`.

#### Tests run
- grader on reference: 1.0 (10 / 10 subchecks pass)
- grader on broken_wrong_format: 0.0 (matches measured_score)
- grader on broken_wrong_geometry: 0.6 (matches measured_score)
- grader on broken_wrong_attributes: 0.9 (matches measured_score)
- pytest: pass (35 / 35)

---

## Evaluator review 2026-05-26 (second pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits touched this task since the prior evaluator block (commit
`801523652b4a47fdc762fc2f1f08f92287c1a6ee`, 2026-05-26T13:12:49Z, which was
the prior evaluator's own artefact commit). The complete design-history change
log is reconstructed in the prior evaluator-review block above and is unchanged;
the most recent design-affecting commit remains `29a9ae3` (folder reorg, grader
path-only) at 2026-05-26T09:51:37Z (UTC), and the most recent
instruction-/grader-semantics commit remains `db638f4` (2026-05-17T19:17:27Z,
restored the explicit `*_since_2014` change_type enum). I re-confirmed via
`git show 29a9ae3 -- .../grade.py` that 29a9ae3's only grader edit is the
`reference/outputs/` → `reference/solution/outputs/` path string; no scoring
logic changed.

### 2. Current-state review

This pass exists because two fresh runs were added after the prior evaluation,
which lifts the evidence base above the prior `insufficient-evidence` threshold.

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae3, class: mixed —
  grader path-only; no scoring-logic change). Instruction/grader-semantics have
  been stable since 2026-05-17T19:17:27Z (db638f4).

#### Runs considered
| Run | Adapter (family) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic (claude-code) | 2026-05-26T17:53:30Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-26T19:22:26Z | 0.0 | done (model-side fail: 5 stub features) | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-26T08:24:02Z | 0.0 | done (model-side fail: malformed JSON, no output) | current (pre-reorg by ~1h, identical grader semantics) |

(All pre-2026-05-26 runs remain stale per the prior block's footnote and are
not re-listed here; they predate the 29a9ae3 cutoff.)

#### Verdict
**calibrated**

There are now two `current` runs from two different agent families. The capable
agent (Claude Opus, run-20260526-1753Z) scored 1.0 with a genuinely correct
output — 70 MultiPolygon features, real normalised Bezirk names (Alsergrund,
Brigittenau, Döbling, …), the expected ~23-per-change_type balance, district-name
Jaccard 0.958, coverage IoU 0.959, touches_changed accuracy 1.0 on 69 matched
features, unchanged-area fraction 0.958. The weak agent (Gemma 4 26B,
run-20260526-1922Z) scored 0.0, but on inspection its output is a degenerate
stub: 5 features carrying fabricated names ("district1".."district4") — the model
never executed the real Overpass-fetch-and-difference pipeline. The grader
correctly rejects it at Gate 2 ("only 5 features; expected >= 20"). That is a
model-side failure (per §2d, not a task defect), not grader over-strictness — the
output is plainly wrong, not correct-but-rejected. Scores therefore span 0.0–1.0
across agents of differing capability, the 1.0 falls on a verifiably-correct
output, and the 0.0 falls on a verifiably-incomplete one. This is the calibrated
shape the L1≫L2≫L3 gradient expects for an L3 live-data task.

The grader is internally consistent: reference re-grades 1.0 (10/10), and the
three broken sets re-grade exactly at their declared `measured_score`
(`wrong_format` 0.0, `wrong_geometry` 0.6, `wrong_attributes` 0.9 — three
distinct ranges). pytest 35/35. No `too-easy` concern: not every current run
scored ≥0.95 (Gemma is 0.0), and the instruction has already had its named-op /
`admin_level=9` / `[date:...]` gifts stripped across commits a78a513, 64740d0,
6474005 — only the necessary output-schema contract (filename, CRS, geometry
type, property names, change_type enum) remains, which is the redundant-schema
safety net the design rules require.

#### Specific findings
- Reference re-grades 1.0; broken sets re-grade 0.0 / 0.6 / 0.9 matching
  `metadata.yaml > broken_solutions > measured_score`. Grader has resolution and
  is collusion-safe. No change.
- The opus 1.0 output retained "Gerasdorf bei Wien" (24 distinct names, 70
  features vs the reference's 23 / 69) because it did not apply the
  non-Vienna-municipality filter. The drift-tolerant subchecks absorbed this
  (total count 70 vs 69 within ±20%; per-type within ±25%; name Jaccard 0.958 ≥
  0.75). This is the intended tolerance behaviour, not a leak — the deliverable
  is still substantively correct.
- HR-001 (carried forward, unchanged): the area subchecks
  (`unchanged_area_dominates`, `changed_area_is_small`) compute `.area` on
  EPSG:4326 geometries and emit a geopandas `UserWarning` on every grade
  invocation (confirmed at grade.py:220-221, 294, 297, 299). The ratios are
  scale-invariant (numerator and denominator share the same geographic
  distortion), so the checks are correct and pass on the reference / distinguish
  broken outputs, but the warnings are cosmetically noisy. Editing this changes
  grader semantics, so I do not apply it unilaterally.
  <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="low" -->
  Confirm whether the area subchecks should reproject to a projected CRS to
  silence the per-grade geopandas warnings, or whether the current
  scale-invariant geographic-area approach is the preferred design.
- HR-002 (carried forward, unchanged): the inventory row labels this task
  data-scale "Medium" while quantifying it as "~10² administrative polygons";
  the thesis `data-scale-table` defines `medium` as 10⁴–10⁵ features. The
  reference output has 69 features (23 Bezirke × 3 change_types) → `small` per
  the thesis. `task.json > tags.scale` is `"medium"`. `coverage.yaml` uses
  `small` (thesis-correct). I cannot edit `inventory.md`, and changing
  `task.json` tags is borderline (it is a design-contract field), so I flag.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  Either correct the inventory label to "Small", or document the scale axis as
  measuring the input universe rather than the output feature count. coverage.yaml
  uses `small`; please confirm and reconcile `task.json > tags.scale`.

### 3. Changes applied this run

#### Unilateral edits
- None. The verdict moved from `insufficient-evidence` to `calibrated` purely on
  the strength of the two new current runs; the grader, reference, broken sets,
  instruction, and coverage tags are all already correct. `coverage.yaml` is
  refreshed with the new `evaluator_run_at` timestamp only (no slug changes).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — grader-miscalibration-suspected — area subchecks run in EPSG:4326 and
  emit per-grade geopandas warnings; scale-invariant by construction. Leave
  alone (changes grader semantics).
- HR-002 — inventory-mismatch — inventory says "Medium (~10²)"; thesis `medium`
  is 10⁴–10⁵. coverage.yaml written as `small`; task.json tag left unchanged
  (borderline design-contract edit).

#### Tests run
- grader on reference: 1.0 (10 / 10 subchecks pass)
- grader on broken_wrong_format: 0.0 (matches measured_score)
- grader on broken_wrong_geometry: 0.6 (matches measured_score)
- grader on broken_wrong_attributes: 0.9 (matches measured_score)
- pytest: pass (35 / 35)

---

## Evaluator review 2026-05-27 (third pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/dc-l3-vienna-overpass-historical/`
since the prior evaluator-review block (the second-pass artefact commit
`a7318fdadaa7a18a544a7a3d2f3de0d6c80a1caa`, 2026-05-26T20:22:28Z). I verified
this with `git log a7318fd..HEAD -- benchmark/tasks/dc-l3-vienna-overpass-historical/`
(empty). The 24 commits between `a7318fd` and HEAD (`93af65a`) are all evaluator
passes on *other* tasks. The complete design-history change log is reconstructed
in the first evaluator-review block above and remains accurate; I spot-checked the
referenced shas (`6cbfffa` initial-authoring, `1710715`, `284b843`, `64740d0` —
the prior log's `6474005` is a transcription typo for `64740d0`, the nudge-removal
commit). The most recent design-affecting commit remains `29a9ae3` (folder reorg,
grader path-only, no scoring-logic change) at 2026-05-26T09:51:37Z (UTC);
instruction/grader semantics have been stable since `db638f4`
(2026-05-17T19:17:27Z).

### 2. Current-state review

This is a re-confirmation pass: no new commits and no new runs were added since
the second pass, so the evidence base is unchanged.

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae3, class: mixed —
  grader path-only; no scoring-logic change). Instruction/grader-semantics stable
  since 2026-05-17T19:17:27Z (db638f4).

#### Runs considered
| Run | Adapter (family) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus (claude-code) | 2026-05-26T18:39:36Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-26T19:29:06Z | 0.0 | done (model-side fail: 5 stub features) | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-26T08:24:02Z | 0.0 | done (model-side fail: no output written) | stale by strict rule (started ~1.5h before the 09:51Z cutoff; identical grader semantics — listed for completeness) |

(No new runs exist for this task since the second pass; the latest run dir is
`run-20260526-1922Z`. All pre-2026-05-26 runs remain stale and are catalogued in
the first evaluator-review block above.)

#### Verdict
**calibrated**

The verdict is unchanged from the second pass and rests on the same two
unambiguously-current cross-family runs. The capable agent (Claude Opus,
run-20260526-1753Z) scored 1.0 on a verifiably-correct output — 70 MultiPolygon
features, real normalised Bezirk names, district-name Jaccard 0.958, coverage IoU
0.959, unchanged-area fraction 0.958, touches_changed accuracy 1.0, total count 70
vs ref 69 within ±20%. The weak agent (Gemma 4 26B, run-20260526-1922Z) scored
0.0, but on inspection its output is a degenerate 5-feature stub carrying
fabricated placeholder names (`district1`..`district4`) — the model never executed
the real Overpass-fetch-and-difference pipeline. The grader correctly rejects it
at Gate 2 ("only 5 features; expected >= 20"). That is a model-side failure (per
task-evaluator-prompt.md §2d), not grader over-strictness. The third
(strictly-stale) Gemma run wrote no output at all — also model-side.

Scores span 0.0–1.0 across agents of differing capability, the 1.0 falls on a
verifiably-correct output, the 0.0 falls on a verifiably-incomplete one. This is
the calibrated shape an L3 live-data task should show. Re-running this pass:
reference re-grades 1.0 (10/10 subchecks); the three broken sets re-grade exactly
0.0 / 0.6 / 0.9 (three distinct ranges, matching `metadata.yaml > measured_score`);
pytest 35/35. No `too-easy` concern (Gemma is 0.0, and the instruction's named-op
/ `admin_level=9` / `[date:...]` gifts were stripped across commits a78a513 /
64740d0 / 6474005, leaving only the redundant output-schema contract).

#### CRS / format consistency (Step 2c-CRS)
Output is EPSG:4326 GeoJSON MultiPolygon throughout: the reference output,
`task.json > expected_outputs[]`, and the README all agree. The grader does **not**
do a one-sided reprojection — it computes `.area` on both the submission and the
reference in EPSG:4326 and only ever compares *ratios* of the same set (so the
geographic-area distortion cancels identically on both sides). No CRS/format
inconsistency.

#### Specific findings
- Reference re-grades 1.0; broken sets re-grade 0.0 / 0.6 / 0.9 matching
  `metadata.yaml > broken_solutions > measured_score`. Grader has resolution and
  is collusion-safe. No change.
- The opus 1.0 output retained "Gerasdorf bei Wien" (24 distinct names, 70
  features vs the reference's 23 / 69) because it skipped the
  non-Vienna-municipality filter. The drift-tolerant subchecks absorbed this as
  designed (count within ±20%, name Jaccard 0.958 ≥ 0.75). Intended tolerance
  behaviour, not a leak.
- HR-001 (carried forward, unchanged): the area subchecks
  (`unchanged_area_dominates`, `changed_area_is_small`) compute `.area` on
  EPSG:4326 geometries and emit a geopandas `UserWarning` on every grade
  invocation (re-confirmed this pass: 5 UserWarning lines on the reference grade).
  The ratios are scale-invariant, so the checks are correct and pass on the
  reference / distinguish broken outputs; the warnings are cosmetic. Editing this
  changes grader semantics, so it is not applied unilaterally.
  <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="low" -->
  Confirm whether the area subchecks should reproject to a projected CRS to silence
  the per-grade geopandas warnings, or whether the current scale-invariant
  geographic-area approach is the preferred design.
- HR-002 (carried forward, unchanged): the inventory row labels this task
  data-scale "Medium" while quantifying it as "~10² administrative polygons"; the
  thesis `data-scale-table` defines `medium` as 10⁴–10⁵ features. The reference
  output has 69 features (23 Bezirke × 3 change_types) → `small` per the thesis.
  `task.json > tags.scale` is `"medium"`. `coverage.yaml` uses `small`
  (thesis-correct). `inventory.md` is out of my edit scope and changing the
  `task.json` tag is a borderline design-contract edit, so I flag rather than fix.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  Either correct the inventory label to "Small", or document the scale axis as
  measuring the input universe rather than the output feature count. coverage.yaml
  uses `small`; please confirm and reconcile `task.json > tags.scale`.
- Instruction remains calibrated relative to the design rules: the output-schema
  contract (filename, CRS, geometry type, property names, change_type enum) is
  stated explicitly per the schema-in-prompt convention; named operations and the
  `admin_level=9` / `[date:...]` syntax remain stripped. No further gifts to remove,
  no necessary hints missing.

### 3. Changes applied this run

#### Unilateral edits
- None. No new commits and no new runs since the second pass; the grader,
  reference, broken sets, instruction, and coverage tags are all already correct.
  `coverage.yaml` is refreshed with a new `evaluator_run_at` timestamp only (no
  slug changes).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — grader-miscalibration-suspected — area subchecks run in EPSG:4326 and
  emit per-grade geopandas warnings; scale-invariant by construction. Leave alone
  (changes grader semantics).
- HR-002 — inventory-mismatch — inventory says "Medium (~10²)"; thesis `medium` is
  10⁴–10⁵. coverage.yaml written as `small`; task.json tag left unchanged
  (borderline design-contract edit).

#### Tests run
- grader on reference: 1.0 (10 / 10 subchecks pass)
- grader on broken_wrong_format: 0.0 (matches measured_score)
- grader on broken_wrong_geometry: 0.6 (matches measured_score)
- grader on broken_wrong_attributes: 0.9 (matches measured_score)
- pytest: pass (35 / 35)

---

## Evaluator review 2026-05-28 (fourth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

One new commit has touched `benchmark/tasks/dc-l3-vienna-overpass-historical/`
since the prior evaluator-review block (third-pass artefact commit
`1e8ede83`, 2026-05-27T15:09:09Z):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342be | docs-change | Drops the unused `prompt_version: "2026-05-12-a"` line from `metadata.yaml`. No prompt, grader, tolerances, input, reference, or broken-set change. | Commit msg: "Add task content versioning; drop unused prompt_version" — repo-wide sweep introducing `task.json.version` and removing the orphan `prompt_version` field. |

The repo-wide commit also adds the integer `version` field semantics to
`task.json` (initially absent → implicitly v1), but did not write `version`
into this task's `task.json` itself. This pass applies the first unilateral
edit that meaningfully changes the agent-visible prompt, so per the new
versioning rule I add `"version": 2`.

The complete pre-622342be design-history change log is reconstructed in the
first evaluator-review block above and remains accurate. The most recent
scoring-affecting commit is still `29a9ae3` (folder reorg, grader path-only,
2026-05-26T09:51:37Z); instruction/grader semantics have been stable since
`db638f4` (2026-05-17T19:17:27Z).

### 2. Current-state review

This pass exists because (a) four fresh runs were added since the third
pass and (b) the new repo-wide rule "strip any CRS mention when the output
is GeoJSON" (task-evaluator-prompt.md Step 4) applies unilaterally to this
task's instruction, which still carried a redundant `EPSG:4326` next to the
`.geojson` filename.

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae3, class:
  mixed — grader path-only; no scoring-logic change). The 2026-05-28
  metadata.yaml prompt_version drop (622342be) is `docs-change`: it removes
  an unused field with no scoring impact, so it does not move the cutoff.
  Instruction/grader-semantics have been stable since 2026-05-17T19:17:27Z
  (db638f4).

#### Runs considered
| Run | Adapter (family) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-28T03:28:42Z | 0.0 | done (model-side fail: 7-feature stub, Gate 2 reject) | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-code) | 2026-05-28T01:43:54Z | 0.9 | done (per_type_feature_count partial: 19/16 added/removed vs ref 23/23 — real OSM drift) | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-27T23:39:28Z | 0.0 | done (model-side fail: no output file) | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-code) | 2026-05-27T20:43:40Z | 0.8 | done (district_name_set_overlap=0 + touches_changed_accuracy=0 — lowercased + ß→ss normalisation diverges from reference's Title-case + diacritics) | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-26T19:22:26Z | 0.0 | done (model-side fail: 5 stub features) | current |
| run-20260526-1753Z | claude-code-opus-basic (claude-code) | 2026-05-26T17:53:30Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-26T08:24:02Z | 0.0 | done (model-side fail: no output) | current (pre-reorg by ~1.5h, identical grader semantics) |

(All pre-2026-05-26 runs remain stale and are catalogued in the first
evaluator-review block above.)

#### CRS / format consistency (Step 2c-CRS)
Output is EPSG:4326 GeoJSON MultiPolygon throughout: the reference output,
`task.json > expected_outputs[]`, and the README all agree. After this
pass's edit, the instruction no longer states `EPSG:4326` (GeoJSON pins
WGS84 by RFC 7946; this is what the Step 4 strip rule covers). The grader
does **not** do a one-sided reprojection; it computes `.area` on both the
submission and the reference in EPSG:4326 and compares *ratios* of the
same set, so the geographic-area distortion cancels identically on both
sides. No CRS/format inconsistency.

#### Verdict
**calibrated**

Across seven current cross-family runs, scores span 0.0–1.0. The capable
agent (Claude Opus) lands 0.8, 0.9, 1.0 on three independent runs — partial
credit lining up with real defects (district-name normalisation drift,
per-type count drift from live OSM editing). The weak agent (Gemma 4 26B)
scores 0.0 on all four runs, in each case for model-side reasons: no output
written, or 5–7 stub features carrying fabricated placeholder names. The
grader correctly Gate-2-rejects the stubs ("only N features; expected >= 20")
and the missing-output run at Gate 1. This is the calibrated shape an L3
live-data task should show: full credit possible, partial credit calibrated
to real defects, weak agents fail visibly and correctly.

Re-running the calibration tests: reference re-grades 1.0 (10/10 subchecks);
the three broken sets re-grade exactly 0.0 / 0.6 / 0.9 (matching
`metadata.yaml > broken_solutions > measured_score`, three distinct ranges);
pytest 41/41. No `too-easy` concern (Gemma is 0.0; opus shows partial-credit
runs); no `too-strict` concern (every observed below-1.0 on a capable agent
points at a real defect, not a grader miscalibration).

#### Specific findings
- Reference re-grades 1.0; broken sets re-grade 0.0 / 0.6 / 0.9 matching
  `metadata.yaml`. Grader has resolution and is collusion-safe. No change.
- The opus run-20260527-2016Z 0.8 output normalised district names by
  lowercasing + replacing `ß` with `ss` (`landstrasse` vs reference
  `Landstraße`). The `district_name_set_overlap` Jaccard drops to 0,
  cascading to `touches_changed_accuracy=0` because the (change_type,
  district_name) match key fails on every feature. The instruction says
  "district_name (normalised)" without fixing a normalisation form. This is
  a `prompt-vs-grader-judgment` shape — the agent's normalisation is
  internally consistent and matches both snapshots, but the grader compares
  to the reference's Title-case + diacritic-preserving choice. I do **not**
  resolve this unilaterally per Step 4 ("Resolve a borderline
  prompt-vs-grader call yourself" is forbidden). The drift-tolerant
  thresholds already absorb 0.8 as partial credit, which is reasonable for
  the failure mode.
  <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" -->
  The instruction asks for "district_name (normalised)" without fixing a
  normalisation form; the grader compares to the reference's Title-case +
  diacritic-preserving names. Should the instruction add a canonical-form
  hint (e.g. "match the current snapshot's casing and diacritics"), should
  the grader compare names case-folded + diacritic-stripped, or is the
  current 0.8 partial-credit shape (district_name_set_overlap + the cascaded
  touches_changed_accuracy fail) the intended drift signal?
- The opus run-20260528-0113Z 0.9 output failed only
  `per_type_feature_count` (sub=19/16 added/removed vs ref=23/23) because
  live OSM has reverted some of the 2014-vs-current micro-edits since the
  reference was generated. The ±25% per-type tolerance just barely missed
  on the removed bucket (23 → 16 is a 30% drop). This is the expected
  shape of an L3 drift-sensitive task and is the kind of partial-credit the
  rubric is designed to produce; not a calibration defect.
- HR-002 carried forward from the first/second/third pass (area subchecks
  on EPSG:4326 geometries emit per-grade geopandas warnings; scale-invariant
  by construction). Re-confirmed unchanged this pass.
  <!-- HUMAN-REVIEW id="HR-002" category="grader-miscalibration-suspected" severity="low" -->
  Confirm whether the area subchecks should reproject to a projected CRS to
  silence the per-grade geopandas warnings, or whether the current
  scale-invariant geographic-area approach is the preferred design.
- HR-003 carried forward from the first/second/third pass (inventory row
  labels this "Medium (~10²)"; thesis `medium` is 10⁴–10⁵; coverage.yaml
  uses thesis-correct `small`; task.json `tags.scale="medium"` left
  unchanged). Re-confirmed unchanged this pass.
  <!-- HUMAN-REVIEW id="HR-003" category="inventory-mismatch" severity="low" -->
  Either correct the inventory label to "Small", or document the scale axis
  as measuring the input universe rather than the output feature count.
  coverage.yaml uses `small`; please confirm and reconcile
  `task.json > tags.scale`.
- Instruction is calibrated after this pass's edit: the redundant
  `EPSG:4326` next to a `.geojson` filename is removed (RFC 7946 pins
  WGS84); the output-schema contract (filename, geometry type, property
  names, change_type enum) is stated explicitly per the schema-in-prompt
  convention; named operations and the `admin_level=9` / `[date:...]`
  syntax remain stripped from prior commits. No further gifts to remove,
  no necessary hints missing.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: stripped redundant `EPSG:4326` from the instruction's output
  clause (now reads "Output vienna_boundary_changes.geojson, MultiPolygon,
  each feature with …"). Re-grade on reference: 1.0 (10/10). Reason:
  Step 4 "Strip any CRS mention when the output is GeoJSON" — RFC 7946
  pins WGS84; the `expected_outputs[].crs` + grader CRS gate already
  enforce the contract. Mechanical, not a `prompt-vs-grader-judgment` call.
- `task.json`: added `"version": 2` (was implicitly v1, no prior field).
  Per Step 4 the first unilateral edit changing the agent-visible prompt
  in an evaluator-review block must bump `version`.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — district-name normalisation form is
  not pinned by the prompt; grader compares against reference's Title-case
  + diacritic-preserving choice. Borderline; flagged not fixed.
- HR-002 — grader-miscalibration-suspected — area subchecks run in
  EPSG:4326 and emit per-grade geopandas warnings; scale-invariant by
  construction. Leave alone (changes grader semantics).
- HR-003 — inventory-mismatch — inventory says "Medium (~10²)"; thesis
  `medium` is 10⁴–10⁵. coverage.yaml written as `small`; task.json tag left
  unchanged (borderline design-contract edit).

#### Tests run
- grader on reference: 1.0 (10 / 10 subchecks pass)
- grader on broken_wrong_format: 0.0 (matches measured_score)
- grader on broken_wrong_geometry: 0.6 (matches measured_score)
- grader on broken_wrong_attributes: 0.9 (matches measured_score)
- pytest: pass (41 / 41)

---

## Evaluator review 2026-06-06 (fifth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/dc-l3-vienna-overpass-historical/`
since the fourth-pass artefact commit `c1e83f59` (2026-05-28T13:57:07Z).
`git log c1e83f5..HEAD -- benchmark/tasks/dc-l3-vienna-overpass-historical/`
is empty. The complete design-history change log is reconstructed in the
prior evaluator-review blocks above and remains accurate. The most recent
scoring-affecting commit is still `29a9ae3` (folder reorg, grader path-only,
2026-05-26T09:51:37Z); instruction/grader semantics have been stable since
`db638f4` (2026-05-17T19:17:27Z); the fourth pass added `version: 2` and
stripped redundant `EPSG:4326` from the instruction.

### 2. Current-state review

This pass exists because nine fresh runs were added since the fourth pass
and because `task.json` was missing `analyst_notes` (per Step 4 the
evaluator must author it when absent).

#### Cutoff
- design-affecting cutoff: 2026-05-28T13:57:07Z (commit c1e83f59, class:
  prompt-change — fourth-pass instruction edit stripping the redundant
  `EPSG:4326`). All runs started after this timestamp are `current`.

#### Runs considered
| Run | Adapter (family) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1334Z | openrouter-gemma4-26b-detailed (openrouter) | 2026-06-06T13:56:29Z | n/a | cancelled before start | current (no signal) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed (openrouter) | 2026-06-06T11:43:48Z | 0.0 | done (model-side: no output) | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed (openrouter) | 2026-06-06T09:57:35Z | failed | docker exec timeout | current (model-side / harness) |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic (openrouter) | 2026-05-31T11:35:13Z | failed | max iterations exceeded (100) | current (model-side) |
| run-20260529-0109Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-29T01:24:10Z | 0.0 | done (model-side: 6-feature stub, Gate 2 reject) | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-code) | 2026-05-28T23:50:19Z | 0.8 | done (district_name Jaccard=0 → cascaded touches_changed=0; doebling vs Döbling) | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-28T22:37:13Z | 0.0 | done (model-side: no output) | current |
| run-20260528-1927Z | claude-code-opus-basic (claude-code) | 2026-05-28T19:46:59Z | 0.8 | done (district_name Jaccard=0 → cascaded touches_changed=0; dobling vs Döbling) | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic (openrouter) | 2026-05-28T16:51:45Z | 0.0 | done (model-side: no output) | current |

(All pre-2026-05-28T13:57Z runs are now strictly stale by the fourth-pass
cutoff and are catalogued in the prior evaluator-review blocks.)

#### CRS / format consistency (Step 2c-CRS)
Output is GeoJSON MultiPolygon (WGS84 by RFC 7946) throughout: the
reference output, `task.json > expected_outputs[]`, and the README all
agree. The grader does not do a one-sided reprojection; it computes
`.area` on both submission and reference in EPSG:4326 and compares
*ratios* of the same set, so geographic-area distortion cancels
identically on both sides. No CRS/format inconsistency.

#### Verdict
**calibrated**

Across nine current runs, scores span 0.0–0.8 (no 1.0 this pass, but the
0.8s are partial credit on real defects, not grader over-strictness).
Both Claude Opus runs scored 0.8 with exactly the same failure mode:
ASCII-folding district names (`Döbling` → `dobling` in run-20260528-1927Z,
`Döbling` → `doebling` in run-20260528-2332Z) collapses the
`district_name_set_overlap` Jaccard to 0, which cascades into
`touches_changed_accuracy=0` because the (change_type, district_name)
match key fails on every feature. The other eight subchecks pass — feature
count, per-type counts (23/23/23), coverage IoU 1.0, unchanged area
fraction 0.999, changed area fraction 0.0008. This is the exact
prompt-vs-grader-judgment shape carried as HR-001 in the fourth pass, now
observed twice more in independent runs. The shape is consistent: the
prompt says "normalise [district names] to match" without fixing a target
form, so the agent picks a fold-and-lowercase normalisation that is
internally consistent but disagrees with the reference's
diacritics-preserving Title-case. The drift-tolerant rubric absorbs this
as 0.8, which is the intended partial-credit behaviour.

The remaining seven current runs are all model-side failures: no output
written (Gemma 4 26B and 4 26B-detailed), 6-feature stubs (Gemma 4 26B),
max-iterations exceeded (DeepSeek V4 Pro), or harness `docker exec`
timeouts. Per task-evaluator-prompt.md §2d, model-side failures are not
task problems. The grader correctly rejects degenerate stubs at Gate 2.

Re-running the calibration tests: reference re-grades 1.0 (10/10
subchecks); the three broken sets re-grade exactly 0.0 / 0.6 / 0.9
(matching `metadata.yaml > broken_solutions > measured_score`, three
distinct ranges); pytest 41/41. No `too-easy` concern (no current run
≥0.95); no `too-strict` concern (every observed below-1.0 on a capable
agent points at a real defect — district-name normalisation drift).

#### Specific findings
- Reference re-grades 1.0; broken sets re-grade 0.0 / 0.6 / 0.9 matching
  `metadata.yaml`. Grader has resolution and is collusion-safe.
- HR-001 from the fourth pass (prompt-vs-grader-judgment on district-name
  normalisation form) is now observed in two more independent opus runs
  (run-20260528-1927Z and run-20260528-2332Z, both 0.8). The signal has
  become more robust: this normalisation-form disagreement is a recurring
  drift, not a one-off. Still flagged not fixed — the call between "pin
  canonical form in prompt", "case-fold + diacritic-strip in grader", or
  "accept 0.8 as the intended drift signal" is a judgment the evaluator
  cannot resolve unilaterally per Step 4.
  <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" -->
  Two more opus runs (run-20260528-1927Z, run-20260528-2332Z) reproduce
  the fourth-pass HR finding: lowercased / ASCII-folded district names
  collapse `district_name_set_overlap` to 0 and cascade into
  `touches_changed_accuracy=0`, capping the score at 0.8. Should the
  instruction add a canonical-form hint (e.g. "use the current snapshot's
  casing and diacritics"), should the grader case-fold and strip
  diacritics before comparing, or is the 0.8 partial-credit shape the
  intended drift signal? Three independent opus runs now exhibit this.
- HR-002 carried forward (area subchecks on EPSG:4326 emit per-grade
  geopandas warnings; scale-invariant by construction). Re-confirmed this
  pass; not applied unilaterally because it changes grader semantics.
  <!-- HUMAN-REVIEW id="HR-002" category="grader-miscalibration-suspected" severity="low" -->
  Confirm whether the area subchecks should reproject to a projected CRS
  to silence the per-grade geopandas warnings, or whether the current
  scale-invariant geographic-area approach is the preferred design.
- HR-003 carried forward (inventory says "Medium (~10²)"; thesis `medium`
  is 10⁴–10⁵; coverage.yaml uses thesis-correct `small`; task.json
  `tags.scale="medium"` left unchanged). Re-confirmed unchanged this pass.
  <!-- HUMAN-REVIEW id="HR-003" category="inventory-mismatch" severity="low" -->
  Either correct the inventory label to "Small", or document the scale
  axis as measuring the input universe rather than the output feature
  count. coverage.yaml uses `small`; please confirm and reconcile
  `task.json > tags.scale`.
- `task.json.analyst_notes` was missing; authored this pass with the
  hidden gotchas surfaced (date-directive syntax, Gerasdorf-bei-Wien
  filter, name-normalisation form). Schema-conformant, full sentences,
  no jargon. Does not require a `version` bump (analyst_notes is
  human-facing only, not seen by the agent at run time).

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `analyst_notes` block (description + approach +
  pitfalls). Surfaces the date-directive gotcha, the Gerasdorf-bei-Wien
  filter, and the diacritics-and-casing normalisation pitfall that drives
  HR-001. Re-grade on reference: 1.0 (10/10). Reason: `analyst_notes`
  was absent; Step 4 requires the evaluator to author it. No `version`
  bump (analyst_notes is not seen by the agent).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — district-name normalisation form
  not pinned; now reproduced in three independent opus runs. Borderline
  call between prompt-side hint, grader-side case-fold+strip, or accept
  the 0.8 partial-credit shape as intended drift.
- HR-002 — grader-miscalibration-suspected — area subchecks run in
  EPSG:4326 and emit per-grade geopandas warnings; scale-invariant by
  construction. Leave alone (changes grader semantics).
- HR-003 — inventory-mismatch — inventory says "Medium (~10²)"; thesis
  `medium` is 10⁴–10⁵. coverage.yaml uses `small`; task.json tag left
  unchanged (borderline design-contract edit).

#### Tests run
- grader on reference: 1.0 (10 / 10 subchecks pass)
- grader on broken_wrong_format: 0.0 (matches measured_score)
- grader on broken_wrong_geometry: 0.6 (matches measured_score)
- grader on broken_wrong_attributes: 0.9 (matches measured_score)
- pytest: pass (41 / 41)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- "All three change_type values present" migrated to a new
  `all_change_types_present` subcheck.
- "Geometry types are polygonal (Polygon/MultiPolygon)" migrated to a
  new `geometry_type_polygonal` subcheck.
- "Feature count >= 20" migrated to a new
  `feature_count_plausible` subcheck.
- Subcheck total: 10 → 13.

### Verification
- Reference solution re-graded: 1.0 (13/13 subchecks).

---

## Evaluator review 2026-06-11 (sixth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

Two new commits have touched `benchmark/tasks/dc-l3-vienna-overpass-historical/`
since the fifth-pass artefact commit `61e5b93` (2026-06-06T14:53:45Z):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change | Removed the `structural_correctness` Gate 2 and its early-return; migrated its three checks (all change_type values present, polygonal geometry types, feature count >= 20) to one-point subchecks `all_change_types_present`, `geometry_type_polygonal`, `feature_count_plausible`. Subcheck total 10 -> 13. | Commit msg: benchmark-wide refactor to a single hard gate (`format_schema_valid`); shape-recoverable defects now cost a point each instead of collapsing the score. Documented in the "Manual cleanup 2026-06-06" block above. |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to the seven data-content subchecks (`total_feature_count`, `district_name_set_overlap`, `unchanged_area_dominates`, `overall_coverage_iou`, `per_type_feature_count`, `touches_changed_accuracy`, `changed_area_is_small`); the six schema/structural subchecks stay at 1.0. Score is now sum(weight passed)/sum(weight), denominator 27. | Commit msg: repo-wide sweep weighting data-content subchecks 3x across fio/geo/spa/dc graders. |

The complete pre-existing design-history change log is reconstructed in the
prior evaluator-review blocks above and remains accurate. Instruction text
unchanged since the fourth pass (c1e83f5, version 2).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38Z (commit c749e57, class:
  grader-change — subcheck weighting changes the numeric score of any
  partially-correct submission). Both post-cutoff runs were scored at
  suite SHAs (6510297, ec540aa) whose `task.json` is version 2 == current,
  so they pass the version check too.

#### Runs considered
| Run | Adapter (family) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic (openrouter/deepseek) | 2026-06-09T10:09:48Z | 0.44 | done | current |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed (openrouter/deepseek) | 2026-06-08T09:40:20Z | 0.56 | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed (openrouter/gemma) | 2026-06-07T13:29:06Z | 0.07 | done | stale (pre-c749e57 weighting; post-363aed2) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed (openrouter/gemma) | 2026-06-06T18:08:13Z | 0.0 | done | stale (pre-363aed2 and pre-c749e57) |

(All pre-2026-06-06 runs are catalogued in the prior evaluator-review
blocks and remain stale.)

#### CRS / format consistency (Step 2c-CRS)
Unchanged from prior passes: GeoJSON MultiPolygon, WGS84 by RFC 7946;
reference output, `expected_outputs[]`, and README agree. The grader does
no one-sided reprojection (area ratios computed identically on both sides
in EPSG:4326). Both current runs emitted EPSG:4326 GeoJSON MultiPolygon.
No inconsistency.

#### Verdict
**insufficient-evidence**

Only two runs post-date the c749e57 weighting cutoff and both come from a
single agent family (DeepSeek V4 Flash, basic and gis_detailed prompt
variants). Per Step 2d that is insufficient for a calibration claim. The
two runs nonetheless behave the way the rubric intends: partial credit
lands on real defects, not grader over-strictness.

- run-20260608-074701Z (0.56): output is geometrically sound (coverage IoU
  0.959, unchanged fraction 0.959, changed fraction 0.041, all structural
  subchecks pass) but the agent lowercased every district name
  (`döbling`, `landstraße`, plus `rudolfsheim funfhaus` with the hyphen
  and umlaut dropped) and kept `gerasdorf bei wien`. The lowercasing
  collapses `district_name_set_overlap` to Jaccard 0 and cascades into
  `touches_changed_accuracy` 0/0 matched, exactly the HR-001 shape from
  the fourth and fifth passes, now reproduced in a third model family.
  It also under-produced changed fragments (added 8 / removed 7 vs ref
  23/23), failing `per_type_feature_count` and `total_feature_count`
  (38 vs 69).
- run-20260609-084636Z (0.44): the agent emitted 1,483 features — one per
  raw fragment instead of one MultiPolygon per (district, change_type) —
  failing `total_feature_count` and `per_type_feature_count` (unchanged:
  1437 vs 23), and its fragment geometry is substantively wrong anyway
  (coverage IoU 0.07, unchanged fraction 0.36, changed fraction 0.64),
  failing the two area-dominance subchecks. district-name Jaccard 1.0 and
  touches_changed accuracy 1.0 on the 69 matched keys earned the
  data-content credit it deserved.

Grader internal consistency under the new weighted scheme: reference
re-grades 1.0 (13/13); broken sets re-grade 0.0 / 0.56 / 0.89 — still
three distinct bands and still inside their declared
`expected_score_range`s ([0.0,0.0], [0.3,0.7], [0.8,1.0]). The weighting
commit shifted `wrong_geometry` 0.6 -> 0.56 and `wrong_attributes`
0.9 -> 0.89, so `metadata.yaml > measured_score` is refreshed this pass.
pytest 41/41.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output filename `vienna_boundary_changes.geojson` | instruction | stated |
| required properties change_type / district_name / touches_changed | instruction | stated |
| change_type enum `*_since_2014` / `unchanged` | instruction | stated |
| MultiPolygon geometry | instruction + expected_outputs | stated |
| CRS WGS84 | GeoJSON convention (RFC 7946) | inferable |
| Vienna coordinate envelope | the data itself | inferable |
| touches_changed boolean | instruction ("boolean") | stated |
| unchanged area dominates / changed area small | regional knowledge (Vienna Bezirke stable since 1955) | inferable |
| feature count ~69, per-type ~23 | 23 Bezirke x 3 change types, derivable from data | inferable, but see HR-004 (requires the per-(district, change_type) dissolve) |
| district_name form (Title-case, diacritics preserved) | "normalised" with no target form pinned | missing -> HR-001 (carried) |
| one feature per (district, change_type) | README states it; instruction says "classify each resulting geometry fragment" | missing/ambiguous -> HR-004 (new) |

Factual claims checked: no bundled inputs to verify (live Overpass task);
output filename, property names, and enum values verified against the
reference output schema. No inaccurate claims found.

#### Reference faithfulness
`reference/solution/generate.py` implements the instruction: two Overpass
fetches (current + 2014-01-01 attic), name normalisation, per-district
intersection/difference/symmetric-difference classification,
touches_changed adjacency, GeoJSON output. One reading tension rather than
a deviation: the reference dissolves fragments into one MultiPolygon per
(district, change_type) while the instruction's "classify each resulting
geometry fragment" wording can be read per-fragment — covered by HR-004
below as a prompt-vs-grader judgment, not a reference defect. Otherwise
faithful; no unrequested operations, no skipped steps, CRS choice
appropriate (everything stays in WGS84; grader compares like with like).

#### Specific findings
- Reference re-grades 1.0 (13/13) under the weighted grader; broken sets
  re-grade 0.0 / 0.56 / 0.89, three distinct bands inside their declared
  ranges. `metadata.yaml > measured_score` refreshed accordingly
  (unilateral, no version bump).
- HR-001 (carried from fourth/fifth pass, evidence strengthened): the
  district-name normalisation form is still not pinned by the prompt and
  the grader still compares against the reference's Title-case +
  diacritic-preserving names. Previously seen in three opus runs; now also
  in deepseek run-20260608-074701Z (lowercased names, Jaccard 0, cascaded
  touches_changed_accuracy 0). Four independent runs across two model
  families now show this exact shape.
  <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" -->
  The instruction asks for "district_name (normalised)" without fixing a
  target form; the grader compares to the reference's Title-case +
  diacritic-preserving names, and a lowercase/ASCII-folded but internally
  consistent normalisation loses 6 of 27 weight points (district_name_set_overlap
  + cascaded touches_changed_accuracy). Decide: pin a canonical form in
  the prompt (e.g. "keep the current snapshot's casing and diacritics"),
  case-fold + diacritic-strip in the grader before comparing, or accept
  the partial-credit shape as the intended drift signal. Now reproduced in
  four runs across two model families.
- HR-002 (carried, unchanged): area subchecks (`unchanged_area_dominates`,
  `changed_area_is_small`) compute `.area` on EPSG:4326 geometries and
  emit geopandas UserWarnings each grade; ratios are scale-invariant so
  the checks are correct, the warnings cosmetic.
  <!-- HUMAN-REVIEW id="HR-002" category="grader-miscalibration-suspected" severity="low" -->
  Confirm whether the area subchecks should reproject to a projected CRS
  to silence the per-grade geopandas warnings, or whether the current
  scale-invariant geographic-area approach is the preferred design.
- HR-003 (carried, unchanged): inventory row labels data-scale "Medium"
  while quantifying it as ~10^2 polygons; thesis `data-scale-table`
  defines medium as 10^4-10^5. coverage.yaml uses thesis-correct `small`;
  `task.json > tags.scale` remains "medium".
  <!-- HUMAN-REVIEW id="HR-003" category="inventory-mismatch" severity="low" -->
  Either correct the inventory label to "Small", or document the scale
  axis as measuring the input universe rather than the output feature
  count, and reconcile `task.json > tags.scale`.
- HR-004 (new): the instruction says "Classify each resulting geometry
  fragment by how it changed" and then "Output
  vienna_boundary_changes.geojson, MultiPolygon, each feature with ...",
  but never states that fragments must be dissolved into one MultiPolygon
  feature per (district, change_type). The README pins this ("Each
  (district_name, change_type) pair produces at most one feature") and
  the grader enforces it numerically (total_feature_count 69 +-20%,
  per_type_feature_count 23 +-25%, jointly 6 of 27 weight points).
  run-20260609-084636Z emitted 1,483 per-fragment features and lost both
  count subchecks (its geometry was independently wrong too, so the run is
  not clean evidence of an otherwise-correct submission being punished).
  The "MultiPolygon" output type is a reasonable aggregation hint, but
  "each resulting geometry fragment" actively pulls toward per-fragment
  features. Adding the dissolve requirement to the prompt would be new
  information, which is not a unilateral edit.
  <!-- HUMAN-REVIEW id="HR-004" category="prompt-vs-grader-judgment" severity="low" -->
  Decide whether the instruction should state the aggregation explicitly
  (e.g. "one feature per district and change type") or whether inferring
  the dissolve from the MultiPolygon output type and the per-district
  framing is part of the test. If the former, the wording "classify each
  resulting geometry fragment" should be adjusted at the same time and
  `version` bumped.
- Instruction house style: the prompt is mostly full sentences; the final
  output clause ("Output vienna_boundary_changes.geojson, MultiPolygon,
  each feature with ...") is compressed but was reviewed and accepted by
  the fourth and fifth passes under the same rules. Rewriting it now would
  bump `version` and invalidate the only two current runs for marginal
  register gain; left unchanged. If a human edits the prompt for HR-001 or
  HR-004, fold a full-sentence rewrite of that clause into the same bump.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` for the
  weighted 13-subcheck grader (wrong_geometry 0.6 -> 0.56,
  wrong_attributes 0.9 -> 0.89; wrong_format unchanged at 0.0). Re-grade
  on reference: 1.0. Reason: c749e57 changed the scoring denominator;
  measured_score refresh is an explicitly permitted unilateral edit and
  needs no version bump. Both values remain inside their declared
  expected_score_range.
- `coverage.yaml`: refreshed `evaluator_run_at` only; all slugs
  re-validated against `coverage-vocabulary.yaml`, no slug changes.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — district-name normalisation form
  not pinned; now reproduced in four runs across two model families.
- HR-002 — grader-miscalibration-suspected — area subchecks in EPSG:4326
  emit per-grade geopandas warnings; scale-invariant by construction.
- HR-003 — inventory-mismatch — inventory "Medium (~10^2)" vs thesis
  `medium` = 10^4-10^5; coverage.yaml uses `small`.
- HR-004 — prompt-vs-grader-judgment — per-(district, change_type)
  dissolve enforced by the grader and stated in the README but not in the
  instruction, whose "each resulting geometry fragment" wording pulls the
  other way.

#### Tests run
- grader on reference: 1.0 (13/13 subchecks, weighted)
- grader on broken_wrong_format: 0.0 (matches refreshed measured_score)
- grader on broken_wrong_geometry: 0.5556 (recorded as 0.56)
- grader on broken_wrong_attributes: 0.8889 (recorded as 0.89)
- pytest: pass (41/41)

---

## Weight recalibration 2026-06-14 (grading-only)  (evaluator-commit <pending>)

### Change
**RECALIBRATED.** Replaced the blunt repo-wide `weight=3.0` content sweep
(c749e57) with severity-tiered weights reasoned from what this DC-L3 task
actually tests. The seven data-content subchecks were all at 3.0 and the
six schema/structural ones at 1.0 (flat-3x); they are now split into three
tiers by how central the failure each one catches is. No check logic,
threshold, or gate changed; only `weight=` values. No `task.json` version
bump (grading-only).

### Reasoning
The central skill of this task is **correct historical change detection** —
did the agent fetch both Overpass snapshots, difference them per district,
and produce a realistic symmetric difference (Vienna's Bezirke have not
moved since 1955, so the diff must be tiny). The README's expected
weak-agent failure mode is exactly the attic-API / change-detection miss,
caught by the area-dominance and per-type-count checks. Those get the
highest weight. Name normalisation and the touches_changed adjacency flag
are real but secondary deliverables (Tier B). Pure schema/structural sanity
(CRS, envelope, geom type, enum presence, boolean type, count>=20) is
cosmetic for severity purposes (Tier C).

Disjoint-failure check: `wrong_geometry` concentrates all its failures in
the central change-detection group, so up-weighting Tier A pushes it
*down* (more severe -> lower), while `wrong_attributes` (geometry correct,
only touches inverted) touches one Tier-B check and stays near the top.
Up-weighting the central group therefore *reinforces* the correct ordering
rather than inverting it.

### Weight changes
| Subcheck | Tier | old | new |
|---|---|---|---|
| unchanged_area_dominates | A (central: realistic diff) | 3.0 | 4.0 |
| changed_area_is_small | A (central: realistic diff) | 3.0 | 4.0 |
| per_type_feature_count | A (central: change detection) | 3.0 | 4.0 |
| overall_coverage_iou | A (central: right geometry/region) | 3.0 | 4.0 |
| touches_changed_accuracy | B (adjacency deliverable) | 3.0 | 2.0 |
| district_name_set_overlap | B (name normalisation) | 3.0 | 2.0 |
| total_feature_count | B (aggregate count) | 3.0 | 2.0 |
| all_change_types_present | C (structural) | 1.0 | 1.0 |
| geometry_type_polygonal | C (structural) | 1.0 | 1.0 |
| feature_count_plausible | C (structural) | 1.0 | 1.0 |
| crs_is_wgs84 | C (structural) | 1.0 | 1.0 |
| coordinates_in_vienna_envelope | C (structural) | 1.0 | 1.0 |
| touches_changed_is_boolean | C (structural) | 1.0 | 1.0 |

Denominator: 27 -> 28 (4×4 + 3×2 + 6×1).

### Broken scores before -> after
| Class | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.00 | 0.00 | gate fail (missing columns); unchanged |
| wrong_geometry | 0.5556 | 0.5000 | central change-detection broken (4 central fails) -> drops, correctly the most-severe non-gate case |
| wrong_attributes | 0.8889 | 0.9286 | geometry correct, only touches inverted -> rises, cosmetic slip near the top |

Ordering: monotone and severity-aligned —
`wrong_format` 0.00 < `wrong_geometry` 0.50 < `wrong_attributes` 0.93 < reference 1.00.
The two informative brokens keep their declared `expected_score_range`s
([0.3,0.7] and [0.8,1.0]) and now sit further apart, sharpening resolution.

### Prior-run re-grade summary (8 current/notable runs at task version 2)
| Run | old | new | failure |
|---|---|---|---|
| run-20260526-1753Z | 1.00 | 1.00 | (correct) |
| run-20260528-0113Z | 0.8889 | 0.8571 | per_type drift only (real OSM drift) |
| run-20260527-2016Z | 0.7778 | 0.8571 | name-fold (HR-001): district_name + cascaded touches |
| run-20260528-1927Z | 0.7778 | 0.8571 | name-fold (HR-001) |
| run-20260528-2332Z | 0.7778 | 0.8571 | name-fold (HR-001) |
| run-20260608-074701Z | 0.5556 | 0.6429 | name-fold + under-produced fragments |
| run-20260609-084636Z | 0.4444 | 0.3571 | 1,483 fragments + broken geometry (IoU 0.07) |
| run-20260607-112430Z | 0.0741 | 0.0714 | degenerate (11/13 fail) |

Notable shifts: the name-normalisation runs (HR-001 drift, geometry fully
correct) rise from ~0.78 to ~0.86 — the disputed Title-case-vs-folded form
is a Tier-B issue, not a central change-detection failure, so a lighter
penalty is more faithful to severity. Conversely run-20260609 (genuinely
broken fragment geometry) drops from 0.44 to 0.36, now correctly below
`wrong_geometry`, since it fails 5 central checks. The ordering across all
runs is severity-monotone.

### HRs
None dropped. The four open HRs (HR-001 prompt-vs-grader district-name form,
HR-002 EPSG:4326 area-warning cosmetics, HR-003 inventory-mismatch, HR-004
per-(district,change_type) dissolve) are unrelated to the 3x-content-weighting
concern this pass resolves; all carried forward unchanged.

### Notes (no action — outside grading-only scope)
- The fifth-pass folder reorg renamed HR-002 (was inventory) to HR-003 and
  introduced HR-002 for the EPSG:4326 area warnings; status.json reflects
  the current numbering. No threshold or check is changed here.

### Tests run
- grader on reference: 1.0 (13/13, weighted; denom 28)
- grader on broken_wrong_format: 0.0
- grader on broken_wrong_geometry: 0.5000 (recorded 0.50)
- grader on broken_wrong_attributes: 0.9286 (recorded 0.93)
- pytest: not run (orchestrator runs the suite)
