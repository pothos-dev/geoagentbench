# Implementation notes — geo-l1-tokyo-busstop-buffer

## Status
completed

## Summary
L1 geometric-operation task, redesigned to test **unprompted CRS reasoning
for metric buffering**.  Input converted from EPSG:6677 to WGS84.
Instruction no longer mentions any CRS or says "honest metric distance,
not degrees".  The model must independently recognise that buffering in
WGS84 produces degree-radius polygons and choose an appropriate projected
CRS.

## Changes from previous version (2026-05-08-a → 2026-05-17-a)
- Input data: converted from EPSG:6677 to EPSG:4326 (WGS84)
- Instruction: removed "honest metric distance, not degrees" and "EPSG:6677"
- Output: removed CRS requirement from expected_outputs
- Grader: removed CRS gate check; all geometric comparisons now done by
  reprojecting submission to EPSG:6677 (reference CRS); area tolerance
  widened to ±2%; IoU threshold lowered to 0.95
- Broken solutions: added `broken_degrees_buffer` (buffered in WGS84 degrees)
- Reference: regenerated from WGS84 input with explicit reproject to EPSG:6677

## Verification results
- Reference grader score: 1.00 (5/5 subchecks)
- Broken-solution scores:
  - wrong_format: 0.00 (expected [0.0, 0.0])
  - degrees_buffer: 0.40 (2/5) (expected [0.3, 0.5])
  - wrong_radius: 0.60 (3/5) (expected [0.55, 0.65])
  - shifted_centers: 0.40 (2/5) (expected [0.35, 0.45])

## Failure-mode coverage
- Buffered in WGS84 degrees (primary target): broken_degrees_buffer
- Wrong buffer radius: broken_wrong_radius
- Shifted centres + wrong radius: broken_shifted_centers
- Wrong output format: broken_wrong_format
- Drop connector_id: principled — Gate 1 schema check
- Emit Point instead of Polygon: principled — Gate 2 geometry type check
- Filter out connectors: principled — Gate 2 count tolerance

## Open issues
(none)

## Library extensions
(none)

---

# Evaluator review log

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Originally authored as an L1 geometric-operations test where a 300-point Tokyo
connector layer was supplied in **projected** EPSG:6677 (JGD2011 Plane IX) and
the agent was asked to produce a 400 m planar buffer per connector, exported as
GeoParquet in EPSG:6677. The instruction explicitly told the agent to compute
"in metres on the JGD2011 Plane IX grid the input is already in" and named the
output CRS EPSG:6677. The grader checked count, areas (±1%), per-id IoU (≥0.99),
schema, and explicit CRS match. The inventory row, the first README, and the
2026-05-08 first commit all describe this projected-CRS, hand-held variant.

The task was substantially redesigned on 2026-05-17 to test **unprompted CRS
reasoning**: input converted to WGS84, all CRS mentions stripped from the
instruction, output CRS requirement dropped, grader generalised to reproject to
EPSG:6677 internally with widened tolerances (±2% area, IoU ≥0.95), and a
`broken_degrees_buffer` failure mode added as the primary target. This is the
current task design.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | fbd20f2 | initial-authoring | Initial task: WGS84-projected input, EPSG:6677 buffers, strict CRS grader | (initial) |
| 2026-05-08 | 001e459 | docs-change | Path move under benchmark/eval/tasks/ | Commit msg: "split into authoring/ and eval/ subtrees" (mechanical) |
| 2026-05-13 | 284b843 | prompt-change | Added `tags` dict to task.json (region/crs/formats/etc.) | Commit msg: "add structured tags to all 36 task.json files" — derived from inventory axes |
| 2026-05-13 | 1710715 | prompt-change | Added "Output schema:" block to instruction (filename, column, geometry type) | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | a3a8d53 | docs-change | Path move benchmark/eval/tasks/ -> benchmark/tasks/ | Commit msg: "move benchmark/eval/tasks/ to benchmark/tasks/" (mechanical) |
| 2026-05-13 | 8915010, 1b8dda1, 3c65373, cfbdc7c | docs-change | Added/regenerated assets/image-prompt.md and image.webp | Commit msgs: image-card generation passes |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded "Output schema:" bullets into prose, kept all technical requirements | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | f40e39e | prompt-change | Stripped "on the JGD2011 Plane IX grid the input is already in" -> "in a projected CRS" | Commit msg: "Strip deducible information from GEO task instructions" |
| 2026-05-15 | 6500d9a | prompt-change | Stripped "measured in metres in a projected CRS" -> "honest metric distance, not degrees" (output EPSG:6677 line still kept) | Commit msg: "Strip deducible information from GEO task instructions (batch 2)" |
| 2026-05-17 | 6deb6e7 | mixed (prompt-change + grader-change + data-change + reference-change + tests-change) | Converted input from EPSG:6677 to WGS84; removed "honest metric distance, not degrees" and "EPSG:6677" from instruction; dropped output-CRS requirement from expected_outputs; rewrote grader to reproject to EPSG:6677 internally with ±2% area and IoU ≥0.95; regenerated reference outputs from WGS84 with explicit reproject; added `broken_degrees_buffer` failure | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-26 | 29a9ae3 | docs-change | Layout reorg: IMPLEMENTATION_NOTES -> audit/AUTHORING_HISTORY.md, data/ -> inputs/, reference -> reference/solution + reference/failures, image -> assets/; grader/generator path updates | Commit msg: "Reorganize task folder layout" (mechanical, no semantic change) |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:29:17+00:00 (commit 6deb6e7, class: mixed prompt-change + grader-change + data-change + reference-change + tests-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:54:11Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:24:31Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:48:55Z | 1.0 | done | current |

Stale (pre-cutoff) runs considered and excluded: run-20260512-0833Z, run-20260512-1620Z, run-20260512-1754Z, run-20260512-2316Z, run-20260513-0110Z, run-20260513-0922Z, run-20260513-0926Z, run-20260513-0928Z, run-20260513-0937Z, run-20260513-0943Z, run-20260514-0946Z, run-20260514-1245Z, run-20260514-1554Z, run-20260515-0624Z, run-20260515-0926Z, run-20260515-2053Z, run-20260516-0743Z, run-20260516-1130Z, run-20260516-2248Z, run-20260517-0134Z, run-20260517-0304Z, run-20260517-0614Z — all pre-date the 2026-05-17 redesign and answer a different (projected-input) version of the task.

#### Verdict
**calibrated**

Reference grader scores 1.0 on the bundled reference output (5/5 subchecks, gates pass). All three `current` runs scored 1.0 — Claude Opus, DeepSeek V4 Flash, and Gemma 4 26B all reprojected to EPSG:6677, buffered 400 m, and saved as GeoParquet. Inspection of the Gemma and DeepSeek `outputs/solve.py` shows the agents explicitly recognised that the input was WGS84 (`crs.is_geographic`) and picked EPSG:6677 (the canonical JGD2011 Plane IX zone for Tokyo). This is exactly the skill the 2026-05-17 redesign aimed to probe, so the post-cutoff 3/3 hit-rate is informative, not embarrassing: even mid-tier OpenRouter models have enough geospatial knowledge to know "Tokyo + metres + WGS84 input -> reproject to a Japanese plane CRS". The instruction does not name any CRS, projection family, projection method, or tolerance; it only specifies the goal (400 m walkable catchment), the file/format/column contract, and the persona. The grader does not over-pin the answer (it reprojects to EPSG:6677 itself and accepts ±2% area / IoU ≥0.95 in projected units, so UTM 54N, JGD2011 Plane IX, JGD2000 Plane IX, and similar Tokyo-region projections all score full marks). With only three current runs across three families, calling this `too-easy` would require either a clear "gift" left in the instruction (there is none — the prompt is already short, prose-only, and CRS-silent) or evidence that an L1-incompetent agent passes anyway (we do not have such an agent in the current cohort). The 2026-05-17 author block already records the design choice "instruction no longer mentions any CRS"; the task is doing what it was redesigned to do.

#### Specific findings
- Instruction (`task.json:instruction`) contains no CRS, no projection family, no algorithm name, and no procedural decomposition. The only retained "hint" is "400 m" with metric units, which is the problem definition itself (per `instruction-stripping-guide.md` §EDGE CASES: "Honest 400 m buffer measured in metres" stays). No further stripping is available without making the task underspecified.
- Grader (`grade.py:60-67`) silently assigns EPSG:4326 to submissions with no CRS metadata before reprojecting to EPSG:6677. This is lenient but coherent — an agent that produced WGS84-degree buffers and forgot to set the CRS would still be caught by the area check (areas blow up after reprojection). Confirmed by the recorded `broken_degrees_buffer` measured score of 0.4.
- Broken-solution measured scores in `metadata.yaml` (0.0 / 0.4 / 0.6 / 0.4) all sit inside their declared `expected_score_range`; no recalibration needed.
- Inventory row (`benchmark/authoring/inventory.md:493-516`) matches the current task on category, difficulty, region, formats, geometry types, themes, and explicitly notes "CRS out: n/a (model must independently choose a projected CRS for metric buffering)". Consistent with current `task.json` / `metadata.yaml` / `README.md`.
- `task.json.tags.crs` still lists `["EPSG:4326"]` only (input CRS). This is consistent with the redesign — no output CRS is specified — but worth noting for the matrix: the task exercises the wgs84→conformal reprojection axis even though only EPSG:4326 appears in the tags. Captured in `coverage.yaml > crs_variants: [wgs84, conformal]`.
- Only 3 `current` runs are available. Three independent families (Anthropic Claude, DeepSeek, Google Gemma) is enough breadth to read "calibrated" rather than "insufficient-evidence", but a future sweep with weaker models would tighten the verdict.
- No HUMAN-REVIEW markers required: all design commits have an explanatory message, the prompt-vs-grader split is unambiguous (output CRS deliberately unspecified by design), no coverage-vocabulary gap, no inventory mismatch.

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated as-is; no grader tolerance change, no instruction edit, no broken-set rescoring needed)

#### Proposed but not applied (HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- pytest: pass (35 passed)

## Evaluator review 2026-05-27  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 as an L1 geometric-operations task: a 300-point Tokyo
connector layer (Overture `transportation.connector`, sliced from a Tokyo
Station bbox) shipped in **projected** EPSG:6677 (JGD2011 Plane IX), with the
agent asked to draw a 400 m planar buffer per connector and export GeoParquet.
The original instruction named the CRS and told the agent it was already in
plane-IX metres, so no reprojection reasoning was required. The inventory row
(`benchmark/authoring/inventory.md:493-516`) and the first README describe this
hand-held projected-input variant.

The task was substantially redesigned on 2026-05-17 (commit 6deb6e7) to test
**unprompted CRS reasoning for metric buffering**: input converted to WGS84, all
CRS / projection mentions stripped from the instruction, output-CRS requirement
dropped from `expected_outputs`, grader generalised to reproject the submission
to EPSG:6677 internally (±2% area, IoU ≥0.95), and a `broken_degrees_buffer`
failure added as the primary target. This is the current design and matches the
inventory row's "CRS out: n/a (model must independently choose a projected CRS)".

This is the **second** evaluator pass. The first (2026-05-26, evaluator-commit
7dcc9c1) reviewed the identical post-redesign state and returned `calibrated`
with no edits. Nothing design-affecting has changed since; this pass re-verifies.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9ca64c5 | initial-authoring | Initial task: projected EPSG:6677 input, 400 m buffers, strict CRS grader (named the CRS in the instruction) | (initial) — predates the repo restructure, so `--follow` on the dir misses it; found via slug search |
| 2026-05-08 | fbd20f2 / 001e459 | docs-change | Repo restructure + authoring/eval subtree split (path moves only) | Commit msgs: "restructure: split repo…" / "split into authoring/ and eval/ subtrees" (mechanical) |
| 2026-05-13 | a3a8d53 | docs-change | Path move benchmark/eval/tasks/ -> benchmark/tasks/ | Commit msg: "move benchmark/eval/tasks/ to benchmark/tasks/" (mechanical) |
| 2026-05-13 | 8915010, 1b8dda1, 3c65373, cfbdc7c | docs-change | Added/regenerated assets image-prompt.md and image.webp | Commit msgs: image-card generation passes |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded "Output schema:" bullets into prose, kept all technical requirements | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | f40e39e | prompt-change | Stripped "on the JGD2011 Plane IX grid the input is already in" -> "in a projected CRS" | Commit msg: "Strip deducible information from GEO task instructions" |
| 2026-05-15 | 6500d9a | prompt-change | Stripped "measured in metres in a projected CRS" -> "honest metric distance, not degrees" (output EPSG:6677 line still kept) | Commit msg: "Strip deducible information from GEO task instructions (batch 2)" |
| 2026-05-17 | 6deb6e7 | mixed (prompt + grader + data + reference + tests) | Converted input EPSG:6677 -> WGS84; removed "honest metric distance, not degrees" and "EPSG:6677" from instruction; dropped output-CRS requirement; rewrote grader to reproject submission to EPSG:6677 internally (±2% area, IoU ≥0.95, no CRS gate); regenerated reference from WGS84; added `broken_degrees_buffer` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg: IMPLEMENTATION_NOTES -> audit/AUTHORING_HISTORY.md, data/ -> inputs/, reference -> reference/solution + reference/failures, image -> assets/; grader/generator path-string updates only (verified diff: only path constants changed, no logic) | Commit msg: "Reorganize task folder layout" (mechanical, no semantic change) |
| 2026-05-26 | 7dcc9c1 | docs-change | First evaluator pass: wrote audit/AUTHORING_HISTORY.md review block, coverage.yaml, audit/status.json; verdict calibrated, no task edits | Commit msg: "Re-evaluate geo-l1-tokyo-busstop-buffer: calibrated, no edits" (evaluator artefacts) |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:29:17+00:00 (commit 6deb6e7, class: mixed prompt-change + grader-change + data-change + reference-change + tests-change). The 2026-05-26 reorg (29a9ae3) was verified to be path-only and the 2026-05-26 evaluator commit (7dcc9c1) touched only audit artefacts, so neither moves the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:48:18Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T17:48:52Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:00:19Z | 1.0 | done | current |

No new runs since the 2026-05-26 evaluation; the same three post-cutoff runs are the available evidence. Stale (pre-cutoff) runs were re-confirmed and excluded: 22 run dirs dated 2026-05-12 through 2026-05-17T06:14Z all predate the redesign and answer the projected-input variant.

#### Verdict
**calibrated**

Re-verified end to end. The reference output scores 1.0 (5/5 subchecks, 2/2 gates). All three `current` runs scored a full 5/5: each produced `tokyo_stop_catchments.geoparquet`, 300 Polygon rows, `connector_id` preserved, and buffers whose area reprojected to EPSG:6677 is 501847.8 m² (median) — within ±2% of π·400² = 502654.8 m². The slight under-shoot vs the exact circle area is the expected geopandas `quad_segs=8` polygon approximation, comfortably inside tolerance. The DeepSeek and Gemma submissions carry EPSG:4326 CRS metadata; the Opus submission carries OGC:CRS84 (= WGS84) metadata — all three buffered in a metric CRS and reprojected the geometry back to lat/lon for output, which the grader reprojects to EPSG:6677 for comparison. The instruction names no CRS, no projection family, no algorithm, and no procedural decomposition; the only quantitative hint ("400 m") is the problem definition itself. With three independent families (Anthropic, DeepSeek, Google) all passing but no extractable gift in the prompt and no L1-incompetent agent in the cohort, this reads `calibrated` rather than `too-easy`. State is unchanged from the 2026-05-26 pass; that verdict still holds.

#### 2c-CRS output-CRS / format consistency
- Reference output CRS: EPSG:6677; `expected_outputs[]` deliberately specifies **no** CRS (`{name, format: geoparquet, geometry_type: Polygon}`), which is the design contract for an unprompted-CRS task. README §Output explicitly states "No output CRS specified — the model chooses." All three sources agree: the output CRS is intentionally unconstrained.
- The grader reprojects **both** the submission *and* (implicitly, since the reference is already EPSG:6677) compares in EPSG:6677. The source input point file is also reprojected to EPSG:6677 for the contains-point check. This is the allowed "transform both sides the same way" pattern, **not** a one-sided reprojection — the grader never coerces only the submission to match a mismatched reference. No `prompt-grader-inconsistent` finding.
- README's stated output CRS ("the model chooses") matches the reference contract. No stale-README fix needed.

#### Specific findings
- Instruction (`task.json:instruction`) contains no CRS, projection family, algorithm name, or procedural steps. The retained "400 m" metric hint is the problem definition (`instruction-stripping-guide` edge case: an honest 400 m buffer measured in metres stays). No further stripping available without underspecifying the task.
- Grader (`grade.py:61-67`) assigns EPSG:4326 to a submission with null CRS before reprojecting to EPSG:6677. Lenient but coherent: a degree-buffer submission that forgot to set its CRS still fails the area check after reprojection (confirmed: `broken_degrees_buffer` = 0.4).
- Broken-solution scores re-measured this pass: wrong_format 0.0, degrees_buffer 0.4, wrong_radius 0.6, shifted_centers 0.4 — all match the recorded `metadata.yaml > broken_solutions > measured_score` and sit inside their declared `expected_score_range`. No recalibration needed.
<!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" -->
- `inputs/_prepare.py` docstring/body still describes shipping the bundled input in EPSG:6677 (a leftover from the pre-redesign authoring helper), but the committed `inputs/tokyo_connectors.geojson` is verified to be EPSG:4326. The helper is authoring-time only, not run at grading time, and `inputs/` is outside the evaluator's edit authority — recorded as HR-001 (low) so the stale helper narrative can be reconciled by a human.
- Inventory row (`inventory.md:493-516`) matches current task on category, difficulty, region, formats, geometry types (Point -> Polygon), theme (`transportation.connector`), OSM tag (`railway`), scale (small), and "CRS out: n/a". Consistent.
- `task.json.tags.crs` lists only `["EPSG:4326"]` (input CRS); the task nevertheless exercises a wgs84->conformal reprojection internally. Captured in `coverage.yaml > crs_variants: [wgs84, conformal]`. Consistent with the redesign (no output CRS pinned).
- Only 3 `current` runs across 3 families — enough breadth to read `calibrated` over `insufficient-evidence`, but a future sweep with a weaker L1 agent would tighten the read.

### 3. Changes applied this run

#### Unilateral edits
(none — task re-verified calibrated; no grader tolerance change, no instruction edit, no broken-set rescoring needed; only the evaluator artefacts AUTHORING_HISTORY.md / coverage.yaml / status.json refreshed)

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — design-rationale — `inputs/_prepare.py` docstring/code still reprojects to EPSG:6677, contradicting the committed WGS84 input and the redesign intent; `inputs/` is outside evaluator edit authority. A human should reconcile the stale authoring helper with the redesigned WGS84 input.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- broken solutions: 0.0 / 0.4 / 0.6 / 0.4 (all in declared ranges)
- pytest: pass (35 passed)

## Evaluator review 2026-05-28  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 as an L1 geometric-operations task: a Tokyo `transportation.connector`
point layer (Overture, sliced from a Marunouchi/Yaesu bbox around Tokyo Station)
shipped in **projected** EPSG:6677 (JGD2011 Plane IX), with the agent asked to
produce a 400 m planar buffer per connector and export GeoParquet. The original
instruction named the CRS and told the agent the input was already in plane-IX
metres, so no reprojection reasoning was required.

The task was substantially redesigned on 2026-05-17 (commit 6deb6e7) to test
**unprompted CRS reasoning for metric buffering**: input converted to WGS84, all
CRS / projection mentions stripped from the instruction, output-CRS requirement
dropped from `expected_outputs`, grader generalised to reproject the submission
to EPSG:6677 internally (±2% area, IoU ≥0.95), `broken_degrees_buffer` added as
the primary target failure. This remains the current design; matches the
inventory row's "CRS out: n/a (model must independently choose a projected CRS)".

This is the **third** evaluator pass. The first (2026-05-26, evaluator-commit
7dcc9c1) and second (2026-05-27, evaluator-commit c0bbdbd) both returned
`calibrated` with no edits. Since the last pass, two new sweeps brought four
additional `current` runs into evidence, one of which (Gemma 4 26B,
2026-05-27T2321Z) scored 0.6 due to picking Web Mercator for the metric buffer
— a legitimate failure mode that demonstrates the task is discriminating, not
"too easy". The post-cutoff hit-rate dropped from 3/3 to 6/7.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9ca64c5 | initial-authoring | Initial task: projected EPSG:6677 input, 400 m buffers, strict CRS grader (named the CRS in the instruction) | (initial) — predates the repo restructure; found via slug search |
| 2026-05-08 | fbd20f2 / 001e459 | docs-change | Repo restructure + authoring/eval subtree split (path moves only) | Commit msgs: "restructure: split repo…" / "split into authoring/ and eval/ subtrees" (mechanical) |
| 2026-05-13 | a3a8d53 | docs-change | Path move benchmark/eval/tasks/ -> benchmark/tasks/ | Commit msg: "move benchmark/eval/tasks/ to benchmark/tasks/" (mechanical) |
| 2026-05-13 | 8915010, 1b8dda1, 3c65373, cfbdc7c | docs-change | Added/regenerated assets image-prompt.md and image.webp | Commit msgs: image-card generation passes |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded "Output schema:" bullets into prose, kept all technical requirements | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | f40e39e | prompt-change | Stripped "on the JGD2011 Plane IX grid the input is already in" -> "in a projected CRS" | Commit msg: "Strip deducible information from GEO task instructions" |
| 2026-05-15 | 6500d9a | prompt-change | Stripped "measured in metres in a projected CRS" -> "honest metric distance, not degrees" (output EPSG:6677 line still kept) | Commit msg: "Strip deducible information from GEO task instructions (batch 2)" |
| 2026-05-17 | 6deb6e7 | mixed (prompt + grader + data + reference + tests) | Converted input EPSG:6677 -> WGS84; removed "honest metric distance, not degrees" and "EPSG:6677" from instruction; dropped output-CRS requirement; rewrote grader to reproject submission to EPSG:6677 internally (±2% area, IoU ≥0.95, no CRS gate); regenerated reference from WGS84; added `broken_degrees_buffer` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg: IMPLEMENTATION_NOTES -> audit/AUTHORING_HISTORY.md, data/ -> inputs/, reference -> reference/solution + reference/failures, image -> assets/; grader/generator path-string updates only | Commit msg: "Reorganize task folder layout" (mechanical, no semantic change) |
| 2026-05-26 | 7dcc9c1 | docs-change | First evaluator pass artefacts (AUTHORING_HISTORY block, coverage.yaml, status.json); verdict calibrated, no task edits | Commit msg: "Re-evaluate geo-l1-tokyo-busstop-buffer: calibrated, no edits" |
| 2026-05-27 | c0bbdbd | docs-change | Second evaluator pass artefacts (AUTHORING_HISTORY block + coverage.yaml + status.json refresh; HR-001 raised against stale `inputs/_prepare.py`); verdict calibrated, no task edits | Commit msg: "Re-evaluate geo-l1-tokyo-busstop-buffer: calibrated, no task edits" |
| 2026-05-28 | 622342b | docs-change | Removed unused `prompt_version: 2026-05-17-a` line from metadata.yaml as part of a repo-wide drop; `task.json`/`grade.py`/`inputs/`/`reference/` untouched | Commit msg: "Add task content versioning; drop unused prompt_version" — does not change prompt, grader logic, tolerances, or inputs; not a design-affecting change |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:29:17+00:00 (commit 6deb6e7, class: mixed prompt-change + grader-change + data-change + reference-change + tests-change). Commit 622342b on 2026-05-28 only stripped the unused `prompt_version` line from `metadata.yaml`; verified by re-reading the diff. Neither tolerances, grader logic, instruction, inputs, nor `expected_outputs` were touched, so the cutoff does not advance.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:48:18Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T17:48:52Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:00:19Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T22:20:21Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:55:17Z | 0.6 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:42:07Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:06:39Z | 1.0 | done | current |

Stale (pre-cutoff) runs considered and excluded: 22 run dirs dated 2026-05-12 through 2026-05-17T06:14Z all predate the redesign and answer the projected-input variant.

#### Verdict
**calibrated**

Reference output regrades 1.0 (5/5 subchecks, 2/2 gates). Across seven `current` runs from three families (Anthropic Claude Opus 4.7 ×3, DeepSeek V4 Flash ×1, Google Gemma 4 26B ×3) the score distribution is 1.0 ×6 and 0.6 ×1. The 0.6 hit was Gemma's 2026-05-27T2321Z run: its `solve.py` (see `outputs/solve.py`) chose `EPSG:3857` (Web Mercator) for the buffer ("EPSG:3857 is a good general-purpose projected CRS"), buffered 400 in Mercator units, then reprojected back to WGS84. Tokyo sits at ≈35° N where the Mercator scale factor is sec(35°) ≈ 1.221, so 400 Mercator metres correspond to ≈327 ground metres; the grader (reprojecting to EPSG:6677) measured a median buffer area of 330 330 m² versus the expected π·400² = 502 654.8 m² and zero polygons fell inside the ±2% band. `buffer_contains_source_point` still passed (the buffer is centred correctly, just too small), and ID-set checks passed, giving the partial score of 0.6 — exactly the behaviour the `broken_wrong_radius` failure-mode test calibrates against. This is a **legitimate L1 discrimination**: Web Mercator is famously *not* metric-correct at non-equatorial latitudes, and a geospatially literate agent in Tokyo should reach for JGD2011 Plane IX / UTM 54N / equivalent. The other Gemma runs (2026-05-26 and 2026-05-28T0317Z) picked correct Japanese plane CRSes and scored 1.0, so the failure is intermittent within one model family, which is precisely the discriminating signal an L1 task should produce. Verdict moves from "calibrated on 3/3 passes" to "calibrated with an in-distribution failure observed" — the prior `too-easy` worry is now empirically retired. Instruction names no CRS, no projection family, no algorithm, no procedural decomposition; the only quantitative hint ("400 m") is the problem definition itself. No prompt-grader inconsistency, no over-/under-tolerance, no gift left in the instruction.

#### 2c-CRS output-CRS / format consistency
- Reference output CRS: EPSG:6677; `expected_outputs[]` deliberately specifies **no** CRS (`{name, format: geoparquet, geometry_type: Polygon}`), which is the design contract for an unprompted-CRS task. README §Output states "No output CRS specified — the model chooses." All three sources agree: the output CRS is intentionally unconstrained.
- Grader (`grade.py:_to_ref_crs` + per-subcheck use) reprojects **both** sides into EPSG:6677 for the area / IoU / contains-point comparison (reference is already in 6677 on disk; submission and input are reprojected the same way). This is the allowed "transform both sides the same way" pattern, **not** a one-sided reprojection that papers over a contract mismatch.
- README's stated output CRS ("the model chooses") matches the reference contract. No stale-README fix needed.

#### Specific findings
- Instruction (`task.json:instruction`) contains no CRS, projection family, algorithm name, or procedural steps; the retained "400 m" metric hint is the problem definition itself. No further stripping available without underspecifying the task.
- Grader (`grade.py:61-67`) assigns EPSG:4326 to a submission with null CRS metadata before reprojecting to EPSG:6677. Lenient but coherent — a degree-buffer submission that forgot to set its CRS still fails the area check after reprojection (confirmed by re-measured `broken_degrees_buffer` = 0.4).
- Broken-solution scores re-measured this pass: `broken_wrong_format` 0.0, `broken_degrees_buffer` 0.4, `broken_wrong_radius` 0.6, `broken_shifted_centers` 0.4 — all match the recorded `metadata.yaml > broken_solutions > measured_score` and sit inside their declared `expected_score_range`. No recalibration needed.
- The 2026-05-27T2321Z Gemma 0.6 run scored exactly within the `broken_wrong_radius` expected_score_range — i.e. the task's broken-set design already anticipated "agent picks a metric-but-scale-wrong CRS" as an off-by-radius-equivalent failure, and the live agent fell into that bucket. The grader does the right thing here.
- HR-001 from the 2026-05-27 pass (`inputs/_prepare.py` stale narrative about reprojecting to EPSG:6677) is still open. Re-verified this pass: the committed `inputs/tokyo_connectors.geojson` is EPSG:4326 (correct), but `_prepare.py:85-90` still calls `.to_crs("EPSG:6677")` before writing. The helper is authoring-time only and not run at grading time, and `inputs/` is outside the evaluator's edit authority — re-flagged as HR-001 (low) so a human can reconcile.
- Inventory row (`inventory.md:493-516`) matches current task on category, difficulty, region, formats, geometry types (Point -> Polygon), theme (`transportation.connector`), OSM tag (`railway`), scale (small), and "CRS out: n/a". Consistent.
- `task.json` has no explicit `version` field (implicit v1, per the 2026-05-28 versioning convention). No unilateral edits this pass, so no version bump required.
- `task.json.tags.crs` lists only `["EPSG:4326"]` (input CRS); the task exercises a wgs84->conformal reprojection internally, which is captured in `coverage.yaml > crs_variants: [wgs84, conformal]`. Consistent with the redesign (no output CRS pinned).

<!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" -->
`inputs/_prepare.py` lines 85-94 still reproject to EPSG:6677 and the file's
docstring describes shipping the bundled input projected, contradicting the
post-2026-05-17 redesign that requires a **WGS84** input (which is what the
committed `tokyo_connectors.geojson` actually is). The helper is not run at
grading time so it cannot mis-grade anything, but the narrative is
misleading for any future maintainer. A human with `inputs/` edit authority
should either (a) remove the `to_crs("EPSG:6677")` call and update the
docstring to match the redesign, or (b) regenerate `tokyo_connectors.geojson`
via the corrected helper to confirm input parity. Re-categorised from
`design-rationale` (where the prior pass placed it) to
`reference-or-data-edit-needed` since the action item is a concrete edit to
`inputs/`, which is outside the evaluator's edit authority.

### 3. Changes applied this run

#### Unilateral edits
(none — task re-verified calibrated; runs now include an in-distribution
failure that confirms the L1 discrimination is working; no grader tolerance
change, no instruction edit, no broken-set rescoring needed; only the
evaluator artefacts AUTHORING_HISTORY.md / coverage.yaml / status.json
refreshed)

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — `inputs/_prepare.py` still
  reprojects to EPSG:6677 and its docstring describes a projected input,
  contradicting the 2026-05-17 WGS84 redesign; `inputs/` is outside
  evaluator edit authority. (Carried over from the 2026-05-27 pass with
  category refined.)

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- broken solutions: wrong_format 0.0 / degrees_buffer 0.4 / wrong_radius 0.6 / shifted_centers 0.4 (all in declared ranges)
- pytest: pass (41 passed)

## Evaluator review 2026-06-06  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 as an L1 geometric-operations task: a Tokyo
`transportation.connector` point layer shipped in projected EPSG:6677 with
the agent asked to draw a 400 m planar buffer per connector and export
GeoParquet. The 2026-05-17 redesign (commit 6deb6e7) converted the input to
WGS84, stripped all CRS guidance from the instruction, dropped the output-CRS
requirement, generalised the grader to reproject the submission to EPSG:6677
internally (±2% area, IoU ≥ 0.95), and added `broken_degrees_buffer` as the
primary target. The task now tests unprompted CRS reasoning for metric
buffering; this matches the inventory row's "CRS out: n/a".

This is the **fourth** evaluator pass. Prior passes (2026-05-26 7dcc9c1,
2026-05-27 c0bbdbd, 2026-05-28 c067828) all returned `calibrated` with no
task edits. The design-affecting cutoff has not advanced since 2026-05-17.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9ca64c5 | initial-authoring | Initial task: projected EPSG:6677 input, 400 m buffers, strict CRS grader | (initial) — found via slug search; predates the repo restructure |
| 2026-05-08 / 2026-05-13 | fbd20f2 / 001e459 / a3a8d53 | docs-change | Repo restructures and path moves | Mechanical |
| 2026-05-13 | 89150101, 1b8dda1, 3c65373, cfbdc7c | docs-change | Task card image assets | Image-card generation passes |
| 2026-05-13 | 12c9fb0 | prompt-change | Folded "Output schema:" bullets into prose | Commit msg |
| 2026-05-14 | f40e39e | prompt-change | Stripped "on the JGD2011 Plane IX grid the input is already in" | Commit msg: "Strip deducible information from GEO task instructions" |
| 2026-05-15 | 6500d9a | prompt-change | Stripped "measured in metres in a projected CRS" → "honest metric distance, not degrees" | Commit msg |
| 2026-05-17 | 6deb6e7 | mixed (prompt + grader + data + reference + tests) | Converted input to WGS84; stripped all remaining CRS hints; rewrote grader to reproject internally; regenerated reference; added `broken_degrees_buffer` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg; path-string updates only | Commit msg (mechanical) |
| 2026-05-26 | 7dcc9c1 | docs-change | First evaluator pass artefacts; verdict calibrated | Commit msg |
| 2026-05-27 | c0bbdbd | docs-change | Second evaluator pass artefacts; verdict calibrated; HR-001 raised against stale `_prepare.py` | Commit msg |
| 2026-05-28 | 622342b | docs-change | Removed unused `prompt_version` line from metadata.yaml as part of a repo-wide drop | Commit msg — not design-affecting |
| 2026-05-28 | c067828 | docs-change | Third evaluator pass artefacts; verdict calibrated; HR-001 re-flagged | Commit msg |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:29:17+00:00 (commit 6deb6e7, class: mixed prompt-change + grader-change + data-change + reference-change + tests-change). No commits since touch `task.json.instruction`, `inputs/`, `expected_outputs[]`, `grade.py`, `metadata.yaml > tolerances`, or `reference/`. The cutoff is unchanged.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:48:18Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T17:48:52Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:00:19Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T22:20:21Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:55:17Z | 0.6 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T02:42:07Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:06:39Z | 1.0 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:42:30Z | 1.0 | done | current |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T21:50:30Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:16:05Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:26:47Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:02:32Z | 0.6 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T17:05:25Z | 1.0 | done | current |
| run-20260606-0942Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:42:49Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:16:38Z | 1.0 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:34:09Z | 0.6 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | (cancelled) | cancelled | current (no score) |

Stale (pre-cutoff) runs excluded: 22 run dirs dated 2026-05-12 through 2026-05-17T06:14Z.

#### Verdict
**calibrated**

Reference output regrades 1.0 (5/5 subchecks, 2/2 gates). Across 16 scored `current` runs spanning Anthropic Claude Opus, DeepSeek V4 Flash/Pro, and Google Gemma 4 26B, the score distribution is 1.0 × 13 and 0.6 × 3. All three 0.6 hits came from Gemma 4 26B and show the same signature in `score.json`: 0/300 polygons within ±2% of π·400² with median area 330 330 m² versus the 502 654.8 m² target, contains-point and ID checks passing. That is the unmistakable Web Mercator (EPSG:3857) at Tokyo latitude: sec(35.6°)² ≈ 1.521, and 502 655 / 1.521 ≈ 330 477, matching the observed 330 330 to within rounding. Web Mercator is famously *not* metric-correct off the equator; a geospatially literate agent in Tokyo should reach for JGD2011 Plane IX or UTM 54N. The Gemma family clearly has a Mercator failure mode here but also passes on most attempts (5/8 since 2026-05-26). That intermittent within-family failure is exactly the discrimination signal an L1 task should produce.

The instruction names no CRS, projection family, algorithm, or procedural step; the only quantitative hint ("400 m") is the problem definition itself. The grader does not over-pin the answer (reprojects internally to EPSG:6677, accepts ±2% area / IoU ≥ 0.95). No prompt-grader inconsistency, no over- or under-tolerance, no gift left in the instruction.

#### 2c-CRS output-CRS / format consistency
- Reference output CRS: EPSG:6677. `expected_outputs[]` deliberately specifies **no** CRS (`{name, format: geoparquet, geometry_type: Polygon}`) by design. README §Output states "No output CRS specified — the model chooses." All three sources agree.
- Grader (`grade.py:_to_ref_crs`) reprojects **both** the submission and the input (for the contains-point subcheck) into EPSG:6677, while the reference is already in 6677 on disk. This is the allowed "transform both sides the same way" pattern, not a one-sided reprojection that would paper over a contract mismatch.
- README's "the model chooses" matches the reference contract. No stale-README fix needed.

#### Specific findings
- Instruction lightly rewritten in this pass for house style (see Section 3); the deliberate CRS omission and "400 m" metric hint are preserved.
- `analyst_notes` was missing; authored in this pass to surface the unprompted-CRS gotcha and the Web Mercator pitfall now observed empirically.
- `task.json.version` introduced (1 → 2) per the 2026-05-28 versioning convention, since the instruction was edited.
- Grader (`grade.py:61-67`) silently assigns EPSG:4326 to a submission with null CRS metadata before reprojecting to EPSG:6677. Lenient but coherent: a degree-buffer submission still fails the area check after reprojection (confirmed `broken_degrees_buffer` = 0.4 this pass).
- Broken-solution scores re-measured this pass: `broken_wrong_format` 0.0, `broken_degrees_buffer` 0.4, `broken_wrong_radius` 0.6, `broken_shifted_centers` 0.4 — all match the recorded `measured_score` and sit inside their declared `expected_score_range`.
- HR-001 from the prior pass (`inputs/_prepare.py` still calls `.to_crs("EPSG:6677")` and its docstring describes a projected input, contradicting the 2026-05-17 WGS84 redesign) is re-flagged unchanged; `inputs/` is outside the evaluator's edit authority.
- Inventory row matches current task on every axis. Consistent.

<!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" -->
`inputs/_prepare.py` still reprojects to EPSG:6677 and its docstring describes
shipping the bundled input projected, contradicting the 2026-05-17 WGS84
redesign. The committed `inputs/tokyo_connectors.geojson` is correctly
EPSG:4326, so this does not affect grading, but the narrative is misleading
for any future maintainer. A human with `inputs/` edit authority should
either remove the `to_crs("EPSG:6677")` call and update the docstring, or
regenerate the input via the corrected helper. The human applying the fix
should also bump `task.json.version` once more (since `inputs/` changes
require a bump). Carried over from the 2026-05-27 pass with category and
narrative unchanged.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style rewrite of `instruction` (removed em-dash, replaced fragment "Need a 400 m buffer..." with a full-sentence ask, deduplicated the `connector_id` mention, referenced the file by its actual filename). Deliberate CRS omission and the "400 m" metric problem definition preserved verbatim. Re-grade on reference: 1.0 (5/5).
- `task.json`: added `analyst_notes` (description, approach, pitfalls) covering the unprompted-CRS gotcha and the empirically observed Web Mercator pitfall. Human-facing only.
- `task.json`: bumped `version` 1 → 2 (implicit v1 → explicit v2) because the instruction changed.
- `metadata.yaml > broken_solutions > measured_score`: re-verified (0.0 / 0.4 / 0.6 / 0.4); values unchanged, no edit needed.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — `inputs/_prepare.py` still reprojects to EPSG:6677 and its docstring describes a projected input, contradicting the 2026-05-17 WGS84 redesign. Carried over from the prior pass.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- broken solutions: wrong_format 0.0 / degrees_buffer 0.4 / wrong_radius 0.6 / shifted_centers 0.4 (all in declared ranges)
- pytest: pass (41 passed)


---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geometry-type-is-Polygon/MultiPolygon check migrated to new subcheck
  `geometry_types_polygonal`.
- Row-count-within-±5% check migrated to new subcheck
  `row_count_within_tolerance`.
- Subcheck count: 5 → 7.

### Verification
- Reference solution re-graded: 1.0 (7/7 subchecks).

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 as an L1 geometric-operations task: a 300-point Tokyo
`transportation.connector` layer shipped in projected EPSG:6677, with the agent
asked to draw a 400 m planar buffer per connector and export GeoParquet. The
2026-05-17 redesign (commit 6deb6e7) converted the input to WGS84, stripped all
CRS guidance from the instruction, dropped the output-CRS requirement, and
generalised the grader to reproject the submission to EPSG:6677 internally
(±2% area, IoU >= 0.95), making the task a test of unprompted CRS reasoning
for metric buffering. This matches the inventory row's "CRS out: n/a".

This is the **fifth** evaluator pass. Prior passes (2026-05-26 7dcc9c1,
2026-05-27 c0bbdbd, 2026-05-28 c067828, 2026-06-06 9cd6cf2) all returned
`calibrated`; the fourth pass applied a house-style instruction rewrite,
authored `analyst_notes`, and bumped `version` 1 -> 2. Since then, two
benchmark-wide grader refactors landed (see change log); this pass verifies
the task under the new scoring scheme.

#### Change log
(Entries through 2026-05-28 are documented in the prior review blocks above and
are unchanged; only commits since the 2026-06-06 pass are listed.)

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 9cd6cf2 | mixed (prompt-change + docs-change) | Fourth evaluator pass: house-style instruction rewrite, `analyst_notes` authored, `version` 1 -> 2, evaluator artefacts | Commit msg: "Re-evaluate geo-l1-tokyo-busstop-buffer: calibrated; house-style instruction + analyst_notes (v1->v2)" |
| 2026-06-06 | 363aed2 | grader-change | Benchmark-wide: removed `Gate("structural_correctness", ...)`; geometry-type and row-count checks migrated to subchecks `geometry_types_polygonal` and `row_count_within_tolerance` (5 -> 7 subchecks) | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" |
| 2026-06-07 | c749e57 | grader-change | Benchmark-wide: added `weight=3.0` to the five data-content subchecks (`connector_id_set_preserved`, `buffer_area_400m`, `per_id_iou_high`, `buffer_contains_source_point`, `row_count_within_tolerance`); score is now weight-summed (total weight 17) | Commit msg: "Weight data-content subchecks 3x across all categories" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38+00:00 (commit c749e57, class: grader-change).
- The last prompt/input-affecting commit is 9cd6cf2 (2026-06-06T16:46:37Z, instruction rewrite, v2). The two later commits are grader-only (aggregation semantics); they change scoring, not what the agent sees. Runs that answered the v2 prompt but were scored before the reweighting were therefore **re-graded locally with the current grader** and reported with their re-graded scores below, rather than discarded.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:25:02Z | 1.0 (re-grade 1.0) | done | current (v2 prompt; re-graded under c749e57 grader) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T15:44:02Z | 0.6471 (re-grade 0.6471) | done | current (v2 prompt; re-graded under c749e57 grader) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:56:25Z | 1.0 | done | current |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T12:22:24Z | 1.0 | done | current |

Stale runs excluded: the 22 pre-redesign run dirs (2026-05-12 through 2026-05-17T06:14Z, projected-input variant) and the 17 run dirs from run-20260517-1254Z through run-20260606-1334Z (documented in the 2026-05-26/27/28 and 2026-06-06 blocks), all of which started before the 9cd6cf2 v2 instruction landed at 2026-06-06T16:46Z and therefore answered the v1 prompt. All four post-9cd6cf2 runs carry `task_version: 2` in `run.json` (version check passes).

#### Verdict
**calibrated**

Reference output regrades 1.0 (1/1 gate, 7/7 subchecks) under the new weighted scheme. Across the four `current` v2-prompt runs (Gemma 4 26B x2, DeepSeek V4 Flash x2, spanning basic and gis_detailed prompt variants), scores are 1.0 x3 and 0.6471 x1. The 0.6471 run (run-20260607-112430Z) is the familiar Gemma Web Mercator failure: its `outputs/solve.py` reprojects to EPSG:3857 ("Reprojecting to EPSG:3857 for buffering"), so at Tokyo latitude the 400-unit buffer shrinks to ~327 ground metres; `score.json` shows the signature 0/300 polygons within ±2% (median area 330 330.3 m² vs 502 654.8 m² target) with `buffer_area_400m` and `per_id_iou_high` failing and everything else passing, giving 11/17 = 0.6471. The three passing runs picked EPSG:32654 (UTM 54N) or equivalent. The same intermittent within-family Mercator failure was observed in the 2026-05-28 and 2026-06-06 passes; the task continues to discriminate exactly along the axis it was redesigned to probe. The instruction (v2) names no CRS, projection family, algorithm, or procedural decomposition; the only quantitative hint ("400 m") is the problem definition itself.

#### 2c-CRS output-CRS / format consistency
- Reference output CRS: EPSG:6677. `expected_outputs[]` deliberately pins no CRS (`{name, format: geoparquet, geometry_type: Polygon}`) by design; README §Output states "No output CRS specified — the model chooses." All three sources agree.
- Grader (`grade.py:_to_ref_crs`) reprojects the submission and the input (for the contains-point subcheck) into EPSG:6677, the CRS the reference is already stored in. This is the allowed "transform both sides the same way" pattern, not a one-sided reprojection papering over a contract mismatch.
- All four current-run outputs are valid GeoParquet, 300 rows, columns `[connector_id, geometry]`, all-Polygon, stored in EPSG:4326 (agents buffered in a metric CRS and reprojected back), which the grader handles by design.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `tokyo_stop_catchments.geoparquet`, GeoParquet | instruction | stated |
| `connector_id` present, populated, values preserved | instruction ("keep `connector_id` on every row with the original value preserved") | stated |
| Polygon/MultiPolygon geometry | instruction ("one Polygon or MultiPolygon row per input connector") | stated |
| 400 m metric buffer (area within ±2% of pi*400², IoU >= 0.95 vs reference) | instruction states 400 m; the metric interpretation and CRS choice are the skill under test | stated / inferable |
| row count ~ 300 (±5%) | instruction ("around every connector", "per input connector") | inferable |
| output CRS | deliberately unspecified; grader accepts any CRS (reprojects internally) | not a constraint |

Factual claims verified: input filename `tokyo_connectors.geojson` exists in `inputs/`; it is EPSG:4326 with 300 Point features and a `connector_id` column; the output filename/format/column match the reference output schema. No inaccurate claim found.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads the WGS84 input, reprojects to EPSG:6677 (the canonical metric CRS for Tokyo, an optimal choice), buffers 400 m, and writes GeoParquet with exactly the `connector_id` and `geometry` columns. The only unrequested operation is a stable sort by `connector_id`, which affects row order only; the prompt does not constrain row order and no graded property depends on it. No deviation worth flagging.

#### Specific findings
- The two benchmark-wide grader refactors (363aed2 gate-2 drop, c749e57 3x reweighting) changed this task's score aggregation without a `task.json.version` bump. That is consistent with how the refactors were applied across all tasks (versioning tracks per-task content generations; the repo-wide scoring semantics are tracked by `suite_git_sha`), so it is recorded as a note, not a flag.
- Broken-solution scores re-measured under the weighted grader: `broken_wrong_format` 0.0, `broken_degrees_buffer` 0.4706, `broken_wrong_radius` 0.6471, `broken_shifted_centers` 0.4706. The recorded `measured_score` values (0.0 / 0.4 / 0.6 / 0.4) were stale; refreshed to 0.0 / 0.47 / 0.65 / 0.47 in `metadata.yaml` this pass.
- `broken_shifted_centers` now measures 0.4706, **outside** its declared `expected_score_range` [0.35, 0.45]; `broken_degrees_buffer` (0.4706 in [0.3, 0.5]) and `broken_wrong_radius` (0.6471 in [0.55, 0.65]) still fit, the latter exactly at the top edge. The ranges were calibrated for the pre-weighting equal-weight scheme; updating them is a calibration declaration outside the evaluator's unilateral list -> HR-002.
- README was stale on three points and fixed this pass (docs-change, no version bump): input path said `data/` (layout reorg renamed it `inputs/`), failure modes 6 and 7 still cited the removed "Gate 2", and the listed broken-set scores predated the reweighting.
- Stray authoring scratch files `solve.py` and `tokyo_stop_catchments.geoparquet` sit tracked at the task top level (present since at least the 2026-05-13 move). They are not referenced by `task.json`, the grader, or the harness (only `inputs[]` urls are served to agents), so nothing leaks at run time, but `solve.py` is a worked solution committed outside `reference/` and the geoparquet is a stale pre-redesign artefact. Deleting files is outside the evaluator's write authority -> HR-003.
- HR-001 (stale `inputs/_prepare.py` still reprojects to EPSG:6677 and describes a projected input, contradicting the 2026-05-17 WGS84 redesign) re-verified still present at `_prepare.py:87-90` and docstring; carried over unchanged.
- Inventory row matches the current task on category, difficulty, region, formats, geometry types, theme, OSM tag, scale, and "CRS out: n/a". Consistent.
- Coverage slugs re-validated against `coverage-vocabulary.yaml`; `coverage.yaml` content unchanged, timestamp refreshed.

<!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" -->
`inputs/_prepare.py` still calls `.to_crs("EPSG:6677")` and its docstring
describes shipping the bundled input projected, contradicting the 2026-05-17
WGS84 redesign. The committed `inputs/tokyo_connectors.geojson` is correctly
EPSG:4326, so grading is unaffected, but the helper narrative is misleading
for future maintainers. A human with `inputs/` edit authority should remove
the reprojection and fix the docstring (and bump `task.json.version` if the
bundled input is regenerated). Carried over from the 2026-05-27/28 and
2026-06-06 passes.

<!-- HUMAN-REVIEW id="HR-002" category="grader-miscalibration-suspected" severity="low" -->
The benchmark-wide 3x reweighting (c749e57) moved `broken_shifted_centers`
to 0.4706, outside its declared `expected_score_range` [0.35, 0.45], and
pushed `broken_wrong_radius` (0.6471) to the very top of its [0.55, 0.65]
range. The grader itself behaves correctly (the failing subchecks are the
right ones); only the declared calibration envelopes predate the weighting
scheme. A human should refresh the `expected_score_range` declarations in
`metadata.yaml` for the weighted scheme (suggested: shifted_centers
[0.4, 0.55], degrees_buffer [0.4, 0.55], wrong_radius [0.6, 0.7]). No
version bump needed (declarative metadata only).

<!-- HUMAN-REVIEW id="HR-003" category="reference-or-data-edit-needed" severity="low" -->
Tracked scratch files `solve.py` (a worked solution) and
`tokyo_stop_catchments.geoparquet` (a stale pre-redesign output, still in
EPSG:6677-era shape) sit at the task top level outside `reference/`. They
are never served to agents (the harness only serves `inputs[]` urls) and do
not affect grading, but they are clutter and a potential confusion source.
A human should `git rm` both; file deletion is outside the evaluator's
write authority. No version bump needed (neither file is part of the
prompt, grader, or input contract).

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` to the weighted-grader values (wrong_format 0.0, degrees_buffer 0.47, wrong_radius 0.65, shifted_centers 0.47). Re-grade on reference: 1.0. Reason: recorded values predated the 363aed2 gate-2 drop and c749e57 reweighting.
- `README.md`: fixed stale input path (`data/` -> `inputs/`), replaced removed "Gate 2" references with the `geometry_types_polygonal` / `row_count_within_tolerance` subchecks, and updated the listed broken-set scores. Reason: stale docs after the two benchmark-wide grader refactors and the 2026-05-26 layout reorg.

No `version` bump: neither edit changes the instruction, grader logic, tolerances, or inputs.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — stale `inputs/_prepare.py` (EPSG:6677 reprojection + projected-input docstring) contradicts the WGS84 redesign; carried over.
- HR-002 — grader-miscalibration-suspected — `expected_score_range` envelopes predate the 3x reweighting; `broken_shifted_centers` (0.4706) now falls outside [0.35, 0.45].
- HR-003 — reference-or-data-edit-needed — tracked scratch `solve.py` and `tokyo_stop_catchments.geoparquet` at task top level should be removed.

#### Tests run
- grader on reference: 1.0 (1/1 gate, 7/7 subchecks, weighted)
- broken solutions: wrong_format 0.0 / degrees_buffer 0.4706 / wrong_radius 0.6471 / shifted_centers 0.4706
- re-grade of current run outputs: 1.0 / 0.6471 / 1.0 / 1.0 (matches recorded scores)
- pytest: pass (41 passed)

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Summary
Per-task reasoned subcheck weights replace the blunt 05b389b / c749e57 3x
"data-content" weighting. The central skill this task probes is **correct
metric buffering in a projected CRS at the right radius**; its detectors
(`buffer_area_400m`, `per_id_iou_high`, and the placement check
`buffer_contains_source_point`) are now weighted highest, and the structural
/ cosmetic checks lowest. Grading-only change: only `weight=` values in
`grade.py` were touched (no check logic, thresholds, or gates). Resolves the
open HR-002 (the 3x reweighting had drifted `broken_shifted_centers` to
0.4706, outside its declared envelope).

### 1. Centrality analysis (which subcheck catches which failure, how central)
| Subcheck | Failure it catches | Centrality |
|---|---|---|
| `buffer_area_400m` | wrong radius / degrees-buffer / scale-wrong CRS (e.g. Web Mercator) | CENTRAL — the metric-buffering skill itself |
| `per_id_iou_high` | wrong radius / degrees / shifted centres / wrong CRS (full shape+placement match) | CENTRAL — the metric-buffering skill itself |
| `buffer_contains_source_point` | shifted centres / wrong join (placement / centring) | central placement, slightly below size+shape match |
| `connector_id_set_preserved` | dropped / renamed join key | structural (contract, not GIS skill) |
| `connector_id_populated` | empty join key | structural |
| `geometry_types_polygonal` | emitted Points instead of buffering | cosmetic / structural |
| `row_count_within_tolerance` | filtered out connectors | structural |

### 2. Weight changes (subcheck: old -> new)
| Subcheck | Old | New |
|---|---|---|
| `buffer_area_400m` | 3.0 | **4.0** |
| `per_id_iou_high` | 3.0 | **4.0** |
| `buffer_contains_source_point` | 3.0 | 3.0 (unchanged) |
| `connector_id_set_preserved` | 3.0 | **2.0** |
| `row_count_within_tolerance` | 3.0 | **1.0** |
| `connector_id_populated` | 1.0 | 1.0 (unchanged) |
| `geometry_types_polygonal` | 1.0 | 1.0 (unchanged) |

Total weight 17 -> 16. Rationale: a meaningful/central mistake (wrong size,
wrong shape, wrong placement of the buffer) must drop the score hard, so the
three buffer-geometry detectors carry 4+4+3 = 11 of 16 weight (69%).
Join-key integrity (`connector_id_set_preserved`) is a real contract but not
the GIS skill under test, so it sits at 2.0; the purely structural / cosmetic
checks (populated, geometry-type, row-count) stay at 1.0 each. The 3x
content weighting had over-weighted `connector_id_set_preserved` and
`row_count_within_tolerance` (structural) to the same level as the central
geometric checks, flattening severity.

### 3. Broken-score before -> after (and ordering)
| Broken | Before (c749e57 3x) | After | Severity note |
|---|---|---|---|
| `broken_wrong_format` | 0.0 | 0.0 | catastrophic — wrong format, hard-gate fail |
| `broken_degrees_buffer` | 0.4706 | 0.3125 | severe — buffered in WGS84 degrees; size + placement both wrong |
| `broken_shifted_centers` | 0.4706 | 0.3125 | severe — 1000 m shift + 200 m radius; size + placement both wrong |
| `broken_wrong_radius` | 0.6471 | 0.5000 | moderate — projected CRS + centring correct, only radius half-size |

Ordering is now sensible and monotone by severity:
0.0 (catastrophic) < 0.3125 (degrees / shifted, central skill wrecked) <
0.5 (wrong_radius, central skill mostly intact) < 1.0 (reference). The
degrees/shifted tie is unavoidable and defensible — both fail the identical
set of subchecks (area, IoU, contains-point) and both are severe failures of
the central skill; the grader has no finer signal to separate them, and
neither should outscore the radius-only error. No disjoint-failure inversion:
up-weighting the geometry detectors pushes the two severe brokens *down*
relative to `wrong_radius` (which keeps its w=3 contains-point point),
preserving the intended ordering.

### 4. Prior-run re-grade (current v2-prompt runs)
| Run | Adapter | Old score | New score |
|---|---|---|---|
| run-20260606-1733Z | gemma4-26b-detailed | 1.0 | 1.0 |
| run-20260607-112430Z | gemma4-26b-detailed | 0.6471 | 0.5 |
| run-20260608-074701Z | deepseek-v4-flash-detailed | 1.0 | 1.0 |
| run-20260609-084636Z | deepseek-v4-flash-basic | 1.0 | 1.0 |

The three full-pass runs are unchanged at 1.0. The one partial run
(run-20260607-112430Z, Gemma's Web Mercator buffer: fails area + IoU, passes
contains-point and all structural) moves 0.6471 -> 0.5, landing exactly on
the `broken_wrong_radius` class it behaviourally matches (correct centring,
wrong effective radius). That is the intended re-bucketing, not a regression.

### 5. Reasoning
The 05b389b / c749e57 commit applied weight=3.0 to all five "data-content"
subchecks one-size-fits-all, which inflated two structural checks
(`connector_id_set_preserved`, `row_count_within_tolerance`) to the weight of
the actual GIS skill and flattened the severity gradient (degrees-buffer and
wrong-radius came out only 0.18 apart, and shifted_centers drifted outside
its envelope). The reasoned scheme puts 69% of the weight on the three
buffer-geometry detectors so a model that gets the buffering wrong drops
hard, while a model that merely drops the join key or filters a few rows
(structural slips) loses comparatively little. Reference holds at 1.0.

### Notes (not changed)
- Thresholds and gates are untouched. The `_to_ref_crs` null-CRS-assumes-4326
  leniency (`grade.py:61-67`) is coherent (a degree buffer still fails the area
  check after reprojection) and was not modified.
- HR-001 (stale `inputs/_prepare.py`) and HR-003 (tracked scratch `solve.py`
  / stale `tokyo_stop_catchments.geoparquet`) remain open; both require edits
  outside the grader's authority and are unaffected by this reweighting.

### Changes applied this run
- `grade.py`: subcheck `weight=` values only (table in §2). No logic change.
- `metadata.yaml`: refreshed `broken_solutions` `measured_score` (0.0 / 0.3125
  / 0.5 / 0.3125) and `expected_score_range` envelopes to the reasoned-weight
  scheme; updated weight-arithmetic prose in the descriptions.
- `README.md`: refreshed stale broken-score fractions (0.31 / 0.50 / 0.31).
- `audit/status.json`: dropped HR-002; recorded edits.

### Tests run
- grader on reference: 1.0 (1/1 gate, 7/7 subchecks, weighted)
- broken solutions: wrong_format 0.0 / degrees_buffer 0.3125 / wrong_radius 0.5 / shifted_centers 0.3125
- re-grade of current run outputs: 1.0 / 0.5 / 1.0 / 1.0
- pytest: not-run (orchestrator runs the suite)
