# Implementation notes — spa-l1-capetown-hospital-nn

## Status
completed

## Summary
L1 spatial analysis task, redesigned to test **unprompted CRS reasoning for
metric distance computation**.  Input data converted from EPSG:32734 to WGS84.
Instruction no longer mentions any CRS or says "in the same CRS as the input
data".  The model must independently recognise that distances on WGS84
coordinates are in degrees, not metres, and choose an appropriate projected CRS.

## Changes from previous version (2026-05-08-a → 2026-05-17-a)
- Input data: both addresses.parquet and hospitals.parquet converted from
  EPSG:32734 to EPSG:4326 (WGS84)
- Instruction: removed "in the same CRS as the input data"
- Output: removed CRS requirement from expected_outputs
- Grader: removed CRS gate check; distance tolerance widened to 50 m (from
  1 m) to accept any reasonable projected CRS for Cape Town
- Broken solutions: added `broken_degrees_distance` (computed NN in WGS84)
- Reference: regenerated with explicit reproject to EPSG:32734

## Verification results
- Reference grader score: 1.00 (5/5 subchecks)
- Broken-solution scores:
  - wrong_format: 0.00 (expected [0.0, 0.0])
  - degrees_distance: 0.60 (3/5) (expected [0.5, 0.7])
  - wrong_hospital: 0.60 (3/5) (expected [0.5, 0.7])
  - distance_in_km: 0.80 (4/5) (expected [0.75, 0.85])

## Failure-mode coverage
- Computed NN in WGS84 degrees (primary target): broken_degrees_distance
- Wrong hospital assignment: broken_wrong_hospital
- Distance in km not m: broken_distance_in_km
- Wrong output format: broken_wrong_format
- Omitted/stringified distance_m: principled — Gate 1 + distance_m_numeric_finite
- Dropped/duplicated rows: principled — Gate 2 + address_set_preserved
- Computed NN in wrong CRS: principled — distance_m_matches_reference

## Open issues
(none)

## Library extensions
(none)

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the inventory's `spa-l1-capetown-hospital-nn` row: an L1 spatial-analysis exercise that gives the agent two small bundled GeoParquet point layers (~120 residential addresses, ~37 hospital points) for Cape Town and asks it to produce one GPKG row per address with the nearest hospital's name and the straight-line distance in metres. The original 2026-05-08 authoring placed both inputs in EPSG:32734 (UTM 34S) so the task was purely an exercise in correctly calling sjoin-nearest and emitting metric distance. The 2026-05-17 redesign converted the inputs to WGS84 and stripped every CRS hint from the instruction, retargeting the task to probe **unprompted CRS reasoning for metric distance** — the agent must independently realise that WGS84 degrees are not metres and pick its own projected CRS.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e2f70fcf | initial-authoring | Task created with EPSG:32734 inputs, EPSG:32734 GPKG output, 3 broken solutions (wrong_format, wrong_hospital, distance_in_km), instruction names EPSG:32734 | (initial) |
| 2026-05-13 | 12c9fb09 | prompt-change | Folded the "Output schema:" bullet list into prose while keeping CRS code, geometry, columns, units | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | 1bc112e1 | prompt-change | Replaced "EPSG:32734" in instruction with "in the same CRS as the input data" — stripped deducible CRS code | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 6deb6e77 | mixed (data + prompt + grader + reference + tests) | Inputs reprojected EPSG:32734 → EPSG:4326; instruction dropped "same CRS as input"; grader removed CRS gate, widened distance tolerance 1 m → 50 m; reference now reprojects to EPSG:32734 internally; added `broken_degrees_distance` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-17 | 7f31f98d | prompt-change | Replaced "in the same CRS as the input data, retaining the input address geometry — one feature per input address — and the three columns" with "retaining the input address geometry — one feature per input address — with columns" (cleanup leftover phrasing) | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change (path moves only) | Folder layout reorg: data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, image* → assets/; grader and generator paths updated | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit 7f31f98d, class: prompt-change). The 2026-05-26 reorg only renamed paths inside the task dir and updated path constants in grade.py and reference/solution/generate.py; it does not alter the answer key or instruction semantics. Treated as docs-change for cutoff purposes.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T14:11:29Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:53:59Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:11:38Z | 0.8 | done | current |

Stale runs (pre-cutoff 2026-05-17T12:49:06Z) — many runs from 2026-05-12 through 2026-05-17 morning exist but predate the most recent prompt-change and are not used as evidence here.

#### Verdict
**calibrated**

Three current runs across three independent agent families show a sensible score spread (1.0 / 1.0 / 0.8). Claude Opus and DeepSeek V4 Flash both correctly recognised WGS84 input, chose a UTM (or equivalent local conformal) CRS, and matched all 120 reference distances within 50 m. Gemma 4 26B chose EPSG:3857 (Web Mercator) — a documented anti-pattern at high latitudes that inflates distances away from the equator — and so its `distance_m_matches_reference` subcheck failed on 116/120 rows while it still got the nearest hospital right on 119/120. That is precisely the failure mode the redesign was built to detect, and the grader caught it cleanly. The 50 m distance tolerance is wide enough to absorb the EPSG:32734 ↔ EPSG:32735 ↔ local conformal choice for Cape Town (distances 50 m – 6000 m), but narrow enough to reject Web-Mercator drift; this matches the rationale in `metadata.yaml`.

#### Specific findings
- Instruction at `task.json:14` reads clean: no CRS code, no library/function name, no "you must reproject" hint. The only redundant-but-acceptable element is the second sentence restating the output filename and column list — that matches the redundant-output-schema convention from `author-context.md`.
- Grader at `grade.py:33-216`: gates are sensible (file exists, parses as GPKG, has columns; geometry Point only; row count ±5%). Subchecks cover name populated, distance numeric/finite/non-negative, distance vs reference ≤50 m for ≥95%, name match for ≥95%, address-set Jaccard ≥0.95. The 50 m tolerance is documented inline and matches `metadata.yaml`.
- Broken-solution measured scores in `metadata.yaml` (0.0 / 0.6 / 0.6 / 0.8) align with the README's failure-mode listing; not re-measured this run because no grader or reference change occurred.
- Inventory row in `authoring/inventory.md:674-697` matches the current task on every axis (region cape-town, bundled, NN, geoparquet→gpkg, point, amenity=hospital, small). No inventory mismatch.
- Reference at `reference/solution/generate.py:36-37` reprojects to EPSG:32734 before sjoin-nearest — correct for Cape Town.

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated, no gifts in the instruction, no broken tolerances)

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- pytest: pass (35 passed in 0.56s)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the inventory's `spa-l1-capetown-hospital-nn` row (`authoring/inventory.md:674-697`): an L1 spatial-analysis exercise that hands the agent two small bundled GeoParquet point layers (120 residential pickup addresses, 37 hospital points) for Cape Town and asks for one GPKG row per address carrying the nearest hospital's name and the straight-line distance in metres, with the input `address_id` preserved as a join key. The original 2026-05-08 authoring placed both inputs in EPSG:32734 (UTM 34S), so the task only exercised correctly calling sjoin-nearest and emitting metric distance. The 2026-05-17 redesign converted the inputs to WGS84 and stripped every CRS hint from the instruction, re-targeting the task to probe **unprompted CRS reasoning for metric distance** — the agent must independently realise that distances on WGS84 degrees are not metres and pick its own projected CRS.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e2f70fcf | initial-authoring | Task created: EPSG:32734 inputs, EPSG:32734 GPKG output, 3 broken solutions (wrong_format, wrong_hospital, distance_in_km); instruction named EPSG:32734 | (initial) |
| 2026-05-13 | 12c9fb09 | prompt-change | Folded the "Output schema:" bullet list into prose while keeping CRS code, geometry, columns, units | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | 1bc112e1 | prompt-change | Replaced "EPSG:32734" in instruction with "in the same CRS as the input data" — stripped the deducible EPSG code | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 6deb6e77 | mixed (data + prompt + grader + reference + tests) | Inputs reprojected EPSG:32734 → EPSG:4326; instruction dropped "same CRS as input"; grader removed CRS gate and widened distance tolerance 1 m → 50 m; reference now reprojects to EPSG:32734 internally; added `broken_degrees_distance` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-17 | 7f31f98d | prompt-change | Removed leftover "in the same CRS as the input data, retaining …" phrasing, leaving "retaining the input address geometry … with columns" | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change (path moves only) | Folder reorg: data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image*→assets/; path constants in grade.py and generate.py updated. addresses.parquet/hospitals.parquet are pure renames (Bin, no content change) | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 0730b56d | docs-change (evaluator artefacts) | First task-evaluator pass: wrote coverage.yaml, prior evaluator-review block, status.json. Verdict calibrated, 0 flags | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 0 flags" |

This run's reconstruction agrees with the prior evaluator block above on every commit and class. The `git log --follow` directory form omits the initial-authoring commit `e2f70fcf` because of the 2026-05-08 repo restructure moves; it is recovered by grepping commits whose message mentions the slug, as the prior evaluator also did.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit 7f31f98d, class: prompt-change). The 2026-05-26 reorg (29a9ae32) only renamed paths inside the task dir and updated path constants in grade.py and reference/solution/generate.py — the two input parquets moved with no byte change — so it does not alter the answer key or instruction semantics and is treated as docs-change for cutoff purposes. The 0730b56d evaluator commit touched only audit artefacts.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (opus) | 2026-05-17T14:11:29Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:53:59Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:11:38Z | 0.8 | done | current |

Stale runs (pre-cutoff 2026-05-17T12:49:06Z) — 22 further runs from 2026-05-12 through the morning of 2026-05-17 exist (mix of haiku/sonnet/opus/deepseek/gemma/hy3, scores 0.0–1.0, plus three cancelled gemma runs and one ConnectError failure). They predate the most recent prompt-change and the WGS84 redesign, so they are not used as evidence here.

#### Verdict
**calibrated**

Three current runs across three independent agent families show a sensible spread (1.0 / 1.0 / 0.8) that exercises exactly the skill the redesign targets. Claude Opus (run-20260517-1254Z) and DeepSeek V4 Flash (run-20260517-1424Z) both recognised the WGS84 input, computed distance in a metric CRS, and matched all 120 reference distances within 50 m and all 120 hospital names — 5/5 subchecks. Gemma 4 26B (run-20260526-0748Z) got the nearest hospital right on 119/120 but failed `distance_m_matches_reference` (only 4/120 within 50 m), scoring 0.8. Inspecting its output: distances span 57–7168 m versus the reference 47–5957 m; 7168/5957 ≈ 1.20 ≈ 1/cos(34°S), the unmistakable signature of computing distance in Web Mercator (EPSG:3857), the documented high-latitude anti-pattern. The 50 m tolerance is wide enough to absorb the legitimate UTM-34S/UTM-35S/local-conformal choice for Cape Town (distances 47–6000 m) yet narrow enough to reject Web-Mercator inflation — matching the `metadata.yaml` rationale. Verdict is not `too-strict`, so per the prompt no transcript was read.

#### Specific findings
- Instruction (`task.json:14`) is clean: no EPSG code, no library/function name, no "you must reproject" nudge. The closing sentence restating filename/format/columns is the intended redundant-output-schema safety net (`author-context.md`). No gift to strip.
- Grader (`grade.py:52-217`) compares `distance_m` as a CRS-independent scalar (metres) keyed by `address_id` and never reprojects one side to match the other — there is no one-sided-reprojection hazard. Gates (file/GPKG/columns; Point-only; row count ±5%) and the five subchecks are sound and match `metadata.yaml`.
- Output-CRS/contract consistency: `expected_outputs[]` deliberately omits a CRS (model chooses); README states "No output CRS specified — the model chooses"; reference output is EPSG:32734; all three current submissions stored geometry in EPSG:4326 and still scored on the scalar `distance_m`. Consistent — no CRS contract mismatch.
- Inventory row (`authoring/inventory.md:674-697`) matches the current task on every axis (cape-town, bundled, nearest-neighbour, geoparquet→gpkg, point, amenity=hospital, small, no quality issues). No inventory mismatch.
- Broken-solution measured scores in `metadata.yaml` (0.0 / 0.6 / 0.6 / 0.8) are unchanged; no grader/reference edit occurred this run, so they were not re-measured.
- Stale-but-true defect: `inputs/_prepare.py` (docstring + the `fetch_hospitals`/`fetch_addresses` `.to_crs("EPSG:32734")` calls and the line "The output GPKG must stay in EPSG:32734") still describe the pre-redesign EPSG:32734 input regime, but the committed `addresses.parquet`/`hospitals.parquet` are correctly EPSG:4326 (verified by direct read). The helper is authoring-time only and is not consumed by the grader or the agent, so this does not affect scoring — but the file lives under `inputs/`, which the evaluator may not edit. Flagged HR-001 (`reference-or-data-edit-needed`, low). <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" --> `inputs/_prepare.py` still documents and reprojects to EPSG:32734, contradicting the WGS84 inputs the 2026-05-17 redesign committed; a human should refresh the helper's docstring and drop the trailing `.to_crs("EPSG:32734")` calls so re-running it reproduces the WGS84 inputs. No grading impact.

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; no gifts in the instruction, no broken tolerances, no stale README CRS claim)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — `inputs/_prepare.py` docstring and `.to_crs("EPSG:32734")` calls are stale vs the committed WGS84 inputs; refresh for reproducibility. No grading impact.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- pytest: pass (35 passed in 0.87s)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the inventory's `spa-l1-capetown-hospital-nn` row (`authoring/inventory.md:674-697`): an L1 spatial-analysis exercise that hands the agent two small bundled GeoParquet point layers (120 residential pickup addresses + 37 hospital points) for Cape Town and asks for one GPKG row per address carrying the nearest hospital's name and the straight-line distance in metres, with the input `address_id` preserved as a join key. The original 2026-05-08 authoring placed both inputs in EPSG:32734 (UTM 34S), so the task only exercised correctly calling sjoin-nearest and emitting metric distance. The 2026-05-17 redesign converted the inputs to WGS84 and stripped every CRS hint from the instruction, retargeting the task to probe **unprompted CRS reasoning for metric distance** — the agent must independently realise that distances on WGS84 degrees are not metres and pick its own projected CRS.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e2f70fcf | initial-authoring | Task created: EPSG:32734 inputs, EPSG:32734 GPKG output, 3 broken solutions (wrong_format, wrong_hospital, distance_in_km); instruction named EPSG:32734 | (initial) |
| 2026-05-13 | 12c9fb09 | prompt-change | Folded the "Output schema:" bullet list into prose while keeping CRS code, geometry, columns, units | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | 1bc112e1 | prompt-change | Replaced "EPSG:32734" in instruction with "in the same CRS as the input data" — stripped the deducible EPSG code | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 6deb6e77 | mixed (data + prompt + grader + reference + tests) | Inputs reprojected EPSG:32734 → EPSG:4326; instruction dropped "same CRS as input"; grader removed CRS gate and widened distance tolerance 1 m → 50 m; reference now reprojects to EPSG:32734 internally; added `broken_degrees_distance` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-17 | 7f31f98d | prompt-change | Removed leftover "in the same CRS as the input data, retaining …" phrasing, leaving "retaining the input address geometry … with columns" | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change (path moves only) | Folder reorg: data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image*→assets/; path constants in grade.py and generate.py updated. addresses.parquet/hospitals.parquet are pure renames (Bin, no content change) | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 0730b56d | docs-change (evaluator artefacts) | First task-evaluator pass: wrote coverage.yaml, prior evaluator-review block, status.json. Verdict calibrated, 0 flags | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 0 flags" |
| 2026-05-27 | cddc720f | docs-change (evaluator artefacts) | Second task-evaluator pass: appended evaluator-review block, refreshed status.json. Verdict calibrated, 1 flag (HR-001 stale `inputs/_prepare.py` docstring/`.to_crs("EPSG:32734")` calls) | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 1 flag" |
| 2026-05-28 | 622342be | docs-change (metadata cleanup) | Repo-wide: dropped the unused `prompt_version: 2026-05-17-a` line from `metadata.yaml`; introduced an integer `task.json.version` field schema but did not stamp this task. Neither change touches the agent-visible prompt, grader logic, inputs, or expected_outputs | Commit msg: "Add task content versioning; drop unused prompt_version" |

This reconstruction agrees with the prior evaluator block on every pre-existing commit and class. The `git log --follow` directory form still omits initial-authoring commit `e2f70fcf` (2026-05-08 repo restructure moves); it is recovered by grepping commits whose message mentions the slug, matching the prior evaluator's approach.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit 7f31f98d, class: prompt-change). The 2026-05-26 reorg (29a9ae32) only renamed paths inside the task dir and updated path constants; the parquet inputs moved with no byte change; treated as docs-change. The 2026-05-27 evaluator commit (cddc720f) touched only audit artefacts. The 2026-05-28 commit (622342be) only deleted the unused `prompt_version` line from `metadata.yaml` for this task — no prompt, grader, tolerances, or input contract change — so it does not advance the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T14:11:29Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:53:59Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:11:38Z | 0.8 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T23:01:43Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:59:02Z | 0.8 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T03:05:24Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:10:39Z | 1.0 | done | current |

Stale runs (pre-cutoff 2026-05-17T12:49:06Z) — 22 further runs from 2026-05-12 through the morning of 2026-05-17 exist (mix of haiku/sonnet/opus/deepseek/gemma/hy3, scores 0.0–1.0, plus three cancelled gemma runs and one ConnectError failure). They predate the WGS84 redesign and are not used as evidence here.

#### Verdict
**calibrated**

Seven current runs across three independent agent families now span a meaningful score range and demonstrate that the task discriminates well. Claude Opus (4-6 and 4-7) and DeepSeek V4 Flash consistently match all 120 reference distances within 50 m and all 120 hospital names → 5/5 subchecks → 1.0. Gemma 4 26B is non-deterministic on the CRS-choice step: on 2026-05-26 and 2026-05-27 it picked EPSG:3857 (Web Mercator) — the documented high-latitude anti-pattern at 34°S — and its `distance_m_matches_reference` failed (4/120 within 50 m; max distance 7167 m vs reference 5957 m, ratio ≈ 1/cos(34°S)), so 0.8; on 2026-05-28 it picked a metric CRS and scored 1.0 (max distance exactly 5956.7 m, matching reference). That same agent toggling between the two outcomes is the cleanest possible evidence that the 50 m tolerance is calibrated correctly: it absorbs the legitimate UTM-34S/UTM-35S/local-conformal choice for Cape Town yet rejects Web-Mercator drift. Verdict is not `too-strict`, so per the prompt no transcript was read.

#### Specific findings
- Instruction (`task.json:14`) reads clean: no EPSG code, no library/function name, no "you must reproject" nudge. The closing sentence restating filename/format/columns is the intended redundant-output-schema safety net (`task-design-prompt.md:78`). Output is GPKG, not GeoJSON, so the "strip any CRS mention when the output is GeoJSON" rule does not apply. No gift to strip.
- Grader (`grade.py:52-217`) compares `distance_m` as a CRS-independent scalar (metres) keyed by `address_id` and never reprojects one side to match the other — there is no one-sided-reprojection hazard. Gates (file/GPKG/columns; Point-only; row count ±5%) and the five subchecks remain sound and match `metadata.yaml`.
- Output-CRS / contract consistency (2c-CRS): `expected_outputs[]` deliberately omits a CRS (model chooses); README states "No output CRS specified — the model chooses"; reference output is EPSG:32734; current submissions store geometry in EPSG:4326 or EPSG:3857; grading runs on the scalar `distance_m`, so the CRS of the submission file does not enter the score computation. Consistent — no CRS contract mismatch.
- Inventory row (`authoring/inventory.md:674-697`) still matches every axis (cape-town, bundled, nearest-neighbour, geoparquet→gpkg, point, amenity=hospital, small, no quality issues). No inventory mismatch.
- Broken-solution measured scores in `metadata.yaml` (0.0 / 0.6 / 0.6 / 0.8) are unchanged; no grader/reference edit occurred this run, so they were not re-measured.
- The 2026-05-28 commit's removal of `prompt_version: 2026-05-17-a` from `metadata.yaml` is a repo-wide cleanup; it does not affect grading and does not warrant a `task.json.version` bump (the field is not yet stamped on this task — it is implicitly v1 per the new convention).
- HR-001 from the prior 2026-05-27 review (stale `inputs/_prepare.py` docstring + `.to_crs("EPSG:32734")` calls vs the committed WGS84 inputs) is still open. The file is authoring-time only, has no grading impact, and `inputs/` is off-limits for the evaluator. Re-raised here as HR-001 so the orchestrator continues to see it.
  <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" --> `inputs/_prepare.py` still documents and reprojects to EPSG:32734, contradicting the WGS84 inputs the 2026-05-17 redesign committed; a human should refresh the helper's docstring and drop the trailing `.to_crs("EPSG:32734")` calls so re-running it reproduces the WGS84 inputs. No grading impact. (Re-raised verbatim from the 2026-05-27 evaluator block.)

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; no gifts in the instruction, no broken tolerances, no stale README/CRS claim, no `task.json.version` bump required since no prompt/grader/input edit was made)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — `inputs/_prepare.py` docstring and `.to_crs("EPSG:32734")` calls are stale vs the committed WGS84 inputs; refresh helper for reproducibility. No grading impact.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- pytest: pass (41 passed in 0.47s)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the inventory's `spa-l1-capetown-hospital-nn` row (`authoring/inventory.md:674-697`): an L1 spatial-analysis exercise that hands the agent two small bundled GeoParquet point layers (120 residential pickup addresses + 37 hospital points) for Cape Town and asks for one GPKG row per address carrying the nearest hospital's name and the straight-line distance in metres, with the input `address_id` preserved as a join key. The 2026-05-17 redesign converted both inputs to WGS84 and stripped every CRS hint from the instruction, retargeting the task to probe **unprompted CRS reasoning for metric distance** — the agent must independently realise that distances on WGS84 degrees are not metres and pick its own projected CRS.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e2f70fcf | initial-authoring | Task created: EPSG:32734 inputs, EPSG:32734 GPKG output, 3 broken solutions (wrong_format, wrong_hospital, distance_in_km); instruction named EPSG:32734 | (initial) |
| 2026-05-13 | 12c9fb09 | prompt-change | Folded the "Output schema:" bullet list into prose while keeping CRS code, geometry, columns, units | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | 1bc112e1 | prompt-change | Replaced "EPSG:32734" in instruction with "in the same CRS as the input data" — stripped the deducible EPSG code | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 6deb6e77 | mixed (data + prompt + grader + reference + tests) | Inputs reprojected EPSG:32734 → EPSG:4326; instruction dropped "same CRS as input"; grader removed CRS gate and widened distance tolerance 1 m → 50 m; reference now reprojects to EPSG:32734 internally; added `broken_degrees_distance` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-17 | 7f31f98d | prompt-change | Removed leftover "in the same CRS as the input data, retaining …" phrasing, leaving "retaining the input address geometry … with columns" | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change (path moves only) | Folder reorg: data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES.md→audit/AUTHORING_HISTORY.md, image*→assets/; path constants in grade.py and generate.py updated. Parquets are pure renames (no content change) | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 0730b56d | docs-change (evaluator artefacts) | First task-evaluator pass: wrote coverage.yaml, prior evaluator-review block, status.json. Verdict calibrated, 0 flags | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 0 flags" |
| 2026-05-27 | cddc720f | docs-change (evaluator artefacts) | Second task-evaluator pass: appended evaluator-review block, refreshed status.json. Verdict calibrated, 1 flag (HR-001 stale `inputs/_prepare.py`) | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 1 flag" |
| 2026-05-28 | 622342be | docs-change (metadata cleanup) | Repo-wide: dropped the unused `prompt_version: 2026-05-17-a` line from `metadata.yaml`; introduced an integer `task.json.version` field schema but did not stamp this task | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 356e6c45 | docs-change (evaluator artefacts) | Third task-evaluator pass: appended evaluator-review block, refreshed status.json. Verdict calibrated, 1 flag (HR-001 re-raised verbatim) | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 1 flag" |

This reconstruction agrees with the prior evaluator blocks on every pre-existing commit and class. No commits since 2026-05-28 have touched files under `benchmark/tasks/spa-l1-capetown-hospital-nn/`. Two cross-cutting commits in the interval (05aabd64 "Soften CRS hard-fail to subcheck deductions across 21 graders" and bf9ccce9 "Accept OGC:CRS84 as EPSG:4326 in grader CRS gates") did **not** modify this task's `grade.py` — `git show <sha> -- benchmark/tasks/spa-l1-capetown-hospital-nn/` returns empty for both — so they do not advance the design-affecting cutoff for this task.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit 7f31f98d, class: prompt-change). Unchanged from the previous review. The 2026-05-28 commits (622342be metadata cleanup, 356e6c45 evaluator artefacts) and all later cross-cutting commits left this task's prompt, grader, inputs, and reference untouched.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T14:11:29Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:53:59Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:11:38Z | 0.8 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T23:01:43Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T00:59:02Z | 0.8 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T03:05:24Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:10:39Z | 1.0 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:51:33Z | 0.8 | done | current |
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T22:06:47Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:19:45Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-29T00:48:12Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:05:59Z | 0.8 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T18:05:18Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:26:36Z | 0.0 | done | current (model-side: no output file) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:46:51Z | 0.8 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | n/a | cancelled | current (cancelled) |

Stale runs (pre-cutoff 2026-05-17T12:49:06Z) — 22 further runs from 2026-05-12 through the morning of 2026-05-17 exist and are not used as evidence.

#### Verdict
**calibrated**

Sixteen current runs across four agent families (Claude Opus 4-6 and 4-7, DeepSeek V4 Flash, DeepSeek V4 Pro, Gemma 4 26B with both prompt variants) preserve the discriminating spread the previous review documented. Opus and DeepSeek consistently score 1.0 (5/5). Gemma 4 26B continues to toggle between Web-Mercator (score 0.8: 119/120 hospital names right, 4/120 distances within 50 m — the EPSG:3857 ≈ 1/cos(34°S) signature at Cape Town's latitude) and a metric CRS (score 1.0). The new `gis_detailed` prompt variant adds two more 0.8 runs from Gemma and one 0.0 run where the model never wrote `nearest_hospital.gpkg` at all — a model-side failure, explicitly excluded as task-calibration evidence per the prompt. The same Gemma model flipping between 0.8 and 1.0 on the identical prompt is still the cleanest possible evidence that the 50 m tolerance discriminates correctly. Verdict is not `too-strict`, so per the prompt no transcript was read.

#### Specific findings
- Instruction (`task.json:14`) carries two em-dashes ("EMS coverage planning — for every pickup address…" and "retaining the input address geometry — one feature per input address — with columns…"), which the house-style rules forbid. Rewriting unilaterally under "Rewrite the instruction for house style"; bump `version` `1 → 2`. The rewrite preserves the persona ("I am putting together EMS coverage planning for the Western Cape"), the named context, every column and unit, and the deliberate CRS omission.
- README at `README.md:33,35,41` still references `data/addresses.parquet`, `data/hospitals.parquet`, `outputs/nearest_hospital.gpkg` — paths that pre-date the 2026-05-26 folder reorg. The actual layout is `inputs/<…>.parquet` and the canonical output filename is `nearest_hospital.gpkg`. Fixing unilaterally as a docs-change (no version bump needed).
- `task.json` is missing `analyst_notes`. Authoring under Step 4's "Author or refresh `analyst_notes`" rule. Schema: `description` (one paragraph on the unprompted-CRS gotcha), `approach` (five high-level steps in imperative voice with no library names), `pitfalls` (five sentences, starting with the WGS-degrees and Web-Mercator failure modes, then identifier and format pitfalls). `analyst_notes` is human-facing only, so no version bump on its own.
- Grader (`grade.py:52-217`) compares `distance_m` as a CRS-independent scalar keyed by `address_id` and never reprojects one side to match the other. The 05aabd64 "Soften CRS hard-fail" sweep did **not** touch this task because the grader has no CRS gate to soften: outputs are deliberately not pinned to a CRS. No work to do here.
- Output-CRS / contract consistency (2c-CRS): `expected_outputs[]` deliberately omits a CRS (model chooses); README states "No output CRS specified — the model chooses"; reference output is EPSG:32734; current submissions store geometry in EPSG:4326 / EPSG:3857 / various UTM. Grading runs on the scalar `distance_m`, so the CRS of the submission file does not enter the score computation. Still consistent.
- Inventory row (`authoring/inventory.md:674-697`) still matches every axis (cape-town, bundled, nearest-neighbour, geoparquet→gpkg, point, amenity=hospital, small, no quality issues). No inventory mismatch.
- Broken-solution measured scores in `metadata.yaml` (0.0 / 0.6 / 0.6 / 0.8) are unchanged; the grader was not modified this run, so they were not re-measured.
- HR-001 from the prior evaluator reviews (stale `inputs/_prepare.py` docstring + `.to_crs("EPSG:32734")` calls vs the committed WGS84 inputs) is still open. The file is authoring-time only, has no grading impact, and `inputs/` is off-limits for the evaluator. Re-raised here as HR-001 so the orchestrator continues to see it.
  <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" --> `inputs/_prepare.py` still documents and reprojects to EPSG:32734, contradicting the WGS84 inputs the 2026-05-17 redesign committed; a human should refresh the helper's docstring and drop the trailing `.to_crs("EPSG:32734")` calls so re-running it reproduces the WGS84 inputs. No grading impact. (Re-raised verbatim from prior evaluator blocks.)

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style rewrite of `instruction` (removed both em-dashes, opened with purpose-then-ask, referenced files by `.parquet` filenames). Re-grade on reference: 1.0 (5/5 subchecks, 2/2 gates). Reason: house style forbids em-dashes and "Open with the purpose, then the ask"; preserved persona, columns, units, and deliberate CRS omission.
- `task.json`: added `version: 2` (was implicitly v1). Reason: instruction edit requires a version bump per the bump-required list.
- `task.json`: authored `analyst_notes` block (description + 5-step approach + 5 pitfalls). Reason: field was missing; analyst_notes is human-facing and does not require its own version bump.
- `README.md`: fixed stale `data/…parquet` and `outputs/nearest_hospital.gpkg` paths to match the 2026-05-26 folder reorg. Reason: docs-change, no version bump required.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — `inputs/_prepare.py` docstring and `.to_crs("EPSG:32734")` calls are stale vs the committed WGS84 inputs; refresh helper for reproducibility. No grading impact.

#### Tests run
- grader on reference: 1.0 (5/5 subchecks, 2/2 gates)
- pytest: pass (41 passed in 0.59s)

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geometry-type-is-Point check migrated to a new `geometry_types_point_only` subcheck (was Gate-2 component).
- Row-count ±5% check deleted: already covered by the stricter `address_set_preserved` Jaccard ≥0.95 subcheck.
- Subchecks now total 6 (was 5).

### Verification
- Reference solution re-graded: 1.0 (6/6 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the inventory's `spa-l1-capetown-hospital-nn` row (`authoring/inventory.md:674-697`): an L1 spatial-analysis exercise that hands the agent two small bundled WGS84 GeoParquet point layers (120 residential pickup addresses + 37 hospital points) for Cape Town and asks for one GPKG row per address carrying the nearest hospital's name and the straight-line distance in metres, with the input `address_id` preserved as a join key. The 2026-05-17 redesign converted both inputs to WGS84 and stripped every CRS hint from the instruction, retargeting the task to probe unprompted CRS reasoning for metric distance: the agent must independently realise that distances on WGS84 degrees are not metres and pick its own projected CRS.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e2f70fcf | initial-authoring | Task created: EPSG:32734 inputs, EPSG:32734 GPKG output, 3 broken solutions; instruction named EPSG:32734 | (initial) |
| 2026-05-13 | 12c9fb09 | prompt-change | Folded the "Output schema:" bullet list into prose | Commit msg: "Merge output schema blocks into prose for 6 more task instructions" |
| 2026-05-14 | 1bc112e1 | prompt-change | Replaced "EPSG:32734" in instruction with "in the same CRS as the input data" | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 6deb6e77 | mixed (data + prompt + grader + reference + tests) | Inputs reprojected to EPSG:4326; instruction dropped "same CRS as input"; grader removed CRS gate, widened distance tolerance 1 m -> 50 m; reference reprojects to EPSG:32734 internally; added `broken_degrees_distance` | Commit msg: "Redesign buffer and NN tasks to test unprompted CRS reasoning" |
| 2026-05-17 | 7f31f98d | prompt-change | Removed leftover "in the same CRS as the input data" phrasing | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae32 | docs-change (path moves only) | Folder reorg; parquets byte-identical | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 0730b56d | docs-change (evaluator artefacts) | First evaluator pass: calibrated, 0 flags | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 0 flags" |
| 2026-05-27 | cddc720f | docs-change (evaluator artefacts) | Second evaluator pass: calibrated, 1 flag (HR-001 stale `inputs/_prepare.py`) | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 1 flag" |
| 2026-05-28 | 622342be | docs-change (metadata cleanup) | Dropped unused `prompt_version` line from `metadata.yaml` | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 356e6c45 | docs-change (evaluator artefacts) | Third evaluator pass: calibrated, 1 flag (HR-001 re-raised) | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 1 flag" |
| 2026-06-06 | 5db613fc | mixed (prompt + docs, evaluator pass) | Fourth evaluator pass: house-style rewrite of `instruction` (em-dashes removed), `version` stamped 2, `analyst_notes` authored, README paths fixed | Commit msg: "Re-evaluate spa-l1-capetown-hospital-nn: calibrated, 1 flag" |
| 2026-06-06 | 363aed21 | grader-change | Dropped Gate 2 (`structural_correctness`): geometry-type check became subcheck `geometry_types_point_only`, row-count gate deleted (covered by Jaccard subcheck); subchecks 5 -> 6 | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" (repo-wide refactor; manual-cleanup block above documents it) |
| 2026-06-07 | c749e57b | grader-change | Tagged the three data-content subchecks (`distance_m_matches_reference`, `nearest_hospital_name_matches_reference`, `address_set_preserved`) with `weight=3.0`; score is now weighted (total weight 12) | Commit msg: "Weight data-content subchecks 3x across all categories" (repo-wide) |

This reconstruction agrees with all four prior evaluator blocks on pre-existing commits. The two new commits since the 2026-06-06 review are both repo-wide grader refactors that change score arithmetic only; neither touches the instruction, inputs, reference outputs, or the answer key.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38Z (commit c749e57b, class: grader-change). Note both cutoff-advancing commits since the last review (363aed21 gate-2 drop, c749e57b 3x weighting) alter only how outputs are scored, not what a correct output is; the prompt and answer key have been stable since 5db613fc (2026-06-06T16:55:52Z, version 2).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-09T07:31:18Z | 1.0 | done | current (task_version 2, suite 6510297) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T12:32:49Z | 1.0 | done | current (task_version 2, suite ec540aa) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:46:51Z | 0.8 | done | stale (pre-cutoff); re-graded under current grader: **0.75** (Web-Mercator distance failure) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:35:01Z | 1.0 | done | stale (pre-cutoff); re-graded under current grader: **1.0** |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T16:36:30Z | 1.0 | done | stale (pre-cutoff); re-graded under current grader: **1.0** |

Stale runs: 22 pre-redesign runs (2026-05-12 .. 2026-05-17 morning) plus the 13 runs from 2026-05-17 .. 2026-06-06 documented in the prior evaluator blocks; all pre-date either the WGS84 redesign, the version-2 prompt, or the gate-2/weighting grader refactors and are not used as primary evidence. The three gemma runs above are listed individually because their outputs were produced under the current version-2 prompt and unchanged answer key, so re-grading them with the current weighted grader recovers valid cross-family evidence despite the timestamp staleness.

#### Verdict
**calibrated**

Only two runs post-date the weighting commit and both are DeepSeek V4 Flash (1.0 under both prompt variants), which alone would be insufficient-evidence. However, the two cutoff-advancing commits changed score arithmetic only, and the three Gemma 4 26B runs started after the version-2 prompt (2026-06-06/07) re-grade under the current grader to 0.75 / 1.0 / 1.0. The 0.75 run is the documented Web-Mercator anti-pattern (`distance_m_matches_reference` fails on the 1/cos(34 S) inflation; hospital names still right), now costing 3/12 weighted points instead of 1/5. Combined, four-family evidence (Opus, DeepSeek Flash/Pro, Gemma) preserves the discriminating spread the previous four reviews documented: strong agents 1.0, weaker agents toggling on exactly the unprompted-CRS skill the task targets. The 50 m tolerance continues to absorb legitimate UTM-34S/35S choices while rejecting Web-Mercator drift.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `nearest_hospital.gpkg`, GPKG format | instruction, output paragraph | stated |
| columns `address_id`, `nearest_hospital_name`, `distance_m` | instruction, both paragraphs | stated |
| `nearest_hospital_name` non-empty string | instruction ("comes through as a non-empty string") | stated |
| `distance_m` numeric, finite, non-negative, metres | instruction ("numeric, finite, non-negative value in metres") | stated |
| geometry stays the address Point | instruction ("keeping the original address geometry") | stated |
| one feature per input address (Jaccard >= 0.95) | instruction ("one feature per input address", "keep the original address_id") | stated |
| distance within 50 m of reference for >= 95% | grader-internal tolerance | inferable (metric distance computed in any reasonable projected CRS for Cape Town lands well inside 50 m; the tolerance only excludes wrong-CRS/wrong-unit answers) |
| nearest hospital matches reference for >= 95% | follows from "find the nearest hospital ... by straight-line distance" | inferable |
| metric CRS must be chosen for the distance computation | deliberately unstated; inferable from WGS84 inputs + "distance in metres" | inferable (this is the skill under test) |

Factual claims checked: `addresses.parquet` (120 Points, `address_id`, EPSG:4326) and `hospitals.parquet` (37 Points, `hospital_id`, `name`, EPSG:4326) verified by direct read; output filename, format, and column names match `expected_outputs[]` and the reference output schema. No missing or inaccurate claims.

#### Reference faithfulness
`reference/solution/generate.py` reads both parquets, reprojects both layers to EPSG:32734 (the canonical UTM zone for Cape Town), runs `sjoin_nearest` with a distance column, breaks ties deterministically, keeps exactly the requested four columns, and writes one GPKG feature per address. No unrequested operations (the fixed-timestamp stamp is reproducibility plumbing, not data manipulation), no skipped steps, and the CRS choice is well-suited to the region. Faithful.

#### Specific findings
- Grader re-weighting (c749e57b) shifted the broken-set scores: degrees_distance 0.6 -> 0.5, wrong_hospital 0.6 -> 0.5, distance_in_km 0.8 -> 0.75 (wrong_format stays 0.0). All remain inside their `expected_score_range`. Re-measured this run with one grader invocation each; `metadata.yaml > broken_solutions > measured_score` updated accordingly (unilateral, no version bump required).
- README "Failure modes" section still quoted the pre-weighting scores (0.6/0.6/0.8) and referenced the deleted "Gate 2 row-count check". Fixed unilaterally (docs-change, no version bump).
- Instruction (`task.json:15`, version 2) remains clean: no EPSG code, no library names, no em-dashes, purpose-then-ask shape, deliberate CRS omission intact. The column list appearing in both paragraphs is the intended redundant-output-schema safety net; para 1 carries the value constraints, para 2 the file contract. No gift to strip, no redundancy worth churning.
- `analyst_notes` (authored 2026-06-06) remains accurate after the grader refactors: the wrong-format pitfall still fails the single hard gate, and the distance pitfalls map to the now-3x-weighted subchecks. No refresh needed.
- 2c-CRS: `expected_outputs[]` deliberately omits a CRS; README states the model chooses; reference output is EPSG:32734; current submissions are EPSG:4326. Grading runs on the scalar `distance_m` keyed by `address_id` with no reprojection of either side, so no one-sided-reprojection hazard and no contract mismatch.
- Inventory row (`authoring/inventory.md:674-697`) still matches every axis. No mismatch.
- HR-001 from the 2026-05-27/05-28/06-06 reviews (stale `inputs/_prepare.py` docstring + `.to_crs("EPSG:32734")` calls vs the committed WGS84 inputs) is still open: lines 5, 27, 107, 147 still document/produce EPSG:32734. The file is authoring-time only with no grading impact, and `inputs/` is off-limits for the evaluator. Re-raised as HR-001.
  <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" --> `inputs/_prepare.py` still documents and reprojects to EPSG:32734, contradicting the WGS84 inputs the 2026-05-17 redesign committed; a human should refresh the helper's docstring and drop the trailing `.to_crs("EPSG:32734")` calls so re-running it reproduces the WGS84 inputs, and bump `version` if the regenerated parquets differ. No grading impact. (Re-raised from prior evaluator blocks.)

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` to the weighted grader's scores (0.0 / 0.5 / 0.5 / 0.75). Re-grade on reference: 1.0 (6/6 subchecks). Reason: c749e57b's 3x data-content weighting changed the arithmetic; all scores remain inside their expected ranges.
- `README.md`: updated the three broken-set scores in "Failure modes" and removed the stale "Gate 2 row-count check" reference. Reason: docs drifted behind the 363aed21/c749e57b grader refactors; no version bump for docs.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp (slugs unchanged, all validated against `coverage-vocabulary.yaml`).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — `inputs/_prepare.py` docstring and `.to_crs("EPSG:32734")` calls are stale vs the committed WGS84 inputs; refresh helper for reproducibility. No grading impact.

#### Tests run
- grader on reference: 1.0 (6/6 subchecks, 1/1 gate)
- broken sets re-measured: wrong_format 0.0, degrees_distance 0.5, wrong_hospital 0.5, distance_in_km 0.75 (all within expected ranges)
- pytest: pass (41 passed)

---

## Weight recalibration 2026-06-14  (evaluator-commit <pending>)

**Change:** Recalibrated subcheck weights so the score tracks error severity. The blunt repo-wide commit (05b389b/c749e57) had set all three "data-content" subchecks to weight 3.0, lumping the address-set bookkeeping check in with the two subchecks that detect the central skill. Re-weighted: the two central subchecks up to 4.0, and `address_set_preserved` down to 2.0 (data loss, but not the analysis itself). Grading-only; no version bump.

The central skill is **correct nearest-neighbour assignment computed in a projected CRS**. The two subchecks that detect its failure are `distance_m_matches_reference` (catches degree-vs-metre, wrong-CRS, wrong-unit) and `nearest_hospital_name_matches_reference` (catches wrong-hospital). These now carry the highest weight. The structural/format checks (geometry Point-only, name populated, distance numeric/finite) stay at 1.0. `address_set_preserved` is dropped/duplicated-row data loss — worse than a format slip but not the NN analysis — so it sits between, at 2.0.

#### Weight changes
| Subcheck | old | new | role |
|---|---|---|---|
| geometry_types_point_only | 1.0 | 1.0 | structural |
| nearest_hospital_name_populated | 1.0 | 1.0 | structural |
| distance_m_numeric_finite | 1.0 | 1.0 | structural |
| distance_m_matches_reference | 3.0 | **4.0** | CENTRAL (CRS/metric distance) |
| nearest_hospital_name_matches_reference | 3.0 | **4.0** | CENTRAL (NN assignment) |
| address_set_preserved | 3.0 | **2.0** | data-loss (row drop/dup) |

Total weight 12 -> 13.

#### Broken scores before -> after
| Broken | before | after | note |
|---|---|---|---|
| wrong_format | 0.00 | 0.00 | hard gate (wrong format) — unchanged |
| degrees_distance | 0.50 | 0.3846 | both central subchecks fail — most severe; now a meaningful sub-0.5 drop |
| wrong_hospital | 0.50 | 0.3846 | both central subchecks fail — equally severe |
| distance_in_km | 0.75 | 0.6923 | only the distance subcheck fails (hospital right) — lighter, recoverable slip |

Ordering: monotone and defensible. The two both-central failures (degrees, wrong_hospital) sit lowest at 0.385; the single-central unit slip (distance_in_km) sits clearly above at 0.692; reference stays 1.0. A hypothetical row-drop-only failure (only `address_set_preserved` fails) would score 0.846 — penalised more than a pure format slip but well below a correct answer, as intended for data loss. No disjoint-failure inversion: the central pair dominates, the data-loss check is intermediate, and the structural checks are lowest.

#### Prior-run re-grade summary
Re-graded the 19 runs that exist under the current answer key (the version-2 prompt, post-redesign). All 1.0 runs (Opus 4-6/4-7, DeepSeek V4 Flash/Pro, and Gemma's metric-CRS runs) stay 1.0; the one no-output run stays 0.0. The six Gemma 4 26B Web-Mercator runs (run-20260526-0748Z, -20260527-2321Z, -20260528-1624Z, -20260529-0109Z, -20260606-1129Z, and the stale-listed -20260606-1129Z) recorded 0.8 under the old 5-subcheck grader and re-grade to **0.6923** under the recalibrated weights (they fail only `distance_m_matches_reference` — the 1/cos(34°S) inflation signature — with the hospital still right). No other notable shifts; the recalibration deepens the penalty for getting the central metric-distance computation wrong, exactly as intended.

#### Reasoning
A meaningful/central mistake (wrong CRS, degrees, wrong hospital) must cause a meaningful score drop; a cosmetic/structural slip should only lightly drop the score. Under the old flat 3.0-on-three weighting, both-central failures scored 0.5 (right at the pass/fail midpoint) and a row-drop would have cost as much as a wrong-hospital — miscalibrated. The new 1/1/1/4/4/2 split pushes both-central failures to 0.385 (clearly failing) while keeping the unit-only slip at 0.692, and demotes the bookkeeping check to a data-loss-appropriate 2.0.

#### HR status
HR-001 (`inputs/_prepare.py` stale EPSG:32734 docstring/calls vs committed WGS84 inputs) is `reference-or-data-edit-needed`, NOT a weighting HR — kept open and unchanged. No grading impact.

#### Tests run
- grader on reference: 1.0 (6/6 subchecks, 1/1 gate)
- broken sets re-measured: wrong_format 0.00, degrees_distance 0.3846, wrong_hospital 0.3846, distance_in_km 0.6923 (all within updated expected ranges)
- pytest: not run (orchestrator runs the suite)
