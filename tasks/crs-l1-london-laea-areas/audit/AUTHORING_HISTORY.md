# Implementation notes — crs-l1-london-laea-areas

## Status
completed

## Summary
L1 CRS-reprojection task, redesigned to test **unprompted CRS reasoning**.
Input is a WGS84 GeoJSON of 232 London-area admin polygons.  The instruction
asks for a CSV with `id, name, area_km2` — no output CRS is specified.  The
model must independently recognise that area computation on geographic
coordinates is meaningless and choose an appropriate projected CRS.

Previous version explicitly asked for EPSG:3035 output and a GeoJSON with
`area_km2_laea`.  This version removes all CRS guidance.

## Changes from previous version (2026-05-07-a → 2026-05-17-a)
- Instruction: removed all mention of EPSG:3035 / LAEA / reprojection
- Output: changed from GeoJSON (EPSG:3035, MultiPolygon) to CSV (id, name, area_km2)
- Grader: rewritten for CSV; area tolerance widened from 1 % to 2 % to accept
  any reasonable projection (LAEA, UTM, OSGB, geodesic)
- Broken solutions: replaced (wrong_format → GeoJSON-instead-of-CSV,
  degrees_area → computed in WGS84 degrees², area_m2 → m² not km²)
- Reference: regenerated as CSV using EPSG:3035 for area computation

## Verification results
- Reference grader score: 1.00 (5/5 subchecks)
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - degrees_area: 0.60 (3/5) (expected range [0.5, 0.7])
  - area_m2: 0.60 (3/5) (expected range [0.5, 0.7])
- Second-run output match: deterministic (CSV from pandas, sorted by name+id)

## Failure-mode coverage
- Computed area in WGS84 degrees² (primary target failure): broken_degrees_area
- Correctly reprojected but area in m² not km²: broken_area_m2
- Wrong output format: broken_wrong_format
- Drop / rename required columns: principled — Gate 1 schema check
- Filter out features: principled — Gate 2 count tolerance + id Jaccard subcheck

## Open issues
- [low] Old broken solution directories from previous version (broken_wrong_crs,
  broken_area_units) and old reference output (boroughs_laea.geojson) should be
  cleaned up.

## Inventory change proposals
(applied — inventory.md updated)

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
First-version task (`prompt_version: 2026-05-07-a`) was a classic CRS-reprojection
exercise: input WGS84 GeoJSON of 232 London-area admin polygons, instruction
named EPSG:3035 LAEA Europe explicitly, output GeoJSON in 3035 with an
`area_km2_laea` attribute. Story: Sophia Marchetti at UCL needs an honest
pan-European borough land-area table for a Horizon report. The skill exercised
was: identify that lat/lon `.area` is meaningless, reproject to a named CRS,
divide by 1e6.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 1dc5019 | initial-authoring | Initial scaffold: task.json with EPSG:3035 explicit, metadata, grader, README, generate.py | Initial benchmark commit |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" bullet list (CRS, geom type, required cols, join key) to instruction | Commit msg: "declare exact output schema in prompts to match graders" — implicit grader contracts surfaced into prompt |
| 2026-05-13 | 284b843 | prompt-change | Added `tags` dict (region/data_source/formats/crs/geom/operations/themes/quality/scale) to task.json | Commit msg: structured tags for filtering, derived from inventory axes |
| 2026-05-13 | 4f0cfc0 | prompt-change | Merged the "Output schema:" bullet list into a single prose paragraph | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d | prompt-change | Removed input-CRS mentions, input column enumeration, geometry-type description from instruction (input-side hints only; output requirements preserved) | Commit msg: "Strip deducible information from CRS task instructions … Output requirements (target CRS, output columns, output geometry types) and task framing are preserved." |
| 2026-05-15 | 7ac5fbe | prompt-change | Further stripped the "lat/lon areas are useless across Europe, … the standard equal-area for pan-EU work" rationale plus the "polygon area … computed in the projected CRS" wording; still names EPSG:3035 | Commit msg: "Strip deducible information from CRS task instructions" (no further explanation; rationale presumed continuation of prior commit's intent) <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: continuation of d5c283d implied but not stated in this commit's message. |
| 2026-05-17 | fbf3b26 | mixed (prompt + grader + reference + tests + docs) | Full redesign to test **unprompted CRS reasoning**: instruction no longer names any CRS; output changed from GeoJSON-in-3035 with `area_km2_laea` to plain CSV `id,name,area_km2`; tags updated (formats `[geojson,csv]`, crs `[EPSG:4326]`, operations dropped `reprojection`); area tolerance widened 1 % → 2 % to accept any reasonable projection (LAEA, UTM, OSGB, geodesic); broken set re-cut (wrong_format = GeoJSON-not-CSV, degrees_area = WGS84 `.area` without reproject, area_m2 = m² not km²); reference regenerated as CSV; old broken dirs broken_wrong_crs, broken_area_units left in place as legacy artefacts (flagged in Open issues) | Commit msg: "Remove all CRS guidance from the instruction — the model now receives WGS84 polygons and must independently figure out that area computation on geographic coordinates is meaningless." |
| 2026-05-26 | 29a9ae3 | mixed (path-only: prompt + grader + reference + data + tests + docs) | Repo-wide reorg of task folder layout: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md; data/ → inputs/; reference/generate.py + outputs/ + visualizations/ → reference/solution/; tests/ → reference/failures/; image*.* → assets/. Inside task.json, only the input URL path changed (`data/` → `inputs/`); no semantic prompt or grader change. | Commit msg: "Migrate every benchmark task to a clearer layout that separates audience concerns" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff for prompt/grader semantics: **2026-05-17T12:15:58Z** (commit fbf3b26, class: mixed — full redesign of prompt+grader+reference+tests).
- A later mixed commit (29a9ae3, 2026-05-26T09:51:37Z) changed only filesystem layout and the input URL path inside task.json; it did not change instruction semantics, grader logic, reference values, or input bytes. Treating runs after the 2026-05-17 redesign as "current" for the semantic question, with the caveat that the 2026-05-26 path move is irrelevant to scoring.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:54:12Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:24:31Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:48:55Z | 1.0 | done | current |

Footnote — stale (pre-redesign) runs considered and discarded: 22 earlier
runs spanning 2026-05-12 → 2026-05-17 06:14Z under the previous prompt
version (`2026-05-07-a` / GeoJSON output). The most recent stale-window run
(run-20260517-0614Z, openrouter-deepseek-v4-flash-basic) scored 0.0 under
the old grader. These are not valid evidence for the current task.

#### Verdict
**calibrated**

The three current runs come from three independent model families (Anthropic
Claude Opus 4.6, DeepSeek v4 Flash, Google Gemma 4 26B). All three produce
correct CSVs that score 1.0, and each chose a different reprojection path:
Opus picked EPSG:3035 (LAEA Europe), DeepSeek and Gemma both picked
EPSG:27700 (British National Grid). The grader's 2 % tolerance correctly
accepts both choices for the London region — for example, Opus's Abbots
Langley area was 18.5457 km² (LAEA), the reference (also LAEA) is 18.5457
km², and DeepSeek/Gemma's OSGB value is 18.5374 km² — a 0.04 % difference,
comfortably inside the 2 % floor.

The fact that all three models scored 1.0 is **not** evidence of
over-specification: re-reading the current instruction (task.json, line 14),
no CRS is named, no algorithm is described, no library is called out, and
the only hint that reprojection is needed is the filename
`london_admin_wgs84.geojson` (which is accurate self-describing data, not a
gift). The "too-easy" rubric only fires when the instruction
over-specifies the answer; here, the instruction is correctly minimal and
the agents independently demonstrated the target skill (recognising that
WGS84 `.area` is meaningless and reprojecting to a metric CRS). For an L1
task, three out of three current agents clearing the bar is acceptable
calibration; the broken-solution catalogue covers the canonical failure
mode (`broken_degrees_area`, 0.6) for weaker agents that would otherwise
slip through.

Verified at this audit: reference grader re-run = **1.0** (5/5
subchecks); broken_wrong_format = 0.0, broken_degrees_area = 0.6,
broken_area_m2 = 0.6, all matching metadata.yaml > broken_solutions >
measured_score exactly. Legacy broken dirs broken_wrong_crs and
broken_area_units both score 0.0 (no `borough_areas.csv` present), which is
correct but uninformative — they belong to the previous prompt version.

Cross-axis consistency: tags in task.json (`crs: [EPSG:4326]`,
`operations: [area_calculation]`, `formats: [geojson, csv]`) line up with
the post-redesign inventory row.

#### Specific findings
- Verdict: **calibrated**. No prompt or grader change required.
- Legacy broken directories `reference/failures/broken_wrong_crs/` and
  `reference/failures/broken_area_units/` (and the stale
  `reference/solution/outputs/boroughs_laea.geojson`) are residue from the
  pre-2026-05-17 prompt version. They no longer correspond to a failure
  mode the current grader exercises and add noise to the failure catalogue.
  Removing them is an edit under `reference/failures/` and
  `reference/solution/outputs/`, which the evaluator is not permitted to
  apply. <!-- HUMAN-REVIEW id="HR-002" category="reference-or-data-edit-needed" severity="low" -->
  Author should delete `reference/failures/broken_wrong_crs/`,
  `reference/failures/broken_area_units/`, and
  `reference/solution/outputs/boroughs_laea.geojson` in a follow-up commit.
  The existing AUTHORING_HISTORY "Open issues" section already lists this
  as a low-priority cleanup item, so this flag is purely an explicit
  hand-off to the human.
- Grader correctness re-checked end-to-end: reference 1.00, broken_wrong_format
  0.00, broken_degrees_area 0.60, broken_area_m2 0.60 — exact agreement with
  declared `measured_score` values; no drift since the 2026-05-17 redesign.
- pytest after this audit: 35/35 pass.

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; coverage.yaml + this audit block are evaluator
artefacts, not edits to the task contract)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — commit 7ac5fbe ("Strip deducible information from CRS task instructions", 2026-05-15) has no body. Rationale is presumed to be a continuation of d5c283d on the previous day, but the commit message does not say so. Low-severity; only matters if the human ever needs to reconstruct that day's intent.
- HR-002 — reference-or-data-edit-needed — legacy broken-solution directories `broken_wrong_crs/`, `broken_area_units/`, and stray reference output `boroughs_laea.geojson` should be deleted by a human (already in the pre-existing Open issues list).

#### Tests run
- grader on reference (`benchmark/tasks/crs-l1-london-laea-areas/reference/solution/outputs`): **1.0** (5/5 subchecks).
- grader on each broken set: wrong_format 0.0, degrees_area 0.6, area_m2 0.6, wrong_crs 0.0 (legacy), area_units 0.0 (legacy) — all match metadata.
- pytest (benchmark/eval): 35 passed, 0 failed.

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
First version (`prompt_version: 2026-05-07-a`, commit 1dc5019 under the
pre-reorg path) was a straightforward CRS-reprojection exercise: a WGS84
GeoJSON of 232 London-area administrative units, an instruction that named
EPSG:3035 (LAEA Europe) explicitly, and a GeoJSON output in EPSG:3035 carrying
an `area_km2_laea` attribute. The persona — Sophia Marchetti at UCL's EU
climate-policy unit — needs an honest pan-European borough land-area table for
a Horizon report. The skill exercised was: recognise that lat/lon `.area` is
meaningless, reproject to the named CRS, divide by 1e6.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 1dc5019 | initial-authoring | Initial scaffold under `benchmark/eval/tasks/`: task.json naming EPSG:3035, metadata, grader, README, generate.py, GeoJSON reference | (initial benchmark commit) |
| 2026-05-13 | (image/path commits) | docs-change | image-prompt.md + image.webp added/regenerated for all 36 tasks; directory moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msgs: image generation + repo restructure; no semantic prompt/grader change |
| 2026-05-13 | 4f0cfc0 | prompt-change | Merged the explicit "Output schema:" bullet list into a single prose paragraph | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d | prompt-change | Stripped input-side hints (input CRS, input column enumeration, geometry-type description) from the instruction; output requirements preserved | Commit msg: "Strip deducible information from CRS task instructions … Output requirements (target CRS, output columns, output geometry types) and task framing are preserved." |
| 2026-05-15 | 7ac5fbe | prompt-change | Stripped the "lat/lon areas are useless across Europe … standard equal-area for pan-EU work" rationale and the "polygon area … computed in the projected CRS" wording; instruction still named EPSG:3035 | Commit msg: "Strip deducible information from CRS task instructions" — body is empty, so this commit does not itself restate the why <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: continuation of d5c283d implied but not stated in this commit's message/body. |
| 2026-05-17 | fbf3b26 | mixed (prompt + grader + reference + tests + docs) | Full redesign to test **unprompted CRS reasoning**: instruction no longer names any CRS; output changed from GeoJSON-in-3035 (`area_km2_laea`) to plain CSV `id,name,area_km2`; tags updated (formats `[geojson,csv]`, crs `[EPSG:4326]`, `reprojection` dropped from operations); area tolerance widened 1 % → 2 % to accept any reasonable projection (LAEA, UTM, OSGB, geodesic); broken set re-cut (wrong_format = GeoJSON-not-CSV, degrees_area = WGS84 `.area` un-reprojected, area_m2 = m² not km²); reference regenerated as CSV; legacy broken dirs `broken_wrong_crs`, `broken_area_units` and old `boroughs_laea.geojson` left in place | Commit msg: "Remove all CRS guidance from the instruction — the model now receives WGS84 polygons and must independently figure out that area computation on geographic coordinates is meaningless." |
| 2026-05-26 | 29a9ae3 | mixed (path-only) | Repo-wide reorg: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md; data/ → inputs/; reference/generate.py + outputs/ → reference/solution/; tests/ → reference/failures/; image*.* → assets/. In task.json only the input URL path changed (`data/` → `inputs/`); no semantic prompt or grader change | Commit msg: "Migrate every benchmark task to a clearer layout that separates audience concerns" |
| 2026-05-26 | 2b94fe7 | docs-change | Prior evaluator review: appended 2026-05-26 review block to AUTHORING_HISTORY.md, wrote coverage.yaml and audit/status.json; verdict calibrated, no contract edits | Commit msg: "Re-evaluate crs-l1-london-laea-areas: calibrated; 2 low flags" — evaluator artefacts only |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T12:15:58Z** (commit fbf3b26, class: mixed — full prompt + grader + reference + tests redesign).
- Later commits 29a9ae3 (2026-05-26, path-only) and 2b94fe7 (2026-05-26, evaluator docs/coverage only) do not change instruction semantics, grader logic, reference values, or input bytes; they do not move the cutoff. Runs after 2026-05-17T12:15:58Z are therefore `current`.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T12:54:12Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:24:31Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T07:48:55Z | 1.0 | done | current |

Footnote — stale (pre-redesign) runs considered and discarded: 22 earlier
runs spanning 2026-05-12 → 2026-05-17 06:14Z under the previous prompt
version (`2026-05-07-a` / GeoJSON output). The most recent stale-window run
(run-20260517-0614Z) scored 0.0 under the old grader. They are not valid
evidence for the current task.

#### Verdict
**calibrated**

Three `current` runs from three independent model families (Anthropic Claude
Opus 4.6, DeepSeek V4 Flash, Google Gemma 4 26B) all produce correct CSVs that
score 1.0 (gates pass; all 5 subchecks pass), and each independently chose its
own projected CRS for area: Opus picked EPSG:3035 (LAEA Europe), DeepSeek and
Gemma both picked EPSG:27700 (British National Grid). This is exactly the skill
the task probes — recognising that WGS84 `.area` is meaningless and reprojecting
to a metric CRS without being told to. The grader's 2 % per-feature tolerance
correctly accepts both choices: e.g. Abbots Langley = 18.5457 km² (LAEA, Opus
and reference) vs 18.5374 km² (OSGB, DeepSeek/Gemma) — a 0.04 % difference,
comfortably inside the floor.

Three-of-three at 1.0 is **not** the `too-easy` signal: re-reading task.json
line 14, the instruction names no CRS, no algorithm, and no library; the only
cue that reprojection is needed is the accurate filename
`london_admin_wgs84.geojson` (self-describing data, not a gift). The `too-easy`
rubric fires only when the instruction over-specifies the answer, which it does
not here. For an L1 task, capable agents clearing the bar is expected
calibration, and the broken-solution catalogue covers the canonical weak-agent
failure (`broken_degrees_area`, 0.6) for agents that would compute area in
degrees².

**Output-CRS / format consistency (2c-CRS):** the declared output is CSV with
columns `id,name,area_km2` — a tabular, geometry-free output, so there is no
output CRS to pin and no reprojection performed by the grader. The grader
compares the agent's scalar `area_km2` against the reference's scalar
`area_km2` directly (no one-sided reprojection of geometry); both numbers are
each produced from their own author's/agent's projection choice. README,
`expected_outputs[]`, and reference all agree: CSV, no output CRS. No
inconsistency.

Verified at this audit: reference grader re-run = **1.0** (5/5 subchecks);
broken_wrong_format 0.0, broken_degrees_area 0.6, broken_area_m2 0.6 — all
match `metadata.yaml > broken_solutions > measured_score` exactly. Legacy dirs
broken_wrong_crs 0.0 and broken_area_units 0.0 (no `borough_areas.csv`; they
emit `boroughs_laea.geojson` from the old prompt version) — correct but
uninformative. pytest: 35 passed.

Cross-axis consistency: task.json tags (`crs: [EPSG:4326]`,
`operations: [area_calculation]`, `formats: [geojson, csv]`,
`themes: [divisions.division, boundary_administrative]`, `scale: small`) line up
with the post-redesign inventory row and with coverage.yaml.

#### Specific findings
- Verdict: **calibrated**. No prompt, grader, or tolerance change required.
- HR-001 (carried forward, design-rationale, low): commit 7ac5fbe
  ("Strip deducible information from CRS task instructions", 2026-05-15) has an
  empty body. Its rationale is presumed to continue the previous day's d5c283d,
  but neither the subject nor the body says so. Low-severity; only matters if a
  human later needs to reconstruct that day's intent. Superseded in effect by
  the 2026-05-17 redesign, which dropped the EPSG hint entirely.
- HR-002 (carried forward, reference-or-data-edit-needed, low): legacy
  broken-solution directories `reference/failures/broken_wrong_crs/` and
  `reference/failures/broken_area_units/`, plus the stray reference output
  `reference/solution/outputs/boroughs_laea.geojson`, are residue from the
  pre-2026-05-17 prompt version. They no longer correspond to a failure mode the
  current CSV grader exercises (both score 0.0 only because the expected CSV is
  absent) and add noise to the failure catalogue. Deleting them is an edit under
  `reference/failures/` and `reference/solution/outputs/`, which the evaluator is
  not permitted to apply. Author should delete all three in a follow-up commit.
  This is already listed in the author's "Open issues" section; the flag is an
  explicit hand-off. <!-- HUMAN-REVIEW id="HR-002" category="reference-or-data-edit-needed" severity="low" -->

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; coverage.yaml + this audit block + status.json are
evaluator artefacts, not edits to the task contract)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — commit 7ac5fbe (2026-05-15) has an empty body; rationale presumed to continue d5c283d but not stated. Low; effectively moot after the 2026-05-17 full redesign.
- HR-002 — reference-or-data-edit-needed — legacy broken dirs `broken_wrong_crs/`, `broken_area_units/`, and stray `boroughs_laea.geojson` should be deleted by a human (already in the author's Open issues list).

#### Tests run
- grader on reference (`benchmark/tasks/crs-l1-london-laea-areas/reference/solution/outputs`): **1.0** (5/5 subchecks).
- grader on each broken set: wrong_format 0.0, degrees_area 0.6, area_m2 0.6; legacy wrong_crs 0.0, area_units 0.0 — all match metadata.
- pytest (benchmark/eval): 35 passed, 0 failed.

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
First version (commit 1dc5019, `prompt_version: 2026-05-07-a` under the pre-reorg
path) was a straightforward CRS-reprojection exercise: WGS84 GeoJSON of 232
London-area admin polygons; the instruction named EPSG:3035 (LAEA Europe)
explicitly; output GeoJSON in EPSG:3035 with `area_km2_laea`. Persona: Sophia
Marchetti at UCL's EU climate-policy unit, preparing a pan-European borough
land-area table for a Horizon report. Skill exercised: recognise that lat/lon
`.area` is meaningless, reproject to the named CRS, divide by 1e6.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 1dc5019 | initial-authoring | Initial scaffold under `benchmark/eval/tasks/`: task.json naming EPSG:3035, metadata, grader, README, generate.py, GeoJSON reference | (initial benchmark commit) |
| 2026-05-13 | (image/path commits) | docs-change | image-prompt.md + image.webp added/regenerated for all 36 tasks; directory moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msgs: image generation + repo restructure; no semantic prompt/grader change |
| 2026-05-13 | 4f0cfc0 | prompt-change | Merged the explicit "Output schema:" bullet list into a single prose paragraph | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d | prompt-change | Stripped input-side hints (input CRS, input column enumeration, geometry-type description); output requirements preserved | Commit msg: "Strip deducible information from CRS task instructions … Output requirements (target CRS, output columns, output geometry types) and task framing are preserved." |
| 2026-05-15 | 7ac5fbe | prompt-change | Stripped the "lat/lon areas are useless across Europe … standard equal-area for pan-EU work" rationale and the "polygon area … computed in the projected CRS" wording; instruction still named EPSG:3035 | Commit msg subject only ("Strip deducible information from CRS task instructions"); body empty <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: continuation of d5c283d implied but not stated in this commit's message/body. |
| 2026-05-17 | fbf3b26 | mixed (prompt + grader + reference + tests + docs) | Full redesign to test **unprompted CRS reasoning**: instruction no longer names any CRS; output changed from GeoJSON-in-3035 (`area_km2_laea`) to plain CSV `id,name,area_km2`; tags updated (formats `[geojson,csv]`, crs `[EPSG:4326]`, `reprojection` dropped from operations); area tolerance 1 % → 2 % to accept any reasonable projection (LAEA, UTM, OSGB, geodesic); broken set re-cut (wrong_format, degrees_area, area_m2); reference regenerated as CSV; legacy `broken_wrong_crs`, `broken_area_units`, `boroughs_laea.geojson` left in place | Commit msg: "Remove all CRS guidance from the instruction — the model now receives WGS84 polygons and must independently figure out that area computation on geographic coordinates is meaningless." |
| 2026-05-26 | 29a9ae3 | mixed (path-only) | Repo-wide reorg of task folder layout; only the input URL path inside task.json changed (`data/` → `inputs/`); no semantic prompt or grader change | Commit msg: "Migrate every benchmark task to a clearer layout that separates audience concerns" |
| 2026-05-26 | 2b94fe7 | docs-change | Prior evaluator review (2026-05-26): appended review block, wrote coverage.yaml + audit/status.json; verdict calibrated | Commit msg: "Re-evaluate crs-l1-london-laea-areas: calibrated; 2 low flags" |
| 2026-05-27 | 00f2007 | docs-change | Prior evaluator review (2026-05-27): appended review block, refreshed coverage.yaml + audit/status.json; verdict calibrated | Commit msg: "Re-evaluate crs-l1-london-laea-areas: calibrated; 2 low flags" |
| 2026-05-28 | 622342b | docs-change (metadata-only) | Repo-wide drop of the `prompt_version: 2026-05-17-a` field from `metadata.yaml`; this field tagged the orchestrator's authoring template and had no runtime semantic effect (no impact on tolerances, instruction, grader, or inputs) | Commit msg: "Add task content versioning; drop unused prompt_version" — system-wide introduction of `task.json.version`; this task does not yet carry the new field, so it is implicitly v1 |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T12:15:58Z** (commit fbf3b26, class: mixed — full prompt + grader + reference + tests redesign).
- Later commits 29a9ae3 (2026-05-26, path-only), 2b94fe7 (2026-05-26, evaluator artefacts), 00f2007 (2026-05-27, evaluator artefacts), and 622342b (2026-05-28, `prompt_version` field removed from metadata.yaml — not a tolerance/instruction/grader/inputs change) do not change instruction semantics, grader logic, tolerances, reference values, or input bytes; they do not move the cutoff. Runs after 2026-05-17T12:15:58Z are therefore `current`.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T12:54:12Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:24:31Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T07:48:55Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus (claude-opus-4-7) | 2026-05-27T20:16:18Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-27T23:21:17Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus (claude-opus-4-7) | 2026-05-28T01:13:49Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T03:17:33Z | 1.0 | done | current |

Footnote — stale (pre-redesign) runs considered and discarded: 22 earlier
runs spanning 2026-05-12 → 2026-05-17 06:14Z under the previous prompt
version. Not valid evidence for the current task.

#### Verdict
**calibrated**

Seven `current` runs across three independent model families (Anthropic Claude
Opus 4.6 + Opus 4.7, DeepSeek V4 Flash, Google Gemma 4 26B) all produce correct
CSVs that score 1.0. Each model independently picks a CRS: Opus (4.6 and 4.7)
picks EPSG:3035 (LAEA Europe); Gemma 4 26B picks EPSG:27700 (British National
Grid); DeepSeek picked OSGB previously. This is exactly the skill the task
probes — recognising that WGS84 `.area` is meaningless and reprojecting to a
metric CRS without being told to. The grader's 2 % per-feature tolerance
correctly accepts both choices: at Abbots Langley = 18.5457 km² (LAEA) vs
18.5374 km² (OSGB) — a 0.04 % difference, comfortably inside the floor.
Verified against this audit's run outputs (matches reference's LAEA value
exactly for Opus runs; OSGB-differs-by-0.04% for Gemma runs).

Seven-of-seven at 1.0 is **not** the `too-easy` signal: re-reading task.json
line 14 ("Pan-European land-area comparison for the Horizon report — I need
the polygon area in square kilometres for every feature in the supplied
london_admin file. Output a CSV to borough_areas.csv with columns id, name,
area_km2. Use id as the feature identity key."), the instruction names no CRS,
no algorithm, and no library; the only cue that reprojection is needed is the
accurate filename `london_admin_wgs84.geojson` (self-describing data, not a
gift). For an L1 task, capable agents clearing the bar is expected
calibration. The broken-solution catalogue covers the canonical weak-agent
failure (`broken_degrees_area`, 0.6) for agents that would compute area in
degrees².

**Output-CRS / format consistency (2c-CRS):** the declared output is CSV with
columns `id,name,area_km2` — a tabular, geometry-free output, so there is no
output CRS to pin and no reprojection performed by the grader. The grader
compares scalar `area_km2` against scalar `area_km2` directly (no one-sided
reprojection of geometry); both numbers are each produced from their own
agent's projection choice. README, `expected_outputs[]`, and reference all
agree: CSV, no output CRS. No inconsistency.

Verified at this audit: reference grader re-run = **1.0** (5/5 subchecks);
broken_wrong_format 0.0, broken_degrees_area 0.6, broken_area_m2 0.6 — all
match `metadata.yaml > broken_solutions > measured_score` exactly. Legacy
`broken_wrong_crs` 0.0 and `broken_area_units` 0.0 (no `borough_areas.csv`;
they emit `boroughs_laea.geojson` from the old prompt version) — correct but
uninformative. pytest: 41 passed.

Cross-axis consistency: task.json tags (`crs: [EPSG:4326]`,
`operations: [area_calculation]`, `formats: [geojson, csv]`,
`themes: [divisions.division, boundary_administrative]`, `scale: small`) line
up with the post-redesign inventory row and with coverage.yaml.

#### Specific findings
- Verdict: **calibrated**. No prompt, grader, or tolerance change required.
- HR-001 (carried forward, design-rationale, low): commit 7ac5fbe
  ("Strip deducible information from CRS task instructions", 2026-05-15) has an
  empty body. Its rationale is presumed to continue the previous day's d5c283d,
  but neither the subject nor the body says so. Low-severity; superseded in
  effect by the 2026-05-17 redesign, which dropped the EPSG hint entirely.
- HR-002 (carried forward, reference-or-data-edit-needed, low): legacy
  broken-solution directories `reference/failures/broken_wrong_crs/` and
  `reference/failures/broken_area_units/`, plus the stray
  `reference/solution/outputs/boroughs_laea.geojson`, are residue from the
  pre-2026-05-17 prompt version. They no longer correspond to a failure mode
  the current CSV grader exercises (both score 0.0 only because the expected
  CSV is absent). Deleting them is an edit under `reference/failures/` and
  `reference/solution/outputs/`, which the evaluator is not permitted to apply.
  Author should delete all three in a follow-up commit; the human applying the
  fix should also bump `task.json.version` from implicit-v1 to explicit v2.
  Already listed in the author's "Open issues" section.
  <!-- HUMAN-REVIEW id="HR-002" category="reference-or-data-edit-needed" severity="low" -->

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; no contract edits applied. coverage.yaml + this
audit block + status.json are evaluator artefacts, not edits to the task
contract, so no `task.json.version` bump is required this run.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — commit 7ac5fbe (2026-05-15) has an empty body; rationale presumed to continue d5c283d but not stated. Low; effectively moot after the 2026-05-17 full redesign.
- HR-002 — reference-or-data-edit-needed — legacy broken dirs `broken_wrong_crs/`, `broken_area_units/`, and stray `boroughs_laea.geojson` should be deleted by a human (already in the author's Open issues list). Human should also bump `task.json.version` to 2 on the same commit.

#### Tests run
- grader on reference (`benchmark/tasks/crs-l1-london-laea-areas/reference/solution/outputs`): **1.0** (5/5 subchecks).
- grader on each broken set: wrong_format 0.0, degrees_area 0.6, area_m2 0.6; legacy wrong_crs 0.0, area_units 0.0 — all match metadata.
- pytest (benchmark/eval): 41 passed, 0 failed.

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior reviews. First version (commit 1dc5019, `prompt_version: 2026-05-07-a` under the pre-reorg path) was a straightforward CRS-reprojection exercise that explicitly named EPSG:3035. The 2026-05-17 redesign (fbf3b26) stripped all CRS guidance and changed the output to a plain CSV `id,name,area_km2` so the task probes **unprompted CRS reasoning**. Persona Sophia Marchetti at UCL preparing a Horizon-report borough land-area table is unchanged.

#### Change log (new commits only)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 072c89d | prompt-change | Rewrote `task.json.instruction` in the project's house style ("I need to create a land-area comparison for the Horizon report. Can you get me the area in km² for every borough in `london_admin.geojson`?..."); added `analyst_notes` (description + 5-step approach + 4 pitfalls). No CRS hint reintroduced; the persona's "Horizon report" framing preserved. `version` field **not** bumped despite the instruction change. | Commit msg: "Rewrite crs-l1 london and nyc prompts in house style with analyst_notes" |

For commits prior to 2026-06-06, see the 2026-05-26, 2026-05-27, and 2026-05-28 evaluator-review blocks above.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-06T14:12:49Z** (commit 072c89d, class: prompt-change — house-style rewrite of `task.json.instruction` and authoring of `analyst_notes`). `analyst_notes` itself is agent-invisible, but the instruction text was rewritten in the same commit so the cutoff still moves.
- Prior cutoff was 2026-05-17T12:15:58Z (full redesign). Between then and 072c89d, only path-only / evaluator-artefact / versioning-system commits landed; none semantic.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T16:24:48Z | 1.0 | done | stale (pre-2026-06-06 rewrite) |
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T19:27:04Z | 1.0 | done | stale |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:25:13Z | 1.0 | done | stale |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T23:32:30Z | 1.0 | done | stale |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:09:37Z | 1.0 | done | stale |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T09:02:31Z | 1.0 | done | stale |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:53:06Z | 1.0 | done | stale (still pre-rewrite at 14:12:49Z) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:29:23Z | 1.0 | done | stale |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:34:10Z | 1.0 | done | stale |

Footnote — older stale runs (pre-2026-05-17 redesign) remain discarded as before. All seven post-2026-05-28 runs all scored 1.0 under the pre-rewrite instruction, across Anthropic Opus 4.7, DeepSeek V4 Pro, and Google Gemma 4 26B (three model families). The 2026-06-06 house-style rewrite preserved every factual constraint of the prior instruction (no CRS, same output schema, same persona framing), so prior pass/fail outcomes are very likely to carry across; but this is *expectation*, not evidence, and the prompt's cutoff rules treat the runs as `stale`.

#### Verdict
**insufficient-evidence**

The 2026-06-06 commit moved the design-affecting cutoff to 2026-06-06T14:12:49Z. Zero `current` runs exist after that timestamp; the most recent run (run-20260606-1334Z) started at 13:34:10Z and predates the rewrite by ~38 minutes. Per the prompt's rules for `insufficient-evidence`, fewer than 2 current runs disqualifies a calibration verdict.

That said, there is **no positive reason to suspect a regression**:
- The 2026-06-06 rewrite is a pure register/sentence-shape change. It preserves the persona ("for the Horizon report"), the named output filename (`borough_areas.csv`), the column set (id, name, area), the `area_km2` semantics ("the area in km²"), and the identity-key statement ("use the `id` field to identify each borough"). It does **not** name a CRS, mention reprojection, mention `.area`, or otherwise leak the hidden gotcha. `analyst_notes` is agent-invisible.
- All seven pre-rewrite current-equivalent runs (post the 2026-05-17 redesign) scored 1.0 across three independent model families. The skill being tested is unchanged.
- This audit re-ran the grader on the reference: **1.0** (5/5 subchecks). All five broken sets still score exactly as `metadata.yaml > broken_solutions > measured_score` declares (wrong_format 0.0, degrees_area 0.6, area_m2 0.6; legacy wrong_crs 0.0, area_units 0.0). No drift.
- pytest (benchmark/eval): 41 passed.

**Output-CRS / format consistency (2c-CRS):** unchanged. Output is CSV with scalar `area_km2` — geometry-free, no output CRS to pin, no reprojection performed by the grader. README, `expected_outputs[]`, and reference all agree.

**Cross-axis consistency:** task.json `tags` (`crs: [EPSG:4326]`, `operations: [area_calculation]`, `formats: [geojson, csv]`, `themes: [divisions.division, boundary_administrative]`, `scale: small`) line up with the inventory row and with `coverage.yaml`.

The verdict is `insufficient-evidence` mechanically but the expectation is that the next round of runs against version 2 will continue to score as before.

#### Specific findings
- Verdict: **insufficient-evidence** (purely from the run-vs-cutoff arithmetic; no positive concern about the rewrite).
- **Missed `version` bump on commit 072c89d.** That commit edited `task.json.instruction` (per Step 4's bump-required list) but did not add or bump the `version` field, so `task.json` carried implicit-v1 content under v2 semantics. This audit adds `"version": 2` to `task.json` to make the content fingerprint consistent with the new instruction. The recorded `task_version: 1` in run.json files for the post-072c89d 2026-06-06 runs (run-20260606-0953Z / 1129Z / 1334Z) is incorrect — those runs received the rewritten instruction but report v1. That is a per-run-recording artefact (the runs predate any version field appearing in task.json) and not something this audit can amend retroactively; surfacing it as a low flag.
  <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" -->
  Low-severity note: commit 072c89d should have bumped `version` to 2 in the same commit per the policy in `task-evaluator-prompt.md` Step 4. This audit applies the bump as a follow-on unilateral edit. Three post-072c89d runs from 2026-06-06 morning recorded `task_version: 1` against what was effectively v2 instruction text; the eval UI will treat them as outdated once v2 is present, which is the correct behaviour going forward.
- HR-002 (carried forward, reference-or-data-edit-needed, low): legacy broken-solution directories `reference/failures/broken_wrong_crs/` and `reference/failures/broken_area_units/`, plus stray `reference/solution/outputs/boroughs_laea.geojson`, are residue from the pre-2026-05-17 prompt version. The evaluator is not permitted to delete files under `reference/failures/` or `reference/solution/outputs/`. Author should delete all three in a follow-up commit. Already in the author's "Open issues" list and surfaced by every prior evaluator pass.
  <!-- HUMAN-REVIEW id="HR-002" category="reference-or-data-edit-needed" severity="low" -->

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `"version": 2`. Reason: commit 072c89d rewrote `task.json.instruction` (a bump-required class per Step 4) but missed adding the version field; this restores the content-fingerprint invariant. Re-grade on reference: **1.0** (5/5 subchecks).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — note that commit 072c89d should have bumped `version`. Bump now applied; flag is a heads-up to the human reviewing the 2026-06-06 batch.
- HR-002 — reference-or-data-edit-needed — legacy broken dirs `broken_wrong_crs/`, `broken_area_units/`, and stray `boroughs_laea.geojson` should be deleted by a human (already in author's Open issues list).

#### Tests run
- grader on reference (`benchmark/tasks/crs-l1-london-laea-areas/reference/solution/outputs`): **1.0** (5/5 subchecks).
- grader on each broken set: wrong_format 0.0, degrees_area 0.6, area_m2 0.6; legacy wrong_crs 0.0, area_units 0.0 — all match metadata.
- pytest (benchmark/eval): 41 passed, 0 failed.

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Row-count-within-5%-of-reference check migrated from Gate 2 to a new
  `row_count_within_5_percent` subcheck (was not already covered).
- Subcheck count grew from 5 to 6.

### Verification
- Reference solution re-graded: 1.0 (6/6 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior reviews. First version (commit 1dc5019) explicitly named EPSG:3035; the 2026-05-17 redesign (fbf3b26) stripped all CRS guidance and changed the output to a plain CSV `id,name,area_km2` so the task probes **unprompted CRS reasoning**. Persona Sophia Marchetti at UCL preparing a Horizon-report land-area table is unchanged.

#### Change log (new commits since the 2026-06-06 review)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | d444e7d | docs-change (+version field) | Prior evaluator review: appended 2026-06-06 block, refreshed coverage.yaml + status.json, added `"version": 2` to task.json (the bump 072c89d missed) | Commit msg: "Re-evaluate crs-l1-london-laea-areas: insufficient-evidence; bump version to 2" |
| 2026-06-06 | 363aed2 | grader-change | Dropped the `structural_correctness` gate; the row-count-within-5% check migrated from Gate 2 to a new `row_count_within_5_percent` subcheck (subchecks 5 → 6). No version bump in this commit (v2 retained) | Commit msg: gate was inconsistent across the 36 graders; library now has a single hard `format_schema_valid` gate, salvageable checks become subchecks |
| 2026-06-07 | 05b389b | grader-change | Re-tagged five data-content subchecks (row count, id set, per-feature area, total area, name) with `weight=3.0`; `area_column_is_numeric` stays weight 1.0. Max score basis is now 16 points. No version bump in this commit (v2 retained) | Commit msg: "so a clean-schema-wrong-data submission scores visibly lower than a correct-data slightly-off-schema one" |
| 2026-06-09 | ec540aa | prompt-change | Restored the exact column name in the instruction: "id, name, and area" → "id, name, and area_km2". version 2 → 3 | Commit msg: the 072c89d house-style rewrite softened the column name; models wrote `area` and failed `format_schema_valid` |
| 2026-06-09 | 2740c77 | prompt-change | Broadened "every borough" / "one row per borough" to "every administrative unit (both the borough-level `county` features and the surrounding `locality` features)" / "one row per feature". version 3 → 4 | Commit msg: reference contains all 232 features; a literal reading made the model filter to the 33 boroughs and lose two weight-3 subchecks despite perfect per-id area math |

Note: 363aed2 and 05b389b were grader changes that did not bump `version` in the same commit (the bump policy would have asked for one). The omission is moot in practice: both landed under v2 and the subsequent v3/v4 bumps now correctly mark every pre-2740c77 run as outdated. No HR flag raised; there is nothing left for a human to do.

For commits prior to 2026-06-06, see the earlier evaluator-review blocks.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-09T12:37:28Z** (commit 2740c77, class: prompt-change, version 4).

#### Runs considered
| Run | Adapter | Task started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T17:33:26Z | 0.0 | done | stale (v2; wrote `area` column, Gate-1 fail — the failure ec540aa fixed) |
| run-20260607-112405Z | openrouter-gemma4-26b-detailed | 2026-06-07T11:24:05Z | — | cancelled | stale (v2, cancelled) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T11:24:30Z | 1.0 | done | stale (v2) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-09T06:46:47Z | 0.4375 | done | stale (v3; filtered to the 33 `county` boroughs — the failure 2740c77 fixed) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T18:09:08Z | 1.0 | done | **current** (see note) |

Validity note for run-20260609-084636Z: `run.json > invocation.suite_git_sha` is ec540aa (a v3 tree), which under the strict suite-sha reading would mark the run stale. But the suite sha is recorded at run launch (08:46Z) and this task started 18:09Z, after 2740c77 landed; the harness loaded the live tree, the per-task record says `task_version: 4`, and the output contains all 232 rows (responsive to v4's "every administrative unit" wording, where the v3 prompt produced 33-row outputs). Counted as `current` on that direct evidence. Older runs (pre-2026-06-06) remain stale as established by prior reviews.

#### Verdict
**insufficient-evidence**

Only one `current` run exists (run-20260609-084636Z, DeepSeek V4 Flash, score 1.0), and it is a single model family; the rubric requires at least 2. There is no positive reason to suspect mis-calibration: the current run's CSV matches the reference closely (232/232 ids, max per-feature relative area difference 0.052%, all names preserved, totals within 0.03%), and the v3/v4 prompt fixes responded to real, well-understood failure shapes (column named `area`; borough-only filtering) that the diffs show were prompt-side defects, not grader defects. Re-verified this audit: reference grader score **1.0** (6/6 subchecks, 16/16 points); broken sets wrong_format 0.0, degrees_area 0.625, area_m2 0.625 (both inside their declared [0.5, 0.7] ranges; metadata.yaml measured_score refreshed from the stale pre-weighting 0.6); legacy wrong_crs 0.0, area_units 0.0. pytest: 41 passed.

**Output-CRS / format consistency (2c-CRS):** unchanged from prior reviews. Output is a geometry-free CSV with scalar `area_km2`; no output CRS to pin, no reprojection in the grader (scalar-vs-scalar comparison). README, `expected_outputs[]`, and reference agree: CSV.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `borough_areas.csv`, CSV | instruction | stated |
| columns `id`, `name`, `area_km2` | instruction ("its id, name, and area_km2") | stated |
| all 232 features, both subtypes | instruction (parenthetical naming `county` and `locality`) | stated |
| `id` is the identity/join key | instruction ("Use the `id` field to identify each feature") | stated |
| area in km² | instruction ("area in km²") | stated |
| per-feature area within 2% of reference | grader-internal tolerance | inferable (standard drift margin; any reasonable projected CRS for London lands well inside it) |
| total area within 2% | grader-internal | inferable (follows from per-feature correctness) |
| `area_km2` numeric dtype | nowhere explicit | inferable (an area column is a number) |
| must compute area in a projected/metric CRS | deliberately omitted | inferable from the input's WGS84 metadata plus domain expertise; this is the skill under test |

Factual claims checked: column names, units, output filename, and the `county`/`locality` subtype split (33/199 of 232 features) all verified against `inputs/london_admin_wgs84.geojson` and the reference output. One mismatch: the instruction references **`london_admin.geojson`** but the staged workspace file is **`london_admin_wgs84.geojson`** (the eval runner uploads by real basename, `eval/core/runner.py` uses `fpath.name`). See HR-001.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads the bundled GeoJSON, reprojects to EPSG:3035 (LAEA Europe, an appropriate equal-area choice for area computation), computes area in km², and writes all 232 rows with exactly `id,name,area_km2`. The only operation the prompt does not request is a deterministic name+id row sort, which exists so regeneration is reproducible; the grader merges on `id` and is row-order-insensitive, so it imposes nothing on the agent. Not flagged.

#### Specific findings
- Verdict: **insufficient-evidence** (one current run; single model family). No grader or tolerance problem found; recommend simply accumulating v4 runs.
- The instruction names the input as `london_admin.geojson`, but the file the agent actually finds in its working directory is `london_admin_wgs84.geojson`. The mismatch dates to the 072c89d house-style rewrite (the pre-rewrite instruction said "the supplied london_admin file"). Agents have coped so far by listing the workspace (the only GeoJSON present), but it is an inaccurate factual claim, and fixing it is a design call: correcting the instruction to `london_admin_wgs84.geojson` puts the WGS84 cue into the prompt text (the cue already exists on disk, so this is mild), while renaming the bundled file to `london_admin.geojson` removes the filename cue entirely and makes the hidden gotcha harder (a data edit the evaluator may not make, requiring input + reference regeneration + version bump). <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> Human must pick one: (a) fix the filename in the instruction, or (b) rename `inputs/london_admin_wgs84.geojson` to `london_admin.geojson` (and update `task.json.inputs[].url`, `_prepare.py` reference docs, regenerate nothing else since content is unchanged) plus bump `version` to 5. Option (b) is truer to the task's "no hints" design.
- HR-002 (carried forward, reference-or-data-edit-needed, low): legacy broken-solution directories `reference/failures/broken_wrong_crs/` and `reference/failures/broken_area_units/`, plus stray `reference/solution/outputs/boroughs_laea.geojson` (and its copy inside `broken_wrong_format/outputs/`), are residue from the pre-2026-05-17 prompt version and should be deleted by a human. Flagged by every evaluator pass since 2026-05-26. <!-- HUMAN-REVIEW id="HR-002" category="reference-or-data-edit-needed" severity="low" -->
- `metadata.yaml > broken_solutions > measured_score` for degrees_area and area_m2 was stale (0.6, the pre-weighting 3/5 value); both now measure 0.625 (10/16) under the 05b389b weighted grader. Refreshed unilaterally; expected ranges still hold.
- README had three stale statements (pre-reorg `data/` path, `outputs/` prefix on the deliverable, and a reference to the removed "Gate 2 row-count check"). Fixed unilaterally (docs-change).
- `analyst_notes.pitfalls` did not mention the borough-only filtering failure that run-20260608-074701Z actually hit and that 2740c77 patched the prompt against; added one pitfall sentence and updated "original boroughs" to "original admin units". analyst_notes is agent-invisible; no version bump.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: measured_score 0.6 → 0.625 for degrees_area and area_m2 (re-measured under the weighted grader). Re-grade on reference: 1.0. Reason: stale post-05b389b values.
- `README.md`: `data/` → `inputs/` path, dropped stale `outputs/` prefix, replaced removed "Gate 2 row-count check" with the current subcheck names. Reason: docs drifted behind the 2026-05-26 reorg and 2026-06-06 gate refactor.
- `task.json` (`analyst_notes` only): added the borough-filtering pitfall observed in run-20260608-074701Z; "original boroughs" → "original admin units". Re-grade on reference: 1.0. Reason: notes refresh after the 2740c77 reframing; agent-invisible, no version bump.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — instruction says `london_admin.geojson`; staged file is `london_admin_wgs84.geojson`. Human picks: fix the instruction filename, or rename the input (truer to the no-hints design) and bump version.
- HR-002 — reference-or-data-edit-needed — delete legacy `broken_wrong_crs/`, `broken_area_units/`, and stray `boroughs_laea.geojson` artefacts (carried since 2026-05-26).

#### Tests run
- grader on reference: 1.0 (6/6 subchecks, 16/16 weighted points)
- grader on broken sets: wrong_format 0.0, degrees_area 0.625, area_m2 0.625, legacy wrong_crs 0.0, legacy area_units 0.0
- pytest: pass (41 passed)

#### HR-001 resolution (2026-06-11)
Human decision: renamed `inputs/london_admin_wgs84.geojson` to `inputs/london_admin.geojson` so the instruction's filename claim is accurate and the wgs84 cue is removed from the filename. Version bumped to 5. Applied by a delegated agent.

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change
Per-task **reasoned subcheck reweighting**, replacing the blunt one-size-fits-all
`weight=3.0`-on-all-content-subchecks scheme that commit 05b389b (2026-06-07)
applied repo-wide. Grading-only change: no `task.json.version` bump, no
threshold/gate/check-logic change, only `weight=` values edited in `grade.py`.

This is a CRS-category task where the central skill is **unprompted CRS
reasoning** — recognising that WGS84 `.area` is meaningless and reprojecting to
a metric CRS before computing area. The output is a geometry-free CSV, so there
is no CRS-metadata-declaration label to game; the checks that *prove the
reprojection actually happened* are the per-feature and total area comparisons.
Per the operator directive, those proof-of-reprojection checks are weighted to
dominate the score, while structural/attribute/cosmetic checks are down-weighted.

### Weight changes
| Subcheck | old | new | rationale |
|---|---|---|---|
| `area_km2_per_feature_matches` | 3.0 | **5.0** | central proof-of-reprojection; both target failures fail exactly here |
| `total_area_within_2_percent` | 3.0 | 3.0 (unchanged) | corroborating proof-of-reprojection; partly redundant with per-feature |
| `feature_id_set_preserved` | 3.0 | **2.0** | structural (join-key preservation), secondary to the CRS skill |
| `row_count_within_5_percent` | 3.0 | **1.0** | structural; redundant with the id-set check |
| `name_attribute_preserved` | 3.0 | **1.0** | attribute preservation, not the CRS skill |
| `area_column_is_numeric` | 1.0 | **0.5** | cosmetic dtype check |

Weight budget: 5.0 + 3.0 + 2.0 + 1.0 + 1.0 + 0.5 = **12.5**.

### Broken scores before → after
| Broken | before | after | severity note |
|---|---|---|---|
| `wrong_format` | 0.00 | 0.00 | catastrophic — wrong output format, hard-gate fail (most severe) |
| `degrees_area` | 0.625 | **0.36** | canonical CRS-reasoning failure (area in degrees²); now drops meaningfully — fails the two proof-of-reprojection checks (5.0+3.0 of 12.5) |
| `area_m2` | 0.625 | **0.36** | same proof-of-reprojection failure shape (m² not km²) |
| legacy `wrong_crs` | 0.00 | 0.00 | no `borough_areas.csv` (pre-2026-05-17 residue; uninformative) |
| legacy `area_units` | 0.00 | 0.00 | no `borough_areas.csv` (pre-2026-05-17 residue; uninformative) |

Ordering is now sensible and monotone: a central CRS mistake (proof-of-reprojection
checks failing) drops the score to 0.36, distinctly below a correct run (1.0);
a wrong-output collapse goes to 0.0; an isolated cosmetic dtype slip would cost
only 0.5/12.5 = 0.04, and an isolated structural slip (name or row count) only
1.0/12.5 = 0.08. No disjoint-failure inversion: the two area-failure brokens
(which fail exactly the high-weight area pair and nothing else) are correctly the
lowest non-zero score.

### Prior-run re-grade
Only one `current` run exists at the live task version (v5; v4 is comparable —
the v4→v5 bump was a file-rename-only change with no semantic effect):
`run-20260609-084636Z` (DeepSeek V4 Flash, recorded 1.0). Re-graded under the new
weights: **1.0 → 1.0** (perfect CSV, all subchecks pass; weight changes do not
affect an all-pass run). No notable shifts.

### Reasoning
The central skill — proving the reprojection happened — is concentrated in
`area_km2_per_feature_matches` (every feature's area is correct in km²) with
`total_area_within_2_percent` corroborating. Up-weighting per-feature to 5.0 and
keeping total at 3.0 makes those two carry 8 of 12.5 points, so failing them (the
exact failure shape of both target brokens) costs 0.64 of the score. The
remaining structural checks (id set, row count, name) and the cosmetic dtype check
are genuinely secondary to the CRS skill and so carry low weight. A file that
preserves schema/ids/names perfectly but never transformed coordinates (or botched
the unit) now scores 0.36 — it can never approach or exceed an honest, correctly
reprojected file. This satisfies the directive that CRS correctness dominate via
the proof-of-reprojection checks rather than any metadata label.

#### Threshold note (no change made)
The two area checks share the same 2 % tolerance and the per-feature check uses a
0.95 pass-rate floor; the total-area check is essentially implied by per-feature
correctness, so the two are partially correlated rather than independent signals.
I left thresholds untouched per the grading-only constraint and kept total at 3.0
(below per-feature's 5.0) to avoid double-counting the same underlying evidence.

#### HR
HR-002 (legacy broken-dir cleanup) is unrelated to weighting and is retained. No
grader-miscalibration HR existed in status.json to drop (the 05b389b 3x weighting
was never flagged here as a pending HR item).

### Changes applied this run
- `grade.py`: subcheck `weight=` values only (table above). Re-grade on reference: **1.0**.
- `metadata.yaml`: `degrees_area` / `area_m2` `measured_score` 0.625 → 0.36; `expected_score_range` [0.5, 0.7] → [0.3, 0.45]; added weight-arithmetic prose to the broken descriptions.
- `README.md`: no edit (contains no score fractions or weight prose).
- pytest: not run (orchestrator runs the suite).
