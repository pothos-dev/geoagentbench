# Implementation notes — geo-l1-capetown-building-centroids

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 geometric-operation task: 122 Cape Town CBD building footprints
sliced from Overture (release 2026-04-15.0) and shipped as an
EPSG:32734 shapefile → per-feature centroid Points in EPSG:4326,
`building_id` preserved across the dBase 10-char truncation. Reference,
grader, and three broken solutions built and verified inside the
project Docker container.

## Verification results
- Reference grader score: 1.00 (5 / 5 subchecks pass).
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    (CSV-with-WKT cannot be parsed as the expected GeoJSON file).
  - bbox_corner_instead_of_centroid: 0.400 (expected range
    [0.35, 0.50]) — Gate 1 / 2 pass; `centroid_within_1m`,
    `centroid_median_distance_tight`, and the bbox-containment
    subcheck all fail (median offset ≈ 17 m).
  - wrong_ids: 0.200 (expected range [0.15, 0.30]) — Gate 1 / 2 pass;
    `building_id_set_preserved` fails plus all three id-keyed
    subchecks (per-id distance and bbox containment) fail because no
    ids match between submission and reference.
- Second-run output match: bit-identical (verified with `diff -q` on
  `reference/outputs/building_centroids.geojson` before / after a
  second `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Wrong output format (CSV / Parquet / raw WKT): broken_wrong_format
- Bbox corner instead of geometric centroid:
  broken_bbox_corner_instead_of_centroid
- Fabricated / re-numbered building ids: broken_wrong_ids
- Centroid computed in degrees (not metres): principled —
  `centroid_within_1m` + `centroid_median_distance_tight`
- Output left in EPSG:32734 instead of EPSG:4326: principled —
  Gate 1 CRS check
- Truncated `building_i` column dropped on write: principled —
  Gate 1 column-presence check
- `point_on_surface` instead of `centroid` (matters on L/U shapes):
  principled — `centroid_median_distance_tight`
- Global union → single centroid: principled — Gate 2 row-count check

## Open issues
(none — bundled input is sliced from Overture's
`theme=buildings/type=building` collection per `AUTHOR_CONTEXT.md`
guidance; no OSM Overpass / Geofabrik fallback was needed.)

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — the grader uses `Gate`, `Subcheck`, `ScoreReport`, and
`feature_set_equality_by_id`. Per-feature centroid distance is
computed with shapely's `.distance` after a `to_crs("EPSG:32734")`
roundtrip on both sides.)

## Runtime
~12 minutes (one Overture S3 bbox slice + reference generation +
three broken-solution builds + grader runs, all inside Docker).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The inventory row defines an L1 geometric-ops task: a single primary `centroid` per row on 122 bundled Cape Town CBD building footprints, with a mandatory CRS reprojection from EPSG:32734 (UTM 34S) to EPSG:4326 on the output GeoJSON, preserving each building's `building_id` as the join key. The persona (Thandi Nkosi, Cape Town addressing project) wants a Point-only layer for a point-rendering web tool. The original task.json, README, and IMPLEMENTATION_NOTES.md from commit 9664989 frame two L1-level format-literacy twists: (a) computing centroids in metric not degrees, and (b) recovering the truncated `building_i` dBase field as `building_id` on output. The grader was authored with two gates (file/CRS/column validity, geometry-type + row-count) and five subchecks (id populated, id-set Jaccard, per-id centroid distance ≤ 1 m, median distance ≤ 0.05 m, centroid inside footprint bbox).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9664989 | initial-authoring | Initial task: task.json, grade.py (235 lines), reference/generate.py + outputs, three broken solutions, README, IMPLEMENTATION_NOTES.md, 122-feature shapefile from Overture 2026-04-15.0. | (initial) |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit `Output schema:` bullet list to the instruction (file name, required `building_id` column, dBase truncation hint, Point-only geometry). | Commit msg: "declare exact output schema in prompts to match graders … No grader changes; no subchecks loosened." |
| 2026-05-13 | 284b843 | prompt-change | Added top-level `tags` dictionary to task.json (region, formats, crs, geometry_type, operations, themes, scale). No semantic instruction edit. | Commit msg: "add structured tags to all 36 task.json files … for filtering." |
| 2026-05-13 | 12c9fb0 | prompt-change | Rewrote the bullet-list `Output schema:` block as natural prose; kept all technical requirements (Point-only, building_id, WGS84, dBase truncation hint, FeatureCollection). | Commit msg: "Merge output schema blocks into prose for 6 more task instructions … preserving all technical requirements." |
| 2026-05-14 | f40e39e | prompt-change | Stripped "one true polygon centroid (Point geometry) per footprint" down to "one centroid per footprint", and removed the dBase-truncation hint (`building_i` rename instruction) from the instruction prose. | Commit msg: "Strip deducible information from GEO task instructions." Detail not given per-task, but consistent with `instruction-stripping-guide.md` (the dBase rename is a deducible format-literacy step). |
| 2026-05-17 | 64740d0 | prompt-change | Removed " in WGS84 (EPSG:4326)" from the closing schema-restating sentence of the instruction. | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" — note the commit subject targets dc-* tasks but this geo-* task was also edited in the same pass. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why for THIS task: not explicitly stated in commit message. |
| 2026-05-17 | db638f4 | grader-change | Replaced hand-rolled `crs.to_epsg() == 4326` check with `is_wgs84()` helper (accepts both EPSG:4326 and OGC:CRS84); rewrote the CRS-fail message from "expected EPSG:4326" to "expected WGS 84". | Commit msg: "Fix graders and prompts for 6 tasks that regressed after nudge removal … GeoJSON tasks (capetown-centroids, …) now expect WGS 84 instead of projected CRS, with reprojection to reference CRS for geometric comparison." |
| 2026-05-26 | 29a9ae3 | mixed (paths only) | Renamed `data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`. Updated path constants in grade.py, reference/solution/generate.py, reference/failures/_make_brokens.py, and `inputs[].url` in task.json. No semantic change. | Commit msg: "Reorganize task folder layout … separates audience concerns." |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (commit 29a9ae3, class: mixed — path-only rewrites to task.json, grade.py, reference/solution/generate.py, reference/failures/_make_brokens.py). Last semantically design-affecting commit was 2026-05-17T19:17:27+00:00 (db638f4, grader-change). Most prior runs (2026-05-12 through 2026-05-17) pre-date the layout reorg; conservatively only runs after 2026-05-26T09:51:37Z are treated as `current`.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:59:56Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |

Stale runs (pre-cutoff, not used as evidence): run-20260512-0833Z, run-20260512-0902Z, run-20260512-1619Z, run-20260512-1753Z, run-20260512-2315Z, run-20260513-0108Z, run-20260513-0922Z, run-20260513-0926Z, run-20260513-0928Z, run-20260513-0937Z, run-20260513-0943Z, run-20260514-0946Z, run-20260514-1245Z, run-20260514-1554Z, run-20260515-0624Z, run-20260515-0926Z, run-20260515-2053Z, run-20260516-0743Z, run-20260516-1130Z, run-20260516-2248Z, run-20260517-0134Z, run-20260517-0304Z, run-20260517-0614Z, run-20260517-1254Z, run-20260517-1424Z (25 runs). Not opened — predate the 2026-05-26 reorg.

#### Verdict
**insufficient-evidence**

Only one current run exists (Gemma 4 26B basic), and it failed Gate 1 at the CRS check because the agent wrote the centroids to GeoJSON without `to_crs(4326)` (kept them in EPSG:32734). The grader correctly identified the CRS mismatch. Inspecting `outputs/solve.py` confirms the agent computed `.centroid` and serialized to GeoJSON, omitting reprojection — this is exactly the failure mode the task is designed to test, not a grader miscalibration. Reference grader still scores 1.0 (5/5 subchecks) post-reorg, so the task remains structurally correct. With one run from one agent family, however, calibration cannot be confirmed: a larger Claude/OpenRouter sweep on the post-reorg artefacts is required before declaring the task `calibrated` vs `too-strict` vs `too-easy`.

#### Specific findings
- Reference output grades 1.0 (5/5 subchecks) under the current grader — `format_schema_valid` + `structural_correctness` both pass; all five subchecks pass; median centroid distance is 0.0000 m (well under the 0.05 m tight floor).
- Sole current run (Gemma 4 26B) is a clean model-side failure: the agent omitted `to_crs(4326)` before writing GeoJSON. The task probes this failure mode by design (README §5 + failure-mode #5). Score 0.0 is correct per the grader contract.
- The closing schema-restating sentence in the current instruction does **not** restate the CRS (commit 64740d0 stripped "in WGS84 (EPSG:4326)" from it). The `task-design-prompt.md` rule for L1 says: *"End the instruction with a sentence restating output format and CRS. Redundant with `expected_outputs[]` — intentional safety net."* Counterargument: GeoJSON output ⇒ WGS84 by RFC 7946, so omitting the explicit CRS is defensible per the evaluator-prompt §2d rule ("If the instruction is implicit but the format-level convention covers the omission, the instruction is fine"). The commit subject was "Remove answer-giving nudges from data-cleaning task prompts", which makes the targeting of this geo-* task in the same commit ambiguous in intent. <!-- HUMAN-REVIEW id="HR-002" category="prompt-vs-grader-judgment" severity="low" --> Decide whether to restore the explicit "in WGS84 (EPSG:4326)" closing-sentence safety net per `task-design-prompt.md` line 79, or accept the GeoJSON/RFC-7946 implicit convention as sufficient. Not unilaterally edited because the call is judgmental and a single current run is not evidence either way.
- The dBase truncation hint was also stripped from the instruction (commit f40e39e). The grader still rejects via Gate 1 if the column is missing; the README and metadata.yaml documentation of the truncation is preserved. This is consistent with the instruction-stripping-guide; no flag.
- More current runs needed before any further calibration call.

### 3. Changes applied this run

#### Unilateral edits
(none — verdict is insufficient-evidence; reference still scores 1.0; no clear-cut gift or grader miscalibration in evidence.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit 64740d0 subject targets dc-* tasks but also edited this geo-* task; per-task rationale for stripping CRS from the closing sentence not stated.
- HR-002 — prompt-vs-grader-judgment — Closing schema-restating sentence omits CRS, contrary to `task-design-prompt.md` line 79, but defensible by RFC 7946 convention. Pick a side.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks pass; format_schema_valid + structural_correctness gates pass)
- pytest (benchmark/eval): pass (35/35)

---

## Evaluator review 2026-05-26T20:44Z  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/geo-l1-capetown-building-centroids/` since the prior evaluator block above, other than that block's own artefact commit (a92b4c2, 2026-05-26T14:18:51Z, docs-only). The reconstructed design history in the prior block (commits 9664989 initial-authoring → 1710715/284b843/12c9fb0/f40e39e/64740d0 prompt-changes → db638f4 grader-change → 29a9ae3 layout reorg) remains accurate and complete; it is not restated here. The design intent is unchanged: an L1 geometric-ops task computing a per-footprint `centroid` on 122 bundled Cape Town CBD building polygons, with a mandatory EPSG:32734 → EPSG:4326 reprojection on the GeoJSON output and preservation of the `building_id` join key across the dBase 10-char column truncation.

### 2. Current-state review

This re-evaluation was triggered by the orchestrator adding two fresh runs (one opus, one gemma) on top of the single gemma run the prior block could consider. The task now has three `current` runs spanning two agent families, so the prior `insufficient-evidence` verdict can be upgraded.

#### Cutoff
- design-affecting cutoff: unchanged from prior block — most-recent design-affecting commit is db638f4 (grader-change, 2026-05-17T19:17:27Z); the 2026-05-26 layout reorg (29a9ae3, 2026-05-26T09:51:37Z) was path-only `mixed`. Conservatively, runs started after 2026-05-26T09:51:37Z are treated as `current`. All three runs below clear that bar.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:01:05Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:43:55Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:59:56Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |

Stale runs (pre-2026-05-26 reorg, not used as evidence): the 25 runs listed in the prior evaluator block (2026-05-12 through 2026-05-17). Not re-opened.

#### Verdict
**calibrated**

Three current runs across two agent families now give a sensible score spread. Opus (run-20260526-1753Z) scored 1.0 — its output matches the reference exactly: 122 Point rows, CRS EPSG:4326, `building_id` preserved (Jaccard 1.0), median centroid distance 0.0000 m, all 5/5 subchecks and both gates pass. Both Gemma runs (run-20260526-1922Z, run-20260526-0748Z) scored 0.0, failing Gate 1 at the CRS check with the identical signature "CRS is 32734, expected WGS 84". Inspecting `run-20260526-1922Z/outputs/solve.py` confirms the Gemma agent handled the dBase rename (`building_i` → `building_id`) and computed `.centroid` correctly, but called `.centroid` on the UTM-34S geometry and wrote GeoJSON **without** `to_crs(4326)` — leaving the file in EPSG:32734. That is precisely README failure-mode #5 ("forgot to reproject to WGS84 on output"), a genuine model-side miss of the operation the task is designed to probe, not a grader miscalibration. The capability gradient (a strong agent infers GeoJSON⇒WGS84 and reprojects; a weaker one omits it) is exactly what a well-calibrated L1 should produce. Reference still grades 1.0 (5/5) and `benchmark/eval` pytest is 35/35 green.

This run evidence also resolves the prior block's HR-002. The current instruction omits an explicit output CRS (commit 64740d0 stripped "in WGS84 (EPSG:4326)"); the prior evaluator could not tell whether that omission was a fault or a feature with only one failing run. With Opus correctly inferring WGS84 from the GeoJSON/RFC-7946 convention while Gemma did not, the implicit-CRS instruction is demonstrably a working discriminator rather than an ambiguity — the GeoJSON convention is sufficient for a competent agent, and stripping the explicit CRS created a meaningful difficulty signal. The prior HR-002 is therefore closed (not re-raised). HR-001 (per-task design rationale for commit 64740d0, whose subject line targeted dc-* tasks) is retained: run evidence cannot retroactively explain *why* a past commit edited this geo-* task, and the evaluator prompt forbids inferring commit rationale from run behaviour. It remains a low-severity design-rationale flag.

#### Specific findings
- Score spread 1.0 (opus) vs 0.0 / 0.0 (gemma ×2) across two families — calibrated; no grader miscalibration in evidence.
- Both Gemma 0.0 results are clean model-side failures of failure-mode #5 (missing reprojection). README §"Failure modes" #5 + the Gate-1 CRS check correctly detect it. Not a task problem; no simplification proposed.
- Opus output is feature-for-feature identical to the reference (Jaccard 1.0, median 0.0000 m), confirming the reference and grader are mutually consistent post-reorg.
- HR-002 from the prior block (CRS-in-closing-sentence) is resolved by this run evidence and not re-raised; the implicit GeoJSON⇒WGS84 convention is confirmed adequate.
- HR-001 from the prior block (design rationale for commit 64740d0) is retained, re-numbered HR-001 in this block, severity low.

### 3. Changes applied this run

#### Unilateral edits
(none — verdict is calibrated; reference scores 1.0; no gift or grader miscalibration in evidence.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit 64740d0 subject ("Remove answer-giving nudges from data-cleaning task prompts") targeted dc-* tasks but also stripped "in WGS84 (EPSG:4326)" from this geo-* task's closing sentence; per-task rationale not stated in the commit message. Low severity; the resulting implicit-CRS instruction is now shown to be well-calibrated, so this is a documentation/intent gap only.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks pass; both gates pass)
- pytest (benchmark/eval): pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/geo-l1-capetown-building-centroids/` since the prior evaluator block (2026-05-26T20:44Z). The only commits to the directory since that block are the two prior evaluator artefact commits themselves — a92b4c2 (2026-05-26T14:18Z) and 0443c5e (2026-05-26T20:45Z) — both docs-only (each touched only `audit/AUTHORING_HISTORY.md`, `audit/status.json`, `coverage.yaml`). The reconstructed design history in the prior two blocks remains accurate and complete and is not restated here: initial-authoring 9664989 (2026-05-08) → prompt-changes 1710715 / 284b843 / 12c9fb0 / f40e39e / 64740d0 → grader-change db638f4 (2026-05-17) → path-only layout reorg 29a9ae3 (2026-05-26). Design intent unchanged: an L1 geometric-ops task computing a per-footprint `centroid` on 122 bundled Cape Town CBD building polygons (sliced from Overture release 2026-04-15.0), with a mandatory EPSG:32734 → EPSG:4326 reprojection on the GeoJSON output and preservation of the `building_id` join key across the dBase 10-char column truncation (`building_id` → `building_i` on disk).

### 2. Current-state review

This re-evaluation re-verified the post-reorg artefacts from scratch (grader on reference + all three broken solutions + pytest + light inspection of all three current-run outputs). The run set and the design-affecting cutoff are unchanged from the prior block, so the prior `calibrated` verdict is re-confirmed rather than revised.

#### Cutoff
- design-affecting cutoff: unchanged. Most-recent design-affecting commit is db638f4 (grader-change, 2026-05-17T19:17:27Z). The 2026-05-26 layout reorg (29a9ae3, 2026-05-26T09:51:37Z) is path-only `mixed`. Conservatively, runs started after 2026-05-26T09:51:37Z are treated as `current`. The three runs below clear that bar; no new runs have appeared since the prior block.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:01:05Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:43:55Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:59:56Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |

Stale runs (pre-2026-05-26 reorg, not used as evidence): the 25 runs listed in the first evaluator block (2026-05-12 through 2026-05-17). Not re-opened.

#### Verdict
**calibrated**

Three current runs across two agent families give a sensible spread that re-confirms the prior block. Opus (run-20260526-1753Z) scores 1.0: 122 Point rows in WGS84 (CRS member `OGC:1.3:CRS84`), coordinates feature-for-feature identical to the reference (sample `[18.42687, -33.92266]`), `building_id` preserved (Jaccard 1.0), median centroid distance 0.0000 m, both gates and all 5/5 subchecks pass. Both Gemma runs score 0.0, failing Gate 1 at the CRS check with the identical signature "CRS is 32734, expected WGS 84". Light inspection of both Gemma outputs confirms 122 Point rows with `building_id` preserved but coordinates left in UTM-34S metres (sample `[262131.6, 6243436.7]`) tagged as EPSG:32734 — the agents computed `.centroid` correctly but omitted `to_crs(4326)` before writing GeoJSON. That is precisely README failure-mode #5, a genuine model-side miss of the reprojection step the task is designed to probe, not a grader miscalibration. The capability gradient (a strong agent infers GeoJSON⇒WGS84 and reprojects; weaker ones omit it) is exactly what a well-calibrated L1 should produce.

Output-CRS / format consistency (Step 2c-CRS) holds: the reference output is WGS84 (`OGC:1.3:CRS84` lon/lat, the RFC-7946 default), `expected_outputs[].crs` is `EPSG:4326`, and the README states EPSG:4326 — all three agree. The grader does **not** one-sidedly reproject the submission to match the reference: for the per-building distance subchecks it reprojects **both** sub and ref to EPSG:32734 (grade.py lines 153-154), which is the allowed both-sides metric transform. Reference still grades 1.0 (5/5) and `benchmark/eval` pytest is 35/35 green.

#### Specific findings
- Score spread 1.0 (opus) vs 0.0 / 0.0 (gemma ×2) across two families — calibrated; no grader miscalibration in evidence.
- Both Gemma 0.0 results are clean model-side failures of README failure-mode #5 (missing reprojection); the Gate-1 CRS check correctly detects them. Not a task problem; no simplification proposed (per evaluator-prompt §2d model-side-failure rule).
- Reference output grades 1.0 (5/5) under the current grader; broken solutions re-graded 0.0 / 0.4 / 0.2 — each in its declared `metadata.yaml` range ([0.0,0.0] / [0.35,0.50] / [0.15,0.30]) and the three ranges are distinct, so the grader retains resolution.
- Output-CRS contract is internally consistent (reference WGS84 = contract EPSG:4326 = README EPSG:4326); grader reprojects both sides for the metric check, no one-sided reprojection. No `prompt-grader-inconsistent` finding.
- Minor documentation imprecision (no flag, no edit): `metadata.yaml` note #2 and `inputs/_prepare.py` docstring state `building_id` "is exactly 10 chars and survives unchanged", but the column name `building_id` is 11 chars and is in fact truncated to `building_i` on disk (verified by reading the shapefile). The reference and grader both handle this correctly via the `building_i`→`building_id` rename, so scoring is unaffected; `inputs/_prepare.py` is not editable by the evaluator and `metadata.yaml`'s wording does not change any score, so this is left as a note only.
- HR-001 from the prior block (per-task design rationale for commit 64740d0, whose subject targeted dc-* tasks) is retained, re-numbered HR-001 in this block, severity low. Run evidence cannot retroactively explain *why* that past commit also edited this geo-* task, and the evaluator prompt forbids inferring commit rationale from run behaviour.
- HR-002 from the first block (CRS in closing sentence) was resolved and closed by the second block's run evidence (Opus correctly infers GeoJSON⇒WGS84; the implicit-CRS instruction is a working discriminator, not an ambiguity). Not re-raised.

### 3. Changes applied this run

#### Unilateral edits
(none — verdict is calibrated; reference scores 1.0; broken-solution scores unchanged; no gift or grader miscalibration in evidence.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit 64740d0 subject ("Remove answer-giving nudges from data-cleaning task prompts") targeted dc-* tasks but also stripped "in WGS84 (EPSG:4326)" from this geo-* task's closing sentence; per-task rationale not stated in the commit message. Low severity; the resulting implicit-CRS instruction is now shown well-calibrated, so this is a documentation/intent gap only.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks pass; both gates pass)
- broken solutions re-graded: wrong_format 0.0, bbox_corner_instead_of_centroid 0.4, wrong_ids 0.2 (all in declared ranges)
- pytest (benchmark/eval): pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

One new commit has touched `benchmark/tasks/geo-l1-capetown-building-centroids/` since the prior evaluator block (df6be96, 2026-05-27T19:29:24Z, which was the prior block's own docs-only artefact commit):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | docs-change | Removed the unused `prompt_version: 2026-05-08-a` line from `metadata.yaml`. No other change inside this task's directory. | Commit msg: "Add task content versioning; drop unused prompt_version" — `prompt_version` tagged the orchestrator's authoring template, not the task content; harness/UI now use a new integer `version` field on `task.json` instead. Repo-wide cleanup. |

This commit does not change the agent-visible prompt, the grader, the tolerances, the input bundle, or any reference / failures content. It is therefore not design-affecting; the cutoff carries over from db638f4. The complete prior design history (initial-authoring 9664989 → prompt-changes 1710715 / 284b843 / 12c9fb0 / f40e39e / 64740d0 → grader-change db638f4 → path-only layout reorg 29a9ae3) remains accurate and is not restated. Design intent unchanged.

Note on the new `version` field: the repo-wide commit 622342b introduces an integer `version` on `task.json`. The current `task.json` for this task does **not** yet carry the field, so the task is implicitly v1. Per the evaluator-prompt's new Step-4 versioning rule, the first unilateral edit that meaningfully changes the prompt / grader / inputs would write `version: 2`. This block applies no such edit, so the field is not introduced and the task remains implicitly v1.

### 2. Current-state review

This re-evaluation re-verified the post-reorg artefacts from scratch (grader on reference + three broken solutions + pytest) and adds four newly-arrived current runs to the runs table. The verdict `calibrated` is re-confirmed.

#### Cutoff
- design-affecting cutoff: unchanged. Most-recent design-affecting commit is db638f4 (grader-change, 2026-05-17T19:17:27Z). The 2026-05-26 layout reorg (29a9ae3, 2026-05-26T09:51:37Z) was path-only `mixed`; the 2026-05-28 prompt_version drop (622342b) is docs-change inside this task's `metadata.yaml`. Conservatively, runs started after 2026-05-26T09:51:37Z are treated as `current`. All seven runs below clear that bar.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:06:19Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T02:41:18Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:54:47Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T22:19:24Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:43:55Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T19:01:05Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:59:56Z | 0.0 | done (Gate 1 reject: CRS 32734, expected WGS 84) | current |

Stale runs (pre-2026-05-26 reorg, not used as evidence): the 25 runs listed in the first evaluator block (2026-05-12 through 2026-05-17). Not re-opened.

#### Verdict
**calibrated**

Seven current runs across two agent families now give a strongly-replicated bimodal spread that re-confirms the prior block. All three Opus runs (run-20260526-1753Z, run-20260527-2016Z, run-20260528-0113Z) score 1.0 with 122/122 features, both gates pass, and all 5/5 subchecks pass (median centroid distance 0.0000 m, Jaccard 1.0). All four Gemma runs (run-20260526-0748Z, run-20260526-1922Z, run-20260527-2321Z, run-20260528-0317Z) score 0.0 with the identical Gate-1 signature "CRS is 32734, expected WGS 84". Light inspection of run-20260527-2321Z's `outputs/building_centroids.geojson` confirms 122 Point rows with `building_id` preserved (sample `BLD00001`) but coordinates left in UTM-34S metres (sample `[262131.6, 6243436.7]`) tagged as EPSG:32734 — exactly README failure-mode #5 (missing `to_crs(4326)` before GeoJSON write), a clean model-side miss of the reprojection step the task is designed to probe, not a grader miscalibration. The capability gradient (Opus infers GeoJSON⇒WGS84 from RFC 7946; Gemma omits the reprojection) is exactly what a well-calibrated L1 should produce, and it now replicates 3-of-3 (Opus) vs 4-of-4 (Gemma) across the run set.

Output-CRS / format consistency (Step 2c-CRS) holds: the reference output is WGS84 (`OGC:1.3:CRS84` lon/lat, the RFC-7946 default), `expected_outputs[].crs` is `EPSG:4326`, and the README states EPSG:4326 — all three agree. The grader does **not** one-sidedly reproject the submission to match the reference: for the per-building distance subchecks it reprojects **both** sub and ref to EPSG:32734 (grade.py lines 153-154), the allowed both-sides metric transform. Reference still grades 1.0 (5/5) and `benchmark/eval` pytest is 41/41 green (up from 35/35 last block — repo-wide test growth, not task-local).

Instruction-tightening sweep (Step 4 "Tighten redundant statements"): the closing schema-restating sentence "Write the result to `building_centroids.geojson` as a GeoJSON FeatureCollection with Point geometry only and the `building_id` column described above." is the deliberate safety-net sentence required by `task-design-prompt.md` line 79; the filename / format / geometry-type repetitions inside it are the intended redundancy of that safety net (per task-design-prompt rule 79). The `building_id` repetition is identity-key information not pinned by `expected_outputs[]` — per evaluator-prompt §4 the rule explicitly forbids stripping identity-key references that the schema does not already encode ("'feature_id is the join key' is identity-key information not present in `expected_outputs[]`"). The instruction never mentions EPSG / WGS84 / 4326 (already stripped at commit 64740d0), so the GeoJSON-CRS strip rule has no work to do. No unilateral instruction edit is warranted.

#### Specific findings
- Bimodal score spread 1.0 / 1.0 / 1.0 (opus ×3) vs 0.0 / 0.0 / 0.0 / 0.0 (gemma ×4) across two families — calibrated; no grader miscalibration in evidence.
- All four Gemma 0.0 results are clean model-side failures of README failure-mode #5 (missing reprojection); the Gate-1 CRS check correctly detects them. Not a task problem; no simplification proposed (per evaluator-prompt §2d model-side-failure rule).
- Reference output grades 1.0 (5/5) under the current grader; broken solutions re-graded 0.0 / 0.4 / 0.2 — each in its declared `metadata.yaml` range ([0.0,0.0] / [0.35,0.50] / [0.15,0.30]) and the three ranges are distinct, so the grader retains resolution.
- Output-CRS contract is internally consistent (reference WGS84 = contract EPSG:4326 = README EPSG:4326); grader reprojects both sides for the metric check, no one-sided reprojection. No `prompt-grader-inconsistent` finding.
- Instruction has no redundant statement that the schema already pins and that this evaluator should strip; safety-net sentence is intentionally redundant per task-design-prompt line 79. No edit applied.
- The 2026-05-28 commit 622342b that dropped `prompt_version` from `metadata.yaml` is docs-change only and does not move the design-affecting cutoff.
- HR-001 from the prior block (per-task design rationale for commit 64740d0, whose subject targeted dc-* tasks) is retained, re-numbered HR-001 in this block, severity low. Run evidence cannot retroactively explain *why* that past commit also edited this geo-* task, and the evaluator prompt forbids inferring commit rationale from run behaviour.

### 3. Changes applied this run

#### Unilateral edits
(none — verdict is calibrated; reference scores 1.0; broken-solution scores unchanged; no gift or grader miscalibration in evidence; instruction-tightening sweep found nothing to strip.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit 64740d0 subject ("Remove answer-giving nudges from data-cleaning task prompts") targeted dc-* tasks but also stripped "in WGS84 (EPSG:4326)" from this geo-* task's closing sentence; per-task rationale not stated in the commit message. Low severity; the resulting implicit-CRS instruction is now demonstrably well-calibrated (7-run bimodal spread, Opus vs Gemma), so this is a documentation/intent gap only.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks pass; both gates pass)
- broken solutions re-graded: wrong_format 0.0, bbox_corner_instead_of_centroid 0.4, wrong_ids 0.2 (all in declared ranges)
- pytest (benchmark/eval): pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

Two new commits have touched `benchmark/tasks/geo-l1-capetown-building-centroids/` since the prior evaluator block (2026-05-28):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | docs-change | Dropped unused `prompt_version: 2026-05-08-a` line from `metadata.yaml`. | Commit msg: repo-wide cleanup; `prompt_version` tagged the authoring template, not task content. |
| 2026-05-28 | 05aabd6 | grader-change | Reworked Gate-1 CRS handling: a wrong-CRS submission is now reprojected to canonical for the geometric subchecks and docked via two new soft-CRS subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) instead of hard-failing Gate 1. Module-level `CANONICAL_EPSG = 4326` and `MEANINGFUL_EPSGS = {4326, 32734}` configure the policy for this task. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders … over-penalises a recoverable failure mode … re-grading the existing Gemma run shows the intended shape (this task: 0.000 → 0.857)." |

The 05aabd6 commit is the new design-affecting cutoff (a grader-change). The complete prior design history (initial-authoring 9664989 → prompt-changes 1710715 / 284b843 / 12c9fb0 / f40e39e / 64740d0 → grader-change db638f4 → path-only layout reorg 29a9ae3 → docs-only 622342b) remains accurate and is not restated. Design intent unchanged: an L1 geometric-ops task computing a per-footprint `centroid` on 122 bundled Cape Town CBD building polygons, with a mandatory EPSG:32734 → EPSG:4326 reprojection on the GeoJSON output and preservation of the `building_id` join key across the dBase 10-char column truncation. The soft-CRS refactor preserves intent — a CRS miss is now a graded deduction instead of a hard zero, which the commit message frames as recognising centroid math as correct even when reprojection is missed.

### 2. Current-state review

This re-evaluation re-verified the post-soft-CRS artefacts from scratch (grader on reference + three broken solutions + pytest) and adds six newly-arrived current runs to the runs table. Verdict moves from `calibrated` (under the pre-soft-CRS scoring) to `calibrated` (under the new scoring) — the bimodal pre-soft spread is now a graded gradient that better separates capability levels.

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57Z** (commit 05aabd6, class: grader-change). Runs started strictly after this timestamp are `current`. The 2026-05-28 prompt_version drop (622342b, docs-change inside `metadata.yaml`) does not move the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:32:05Z | 0.857 | done (6/7: missing crs_is_canonical, output EPSG:32734) | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:15:00Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T17:04:53Z | 0.857 | done (6/7: missing crs_is_canonical, output EPSG:32734) | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:01:20Z | 0.857 | done (6/7: missing crs_is_canonical, output EPSG:32734) | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:26:01Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:15:34Z | 0.857 | done (6/7: missing crs_is_canonical, output EPSG:32734) | current |

Stale runs (pre-2026-05-28T19:02:57Z soft-CRS cutoff, not used as evidence): the seven runs from the prior block (2026-05-26 through 2026-05-28T17:42Z, all under the old hard-fail policy that scored Gemma 0/0/0/0). Not re-graded against the new grader — the prior block's evidence is no longer load-bearing now that we have six post-cutoff runs across three agent families.

#### Verdict
**calibrated**

Six current runs across three agent families (Opus, Gemma 4 26B, DeepSeek V4 Pro) give a sensible graded spread under the new soft-CRS policy. Opus (run-20260528-2332Z) scores 1.0 — emits 122 Point rows in canonical WGS84, `building_id` preserved, median distance 0.0000 m, all 5 geometric subchecks plus both CRS subchecks pass. One Gemma-detailed run (run-20260606-0953Z) also scored 1.0, confirming that the GeoJSON⇒WGS84 inference is reachable for Gemma under the `gis_detailed` prompt variant. The other four runs (3 Gemma basic + 1 DeepSeek) all score the identical 0.857 (6/7): they get every geometric subcheck right — `building_id_populated`, `building_id_set_preserved` (Jaccard 1.0), `centroid_within_1m` (122/122), `centroid_median_distance_tight` (0.0000 m after reprojection), `centroid_inside_own_footprint_bbox` (122/122) — and `crs_in_meaningful_set` (EPSG:32734 is in the accept list), but lose `crs_is_canonical` because the file is left in EPSG:32734 instead of being reprojected to WGS84. That is exactly the calibration shape the 05aabd6 commit was designed to produce: the agent's centroid math is correct, just delivered in the wrong CRS, and the deduction is one subcheck out of seven rather than a zero.

The capability gradient now reads as a graded scale rather than bimodal: 1.0 (strong agent, reprojects), 0.857 (weak agent, computes the centroid right but misses the reprojection), and 0.0 would require failing structural correctness or losing the `building_id` join key. This is more informative than the pre-soft 1.0-vs-0.0 split.

Output-CRS / format consistency (Step 2c-CRS) holds: the reference output is WGS84 (`OGC:1.3:CRS84`), `expected_outputs[].crs` is `EPSG:4326`, and the README states EPSG:4326 — all three agree. The grader reprojects **both** sub and ref to EPSG:32734 for the per-building distance subchecks (the allowed both-sides metric transform); the new one-sided reprojection of the submission to canonical is implemented by `grade_crs_soft` and is the declared accept-list policy (not a CRS-mismatch paper-over). No `prompt-grader-inconsistent` finding.

Broken-solution scores have shifted under the new 7-subcheck grader: bbox_corner_instead_of_centroid was 2/5 = 0.4, now 4/7 ≈ 0.571 (both new CRS subchecks pass because the broken solution emits WGS84); wrong_ids was 1/5 = 0.2, now 3/7 ≈ 0.429 (same reason). `wrong_format` stays at 0.0. `metadata.yaml > broken_solutions` `expected_score_range` and `measured_score` are refreshed unilaterally to match the new arithmetic (Step 4 explicitly permits `measured_score` updates and peer evaluator passes — fio-l1-paris-kml-pois, fio-l1-vienna-shapefile-recovery — have established the pattern of widening `expected_score_range` alongside when the grader subcheck count changes).

Instruction-tightening sweep (Step 4 "Tighten redundant statements"): unchanged from prior pass. The closing schema-restating sentence is the deliberate safety-net sentence required by `task-design-prompt.md`; the `building_id` repetition is identity-key information not pinned by `expected_outputs[]` (Step 4 explicitly forbids stripping that). The instruction never mentions EPSG / WGS84 / 4326 (already stripped at 64740d0), so the GeoJSON-CRS strip rule has no work to do. No unilateral instruction edit applied.

`analyst_notes` was missing from `task.json`. Authored unilaterally per Step 4 — description covers the two hidden gotchas (unstated reprojection, dBase column truncation), `approach` is library-agnostic, and `pitfalls` cover the README's documented failure modes plus the new soft-CRS scoring consequence ("EPSG:32734 stays in the meaningful set"). No `version` bump because `analyst_notes` is human-facing only (per Step-4 bump-not-required list).

#### Specific findings
- Six current runs across three agent families now produce a graded 1.0 / 1.0 / 0.857 / 0.857 / 0.857 / 0.857 spread under the soft-CRS grader — calibrated; the scoring matches the commit-msg intent for 05aabd6.
- Reference output grades 1.0 (7/7) under the current grader; broken solutions re-grade 0.0 / 0.5714 / 0.4286 — `metadata.yaml` `measured_score` and `expected_score_range` refreshed to match (range widened by 0.15 on both broken solutions to absorb the +2-subcheck shift).
- Output-CRS contract is internally consistent (reference WGS84 = contract EPSG:4326 = README EPSG:4326); the soft-CRS one-sided reprojection of the submission is the declared accept-list policy, not a one-sided paper-over. No `prompt-grader-inconsistent` finding.
- `analyst_notes` authored on `task.json` (description + approach + pitfalls). Human-facing only; no version bump.
- README §"Failure modes" #5 ("forgot to reproject to WGS84 on output") still reads as a Gate-1 rejection in the README text but is now a 1-subcheck deduction under the soft-CRS grader. Left as is — the README phrasing pre-dates 05aabd6 and the README references are bracketed by the broken-solution score updates I made; rewriting all eight failure-mode entries would be a wider scope edit than this pass warrants. Minor documentation imprecision; not flagged.
- HR-001 from the prior block (per-task design rationale for commit 64740d0) remains the only standing HR — re-numbered HR-001 in this block, severity low. Run evidence still cannot retroactively explain *why* that past commit also edited this geo-* task.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `analyst_notes` (description + approach + pitfalls). Re-grade on reference: 1.0. Reason: field was missing; Step 4 requires authoring when absent. Human-facing only, no `version` bump.
- `metadata.yaml`: refreshed `broken_solutions.bbox_corner_instead_of_centroid.measured_score` 0.4 → 0.5714 and `expected_score_range` [0.35, 0.50] → [0.50, 0.65]; refreshed `broken_solutions.wrong_ids.measured_score` 0.2 → 0.4286 and `expected_score_range` [0.15, 0.30] → [0.35, 0.50]; added a soft-CRS policy note to `tolerances.rationale` documenting the 7-subcheck total. Re-grade on reference: 1.0; broken re-grades 0.0 / 0.5714 / 0.4286 (all inside the new ranges). Reason: the 05aabd6 grader-change added two CRS subchecks (5 → 7 total); peer evaluator passes (fio-l1-paris-kml-pois, fio-l1-vienna-shapefile-recovery) established the pattern of widening ranges alongside.
- `README.md`: refreshed the two `broken_*` score citations in the §"Failure modes" list (0.4 → 0.571 and 0.2 → 0.429), with a parenthetical note that the previous values were under the original 5-subcheck grader. Re-grade on reference: 1.0. Reason: keep the README in lock-step with `metadata.yaml`; doc-only.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit 64740d0 subject ("Remove answer-giving nudges from data-cleaning task prompts") targeted dc-* tasks but also stripped "in WGS84 (EPSG:4326)" from this geo-* task's closing sentence; per-task rationale not stated in the commit message. Low severity; the resulting implicit-CRS instruction is demonstrably well-calibrated (six runs across three agent families produce a graded 1.0 / 0.857 spread), so this is a documentation/intent gap only.

#### Tests run
- grader on reference: 1.0 (7/7 subchecks pass; both gates pass)
- broken solutions re-graded: wrong_format 0.0, bbox_corner_instead_of_centroid 0.5714, wrong_ids 0.4286 (all in newly-declared ranges)
- pytest (benchmark/eval): pass (41/41)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geometry-type-is-Point check migrated to new subcheck
  `geometry_types_point`.
- Row-count-within-±5% check migrated to new subcheck
  `row_count_within_tolerance`.
- Subcheck count: 7 → 9.

### Verification
- Reference solution re-graded: 1.0 (9/9 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

Two new design-affecting commits have touched `benchmark/tasks/geo-l1-capetown-building-centroids/` since the last evaluator block (2026-06-06; that block's own artefact commit was 3b52907):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change | Dropped the `structural_correctness` gate; geometry-type-is-Point and row-count-within-±5% migrated to subchecks `geometry_types_point` and `row_count_within_tolerance` (7 -> 9 subchecks). Docstring rewritten to the single-gate shape. Also appended the "Manual cleanup 2026-06-06" section to this file. | Commit msg: benchmark-wide refactor; the second gate was inconsistent across 36 graders (34 effectively hard), so every shape-recoverable check now costs a point instead of zeroing the score. |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to the five data-content subchecks (`building_id_set_preserved`, `centroid_within_1m`, `centroid_median_distance_tight`, `centroid_inside_own_footprint_bbox`, `row_count_within_tolerance`); schema/CRS subchecks stay weight 1. Score is now sum(weight passed)/sum(weight), denominator 19. | Commit msg: benchmark-wide; data-content subchecks weighted 3x across fio/geo/spa/dc, schema/structural checks stay 1.0. |

The complete prior design history (initial-authoring 9664989 -> prompt-changes 1710715 / 284b843 / 12c9fb0 / f40e39e / 64740d0 -> grader-change db638f4 -> layout reorg 29a9ae3 -> docs 622342b -> soft-CRS grader-change 05aabd6) remains accurate and is not restated. Design intent unchanged: an L1 geometric-ops task computing a per-footprint `centroid` on 122 bundled Cape Town CBD building polygons, with a deliberately-unstated EPSG:32734 -> EPSG:4326 reprojection on the GeoJSON output and preservation of the `building_id` join key across the dBase 10-char column truncation. Both new commits rescale scoring without changing the prompt, inputs, reference, or any pass/fail threshold.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:32:38Z** (commit c749e57, class: grader-change). The 363aed2 Gate-2 drop (2026-06-06T20:11:02Z) is superseded by this later cutoff. `task.json` carries no `version` field, so the task is implicitly v1; all candidate runs also recorded task_version 1, so validity reduces to the timestamp cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T12:21:54Z | 0.947 | done (18/19: only crs_is_canonical fails, output EPSG:32734) | current |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:55:39Z | 0.947 | done (18/19: only crs_is_canonical fails, output EPSG:32734) | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T15:42:23Z | 0.947 | done | stale (started 2h55m before the c749e57 cutoff; suite sha 06fd6c0 pre-dates the weight commit) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:24:04Z | 0.857 | done (6/7 pre-weights) | stale (pre-cutoff) |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | - | cancelled | stale (pre-cutoff) |

Older stale runs: the six runs from the 2026-06-06 block (2026-05-28 through 2026-06-06) and the 32 runs before those, listed in earlier blocks. Not re-opened.

#### Verdict
**insufficient-evidence**

Only two `current` runs exist and both come from one agent family (DeepSeek V4 Flash, basic and detailed prompt variants), so the mechanical Step-2d rule forces `insufficient-evidence`. Nothing in the evidence suggests a problem, though. Both runs produced 122 Point rows with `building_id` fully preserved (Jaccard 1.0), centroids identical to the reference after normalization (sample coordinates `[262131.64, 6243436.71]` in metres), but left the file in EPSG:32734 instead of WGS84 - the task's signature reprojection miss. Under the weighted soft-CRS grader each loses exactly the weight-1 `crs_is_canonical` subcheck: 18/19 ≈ 0.947. That is the intended scoring shape for "correct geometry, wrong delivery CRS". Continuity from the previous calibrated verdict is strong: the c749e57/363aed2 changes are pure rescalings of the subcheck pass-vector, and mapping the 2026-06-06 block's six multi-family runs through the new arithmetic gives 1.0 (opus), 1.0 (gemma-detailed), 0.947 x4 (gemma-basic x3, deepseek-pro) - same ordering, no rank inversions. The stale gemma run-20260607-112430Z (0.947, started 2h55m pre-cutoff against an identical prompt/input bundle) corroborates. A multi-family post-cutoff sweep would upgrade this to `calibrated`; nothing needs fixing in the meantime.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `building_centroids.geojson`, GeoJSON FeatureCollection | instruction, closing sentence | stated |
| `building_id` column present | instruction ("ensure the output carries a `building_id` column") | stated |
| `building_id` non-empty every row | instruction ("Every row must have a non-empty `building_id`") | stated |
| `building_id` set preserved (Jaccard >= 0.95) | instruction ("Keep the building IDs ... from the input") | stated (tolerance grader-internal, standard) |
| one centroid per footprint (row count ±5%) | instruction ("one centroid per footprint") | stated |
| Point-only geometry | instruction, closing sentence | stated |
| centroid within 1 m / median <= 0.05 m of reference | follows from "centroid"; tolerances grader-internal | inferable |
| centroid inside own footprint bbox | geometric consequence of a correct centroid | inferable |
| `crs_is_canonical` EPSG:4326 | GeoJSON output => WGS84 by RFC 7946 | inferable (deliberate omission, the task's main probe) |
| `crs_in_meaningful_set` {4326, 32734} | EPSG:32734 is the input CRS / natural metric CRS | inferable |

Factual claims verified: `capetown_buildings` matches `inputs/capetown_buildings.shp` (+sidecars); the input carries the (truncated) id column `building_i`; 122 features; reference output schema is exactly `building_id` + Point geometry. No missing or inaccurate claim.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads the shapefile, restores `building_i` -> `building_id`, computes the planar centroid in the projected input CRS, reprojects to EPSG:4326, and writes GeoJSON. The only unrequested operation is a stable sort by `building_id` before writing, which is a determinism guard; feature order is not graded (all comparisons are id-keyed or set-based), so it cannot change any score. No flag.

#### Specific findings
- Both current runs are the designed reprojection-miss failure mode, scored 0.947 under the soft-CRS weighted grader - model-side, not a task problem.
- Reference grades 1.0 (19/19 weight) under the weighted grader; broken solutions re-grade 0.0 / 0.5263 / 0.3684 - both non-zero scores moved (0.5714 -> 0.5263, 0.4286 -> 0.3684) because the denominator grew from 7 to 19, but each stays inside its declared `expected_score_range` ([0.50, 0.65] and [0.35, 0.50]), so only `measured_score` and the description arithmetic needed refreshing, not the ranges.
- `metadata.yaml` tolerances rationale said "subcheck total is therefore 7 ... stated as N/7" - stale after 363aed2/c749e57; refreshed to document the 9-subcheck, weight-19 arithmetic. No tolerance value changed.
- README failure modes #5 and #8 still described the pre-refactor grader (Gate-1 CRS rejection; "Gate 2 row-count check"), and the weak-agent paragraph said a CRS miss "trips Gate 1"; refreshed to the soft-CRS subcheck deduction and the `row_count_within_tolerance` subcheck. Broken-score citations updated.
- `analyst_notes` pitfalls 1 and 6 referenced "dock by one" (now a weight-1 deduction out of 19) and a "row-count gate" (now a subcheck); refreshed. Human-facing only, no version bump.
- `coverage.yaml`: added `shapefile-column-truncation` to `data_quality_issues` - the task deliberately probes the dBase truncation (README names it; peer task fio-l1-vienna-shapefile-recovery tags the same slug). The inventory row's "Data quality issues: -" plausibly means "no synthetic data corruption", so recorded as a coverage-accuracy note, not an inventory-mismatch flag.
- Output-CRS / format consistency (2c-CRS) holds: reference output WGS84 (`OGC:1.3:CRS84`) = `expected_outputs[].crs` EPSG:4326 = README EPSG:4326. The grader reprojects both sides to EPSG:32734 for the metric distance subchecks (allowed both-sides transform); the one-sided submission reprojection in `grade_crs_soft` implements the declared accept-list policy. No `prompt-grader-inconsistent` finding.
- Instruction-tightening sweep: unchanged from prior passes - no EPSG/WGS84 mention to strip, the closing sentence is the intended safety net, and the `building_id` repetition is identity-key information not pinned by `expected_outputs[]`. No instruction edit.
- HR-001 from the prior blocks (per-task design rationale for commit 64740d0, whose subject targeted dc-* tasks) is retained, re-numbered HR-001 in this block, severity low. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Commit 64740d0 ("Remove answer-giving nudges from data-cleaning task prompts") also stripped "in WGS84 (EPSG:4326)" from this geo-* task's closing sentence; per-task rationale not stated in the commit message. Documentation/intent gap only - the implicit-CRS instruction has repeatedly proven well-calibrated.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions` measured scores to the weighted grader (bbox_corner 0.5714 -> 0.5263, wrong_ids 0.4286 -> 0.3684; ranges unchanged, both still contain) and replaced the stale "N/7" rationale paragraph with the 9-subcheck / weight-19 arithmetic. Re-grade on reference: 1.0. Reason: Step 4 permits `measured_score` refreshes; no tolerance changed, no version bump.
- `README.md`: updated broken-score citations, rewrote failure modes #5 (soft-CRS deduction instead of Gate-1 rejection) and #8 (`row_count_within_tolerance` subcheck instead of "Gate 2"), and the weak-agent paragraph. Re-grade on reference: 1.0. Reason: docs-only lock-step with the post-363aed2/c749e57 grader.
- `task.json` (`analyst_notes` only): refreshed pitfalls 1 and 6 for the gate-2 removal and weighting. Re-grade on reference: 1.0. Reason: keep human-facing notes accurate; no agent-visible change, no version bump.
- `coverage.yaml`: added `shapefile-column-truncation` to `data_quality_issues` with an explanatory note; refreshed `evaluator_run_at`.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 - design-rationale - Commit 64740d0 stripped the explicit CRS from this geo-* task's closing sentence under a dc-*-targeted commit subject; rationale undocumented. Low severity, carried over.

#### Tests run
- grader on reference: 1.0 (9/9 subchecks pass, weight 19/19; gate passes)
- broken solutions re-graded: wrong_format 0.0, bbox_corner_instead_of_centroid 0.5263, wrong_ids 0.3684 (all in declared ranges)
- pytest (benchmark/eval): pass (41/41)

---

## Evaluator review 2026-06-14  (evaluator-commit `<pending>`)

### Summary
Subcheck **weight recalibration** (grading-only). Replaced the blunt
one-size-fits-all `weight=3.0`-on-all-data-content scheme (commit
c749e57) with weights reasoned from what this task actually probes. The
central skill is correct per-footprint centroid computation in a
projected CRS, so the two direct centroid-distance subchecks now carry
the highest weight; the structural row-count check was demoted to
weight 1. No check logic, threshold, or gate touched. `task.json`
version not bumped.

### Weight changes
| Subcheck | Old | New | Rationale |
|---|---|---|---|
| `centroid_within_1m` | 3 | **4** | central skill (primary centroid-correctness detector) |
| `centroid_median_distance_tight` | 3 | **4** | central skill (tight check that separates near-correct, e.g. point_on_surface, from correct) |
| `row_count_within_tolerance` | 3 | **1** | structural, not the central skill; the only realistic way to fail it (union-everything) also fails every id-keyed distance check, so it needs no heavy weight |
| `building_id_set_preserved` | 3 | 3 | unchanged - join-key preservation is central (persona explicitly required it) |
| `centroid_inside_own_footprint_bbox` | 3 | 3 | unchanged - sanity/pairing check that catches projected-tagged-as-4326 and wrong id-pairing |
| `building_id_populated` | 1 | 1 | unchanged - schema |
| `geometry_types_point` | 1 | 1 | unchanged - structural |
| `crs_is_canonical` | 1 | 1 | unchanged - cosmetic delivery-CRS slip |
| `crs_in_meaningful_set` | 1 | 1 | unchanged - CRS |

Denominator stays 19 (4 + 4 + 3 + 3 + 1x5): the +1+1 from the two
centroid checks is offset by the -2 from row_count, so prior-run scores
whose only deduction is `crs_is_canonical` are unchanged.

### Broken-solution scores: before -> after
| Broken | Before | After | Severity note |
|---|---|---|---|
| `wrong_format` | 0.0 | 0.0 | unrecoverable (gate); most severe |
| `wrong_ids` | 0.3684 | **0.2632** | lost the explicitly-required join key + every centroid check fails; most severe non-gate, correctly lowest |
| `bbox_corner_instead_of_centroid` | 0.5263 | **0.4211** | central skill (centroid) systematically wrong (~17 m); IDs/structure intact; sits above wrong_ids |
| reference | 1.0 | 1.0 | unchanged (>= 0.95 ok) |

Ordering check: monotone and defensible -
`0.0 (format) < 0.263 (wrong_ids) < 0.421 (bbox_corner) < 0.947
(reprojection-miss, cosmetic) < 1.0 (reference)`. No rank inversion;
the cosmetic CRS slip sits near the top while the two central-skill
failures drop further than under the blunt weighting. Disjoint-failure
trap checked: wrong_ids fails a strict superset of bbox_corner's failed
checks (it adds `building_id_set_preserved`), so it stays strictly
below bbox_corner under any positive weighting - up-weighting the
centroid checks cannot invert this pair.

### Prior-run re-grade (current task version, weight-19 denominator)
| Run | Adapter | Old | New |
|---|---|---|---|
| run-20260608-074701Z | deepseek-v4-flash-detailed | 0.9474 | 0.9474 |
| run-20260609-084636Z | deepseek-v4-flash-basic | 0.9474 | 0.9474 |
| run-20260607-112430Z (stale) | gemma4-26b-detailed | 0.9474 | 0.9474 |
| run-20260606-0953Z (stale) | gemma4-26b-detailed | 1.0 | 1.0 |
| run-20260606-1129Z (stale) | gemma4-26b-detailed | 0.9474 | 0.9474 |
| run-20260606-1733Z (stale) | gemma4-26b-detailed | 0.8421 | 0.7895 |

The two `current` post-c749e57 runs (run-20260608-074701Z,
run-20260609-084636Z) are unchanged at 0.947 - their only deduction is
the weight-1 `crs_is_canonical`, and the denominator is unchanged. The
one shifting run (run-20260606-1733Z, stale, a point_on_surface-style
miss that loses the median + canonical checks) drops 0.842 -> 0.789,
correctly reflecting the higher weight on the median centroid check.
No notable inversions among current runs.

### HR status
HR-001 (design-rationale for commit 64740d0) is **retained** - it is a
design-rationale flag, not a weighting flag, and is unaffected by this
pass.

### Reasoning
The central skill of a GEOMETRIC-OPS centroid task is computing the
correct centroid in the right (projected) CRS. The blunt c749e57
weighting put `row_count_within_tolerance` on equal footing (weight 3)
with the genuine centroid-correctness probes, which over-credits a
purely structural property: any solution that gets centroids right
trivially gets 122/122 rows, and the only way to break row count
(global union) simultaneously fails all the distance checks. Demoting
row_count to 1 and promoting the two direct centroid-distance checks to
4 makes a meaningful/central mistake (wrong centroid, lost join key)
cause a meaningful score drop while a cosmetic mistake (wrong delivery
CRS) only lightly dents the score (0.947). The bbox-containment and
join-key checks remain weight 3 because both detect genuine
data-content failures of the task's contract.

### Changes applied this run
#### Unilateral edits
- `grade.py`: weights only - `centroid_within_1m` 3 -> 4,
  `centroid_median_distance_tight` 3 -> 4, `row_count_within_tolerance`
  3 -> 1. No logic/threshold/gate change.
- `metadata.yaml`: rewrote the weight-arithmetic rationale paragraph;
  refreshed `broken_solutions` measured_score + expected_score_range
  (bbox_corner 0.5263 -> 0.4211, range [0.50,0.65] -> [0.35,0.50];
  wrong_ids 0.3684 -> 0.2632, range [0.35,0.50] -> [0.20,0.35]).
- `README.md`: refreshed the two broken-score citations in the
  failure-mode list.

#### Tests run
- grader on reference: 1.0 (9/9 subchecks pass; gate passes)
- broken solutions re-graded: wrong_format 0.0,
  bbox_corner_instead_of_centroid 0.4211, wrong_ids 0.2632 (all in
  newly-declared ranges)
- pytest: not run (orchestrator runs the suite)
