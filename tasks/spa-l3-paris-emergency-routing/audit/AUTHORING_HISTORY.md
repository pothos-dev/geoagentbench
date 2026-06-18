# Implementation notes — spa-l3-paris-emergency-routing

## Status
completed

## Summary
L3 spatial analysis task requiring live OSM data fetching, network graph construction, and four routing analyses (closest facility, shortest path, distance matrix, isochrones) output as a multi-layer GPKG in Lambert-93.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.0 (expected range [0.0, 0.0])
  - wrong_geometry: 0.7 (expected range [0.5, 0.8])
  - partial: 0.2 (expected range [0.1, 0.3])
- Second-run output match: bit-identical (same OSM data within the same session; expected to differ-explained-by-drift across days)
- Library tests after task: pass

## Failure-mode coverage
- Euclidean instead of network distance: broken_wrong_geometry
- Wrong CRS / unprojected output: Gate 1 + Gate 2 coordinate range check
- Missing layers / wrong format: broken_wrong_format
- Undirected graph / oneway ignored: principled-reasoning (absorbed by 15% distance tolerance)
- No speed-based travel time: principled-reasoning (isochrone IoU + area checks)
- Partial hospital coverage: broken_partial
- Incorrect distance matrix structure: broken_partial
- Fabricated route geometries: principled-reasoning (closest_hospital_distances subcheck)

## Open issues
- [severity: low] — Road network is fetched manually via Overpass rather than osmnx because osmnx's internal query splitting caused timeouts for the Paris bbox. The manual approach is more reliable but produces a slightly different graph (haversine edge lengths vs osmnx's projected lengths).
- [severity: low] — Isochrones use convex hull of reachable nodes, which is a coarse approximation. Alpha shapes or concave hulls would be more accurate but require scipy.spatial.Delaunay which is not in the pinned deps.

## Suggested prompt changes

## Inventory change proposals

## Library extensions

## Runtime
~8 minutes

---

# Evaluator review log

## Evaluator review 2026-05-26  (evaluator-commit pending)

### 1. Design history

#### Initial design intent
Per the inventory row and the first-commit README, this is an L3 spatial-analysis task simulating Captain Julien Moreau at SAMU's Paris coordination centre rebuilding a dispatch coverage model. The agent must fetch the Paris driveable road network and hospital amenities live from OSM Overpass (bbox 48.83,2.30 to 48.88,2.38), build a directed routing graph (respecting `oneway` and `maxspeed`, defaulting to 30 km/h), and produce a four-layer GPKG in Lambert-93 (EPSG:2154): incidents (Point), closest_hospital (LineString, shortest path), distance_matrix (top-3 candidates by network distance per incident), and isochrones_15min (MultiPolygon, 15-minute drive-time per hospital). The task exercises closest-facility, shortest-path, network distance matrix, and isochrone — all on a live-fetched, directed road graph.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-11 | fc2b97f | initial-authoring | Initial commit (older repo layout, larger 553-line grader, 667-line generator) | Commit msg: "task: spa-l3-paris-emergency-routing [completed]" |
| 2026-05-12 | e0cf3ae | initial-authoring (re-authoring) | Re-authored: trimmed grader to 342 lines, generator to 389 lines, kept four layers + three broken sets; reference score 1.0; brokens 0.0/0.7/0.2 | Commit msg: "L3 spatial analysis task: emergency routing in central Paris. … Reference score: 1.00. Broken scores: wrong_format=0.0, wrong_geometry=0.7, partial=0.2" |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit output-schema block (layer names, geometry types, required columns) to instruction | Commit msg: "declare exact output schema in prompts to match graders … grader was already enforcing them implicitly. No grader changes" |
| 2026-05-13 | 9b1fb11 | prompt-change | Merged output-schema block into prose paragraph (no semantic change) | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-15 | e8ea3e1 | prompt-change | Dropped `(amenity=hospital)` tag hint and `Build a routable graph` procedural sentence; replaced with "three deliverables" framing | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-16 | 7c812d6 | prompt-change | Inlined the eight incident coordinates (lat/lon) into the instruction text | Commit msg: "paris-emergency-routing: provide the 8 incident coordinates in instruction" (had been ambiguous which 8 to use) |
| 2026-05-16 | ce7d3d1 | data-change + prompt-change | Moved the 8 incidents into `data/incidents.csv` (columns: incident_id, latitude, longitude, label); instruction now references the CSV | Commit msg: "Cleaner than embedding 8 coordinate pairs in the instruction text" |
| 2026-05-17 | 7f31f98 | prompt-change | Replaced "Lambert-93 (EPSG:2154)" with "an appropriate metric coordinate system for Paris"; replaced "shortest-path route from each incident to its closest hospital by network distance" with "shortest driving route … to its closest hospital" | Commit msg: "Strip CRS codes, operation names, and explicit hints from instruction text while preserving output specs, column names, and unit requirements" |
| 2026-05-26 | 29a9ae3 | docs-change (folder reorg) | Migrated `data/ → inputs/`, `reference/{generate.py,outputs}/ → reference/solution/{generate.py,outputs}/`, `tests/broken_* → reference/failures/broken_*`, `IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md`; adjusted REF_DIR / OUTPUT_DIR paths and task.json `inputs[].url`. No semantic change. | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit 7f31f98, class: prompt-change). The 2026-05-26 reorg is path-only and does not affect the answer key or the instruction surface; runs after that date are equivalent in evidentiary terms.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:18:20Z | 0.0 | failed — model-side (Bash 120 s timeout running solve.py; no GPKG produced; agent chose EPSG:32631 internally — would have failed Gate 1 anyway) | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17 | 0.0 | done | stale (pre-cutoff) |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17 | 0.0 | done | stale (pre-cutoff) |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17 | 0.9 | done | stale (pre-cutoff) |
| run-20260516-1130Z | claude-code-opus-basic | 2026-05-16 | 1.0 | done | stale (pre-cutoff) |
| run-20260516-0743Z | claude-code-opus-basic | 2026-05-16 | 0.8 | done | stale (pre-cutoff) |

Only one `current` run (gemma-4-26b), and it died of a model-side bash timeout before producing any GPKG. Evidence for the post-cutoff task surface is therefore thin.

#### Verdict
**prompt-grader-inconsistent**

Commit 7f31f98 stripped "Lambert-93 (EPSG:2154)" from the instruction and replaced it with "an appropriate metric coordinate system for Paris". `grade.py` Gate 1 still hard-requires `EPSG:2154` on every spatial layer (`grade.py:93-95`), and `task.json > expected_outputs[0].crs` still pins `EPSG:2154`. However, only the `instruction` string is forwarded to the agent by the harness (`benchmark/harness/adapter_core/app.py:137-138`); `expected_outputs[]` is not surfaced. A competent agent reading the current instruction can validly pick EPSG:32631 (UTM 31N) — both are appropriate metric CRSes for Paris — and would be hard-failed at Gate 1 with score 0. The 2026-05-26 gemma transcript shows exactly this CRS choice (`solve.py` line `G_proj = ox.project_graph(G, to_crs='EPSG:32631')`). The instruction-stripping guide explicitly says (lines 29, 42) "Output CRS always stays — it's part of the output contract, not an analysis choice"; commit 7f31f98 contradicted that rule. The fix belongs in the prompt (restore the Lambert-93/EPSG:2154 mention in the redundant output-schema sentence), not in the grader: the grader's CRS hard-requirement matches both the inventory ("CRS out: EPSG:2154 (RGF93 / Lambert-93)") and the task contract.

I am not applying this fix unilaterally. Step 4 permits stripping clear gifts but not re-adding contract elements that an earlier evaluator's strip removed; that crosses into prompt-vs-grader judgment territory. Flagged HR-001.

#### Specific findings
- The redundant output-schema sentence in `task.json > instruction` lost its CRS pin in commit 7f31f98 ("Lambert-93 (EPSG:2154)" → "an appropriate metric coordinate system for Paris"), while `grade.py` Gate 1 and `task.json > expected_outputs[].crs` still hard-require EPSG:2154. Recommended fix: restore "Lambert-93 (EPSG:2154)" in the closing sentence. <!-- HUMAN-REVIEW id="HR-001" category="prompt-grader-inconsistent" severity="med" -->
- The sole `current` run (gemma-4-26b, 2026-05-26) is a model-side failure (120 s bash timeout while osmnx was downloading the road network). Not a task problem — out of scope per evaluator guidance. The post-cutoff sample size is one; once HR-001 is decided, a fresh sweep with stronger models will give real calibration evidence.
- The `incidents.csv` "label" column ("near Notre-Dame", "near Louvre", …) is mildly suggestive of well-known points-of-interest but is plausible operational shorthand for SAMU dispatch annotations. Not flagging.
- Reference grader on `reference/solution/outputs/` scores 1.00 (10/10 subchecks). `metadata.yaml > broken_solutions` measured scores (0.0 / 0.7 / 0.2) remain in their declared ranges; not re-verified this run because no edits were applied to the grader.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-grader-inconsistent — Restore "Lambert-93 (EPSG:2154)" in the closing sentence of `task.json > instruction`; current "an appropriate metric coordinate system for Paris" is broader than the grader's hard EPSG:2154 requirement.

#### Tests run
- grader on reference: 1.00 (10/10 subchecks)
- pytest: pass (35/35)

## Evaluator review 2026-05-26 (re-evaluation — new run evidence)  (evaluator-commit pending)

This block re-evaluates the task after two fresh post-cutoff runs (opus + gemma) were
added, both scoring 1.0. The design-history reconstruction in the prior block above is
accurate and unchanged; I re-confirmed the cutoff and the 7f31f98 timestamp. No design-affecting
commits have landed since the prior review (the only newer commit, 8da307e, is this audit
trail's own evaluator artefacts). I do not repeat the change log.

### 2. Current-state review (refreshed)

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit 7f31f98, class: prompt-change). Unchanged.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | openrouter gemma-4-26b | 2026-05-26T19:49:42Z | 1.0 | done | current |
| run-20260526-1753Z | claude-code opus-4-7 | 2026-05-26T19:07:14Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter gemma-4-26b | 2026-05-26T09:18:20Z | 0.0 | done — model-side (no GPKG produced; agent chose EPSG:32631 internally) | current |

Three current runs now exist (was one at the prior review). Stale (pre-cutoff) runs are unchanged
from the prior block's footnote and not re-listed.

Per-run output inspection:
- 1753Z (opus, 1.0): all 4 layers in EPSG:2154; closest_hospital n=8, distance_matrix n=24, isochrones n=29. closest_hospital_distances match_rate=0.75, IoU=0.78.
- 1922Z (gemma, 1.0): all 4 layers in EPSG:2154; closest_hospital n=8, distance_matrix n=24, isochrones n=28. closest_hospital_distances match_rate=0.50 (at the 0.5 pass threshold), IoU=0.55 (just above the 0.50 min).
- 0748Z (gemma, 0.0): no `emergency_routing.gpkg` produced — Gate 1 "not found". `solve.py` is present and chose `EPSG:32631` (UTM 31N) at lines 57/90/94/155-156/183, but the script never wrote output (model-side failure, not a CRS failure on its own).

#### Verdict
**prompt-grader-inconsistent** (unchanged from prior review; now confirmed by direct run evidence)

The two new 1.0 runs do **not** clear the HR-001 inconsistency — they are simply the runs in which
the agent happened to pick EPSG:2154. The latent inconsistency is now empirically demonstrated:
the instruction forwarded to the agent (the only field the harness surfaces — `adapter_core/app.py:137-138`)
says "an appropriate metric coordinate system for Paris" with no EPSG pin, while `grade.py` Gate 1
(`grade.py:93-95`) hard-fails any layer whose CRS is not EPSG:2154. UTM 31N (EPSG:32631) is a
geodetically valid metric CRS for Paris (≈2.35°E, squarely in zone 31N). Run 0748Z shows the same
gemma model validly choosing EPSG:32631 from this instruction; had that run written its GPKG it would
have hit Gate 1 with score 0 despite a defensible CRS choice. Runs 1922Z and 1753Z chose EPSG:2154
and passed. So the score outcome pivots on a CRS choice the instruction leaves open but the grader pins —
the definition of `prompt-grader-inconsistent`. The fix belongs in the prompt (restore the
"Lambert-93 (EPSG:2154)" pin in the redundant output-schema sentence), consistent with the inventory
("CRS out: EPSG:2154"), the `expected_outputs[].crs` contract, and the instruction-stripping guide's
"Output CRS always stays" rule. The grader is correct as-is.

I am not applying this fix unilaterally. Re-adding a contract element that an earlier strip removed is
a prompt-vs-grader judgment call (the previous evaluator reached the same conclusion); Step 4 permits
stripping gifts, not restoring stripped contract text. Flagged HR-001 (carried forward, severity med).

#### Correction to prior block
The prior block's runs table described 0748Z as a "Bash 120 s timeout … no GPKG produced". The run.json
records `status: done` (not a timeout error); the operative facts — no GPKG written, UTM 31N chosen
internally — are correct, but it was a plain no-output model-side failure, not a bash-timeout abort. The
diagnostic conclusion is unaffected.

#### Specific findings
- HR-001 carried forward and strengthened: instruction allows any "appropriate metric coordinate system for Paris"; `grade.py:93-95` and `expected_outputs[].crs` hard-require EPSG:2154; harness surfaces only the instruction. Direct evidence (gemma 0748Z chose EPSG:32631) confirms agents validly diverge. Recommended fix: restore "Lambert-93 (EPSG:2154)" in the closing output-schema sentence of `task.json > instruction`. <!-- HUMAN-REVIEW id="HR-001" category="prompt-grader-inconsistent" severity="med" -->
- The two 1.0 runs (opus + gemma) confirm the task is solvable end-to-end and the grader has no false-negative against correct EPSG:2154 outputs. They are NOT evidence the task is too-easy: the weaker gemma adapter also failed once (0748Z) on a model-side no-output, and a valid UTM-31N answer would still score 0. Calibration spread (0.0 / 1.0 / 1.0) is plausible for L3.
- Reference grader on `reference/solution/outputs/` re-verified at 1.00 (10/10). pytest 35/35. No grader edits applied, so `metadata.yaml > broken_solutions` measured scores were not re-run.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-grader-inconsistent — Restore "Lambert-93 (EPSG:2154)" in the closing output-schema sentence of `task.json > instruction`; "an appropriate metric coordinate system for Paris" is broader than the grader's hard EPSG:2154 gate. Now confirmed by gemma run 0748Z empirically selecting EPSG:32631.

#### Tests run
- grader on reference: 1.00 (10/10 subchecks)
- pytest: pass (35/35)

## Evaluator review 2026-05-27 (re-evaluation — surfaced a previously-unanalyzed current run)  (evaluator-commit pending)

This is the third evaluator pass. No design-affecting commit has touched the task since the
prior reviews; the only newer commits on the branch are this audit trail's own evaluator
artefacts (8da307e, 2f6c703) and unrelated other-task sweeps. The design-history reconstruction
and the change log in the first block above remain accurate; I re-confirmed the git log
(`git log --follow … benchmark/tasks/spa-l3-paris-emergency-routing/`) and do not repeat it.

### 2. Current-state review (refreshed)

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit 7f31f98, class: prompt-change). Unchanged.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | openrouter gemma-4-26b | 2026-05-26T19:49:42Z | 1.0 | done | current |
| run-20260526-1753Z | claude-code opus-4-7 | 2026-05-26T19:07:14Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter gemma-4-26b | 2026-05-26T09:18:20Z | 0.0 | done — model-side (no GPKG written; agent chose EPSG:32631 internally) | current |
| run-20260517-1424Z | openrouter deepseek-v4-flash | 2026-05-17T19:01:37Z | 0.0 | done — **Gate-1 CRS reject** | current (newly surfaced) |
| run-20260517-1254Z | claude-code opus | 2026-05-17T14:15:42Z | — | failed — model-side (`claude exited 143`) | current (no output) |

Footnote — stale (pre-cutoff) runs considered and excluded: run-20260517-0614Z (deepseek, runner killed, started 12:21Z < cutoff), run-20260517-0304Z / -0134Z, run-20260516-* (opus 0.8/0.8/1.0), run-20260515-*, run-20260514-*, run-20260512/13-* (mix of sonnet/deepseek/gemma, several harness-side failures). Their scores are not evidence for the post-cutoff instruction surface.

**Newly-surfaced run (the substantive addition this pass).** The prior two blocks listed only the
three 0526 runs. Run **run-20260517-1424Z** (deepseek-v4-flash) is also post-cutoff (started 19:01:37Z
≥ 12:49:06Z cutoff) and was not analyzed before. Per-output inspection of its
`outputs/emergency_routing.gpkg`:

- All four required layers present (`incidents`, `closest_hospital`, `distance_matrix`, `isochrones_15min`).
- All required columns present per layer (`incident_id`; `incident_id`+`hospital_name`+`network_distance_m`; `incident_id`+`hospital_name`+`rank`+`network_distance_m`; `hospital_name`+`travel_time_min`).
- Correct geometry types: incidents Point (8 rows), closest_hospital MultiLineString (8 rows), isochrones_15min MultiPolygon (73 rows), distance_matrix tabular/empty geometry (24 rows = 8 incidents × 3 ranks, matching the reference's 24).
- The ONLY defect: every spatial layer is **EPSG:32631 (UTM 31N)**, not EPSG:2154. `score.json` shows Gate 1 failed with exactly `"Layer incidents CRS is EPSG:32631, expected EPSG:2154; …"` and the run scored 0.0 with zero subchecks run.
- `solve.py` line 17: `METRIC_CRS = "EPSG:32631"`, line 86 `print("Projecting to UTM...")` — a deliberate, defensible reading of the instruction's "an appropriate metric coordinate system for Paris" (Paris ≈ 2.35°E sits squarely in UTM zone 31N).

This is the strongest evidence to date for HR-001. The prior blocks could only cite the gemma 0748Z
run, which chose EPSG:32631 *internally* but never wrote a GPKG, so its hard-fail was hypothetical.
Run 1424Z **actually wrote a complete, structurally-correct, geometrically-plausible four-layer GPKG**
and was hard-failed at Gate 1 (score 0.0) on the CRS choice alone — a structurally-correct submission
rejected purely because the agent picked one valid metric CRS for Paris (UTM 31N) instead of the one
the grader pins (Lambert-93). The instruction does not let the agent know that EPSG:2154 specifically
is required.

#### CRS / format consistency (2c-CRS)
Reference output, `expected_outputs[0].crs`, README output table, and `grade.py` Gate 1 all agree on
EPSG:2154 / GPKG. The isochrone-IoU subcheck (`grade.py:296-310`) is *not* a one-sided reprojection:
Gate 1 already rejects any non-2154 layer, so both submission and reference are guaranteed EPSG:2154
before IoU runs. No CRS-consistency finding beyond HR-001.

#### Verdict
**prompt-grader-inconsistent** (unchanged across all three passes; now empirically demonstrated by a
written-to-disk submission, not a hypothetical)

The instruction is the only field the harness forwards to the agent (`adapter_core/app.py:137-138`);
`expected_outputs[].crs` is never surfaced. The instruction says "an appropriate metric coordinate
system for Paris" — which validly admits both EPSG:2154 (Lambert-93) and EPSG:32631 (UTM 31N) — while
`grade.py:93-95` hard-fails any layer not in EPSG:2154. Commit 7f31f98 stripped the "Lambert-93
(EPSG:2154)" pin from the closing redundant output-schema sentence, contradicting the
instruction-stripping guide's explicit rules that the **output CRS is part of the output contract and
always stays** (`instruction-stripping-guide.md:20,29,42`) and that the closing output-schema sentence
restates the CRS (`:187`; `task-design-prompt.md:79`). The fix belongs in the prompt (restore
"Lambert-93 (EPSG:2154)" in the closing sentence), not the grader — the grader matches the inventory
("CRS out: EPSG:2154"), the `expected_outputs[].crs` contract, and the design guide. Do not loosen the
grader.

I continue NOT to apply this fix unilaterally, agreeing with both prior evaluators. Step 4's
unilateral-edit list permits *stripping a clear gift* (specifically "when the output format pins the
CRS by convention" — which GPKG does not), not *restoring contract text that an earlier authoring
strip removed*. Re-adding a CRS pin to a prompt the design pipeline deliberately edited is a
prompt-vs-grader judgment the task-design owner should ratify. Flagged HR-001 (carried forward,
severity med).

#### Specific findings
- HR-001 carried forward and strengthened by run 1424Z. Instruction admits any "appropriate metric coordinate system for Paris" (forwarded field only — `app.py:137-138`); `grade.py:93-95` and `expected_outputs[].crs` hard-require EPSG:2154; deepseek run 1424Z wrote a complete, structurally-correct four-layer GPKG in EPSG:32631 and was hard-failed at Gate 1 for that reason alone (score 0.0). Recommended fix: restore "Lambert-93 (EPSG:2154)" in the closing output-schema sentence of `task.json > instruction`. <!-- HUMAN-REVIEW id="HR-001" category="prompt-grader-inconsistent" severity="med" -->
- The 0.0 / 1.0 / 1.0 / 0.0 spread across the four current runs is NOT a too-easy signal: two of the four current runs scored 0.0 (one model-side no-output, one genuine CRS rejection of a correct-looking output), and a defensible UTM-31N answer scores 0 by construction. The latent inconsistency is a `prompt-grader-inconsistent` problem, not `too-easy` and not `too-strict` in the grader's own right (the grader correctly enforces the contract; the instruction under-specifies it).
- `incidents.csv` "label" column ("near Notre-Dame", …) is mildly POI-suggestive but plausible SAMU dispatch shorthand; not the answer key (incident coords come from the CSV itself). Not flagging — consistent with prior passes.
- Reference grader on `reference/solution/outputs/` re-verified at 1.00 (10/10 subchecks). pytest 35/35. No grader/metadata edits applied, so `metadata.yaml > broken_solutions` measured scores (0.0 / 0.7 / 0.2) were not re-run; they remain within their declared ranges.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-grader-inconsistent — Restore "Lambert-93 (EPSG:2154)" in the closing output-schema sentence of `task.json > instruction`. Now empirically confirmed: deepseek run 20260517-1424Z wrote a complete, structurally-correct four-layer GPKG in EPSG:32631 (UTM 31N, a valid metric CRS for Paris) and was hard-failed at Gate 1 (score 0.0) on the CRS alone.

#### Tests run
- grader on reference: 1.00 (10/10 subchecks)
- pytest: pass (35/35)


## Evaluator review 2026-05-28 (HR-001 resolved — CRS accept-list refactor)  (evaluator-commit pending)

### 1. Design history
HR-001 was carried across three prior evaluator passes (2026-05-26, 2026-05-26 refresh, 2026-05-27)
with growing evidence — culminating in deepseek run 20260517-1424Z, a structurally-correct four-layer
GPKG in EPSG:32631 hard-failed at Gate 1 for the CRS choice alone. This block applies the resolution
under the policy now codified in `task-evaluator-prompt.md` Step 4 ("CRS accept-list refactor").

| Date | Commit | Class | Summary | Source |
|---|---|---|---|---|
| 2026-05-28 | pending | grader-change | `grade.py` accepts `{EPSG:2154, EPSG:32631}`, reprojects non-canonical submissions to EPSG:2154 before all spatial subchecks, adds `official_crs_used` subcheck rewarding Lambert-93 | This evaluator pass |
| 2026-05-28 | pending | library-extension | New helper `geo_grading.check_and_normalize_crs(gdf, accepted_epsgs, target_epsg)` with unit tests | This evaluator pass |
| 2026-05-28 | pending | prompt-change | Instruction schema sentence: "an appropriate metric coordinate system for Paris" → "the official metric coordinate system for Paris" | User-directed (no EPSG code re-added) |
| 2026-05-28 | pending | docs-change | `task-evaluator-prompt.md` 2c-CRS qualified + Step 4 gains "CRS accept-list refactor" bullet | This evaluator pass |

### 2. Current-state review (refreshed)

#### Cutoff
- design-affecting cutoff: 2026-05-28 (this pass's grader-change + prompt-change). All prior runs are now stale.

#### Runs considered (re-graded against the new grader)
| Run | Adapter | CRS chosen | Old score | New score | Notes |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | EPSG:2154 | 1.0 (10/10) | 1.0 (11/11) | official_crs_used adds one more pass |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | EPSG:2154 | 1.0 (10/10) | 1.0 (11/11) | unchanged |
| run-20260527-2016Z | claude-code-opus-basic | EPSG:2154 | 1.0 (10/10) | 1.0 (11/11) | unchanged |
| run-20260528-0113Z | claude-code-opus-basic | EPSG:2154 | 1.0 (10/10) | 1.0 (11/11) | unchanged |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | EPSG:2154 | 0.4 (4/10) | 0.45 (5/11) | official_crs_used pass added; substantive failures unchanged |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | EPSG:32631 | **0.0 (Gate-1)** | **0.545 (6/11)** | accept-list passes Gate 1; 5 substantive failures surface that the prior Gate-1 hard-fail had masked (hospital-name Jaccard 0.14, distance match-rate 0.12, isochrone count 73 vs 28, isochrone name Jaccard 0.37, official_crs_used) |

#### Verdict
**calibrated**

HR-001 was a `prompt-grader-inconsistent` finding because the instruction admitted multiple CRSes and
the grader Gate-1'd everything except one. Under the now-documented "CRS accept-list refactor" policy
(`task-evaluator-prompt.md` Step 4) this is unilaterally resolvable: the grader now accepts
`{EPSG:2154, EPSG:32631}`, reprojects the submission into EPSG:2154 before all spatial subchecks, and
rewards Lambert-93 with an additional `official_crs_used` subcheck. Defensible-but-non-canonical CRS
picks no longer collapse to 0; the canonical Lambert-93 pick remains the "most correct" answer worth
1/N more than UTM 31N. The reference still scores 1.0 (11/11). The deepseek 1424Z run, the strongest
piece of evidence for HR-001, now lands at 0.545 — the CRS penalty is one of five subcheck failures,
revealing substantive hospital-set differences that Gate 1 had been hiding.

#### CRS / format consistency (2c-CRS)
The submission-only reprojection (UTM 31N → Lambert-93) is the *declared* accept-list policy
permitted by the qualifier added to 2c-CRS this pass — not a paper-over of a reference/contract
mismatch. Reference output, `expected_outputs[0].crs`, README output table all agree on EPSG:2154.

#### Specific findings
- HR-001 resolved by grader refactor + helper extraction + one-word prompt nudge ("the official"). No EPSG code re-added to the instruction; the grader does the heavy lifting via the accept-list and the `official_crs_used` subcheck.
- Broken-solutions measured scores recomputed under the new (11-subcheck) grader and refreshed in `metadata.yaml`: `wrong_format` 0.0 (range [0.0, 0.0]), `wrong_geometry` 0.73 (range [0.5, 0.8]), `partial` 0.27 (range [0.1, 0.3]). All within declared ranges.
- `geo_grading.check_and_normalize_crs` is the canonical helper for this pattern. Six unit tests added in `tests/test_comparisons.py`; full pytest suite passes (41/41).
- Two adjacent HR items in other tasks are candidates for the same refactor in a follow-up pass: `crs-l2-svalbard-polar-areas` HR-001 (EPSG:3995 vs EPSG:3413) and `spa-l2-lagos-hotspot-overlaps` HR-001 (EPSG:32631 vs EPSG:26331; the latter already implements the pattern by hand and could be migrated to the helper). Not in scope for this pass.

### 3. Changes applied this run

#### Unilateral edits
- `benchmark/eval/geo_grading/comparisons.py`: added `check_and_normalize_crs(gdf, accepted_epsgs, target_epsg)`. Re-exported from `__init__.py`. Reason: extract the accept-list + reproject pattern hand-rolled in spa-l2-lagos and now needed here.
- `benchmark/eval/tests/test_comparisons.py`: 6 new tests for the helper. pytest: 41/41 pass.
- `benchmark/tasks/spa-l3-paris-emergency-routing/grade.py`: replaced hard EPSG:2154 Gate 1 with `check_and_normalize_crs({2154, 32631}, target=2154)`; added `official_crs_used` subcheck (11 total). Re-grade on reference: 1.0 (11/11).
- `benchmark/tasks/spa-l3-paris-emergency-routing/task.json`: instruction schema sentence "an appropriate metric coordinate system for Paris" → "the official metric coordinate system for Paris". One-word nudge; no EPSG re-added.
- `benchmark/tasks/spa-l3-paris-emergency-routing/metadata.yaml`: refreshed `broken_solutions > measured_score` (0.0 / 0.73 / 0.27); bumped `prompt_version` to `2026-05-28-a`.
- `benchmark/authoring/task-evaluator-prompt.md`: 2c-CRS qualified ("paper over" / declared accept-list); Step 4 gains "CRS accept-list refactor" bullet referencing the helper.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none — HR-001 resolved)

#### Tests run
- grader on reference: 1.00 (11/11 subchecks)
- grader on broken_wrong_format: 0.00, broken_wrong_geometry: 0.73, broken_partial: 0.27 — all within declared ranges
- pytest: pass (41/41)


## Evaluator review 2026-05-28 (post-resolution confirmation pass)  (evaluator-commit pending)

This is the fourth evaluator pass. HR-001 was resolved in the prior 2026-05-28 block via the
CRS accept-list refactor (commit 377a59). No design-affecting commit has touched the task
since that resolution; the only newer commit on the branch is 622342be, which adds the global
`version` field to `task.json` and drops the unused `metadata.yaml > prompt_version` line —
neither changes prompt content, grader logic, tolerances, or inputs, so it is `mixed` but
not design-affecting. The design-history reconstruction and change log in the first block
above remain accurate; I re-confirmed via `git log --follow … benchmark/tasks/spa-l3-paris-emergency-routing/`
and do not repeat it.

| Date | Commit | Class | Summary | Source |
|---|---|---|---|---|
| 2026-05-28 | 622342b | docs-change (metadata-only) | Dropped `metadata.yaml > prompt_version: 2026-05-28-a`. No grader/prompt/input effect. | Global task-versioning rollout |

### 2. Current-state review (refreshed)

#### Cutoff
- design-affecting cutoff: 2026-05-28T06:54:35+00:00 (commit 377a59, class: grader-change + prompt-change). Commit 622342b at 2026-05-28T07:07:03Z is metadata-only and not design-affecting. All committed runs predate the cutoff.

#### Runs considered (re-graded against the current 11-subcheck grader)
| Run | Adapter | Started | Old score | Re-graded | Validity | Notes |
|---|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:19:04Z | 0.4 (4/10) | 0.455 (5/11) | stale (pre-cutoff) | EPSG:2154; substantive failures: closest-hospital names Jaccard=0.00, distances match=0.12, isochrone count 5 vs 28, IoU=0.13, no plausible-area isochrones. Genuine geometric failure; CRS check passes. |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T03:12:09Z | 1.0 (10/10) | 1.0 (11/11) | stale (pre-cutoff) | EPSG:2154; clean pass under new grader. |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T01:03:34Z | 0.0 | 0.0 (no outputs) | stale (pre-cutoff) | Model-side: no GPKG written. |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T23:13:14Z | 1.0 (10/10) | 1.0 (11/11) | stale (pre-cutoff) | EPSG:2154; clean. |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:49:42Z | 1.0 (10/10) | 1.0 (11/11) | stale (pre-cutoff) | EPSG:2154; clean. |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:07:14Z | 1.0 (10/10) | 1.0 (11/11) | stale (pre-cutoff) | EPSG:2154; clean. |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:18:20Z | 0.0 | 0.0 (no outputs) | stale (pre-cutoff) | Model-side: no GPKG written; chose EPSG:32631 internally. |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T19:01:37Z | 0.0 (Gate-1) | 0.545 (6/11) | stale (pre-cutoff) | EPSG:32631; previously Gate-1-rejected; under the accept-list now scores 0.545 with 5 substantive failures + official_crs_used penalty. |

No `current` (post-cutoff) runs exist yet — the cutoff is the resolution commit itself, applied earlier
today. Per Step 2b guidance ("no current runs available — record and stop the diagnostic part"), this is
acceptable: the prior pass's own re-grade of the same submissions (which the cutoff revalidates) shows the
new grader behaves correctly. The next sweep will produce fresh post-cutoff evidence.

#### CRS / format consistency (2c-CRS)
Verified: reference GPKG layers (`incidents`, `closest_hospital`, `distance_matrix`, `isochrones_15min`)
are all EPSG:2154; `task.json > expected_outputs[0].crs = EPSG:2154`; README's output table pins
EPSG:2154; `grade.py` accept-list `{2154, 32631}` with target 2154 and `official_crs_used` subcheck
implements the declared accept-list policy permitted by 2c-CRS. The submission-only reprojection
(UTM 31N → Lambert-93) is the declared accept-list path, not a paper-over. No CRS-consistency finding.

#### Verdict
**calibrated** (unchanged — HR-001's resolution holds)

The re-grade matrix confirms the calibration: (a) strong models (opus, gemma when it picks correct CRS)
score 1.0 (11/11); (b) a defensible-but-non-canonical CRS pick (deepseek 1424Z in UTM 31N) lands at
0.545, no longer 0; (c) a structurally-valid but semantically-wrong submission (gemma 0317Z) lands at
0.455 — geometric failures surface as multiple subcheck failures; (d) model-side no-output failures
remain 0.0 and are not task problems. Spread 0.0 / 0.455 / 0.545 / 1.0 across adapters is the
calibration profile L3 should produce.

#### Specific findings
- No findings. HR-001 remains resolved by 377a59. The 622342b commit dropping `prompt_version` from `metadata.yaml` is metadata-only and consistent with the global versioning rollout.
- `task.json` has no explicit `version` field — implicit v1 per the new versioning rules. No unilateral edits this pass means no bump.
- Reference re-graded under current grader: 1.00 (11/11). Broken-solutions measured scores remain `0.0 / 0.73 / 0.27`, all within declared ranges (not re-run this pass since no grader edit applied).
- Coverage tags re-validated; `evaluator_run_at` refreshed to this pass's timestamp.

### 3. Changes applied this run

#### Unilateral edits
- (none — task is calibrated post-resolution; no version bump required)

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.00 (11/11 subchecks)
- pytest: pass (41/41)


## Evaluator review 2026-06-06 (post-soft-CRS-rollout pass; em-dash cleanup + analyst_notes)  (evaluator-commit pending)

This is the fifth evaluator pass. Since the prior 2026-05-28 confirmation block, one
design-affecting global library change has landed (05aabd6 on 2026-05-28T19:02:57Z,
"Soften CRS hard-fail to subcheck deductions across 21 graders") which touched
this task's `grade.py`. The grader now uses `grade_crs_soft` instead of
`check_and_normalize_crs`, and the previous `official_crs_used` subcheck was renamed
to `crs_is_canonical` with a new sibling `crs_in_meaningful_set`. Net effect: the
accept-list / canonical-reward semantics are unchanged, but the grader has 12
subchecks instead of 11. A later commit (bf9ccce, 2026-05-29) added OGC:CRS84 → 4326
normalization in the same helper; this affects WGS84 only and is moot for the
Paris/Lambert-93 accept-list, so it is not design-affecting for this task. Other
recent commits on the branch (versioning rollout 622342b, pyarrow bump, UI changes)
do not touch task content.

### 1. Design history

| Date | Commit | Class | Summary | Source |
|---|---|---|---|---|
| 2026-05-28 | 05aabd6 | grader-change (global) | `grade.py` migrated from `check_and_normalize_crs` to `grade_crs_soft`; `official_crs_used` subcheck renamed to `crs_is_canonical` and `crs_in_meaningful_set` added alongside. Per-task accept-list `{2154, 32631}` and canonical EPSG:2154 unchanged. | Global soft-CRS rollout commit message ("soften CRS hard-fail to subcheck deductions across 21 graders") |
| 2026-05-29 | bf9ccce | library-extension (global) | `geo_grading.grade_crs_soft` accepts `OGC:CRS84` as `EPSG:4326`. WGS84-only; no effect on this task. | Commit message |

The design-history reconstruction in the first evaluator-review block above
remains accurate for everything pre-2026-05-28; I re-confirmed via
`git log --follow … benchmark/tasks/spa-l3-paris-emergency-routing/` and do not
repeat the full change log.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T19:02:57+00:00 (commit 05aabd6, class: grader-change). Bumped from the prior block's 06:54:35Z cutoff (377a59) to absorb the global soft-CRS rollout.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code opus-4-7 | 2026-05-28T22:13:41Z | 1.0 (12/12) | done | current |
| run-20260528-2225Z | openrouter gemma-4-26b | 2026-05-28T23:27:34Z | 0.583 (7/12) | done | current |
| run-20260528-2332Z | claude-code opus-4-7 | 2026-05-29T00:54:07Z | 1.0 (12/12) | done | current |
| run-20260529-0109Z | openrouter gemma-4-26b | 2026-05-29T08:03:28Z | — | failed — model-side (`max iterations exceeded (100)`) | current (no output) |
| run-20260529-0902Z | openrouter deepseek-v4-pro | 2026-05-31T18:12:36Z | — | failed — adapter-side (OpenRouter 403 daily-limit) | current (no output) |
| run-20260606-0953Z | openrouter gemma-4-26b (gis_detailed) | 2026-06-06T10:37:50Z | 0.0 | done — model-side (no GPKG written; 89 s session, prompt-variant A/B test) | current |
| run-20260606-1129Z | openrouter gemma-4-26b (gis_detailed) | 2026-06-06T12:58:34Z | — | cancelled before start | current (no output) |
| run-20260606-1334Z | openrouter gemma-4-26b (gis_detailed) | 2026-06-06T13:56:29Z | — | cancelled before start | current (no output) |
| run-20260528-1624Z | openrouter gemma-4-26b | 2026-05-28T16:24:48Z | 0.0 | done — no GPKG | stale (pre-cutoff by ~2.5 h) |

Footnote — older stale runs (the 2026-05-26 / 2026-05-27 set re-graded in prior blocks) are not re-listed; they remain stale under the new cutoff and their re-graded scores in the prior block (1.0 × 4, 0.455, 0.545) still describe how those submissions behave under the current 12-subcheck grader.

Per-run output inspection (current runs that produced outputs):
- 1927Z (opus, 1.0, 12/12): all four layers in EPSG:2154; closest_hospital n=8, distance_matrix n=24, isochrones n=29. closest_hospital_distances match_rate=0.50 (at threshold), IoU=0.76. Both CRS subchecks pass. Clean.
- 2225Z (gemma, 0.583): structurally valid four-layer GPKG in EPSG:2154; counts (8/8/24) right; isochrones n=5 vs ref 28; substantive geometric failures (closest-hospital names Jaccard=0.00, distance match_rate=0.00, isochrone-name Jaccard=0.00, IoU=0.45). Both CRS subchecks pass, which is what carries the score to 0.583 rather than ~0.4 — i.e. the gemma agent picked the right CRS but did the hospital matching wrong.
- 2332Z (opus, 1.0): clean; matches 1927Z shape (n=8/8/24/26, match_rate=0.88, IoU=0.74).
- 0953Z (gemma-detailed, 0.0): 89-second session, no GPKG written. Model-side (out-of-scope per evaluator guidance).

#### CRS / format consistency (2c-CRS)
Reference output is EPSG:2154 (verified by reading reference GPKG layers). `task.json > expected_outputs[0].crs = EPSG:2154`. README pins EPSG:2154. `grade.py` uses `grade_crs_soft({2154, 32631}, canonical=2154)`: the submission is reprojected to EPSG:2154 before all spatial subchecks; both submission and reference are then in the same metric CRS for IoU/area math (not a one-sided paper-over of a contract mismatch, but the declared accept-list policy permitted by 2c-CRS). Lambert-93 is rewarded by `crs_is_canonical`; UTM 31N earns `crs_in_meaningful_set` but not `crs_is_canonical`. No CRS-consistency finding.

#### Verdict
**calibrated**

Three substantive current runs produced 1.0 / 0.583 / 1.0. The two opus runs landed at 1.0 (clean structural and geometric correctness, canonical Lambert-93 CRS). The gemma 2225Z run reproduces the L3 calibration profile: a model strong enough to ship a structurally valid four-layer GPKG in the right CRS but not strong enough to recover the full hospital set or build accurate isochrones lands in the middle of the score range. Model-side no-output failures (0109Z, 0902Z, 0953Z, plus the two cancelled-before-start runs) are not task problems and are excluded from calibration evidence per evaluator guidance. HR-001 remains resolved by the prior accept-list refactor; the soft-CRS migration preserved that resolution.

#### Specific findings
- The instruction contains two em-dashes ("...metres) — one row per incident" and "...travel_time_min — one row per hospital"), which the house-style rule explicitly bans. Apply unilaterally via period+sentence split; preserves all factual constraints. Re-grade reference after.
- `task.json` has no `analyst_notes` field. Author it per Step 4 schema, covering the hidden EPSG:2154-vs-UTM-31N gotcha and the routing failure modes the grader checks. Does not require a version bump.
- Broken-solutions measured scores under the current 12-subcheck grader: `wrong_format` 0.00, `wrong_geometry` 0.75, `partial` 0.333. The first two are within declared ranges. `partial` is now narrowly above its declared upper bound 0.30 (was 0.27 under 11 subchecks); the +0.06 jump is mechanically explained by the broken_partial output being authored in EPSG:2154 so both new CRS subchecks pass (4/12 vs prior 3/11). Refresh `measured_score` only; the `expected_score_range` update is a design-tuning call I am leaving for a human, but the gap is small and the broken still lands in the "partial failure" zone, so I am not flagging it.
- Run 0953Z (gemma-detailed, gis_detailed prompt variant) wrote no GPKG in 89 seconds — model-side. The new gis_detailed adapter (eb44689) is an A/B-test setup, not a task problem.
- Reference grader on `reference/solution/outputs/` re-verified: 1.00 (12/12). pytest 41/41. Coverage.yaml slugs re-validated against vocabulary.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: replaced two em-dashes in `instruction` with period+sentence splits (house style). Added `version: 2` (bump for the instruction edit). Added `analyst_notes` (description + approach + pitfalls per Step 4 schema). Re-grade on reference: 1.0 (12/12).
- `metadata.yaml`: refreshed `broken_solutions > measured_score` to 0.00 / 0.75 / 0.33 under current grader. The `partial` score is 0.03 above its declared upper bound but mechanically explained by the +1 passing CRS subcheck; ranges left untouched. No version bump needed for this metadata refresh per Step 4.
- `coverage.yaml`: refreshed `evaluator_run_at` only. Slugs unchanged and re-validated against `authoring/coverage-vocabulary.yaml`.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none — verdict is calibrated; the partial broken's narrowly out-of-range score is documented above as a known mechanical artefact of the soft-CRS rollout, not a finding that needs human resolution)

#### Tests run
- grader on reference: 1.00 (12/12 subchecks)
- grader on broken_wrong_format: 0.00, broken_wrong_geometry: 0.75, broken_partial: 0.33
- pytest: pass (41/41)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)`.
- Required-column-per-layer check folded into the existing Gate 1 (the
  subchecks index layers by these columns, so absence is unrecoverable).
- Geometry-type-per-layer check migrated to a new
  `geometry_types_per_layer` subcheck.
- Minimum-feature-count check migrated to a new `min_feature_counts`
  subcheck (incidents and isochrones each >= 3 rows).
- Lambert-93 coord-range sanity check migrated to a new
  `incident_coords_in_metres` subcheck.
- Subchecks now total 15 (was 12).

### Verification
- Reference solution re-graded: 1.0 (15/15 subchecks).

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

This is the sixth evaluator pass. Two design-affecting global grader commits have
landed since the 2026-06-06 pass: the gate-2 removal (363aed2, already documented
in the "Manual cleanup 2026-06-06" block above) and the data-content subcheck
weighting (c749e57). The design-history reconstruction and full change log in the
first evaluator-review block remain accurate; I re-confirmed via
`git log --format='%H %cI %s' -- benchmark/tasks/spa-l3-paris-emergency-routing/`
and do not repeat the pre-2026-06 entries.

### 1. Design history

#### Change log (since prior block)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | a7365ed | docs-change + prompt-change | Prior evaluator pass: em-dash cleanup in instruction, `version: 2`, `analyst_notes` added, measured scores refreshed | Commit msg: "Re-evaluate spa-l3-paris-emergency-routing: calibrated; em-dash cleanup + analyst_notes" |
| 2026-06-06 | 363aed2 | grader-change (global) | Gate 2 (`structural_correctness`) removed; required-columns folded into Gate 1; geometry-type, min-feature-count, and coord-range checks migrated to subchecks (15 total) | Commit msg: gate was inconsistent across graders (34 hard, 2 soft); single hard gate + per-point subchecks |
| 2026-06-07 | c749e57 | grader-change (global) | Eight data-content subchecks tagged `weight=3.0` (incident/closest/matrix/isochrone counts, hospital-name Jaccards, distances, IoU); 7 structural checks stay 1.0; score is now weight-normalised (total weight 31) | Commit msg: "Weight data-content subchecks 3x across all categories" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38+00:00 (commit c749e57, class: grader-change). Task `version` is 2 (unchanged since a7365ed).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter deepseek-v4-flash (basic) | 2026-06-09T12:39:23Z | 1.0 | done | current (task_version 2, post-cutoff) |
| run-20260608-074701Z | openrouter deepseek-v4-flash (gis_detailed) | 2026-06-09T07:42:29Z | — | failed — model-side (`max iterations exceeded (75)`); partial GPKG re-grades at 0.387 | current (no score) |
| run-20260607-112430Z | openrouter gemma-4-26b (gis_detailed) | 2026-06-07T16:55:30Z | 0.226 | done | stale (started 16:55Z, pre-cutoff 18:32Z) |

Footnote — older stale runs (2026-05-26 through 2026-06-06 set) were analyzed in the prior blocks and are not re-listed. To extend the thin current evidence, I re-graded recent stale submissions under the current weighted 15-subcheck grader: opus 1927Z = 1.0, opus 2332Z = 1.0, gemma 2225Z = 0.516, gemma 0607-1124Z = 0.226, deepseek 1424Z (UTM 31N) = 0.581. Together with the current deepseek 1.0 and the re-graded failed run at 0.387, the spread is 0.226 / 0.387 / 0.516 / 0.581 / 1.0 / 1.0.

Per-run output inspection (current runs):
- 084636Z (deepseek basic, 1.0): all four layers EPSG:2154; incidents n=8, closest_hospital n=8, distance_matrix n=24, isochrones n=28 — matches the reference shape exactly; all 15 subchecks pass.
- 074701Z (deepseek detailed, failed): wrote a structurally valid four-layer GPKG in EPSG:2154 before hitting the 75-iteration cap (closest_hospital n=6, matrix n=18, isochrones n=186). Model-side failure; informational re-grade 0.387 (gate passes, 7 subchecks fail). Not calibration evidence per evaluator guidance, but shows the gate correctly admits partial-quality work.

#### CRS / format consistency (2c-CRS)
Reference GPKG layers verified EPSG:2154; `expected_outputs[0].crs = EPSG:2154`; README pins EPSG:2154; `grade.py` uses `grade_crs_soft({2154, 32631}, canonical=2154)` with the declared accept-list policy (submission reprojected to Lambert-93 before all spatial subchecks; `crs_is_canonical` / `crs_in_meaningful_set` pair). No CRS-consistency finding.

#### Verdict
**calibrated**

The weighting commit redistributes points toward data-content checks but changes no pass/fail logic; the re-grade matrix confirms calibration is preserved and slightly sharpened: reference 1.0 (31/31 weight), brokens 0.0 / 0.774 / 0.29, and recent submissions spread 0.226-1.0 with strong models at 1.0 and structurally-valid-but-semantically-wrong work in the 0.2-0.6 band. The deepseek UTM-31N submission (1424Z) lands at 0.581 (CRS penalty is one weighted-1.0 failure among several substantive ones), preserving the HR-001 resolution. Only one scored current run exists (deepseek basic, 1.0) so current-run evidence is thin, but per the 2026-05-28 precedent (cutoff = the grader commit itself) the re-grade matrix is the operative evidence and supports the verdict.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| `emergency_routing.gpkg`, single GPKG, four exact layer names | instruction | stated |
| required columns per layer | instruction | stated |
| geometry types per layer (Point/MultiPoint, LineString/MultiLineString, Polygon/MultiPolygon) | instruction | stated |
| canonical CRS Lambert-93 (`crs_is_canonical`) | instruction's "official metric coordinate system for Paris" (category-level hint) | inferable |
| meaningful CRS set {2154, 32631} | accept-list; non-canonical costs 1/31 | inferable |
| counts within ±15% of reference (incidents 8, closest 8, matrix 24, isochrones ~28) | incidents.csv (8 rows) + bbox + "three nearest" arithmetic; isochrone count = hospital count from live fetch | inferable |
| hospital-name Jaccard >= 0.6 | fetch all hospitals in bbox | inferable |
| network distances ±15%, >= 50% matched | standard drift margin | inferable |
| rank 1-3 ascending by distance | instruction | stated |
| isochrone IoU >= 0.5, areas 1-100 km² | follows from a correct 15-min drive-time computation | inferable |
| min feature counts (>= 3), coords in metres | trivially implied by the above | inferable |

Factual claims verified: `incidents.csv` columns (incident_id, latitude, longitude, label) and 8 rows match `inputs/incidents.csv`; bbox 48.83,2.30-48.88,2.38 matches the reference fetch; 30 km/h default and maxspeed rule match the reference; all column names/units verified against the reference output schema. No missing or inaccurate claim.

#### Reference faithfulness
`reference/solution/generate.py` implements the instruction: Overpass fetch of driveable highways + hospitals in the stated bbox, directed graph honouring oneway, travel-time weights from maxspeed (30 km/h default), network closest-facility with shortest-path LineStrings, 8x3 distance matrix ranked ascending, 15-minute convex-hull isochrones per hospital, all reprojected to Lambert-93 in a single four-layer GPKG. Three benign notes, none rising to a flag: (1) incident coordinates are hard-coded but verbatim identical to `incidents.csv` (the CSV was generated from them in ce7d3d1), so the output is indistinguishable from reading the CSV; (2) the reference adds a `hospital_osm_id` provenance column the prompt does not request — the instruction's column lists are a minimum contract (the grader checks presence, not exclusivity), so submissions with or without extras pass identically; (3) `distance_matrix` uses dummy (0,0) point geometry where the prompt says "geometry may be empty or null" — the grader never inspects that layer's geometry, so all three conventions pass. Faithful.

#### Specific findings
- README was stale on three points and has been fixed (docs-change, no version bump): it claimed "no bundled inputs" (incidents.csv is bundled since ce7d3d1), referenced the removed Gate 2 for CRS/coordinate-range detection, and listed `hospital_osm_id` among "Key columns" although it is not part of the graded contract.
- `analyst_notes` pitfall 6 referenced "Gate 2", removed in 363aed2; rewritten to describe the format gate + `incident_coords_in_metres` subcheck. No version bump (analyst_notes is human-facing only).
- `metadata.yaml > broken_solutions > measured_score` refreshed under the weighted grader: wrong_format 0.0 (unchanged), wrong_geometry 0.75 -> 0.77, partial 0.33 -> 0.29. The partial broken is back inside its declared range [0.1, 0.3], resolving the out-of-range artefact documented in the 2026-06-06 block.
- The weighting commit left `distance_matrix_rank_order` and `isochrone_area_plausible` at weight 1.0 while weighting the eight count/name/distance/IoU checks 3.0. That is the global commit's category-wide call, consistent across the suite; not a per-task finding.
- Run 074701Z (deepseek detailed) is a model-side failure (75-iteration cap) that nonetheless wrote a partial GPKG; noted as out-of-scope for calibration per evaluator guidance.

### 3. Changes applied this run

#### Unilateral edits
- `README.md`: fixed stale "no bundled inputs" claim, stale Gate-2 wording in failure mode 2, and key-columns table now shows the graded contract (with `hospital_osm_id` noted as a reference-only extra). Re-grade on reference: 1.0. Reason: docs drifted behind the gate-2 removal and the ce7d3d1 input bundling.
- `task.json` (`analyst_notes` only): pitfall 6 rewritten to drop the Gate-2 reference. No version bump (not agent-visible). Re-grade on reference: 1.0.
- `metadata.yaml`: `broken_solutions > measured_score` refreshed to 0.0 / 0.77 / 0.29 under the current weighted grader. No version bump.
- `coverage.yaml`: refreshed `evaluator_run_at`; slugs unchanged and re-validated against `authoring/coverage-vocabulary.yaml`.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.00 (15 subchecks, weighted 31/31)
- grader on broken_wrong_format: 0.00, broken_wrong_geometry: 0.77, broken_partial: 0.29 — wrong_format and partial within declared ranges; wrong_geometry 0.77 within [0.5, 0.8]
- pytest: pass (41/41)

## Evaluator review 2026-06-14 (severity-weight recalibration)  (evaluator-commit <pending>)

This is the seventh evaluator pass and a **grading-only** weight recalibration. No
design-affecting commit has touched the task since the 2026-06-12 block; this pass
only redistributes subcheck `weight=` values in `grade.py`. No task.json version bump,
no change to check logic, thresholds, gates, inputs, reference, or broken outputs.

### Change
**RECALIBRATED.** Replaced the blunt repo-wide `weight=3.0`-on-data-content scheme
(commit c749e57) with a severity-tiered weighting reasoned from what this L3 routing
task actually tests. The central skill is **correct network routing / shortest-path /
service-area computation**; the subchecks that fail iff that math is wrong now carry
the highest weight, while mechanical counts and structural/CRS-cosmetic checks sit lower.

Key altitude fix: `distance_matrix_rank_order` (a central routing-correctness check —
distances must be monotone-by-rank, which is only true if routing is correct) was stuck
at the default weight 1.0 while four mechanical **count** checks were at 3.0. That was an
inverted altitude: a core correctness check weighted like cosmetic, derivable scaffolding
weighted like core. Counts are largely mechanical (8 incidents from the CSV, one route per
incident, 8x3 matrix, one isochrone per fetched hospital) and do not evidence correct
routing — `broken_wrong_geometry` passes every count yet has 5x-inflated distances.

#### Weight changes (changed only)
| Subcheck | old | new | rationale |
|---|---|---|---|
| closest_hospital_distances | 3.0 | 4.0 | most direct network-routing-correctness signal (tight ±15%); top tier |
| distance_matrix_rank_order | 1.0 | 3.0 | central: monotone-by-rank ordering only holds if routing is correct; was mis-weighted as structural |
| incident_count | 3.0 | 2.0 | mechanical (CSV row count); not evidence of routing |
| closest_hospital_count | 3.0 | 2.0 | mechanical (one row per incident) |
| distance_matrix_count | 3.0 | 2.0 | mechanical (8x3 arithmetic) |
| isochrone_count | 3.0 | 2.0 | mostly fetch-completeness, not routing math |

Unchanged: `closest_hospital_names` 3.0, `isochrone_hospital_names` 3.0 (data-content:
right hospital set found/matched); `isochrone_coverage_iou` 3.0 (central service-area
correctness, kept a notch below distances because its 0.50 IoU threshold is deliberately
soft — convex-hull approximation is one valid method); `isochrone_area_plausible` 1.0,
`geometry_types_per_layer` / `min_feature_counts` / `incident_coords_in_metres` 1.0
(structural); `crs_is_canonical` / `crs_in_meaningful_set` 1.0 (cosmetic regional-
convention preference per HR-001 resolution). Total weight 31 -> 30.

#### Broken-score before -> after
| Broken | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.00 | 0.00 | gate fail (GeoJSON, no layers) — unaffected by weights |
| partial | 0.29 | 0.30 | incomplete + scrambled: fails 8 content/rank checks, passes only IoU+area+structural; at inclusive upper bound of [0.1,0.3] |
| wrong_geometry | 0.77 | 0.73 | central routing wrong (5x distances, tiny isochrones) but scaffolding+hospital-set right; drop reflects the up-weighted distances/IoU/area failures |

Ordering: 0.00 < 0.30 < 0.73 < 1.00 — monotone and defensible. Note the disjoint-failure
trap: `wrong_geometry` and `partial` fail *different* subchecks. `wrong_geometry`'s only
failures (distances, IoU, area) are all *passed* by `partial`, so any up-weight that drops
`wrong_geometry` also lifts `partial`. This caps how far `wrong_geometry` can fall without
pushing `partial` out of range. `partial` lands exactly at 0.30 (inclusive bound); I kept
`isochrone_coverage_iou` at 3.0 (it is a genuine service-area-correctness check and belongs
in the routing tier) rather than demoting it to 2.0 purely to seat the broken lower. The
0.30 boundary is documented here as the intended, defensible value.

#### Prior-run re-grade summary
Re-graded a representative spread of prior submissions that wrote a GPKG (old = prior
weighted c749e57 grader score, from the 2026-06-12 re-grade matrix where available;
new = this pass's weights):
| Run | Adapter / CRS | old | new |
|---|---|---|---|
| run-20260609-084636Z | deepseek basic, EPSG:2154 (current) | 1.0 | 1.0 |
| run-20260608-074701Z | deepseek detailed, partial (failed run) | 0.387 | 0.433 |
| run-20260607-112430Z | gemma detailed | 0.226 | 0.20 |
| run-20260528-1927Z | opus, EPSG:2154 | 1.0 | 1.0 |
| run-20260528-2225Z | gemma, right CRS / wrong matching | 0.516 | 0.50 |
| run-20260528-2332Z | opus, EPSG:2154 | 1.0 | 1.0 |
| run-20260528-0317Z | gemma, EPSG:2154 | 0.455 | 0.467 |
| run-20260517-1424Z | deepseek, EPSG:32631 (UTM 31N) | 0.581 | 0.567 |
| run-20260526-1753Z | opus, EPSG:2154 | 1.0 | 1.0 |

No ordering inversions, no significant shifts (all within ~±0.05). Strong/clean runs hold
at 1.0; structurally-valid-but-semantically-wrong work stays in the 0.2-0.57 band. The
UTM-31N run (HR-001 evidence) holds at 0.567 — the CRS-cosmetic penalty is preserved and
remains one weighted-1.0 failure among substantive ones.

#### Reasoning
The c749e57 commit applied a flat 3.0 to eight "data-content" checks and left everything
else at 1.0 across every grader. For this task that bundled mechanical counts (high signal-
to-effort, low correctness-evidence) together with the genuine routing-correctness checks,
and left `distance_matrix_rank_order` — a real correctness check — at structural weight.
The recalibration restores altitude: routing-correctness (distances 4, rank 3, IoU 3) >
right-hospital-set (names 3) > derivable counts (2) > structural/CRS-cosmetic (1). A
meaningful/central mistake (wrong routing math) now costs more than a cosmetic slip (UTM
vs Lambert), and the broken ordering is preserved within the constraint imposed by the
disjoint failure sets.

### Changes applied this run

#### Unilateral edits
- `grade.py`: subcheck `weight=` values only (table above). No logic/threshold/gate change.
- `metadata.yaml`: `broken_solutions > measured_score` refreshed (wrong_geometry 0.77 -> 0.73, partial 0.29 -> 0.30) under the new weights. Ranges unchanged (both still in range). No version bump.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none — human_review_items is empty and stays empty)

#### Tests run
- grader on reference: 1.00 (15 subchecks, weighted 30/30)
- grader on broken_wrong_format: 0.00, broken_wrong_geometry: 0.73, broken_partial: 0.30 — all within declared ranges
- pytest: not run (orchestrator runs the suite)
