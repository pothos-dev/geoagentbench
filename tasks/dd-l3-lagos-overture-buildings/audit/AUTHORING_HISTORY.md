# Implementation notes — dd-l3-lagos-overture-buildings

## Status
completed

## Summary
L3 data-discovery task that fetches ~2.8 M buildings from Overture's S3 bucket with partition pushdown, reprojects to EPSG:26331 for area calculation, filters to footprints > 1000 m² (7730 buildings), spatial-joins with 20 Lagos LGA boundaries (also from Overture divisions), and outputs a GeoParquet + a per-LGA summary Parquet.

## Verification results
- Reference grader score: 1.00 (9/9 subchecks)
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - no_area_filter: 0.44 (expected range [0.30, 0.55])
  - wrong_crs_area: 0.78 (expected range [0.65, 0.85])
- Second-run output match: bit-identical (same Overture release, deterministic sort by id)
- Library tests after task: pass

## Failure-mode coverage
- Mode 1 (downloads entire theme): not-handled (task deadline enforces)
- Mode 2 (wrong output format): broken_wrong_format
- Mode 3 (skips area filter): broken_no_area_filter
- Mode 4 (area in WGS84 degrees²): broken_wrong_crs_area
- Mode 5 (wrong CRS for area): principled-reasoning (summary_area_reasonable subcheck)
- Mode 6 (no LGA spatial join): principled-reasoning (summary_lga_overlap subcheck)
- Mode 7 (includes non-Lagos LGAs): principled-reasoning (summary_lga_overlap + consistency)
- Mode 8 (missing summary file): principled-reasoning (Gate 1 fails)

## Open issues
- [severity: low] — The "unassigned" LGA category (1494 buildings, 19%) represents buildings in the bbox but outside all 20 Lagos LGA polygons. This includes Ogun State spillover and lagoon/water areas. An agent that clips buildings to the union of LGA polygons instead of the bbox would get a lower count, but should still pass the ±10% tolerance.
- [severity: low] — Overture height data is very sparse for Lagos (~4% of large buildings). The p50_height_m subcheck only verifies column existence and plausible values, not precise median agreement, since the sparse data makes median unstable across releases.

## Suggested prompt changes
Empty.

## Inventory change proposals
Empty.

## Library extensions
Empty.

## Runtime
~8 minutes (dominated by Overture S3 fetch for buildings theme)

---

## Evaluator review 2026-05-26  (evaluator-commit pending)

### 1. Design history

#### Initial design intent
Authored as an L3 data-discovery task probing the full real-world workflow of (a) querying Overture's cloud-hosted GeoParquet buildings theme via partition pushdown over a Lagos bbox, (b) reprojecting to EPSG:26331 (Minna / Nigeria West Belt) for honest m² areas, (c) filtering footprints > 1000 m², (d) spatial-joining with the 20 Lagos LGA polygons from Overture divisions.division_area, and (e) emitting a GeoParquet of buildings + a tabular Parquet summary with null-aware height stats. Reference yields 7730 buildings across 20 LGAs (+ "unassigned") at Overture release 2026-04-15.0. Tolerances are intentionally generous (count_pct 0.10, area_pct 0.20, jaccard_min 0.80) to absorb Overture release-to-release drift and reprojection-implementation drift across pyproj/GDAL/DuckDB.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-11 | 5448998 | initial-authoring | Initial task: grade.py, metadata, README, reference outputs + generator, broken sets (wrong_format, no_area_filter, wrong_crs_area), task.json | Initial commit |
| 2026-05-12 | a3a6b45 | initial-authoring | Re-landed task at completed state (cleanup commit; commit message: L3 data-discovery task, reference scores 1.00, broken solutions 0.0/0.44/0.78) | Commit msg: completed task land |
| 2026-05-12 | a0d1c2b | docs-change | Empty diff (re-commit) | Why: not stated in commit message |
| 2026-05-13 | 1710715 | prompt-change | Added explicit output schema block: "Required columns in lagos_buildings.geoparquet: ..." + summary columns | Commit msg: declare exact output schema in prompts to match graders |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ -> benchmark/tasks/ | Repo-wide path move |
| 2026-05-13 | 284b843 | docs-change | Added structured tags dict to task.json (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) | Commit msg: filtering metadata, derived from inventory axes |
| 2026-05-13 | 8915010 | docs-change | Added assets/image-prompt.md | Commit msg: generate image prompts for all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Added assets/image.webp | Commit msg: generate image.webp for all 36 task dirs |
| 2026-05-13 | 3c65373 | docs-change | Regenerated image.webp via FLUX | Commit msg: regenerate all 36 task card images |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated image.webp via nano-banana-2 | Commit msg: regenerate task card images |
| 2026-05-13 | 9b1fb11 | prompt-change | Merged output-schema bullet block into prose; replaced "Two output files: lagos_buildings.geoparquet (EPSG:4326, Polygon/MultiPolygon) and lagos_building_summary.parquet (plain Parquet, no geometry column)" + bullet list with single prose paragraph that still names columns | Commit msg: Merge output schema blocks into prose for 7 task instructions |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped "buildings.building theme", "partition pushdown on the S3 bucket, don't download the whole thing" still implied via "pull from Overture via partition pushdown"; replaced "divisions.division_area" with "Overture administrative boundaries"; dropped "Polygon or MultiPolygon" hint from output spec | Commit msg: Remove input CRS, geometry types, column names, format descriptions, data hints, encoding specifics |
| 2026-05-15 | d343152 | prompt-change | Aggressive second strip: removed the partition-pushdown hint entirely, removed "Compute footprint areas in EPSG:26331 (Minna / Nigeria West Belt), keep only those above the threshold, export geometries in WGS84", removed "Grab Lagos Local Government Area boundaries from Overture administrative boundaries, spatial-join the filtered buildings" — agent must now infer the projection choice, the reprojection-for-area need, the theme name, and the spatial join from first principles | Commit msg: Strip deducible information from DD task instructions |
| 2026-05-18 | ca47dbd | grader-change | _is_wgs84(None) flipped from False to True (RFC 7946 default for GeoJSON without explicit CRS) | Commit msg: Treat missing CRS as WGS 84 in graders |
| 2026-05-18 | f0c244a | grader-change | Replaced local _is_wgs84 helper with shared geo_grading.comparisons.is_wgs84 | Commit msg: Consolidate WGS 84 CRS checks into shared geo_grading package |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorganisation: IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, reference/ -> reference/solution/, tests/ -> reference/failures/, image.webp + image-prompt.md -> assets/; grade.py path constants updated | Commit msg: Reorganize task folder layout |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-18T06:35:57+00:00 (commit f0c244a, class: grader-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T08:30:23Z | 0.0 | done | current (model-side: produced no output) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-05-17T15:27:33Z | 0.78 | done | stale |
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:20:28Z | 1.0 | done | stale |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T08:23:17Z | 0.67 | done | stale |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T03:41:27Z | 1.0 | done | stale |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T01:57:53Z | 1.0 | done | stale |
| run-20260516-2248Z | claude-code-opus-basic | 2026-05-16T23:44:07Z | 1.0 | done | stale |
| run-20260516-1130Z | claude-code-opus-basic | 2026-05-16T20:23:55Z | failed | done | stale (model-side: session stalled 600s) |
| run-20260516-0743Z | claude-code-opus-basic | 2026-05-16T08:12:23Z | 1.0 | done | stale |
| run-20260515-2053Z | claude-code-opus-basic | 2026-05-16T06:31:48Z | 1.0 | done | stale |
| run-20260515-0926Z | openrouter-deepseek-v4-flash-basic | 2026-05-15T11:10:52Z | 0.67 | done | stale |
| run-20260515-0624Z | claude-code-opus-basic | 2026-05-15T07:25:27Z | 1.0 | done | stale |
| (14 earlier stale runs omitted; all pre-d343152 prompt-strip or pre-grader-consolidation) | | | | | stale |

#### Verdict
**insufficient-evidence**

Only one run (Gemma 4 26B on 2026-05-26) is post-cutoff (2026-05-18T06:35:57+00:00, commit f0c244a). That run scored 0.0 by producing no output file at all — Gate 1 fails on missing lagos_buildings.geoparquet, no Overture fetch ever appears in session outputs. This is a **model-side failure**: a small open-source LLM with limited tool-use horizon cannot orchestrate a partition-pushdown DuckDB query against Overture S3 in a single basic-prompt session. Per the evaluator rubric, model-side failures are NOT task problems. Nothing about the task design is implicated.

The nearby stale runs (post-d343152 prompt-strip, pre-grader-consolidation) show a calibrated score distribution: Claude Opus 4.6 consistently 1.0 (7/7 successful), DeepSeek v4-flash spans 0.67–1.0, weak open-source models fail. That is the intended L3 calibration shape: strong models pass, mid-tier partially pass on principled subchecks, weak models miss the task entirely. The grader's nine subchecks discriminate cleanly (height_stats_present, summary_lga_overlap, area_filter_applied each catch a distinct failure mode). I have no concrete reason to suspect mis-calibration.

#### Specific findings
- Reference grader on reference/solution/outputs: 1.00 (9/9), confirmed this run.
- Pytest: 35/35 pass.
- Inventory row (`benchmark/authoring/inventory.md:172`) lists Overture themes as `buildings.building, buildings.building_part` — but `reference/solution/generate.py` only uses `buildings.building` (and `divisions.division_area` for the LGA join). `building_part` is never queried or referenced. The task.json tags also only list `buildings.building` and `divisions.division_area`. <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Inventory should be corrected to drop `buildings.building_part` and add `divisions.division_area`, OR the reference generator should query building parts (less likely intended given the metadata).
- Commit d343152 (2026-05-15) stripped the EPSG:26331 hint from the instruction, leaving the agent to deduce "reproject to an equal-area or projected CRS appropriate for Lagos to get m² areas" entirely from first principles. The README still names EPSG:26331 (Nigeria West Belt) explicitly in the "What this task probes" section, but README is not sent to the agent. Whether an agent must know "EPSG:26331 Minna / Nigeria West Belt" by name vs. picking any locally-suitable projected CRS (e.g. UTM 31N) is borderline: the grader does not check which CRS was used, only that the resulting m² values pass summary_area_reasonable (±20 % of the reference total footprint). UTM 31N over Lagos diverges from EPSG:26331 by < 0.5 % in area, so any reasonable projected choice passes. This is fine as authored — the task tests the *concept* of reprojecting for area, not memorising EPSG:26331 specifically. No change needed.
- The aggressive d343152 strip also removed the explicit "spatial-join the filtered buildings with divisions.division_area" cue. The agent must infer (a) that LGA boundaries exist in Overture's divisions theme and (b) that a within-style spatial join is required. The instruction still says "per-LGA roll-up" and "for each Lagos Local Government Area" — sufficient signal for a competent agent. Stale Claude Opus runs all succeed on this, confirming the cue is adequate. No change needed.
- The grader's `feature_set_jaccard` ≥ 0.80 threshold is loose enough that release-drift in Overture id minting will not penalise honest re-fetches. Aligns with the tolerance rationale in metadata.yaml. Calibrated.
- The grader's `area_filter_applied` subcheck uses a 900 m² threshold (10 % below the prompt-specified 1000 m²) to allow reprojection float drift, and requires ≥ 95 % of submitted buildings to clear it. Sensible.
- Model-side failures noted (not task issues): one current Gemma 4 26B no-output, one stale Claude Opus 600s stall, multiple stale Gemma adapter-wiring failures (cancelled, missing API key, connection error). All consistent with weak/misconfigured models, not task design problems.

### 3. Changes applied this run

#### Unilateral edits
None. The task is well-calibrated as authored. No tolerance loosen, no gift to strip, no broken-set re-grade needed (metadata.yaml broken_solutions.measured_score already matches expected ranges: 0.0 / 0.4444 / 0.7778).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — `authoring/inventory.md` row claims `buildings.building_part` is a source theme; the reference generator does not query it. Either correct the inventory or update the reference (latter is out of scope for the evaluator).

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- pytest: 35 passed, 0 failed

---

## Evaluator review 2026-05-26 (second pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the prior evaluator-review block above. L3 data-discovery task probing partition-pushdown fetch of Overture `buildings.building` over a Lagos bbox, reprojection to a projected CRS for honest m² area, a > 1000 m² footprint filter, a within-style spatial join against Overture `divisions.division_area` (subtype=county, region=NG-LA) to assign each building to a Lagos LGA, and a dual GeoParquet + tabular-Parquet output. Reference (Overture release 2026-04-15.0) yields 7730 buildings; the reference deliberately tags buildings inside the bbox but outside every named Lagos LGA polygon as a synthetic LGA value `"unassigned"` (1494 buildings, ~19 %), so the summary's `n_buildings` sum reconciles exactly with the building file.

#### Change log
No new design-affecting commits since the prior block. `git log --follow` confirms the only commits after the prior cutoff are the prior evaluator's own artefact commit (f670925, docs-change) and the folder reorg (29a9ae3, docs-change, already logged). The design-affecting cutoff is unchanged: **2026-05-18T06:35:57+00:00 (commit f0c244a, grader-change)**.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-26 | f670925 | docs-change | Prior evaluator committed audit/AUTHORING_HISTORY.md, coverage.yaml, audit/status.json (verdict insufficient-evidence) | Commit msg: Re-evaluate dd-l3-lagos-overture-buildings: insufficient-evidence |

### 2. Current-state review

This re-pass was triggered because two fresh runs from different agent families landed after the prior `insufficient-evidence` review, lifting the evidence above the 2-current-runs threshold.

#### Cutoff
- design-affecting cutoff: 2026-05-18T06:35:57+00:00 (commit f0c244a, class: grader-change). Unchanged.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-opus-4-7 | 2026-05-26T18:50:14Z | 0.78 | done | **current** |
| run-20260526-1922Z | google/gemma-4-26b-a4b-it | 2026-05-26T19:39:38Z | 0.56 | done | **current** |
| run-20260526-0748Z | google/gemma-4-26b-a4b-it | 2026-05-26T08:30:23Z | 0.0 | done | current (model-side: produced no buildings file) |
| (29 earlier runs) | claude-code-opus-basic / deepseek-v4-flash / gemma | ≤ 2026-05-17 | 0.67–1.0 | done | stale (pre-cutoff or pre f0c244a) |

Two distinct agent families now have current runs (Claude Opus 4.7; Gemma 4 26B). The evidence threshold for a diagnostic verdict is met.

#### Verdict
**prompt-grader-inconsistent** (borderline; flagged for human resolution, not unilaterally fixed)

The Claude Opus 4.7 run (run-20260526-1753Z, score 0.78) produced a **defensibly-correct** solution. Its building set is essentially identical to the reference (7727 vs 7730; `feature_set_jaccard` = 0.9991), it reprojected to UTM 31N for area (within ~0.5 % of the reference's EPSG:26331, so `area_filter_applied` passes at 100 %), it correctly spatial-joined to the 20 named Lagos LGAs, and it emitted clean per-LGA height stats. It nonetheless lost exactly two subchecks, and **both failures trace to one undocumented reference design choice**: whether buildings inside the bbox but outside every named Lagos LGA polygon (the reference's synthetic `"unassigned"` bucket, 1494 buildings ≈ 19 %) belong in the per-LGA summary.

- `summary_total_consistent` (FAIL): the agent's summary sums to 6233 `n_buildings`, but its building file holds 7727 — the 1494-building gap is precisely the buildings it (legitimately) left `lga = null` in the building file and excluded from a summary it scoped to *named* Lagos LGAs. The grader's ±5 % `sum(n_buildings)` vs building-file-count reconciliation silently requires the agent to invent the same `"unassigned"` row the reference did.
- `summary_area_reasonable` (FAIL, ratio 0.76): 14 452 888 m² vs reference 18 933 555 m². The reference total includes the unassigned buildings' area; the agent's named-LGA-only total is ~19 % lower, landing just under the 0.80 floor. **Same root cause.**

The instruction text (`task.json:14`) says only *"for each Lagos Local Government Area, the building count, total footprint area…"*. It never mentions an `"unassigned"` / out-of-LGA bucket, nor that `sum(n_buildings)` must equal the building-file count. The opus transcript shows the agent reasoned about this deliberately — its hand-off note states buildings whose representative point "falls outside Lagos State (the bbox bleeds into Ogun State) have `lga = null`" and it scoped the summary to the named LGAs accordingly. "For each Lagos LGA = the 20 named LGAs" is at least as defensible a reading as the reference's "+ an unassigned bucket." Two readings are defensible, so per the rubric I pick a default (the grader's reconciliation is over-tight relative to what the instruction licenses) and **flag** rather than edit.

The Gemma 4 26B run (0.56) is a genuine model-side under-fetch: only 41 of ~7730 buildings (Jaccard 0.0), almost certainly a botched / LIMIT-ed pushdown query. Its area math and CRS are fine; it simply fetched a tiny fraction of the data. This is a weak-model failure, not a task problem, and it shows the grader retains low-end resolution. The other current Gemma run (0748Z) produced no buildings file at all — model-side, score 0.

The grader is otherwise well-built: nine subchecks, broken solutions re-graded this pass at 0.0 / 0.4444 / 0.7778 (distinct ranges, matching metadata), generous L3 tolerances (count ±10 %, jaccard ≥ 0.80, area ±20 %) that absorb release drift. The single calibration concern is the `"unassigned"`-bucket assumption baked into `summary_total_consistent` and `summary_area_reasonable`.

#### Specific findings
- The two opus subcheck failures (`summary_total_consistent`, `summary_area_reasonable`) both stem from the reference's synthetic `"unassigned"` LGA bucket, which the instruction does not require the agent to reproduce. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> A human must decide the intended contract: (a) loosen/redefine `summary_total_consistent` to accept a building-file count that exceeds the summary's `n_buildings` sum by the out-of-LGA remainder (and widen `summary_area_reasonable`'s lower bound or compute the reference total over named LGAs only), or (b) add a sentence to the instruction requiring an `"unassigned"` / out-of-LGA row so all buildings are accounted for. Either edit touches `grade.py`+`metadata.yaml` or `task.json`+`reference/solution/generate.py`; the grader-vs-prompt choice is a genuine judgment call, so it is not applied unilaterally. Note option (a)'s area fix may need a reference re-run (reference/ is out of evaluator scope — see HR-002 dependency).
- Reproduction-of-prior finding: the inventory row (`benchmark/authoring/inventory.md:172`) still lists Overture themes `buildings.building, buildings.building_part`, but `reference/solution/generate.py` queries only `buildings.building` and `divisions.division_area`. `building_part` is never used. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Correct the inventory to drop `buildings.building_part` and add `divisions.division_area`, OR (less likely intended) extend the reference to query building parts. Carried over from the prior block's HR-001.
- The EPSG:26331-vs-any-projected-CRS question (stripped from the instruction in commit d343152) remains correctly calibrated: opus chose UTM 31N and still passed `area_filter_applied`; the grader tests the *concept* of reprojecting for area, not memorising EPSG:26331. No change needed.
- Reference grader on reference/solution/outputs re-confirmed 1.00 (9/9) this pass; pytest 35/35.

### 3. Changes applied this run

#### Unilateral edits
None. The single calibration concern (the `"unassigned"`-bucket assumption) is a borderline prompt-vs-grader judgment whose fix would require either a grader+metadata change with a defensible-either-way rationale or a reference edit (out of evaluator scope). Per the rubric, borderline calls are flagged, not applied. Broken-solution `measured_score` values in metadata.yaml already match this pass's re-grade (0.0 / 0.4444 / 0.7778), so no metadata update is warranted.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (med) — `summary_total_consistent` + `summary_area_reasonable` penalise a defensibly-correct output because the reference invents an `"unassigned"` LGA bucket the instruction never requires. Resolve by loosening the grader OR by adding an out-of-LGA-row requirement to the instruction.
- HR-002 — inventory-mismatch (low) — inventory lists `buildings.building_part`; reference never queries it. Carried over.

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- broken solutions re-graded: wrong_format 0.0, no_area_filter 0.4444, wrong_crs_area 0.7778 (match metadata)
- pytest: 35 passed, 0 failed

---

## Evaluator review 2026-05-27 (third pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the prior two evaluator-review blocks. L3 data-discovery task: partition-pushdown fetch of Overture `buildings.building` over the Lagos bbox (3.1, 6.35, 3.7, 6.75), reproject to a projected CRS for honest m² areas, filter footprints > 1000 m², a within-style spatial join against Overture `divisions.division_area` (subtype=county, region=NG-LA) to assign each building to a Lagos LGA, and a dual GeoParquet + tabular-Parquet output with null-aware height stats. The reference (`reference/solution/generate.py`, Overture release 2026-04-15.0) tags bbox-internal buildings outside every named Lagos LGA polygon as a synthetic `lga = "unassigned"` (1494 buildings, ~19 %) so the summary's `n_buildings` sum reconciles exactly with the building file.

#### Change log
No new commits touch the task directory since the prior (second-pass) block. `git log --follow -- benchmark/tasks/dd-l3-lagos-overture-buildings/` shows the most recent commit after the second-pass review is the second pass's own artefact commit (13513d9, docs-change, verdict prompt-grader-inconsistent). The design-affecting cutoff is unchanged: **2026-05-18T06:35:57+00:00 (commit f0c244a, grader-change)**.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-26 | 13513d9 | docs-change | Second-pass evaluator committed audit/AUTHORING_HISTORY.md, coverage.yaml, audit/status.json (verdict prompt-grader-inconsistent) | Commit msg: Re-evaluate dd-l3-lagos-overture-buildings: prompt-grader-inconsistent (2 current runs, opus 0.78 / gemma 0.56) |

### 2. Current-state review

This third pass found the task state, evidence, and runs identical to the second pass — no new design-affecting commits and no new runs. It independently re-verified the second pass's findings against the run artefacts (score.json, output Parquet files, transcript) rather than trusting the prior narrative, and confirms them.

#### Cutoff
- design-affecting cutoff: 2026-05-18T06:35:57+00:00 (commit f0c244a, class: grader-change). Unchanged.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-opus-4-7 | 2026-05-26T18:50:14Z | 0.78 | done | **current** |
| run-20260526-1922Z | google/gemma-4-26b-a4b-it | 2026-05-26T19:39:38Z | 0.56 | done | **current** |
| run-20260526-0748Z | google/gemma-4-26b-a4b-it | 2026-05-26T08:30:23Z | 0.0 | done | current (model-side: produced no buildings file) |
| (29 earlier runs) | claude-code-opus-basic / deepseek-v4-flash / gemma | ≤ 2026-05-17 | 0.67–1.0 | done | stale (pre-cutoff f0c244a) |

Two distinct agent families have current runs (Claude Opus 4.7; Gemma 4 26B). The evidence threshold for a diagnostic verdict is met. These are the same three current runs the second pass analysed; no run has landed since.

#### Verdict
**prompt-grader-inconsistent** (borderline; reaffirmed, flagged for human resolution, not unilaterally fixed)

Independent re-verification this pass:
- Opus run score.json: passes 7/9 subchecks; fails exactly `summary_total_consistent` (sum n_buildings 6233 vs building-file count 7727, ±5 %) and `summary_area_reasonable` (14 452 888 m² vs reference 18 933 555 m², ratio 0.76, need ≥ 0.80).
- Re-read the opus building + summary outputs directly: 7727 buildings (building_count_tolerance passes vs 7730; Jaccard 0.9991), CRS WGS84, of which **1494 carry `lga = None`** — the exact out-of-LGA remainder. The summary has 20 named-LGA rows (incl. Badagry with 0) and **no `"unassigned"` row**; its `n_buildings` sum is 6233 = 7727 − 1494, and its footprint total is ~19 % below the reference because the reference's total includes the unassigned buildings' area.
- Re-read the opus transcript hand-off note: the agent deliberately reasoned that "buildings whose representative point falls outside Lagos State (the bbox bleeds into Ogun State) have `lga = null`" and scoped the summary to "one row per Lagos State LGA (all 20)". This is a defensible reading of the instruction's "for each Lagos Local Government Area"; the instruction (`task.json:14`) never requires an unassigned / out-of-LGA row, nor that `sum(n_buildings)` equal the building-file count.

Both opus failures therefore trace to one undocumented reference design choice (the synthetic `"unassigned"` bucket), which the grader's `summary_total_consistent` reconciliation and `summary_area_reasonable` reference-total silently require the agent to reproduce. Two readings are defensible → per the rubric, pick a default (the grader is over-tight relative to what the instruction licenses) and **flag** rather than edit.

The Gemma 4 26B run (0.56) is a genuine model-side under-fetch (41 of ~7730 buildings, Jaccard 0.0 — botched/LIMIT-ed pushdown); its CRS and area math are fine, so the grader retains low-end resolution. The other current Gemma run (0748Z) produced no buildings file — model-side, score 0. Neither is a task problem.

The grader is otherwise well-built and well-calibrated: nine discriminating subchecks; broken solutions re-graded this pass at 0.0 / 0.4444 / 0.7778 (distinct ranges, matching metadata); generous L3 tolerances (count ±10 %, jaccard ≥ 0.80, area ±20 %) that absorb release drift. The single calibration concern is the `"unassigned"`-bucket assumption baked into two subchecks.

#### Specific findings
- The two opus subcheck failures (`summary_total_consistent`, `summary_area_reasonable`) both stem from the reference's synthetic `"unassigned"` LGA bucket, which the instruction does not require the agent to reproduce. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> A human must decide the intended contract: (a) loosen/redefine `summary_total_consistent` to accept a building-file count that exceeds the summary's `n_buildings` sum by the out-of-LGA remainder (and compute `summary_area_reasonable`'s reference total over named LGAs only / widen its lower bound), OR (b) add a sentence to the instruction requiring an `"unassigned"` / out-of-LGA row so every building is accounted for. Option (a) touches `grade.py` + `metadata.yaml` and may need a reference re-run; option (b) touches `task.json` + `reference/solution/generate.py`. The grader-vs-prompt choice is a genuine judgment call, so it is not applied unilaterally. Reaffirmed from the second pass.
- The inventory row (`benchmark/authoring/inventory.md:172`) still lists Overture themes `buildings.building, buildings.building_part`, but `reference/solution/generate.py` queries only `buildings.building` and `divisions.division_area`; `building_part` is never used (and the thesis `<overture-theme-table>` lists `buildings.building_part` as a valid theme, so this is a per-task spec mismatch, not a vocabulary gap). <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Correct the inventory to drop `buildings.building_part` and add `divisions.division_area`, OR (less likely intended) extend the reference to query building parts. Carried over from both prior blocks.
- The EPSG:26331-vs-any-projected-CRS question (stripped from the instruction in commit d343152) remains correctly calibrated: opus chose UTM 31N and still passed `area_filter_applied` at 100 %; the grader tests the *concept* of reprojecting for area, not memorising EPSG:26331. No change needed.
- Reference grader on reference/solution/outputs re-confirmed 1.00 (9/9) this pass; pytest 35/35.

### 3. Changes applied this run

#### Unilateral edits
None. The single calibration concern (the `"unassigned"`-bucket assumption) is a borderline prompt-vs-grader judgment whose fix would require either a grader+metadata change with a defensible-either-way rationale or a reference edit (out of evaluator scope). Per the rubric, borderline calls are flagged, not applied. The broken-solution `measured_score` values in metadata.yaml already match this pass's re-grade (0.0 / 0.4444 / 0.7778), so no metadata update is warranted.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (med) — `summary_total_consistent` + `summary_area_reasonable` penalise a defensibly-correct output (opus, Jaccard 0.9991 vs reference) because the reference invents an `"unassigned"` LGA bucket the instruction never requires. Resolve by loosening the grader OR by adding an out-of-LGA-row requirement to the instruction. Reaffirmed.
- HR-002 — inventory-mismatch (low) — inventory lists `buildings.building_part`; reference never queries it. Carried over from both prior passes.

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- broken solutions re-graded: wrong_format 0.0, no_area_filter 0.4444, wrong_crs_area 0.7778 (match metadata)
- pytest: 35 passed, 0 failed

---

## Evaluator review 2026-05-28 (fourth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior blocks at the level of the task's purpose: an L3 data-discovery task probing the full real-world workflow of polygon-driven Overture scope (the agent must derive a Lagos State boundary, derive its bbox for S3 partition pushdown, fetch buildings via DuckDB, reproject to a metric CRS for honest m² area, filter > 1000 m², spatial-join to the 20 Lagos LGAs, and emit a dual GeoParquet+plain-Parquet output with null-aware height stats). The **reference design has changed** since the third pass: commit 75b5339 (2026-05-28) replaced the hand-picked task bbox with a Lagos-State-polygon-driven scope and dropped the synthetic `"unassigned"` LGA bucket by construction (any building whose representative point falls outside every named LGA polygon is dropped, not bucketed). The new reference yields **7250 buildings across all 20 LGAs** at Overture release 2026-04-15.0.

#### Change log
Two new commits touch the task directory since the third-pass block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-27 | cec97df | docs-change | Third-pass evaluator committed audit/AUTHORING_HISTORY.md, coverage.yaml, audit/status.json (verdict prompt-grader-inconsistent, reaffirmed) | Commit msg: Re-evaluate dd-l3-lagos-overture-buildings: prompt-grader-inconsistent (3rd pass, reaffirmed; opus 0.78 / gemma 0.56) |
| 2026-05-28 | 75b5339 | mixed (prompt-change + grader-change + reference-change + tests-change) | Resolves third-pass HR-001 by redesigning the scope from a hand-picked bbox to the Lagos State boundary polygon from Overture divisions (subtype='region', country='NG', names.primary='Lagos'). Because the 20 NG-LA LGAs partition the state polygon, every retained building lands in exactly one LGA — the synthetic `"unassigned"` bucket goes away by construction, and the grader's `summary_total_consistent` / `summary_area_reasonable` subchecks become unambiguous. Files: `task.json` (drops the hand-supplied bbox; instruction now scopes to "Lagos State (Nigeria) from Overture"), `reference/solution/generate.py` (fetches state polygon first, derives bbox from polygon bounds, drops slivers instead of bucketing), `reference/solution/outputs/` (regenerated: 7250 buildings across all 20 LGAs — the old bbox had missed Badagry and clipped most of Epe / Ibeju Lekki, yielding 7730 across 19 + unassigned), `reference/failures/_make_brokens.py` (new helper deriving all three broken sets from the reference + one extra Overture fetch), `reference/failures/broken_*/outputs/` (regenerated; new no_area_filter scores 0.5556 — up from 0.4444 — because its summary now reconciles internally), `grade.py` (replaces the hard-coded task-bbox window in `crs_wgs84_coords` with a Lagos-State window 2.5–4.5°E, 6.3–6.8°N; other subchecks unchanged), `README.md` + `metadata.yaml` (narrative aligned, retired "+ unassigned" language, refreshed measured_scores and expected_score_range for no_area_filter). | Commit msg: Resolve dd-l3-lagos-overture-buildings HR-001 via Lagos-State polygon scope |
| 2026-05-28 | fbb3596 | docs-change | Review-queue skill cleanup commit drained the resolved HR-001 entry from `audit/status.json`. Touches only `audit/status.json` for this task (does not change any agent-visible or grader-visible state). | Commit msg: review-queue: clear resolved-HR entries; bundle status.json into Resolve commits going forward |

Commit 75b5339 is a `mixed` class touching prompt + grader + reference + tests in one logical change, so the design-affecting cutoff jumps from `2026-05-18T06:35:57+00:00` (the prior `grader-change` f0c244a) to **2026-05-28T11:23:46+00:00** (75b5339).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T11:23:46+00:00** (commit 75b5339, class: mixed prompt+grader+reference+tests; resolves the third-pass HR-001).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T03:17:33Z | 0.56 | done | stale (pre-cutoff) |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T01:13:49Z | 0.78 | done | stale (pre-cutoff) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:21:16Z | 0.00 | done | stale (pre-cutoff; model-side: no buildings file) |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T20:16:18Z | 0.78 | done | stale (pre-cutoff) |
| (30 earlier runs) | claude-code-opus-basic / deepseek-v4-flash / gemma | ≤ 2026-05-26 | 0.0–1.0 | done | stale (pre-cutoff) |

**No `current` runs.** Every existing run started before 2026-05-28T11:23:46Z. Two opus runs in the recently-stale window scored 0.78 against the pre-resolution grader; both failed exactly `summary_total_consistent` and `summary_area_reasonable` for the `"unassigned"` reason now resolved by commit 75b5339. The next sweep will produce post-cutoff evidence; this pass cannot diagnose from runs.

#### Verdict
**insufficient-evidence**

Per the rubric: with zero `current` runs, the diagnostic part of Step 2 stops. No `HUMAN-REVIEW grader-miscalibration-suspected` is warranted — I have no concrete reason to suspect the post-resolution grader is mis-calibrated. The reference grader self-passes 9/9; broken solutions re-grade to 0.0 / 0.5556 / 0.7778 (matching the updated `metadata.yaml > broken_solutions > measured_score` values committed in 75b5339); pytest 41/41 pass.

#### Specific findings
- The HR-001 resolution (commit 75b5339) is internally consistent and self-grades to 1.00 on reference; broken sets land at 0.0 / 0.5556 / 0.7778, matching the updated `metadata.yaml` ranges (`no_area_filter` widened to `[0.45, 0.65]`, `wrong_format` and `wrong_crs_area` unchanged). The grader change (replacing the task-bbox window in `crs_wgs84_coords` with a Lagos-State window 2.5–4.5°E, 6.3–6.8°N) tracks the polygon-scope change exactly: the reference's actual bounds are `[2.71, 6.38, 4.33, 6.70]`, well inside the new window. Coherent.
- The instruction in `task.json:14` says only *"every building footprint exceeding 1000 m² across Lagos State (Nigeria) from Overture"* and *"for each Lagos Local Government Area"* — no bbox, no EPSG, no theme name, no spatial-join verb. This matches the L3 spec ("agent must infer scope, projection, theme, and join from first principles") and is consistent with the resolution rationale (`"unassigned"` was the only documented prompt-vs-grader gap, now closed by construction).
- The `EPSG:4326 GeoParquet` phrasing in the instruction is **not** a redundant CRS gift: GeoParquet (unlike GeoJSON / RFC 7946) does not pin a CRS by format convention, so the EPSG:4326 hint is necessary information about the output's geometry CRS. Step 4's "strip CRS for GeoJSON" rule does not apply.
- No within-paragraph redundancies of the kind Step 4 enumerates (attribute preservation, geometry type, output filename, identity key, CRS for GeoJSON). The instruction is already tight.
- Inventory mismatch (HR-002 carried over): `benchmark/authoring/inventory.md:165` still lists "Format in: GeoParquet (Overture `buildings.building`, `buildings.building_part`)" and `:172` still lists "Overture themes: `buildings.building`, `buildings.building_part`". The thesis `<overture-theme-table>` aggregate (lines 1088–1089) also credits this task with `buildings.building_part`. The post-resolution `reference/solution/generate.py` queries only `divisions.division_area` (twice — for state polygon and LGA polygons) and `buildings.building`; `building_part` is never used. <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Correct the inventory to drop `buildings.building_part` from the row, the format-in line, and the thesis aggregate, OR (less likely intended for a flood-risk model) extend the reference to query building parts. Carried over from passes 1–3 (was HR-001 in the first block, HR-002 in passes 2 and 3).
- Reference grader on reference/solution/outputs: 1.00 (9/9). Pytest 41/41.

### 3. Changes applied this run

#### Unilateral edits
None. The HR-001 resolution was applied by the human in commit 75b5339 (a deliberate prompt + grader + reference + tests redesign, out of evaluator scope for the unassigned-bucket fix per the third-pass note). The carried-over HR-002 (inventory mismatch) is outside the task directory and the unilateral-edit list — flagged only.

No `task.json.version` bump this pass: there are zero unilateral edits this pass that change the prompt/grader/inputs contract, and 75b5339's content changes were the human resolver's responsibility (the version field had not yet been introduced at the time of that commit; the project-wide `version` rollout in 622342b — which post-dates 75b5339 — explicitly grandfathers all existing task.json files at implicit v1). The next unilateral evaluator edit will be the one that writes `"version": 2`.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch (low) — `authoring/inventory.md` row, format-in line, and the thesis Overture-theme aggregate still credit this task with `buildings.building_part`; the post-resolution reference queries only `buildings.building` (+ `divisions.division_area`). Correct the inventory or extend the reference. Carried over.

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- broken solutions re-graded: wrong_format 0.0, no_area_filter 0.5556, wrong_crs_area 0.7778 (match updated metadata.yaml)
- pytest: 41 passed, 0 failed

---

## Evaluator review 2026-06-06 (fifth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior blocks. L3 data-discovery task: polygon-driven scope (Lagos State boundary from Overture divisions, post-75b5339), bbox-pushdown S3 fetch of `buildings.building`, reproject to a metric CRS for honest m² area, > 1000 m² filter, within-style spatial join against the 20 Lagos LGAs (county-level, `region='NG-LA'`), dual GeoParquet+plain-Parquet output with null-aware height stats.

#### Change log
Two new commits since the fourth-pass block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 94a95f3 | docs-change | Fourth-pass evaluator artefacts (audit/AUTHORING_HISTORY.md, coverage.yaml, audit/status.json; verdict insufficient-evidence post HR-001 resolution) | Commit msg: Re-evaluate dd-l3-lagos-overture-buildings: insufficient-evidence post HR-001 resolution (cutoff jumped to 75b5339) |
| 2026-05-28 | 05aabd6 | grader-change | Replaced the hard-fail CRS gate in `grade.py` with the new `grade_crs_soft` helper. Gate-1 now only rejects submissions with **no** usable CRS; the agent's actual CRS choice is graded via two new subchecks (`crs_is_canonical`, `crs_in_meaningful_set`). `CANONICAL_EPSG = 4326`, `MEANINGFUL_EPSGS = {4326}` at module scope. Subcheck count rises from 9 to 11. | Commit msg: Soften CRS hard-fail to subcheck deductions across 21 graders |

Commit 05aabd6 is a grader-change, so the design-affecting cutoff advances from **2026-05-28T11:23:46+00:00** (75b5339) to **2026-05-28T19:02:57+00:00** (05aabd6).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57+00:00** (commit 05aabd6, class: grader-change).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-2225Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T23:03:55Z | 0.0 | done | **current** (Gate-2 fail: building bounds way outside Lagos window — agent emitted random coords) |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-29T00:00:40Z | 1.0 | done | **current** (11/11 subchecks) |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:36:35Z | 0.0 | done | **current** (model-side: no `lagos_buildings.geoparquet`) |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic (deepseek/deepseek-v4-pro) | 2026-05-31T12:07:13Z | 1.0 | done | **current** (11/11 subchecks) |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:03:34Z | null | failed | current (harness-side: JSONDecodeError) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:52:36Z | 0.0 | done | **current** (model-side: no `lagos_buildings.geoparquet`) |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | null | cancelled | current (no session) |
| (≥ 30 earlier runs) | claude-code-opus / deepseek / gemma | ≤ 2026-05-28T19:02Z | 0.0–1.0 | various | stale (pre-cutoff) |

Three agent families have current scored runs (Claude Opus 4.7, DeepSeek V4 Pro, Gemma 4 26B). The evidence threshold for a diagnostic verdict is met.

#### Verdict
**calibrated**

The score distribution this cutoff is exactly the intended L3 shape. Two strong-model runs (Claude Opus 4.7 → 1.0; DeepSeek V4 Pro → 1.0) score full marks against the post-resolution grader, with reference-comparable building counts (7316 / 7249 vs 7250), high Jaccard (0.9888 / 0.9982), per-LGA summaries that reconcile internally (`summary_total_consistent` passes), correct CRS, and aggregate footprint within 1 % of the reference. The opus run's bounds match the reference exactly: `[2.71, 6.38, 4.33, 6.70]` — i.e. opus actually discovered the Lagos State polygon and derived the bbox from it, the central design intent. The HR-001 resolution (Lagos-State polygon scope, no `"unassigned"` bucket) closes cleanly: opus, which lost 0.22 to the same prompt-vs-grader gap pre-resolution, now scores 1.0.

Weak-model runs (Gemma 4 26B, three current attempts) all fail at agent engineering, not at task design: one emitted gibberish bounds `[0.03, 0.57, 17.40, 17.23]` (no scoping to Lagos at all, likely a botched DuckDB query); two produced no `lagos_buildings.geoparquet` at all (no Overture fetch ever completed); one harness JSONDecodeError; one cancelled. Per the evaluator rubric, these are model-side failures and do not implicate the task. The grader retains low-end resolution (Gate 2 catches the gibberish-bounds case; Gate 1 catches the missing-file case).

The new 05aabd6 CRS subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) work as intended: opus and deepseek both delivered EPSG:4326 buildings, so both pass; the grader no longer hard-fails when the agent picks the wrong CRS, instead docking 1 or 2 subchecks of 11. No current run exercised the non-canonical-CRS path, but the helper is shared across 21 graders and tested in `geo_grading/tests/`.

Re-grading the broken solutions against the post-05aabd6 grader: `wrong_format` 0.0 (gate fail, unchanged), `no_area_filter` 0.6364 (was 0.5556 → 0.6364 mechanically; the two new CRS subchecks pass since the broken set has correct CRS), `wrong_crs_area` 0.8182 (was 0.7778 → 0.8182 same mechanic). All three new measured scores land in the expected ranges after widening the upper bounds on `no_area_filter` and `wrong_crs_area` to absorb the +2 subcheck denominator change. metadata.yaml > broken_solutions > measured_score and expected_score_range refreshed accordingly (no version bump — this is allowed by Step 4).

#### Specific findings
- The HR-001 resolution (commit 75b5339 — Lagos-State polygon scope) is empirically validated: both strong-model current runs score 1.0 with summaries that reconcile internally and footprint totals within 1 % of reference. Confirmed by `summary_total_consistent` and `summary_area_reasonable` passing on both runs.
- The CRS-softening grader change (commit 05aabd6) lands correctly: subcheck count is 11/11, both strong runs pass all 11, and the broken-set re-grade shifts are exactly +2 numerator and +2 denominator on the sets where CRS was correct (`no_area_filter`, `wrong_crs_area`). `wrong_format` Gate-1-fails before subchecks run, so its 0.0 is preserved.
- `task.json.analyst_notes` was missing; written this pass to document what the task tests (polygon scope, partition pushdown, metric CRS for area, area filter, LGA spatial join, dual-format output, null-aware height aggregation) and the seven principal pitfalls (degrees² area, downloading the whole theme, hand-picked bbox, no area filter, missing LGA join, wrong output format, NaN-unsafe height aggregation). Human-facing only; no version bump per Step 4.
- `task.json` carries no explicit `version` field; per commit 622342b's grandfathering, this is implicit v1. No unilateral edit this pass changes the prompt / grader logic / inputs / expected_outputs / tolerances, so no bump is triggered.
- Inventory mismatch carried over: `benchmark/authoring/inventory.md:165` (format-in line) and `:172` (Overture themes line) still credit this task with `buildings.building_part`; the thesis `<overture-theme-table>` aggregate (line 1089) does the same. The post-resolution `reference/solution/generate.py` queries only `divisions.division_area` (state polygon + LGA polygons) and `buildings.building` — `building_part` is never used and is not relevant to a flood-risk footprint roll-up. <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Drop `buildings.building_part` from the inventory row, the format-in line, and the thesis aggregate. Carried over from passes 1–4.
- The instruction's "EPSG:4326 GeoParquet" phrasing is not a redundant CRS gift (GeoParquet does not pin a CRS by format convention, unlike GeoJSON / RFC 7946). Within-instruction redundancy check: no duplicate attribute-preservation / geometry-type / output-filename / identity-key statements between the persona and schema sentences. Instruction is already tight.
- House-style audit on the instruction: opens with purpose ("Updating the flood-risk model"), no em-dashes, filenames referenced directly, units and schema columns explicit. The "Need every building..." and "Also need..." pattern reads slightly spec-grammar (dropped subject) but the prior four passes accepted it and the score distribution does not suggest the phrasing harms comprehension. Left in place.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `analyst_notes` block (description + 6-step approach + 7-item pitfalls). Re-grade on reference: 1.00 (11/11). Reason: field was missing; the task now reads cleanly in the eval UI alongside the prompt. Human-facing only — no version bump.
- `metadata.yaml`: refreshed `broken_solutions.no_area_filter.measured_score` 0.5556 → 0.6364 and `wrong_crs_area.measured_score` 0.7778 → 0.8182 to match the post-05aabd6 grader, and widened both `expected_score_range` upper bounds (`no_area_filter` `[0.45, 0.65]` → `[0.45, 0.70]`; `wrong_crs_area` `[0.65, 0.85]` → `[0.65, 0.90]`) to absorb the mechanical +2 subcheck denominator change. `wrong_format` unchanged at 0.0. Re-grade on reference: 1.00. Reason: keep `metadata.yaml` honest about current grader behaviour. Step 4 explicitly excludes `broken_solutions.measured_score` refreshes from the version-bump list.
- `audit/AUTHORING_HISTORY.md`: appended this evaluator-review block.
- `coverage.yaml`: refreshed timestamp + the post-cutoff note. No slug changes.
- `audit/status.json`: updated with current verdict and the carried-over HR-001.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch (low) — `authoring/inventory.md` row, format-in line, and the thesis Overture-theme aggregate still credit this task with `buildings.building_part`; the post-resolution reference queries only `buildings.building` (+ `divisions.division_area`). Drop the `building_part` entries or extend the reference. Carried over from passes 1–4.

#### Tests run
- grader on reference: 1.00 (11/11 subchecks)
- broken solutions re-graded: wrong_format 0.0, no_area_filter 0.6364, wrong_crs_area 0.8182 (match updated metadata.yaml)
- pytest: 41 passed, 0 failed

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Old Gate-2 "zero-row" check migrated to a new `buildings_non_empty`
  subcheck.
- Old Gate-2 "all geometries are Polygon/MultiPolygon" check migrated
  to a new `geometry_types_valid` subcheck.
- Old Gate-2 "total_bounds inside the generous Lagos WGS84 window"
  check migrated to a new `bounds_in_lagos_window` subcheck. This is
  distinct from the existing `crs_wgs84_coords` subcheck, which uses
  the tighter Lagos-State window.
- The downstream `crs_wgs84_coords` subcheck now guards against the
  zero-row case directly (previously relied on Gate 2 having killed
  the run before reaching it).
- Subcheck count: 11 → 14.

### Verification
- Reference solution re-graded: 1.0 (14/14 subchecks).

---

## Evaluator review 2026-06-12 (sixth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior blocks. L3 data-discovery task: polygon-driven scope (Lagos State boundary from Overture `divisions.division_area`, `subtype='region'`, post-75b5339), bbox-pushdown S3 fetch of `buildings.building` via DuckDB, reproject to a metric CRS for honest m² areas, > 1000 m² footprint filter, within-style spatial join against the 20 Lagos LGAs (`subtype='county'`, `region='NG-LA'`), dual GeoParquet + plain-Parquet output with null-aware height stats. Reference (Overture release 2026-04-15.0): 7250 buildings, 17 496 851 m² total footprint, 20 LGA rows.

#### Change log
Three new commits touch the task directory since the fifth-pass block (the second of which was already documented in the "Manual cleanup 2026-06-06" note appended with the commit itself):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 4d5832e | docs-change | Fifth-pass evaluator artefacts (AUTHORING_HISTORY, coverage.yaml, status.json, analyst_notes, broken-score refresh) | Commit msg: Re-evaluate dd-l3-lagos-overture-buildings: calibrated post 05aabd6 |
| 2026-06-06 | 363aed2 | grader-change | Dropped the `structural_correctness` gate; its three checks migrated to subchecks `buildings_non_empty`, `geometry_types_valid`, `bounds_in_lagos_window`; `crs_wgs84_coords` now guards the zero-row case itself. Subcheck count 11 → 14. | Commit msg: benchmark-wide one-hard-gate refactor so shape-recoverable outputs cost points instead of zeroing the score |
| 2026-06-07 | 632ad1a | grader-change | Seven data-content subchecks (`building_count_tolerance`, `feature_set_jaccard`, `area_filter_applied`, `summary_lga_overlap`, `summary_total_consistent`, `summary_area_reasonable`, `height_stats_present`) now carry `weight=3.0`; the seven schema/structural subchecks keep weight 1. Total weight 28. | Commit msg: schema-clean but data-wrong submissions should score visibly lower than data-correct ones with minor schema drift |

Shared-code note (outside the task dir, no cutoff effect): commit 501e9a6 (2026-06-09) extended `geo_grading.comparisons.grade_crs_soft` to accept multi-EPSG canonical sets for `spa-l2-lagos-hotspot-overlaps`. This grader calls it with a single int (`CANONICAL_EPSG = 4326`); the single-int path is explicitly unchanged, confirmed by re-grading the reference at 1.0 this pass.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:28:21+00:00** (commit 632ad1a, class: grader-change, 3x data-content weighting).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-06-09T10:30:50Z | 1.0 | done | **current** (suite ec540aa ⊇ 632ad1a; task v1 = current v1) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed (deepseek/deepseek-v4-flash) | 2026-06-08T10:24:43Z | 1.0 | done | **current** (suite 6510297 ⊇ 632ad1a; task v1 = current v1) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T13:42:38Z | 0.0 | failed | stale (pre-cutoff; model-side: max iterations exceeded) |
| run-20260607-080517Z | openrouter-gemma4-26b-detailed | 2026-06-07T08:05:17Z | null | failed | stale (pre-cutoff; model-side: max iterations exceeded) |
| run-20260607-060932Z | openrouter-deepseek-v4-flash-detailed | 2026-06-07T06:09:32Z | 1.0 | done | stale (pre-cutoff, scored at 363aed2 before weighting) |
| run-20260606-2050Z | openrouter-deepseek-v4-pro-detailed | 2026-06-06T20:50:17Z | 1.0 | done | stale (pre-cutoff) |
| run-20260606-2029Z | openrouter-deepseek-v4-flash-detailed | 2026-06-06T20:29:25Z | 1.0 | done | stale (pre-cutoff) |
| run-20260606-2011Z | openrouter-gemma4-26b-detailed | 2026-06-06T20:11:52Z | 0.71 | done | stale (pre-cutoff, first run scored under the gate-2-removal grader) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T18:22:10Z | 0.45 | done | stale (pre-cutoff) |
| (≥ 45 earlier runs) | opus / deepseek / gemma / sonnet | ≤ 2026-06-06 | 0.0–1.0 | various | stale (pre-cutoff; analysed in prior blocks) |

#### Verdict
**insufficient-evidence**

Exactly two runs post-date the 632ad1a cutoff and both come from a single agent family (DeepSeek v4-flash, one basic and one detailed prompt variant). Per the rubric, single-family evidence cannot support a diagnostic verdict. What the two runs do show is healthy: both scored 1.0 (14/14 weighted subchecks), with building counts 7272 / 7364 vs reference 7250 (inside ±10 %), id-Jaccard 0.9982 / 0.9808, bounds matching the reference Lagos-State bbox `[2.71, 6.38, 4.17–4.33, 6.70]`, EPSG:4326 GeoParquet output, internally-reconciling summaries, and aggregate footprints within 1.5 % of the reference total. Nothing suggests the 363aed2 gate-removal or the 632ad1a weighting destabilised the task; the fifth-pass `calibrated` verdict (three agent families) remains the best available calibration evidence, and both new grader changes are mechanical re-aggregations that cannot flip a correct submission to a fail (gate-2 removal only softens, weighting only re-weights existing pass/fail outcomes).

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output filenames (`lagos_buildings.geoparquet`, `lagos_building_summary.parquet`) | instruction, output paragraph | stated |
| GeoParquet in EPSG:4326 | instruction ("EPSG:4326 GeoParquet"; necessary — GeoParquet does not pin a CRS by convention) | stated |
| building columns `id`, `height`, `footprint_area_m2`, `lga`, `geometry` | instruction | stated |
| summary columns `lga`, `n_buildings`, `total_footprint_m2`, `n_with_height`, `p50_height_m`; no geometry | instruction | stated |
| > 1000 m² footprint filter (graded at > 900 m² for ≥ 95 % of rows) | instruction; the 10 % slack is grader-internal drift margin | stated / inferable |
| Lagos State scope (count ±10 %, Jaccard ≥ 0.80, bounds windows) | instruction ("across Lagos State (Nigeria) from Overture"); the agent derives the polygon/bbox from Overture divisions | stated / inferable |
| per-LGA roll-up with ≥ 70 % LGA-name overlap | instruction ("for each Lagos Local Government Area"); names come from the data | stated / inferable |
| sum(n_buildings) reconciles with building file (±5 %) | inferable (internal consistency of a roll-up over the same file; unambiguous post-75b5339 since no out-of-LGA bucket exists) | inferable |
| total footprint within ±20 % of reference | inferable (consequence of correct metric-CRS area) | inferable |
| null-aware height stats | instruction ("non-null Overture height", "median height where available (null otherwise)") | stated |
| metric-CRS reprojection for area | deliberately implicit (the L3 test); any sane metric CRS passes the ±20 % tolerance | inferable |
| geometry types Polygon/MultiPolygon | inferable (building footprints) | inferable |

Factual claims checked: both output filenames, all nine column names, the 1000 m² threshold, and "Lagos State (Nigeria)" verified against `reference/solution/outputs/` schemas and the Overture-derived data; no inaccurate claim found. No missing constraint.

#### Reference faithfulness
`reference/solution/generate.py` implements the instruction as written: state polygon → bbox pushdown → metric-CRS (EPSG:26331) area → > 1000 m² filter → representative-point LGA join → EPSG:4326 GeoParquet + per-LGA Parquet with null-aware height aggregation. **Faithful.** Two implementation details reviewed and judged non-deviations: (a) the DuckDB-side degree-area pre-filter (3e-8 deg² ≈ 370 m²) is a pure fetch optimisation strictly looser than the requested 1000 m² filter, so it cannot change the result set; (b) `total_footprint_m2` is rounded to 0.1 m² on sums of 10⁵–10⁷ m², which is presentation-level precision far inside the ±20 % grader tolerance and still "the total footprint area in m²". Reference output (7250 rows, EPSG:4326, 7237 Polygon + 13 MultiPolygon) matches `expected_outputs[]` and the README; the `expected_outputs[].geometry_type: "Polygon"` label is loose against the 13 MultiPolygons (0.18 %), but that field is free-form, machine-unenforced metadata benchmark-wide (values like "Mixed (…)" exist), the task tags/README/grader all document Polygon+MultiPolygon, and the agent never sees the field — recorded as informational, not flagged.

#### Specific findings
- metadata.yaml `broken_solutions.measured_score` values were stale against the 632ad1a weighted grader: re-graded this pass to `no_area_filter` 0.5714 (was 0.6364) and `wrong_crs_area` 0.7857 (was 0.8182); `wrong_format` unchanged at 0.0 (gate fail). Both new scores sit inside the existing `expected_score_range` bounds ([0.45, 0.70] and [0.65, 0.90]), so only `measured_score` and the "Score ≈" description lines were refreshed. Applied unilaterally (Step 4 measured-score refresh; no version bump).
- README.md carried three stale claims: broken-set scores "0.44" and "0.78" (pre-gate-removal, pre-weighting values) and — factually wrong since commit d343152 stripped the EPSG hint — "acceptable given the instruction explicitly names EPSG:26331". Fixed unilaterally (docs-change): scores updated to ≈ 0.57 / ≈ 0.79, the EPSG claim replaced with the accurate "the instruction deliberately names no projected CRS" rationale, and the weak-agent paragraph reworded to "metric-CRS reprojection" accordingly.
- The 632ad1a weighting is well-aimed for this task: the seven weight-3 subchecks are exactly the data-content ones, so the broken-set spread widens in the right direction (no_area_filter drops 0.64 → 0.57 because four of its five failures are weight-3; wrong_crs_area drops 0.82 → 0.79). Discrimination preserved: 0.0 / 0.57 / 0.79 remain distinct and ordered by severity.
- Inventory mismatch carried over (sixth consecutive pass): `benchmark/authoring/inventory.md:165` (Format in) and `:172` (Overture themes) plus thesis `<overture-theme-table>` aggregate (line 1089) still credit this task with `buildings.building_part`; the reference queries only `buildings.building` and `divisions.division_area`. <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Drop `buildings.building_part` from the inventory row, the format-in line, and the thesis aggregate, OR (less likely intended for a flood-risk footprint roll-up) extend the reference to query building parts; a reference extension would also require regenerating `reference/solution/outputs/`, re-checking the broken sets, and bumping `version`. Carried over from passes 1–5.
- Instruction house-style check re-confirmed: opens with purpose, no em-dashes, real filenames, explicit units/columns. The clipped "Need every… / Also need…" register was reviewed and accepted in pass 5; both current runs (and all prior strong-model runs) parse it without issue, so it stays.
- `task.json` still carries no `version` field (implicit v1); nothing in this pass changes the prompt/grader/inputs contract, so no bump is triggered.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions.no_area_filter.measured_score` 0.6364 → 0.5714 and `wrong_crs_area.measured_score` 0.8182 → 0.7857 (post-632ad1a weighted grader), plus the matching "Score ≈" description lines. Re-grade on reference: 1.00. Reason: keep metadata honest about current grader behaviour; expected ranges already contain the new values.
- `README.md`: replaced stale broken-set scores (0.44 → ≈ 0.57, 0.78 → ≈ 0.79 twice) and corrected the false "instruction explicitly names EPSG:26331" claim (the EPSG hint was stripped in d343152). Re-grade on reference: 1.00. Reason: stale README claims are fixed unilaterally as docs-change.
- `audit/AUTHORING_HISTORY.md`: appended this evaluator-review block.
- `coverage.yaml`: refreshed timestamp and notes. No slug changes.
- `audit/status.json`: updated with current verdict and the carried-over HR-001.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch (low) — `authoring/inventory.md:165`, `:172` and the thesis Overture-theme aggregate still credit this task with `buildings.building_part`; the reference queries only `buildings.building` (+ `divisions.division_area`). Carried over from passes 1–5.

#### Tests run
- grader on reference: 1.00 (14/14 subchecks, weighted total 28)
- broken solutions re-graded: wrong_format 0.0, no_area_filter 0.5714, wrong_crs_area 0.7857 (metadata refreshed to match)
- pytest: 41 passed, 0 failed

---

## Weight recalibration 2026-06-14  (evaluator-commit <pending>)

### Change (one line)
**RECALIBRATED** the subcheck weights to reflect error severity for this data-delivery L3. The blunt repo-wide 632ad1a weighting (seven "data-content" subchecks all at 3.0, everything else at 1.0) lumped a presence-only check (`height_stats_present`) and an internal-consistency check (`summary_total_consistent`) in with the genuine dataset-identity checks, so a cosmetic miss could cost as much as fetching the wrong building set. Replaced with a severity-tiered scheme. Grading-only; no `task.json` version bump, no logic/threshold/gate change.

### Reasoning
Central skill of this task: **deliver the correct building dataset** — fetch the right Lagos-State buildings (scope + count), assign each to the right LGA, and compute honest m² areas (which drives the > 1000 m² filter). The subchecks that detect failure of that central skill must dominate; schema/structural/presence checks must barely move the needle.

- **Tier 5 (dataset identity — the heart of the task):** `building_count_tolerance`, `feature_set_jaccard`, `area_filter_applied`. These detect "wrong set of buildings" and "no metric-CRS area / no > 1000 m² filter" — the headline requirement.
- **Tier 4 (roll-up correctness vs ground truth):** `summary_lga_overlap` (the LGA join dimension), `summary_area_reasonable` (honest metric-CRS area total).
- **Tier 2 (derived internal-consistency):** `summary_total_consistent` — important, but it only checks the summary reconciles with the building file, not correctness against ground truth, so it is secondary.
- **Tier 1 (schema / structural / presence / cosmetic):** `height_stats_present` (demoted from 3.0 — it only checks the height columns exist and are not all-zero; the README/metadata explicitly note Lagos height is sparse and the median unstable, so the check deliberately does NOT verify accuracy), `summary_columns_types`, `crs_wgs84_coords`, `crs_is_canonical`, `crs_in_meaningful_set`, `buildings_non_empty`, `geometry_types_valid`, `bounds_in_lagos_window`.

### Weight changes
| Subcheck | old | new |
|---|---|---|
| building_count_tolerance | 3.0 | 5.0 |
| feature_set_jaccard | 3.0 | 5.0 |
| area_filter_applied | 3.0 | 5.0 |
| summary_lga_overlap | 3.0 | 4.0 |
| summary_area_reasonable | 3.0 | 4.0 |
| summary_total_consistent | 3.0 | 2.0 |
| height_stats_present | 3.0 | 1.0 |
| summary_columns_types | 1.0 | 1.0 (unchanged) |
| crs_wgs84_coords | 1.0 | 1.0 (unchanged) |
| crs_is_canonical | 1.0 | 1.0 (unchanged) |
| crs_in_meaningful_set | 1.0 | 1.0 (unchanged) |
| buildings_non_empty | 1.0 | 1.0 (unchanged) |
| geometry_types_valid | 1.0 | 1.0 (unchanged) |
| bounds_in_lagos_window | 1.0 | 1.0 (unchanged) |

Total weight 28 → 33.

### Broken-score before → after
| Broken | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | unrecoverable (Gate-1 fail); most severe, unchanged |
| no_area_filter | 0.5714 | 0.4242 | wrong set entirely — fails count + jaccard + area_filter + area_reasonable (4 high-tier checks); drops further, correctly |
| wrong_crs_area | 0.7857 | 0.7273 | correct set, only area math wrong (fails area_filter + area_reasonable); lightest data error, stays near the top |

Ordering: 0.0 < 0.4242 < 0.7273 < 1.0 — **monotone and severity-ordered**. The cosmetic-ish error (right dataset, wrong area CRS) sits near the top; the gross dataset error (no filter) sits low; the unrecoverable format error is zero. The recalibration widens the gap between "wrong dataset" and "right dataset, minor area slip" relative to the old 0.57/0.79 spread, which is the intended sharpening. No disjoint-failure inversion: every higher-severity broken fails a strict superset (or higher-weighted set) of the lower one's central checks.

### Prior-run re-grade (current task version)
| Run | adapter | old score | new score |
|---|---|---|---|
| run-20260609-084636Z | deepseek-v4-flash-basic | 1.0 | 1.0 |
| run-20260608-074701Z | deepseek-v4-flash-detailed | 1.0 | 1.0 |
| run-20260607-060932Z | deepseek-v4-flash-detailed | 1.0 | 1.0 |
| run-20260606-2050Z | deepseek-v4-pro-detailed | 1.0 | 1.0 |
| run-20260606-2029Z | deepseek-v4-flash-detailed | 1.0 | 1.0 |
| run-20260606-2011Z | gemma4-26b-detailed (50 bldgs) | 0.5714 | 0.4545 |
| run-20260606-1733Z | gemma4-26b-detailed (1358 bldgs) | 0.4286 | 0.3636 |

The two current `current` runs (deepseek-v4-flash, the runs the sixth-pass block lists) are unaffected (1.0 → 1.0): correct submissions pass all 14 subchecks regardless of weighting. Only the two partial Gemma under-fetches shift, both *downward* — correctly, since both botched the central dataset-identity skill (50 / 1358 buildings vs reference 7250, Jaccard 0.0). Full ordering across all artefacts: gate 0.0 < gemma-1733 0.36 < no_area 0.42 < gemma-2011 0.45 < wrong_crs 0.73 < correct 1.0.

### Note on a threshold (not changed)
The two near-band Gemma runs (no_area_filter 0.42 vs gemma-2011 0.45) sit close together; both represent gross dataset failure and the ~0.03 gap is not a meaningful inversion. No threshold or check logic was touched, per the grading-only constraint.

### HR status
HR-001 (inventory-mismatch: `buildings.building_part` credited in inventory/thesis but never queried) is NOT a weighting HR — retained untouched.

### Tests run
- grader on reference: 1.00 (14/14 subchecks, weighted total 33)
- broken solutions re-graded: wrong_format 0.0, no_area_filter 0.4242, wrong_crs_area 0.7273 (metadata + README refreshed to match)
- pytest: not run (orchestrator runs the suite)
