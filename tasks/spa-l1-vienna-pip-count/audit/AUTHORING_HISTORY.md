# Implementation notes — spa-l1-vienna-pip-count

## Prompt version
2026-05-07-a

## Status
completed

## Summary
L1 spatial_analysis task: point-in-polygon count of 49 monitoring
stations against 23 Vienna Bezirk polygons (both bundled in
EPSG:31287 GeoJSON). The agent must emit a CSV listing every Bezirk
with its station count — including the four Bezirke with zero
stations. Reference, grader, and three broken solutions built and
verified inside the project Docker container.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0])
  - inner_join: 0.600 (expected range [0.50, 0.70])
  - name_used_id: 0.800 (expected range [0.70, 0.90])
- Second-run output match: bit-identical (CSV has no embedded
  timestamp; reference output is sorted by `district_code` and the
  Overpass `[date:"2026-05-01T00:00:00Z"]` directive pins the upstream
  OSM state)
- Library tests after task: pass (32/32)

## Failure-mode coverage
- Inner join drops zero-count districts: broken_inner_join
- Wrong attribute pulled into district_name (OSM relation id): broken_name_used_id
- Missing `station_count` column: broken_wrong_format (Gate 1)
- Wrong CRS / lat-lon point arithmetic: principled — per-row
  station_count_per_row_match and station_count_total_match degrade
  together when stations land outside Vienna or in the wrong Bezirk
- `intersects` instead of `within`: not-handled — by design.
  Equivalent on points strictly inside polygons; the bundled inputs
  are constructed so the distinction doesn't change the answer
- Constant station_count filler (e.g., 49 per row): principled —
  station_count_total_match (49 × 23 = 1127 ≠ 49) and per-row checks
  both fail
- station_count as int-valued float (`6.0`): not-handled — by design.
  The grader's `_coerce_int` helper accepts int-valued floats since
  the persona doesn't care about CSV-side dtype tagging

## Open issues
- [severity: low] — Bundled inputs come from OSM Overpass rather than
  Overture. Verified at authoring time that Overture release
  2026-04-15.0's Vienna divisions cannot supply the 23 statutory
  ``Gemeindebezirke`` cleanly: a probe over the Vienna bbox returned
  76 ``subtype='macrohood'`` rows mixing sub-Bezirk locales
  (Spittelberg, Schottenfeld), ``Katastralgemeinden`` ("KG ..."), and
  miscellaneous neighborhoods, while excluding six whole Bezirke
  (Wieden, Neubau, Alsergrund, Rudolfsheim-Fünfhaus, Döbling,
  Donaustadt). OSM's ``boundary=administrative admin_level=9`` under
  Vienna gives the canonical 23 with the Bezirk number in `ref` and
  the German name in `name`. The inventory's OSM-tag axis explicitly
  lists `boundary=administrative` so this fall-back is in scope per
  ``docs/AUTHOR_CONTEXT.md`` ("Fall back to OSM Overpass or Geofabrik
  *only* when the task is intrinsically about an OSM tag family with
  no Overture equivalent"). Recorded here so the orchestrator can
  audit the substitution.

- [severity: low] — Monitoring stations also come from OSM
  (`man_made=monitoring_station`) since Overture has no monitoring-
  station equivalent in `places.place` or any other type. The
  inventory's OSM-tag axis row references `place=*` for "district
  markers" — that's only 23 settlement-marker points (one per Bezirk),
  not 49 monitoring stations — so I read the inventory's intent as
  "OSM is the canonical source for both layers" and used `man_made=
  monitoring_station` for the points, which matches the persona's
  story (air-quality monitoring stations) more directly than
  `place=*`.

- [severity: low] — Gate-2 row-count tolerance is ±25%, intentionally
  wider than the L1 default ±5%. Documented in `metadata.yaml >
  tolerances > rationale`. The wider gate is what gives
  ``broken_inner_join`` (19 / 23 = 17% off) partial credit instead of
  collapsing to 0; without it, the grader can't distinguish "agent
  did the join but skipped the zero-count handling" from "agent did
  nothing useful."

## Suggested prompt changes
(none)

## Inventory change proposals
(none — inventory's primary op (point-in-polygon count), EPSG:31287
input, GeoJSON-in / CSV-out formats, "Small (~10² stations, 23
districts)" data scale, and the persona / story are all met as
written. The task uses 49 stations rather than ~100; 49 is in the
~10² order of magnitude and matches OSM's actual Vienna monitoring-
station count at the pinned Overpass timestamp — synthesising 51
extra stations to hit a round 100 would have been less realistic and
wouldn't have changed the GIS skill probed.)

## Library extensions
(none — task uses `jaccard_similarity_set` from the shared library;
the per-row attribute and count loops in `grade.py` are inlined for
the same reason as `spa-l1-paris-amenity-within`'s grader: each takes
a different per-row predicate and would not pay back as a new shared
helper without first agreeing on a per-feature aggregation contract,
out of scope here.)

## Runtime
~30 minutes (peer task `spa-l1-paris-amenity-within` provided the
task structure, broken-solution authoring template, and grader
skeleton; the only authorial detour was discovering that Overture
release 2026-04-15.0 doesn't expose the 23 Vienna Bezirke cleanly,
which pushed the bundled-input source from Overture to OSM Overpass
mid-authoring. The Overpass relation-to-polygon assembly took one
iteration — the first ring stitcher only checked the most recent ring
for adjacency and failed on all 23 Vienna Bezirk relations; the
rewritten greedy-pool stitcher closes rings correctly. Ring-stitching
code could be refactored into a shared utility if more OSM-Overpass
tasks get authored, but that's a future-task concern.)

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The inventory row defines `spa-l1-vienna-pip-count` as an L1 spatial-analysis
task: point-in-polygon count of monitoring stations against Vienna's 23
Bezirke, both bundled GeoJSON in EPSG:31287 (MGI / Austria Lambert), with a
plain CSV deliverable carrying `district_code, district_name, station_count`
sorted by `district_code`. The persona Ana Brković needs a "coverage
diagnostic" — under-monitored districts must surface — so the design beat is
not just the spatial join itself but the left-join-back so that zero-count
districts also appear. The first commit recovered the task from a parallel
authoring branch with this contract intact: 49 stations / 23 districts,
five binary subchecks plus two gates, three broken classes (`wrong_format`,
`inner_join`, `name_used_id`) calibrating Gate 2 row-count tolerance to ±25%
so the canonical 19-row inner-join failure lands in the partial-credit band.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Recovered task from `tasks-run-2026-05-08-a` branch (task.json, grade.py, metadata, reference solution, three brokens, README/IMPLEMENTATION_NOTES, prepare-input script, bundled GeoJSON inputs) | Commit msg: "recovered" — task migration from parallel branch |
| 2026-05-08 | 001e459 | docs-change | benchmark/ split into authoring/ and eval/ subtrees (path-only) | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ to benchmark/tasks/ (path-only) | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 9b1fb11 | prompt-change | Reflowed instruction: prose-merged the "Output schema" bullet block back into running prose. Persona voice, column names, sort order, "zero-count districts must appear" all retained. | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` via FLUX schnell | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` via nano-banana-2 | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped "(both MGI Lambert)" CRS hint and the "all 23 must be present" feature-count nudge from instruction. Kept "zero-count districts" hint, persona, column names, sort. | Commit msg: "Strip deducible information from SPA task instructions — Remove input CRS mentions, geometry type descriptions, feature counts, specific data value examples, and data quality issue details that the model should discover from file metadata. Keep all output requirements, narrative framing, and genuine design decisions." |
| 2026-05-17 | 7f31f98 | prompt-change | Removed "districts with zero stations must still appear" explicit clause and the "1 through 23 — not the OSM relation id and not a 1010/1020 postal code" / Bezirk-name examples. Persona / "every Bezirk" wording / column names kept. | Commit msg: "Remove nudges from 6 spatial-analysis task prompts — Strip CRS codes, operation names, and explicit hints from instruction text while preserving output specs, column names, and unit requirements." |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + grader-change path-only) | Layout reorg: IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, data/ -> inputs/, reference/ split into solution/ + failures/, image* -> assets/. `grade.py` only had its `REFERENCE_OUT` path constant updated; logic unchanged. | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06+00:00 (commit `7f31f98`, class: prompt-change — "Remove nudges from 6 spatial-analysis task prompts"). The 2026-05-26 layout-reorg commit `29a9ae3` only renamed files and updated the reference path; the grader logic, instruction text, inputs, reference outputs, and broken outputs are byte-identical to their pre-reorg counterparts, so it is not design-affecting for run validity.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T14:12:56Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-05-17T18:56:28Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T09:14:29Z | 1.0 | done | current |

Stale runs (pre-cutoff, considered but not used as evidence): all earlier runs from `run-20260512-…` through `run-20260517-0614Z`. They predate the latest prompt-change so they do not test the current instruction.

#### Verdict
**calibrated**

The three current runs come from three model families of clearly different overall capability — claude-opus-4-6 (strong), deepseek-v4-flash (mid), and gemma-4-26b-a4b-it (weaker; scores 0 on `crs-l2-fiji-antimeridian`, `crs-l3-tokyo-jgd-crossings`, `dc-l2-lagos-snap-normalize`, `dd-l2-tokyo-overture-schools`, `geo-l1-capetown-building-centroids`, etc. on the same run set). All three solve this L1 task perfectly. That is the expected discrimination profile for an L1 single-op task on fully bundled metric-CRS GeoJSON: a competent agent that can do a within-join, group-by-count, and a left-join-back onto the full polygon set should pass. The instruction post-strip retains "listing every Bezirk", "one row per Bezirk", "coverage diagnostic", and the persona's "spot under-monitored areas at a glance" — together these still telegraph the left-join-back beat without ever literally naming "zero-count districts", which is the right calibration for L1 (the agent has to read the persona and infer the contract, not pattern-match a literal sentence). The reference grader scores 1.0; broken solutions score 0.0 / 0.6 / 0.8 verbatim against `metadata.yaml`'s declared ranges. Gate 2 tolerance ±25% still does its job: the inner-join 19-row failure mode lands at 0.6, not 0.0.

#### Specific findings
- All three current runs produced a 23-row, fully-correct CSV with the exact reference values for `district_name` and `station_count`. No agent dropped a column, no agent inner-joined, no agent pulled the relation id into `district_name`. This is consistent with a well-bundled L1 task, not with an over-specified prompt — see the change-log entry for `7f31f98` showing the literal "zero-count districts must appear" gift was already stripped a week before any of these runs started.
- Cross-axis consistency: inventory says GeoJSON-in / CSV-out, EPSG:31287, Point + Polygon, OSM tags `place=*` + `boundary=administrative`, scale "Small (~10² stations, 23 districts)". `task.json.tags`, `metadata.yaml`, `README.md`, and the bundled inputs all agree. Note however that the inventory's OSM-tag axis says `place=*` for the "district markers" but the actual implementation uses `boundary=administrative admin_level=9` for the polygons and `man_made=monitoring_station` for the points; this is explicitly documented under "Open issues" in the author block of `AUTHORING_HISTORY.md` and justified there (`place=*` would give 23 settlement-marker points, not 23 district polygons). I treat this as a fully-disclosed substitution rather than an inventory mismatch: the design intent is to exercise the OSM "administrative boundary" tag family, which the vocabulary slug `boundary-administrative` covers. The `place=*` row of the inventory's OSM-tag axis still claims this task as its sole hit, which is a documentation accuracy issue at the inventory level rather than a task issue. Not flagged.
- Reference solution outputs match `reference/solution/outputs/stations_per_district.csv` byte-for-byte across all three current runs — the Overpass `[date:"2026-05-01T00:00:00Z"]` pin and the int-keyed deterministic sort make this expected, not suspicious.
- No model-side failures (no timeouts, no oversized queries) on the current runs. All three completed under 60 s.

### 3. Changes applied this run

#### Unilateral edits
(none — task is well-calibrated; no tolerances, prompt, or metadata fields needed adjustment)

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.00
- grader on `broken_wrong_format`: 0.00 (expected [0.0, 0.0])
- grader on `broken_inner_join`: 0.60 (expected [0.50, 0.70])
- grader on `broken_name_used_id`: 0.80 (expected [0.70, 0.90])
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The inventory row (`benchmark/authoring/inventory.md`, "Category: spatial_analysis" >
`spa-l1-vienna-pip-count`) defines this as an L1 spatial-analysis task: a
*point-in-polygon count* of Vienna air-quality monitoring stations against the
city's 23 statutory Bezirke, both bundled as GeoJSON in EPSG:31287 (MGI / Austria
Lambert), output as a plain CSV with `district_code, district_name, station_count`
sorted by `district_code`. The persona Ana Brković (Umweltbundesamt) wants a
*coverage diagnostic* so the funding committee can spot under-monitored Bezirke —
which makes the design beat not the spatial join alone but the *left-join-back*
so that zero-count districts also appear in the output. The first commit recovered
the task (with `spa-l1-paris-amenity-within`) from a parallel authoring branch with
the contract intact: 49 stations / 23 districts, two gates + five binary subchecks,
three broken classes (`wrong_format`, `inner_join`, `name_used_id`), and a Gate-2
row-count tolerance of ±25% so the 19-row inner-join failure lands in the
partial-credit band rather than collapsing to zero.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Recovered task from a parallel authoring branch: `task.json` (incl. instruction with the explicit "(both MGI Lambert)" CRS hint and "districts with zero stations must still appear" clause), `grade.py`, `metadata.yaml`, reference solution + outputs, three brokens, README/notes, `_prepare.py`, bundled GeoJSON inputs | Commit msg: "task: … [recovered]" — migration from parallel branch |
| 2026-05-08 | 001e459 | docs-change | `benchmark/` split into `authoring/` and `eval/` subtrees (path-only) | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | 1710715 | prompt-change | Appended an explicit "Output schema" block to the instruction (file name, exact column names with "not the OSM relation id / not the 1010/1020 postal code" disambiguation, Bezirk-name examples, "all 23 Bezirke must be present"). Commit msg states no grader changes. | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | 284b843 | docs-change | Added the `tags` dict (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) to `task.json`; no instruction or grader change | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` (path-only) | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: "add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` | Commit msg: "generate image.webp for all 36 task directories" |
| 2026-05-13 | 9b1fb11 | prompt-change | Reflowed the instruction: prose-merged the bulleted "Output schema" block back into running prose. Column names, sort order, "all 23 must be present, including zero-count districts", and the disambiguation parentheticals all retained. | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` (FLUX schnell) | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` (nano-banana-2) | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped the "(both MGI Lambert)" CRS hint, the Bezirk-name examples / "1010/1020 postal code" / "1 through 23" specifics, replacing them with generic "the Bezirk number — not other identifier columns" and "from the districts layer". Kept the "zero-count districts must still appear / all districts must be present" clause, persona, column names, sort. | Commit msg: "Strip deducible information from SPA task instructions — Remove input CRS mentions, geometry type descriptions, feature counts, specific data value examples …" |
| 2026-05-17 | 7f31f98 | prompt-change | Removed the explicit "districts with zero stations must still appear" clause AND the "one row per Bezirk — all districts must be present, including zero-count districts" sentence. Replaced with "listing every Bezirk with its station count — the committee wants to spot under-monitored areas at a glance" and "one row per Bezirk". Persona, column names, sort order, the three exact column names retained. | Commit msg: "Remove nudges from 6 spatial-analysis task prompts — Strip CRS codes, operation names, and explicit hints …" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path-only grader edit) | Folder-layout reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/` split into `solution/` + `failures/`, image assets → `assets/`. `grade.py`'s only change is its `REFERENCE_OUT` path constant (`reference/outputs/…` → `reference/solution/outputs/…`); scoring logic byte-identical. | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 471f7c1 | docs-change | Prior evaluator review: added `audit/AUTHORING_HISTORY.md` block, `coverage.yaml`, `audit/status.json`. Verdict calibrated, no edits. | Commit msg: "Re-evaluate spa-l1-vienna-pip-count: calibrated, no edits" |

(Note: the directory-level `git log --follow` enumerated the design-affecting and reorg commits; the two early `task.json`-only commits `1710715` and `284b843` surfaced via a slug-scoped `git log -- '*spa-l1-vienna-pip-count*'` and are folded in above. The prior evaluator's change log omitted these two; they are docs/prompt commits dated 2026-05-13, well before the cutoff, so they do not affect run validity.)

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T12:49:06+00:00** (commit `7f31f98`, class: prompt-change — "Remove nudges from 6 spatial-analysis task prompts"). This is the most recent commit in any answer-key/instruction-affecting class. The 2026-05-26 reorg `29a9ae3` only renamed paths and updated `grade.py`'s `REFERENCE_OUT` constant; instruction text, grader logic, inputs, reference outputs, and broken outputs are byte-identical to their pre-reorg counterparts, so it is not design-affecting for run validity.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T14:12:56Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-05-17T18:56:28Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T09:14:29Z | 1.0 | done | current |

Stale runs (pre-cutoff, considered but not used as evidence): all `run-20260512-…` through `run-20260517-0614Z` runs that touched this task (haiku, sonnet ×2, opus ×7, deepseek-v4-flash ×2, tencent/hy3-preview — all 1.0 where they completed; several gemma attempts on 2026-05-13 failed/cancelled with `ConnectError`, a model-side / infra failure unrelated to the task). These predate the latest prompt-change `7f31f98`, so they do not test the current instruction.

#### Verdict
**calibrated**

Three `current` runs from three model families of clearly differing capability — claude-opus-4-6 (strong), deepseek-v4-flash (mid), gemma-4-26b-a4b-it (weaker; scores 0 on several harder tasks in the same 2026-05-26 sweep) — all solve this L1 task perfectly (1.0). That is the expected discrimination profile for an L1 single-op task on two fully bundled, same-metric-CRS GeoJSON layers: a competent agent that can do a `within` join, group-by-count, and a left-join-back onto the full polygon set passes. Crucially, the `too-easy` test is *not* met: it requires both (a) all current runs ≥0.95 *and* (b) an over-specified instruction. Condition (b) is false — the cutoff instruction (`7f31f98`) deliberately *removed* the literal "districts with zero stations must still appear" gift, leaving only the persona-level framing ("listing every Bezirk", "spot under-monitored areas at a glance", "one row per Bezirk"). The weakest model's solver (`run-20260526-0748Z/outputs/solve.py`) explicitly reasons "This means we should include districts that have 0 stations" and left-joins the count onto the full district list — i.e. it *inferred* the zero-count contract from the persona, it did not pattern-match a literal sentence. That is exactly the calibration intended for L1. The reference grader scores 1.0; brokens score 0.0 / 0.6 / 0.8 verbatim against `metadata.yaml`'s declared ranges; Gate-2 ±25% still lands the 19-row inner-join at 0.6 rather than 0.0.

#### Specific findings
- All three current runs produced a 23-row CSV with the exact `{1..23}` `district_code` set, total `station_count` = 49, and 0 name-diffs / 0 count-diffs versus `reference/solution/outputs/stations_per_district.csv`. No agent dropped a column, inner-joined, or pulled the relation id into `district_name`. Consistent with a well-bundled L1 task, not an over-specified one. No proposed change.
- Output-CRS / format consistency (Step 2c-CRS): the output is a non-spatial CSV with no geometry column. `expected_outputs[]` declares `format: csv, crs: null, geometry_type: null`; the reference output is a plain CSV; the README's output table matches. There is no CRS on the output side and the grader does no reprojection (it operates purely on tabular columns), so the one-sided-reprojection hazard does not apply. Consistent. No proposed change.
- Grader / metadata calibration verified by re-run this evaluation: reference 1.0 (5/5); `broken_wrong_format` 0.0; `broken_inner_join` 0.6; `broken_name_used_id` 0.8 — all inside the `metadata.yaml > broken_solutions > expected_score_range` bands and equal to the recorded `measured_score`s. No drift; no tolerance change warranted.
- Cross-axis / inventory consistency: `task.json.tags` (region vienna, formats geojson+csv, crs EPSG:31287, geometry point+polygon, operation pip_count, scale small), `metadata.yaml`, `README.md`, and the bundled inputs all agree. The bundled `districts.geojson` carries only `district_code / district_name / osm_relation_id`; `stations.geojson` carries only `station_id / name`; both declare EPSG:31287. The inventory's OSM-tag axis lists `place=*` (for "district markers") + `boundary=administrative`, but the *implementation* uses `boundary=administrative admin_level=9` relations for the polygons and `man_made=monitoring_station` nodes for the points — there is no `place=*` tag in the actual data and no vocabulary slug for `man_made`. This substitution is fully disclosed in the author block ("Open issues") with a documented rationale (Overture cannot supply the 23 statutory Bezirke cleanly; `place=*` would yield 23 settlement-marker points, not polygons). I treat it as a fully-disclosed, documented substitution rather than a fresh defect — the design intent (exercise the OSM administrative-boundary tag family, covered by slug `boundary-administrative`) is met. The `place=*` claim is an inventory-level documentation accuracy matter, not a task calibration problem. Recorded as a `coverage.yaml > notes` line; not flagged (no new evidence beyond what the author already disclosed).
- No model-side failures on the current runs (all completed quickly, no timeouts/oversized-query failures). The 2026-05-13 gemma `ConnectError`/cancelled attempts are stale infra failures, not task issues.

### 3. Changes applied this run

#### Unilateral edits
(none — the task is well-calibrated. Grader logic, tolerances, instruction, metadata, and reference/broken scores are all internally consistent and confirmed by the current runs. No tolerance, prompt, or metadata field needed adjustment.)

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.00 (5/5 subchecks)
- grader on `broken_wrong_format`: 0.00 (expected [0.0, 0.0])
- grader on `broken_inner_join`: 0.60 (expected [0.50, 0.70])
- grader on `broken_name_used_id`: 0.80 (expected [0.70, 0.90])
- pytest: pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The inventory row (`benchmark/authoring/inventory.md`, "Category: spatial_analysis" >
`spa-l1-vienna-pip-count`) defines this as an L1 spatial-analysis task: a
*point-in-polygon count* of Vienna air-quality monitoring stations against the
city's 23 statutory Bezirke, both bundled GeoJSON in EPSG:31287 (MGI / Austria
Lambert), output as a plain CSV with `district_code, district_name,
station_count` sorted by `district_code`. The persona Ana Brković
(Umweltbundesamt) wants a *coverage diagnostic* so the funding committee can
spot under-monitored Bezirke — making the design beat not the spatial join
alone but the *left-join-back* so that zero-count districts also appear in the
output. The first commit recovered the task (alongside `spa-l1-paris-amenity-
within`) from a parallel authoring branch with the contract intact: 49
stations / 23 districts, two gates + five binary subchecks, three broken
classes (`wrong_format`, `inner_join`, `name_used_id`), and a Gate-2 row-count
tolerance of ±25% so the 19-row inner-join failure lands in the partial-credit
band rather than collapsing to zero.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Recovered task from parallel authoring branch: `task.json` (with explicit "(both MGI Lambert)" CRS hint and "districts with zero stations must still appear" clause), `grade.py`, `metadata.yaml`, reference solution + outputs, three brokens, README/notes, `_prepare.py`, bundled GeoJSON inputs | Commit msg: "task: … [recovered]" — migration from parallel branch |
| 2026-05-08 | 001e459 | docs-change | `benchmark/` split into `authoring/` and `eval/` subtrees (path-only) | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema" block to instruction (filename, exact column names with "not the OSM relation id / not the 1010/1020 postal code" disambiguation, Bezirk-name examples, "all 23 Bezirke must be present") | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json`; no instruction or grader change | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` (path-only) | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: "add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` | Commit msg: "generate image.webp for all 36 task directories" |
| 2026-05-13 | 9b1fb11 | prompt-change | Reflowed instruction: bulleted "Output schema" block prose-merged back into running prose; column names, sort order, "all 23 must be present, including zero-count districts", and the disambiguation parentheticals all retained | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` (FLUX schnell) | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` (nano-banana-2) | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped "(both MGI Lambert)" CRS hint, Bezirk-name examples, "1010/1020 postal code" specifics, "1 through 23" enumeration — replaced with generic "the Bezirk number — not other identifier columns" and "from the districts layer". Kept "zero-count districts must still appear / all districts must be present" clause, persona, column names, sort. | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 7f31f98 | prompt-change | Removed explicit "districts with zero stations must still appear" clause and the "one row per Bezirk — all districts must be present, including zero-count districts" sentence; replaced with "listing every Bezirk with its station count — the committee wants to spot under-monitored areas at a glance" and "one row per Bezirk". Persona, column names, sort order, three exact column names retained. | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path-only grader edit) | Folder-layout reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/` split into `solution/` + `failures/`, image assets → `assets/`. `grade.py`'s only change: `REFERENCE_OUT` path constant; scoring logic byte-identical. | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 471f7c1 | docs-change | Prior evaluator review: appended `audit/AUTHORING_HISTORY.md` block, wrote `coverage.yaml`, `audit/status.json`. Verdict calibrated, no edits. | Commit msg: "Re-evaluate spa-l1-vienna-pip-count: calibrated, no edits" |
| 2026-05-27 | dd10686 | docs-change | Second evaluator review: appended block, refreshed `coverage.yaml`, `audit/status.json`. Verdict calibrated, no edits. | Commit msg: "Re-evaluate spa-l1-vienna-pip-count: calibrated, no edits" |
| 2026-05-28 | 622342b | docs-change (this task) | Repo-wide content-versioning rollout: introduces `task.json.version` and drops the unused `prompt_version` from `metadata.yaml`. This task's `metadata.yaml` had its `prompt_version: 2026-05-07-a` line removed; no `version` field has been added to `task.json` yet (the next evaluator unilateral edit will bump it from implicit-v1 → 2). Instruction, grader, inputs, reference, brokens, tolerances all unchanged. | Commit msg: "Add task content versioning; drop unused prompt_version" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T12:49:06+00:00** (commit `7f31f98`, class: prompt-change — "Remove nudges from 6 spatial-analysis task prompts"). This remains the most recent commit in any answer-key/instruction-affecting class. The 2026-05-26 reorg `29a9ae3` and the 2026-05-28 content-versioning rollout `622342b` are both docs-only for this task (path-renaming and a `prompt_version` field removal respectively); instruction, grader logic, tolerances, inputs, reference outputs, and broken outputs are byte-identical to their pre-reorg counterparts, so neither is design-affecting for run validity.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T14:12:56Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-05-17T18:56:28Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T09:14:29Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T23:04:10Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T01:00:49Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T03:07:17Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T04:12:46Z | 1.0 | done | current |

Stale runs (pre-cutoff, considered but not used as evidence): all `run-20260512-…` through `run-20260517-0614Z` runs that touched this task. They predate `7f31f98` so they do not test the current instruction. Several 2026-05-13 gemma attempts failed/cancelled with `ConnectError` — a model-side / infra failure unrelated to the task.

#### Verdict
**calibrated**

Seven `current` runs across three model families of clearly differing capability — claude-opus-4-6/4-7 (strong), deepseek-v4-flash (mid), gemma-4-26b-a4b-it (weaker; scores 0 on several harder tasks in the same sweeps) — all solve this L1 task perfectly (1.0). That is the expected discrimination profile for an L1 single-op task on two fully bundled, same-metric-CRS GeoJSON layers: a competent agent that can do a `within` join, group-by-count, and a left-join-back onto the full polygon set passes. The `too-easy` test requires both (a) all current runs ≥0.95 *and* (b) over-specified instruction — condition (b) remains false. The cutoff instruction (`7f31f98`) deliberately removed the literal "districts with zero stations must still appear" gift, leaving only persona-level framing ("listing every Bezirk", "spot under-monitored areas at a glance", "one row per Bezirk"). The four new opus + gemma runs (2026-05-27 and 2026-05-28) reproduce byte-identical reference outputs, confirming the prior evaluator's reading that the persona framing is sufficient cueing for L1 calibration. Reference grader 1.0; brokens 0.0 / 0.6 / 0.8 verbatim against `metadata.yaml`; Gate-2 ±25% still lands the 19-row inner-join at 0.6, not 0.0.

#### Specific findings
- All seven current runs produced a 23-row CSV with the exact `{1..23}` `district_code` set, total `station_count` = 49, and zero name-diffs / zero count-diffs versus `reference/solution/outputs/stations_per_district.csv`. Byte-identical for all four new runs since the prior evaluator review (verified via `diff`). No agent dropped a column, inner-joined, or pulled the relation id into `district_name`. Consistent with a well-bundled, well-cued L1 task. No proposed change.
- Output-CRS / format consistency (Step 2c-CRS): the output is a non-spatial CSV with no geometry column. `expected_outputs[]` declares `format: csv, crs: null, geometry_type: null`; the reference output is a plain CSV; the README's output table matches. There is no CRS on the output side and the grader does no reprojection (purely tabular checks), so the one-sided-reprojection hazard does not apply. Consistent. No proposed change.
- Grader / metadata calibration re-verified this run: reference 1.0 (5/5); `broken_wrong_format` 0.0 (Gate-1 missing-column); `broken_inner_join` 0.6 (3/5 subchecks); `broken_name_used_id` 0.8 (4/5 subchecks) — all inside `metadata.yaml > broken_solutions > expected_score_range` bands and equal to the recorded `measured_score`s. No drift; no tolerance change warranted.
- Instruction redundancy audit (Step 4 "tighten redundant statements" + "GeoJSON CRS strip"): the instruction contains no `EPSG`, `WGS84`, or `4326` token (output is plain CSV — neither rule applies); the persona-voice paragraph and the output-schema paragraph have no overlapping constraints (filename, column names, sort order, "every Bezirk" framing each appear in exactly one place). The schema-paragraph parentheticals ("integer-valued, the Bezirk number — not other identifier columns" and "the human-readable German Bezirk name from the districts layer") add identity-key disambiguation that `expected_outputs[]` does not encode (the column types are not declared there) — these are non-mutation invariants and must be kept per the prompt rules. No unilateral edit warranted.
- Cross-axis / inventory consistency: `task.json.tags`, `metadata.yaml`, `README.md`, and the bundled inputs all agree on region vienna, formats geojson+csv, CRS EPSG:31287, geometry point+polygon, operation pip_count, scale small. The OSM-tag substitution (inventory: `place=*` + `boundary=administrative`; implementation: `boundary=administrative admin_level=9` + `man_made=monitoring_station`) remains a fully-disclosed, documented choice in the author block. Captured under `coverage.yaml > notes` as before; not a fresh finding.
- Content-versioning rollout (`622342b`): the repo introduces `task.json.version`; this task currently has no `version` field, so it is implicit-v1. No unilateral edit is being made in this pass, so no version bump is required (the bump rule is "first unilateral edit in an evaluator pass that meaningfully changes prompt/grader/inputs"). The four new runs all record `task_version: null` because they predate the field's rollout — flagged in the runs table as `current` because their `started_at` is after the cutoff and the only change since the cutoff has been docs-only for this task. No proposed change.
- No model-side failures on any of the seven current runs (all completed quickly, no timeouts/oversized-query failures). The 2026-05-13 gemma `ConnectError`/cancelled attempts remain stale infra failures, not task issues.

### 3. Changes applied this run

#### Unilateral edits
(none — the task is well-calibrated. Grader logic, tolerances, instruction, metadata, reference, and broken scores are internally consistent and confirmed by all seven current runs. The instruction has no CRS / GeoJSON redundancy and no persona-vs-schema duplication to strip. No `task.json.version` bump is required because no meaningful edit was made.)

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.00 (5/5 subchecks)
- grader on `broken_wrong_format`: 0.00 (expected [0.0, 0.0])
- grader on `broken_inner_join`: 0.60 (expected [0.50, 0.70])
- grader on `broken_name_used_id`: 0.80 (expected [0.70, 0.90])
- pytest: pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The inventory row (`benchmark/authoring/inventory.md` > Category: spatial_analysis >
`spa-l1-vienna-pip-count`) defines this as an L1 spatial-analysis task: a
point-in-polygon count of Vienna air-quality monitoring stations against the
city's 23 statutory Bezirke, both bundled GeoJSON in EPSG:31287 (MGI / Austria
Lambert), output as a plain CSV with `district_code, district_name,
station_count` sorted by `district_code`. The persona Ana Brković
(Umweltbundesamt) wants a coverage diagnostic so the funding committee can spot
under-monitored Bezirke. The design beat is not the spatial join alone but the
left-join-back so that zero-count districts also appear. First commit recovered
task with 49 stations / 23 districts, two gates plus five binary subchecks,
three broken classes (`wrong_format`, `inner_join`, `name_used_id`), Gate-2
row-count tolerance ±25%.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 9503205 | initial-authoring | Recovered task from parallel authoring branch | Commit msg: "task: … [recovered]" |
| 2026-05-08 | 001e459 | docs-change | `benchmark/` split into `authoring/` and `eval/` (path-only) | Commit msg matches |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema" block to instruction | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json` | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg matches |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg matches |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` | Commit msg matches |
| 2026-05-13 | 9b1fb11 | prompt-change | Prose-merged "Output schema" bullets into running prose | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` (FLUX schnell) | Commit msg matches |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` (nano-banana-2) | Commit msg matches |
| 2026-05-14 | 1bc112e | prompt-change | Stripped "(both MGI Lambert)" CRS hint, name examples, postal-code disambiguation | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 7f31f98 | prompt-change | Removed explicit "districts with zero stations must still appear" sentence; persona framing kept | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + path-only grader edit) | Folder-layout reorg; `grade.py` only updates `REFERENCE_OUT` path | Commit msg matches |
| 2026-05-26 | 471f7c1 | docs-change | Prior evaluator review; verdict calibrated, no edits | Commit msg matches |
| 2026-05-27 | dd10686 | docs-change | Second evaluator review; verdict calibrated, no edits | Commit msg matches |
| 2026-05-28 | 622342b | docs-change (this task) | Repo-wide content-versioning rollout; `prompt_version` dropped from `metadata.yaml` | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 5727e97 | docs-change | Third evaluator review; verdict calibrated, no edits | Commit msg matches |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T12:49:06+00:00** (commit `7f31f98`, class: prompt-change). Most recent commit in any answer-key/instruction-affecting class. The 2026-05-26 reorg `29a9ae3` and the 2026-05-28 content-versioning rollout `622342b` are docs-only for this task (path-renaming and a `prompt_version` field removal); instruction, grader logic, tolerances, inputs, reference outputs, and broken outputs are byte-identical, so neither is design-affecting for run validity.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T14:12:56Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T18:56:28Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:14:29Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T23:04:10Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-28T01:00:49Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T03:07:17Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:12:46Z | 1.0 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:55:27Z | 1.0 | done | current |
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T22:09:18Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:22:46Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-29T00:50:09Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:09:57Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T18:07:48Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:31:12Z | 1.0 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:50:57Z | 1.0 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | (cancelled) | cancelled | current (model-side) |

Stale runs (pre-cutoff): all `run-20260512-…` through `run-20260517-0614Z`. The cancelled 2026-06-06 run is a model-side outcome (no error trace, status cancelled with score null), not a task-calibration signal.

#### Verdict
**calibrated**

Fifteen `current` completed runs across four model families of differing capability (claude-opus-4-6/4-7, deepseek-v4-flash/v4-pro, gemma-4-26b-a4b-it) all solve this L1 task perfectly (1.0). That is the expected discrimination profile for an L1 single-op task on two fully bundled, same-metric-CRS GeoJSON layers. The `too-easy` test requires both (a) all current runs ≥0.95 and (b) over-specified instruction; condition (b) remains false because commit `7f31f98` already stripped the literal "zero-count districts must appear" gift. The weaker gemma runs explicitly reason about including zero-count districts in their solver code, inferring the contract from the persona framing rather than pattern-matching a literal sentence. Reference grader 1.0; brokens 0.0 / 0.6 / 0.8 verbatim against `metadata.yaml`; Gate-2 ±25% still lands the 19-row inner-join at 0.6 rather than 0.0.

#### Specific findings
- All fifteen completed current runs produced byte-identical CSV output versus `reference/solution/outputs/stations_per_district.csv` (verified via `diff` on nine fresh runs since the last evaluator review). No agent dropped a column, inner-joined, or pulled the relation id into `district_name`.
- Output-CRS / format consistency (Step 2c-CRS): output is non-spatial CSV with no geometry column. `expected_outputs[]` declares `format: csv, crs: null, geometry_type: null`; reference output is plain CSV; README's output table matches. No CRS on the output side; grader does no reprojection. Consistent.
- Grader / metadata calibration re-verified: reference 1.0 (5/5); `broken_wrong_format` 0.0 (Gate-1 missing-column); `broken_inner_join` 0.6 (3/5 subchecks); `broken_name_used_id` 0.8 (4/5 subchecks). All inside `metadata.yaml > broken_solutions > expected_score_range` bands and equal to the recorded `measured_score`s.
- Instruction house-style audit (Step 4 house-style rules): the instruction at the start of this evaluator pass contained two em-dashes (rule 3 violation) and referenced input layers by their input-bundle `name` field (`stations`, `districts`) rather than their actual filenames `stations.geojson` / `districts.geojson` (rule 5 violation). Both fixed unilaterally per the house-style rules. The fix preserves the persona, the "Coverage diagnostic for next year's air-quality budget round" framing, every factual constraint, all three column-name specifications, the sort directive, and the deliberate omission of CRS / predicate / explicit-zero-count language. Pattern: opens with purpose ("I'm pulling together a coverage diagnostic …"), then the ask ("Can you take `stations.geojson` and `districts.geojson` and write …").
- `analyst_notes` was missing. Authored per the schema. Description states the hidden gotcha (coverage diagnostic needs every polygon, not just the joined-onto ones); approach is five high-level imperative steps without naming libraries or functions; pitfalls cover the canonical gotcha first (zero-count drop) plus the four other failure modes documented in `README.md > Failure modes` (column-confusion in district_name, dropped station_count column, constant filler, wrong district_code scheme).
- `task.json.version` bumped from implicit-1 to explicit 2 (first unilateral edit in this pass that meaningfully changes the prompt). `analyst_notes` alone would not require a bump, but the instruction edit does.
- Cross-axis / inventory consistency: `task.json.tags`, `metadata.yaml`, `README.md`, and the bundled inputs all agree on region vienna, formats geojson+csv, CRS EPSG:31287, geometry point+polygon, operation pip_count, scale small. The OSM-tag substitution (inventory: `place=*` + `boundary=administrative`; implementation: `boundary=administrative admin_level=9` + `man_made=monitoring_station`) remains fully-disclosed in the author block. Captured under `coverage.yaml > notes`.
- No model-side failures on completed current runs. The one cancelled 2026-06-06 run is harness/infra-side, not task-calibration.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style rewrite of `instruction` — replaced two em-dashes with comma/conjunction phrasing, switched ``stations`` / ``districts`` to actual filenames ``stations.geojson`` / ``districts.geojson``, opened with "I'm pulling together …" purpose-then-ask pattern. Persona, named context, all factual constraints, column names, sort order, and deliberate omissions preserved. Re-grade on reference: 1.00.
- `task.json`: added `version: 2` (implicit-1 → explicit-2) as required for the first unilateral instruction edit in this evaluator pass.
- `task.json`: authored `analyst_notes` (description, approach, pitfalls) per the schema. Human-facing only; no agent-runtime change.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp.

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.00 (5/5 subchecks)
- grader on `broken_wrong_format`: 0.00 (expected [0.0, 0.0])
- grader on `broken_inner_join`: 0.60 (expected [0.50, 0.70])
- grader on `broken_name_used_id`: 0.80 (expected [0.70, 0.90])
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
- Row-count ±25% check deleted: already covered by the stricter
  `exact_count_match` and `district_code_set_complete` subchecks.
- Removed the now-unused `_within_tolerance` helper and
  `GATE2_COUNT_TOLERANCE` constant.
- Subcheck count unchanged at 5.

### Verification
- Reference solution re-graded: 1.0 (5/5 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The inventory row (`benchmark/authoring/inventory.md` > Category: spatial_analysis >
`spa-l1-vienna-pip-count`) defines this as an L1 spatial-analysis task: a
point-in-polygon count of Vienna air-quality monitoring stations against the
city's 23 statutory Bezirke, both bundled GeoJSON in EPSG:31287 (MGI / Austria
Lambert), output as a plain CSV with `district_code, district_name,
station_count` sorted by `district_code`. The persona (Umweltbundesamt analyst)
needs a coverage diagnostic so a funding committee can spot under-monitored
Bezirke; the design beat is the left-join-back so that the four zero-count
districts also appear. First commit recovered the task with 49 stations /
23 districts, three broken classes (`wrong_format`, `inner_join`,
`name_used_id`).

#### Change log
(Entries through 2026-06-06 are carried verbatim in the four prior evaluator
blocks above; only commits since the last review block are itemised here.)

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | ceb765e | mixed (prompt-change + docs-change) | Prior evaluator pass: house-style instruction rewrite, `version` 1 -> 2, `analyst_notes` authored, coverage/status refreshed | Commit msg: "Re-evaluate spa-l1-vienna-pip-count: house-style rewrite, add analyst_notes" |
| 2026-06-06 | 363aed2 | grader-change | Removed `Gate("structural_correctness", ...)` (the ±25% row-count gate), the `_within_tolerance` helper, and `GATE2_COUNT_TOLERANCE`; single hard `format_schema_valid` gate remains; five subchecks unchanged | Commit msg: benchmark-wide "Drop Gate 2 from graders; one hard gate, rest are subchecks" - row-count diagnosis already covered by the stricter `exact_count_match` / `district_code_set_complete` subchecks |
| 2026-06-06 | 6a7113d | docs-change | One cross-reference line in this audit log updated for the tokyo-jgd task rename | Commit msg: mechanical rename of `crs-l3-tokyo-jgd-densification` |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to all five subchecks | Commit msg: "Weight data-content subchecks 3x across all categories". For this grader the weighting is uniform (5 x 3.0), so every possible score is numerically identical to the unweighted grader (3k/15 = k/5) |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:32:38Z** (commit `c749e57`, class: grader-change). Note this commit is provably score-neutral for this task (uniform weight 3.0 on all five subchecks), and the prior grader-change `363aed2` (2026-06-06T20:11Z) only changes behavior for submissions whose row count falls outside ±25% of 23 (previously hard-zeroed, now scored by subchecks); no observed run produced such an output. The most recent change that can alter what an agent sees or how observed outputs score is therefore the prompt rewrite in `ceb765e` (2026-06-06T16:56:10Z), which also bumped `version` to 2.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-09T07:34:12Z | 1.0 | done | current (version 2, post-cutoff) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T12:34:28Z | 0.6 | done | current (version 2, post-cutoff) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T16:49:01Z | 1.0 | done | stale by strict timestamp cutoff, but tests the identical prompt/version-2 content and a grader whose only later change (`c749e57`) is score-neutral; treated as corroborating evidence |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:38:50Z | 1.0 | done | stale (pre gate-removal `363aed2`); same caveat - identical prompt, observed output scores identically under the current grader |

Stale runs (footnote): all runs from `run-20260512-…` through `run-20260606-1334Z` predate the `ceb765e` prompt rewrite or earlier cutoffs and were assessed in the four prior evaluator blocks (scores: fifteen 1.0 completions across opus/deepseek/gemma plus model-side cancellations). `run-20260607-112405Z` was cancelled before this task started (no per-task evidence).

#### Verdict
**calibrated**

By the strict timestamp cutoff there are only two current runs and both are deepseek-v4-flash, which alone would force `insufficient-evidence`; but the post-cutoff grader delta is provably score-neutral (uniform 3.0 weights), so the two gemma-4-26b runs against the identical version-2 prompt count as corroborating evidence, giving two model families. The decisive new signal this pass: the task's partial-credit band has now been hit by a real agent. `run-20260609-084636Z` (deepseek-v4-flash, basic prompt variant) produced the canonical inner-join failure - 19 rows, codes {6, 8, 11, 17} missing - and the grader scored it exactly 0.6 with the intended diagnosis (`exact_count_match` and `district_code_set_complete` fail; per-row name/count and the 49-station total pass). The same model with the gis_detailed prompt variant scored 1.0 a day earlier, i.e. the task discriminates within one model family by prompt-variant capability, exactly the gradient the broken-solution design predicted. The reference grades 1.0; brokens re-measure 0.0 / 0.6 / 0.8, inside all declared ranges. The instruction post-`ceb765e` still withholds the literal zero-count clause and the run evidence confirms the persona framing is a real (failable) inference test, so the `too-easy` condition (b) remains false.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `stations_per_district.csv` | instruction, ask sentence | stated |
| plain CSV, no geometry column | instruction, schema paragraph | stated |
| exact columns `district_code`, `district_name`, `station_count` | instruction, schema paragraph | stated |
| `district_code` = integer Bezirk number, not other id columns | instruction ("integer-valued, the Bezirk number, not other identifier columns") | stated |
| `district_name` = German name from districts layer | instruction | stated |
| every Bezirk appears (23 rows incl. zero-count) | "listing every Bezirk", "one row per Bezirk", persona's "spot under-monitored areas" | inferable (deliberate design beat; failable - see run-20260609-084636Z) |
| per-row counts correct / total 49 | the core task; derivable from the data | inferable |
| int-coercion leniency ("2.0" passes) | grader-internal | inferable (standard dtype leniency) |
| rows sorted by `district_code` | instruction ("Sort rows by `district_code`.") | stated but NOT checked by the grader -> HR-001 |

Factual claims verified: `stations.geojson` (49 Points, EPSG:31287, cols station_id/name) and `districts.geojson` (23 Polygons, EPSG:31287, cols district_code/district_name/osm_relation_id) exist in `inputs/` and match the instruction's references; the three output column names match the reference output header; the reference CSV has 23 rows, total 49, sorted by district_code. No inaccurate claim found.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads the two bundled layers, sanity-checks the CRS without reprojecting, spatial-joins stations to districts with the `within` predicate, group-counts, left-joins the counts back onto the full 23-district list with zero-fill, sorts by `district_code`, and writes the three-column CSV. No unrequested operations, no skipped steps, no CRS issue (no spatial computation beyond containment in the shared metric CRS).

#### Specific findings
- The grader is order-insensitive (it key-joins on `district_code`), but the instruction commits the agent to "Sort rows by `district_code`." An unsorted-but-correct CSV scores 1.0. Whether to add a low-weight `sorted_by_district_code` subcheck or accept the leniency (key-joined CSV comparison is the suite-wide convention; the sibling `spa-l1-paris-amenity-within` grader is also order-insensitive, though its prompt does not ask for a sort) is a judgment call. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Human should decide: add an order subcheck to `grade.py` (version bump required), or keep the leniency and optionally drop the sort directive from the instruction.
- `metadata.yaml` tolerances rationale and the `broken_solutions.inner_join` description still described the removed Gate-2 ±25% row-count gate. Updated unilaterally as a docs-accuracy fix (the `count_pct: 0.25` value is retained for provenance and explicitly marked as no longer gating). No tolerance value changed, so no version bump.
- `README.md` referenced the pre-reorg `data/` input paths, the removed "Gate 1" numbering, and twice claimed the zero-count contract is "spelt out" / an "explicit instruction" although commit `7f31f98` (2026-05-17) removed the literal clause. All fixed unilaterally (docs-change); also recorded the first in-the-wild 0.6 inner-join run in the weak-agent section.
- Neither benchmark-wide grader commit (`363aed2`, `c749e57`) bumped `task.json.version` (still 2). For this task both changes are score-neutral for all observed outputs, so the shared version-2 fingerprint across pre/post runs is harmless; noted for the record, no flag.
- Output-CRS / format consistency (2c-CRS): output is non-spatial CSV; `expected_outputs[]` declares `format: csv, crs: null, geometry_type: null`; reference and README agree; grader does no reprojection. Consistent.
- Coverage axes unchanged since the prior review; `coverage.yaml` re-validated against `coverage-vocabulary.yaml` and only the timestamp refreshed. The documented OSM-tag substitution (`boundary=administrative admin_level=9` + `man_made=monitoring_station` in place of the inventory's `place=*`) remains covered by the existing note.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: rewrote the stale Gate-2 prose in `tolerances.rationale` and `broken_solutions.inner_join.description` to match the single-gate grader; tolerance values untouched. Re-grade on reference: 1.00. Reason: docs accuracy after the 2026-06-06 gate-removal refactor.
- `README.md`: fixed stale `data/` paths to `inputs/`, replaced "Gate 1" with "the format gate", corrected two claims that the zero-count contract is literally "spelt out" in the instruction (it has been persona-implied since `7f31f98`), and recorded the first real 0.6 inner-join run. Re-grade on reference: 1.00. Reason: docs accuracy.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp; axes unchanged.

No `task.json.version` bump: no edit touched the instruction, grader, tolerances, or inputs.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 - prompt-vs-grader-judgment - instruction's "Sort rows by `district_code`." is not enforced by the order-insensitive grader; human to decide between adding a sort subcheck or accepting/removing the directive.

#### Tests run
- grader on reference: 1.00 (5/5 subchecks)
- grader on `broken_wrong_format`: 0.00 (expected [0.0, 0.0])
- grader on `broken_inner_join`: 0.60 (expected [0.50, 0.70])
- grader on `broken_name_used_id`: 0.80 (expected [0.70, 0.90])
- pytest: pass (41/41)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

**Change:** RECALIBRATED subcheck weights for error severity. The blunt
repo-wide commit `c749e57` had set all five subchecks to a uniform
`weight=3.0` (numerically identical to the unweighted grader). That
treated the cosmetic `district_name_per_row_match` label check as
exactly as severe, per failing check, as a core count/join check.
Down-weighted the cosmetic name check to `1.0`; the four central
count/join checks stay at `3.0`. Grading-only; no `task.json.version`
bump (only `weight=` values changed in `grade.py`).

### Reasoning
The central skill this L1 task probes is the correct point-in-polygon
join and the per-district counts — including the left-join-back so
every Bezirk appears (the design's signature beat). Four subchecks
detect that skill and stay highest-weighted:
- `exact_count_match` (3.0) — 23-row completeness; the inner-join gotcha.
- `district_code_set_complete` (3.0) — {1..23} code set; same gotcha.
- `station_count_per_row_match` (3.0) — the per-district PIP counts.
- `station_count_total_match` (3.0) — total = 49; catches constant-fill,
  double-count, scaling.

`district_name_per_row_match` (3.0 -> 1.0) is the one cosmetic check:
when it is the sole failure (the `name_used_id` broken) the join, the
per-district counts, and the total are all correct — only the
human-readable display column is wrong. A label slip should drop the
score lightly, not as hard as dropping four whole districts.

### Weight changes
| Subcheck | old | new |
|---|---|---|
| exact_count_match | 3.0 | 3.0 |
| district_code_set_complete | 3.0 | 3.0 |
| district_name_per_row_match | 3.0 | **1.0** |
| station_count_per_row_match | 3.0 | 3.0 |
| station_count_total_match | 3.0 | 3.0 |

Total weight budget: 15 -> 13.

### Broken scores before -> after
| Broken | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.000 | 0.000 | gate fail (missing column) — unchanged, correct |
| inner_join | 0.600 | **0.538** (7/13) | CENTRAL failure (drops 4 districts, defeats the coverage diagnostic) — now drops the score more |
| name_used_id | 0.800 | **0.923** (12/13) | COSMETIC failure (wrong label column, all counts correct) — now only a light drop |

Ordering: `0.0 < 0.538 (inner_join) < 0.923 (name_used_id) < 1.0`.
Monotone and severity-faithful: the cosmetic slip sits just below
1.0; the central join failure is meaningfully penalised. The two
brokens fail disjoint subcheck sets (inner_join -> {exact_count,
code_set}; name_used_id -> {name}), and the inequality
`w_exact + w_codeset (6) > w_name (1)` guarantees no ordering
inversion. Cross-checked the full failure ladder (wrong-CRS single
count miss -> 0.769; constant-fill / severe-CRS -> 0.538): the
cosmetic label slip is the least-penalised non-trivial failure, as
intended.

### Prior-run re-grade summary
Re-graded all 42 recorded runs under the final weights.
- 39 runs unchanged (all the 1.0 reference-correct outputs stay 1.0;
  reference-correct CSVs are weight-invariant).
- 1 real shift: `run-20260609-084636Z` (deepseek-v4-flash, basic) — the
  canonical 19-row inner-join failure — re-grades 0.600 -> 0.538,
  exactly the intended sharper penalty for the central failure.
- The other "changes" are cancelled / infra-failed runs (2026-05-13
  gemma `ConnectError` set + the cancelled `run-20260606-1334Z`) that
  have no `score.json` and empty outputs; grading their empty dirs
  yields 0.0 but they were never scored runs, so no real shift.

### HR-001
Retained. HR-001 is prompt-vs-grader-judgment (instruction asks "Sort
rows by `district_code`." but the grader is order-insensitive). It is
NOT a weighting issue and is untouched by this pass.

### Changes applied this run
- `grade.py`: `district_name_per_row_match` weight 3.0 -> 1.0 (the only
  weight changed; check logic, thresholds, and the single gate
  untouched).
- `metadata.yaml`: added the severity-weight rationale block; updated
  `broken_solutions.inner_join` (measured 0.6 -> 0.5385, range
  [0.50,0.70] -> [0.45,0.65]) and `broken_solutions.name_used_id`
  (measured 0.8 -> 0.9231, range [0.70,0.90] -> [0.88,0.96]) and their
  weight-arithmetic prose.
- `README.md`: refreshed the two broken score fractions (0.60 -> 7/13 ≈
  0.538; 0.80 -> 12/13 ≈ 0.923) and the in-the-wild weak-agent note.

### Tests run
- grader on reference: 1.00 (5/5 subchecks)
- grader on `broken_wrong_format`: 0.00 (expected [0.0, 0.0])
- grader on `broken_inner_join`: 0.5385 (expected [0.45, 0.65])
- grader on `broken_name_used_id`: 0.9231 (expected [0.88, 0.96])
- pytest: not-run (orchestrator runs the suite)
