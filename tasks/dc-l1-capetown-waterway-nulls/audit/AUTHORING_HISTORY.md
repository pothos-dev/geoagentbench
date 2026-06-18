# Implementation notes — dc-l1-capetown-waterway-nulls

## Status
completed

## Prompt version
2026-05-07-a (re-verification of a triplet authored under 2026-05-06-a;
no code changes — the reference, grader, and three broken solutions
all reproduce their declared scores under the current prompt and the
current Docker image)

## Summary
L1 data-cleaning task: contractor-style waterway GeoJSON for Cape Town
with three independent defect classes (null geometry, empty LineString
geometry, null `waterway_type`) plus a benign null-`name` class that
must be preserved → cleaned GeoJSON with a top-level `dropped_count`
foreign member. Reference, grader, and three broken solutions built
and verified inside the project Docker container.

## Verification results
- Reference grader score: 1.00 (9 / 9 subchecks pass)
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 CRS check
    rejects EPSG:3857 file before any subcheck runs.
  - under_drop: 0.444 (expected range [0.35, 0.55]) — 4 / 9 subchecks
    pass: dropped_count_present, null_name_rows_preserved,
    geometry_preserved_per_id, attributes_preserved_per_id.
  - wrong_geometry: 0.889 (expected range [0.8, 0.95]) — 8 / 9
    subchecks pass; only `geometry_preserved_per_id` fails (per-id
    Hausdorff > 1e-7° because every kept LineString was translated by
    0.01°).
- Second-run output match: bit-identical (verified via `cp` + `diff -q`
  on `reference/outputs/waterways_clean.geojson` before/after a second
  `reference/generate.py` run inside Docker — also bit-identical to
  the previously committed reference, so no broken/reference output
  needed regenerating).
- Library tests after task: pass (32 / 32)

## Failure-mode coverage
- Drop only `null` geometries — miss empty LineStrings + null
  waterway_type rows: broken_under_drop
- Over-drop — also drop null-name rows: principled — `null_name_rows_preserved`
  + `feature_id_set_preserved` subchecks
- Forget the `dropped_count` foreign member: principled —
  `dropped_count_present` + `dropped_count_correct` subchecks
- Report a wrong `dropped_count` value: principled —
  `dropped_count_correct` subcheck (strict equality)
- Output in the wrong CRS: broken_wrong_format
- Disturb geometries: broken_wrong_geometry
- Drop required columns: principled — Gate 1 column check
- Mutate attribute values (fill nulls with sentinels): principled —
  `attributes_preserved_per_id` + `feature_id_set_preserved` subchecks

## Open issues
- [severity: low] — Bundled input is hand-crafted rather than sliced
  from Overture. AUTHOR_CONTEXT.md and OVERTURE_REFERENCE.md both
  permit hand-crafting when the task is *about* malformed data (this
  one is — null and empty geometries do not survive an Overture
  release) and when the inventory anchors on an OSM tag family with
  no clean Overture equivalent for the geometry class involved
  (`waterway=*` linear watercourses; Overture's `base.water` is
  predominantly polygonal water bodies). Defect placement is
  hard-coded by `feature_id` ranges in `data/_prepare_input.py` so
  the layout is reproducible and the failure-mode coverage is
  auditable. Coordinates are deterministic closed-form functions of
  `feature_id` inside the Cape Town municipal bbox; sensor-grade
  geographic accuracy is not under test in this task.

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — the task uses only existing primitives:
`attribute_match`, `count_within_tolerance`,
`feature_set_equality_by_id`. Per-id LineString preservation is
implemented inline against `shapely.hausdorff_distance` because the
existing `topology_equal_within_epsilon` reduces both sides to a
single unioned geometry, which would smear over per-id mismatches —
adding a `per_id_geometry_match_rate` primitive feels premature
given only one task uses it.)

## Runtime
~20 minutes (no network fetch; all work was local Docker runs).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task was authored 2026-05-07 as an L1 data-cleaning task targeting null /
empty handling on a contractor-style GeoJSON of Cape Town waterway centrelines.
The inventory row (`authoring/inventory.md` §`dc-l1-capetown-waterway-nulls`)
anchors it on three independent defect classes (null `geometry`, empty
`LineString` coordinates, null `waterway_type`) plus a benign null-`name`
control class that must be preserved. Output is a cleaned GeoJSON in EPSG:4326
with a top-level `dropped_count` foreign member. The bundled fixture is
hand-crafted (justified in `author-context.md`: malformed-data tasks where the
defect class does not survive an Overture release, plus `waterway=*` linear
watercourses have no clean Overture equivalent). The reference, grader, and
three broken solutions were verified inside Docker and committed in the
initial pair `00630cb` + the unseen authoring commit before it (the original
content of `IMPLEMENTATION_NOTES.md` describes the verification run with
9/9 subchecks at 1.0 on the reference).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 00630cb | initial-authoring | Initial task; updates to `IMPLEMENTATION_NOTES.md` and `metadata.yaml` finishing the authoring triplet | Commit msg: "task: dc-l1-capetown-waterway-nulls [completed]" |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit `Output schema:` bullet block declaring CRS, geometry type, required columns, join key, and the `dropped_count` foreign-member requirement | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | 284b843 | prompt-change | Added structured `tags` dictionary (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) to `task.json` | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | 4f0cfc0 | prompt-change | Rewrote the appended `Output schema:` bullet list into a single prose sentence; technical requirements preserved | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | f5d1e91 | prompt-change | Stripped the answer-giving phrase listing the three defect classes ("null geometry, empty LineString coordinates, or null waterway_type") and the "rows with a null name … should stay" exception from the persona's opening; replaced with the generic "some features are invalid or incomplete — drop any that cannot represent a valid waterway" | Commit msg: "Strip deducible information from DC task instructions" |
| 2026-05-16 | 7c812d6 | prompt-change | Re-inserted a parenthetical ("null or empty geometry, or missing waterway_type") explicitly enumerating the drop predicate inside the prose | Commit msg: "clarify that null waterway_type should be dropped" |
| 2026-05-17 | 64740d0 | prompt-change | Removed the parenthetical again and reworded the persona to "some features are unusable for our mapping pipeline. Drop any features that cannot represent a valid, usable waterway and keep the rest" | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" |
| 2026-05-17 | db638f4 | prompt-change | Appended the dash clause "— a feature needs both a drawable geometry and a known waterway type to be useful —" to compensate for tasks regressing after the nudge removal | Commit msg: "Capetown waterways: hint that both geometry and type are required" |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `sub.crs.to_epsg() == 4326` with shared `is_wgs84(sub.crs)` helper (accepts EPSG:4326 and OGC:CRS84) | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder layout move: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/{generate.py,outputs/,visualizations/}` → `reference/solution/`, `tests/` → `reference/failures/`, `image.{webp,prompt.md}` → `assets/`; grader path constants updated. No semantic change. | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-18T06:35:57+00:00 (commit `f0c244a`, class: `grader-change` — `is_wgs84` consolidation; semantically equivalent to the prior `to_epsg() == 4326` for the existing reference, but it widens acceptance to `OGC:CRS84`, which is a behavioural change in the gate)
- prior nearest cutoff (instruction): 2026-05-17T19:17:27+00:00 (commit `db638f4`, class: `prompt-change`)
- folder move `29a9ae3` on 2026-05-26 is a `docs-change` (path-only) and does not invalidate runs against the prior layout — but in practice the only post-cutoff run was started after this move anyway.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:15:04Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:41:46Z | 0.556 | done | stale (pre-db638f4) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:08:22Z | 0.556 | done | stale (pre-db638f4) |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T07:52:51Z | 1.00 | done | stale (pre-db638f4) |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T03:13:27Z | 1.00 | done | stale (pre-db638f4) |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T01:48:30Z | 1.00 | done | stale (pre-db638f4) |
| (24 earlier runs, 2026-05-12 → 2026-05-16) | various | various | various | done | stale (pre-cutoff) |

#### Verdict
**insufficient-evidence**

Only one `current` run exists (Gemma-4-26B basic, score 1.0) — too narrow to characterise calibration across agent families. The reference grades 1.0 (9/9 subchecks) and the three broken solutions (`wrong_format`, `under_drop`, `wrong_geometry`) reproduce their declared scores (0.0, 0.444, 0.889) exactly under the current grader, so the grading machinery is healthy. The prompt is now in a state that the design-history shows the author iterated on twice (nudge stripped 2026-05-17 in `64740d0`, then partly restored 2026-05-17 in `db638f4`) — the post-`db638f4` instruction does say "a feature needs both a drawable geometry and a known waterway type to be useful", which is a heavy hint but not a name-the-three-defect-classes giveaway. Stale runs from the day of `db638f4` show two agents (Opus, Deepseek) scoring 0.556 and another two (same agents) scoring 1.0, with the 0.556 cases preceding `db638f4`'s extra clause — consistent with the author's note that the prior wording was causing regressions. There is no evidence in the current data that the task is too easy or too strict; the calibration question is open pending more current runs.

#### Specific findings
- The grader was already migrated to `is_wgs84` (commit `f0c244a`) which accepts both EPSG:4326 and OGC:CRS84. This is correct for GeoJSON output (pyogrio writes the legacy `crs` member with the CRS84 URN, which `gpd.read_file` recovers as EPSG:4326 — the gate would have already passed in practice, but the new helper makes the gate robust to writers that emit CRS84). No action.
- The reference fixture (`inputs/capetown_waterways.geojson`) holds the documented defect counts (null_geom=10, empty_geom=5, null_wt=10, null_name=5, total=100; reference output retains 80 features). The `dropped_count = 20` foreign member is asserted via `feature_id` ranges in `inputs/_prepare.py`; verified by direct inspection. No action.
- The instruction's dash clause ("a feature needs both a drawable geometry and a known waterway type to be useful") was added explicitly to compensate for nudge-removal regressions (commit `db638f4`). It is a borderline judgment call whether "drawable geometry" + "known waterway type" is too strong a hint at the answer (the agent is essentially told the two drop predicates by name). Author's stated rationale in the commit message is "hint that both geometry and type are required" — i.e. the author *intended* this as a hint to fight earlier over-stripping. I am not flagging it: the author iterated on this twice and `db638f4` is the stable state. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="low" --> Borderline call retained from the author's last iteration; only flagging in case a future evaluator wants to re-test stripping the dash clause once more current runs land.
- Only 1 current run (started after the 2026-05-18 cutoff) — insufficient to call calibration. Recommend a sweep across Opus/Sonnet/Deepseek/Gemma at the current prompt to fill this gap. <!-- HUMAN-REVIEW id="HR-002" category="task-too-easy-suspected" severity="low" --> Not actually suspected of being too easy yet — flagging the *evidence gap*. Stale data shows mixed outcomes (0.556 and 1.0 across the same models), so the floor isn't 1.0; but no post-cutoff data confirms the present wording reproduces that spread.

### 3. Changes applied this run

#### Unilateral edits
(none — the task is well-formed, the grader and reference still reproduce their declared scores, the prompt is in the state the author committed to in the most recent semantic change, and Step 4 lists no unilateral action that the current evidence supports)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment — Borderline call on whether the dash clause "a feature needs both a drawable geometry and a known waterway type to be useful" is an over-helpful hint. Author iterated twice; retained.
- HR-002 — task-too-easy-suspected — Only 1 current run; need ≥ 2 across different agent families to characterise the post-`db638f4` prompt.

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- grader on broken_wrong_format: 0.000 (gate 1 CRS fail — matches declared 0.0)
- grader on broken_under_drop: 0.444 (4/9 subchecks — matches declared 0.444)
- grader on broken_wrong_geometry: 0.889 (8/9 subchecks — matches declared 0.889)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-26 (second pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the first evaluator pass above. The task is an L1 data-cleaning
task targeting null / empty handling on a contractor-style GeoJSON of Cape Town
waterway centrelines, anchored on the OSM `waterway=*` tag family. Three
independent defect classes (null `geometry`, empty `LineString` coordinates,
null `waterway_type`) must be dropped while a benign null-`name` control class
(`feature_id` 21–25) is preserved. Output is a cleaned GeoJSON in EPSG:4326 with
a top-level `dropped_count` foreign member (20). The bundled fixture is
hand-crafted (justified in `inputs/_prepare.py`).

#### Change log (delta since first evaluator pass)
No new design-affecting commits since the prior review. The full chronology
through `f0c244a` is recorded in the first evaluator-review block above and is
re-confirmed here (I re-read the `f0c244a` diff: it is the `is_wgs84` helper
swap on the Gate-1 CRS check — semantically equivalent for the existing
reference, widens acceptance to OGC:CRS84). Only two commits touch the task
directory since:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-26 | 29a9ae3 | docs-change | Folder layout move (path-only; no semantic change) | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 9420b04 | docs-change | First evaluator pass artefacts (`audit/AUTHORING_HISTORY.md`, `coverage.yaml`, `audit/status.json`) | Commit msg: "Re-evaluate dc-l1-capetown-waterway-nulls: insufficient-evidence …" |

Neither is design-affecting; the cutoff is unchanged.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-18T06:35:57+00:00 (commit `f0c244a`, class: `grader-change` — `is_wgs84` consolidation). Re-confirmed; unchanged from first pass.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:26:23Z | 1.00 | done | current |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:37:32Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:15:04Z | 1.00 | done | current |
| (24 earlier runs, 2026-05-12 → 2026-05-17) | various | various | various | done | stale (pre-cutoff) |

Footnote on stale runs: the day-of-`db638f4` stale runs (2026-05-17) show Opus
and Deepseek scoring 0.556 *before* the dash clause landed, and 1.0 once it did
— i.e. the prior wording produced a real spread; the present wording does not.

#### Verdict
**too-easy**

The evidence gap flagged as HR-002 in the first pass is now filled. Three
`current` runs exist across two agent families (claude-code Opus and OpenRouter
Gemma-4-26B, twice), and **all three score 1.0 (9/9 subchecks)**. These two
adapters demonstrably show varying capability *elsewhere in the same sweep*:
in `run-20260526-1753Z` Opus ranges 0.57 → 1.0 (and fails `crs-l3-tokyo`), and
in `run-20260526-1922Z` Gemma spans 0.0 (five tasks, incl. `geo-l1-capetown-building-centroids`,
`geo-l2-nyc-park-symdiff`, `spa-l2-lagos-hotspot-overlaps`) through 0.55–0.75 to
1.0. So the perfect score on this task is not "these agents always score 1.0" —
it is specific to this task. Combined with the instruction over-specification
below, this meets the Step-2d `too-easy` definition (every current run ≥ 0.95
across agents of varying capability, AND the instruction over-specifies).

The grading machinery itself is healthy: reference 1.0, and the three broken
solutions reproduce their declared distinct ranges exactly (0.0 / 0.444 /
0.889). The task is not mis-graded — it is correctly graded but the prompt
hands the agent the answer.

#### Specific findings
- **Instruction over-specification (the core finding).** The persona's dash
  clause — "a feature needs both a drawable geometry and a known waterway type
  to be useful" (`task.json` line 14) — names *both* of the task's drop
  predicates verbatim. The task's stated central skill (grade.py docstring) is
  for the agent to "recognise three independent defect classes" on its own; the
  instruction instead tells it the geometry must be drawable and the
  waterway_type must be known. The two current solver scripts confirm rote
  translation rather than reasoning: the Opus `solve.py` docstring reads "A
  feature is kept iff: it has a drawable geometry (LineString with >=2
  coordinates), AND it has a known waterway_type" — a near-verbatim echo of the
  clause — and the Gemma `solve.py` comment reads "Filter for known
  waterway_type". This is the "step-by-step procedural decomposition / naming
  the operation" gift category from Step 2d. **I am NOT stripping it
  unilaterally:** the design history shows the author iterated on this exact
  clause twice (stripped in `f5d1e91`/`64740d0`, deliberately re-added in
  `db638f4` with commit message "hint that both geometry and type are
  required") to fix a documented post-nudge-removal regression. Step 4 only
  authorises stripping a *clear* gift; this is the textbook *borderline* case
  that Step 2d/Step 4 require me to flag rather than resolve. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> The dash clause "a feature needs both a drawable geometry and a known waterway type to be useful" names both drop predicates; with it present, all current runs (Opus + 2×Gemma) score 1.0 despite those agents failing other tasks in the same sweep. A human must decide whether to re-strip it (and accept the documented regression risk on weaker agents) or accept the task as a deliberately-easy L1 floor. The author intentionally re-added it; I retain the author's last state.
- **Verdict upgrade vs first pass.** The first pass returned `insufficient-evidence` / HR-002 (only 1 current run, evidence gap). With two further current runs from a second family, the gap is closed and the spread question is answered: the floor on this task is 1.0, not the 0.556 the pre-`db638f4` wording produced. The too-easy reading is now supported by data, not merely suspected. Recording HR-002 below as the (now-resolved) lineage of HR-001.
- **No grader/reference defect.** The fixture defect counts (null_geom=10, empty_geom=5, null_wt=10, null_name=5; 20 dropped / 80 kept) and the three broken-solution ranges are intact and reproduce exactly. No reference/data edit is needed; the calibration issue is entirely on the instruction side.

### 3. Changes applied this run

#### Unilateral edits
(none — the only candidate change is stripping the dash clause from the
instruction, which is a documented borderline call the author deliberately
re-added; Step 4 forbids the evaluator from resolving it. The grader's
`measured_score` values in `metadata.yaml` already match the current grader
exactly, so no update there either.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (severity med) — Re-test stripping the dash clause "a feature needs both a drawable geometry and a known waterway type to be useful"; with it present the task is too-easy (all current runs 1.0). Author re-added it intentionally after a regression, so this needs a human design decision, not a unilateral evaluator edit.

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- grader on broken_wrong_format: 0.000 (matches declared [0.0, 0.0])
- grader on broken_under_drop: 0.444 (matches declared [0.35, 0.55])
- grader on broken_wrong_geometry: 0.889 (matches declared [0.8, 0.95])
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27 (third pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the two prior evaluator passes. L1 data-cleaning task targeting
null / empty handling on a contractor-style GeoJSON of Cape Town waterway
centrelines, anchored on the OSM `waterway=*` tag family. Three independent
defect classes (null `geometry`, empty `LineString` coordinates, null
`waterway_type`) must be dropped while a benign null-`name` control class
(`feature_id` 21–25) is preserved. Output is a cleaned GeoJSON in EPSG:4326 with
a top-level `dropped_count` foreign member (20). The bundled fixture is
hand-crafted (justified in `inputs/_prepare.py`). I re-read each design-affecting
diff directly this pass (`f5d1e91`, `64740d0`, `db638f4`, `f0c244a`) and confirm
the change log below independently.

#### Change log (delta since second evaluator pass)
No new design-affecting commits since the second review. The full chronology
through `f0c244a` is recorded in the first evaluator-review block above and was
re-confirmed in the second. `git log e3366e1..HEAD -- benchmark/tasks/dc-l1-capetown-waterway-nulls/`
returns nothing — the task directory has not been touched since the second
pass's own evaluator commit:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-26 | e3366e1 | docs-change | Second evaluator pass artefacts (`audit/AUTHORING_HISTORY.md`, `coverage.yaml`, `audit/status.json`) | Commit msg: "Re-evaluate dc-l1-capetown-waterway-nulls: too-easy (3 current runs all 1.0)" |

Not design-affecting; the cutoff is unchanged.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-18T06:35:57+00:00 (commit `f0c244a`, class: `grader-change` — `is_wgs84` consolidation; widens Gate-1 CRS acceptance to OGC:CRS84). Re-confirmed; unchanged from first and second passes.
- nearest prior instruction cutoff: 2026-05-17T19:17:27+00:00 (commit `db638f4`, the dash-clause re-insertion).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:26:23Z | 1.00 | done | current |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:37:32Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:15:04Z | 1.00 | done | current |
| (24 earlier runs, 2026-05-12 → 2026-05-17) | various | various | various | done | stale (pre-cutoff) |

No new runs have landed since the second pass (latest run dir is `run-20260526-1922Z`; no 2026-05-27 runs for this task). Footnote on stale runs: the day-of-`db638f4` 2026-05-17 runs show Opus and Deepseek scoring 0.556 *before* the dash clause and 1.0 after it — the prior wording produced a real spread; the present wording does not.

#### Verdict
**too-easy**

Independently re-confirmed. Three `current` runs (post-2026-05-18 cutoff) across
two agent families (claude-code Opus once, OpenRouter Gemma-4-26B twice) **all
score 1.0 (9/9 subchecks)**. I verified the per-run outputs directly: each
produced `waterways_clean.geojson` with exactly 80 features, an exact
`feature_id` set match against the reference (ids 21–100), CRS EPSG:4326, all
LineString, zero null/empty geometries, zero null `waterway_type`, and
`dropped_count = 20` (the two Gemma runs add a harmless extra `id` column that
the grader's subset column check ignores). I also confirmed both families show
varying capability *in the same sweep*: in `run-20260526-1753Z` Opus spans
0.57 → 1.0 (range across 14 done tasks, one further task failed), and in
`run-20260526-1922Z` Gemma spans 0.0 → 1.0 with five 0.0 tasks — including
`geo-l1-capetown-building-centroids`, a same-region peer L1. So the perfect
score on this task is task-specific, not a property of these adapters. This
meets the Step-2d `too-easy` bar (every current run ≥ 0.95 across agents of
varying capability, AND the instruction over-specifies — see below). The
grading machinery is healthy: reference 1.0 and the three broken solutions
reproduce their declared distinct scores exactly (0.0 / 0.444 / 0.889) under the
current grader. The task is correctly graded; the calibration issue is on the
instruction side.

#### Specific findings
- **Instruction over-specification (core finding, unchanged from second pass).**
  The persona's dash clause — "a feature needs both a drawable geometry and a
  known waterway type to be useful" (`task.json` line 14) — names *both* of the
  task's drop predicates. The grade.py docstring states the central skill is for
  the agent to "recognise three independent defect classes" by inspecting the
  data; the instruction instead hands it the geometry+type predicate. The two
  current solver scripts confirm rote translation: the Opus `solve.py` docstring
  reads "A feature is kept iff: it has a drawable geometry (LineString with >=2
  coordinates), AND it has a known waterway_type" — a near-verbatim echo — and
  the Gemma `solve.py` comments enumerate "non-null/non-empty geometry" and
  "known waterway_type". This is the "step-by-step / name-the-predicate" gift
  category from Step 2d. **I am NOT stripping it unilaterally:** the design
  history shows the author iterated on this exact clause twice (stripped in
  `f5d1e91`/`64740d0`, deliberately re-added in `db638f4` with commit message
  "hint that both geometry and type are required") to repair a documented
  post-nudge-removal regression on weaker agents. Step 4 authorises stripping
  only a *clear* gift; this is the textbook *borderline* case Step 2d/Step 4
  require me to flag rather than resolve. <!-- HUMAN-REVIEW id="HR-001" category="prompt-vs-grader-judgment" severity="med" --> The dash clause "a feature needs both a drawable geometry and a known waterway type to be useful" names both drop predicates; with it present, all 3 current runs (Opus + 2×Gemma — families that fail other tasks, incl. a same-region peer L1, in the same sweep) score 1.0, and both solver scripts echo the clause as code. A human must decide whether to re-strip it (accepting the documented regression risk the author hit when it was absent) or accept the task as a deliberately-easy L1 floor. I retain the author's last committed state.
- **No new evidence since the second pass.** The task directory has not changed
  and no new runs exist, so the second pass's `too-easy` verdict stands on the
  same three-run evidence base. This pass re-derives it independently from the
  run.json files and the per-run outputs rather than inheriting it.
- **No grader / reference / data defect.** Fixture defect counts (null_geom=10
  incl. the 5 null-geom-and-type, empty_geom=5, null_wt=10 incl. those 5,
  null_name=5; 20 dropped / 80 kept) are intact, the three broken-solution
  scores reproduce exactly, and `metadata.yaml > broken_solutions > measured_score`
  already equals the current grader's output (0.0 / 0.444 / 0.889) — no metadata
  edit needed. No reference/data edit is warranted; the calibration issue is
  entirely instruction-side.
- **Output-CRS / format consistency (Step 2c-CRS).** `expected_outputs[]`
  (geojson, EPSG:4326, LineString), the reference output (CRS 4326, LineString),
  and the README all agree. The grader applies `is_wgs84` to the submission CRS
  and reads the reference as 4326; there is no reprojection at all (LineString,
  no metric op), so no one-sided reprojection risk. No finding.

### 3. Changes applied this run

#### Unilateral edits
(none — the only candidate change is stripping the dash clause, a documented
borderline call the author deliberately re-added; Step 4 forbids the evaluator
from resolving it. The grader, reference, and broken-solution scores all
reproduce exactly, and `metadata.yaml` already matches, so no other edit is
justified. `coverage.yaml` re-emitted with a fresh timestamp; all slugs validate
against `coverage-vocabulary.yaml` and no axis contradicts another.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — prompt-vs-grader-judgment (severity med) — Decide whether to re-strip the dash clause "a feature needs both a drawable geometry and a known waterway type to be useful". With it present the task is too-easy (all current runs 1.0); the author re-added it intentionally after a regression, so this needs a human design decision, not a unilateral evaluator edit.

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- grader on broken_wrong_format: 0.000 (matches declared [0.0, 0.0])
- grader on broken_under_drop: 0.444 (matches declared [0.35, 0.55])
- grader on broken_wrong_geometry: 0.889 (matches declared [0.8, 0.95])
- pytest: pass (35/35)

---

## Evaluator review 2026-05-28 (fourth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the three prior evaluator passes. L1 data-cleaning task targeting
null / empty handling on a contractor-style GeoJSON of Cape Town waterway
centrelines, anchored on the OSM `waterway=*` tag family. Three independent
defect classes (null `geometry`, empty `LineString` coordinates, null
`waterway_type`) must be dropped while a benign null-`name` control class
(`feature_id` 21–25) is preserved. Output is a cleaned GeoJSON in EPSG:4326
with a top-level `dropped_count` foreign member (20). The bundled fixture is
hand-crafted (justified in `inputs/_prepare.py`).

#### Change log (delta since third evaluator pass)
Three new commits since the third pass. The first introduces task content
versioning (no per-task semantic change for this task — only the
`prompt_version` line was removed from `metadata.yaml`, a pure schema cleanup).
The second is a design decision (HR-001 resolution) replacing "a known waterway
type" with "a proper type" in the em-dash clause, plus a `design_note` block
in `metadata.yaml` recording the calibration evidence. The third is a
queue-hygiene commit that strips the resolved HR-001 entry from `audit/status.json`.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | mixed (metadata-cleanup) | Removed `prompt_version: 2026-05-07-a` from `metadata.yaml`; introduced `version` field semantics on `task.json` (no value added yet for this task — implicit v1) | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 2162f45 | prompt-change | Replaced "a known waterway type" with "a proper type" in the em-dash clause of `task.json.instruction`; added `design_note` to `metadata.yaml` recording the post-trim calibration evidence (6 runs: 5 at 1.0, 1 at 0.556 with the under-drop signature) | Commit msg: "Resolve dc-l1-capetown-waterway-nulls HR-001 via paraphrase trim + design note" |
| 2026-05-28 | fbb3596 | docs-change | Cleared the resolved HR-001 entry from `audit/status.json` per the new review-queue policy | Commit msg: "review-queue: clear resolved-HR entries; bundle status.json into Resolve commits going forward" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff (pre-this-evaluator-edit): 2026-05-28T09:36:32+00:00 (commit `2162f45`, class: `prompt-change` — em-dash clause paraphrase trim "known waterway type" → "proper type")
- design-affecting cutoff (post-this-evaluator-edit): 2026-05-28T13:35:47Z (this evaluator pass, class: `prompt-change` — GeoJSON CRS strip "GeoJSON in EPSG:4326, filename ..." → "Filename ...")
- prior nearest cutoff (grader): 2026-05-18T06:35:57+00:00 (commit `f0c244a`, `is_wgs84` consolidation; unchanged)
- The intermediate `622342b` is a metadata-schema cleanup (`prompt_version` removal) and the `fbb3596` is a queue-hygiene write to `audit/status.json` — neither changes the prompt/grader/reference/data contract, so they do not move the cutoff. I classified `622342b` as `mixed (metadata-cleanup)` for the change log because it edits `metadata.yaml`, but the per-task content edit is purely the `prompt_version` line removal which the evaluator-prompt explicitly classifies as not requiring a version bump.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:24:04Z | 1.00 | done | stale (pre-2162f45) |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T01:32:24Z | 1.00 | done | stale (pre-2162f45) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:35:59Z | 0.556 | done | stale (pre-2162f45) |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T20:34:02Z | 1.00 | done | stale (pre-2162f45) |
| (prior 27 runs through 2026-05-26) | various | various | various | done | stale (pre-cutoff) |

No `current` runs exist post the 2026-05-28T09:36:32+00:00 cutoff, and the
GeoJSON-CRS-strip unilateral edit applied in this pass pushes the cutoff to
the evaluator's edit timestamp. Footnote on stale 2026-05-27/28 runs: across
the two agent families (Opus 4.7 and gemma-4-26b), three runs scored 1.0 and
one (gemma-4-26b run-20260527-2321Z) reproduced the `broken_under_drop`
signature at 0.556 — 5 null geometries left in and `dropped_count` reported
as 15. The `design_note` in `metadata.yaml` (added in 2162f45) records this
as calibration evidence that the dash clause discriminates rather than gives
away the predicates. Those four runs are stale w.r.t. the current prompt, but
collectively they were the basis for the HR-001 resolution.

#### Verdict
**insufficient-evidence**

No `current` runs exist against the present prompt: the 2162f45 paraphrase
trim landed at 09:36Z on 2026-05-28 and no run for this task has started
since; the GeoJSON-CRS strip applied in this pass pushes the cutoff further.
The grader machinery is healthy — reference 1.0 (9/9 subchecks) and the three
broken solutions reproduce their declared scores exactly (0.0 / 0.444 / 0.889)
under the current grader; `metadata.yaml > broken_solutions > measured_score`
already matches and no refresh is needed. Step 2c-CRS check: `expected_outputs[]`
(geojson / EPSG:4326 / LineString), the reference output (CRS 4326, LineString),
and the README all agree, and the grader applies `is_wgs84` to the submission
CRS only (no reprojection on either side — LineString output, no metric op).
No CRS-consistency finding. With no `current` runs, the question of how the
present prompt calibrates across agent families is open; the past evidence
(5 of 6 runs at 1.0 on the prior wording) suggests it will remain on the
easier side, but a fresh sweep is needed to confirm under the trimmed paraphrase
and the GeoJSON-CRS-strip prompt that this pass produces.

#### Specific findings
- **GeoJSON CRS strip applied unilaterally (Step 4 / GeoJSON-CRS strip rule).**
  The instruction said "GeoJSON in EPSG:4326, filename waterways_clean.geojson,
  please." `expected_outputs[].format=geojson` and RFC 7946 pin WGS84 for
  GeoJSON output, so the "in EPSG:4326" naming was redundant with the Gate-1
  `is_wgs84` check. I rewrote the sentence to "Filename waterways_clean.geojson,
  please." Format and CRS naming both removed since "GeoJSON" is in the
  filename extension and the format is pinned by `expected_outputs[]`.
  Reference still scores 1.0 (9/9); pytest 41/41. `version` bumped from
  implicit 1 to explicit 2 on `task.json`.
- **HR-001 from prior passes is resolved (commit 2162f45).** The em-dash clause
  now reads "a feature needs both a drawable geometry and a proper type to be
  useful" — the attribute defect class is no longer named even in paraphrase.
  `metadata.yaml > design_note` records the calibration evidence (6 post-cutoff
  runs against the pre-trim wording: 5 at 1.0 and 1 at 0.556 with the
  under-drop signature). I am not re-raising HR-001 — the design decision is
  documented and the evidence supports it.
- **No grader / reference / data defect.** Fixture defect counts (null_geom=10
  incl. the 5 null-geom-and-type, empty_geom=5, null_wt=10 incl. those 5,
  null_name=5; 20 dropped / 80 kept) intact; the three broken-solution scores
  reproduce exactly under the current grader (0.0 / 0.444 / 0.889).
  `metadata.yaml > broken_solutions > measured_score` already matches — no
  refresh.
- **Insufficient-evidence verdict.** No post-2162f45 (and hence no
  post-this-pass) runs exist for this task. A future sweep across at least two
  agent families on the present prompt would characterise calibration. Not
  raised as a HUMAN-REVIEW item — Step 2d says to raise
  `grader-miscalibration-suspected` only if there is *other* concrete reason
  to suspect a problem; there isn't. The orchestrator will pick this back up
  on the next sweep after fresh runs land.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: stripped "GeoJSON in EPSG:4326" from the instruction
  ("GeoJSON in EPSG:4326, filename waterways_clean.geojson, please." →
  "Filename waterways_clean.geojson, please."). Re-grade on reference: 1.00
  (9/9). Reason: Step-4 GeoJSON CRS-strip rule —
  `expected_outputs[].format=geojson` pins WGS84 by RFC 7946 and the Gate-1
  `is_wgs84` check already enforces it; "GeoJSON" naming also dropped since
  the filename extension and `expected_outputs[]` already pin the format.
- `task.json`: added `version: 2` (implicit v1 → explicit v2). Bumped because
  the instruction edit above changes what the agent sees.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp; all slugs validate
  against `coverage-vocabulary.yaml` unchanged.

#### Proposed but not applied (see HUMAN-REVIEW items)
(none — no new HRs raised this pass; HR-001 from the prior passes was resolved
in commit 2162f45 and the resolution is captured in `metadata.yaml >
design_note`.)

#### Tests run
- grader on reference: 1.00 (9/9 subchecks)
- grader on broken_wrong_format: 0.000 (matches declared [0.0, 0.0])
- grader on broken_under_drop: 0.444 (matches declared [0.35, 0.55])
- grader on broken_wrong_geometry: 0.889 (matches declared [0.8, 0.95])
- pytest: pass (41/41)



---

## Evaluator review 2026-06-06 (fifth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior passes. L1 data-cleaning task targeting null / empty
handling on a contractor-style GeoJSON of Cape Town waterway centrelines,
anchored on the OSM `waterway=*` tag family. Three independent defect classes
(null `geometry`, empty `LineString` coordinates, null `waterway_type`) must
be dropped while a benign null-`name` control class (`feature_id` 21–25) is
preserved. Output is a cleaned GeoJSON in EPSG:4326 with a top-level
`dropped_count` foreign member (20). Bundled fixture is hand-crafted
(justified in `inputs/_prepare.py`).

#### Change log (delta since fourth evaluator pass)
Two new commits since the fourth pass — the fourth-pass evaluator commit
itself, and a project-wide grader policy change that softened the CRS gate
across 21 graders (this task included). The grader change is design-affecting
for this task: it adds two CRS subchecks and stops Gate-1-rejecting wrong-CRS
submissions, which collapses the broken-solution scores into a new shape.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | ec1b73f | docs-change | Fourth evaluator pass artefacts (instruction GeoJSON-CRS strip, version bump to 2, status/coverage/history files) | Commit msg: "Re-evaluate dc-l1-capetown-waterway-nulls: insufficient-evidence; strip redundant GeoJSON+EPSG:4326 from instruction" |
| 2026-05-28 | 05aabd6 | grader-change | Replaced Gate-1 `is_wgs84` hard-fail with `grade_crs_soft` helper. Added module-level `CANONICAL_EPSG = 4326` and `MEANINGFUL_EPSGS = {4326}`. Gate 1 now only fails when the submission has no usable CRS at all; the agent's CRS choice is graded as two soft subchecks (`crs_is_canonical`, `crs_in_meaningful_set`), and the submission is reprojected to canonical before all downstream subchecks. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" — over-penalised wrong-CRS submissions whose geometric work was correct |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T19:02:57+00:00 (commit `05aabd6`, class: `grader-change` — soft-CRS refactor)
- prior cutoff (instruction): 2026-05-28T09:36:32+00:00 (commit `2162f45`, em-dash clause paraphrase trim) — superseded by the grader cutoff above

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:25:12Z | 1.00 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-28T23:32:30Z | 1.00 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:09:37Z | 0.636 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T09:02:31Z | 1.00 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:53:06Z | 0.636 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:29:23Z | 1.00 | done | current |
| (prior 31 runs through 2026-05-28T03:17Z) | various | various | various | done | stale (pre-cutoff) |

Footnote: run-20260606-1334Z (gemma4-26b-detailed) has no score.json — the sweep was cancelled (`cancel.flag` present). Excluded.

#### Verdict
**calibrated**

Six `current` runs across three agent families (Opus, Gemma-4-26B basic and detailed, DeepSeek-V4-Pro). Spread: four at 1.0 and two at 0.636 (both Gemma under-drops — left in 5 null geometries and reported `dropped_count=15`). The 0.636 floor under the new 11-subcheck grader is the under-drop signature (5 of 11 subchecks fail; the under-dropped null geometries break four cleanup subchecks and one attribute subcheck, while CRS, per-id geometry on the common 80 ids, and the null-name preservation still pass). Both broken_under_drop (0.545) and the live Gemma under-drops (0.636) sit in the same band — exactly the discriminative middle ground the design wants. The grader machinery reproduces the three broken-solution scores under the new soft-CRS policy: 0.818 / 0.545 / 0.909, all distinct, all above 0 and below 1. The post-trim em-dash clause from 2162f45 ("a feature needs both a drawable geometry and a proper type to be useful") is discriminating rather than giving the answer away — confirmed by two independent Gemma under-drops on the present wording.

#### Specific findings
- **broken_solutions measured_score refreshed (Step 4 allows).** The new soft-CRS policy (commit 05aabd6) reshaped the broken-solution scores: `wrong_format` 0.0 → 0.818 (was Gate-1-rejected, now scored on the geometric work with two CRS subchecks failing), `under_drop` 0.444 → 0.545 (subcheck denominator went from 9 to 11), `wrong_geometry` 0.889 → 0.909 (same denominator shift). `metadata.yaml > broken_solutions > measured_score` and the `expected_score_range` were both updated; `wrong_format`'s description was rewritten to match the new behaviour. No `_make_brokens.py` edit (out of scope for the evaluator).
- **README failure-mode 5 refreshed.** "wrong CRS rejects the file before any subcheck runs" was the pre-05aabd6 behaviour; updated to describe the soft-CRS path. Weak-agent-failure paragraph re-quoted with new broken-solution scores (0.545 / 0.818 / 0.909) so the cross-references stay accurate.
- **`metadata.yaml > tolerances.rationale` annotated.** Appended a sentence noting that wrong-CRS submissions no longer Gate-1-zero — they cost two soft subchecks. Documents the calibration shift in-line where future evaluators will look.
- **`analyst_notes` authored.** Was missing on this task. Wrote a description / approach / pitfalls block covering the hidden gotcha (three defect classes hiding behind a one-line persona request, plus the null-name control rows that must survive) and the common failure modes. Human-facing only — no `version` bump.
- **Output-CRS / format consistency (Step 2c-CRS).** `expected_outputs[]` (geojson / EPSG:4326 / LineString), the reference output (CRS 4326, LineString), and the README all agree. The grader now reprojects a wrong-CRS submission to canonical for all downstream subchecks; this is a both-sides-symmetric path (canonical on both reference and submission), not a one-sided paper-over. No CRS-consistency finding.
- **Verdict upgrade vs. fourth pass.** The fourth pass returned `insufficient-evidence` (no post-2162f45 runs at the time of writing). With six current runs across three agent families now in hand — and a real two-mode score distribution (four at 1.0, two at 0.636 with the under-drop signature) — the task is `calibrated`. HR-001 from earlier passes was already resolved in 2162f45 and stays resolved; no new HRs raised.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > {wrong_format,under_drop,wrong_geometry} > measured_score` to 0.818 / 0.545 / 0.909 against the post-05aabd6 grader; widened `expected_score_range` to match; rewrote `wrong_format`'s description (no longer Gate-1-rejects); appended a sentence to `tolerances.rationale` noting the soft-CRS policy. Re-grade on reference: 1.00.
- `README.md`: refreshed failure-mode 5 (wrong-CRS) to describe the soft-CRS path; refreshed the weak-agent-failure paragraph's score cross-references (0.545 / 0.818 / 0.909). Re-grade on reference: 1.00.
- `task.json`: authored `analyst_notes` (description, approach, pitfalls). No `version` bump — `analyst_notes` is human-facing only. Re-grade on reference: 1.00.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp; all slugs validate against `coverage-vocabulary.yaml` unchanged.

#### Proposed but not applied (see HUMAN-REVIEW items)
(none — no new HRs raised this pass; HR-001 from earlier passes was resolved in 2162f45 and remains resolved.)

#### Tests run
- grader on reference: 1.00 (11/11 subchecks)
- grader on broken_wrong_format: 0.818 (matches refreshed declared [0.75, 0.9])
- grader on broken_under_drop: 0.545 (matches refreshed declared [0.45, 0.65])
- grader on broken_wrong_geometry: 0.909 (matches refreshed declared [0.85, 0.95])
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
- Geometry-type uniformity (LineString, measured on the non-null subset)
  migrated to a new `geometry_type_linestring_only` subcheck.
- Subcheck total: 11 → 12.

### Verification
- Reference solution re-graded: 1.0 (12/12 subchecks).

---

## Evaluator review 2026-06-11 (sixth pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior passes. L1 data-cleaning task targeting null / empty
handling on a contractor-style GeoJSON of Cape Town waterway centrelines,
anchored on the OSM `waterway=*` tag family. Three independent defect classes
(null `geometry`, empty `LineString` coordinates, null `waterway_type`) must
be dropped while a benign null-`name` control class (`feature_id` 21-25) is
preserved. Output is a cleaned GeoJSON in EPSG:4326 with a top-level
`dropped_count` foreign member (20). Bundled fixture is hand-crafted
(justified in `inputs/_prepare.py`).

#### Change log (delta since fifth evaluator pass)
Three commits touch the task directory since the fifth pass. Two are
benchmark-wide grader policy changes and both are design-affecting.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | f94de1b | docs-change | Fifth evaluator pass artefacts (metadata broken-score refresh for soft-CRS, README refresh, `analyst_notes` authored, status/coverage files) | Commit msg: "Re-evaluate dc-l1-capetown-waterway-nulls: calibrated; refresh broken-score metadata for soft-CRS grader" |
| 2026-06-06 | 363aed2 | grader-change | Removed the `structural_correctness` Gate 2; geometry-type uniformity migrated to a new `geometry_type_linestring_only` subcheck; subcheck total 11 -> 12. (Self-documented in the "Manual cleanup 2026-06-06" block above.) | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" - gate was inconsistent across the 36 graders and collapsed recoverable shapes to zero |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to the eight data-content subchecks (no_null_or_empty_geometry, no_null_waterway_type, dropped_count_correct, feature_count, feature_id_set, null_name_rows, geometry_preserved_per_id, attributes_preserved_per_id); the four schema/structural subchecks (geometry type, dropped_count_present, two CRS checks) stay at 1.0; weighted denominator is now 28 | Commit msg: "Weight data-content subchecks 3x across all categories" - data-content correctness should dominate schema/bookkeeping slips |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff (pre-this-pass): 2026-06-07T18:32:38Z (commit `c749e57`, class: `grader-change` - 3x data-content weighting)
- design-affecting cutoff (post-this-pass): the house-style instruction edit applied in this pass (version 2 -> 3) pushes the cutoff to this evaluator commit
- version check: all runs since 2026-05-28 were scored against `task.json` version 2; the current version is 3 after this pass's edit

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:05:29Z | 1.00 | done | current (pre-this-pass cutoff) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T09:17:52Z | 1.00 | done | current (pre-this-pass cutoff) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T13:18:26Z | 1.00 | done | stale (pre-c749e57; suite 06fd6c0 predates the weighting) |
| (prior 27 scored runs through 2026-06-06) | various | various | various | done | stale (pre-cutoff) |

Footnote: both `current` runs pass the version check (suite shas 6510297 and
ec540aa both contain c749e57 and carry task.json version 2, equal to the
pre-this-pass version). They become stale with respect to the version-3
prompt produced by this pass, but the edit is register-only (em-dash removal,
filename concretisation), so their evidential value for the drop-predicate
calibration is unchanged in substance.

#### Verdict
**insufficient-evidence**

Only two runs post-date the c749e57 weighting cutoff and both come from one
agent family (DeepSeek V4 Flash, basic + detailed prompt variants), which
fails the Step-2d two-family bar. Both scored 1.0 with byte-equivalent
output shape (80 features, dropped_count 20, EPSG:4326, LineString-only,
full column set). There is no concrete reason to suspect miscalibration:
the fifth pass established `calibrated` on six runs across three families
under the same prompt wording, and the two grader changes since are
mechanical re-weightings of the same subcheck outcomes (a fifth-pass Gemma
under-drop at 0.636 would re-weight to roughly 0.46-0.57, preserving the
discriminative middle band). No `grader-miscalibration-suspected` flag is
warranted; fresh multi-family runs against version 3 will settle it.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `waterways_clean.geojson` | instruction, persona paragraph | stated |
| LineString-only output | instruction, output-schema paragraph | stated |
| required columns feature_id/name/waterway_type | "preserving all original columns" + input data | stated/inferable |
| drop null and empty geometries | "a drawable geometry" + data inspection | stated (category level) |
| drop null waterway_type | "a proper type" + data inspection | inferable (deliberate paraphrase, see design_note) |
| keep null-name rows | "keep the rest" (drop predicate is exhaustive) | inferable |
| dropped_count present, top-level foreign member, integer | instruction, both paragraphs | stated |
| dropped_count == 20 | derivable from the data given the predicate | inferable |
| count within 5%, id Jaccard >= 0.95 | grader-internal tolerance on a deterministic predicate | inferable (standard drift margin) |
| geometry/attributes unmutated per id | "keep the rest", "preserving all original columns" | inferable |
| CRS EPSG:4326 canonical (2 soft subchecks) | GeoJSON pins WGS84 by RFC 7946 | inferable |

Factual claims verified: `capetown_waterways.geojson` exists under `inputs/`;
the column names and the 100/80/20 counts match the fixture and the reference
output; no inaccurate claim found. The pre-edit instruction referenced the
input as "the capetown_waterways bundle"; the house-style edit now names the
actual filename.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it drops exactly the
null/empty-geometry and null-waterway_type rows, keeps everything else,
preserves attributes verbatim, and injects the `dropped_count` foreign member
via a json round-trip. The only operation the prompt does not ask for is a
stable sort by `feature_id` before serialisation; the input is already
ordered by `feature_id`, so the sort is a determinism device with no effect
on content, and the grader is order-insensitive (per-id joins and set
Jaccard). Not flagged.

#### Specific findings
- **Stale broken-solution metadata after two grader-policy commits (fixed
  unilaterally).** `metadata.yaml > broken_solutions > measured_score` still
  recorded the 11-subcheck soft-CRS values (0.818 / 0.545 / 0.909); under the
  current 12-subcheck weighted grader the brokens measure 0.929
  (wrong_format, 26/28), 0.464 (under_drop, 13/28), 0.893 (wrong_geometry,
  25/28). `wrong_format`'s old `expected_score_range` [0.75, 0.9] no longer
  contained the measured value. Refreshed all three scores, adjusted the two
  affected ranges ([0.85, 0.97] and [0.4, 0.6]), and rewrote the weighted
  arithmetic in the descriptions. The three brokens remain pairwise distinct
  and the under-drop keeps its discriminative middle band.
- **Stale Gate-2 language in `tolerances.rationale` (fixed unilaterally).**
  The rationale still described geometry-type as a "Gate 2 element"; Gate 2
  was removed benchmark-wide in 363aed2. Rewrote the sentence and appended a
  note documenting the c749e57 weighting (weighted denominator 28).
- **House-style violations in the instruction (fixed unilaterally, version
  2 -> 3).** The instruction contained two em-dash constructions ("Hi - first
  time...", "...usable waterway - a feature needs ... - and keep the rest"),
  referenced the input as "the capetown_waterways bundle" instead of the
  filename, and used the jargon phrase "with the feature identifier as the
  identity key". Rewrote per the house-style rules: em-dashes replaced with
  a comma and parentheses, filename concretised to
  `capetown_waterways.geojson`, identity-key phrase replaced with "with
  feature_id as the key field". The calibrated dash-clause content ("a
  feature needs both a drawable geometry and a proper type to be useful") is
  preserved verbatim inside parentheses, so the design_note calibration
  evidence still applies. Reference re-grade: 1.0 (12/12).
- **`analyst_notes` pitfall arithmetic was wrong (fixed unilaterally).** The
  first pitfall claimed geometry.isna()-only filtering leaves "the ten
  null-waterway_type rows" and lands at "fifteen dropped instead of twenty";
  in fact isna() drops the ten JSON-null rows (ids 1-5, 11-15), leaving five
  empty LineStrings and five null-waterway_type rows, for ten dropped.
  Verified against `broken_under_drop` (90 features, dropped_count 10).
  Corrected the numbers. analyst_notes is human-facing; no extra bump needed
  beyond the instruction bump already taken.
- **README cross-references refreshed (docs-change).** Failure-mode scores
  (0.444/0.818/0.889 -> 0.464/0.929/0.893), stale "subcheck N" ordinals
  (numbering shifted when geometry-type became subcheck 1's neighbour),
  the weak-agent paragraph's weighted arithmetic, and the pre-reorg input
  path `data/capetown_waterways.geojson` -> `inputs/capetown_waterways.geojson`.
- **Output-CRS / format consistency (Step 2c-CRS).** `expected_outputs[]`
  (geojson / EPSG:4326 / LineString), the reference output, and the README
  agree. The soft-CRS path reprojects a non-canonical submission to the
  canonical CRS for downstream subchecks per the declared accept-list policy;
  no one-sided paper-over. No finding.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style instruction rewrite (em-dashes removed, input
  filename concretised, "identity key" jargon replaced); `version` 2 -> 3;
  `analyst_notes` pitfall arithmetic corrected. Re-grade on reference: 1.00
  (12/12). Reason: Step-4 house-style rule; analyst_notes refresh rule.
- `metadata.yaml`: refreshed `broken_solutions > measured_score` to
  0.929 / 0.464 / 0.893 against the post-c749e57 weighted grader; adjusted
  `expected_score_range` for wrong_format and under_drop; rewrote the
  weighted arithmetic in the descriptions; fixed stale Gate-2 language in
  `tolerances.rationale` and documented the weighting. Re-grade on
  reference: 1.00. Reason: Step-4 measured_score refresh; rationale text is
  documentation only (no tolerance value changed).
- `README.md`: refreshed broken-solution score cross-references, removed
  stale subcheck ordinals, fixed pre-reorg input path. Reason: docs-change.
- `coverage.yaml`: refreshed `evaluator_run_at`; slugs unchanged and all
  validate against `coverage-vocabulary.yaml`.

#### Proposed but not applied (see HUMAN-REVIEW items)
(none - no HRs raised this pass)

#### Tests run
- grader on reference: 1.00 (12/12 subchecks)
- grader on broken_wrong_format: 0.929 (matches refreshed declared [0.85, 0.97])
- grader on broken_under_drop: 0.464 (matches refreshed declared [0.4, 0.6])
- grader on broken_wrong_geometry: 0.893 (matches declared [0.85, 0.95])
- pytest: pass (41/41)

---

## Evaluator review 2026-06-14 (seventh pass - subcheck weight recalibration)  (evaluator-commit <pending>)

**RECALIBRATED.** Replaced the blunt c749e57 "weight 3.0 on all eight
data-content subchecks" scheme with a three-tier severity weighting keyed to
how central each failure is to this task's null/empty-cleanup skill. Grading-only
change: only subcheck `weight=` values edited; no logic, threshold, gate, or
`task.json` version change.

### Reasoning
The central skill is null/empty handling: recognise the three defect classes
(null geometry, empty LineString, null `waterway_type`) and drop them while
preserving the benign null-`name` rows. The c749e57 commit gave weight 3.0 to
all eight "data-content" subchecks, which conflated the detectors of the actual
drop predicate with no-mutation and report-value checks - e.g. it weighted
`dropped_count_correct` (a reporting side-channel) as heavily as the actual
cleaning detectors, and weighted a coordinate-jitter (no-mutation) the same as
missing a whole defect class. Re-tiered:
- **4.0 - central cleaning detectors:** `no_null_or_empty_geometry_in_output`,
  `no_null_waterway_type_in_output`, `feature_id_set_preserved`,
  `null_name_rows_preserved`. These detect a wrong drop predicate (missed a
  defect class, or over-dropped the null-name rows) - the skill the task tests.
- **2.5 - no-mutation:** `geometry_preserved_per_id`, `attributes_preserved_per_id`.
  Real data corruption, but peripheral to the drop decision. Set above 2x the
  CRS weight so a coordinate-mutation slip scores below a pure CRS slip.
- **2.0 - derivative / report value:** `feature_count_within_tolerance`,
  `dropped_count_correct`. Consequences of a correct drop plus the reporting
  side-channel, not the cleaning skill itself.
- **1.0 - structural / cosmetic (unchanged):** `geometry_type_linestring_only`,
  `dropped_count_present`, `crs_is_canonical`, `crs_in_meaningful_set`.

Weighted denominator: 28 -> 29.

### Weight changes
| Subcheck | old | new |
|---|---|---|
| no_null_or_empty_geometry_in_output | 3.0 | 4.0 |
| no_null_waterway_type_in_output | 3.0 | 4.0 |
| feature_id_set_preserved | 3.0 | 4.0 |
| null_name_rows_preserved | 3.0 | 4.0 |
| geometry_preserved_per_id | 3.0 | 2.5 |
| attributes_preserved_per_id | 3.0 | 2.5 |
| feature_count_within_tolerance | 3.0 | 2.0 |
| dropped_count_correct | 3.0 | 2.0 |
| geometry_type_linestring_only | 1.0 | 1.0 (unchanged) |
| dropped_count_present | 1.0 | 1.0 (unchanged) |
| crs_is_canonical | 1.0 | 1.0 (unchanged) |
| crs_in_meaningful_set | 1.0 | 1.0 (unchanged) |

### Broken scores before -> after
| Broken | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.929 | 0.931 | cosmetic CRS-only slip; smallest drop |
| wrong_geometry | 0.893 | 0.914 | coordinate mutation (no-mutation tier); sits just below wrong_format |
| under_drop | 0.464 | 0.448 | central-skill failure (missed 2 of 3 defect classes); largest drop, clearly separated |

Ordering: monotone and defensible - cosmetic (0.931) > mutation (0.914) >>
central-cleaning failure (0.448). The three brokens fail disjoint subcheck
groups (CRS / cleaning-detectors+report / no-mutation), so up-weighting the
central group only deepens under_drop and cannot invert the ordering. The
wrong_geometry < wrong_format ordering is preserved because the no-mutation
weight (2.5) exceeds the two CRS weights combined (2 x 1.0).

### Prior-run re-grade summary (current task version)
12 of the listed runs grade 1.0 under both old and new weights (reference-shaped
clean outputs). The discriminating runs are the under-drop-signature runs, which
shift slightly but stay in their middle band: run-20260606-0953Z 0.571 -> 0.638
(attribute-mutating under-drop), run-20260529-0109Z 0.571 -> 0.586 and
run-20260527-2321Z 0.571 -> 0.586 (null-geometry-leaving under-drops). The two
`current` runs the sixth pass relied on (run-20260608-074701Z, run-20260609-084636Z)
stay 1.0. No re-grade crossed a pass/fail-shaped boundary; the recalibration only
changes the magnitude of partial-credit deductions.

### Note (not changed)
No threshold, gate, or check logic touched. The Jaccard 0.95 floor,
1e-7 deg Hausdorff floor, +-5% count tolerance, and strict dropped_count equality
are all left as-is and remain sensible for this deterministic fixture.

### Tests run (weights only; orchestrator runs pytest)
- grader on reference: 1.00 (12/12 subchecks)
- grader on broken_wrong_format: 0.931 (matches refreshed declared [0.85, 0.97])
- grader on broken_under_drop: 0.448 (matches refreshed declared [0.4, 0.6])
- grader on broken_wrong_geometry: 0.914 (matches declared [0.85, 0.95])
- pytest: not-run (orchestrator)
