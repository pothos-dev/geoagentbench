# Implementation notes — geo-l2-bangkok-landuse-intersect

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L2 geometric-ops chain over a bundled Bangkok `base.land_cover`
GeoParquet (~21 660 polygons, 8 classes) plus a hand-crafted BMA
study-area GeoJSON, both in EPSG:32647. Agent must `make_valid` →
intersect → coerce-to-MultiPolygon → simplify(5 m) → write GeoJSON
with `class` + `area_m2`. Reference, grader, and three broken
solutions verified inside the project Docker container.

## Verification results
- Reference grader score: 1.000 (5 / 5 subchecks pass).
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    (file is GeoParquet, not a GeoJSON FeatureCollection).
  - not_intersected: 0.400 (expected range [0.30, 0.50]) — three
    subchecks fail (`count_within_tolerance`,
    `total_area_within_tolerance`, `unioned_geometry_iou`); class
    set still matches.
  - area_in_km2: 0.800 (expected range [0.70, 0.85]) — only
    `total_area_within_tolerance` fails (rel diff 1.0).
- Second-run output match: bit-identical (verified with `diff -q`
  on `reference/outputs/bma_landcover_intersect.geojson` between
  two runs inside Docker; output is sorted by Overture `id` and
  pyogrio's GeoJSON writer is byte-stable for fixed inputs and
  pinned dependency versions).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Output not a GeoJSON: broken_wrong_format
- Wrong output CRS: principled — Gate 1 CRS check
- Skipped intersection (un-clipped output): broken_not_intersected
- Wrong area units (km² instead of m²): broken_area_in_km2
- Skipped make_valid before intersection: principled — bundled-input
  promise + count-tolerance subcheck (catches the cascading
  GEOS-failure variant)
- Forgot MultiPolygon coercion: principled — `all_multipolygon`
  subcheck
- Missing required column: principled — Gate 1 required-columns
  check

## Open issues
(none)

## Suggested prompt changes
(none)

## Inventory change proposals
(none — the inventory row's GeoParquet input + GeoJSON output +
EPSG:32647 + Polygon → MultiPolygon + invalid-rings data-quality
issue + ~10⁴ medium-scale tier all matched cleanly. `base.land_cover`
over the chosen Bangkok bbox returned 21 660 polygons, the upper
end of the medium tier.)

## Library extensions
(none — grader uses `Gate`, `Subcheck`, `ScoreReport`,
`count_within_tolerance`, `iou_with_tolerance`, and
`jaccard_similarity_set`. The per-feature attribute compare is
inline because the output is keyed by feature `id` rather than
class, and a new primitive specifically for that pattern would
not be reused by other tasks.)

## Runtime
~25 minutes (Overture slice ~30 s, reference run ~25 s, broken-solution
generation ~50 s; all runs inside the project Docker container).

---

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 as an L2 geometric-ops chain over a bundled Bangkok
`base.land_cover` GeoParquet (~21 660 polygons / 8 classes) plus a hand-crafted
BMA study-area GeoJSON, both in EPSG:32647 (WGS84 / UTM 47N). The agent had to
`make_valid` invalid bowtie rings, intersect each cleaned land-cover polygon
with the study-area polygon, simplify at 5 m (planar), coerce to MultiPolygon,
and write a GeoJSON FeatureCollection with `class` + `area_m2` per surviving
feature. Output CRS was originally pinned to EPSG:32647 in both `task.json`
and the reference solution; the persona framing ("flood-mitigation briefing,
preview in browser") motivated the simplify step and the size constraint.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | ca7fa01 | initial-authoring | Initial task (instruction names UTM 47N / EPSG:32647 explicitly; output pinned to EPSG:32647). | (initial) |
| 2026-05-08 | 001e459 | docs-change (path-only rename) | Move tree from `benchmark/tasks/` to `benchmark/eval/tasks/`. | Commit msg: "split into authoring/ and eval/ subtrees". |
| 2026-05-13 | a3a8d53 | docs-change | Move back to `benchmark/tasks/`. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/". |
| 2026-05-13 | 8915010, 1b8dda1, 3c65373, cfbdc7c | docs-change | Generate / regenerate `image-prompt.md` and `image.webp`. | Commit msgs: image authoring batches. |
| 2026-05-13 | 12c9fb0 | (no diff against this task — sibling commit) | — | — |
| 2026-05-14 | f40e39e | prompt-change | Drop "Overture-style", drop "in UTM 47N (EPSG:32647)", drop "in the same CRS"; keep "computed in EPSG:32647 metres squared" and "in EPSG:32647" for the output. | Commit msg: "Strip deducible information from GEO task instructions". |
| 2026-05-15 | 6500d9a | prompt-change | Further strip: drop the explicit "EPSG:32647 metres squared" hint and the "in EPSG:32647" output-CRS pin; keep "5 m tolerance" and the named output filename. | Commit msg: "Strip deducible information from GEO task instructions (batch 2)". |
| 2026-05-17 | 64740d0 | prompt-change | Soften "simplified at 5 m tolerance" → "simplified enough that the file is small". | Commit msg: "Remove answer-giving nudges from data-cleaning task prompts" (touched this geo task incidentally). |
| 2026-05-17 | db638f4 | mixed (grader-change + prompt-tags-change) | Grader: replace `EPSG:32647` check with `is_wgs84()` (accepts 4326 / OGC:CRS84); reproject submission to EPSG:32647 only for geometric comparison. `task.json` tag and `expected_outputs[].crs` flipped from `EPSG:32647` to `EPSG:4326`. **Reference output and `reference/solution/generate.py` were NOT updated** — they still write EPSG:32647. | Commit msg: "Fix graders and prompts for 6 tasks that regressed after nudge removal … GeoJSON tasks now expect WGS 84 instead of projected CRS, with reprojection to reference CRS for geometric comparison". |
| 2026-05-26 | 29a9ae3 | mixed (path rename only) | Folder reorg: `data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `image*` → `assets/`. Path constants in `grade.py`, `generate.py`, `_make_brokens.py` updated. No semantic change. | Commit msg: "Reorganize task folder layout". |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T19:17:27+00:00** (commit `db638f4f`, class: mixed — grader CRS change + `task.json` CRS tag flip).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T09:00:36Z | 0.0 | done (gate fail) | current |
| run-20260517-1424Z and 25 earlier | various | 2026-05-12 → 2026-05-17 (pre-cutoff) | mixed (e.g. 1.0 on `run-20260517-1424Z`) | done | stale (pre-cutoff; not used as evidence, listed only as context) |

Only one `current` run exists; insufficient diversity for normal calibration analysis. However, the diagnostic does not need run diversity here — the failure is reproducible against the reference itself (see below).

#### Verdict
**prompt-grader-inconsistent** (additionally, the reference solution is broken under the current grader — a `reference-or-data-edit-needed` issue, not a model-side failure).

Commit `db638f4f` switched the grader's Gate 1 from "CRS must be EPSG:32647" to "CRS must be WGS 84 (EPSG:4326 / OGC:CRS84)" and reproject-for-comparison. It also flipped the `task.json` CRS tag and `expected_outputs[0].crs` to `EPSG:4326`. But it did **not** regenerate `reference/solution/outputs/bma_landcover_intersect.geojson` (still EPSG:32647, written by `reference/solution/generate.py` which still has `TARGET_CRS = "EPSG:32647"`) and did **not** regenerate the three `reference/failures/broken_*/outputs/`. As a result:

- Running the current `grade.py` on `reference/solution/outputs/` returns score **0.0** with `format_schema_valid` failing for "CRS is 32647, expected WGS 84". Verified: `cd benchmark/eval && uv run python ../tasks/geo-l2-bangkok-landuse-intersect/grade.py ../tasks/geo-l2-bangkok-landuse-intersect/reference/solution/outputs`.
- All three broken sets also fail Gate 1 (same reason), so `metadata.yaml > broken_solutions > measured_score` values (0.0 / 0.4 / 0.8) are obsolete; the current measured scores are all 0.0.
- In `run-20260526-0748Z` the agent (Gemma 4 26B) produced a credibly-structured intersected MultiPolygon GeoJSON in EPSG:32647 (the inputs' CRS, and the CRS the reference itself uses); the grader rejected it on Gate 1 alone. The agent output was not obviously wrong on the operations under test — it was rejected purely on the CRS gate.

The instruction (post-commit 6500d9a) intentionally no longer names a CRS, and per RFC 7946 a bare GeoJSON FeatureCollection is conventionally WGS84. So the grader's WGS84 expectation is defensible against the instruction. The mismatch is between (a) the grader + `task.json` (both say WGS84) and (b) the reference solution outputs + `reference/solution/generate.py` + `README.md` + `inventory.md` (all still say EPSG:32647). Since this evaluator may not edit `reference/solution/generate.py`, `inputs/`, or `reference/failures/`, the fix has to be flagged for a human.

Additionally:
- `README.md` "Output" section still says GeoJSON in EPSG:32647 and still lists `id` as an output column; the grader does not check `id` and `task.json` only requires `class` + `area_m2` + geometry. `id` is not load-bearing; the EPSG:32647 claim is now stale.
- `metadata.yaml > tolerances > rationale` still says "agent must … write GeoJSON in WGS 84" via the indirect reading "report `class` + `area_m2`" — but the rationale text is silent on output CRS; nothing wrong there.
- `inventory.md` row says "CRS out: EPSG:32647" — disagrees with current `task.json` (EPSG:4326). Inventory-mismatch flag.

#### Specific findings
- Reference solution generates EPSG:32647 output but current grader rejects non-WGS84. Reference is unilaterally unfixable (forbidden). <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="med" --> The reference solution and three broken outputs need to be regenerated in EPSG:4326 (or `reference/solution/generate.py` updated to write WGS84 GeoJSON and reproject before computing `area_m2`). Until then the task is unsolvable end-to-end against the reference and `metadata.yaml > broken_solutions > measured_score` is stale (all three sets now score 0.0). Marked `med` per the evaluator prompt's rule that per-task scoring quirks are `med` at most (this does not affect any other task; it is localised to this one).
- `README.md` still describes output as "GeoJSON, EPSG:32647, one row per land-cover feature" and lists `id` as a required column. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Update README to match `task.json` (WGS84 output, only `class` + `area_m2` + geometry checked). Could be applied unilaterally as docs-only — but the grader/reference inconsistency above must be resolved first, since the README's correct text depends on which side wins. Held back pending HR-001.
- `inventory.md` row still says CRS out = EPSG:32647 while `task.json` says EPSG:4326. <!-- HUMAN-REVIEW id="HR-003" category="inventory-mismatch" severity="low" --> Inventory needs the same update as the README once HR-001 lands. Out of scope for this evaluator (inventory.md is outside the task directory).
- The Gemma run wrote EPSG:32647 because that is what both inputs are in and what the reference output is in — entirely consistent with the design that existed before commit `db638f4f`. The post-cutoff design assumes the agent will reproject to WGS84 because it is writing a GeoJSON. Whether this is a fair test of a small open model is borderline — the format convention is correct, but the instruction provides no nudge and the reference itself signals the opposite. Flagging the strictness as a borderline judgment, contingent on HR-001 being resolved. <!-- HUMAN-REVIEW id="HR-004" category="prompt-vs-grader-judgment" severity="med" --> Consider whether the instruction should re-name the GeoJSON output CRS explicitly (e.g. "WGS84 GeoJSON") to avoid penalising agents that mirror the inputs' CRS when no instruction-level signal pushes them toward 4326.

### 3. Changes applied this run

#### Unilateral edits
- (none)

The two obvious unilateral candidates — loosening the grader's CRS gate to accept EPSG:32647, or "stripping a gift" in the instruction — were both rejected:
- Loosening the grader would revert the intentional commit `db638f4f` whose stated purpose was the WGS84/RFC-7946 convention. The grader is *defensible*; the reference is the inconsistency. Flag, do not silently revert.
- Stripping a gift in the instruction is not the problem here; the instruction is already maximally stripped.
The right fix is to regenerate `reference/solution/outputs/` and `reference/failures/broken_*/outputs/` in EPSG:4326, which requires editing `reference/solution/generate.py` and `_make_brokens.py` — both forbidden for this evaluator.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — Regenerate reference + broken outputs in EPSG:4326 (or update grader / instruction to re-pin EPSG:32647; pick one).
- HR-002 — design-rationale — Update `README.md` Output section to match the post-`db638f4f` CRS / column contract (do after HR-001).
- HR-003 — inventory-mismatch — Update `benchmark/authoring/inventory.md` row CRS-out to EPSG:4326 (do after HR-001).
- HR-004 — prompt-vs-grader-judgment — Consider re-adding an explicit GeoJSON-WGS84 hint to the instruction.

#### Tests run
- grader on reference: **0.0** (Gate 1 fails — "CRS is 32647, expected WGS 84")
- grader on broken_wrong_format: 0.0 (still fails Gate 1 on JSON-sniff before reaching the CRS check — `measured_score` 0.0 unchanged)
- grader on broken_not_intersected: 0.0 (Gate 1 fails — CRS, not the intended `count` / `total_area` / `iou` subcheck failures)
- grader on broken_area_in_km2: 0.0 (Gate 1 fails — CRS, not the intended `total_area_within_tolerance` failure)
- pytest: **pass** (35 / 35 in `benchmark/eval/`)

## Evaluator review 2026-05-26 (second pass)  (evaluator-commit <pending>)

### 1. Design history

No new design-affecting commits since the first-pass block above. The only commit
touching this task directory since is the prior evaluator's own artefact commit
`fcf6f866` (2026-05-26T14:29Z, docs/audit-only: `audit/AUTHORING_HISTORY.md`,
`coverage.yaml`, `audit/status.json`). The full change log in the first-pass block
remains accurate; the design-affecting cutoff is unchanged at commit `db638f4f`
(2026-05-17T19:17:27+00:00).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-17T19:17:27+00:00** (commit `db638f4f`, class: mixed — grader CRS gate flipped to `is_wgs84()` + `task.json` `expected_outputs[].crs` flipped to EPSG:4326). Unchanged from the first pass.

#### Runs considered
Three `current` runs now exist (all post-cutoff; the two newest also post-date the
first-pass evaluator commit):

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T19:22Z | **1.0** | done (5/5) | current |
| run-20260526-1753Z | claude-code-opus-basic (opus) | 2026-05-26T17:53Z | **1.0** | done (5/5) | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:00Z | **0.0** | done (Gate-1 CRS fail) | current |

Stale (pre-cutoff) runs from 2026-05-12 → 2026-05-17 are listed for context in the
first-pass block; not used as evidence.

#### Verdict
**calibrated** — this overturns the first pass's `prompt-grader-inconsistent` verdict.

The first pass concluded the task was "unsolvable end-to-end against the reference"
because running `grade.py` on `reference/solution/outputs/` returns 0.0. That premise
is a category error. The grader's design is: Gate 1 requires the **submission** to be
WGS84 (consistent with `task.json` `expected_outputs[].crs = EPSG:4326` and RFC 7946 for
a CRS-unspecified GeoJSON), and then it reprojects the submission to `REF_EPSG = 32647`
for geometric comparison against the reference (`grade.py:47,116`). The reference output
is the *comparison target* held in EPSG:32647 — it is **not** a submission and was never
required to pass Gate 1. Feeding the reference output back through `grade.py` as if it
were a submission is not a meaningful self-check; the 0.0 it produces says nothing about
whether the task is solvable.

The two fresh runs prove solvability directly. Both Opus (`run-20260526-1753Z`) and the
weak Gemma 4 26B (`run-20260526-1922Z`) wrote **WGS84** GeoJSON (CRS84 lon/lat ≈100.5°E,
13.5°N), passed Gate 1, and scored a perfect 5/5: 3453 features (exactly matching the
3453-feature reference), class-set Jaccard 1.0, total area 980 026 998 m² vs reference
980 020 971 m² (rel diff 0.0000), unioned IoU 1.0. The grader reprojects their WGS84
output to 32647 and it lands on the reference. Verified by reading both `score.json`
files and both output `crs` members.

The grader also correctly *discriminates*: the earlier Gemma run `run-20260526-0748Z`
produced 3453 geometrically-correct features but wrote them in **EPSG:32647** and was
rejected on the Gate-1 CRS check (score 0.0). That is exactly README failure mode #2
("Output in the wrong CRS … Gate 1's CRS check rejects") working as designed — a real
failure-detection event, not a grader bug. So across three runs the task spans
{0.0 (wrong output CRS), 1.0, 1.0} and distinguishes a weak model's two attempts from
each other. That is a calibrated task with a meaningful, non-trivial CRS-convention
discriminator.

The genuinely valid sub-finding from the first pass survives, narrowed: the two
non-format **broken solutions** are stored in EPSG:32647 and now hit the Gate-1 CRS
check before reaching the subchecks they were authored to exercise, so
`broken_not_intersected` (intended 0.4) and `broken_area_in_km2` (intended 0.8) both
collapse to 0.0. `broken_wrong_format` still correctly scores 0.0 (it is GeoParquet
bytes; the JSON-sniff rejects it before the CRS check). This makes the
`metadata.yaml > broken_solutions > measured_score` values for the two non-format sets
stale, and means those two sets no longer test their intended discriminating subchecks.
The remedy is to regenerate the two broken outputs in WGS84 (edit
`reference/failures/_make_brokens.py` — forbidden for this evaluator). This is a
broken-solution / data-calibration issue, **not** a "task unsolvable" issue, and does
not affect agent grading (proven by the live runs). Flagged HR-001 (re-scoped).

The first pass's HR-004 (prompt-vs-grader strictness — "is requiring WGS84 fair to a
small model when the instruction names no CRS?") is now empirically resolved: the same
weak model that failed on CRS in one attempt got it right in another, and Opus got it
right. The format convention is learnable and the discriminator is fair. I do not carry
HR-004 forward.

#### Specific findings
- Task is solvable and calibrated; the grader correctly accepts WGS84 submissions and
  reprojects for geometric comparison. The "reference grades 0.0" observation reflects
  the reference being the 32647 comparison target, not a submission — no action needed
  on the grader or reference solution for solvability.
- `broken_not_intersected` and `broken_area_in_km2` outputs are stored in EPSG:32647 and
  now fail Gate 1 (CRS) before reaching their intended subchecks, scoring 0.0 instead of
  0.4 / 0.8. Fix requires regenerating them in WGS84 via `_make_brokens.py` — forbidden
  for this evaluator. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" --> Regenerate the two non-format broken outputs in EPSG:4326 (add a `.to_crs(4326)` before the GeoJSON write in `_make_brokens.py`, or set its `TARGET_CRS` write step to WGS84 while keeping `area_m2` computed in the metric CRS), then re-measure. Severity `low`: does not affect live agent grading, only the offline broken-solution calibration fixtures.
- `README.md` Output section still describes the output as "GeoJSON, EPSG:32647" and
  lists an `id` column the grader does not require. The live contract is WGS84 GeoJSON
  with `class` + `area_m2` + geometry. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Update the README Output paragraph to say WGS84 (EPSG:4326), and drop / soften the `id` row (`id` is carried through by the reference but not checked). Left as a flag rather than a unilateral edit because a generic README content rewrite is not in the evaluator's Step-4 unilateral list; trivial for a human to apply.
- `benchmark/authoring/inventory.md` row for this task still records CRS out = EPSG:32647
  while `task.json` says EPSG:4326. <!-- HUMAN-REVIEW id="HR-003" category="inventory-mismatch" severity="low" --> Update the inventory CRS-out to EPSG:4326. Outside the task directory; out of scope for this evaluator to edit.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: updated `broken_solutions > {not_intersected,area_in_km2} > measured_score` to 0.0 (current grader result) with a rationale note that they now hit the Gate-1 CRS check; `wrong_format` measured_score 0.0 unchanged. Re-grade on reference: 0.0 by design (reference is the 32647 comparison target, not a submission); live agent runs score 1.0. Reason: Step 4 explicitly permits refreshing `broken_solutions.measured_score` to the current grader's score with one re-run.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — regenerate `broken_not_intersected` + `broken_area_in_km2` outputs in EPSG:4326 (needs `_make_brokens.py`, forbidden here).
- HR-002 — design-rationale — update `README.md` Output section to the WGS84 contract and drop the unchecked `id` column.
- HR-003 — inventory-mismatch — update the `inventory.md` CRS-out to EPSG:4326.

#### Tests run
- grader on reference outputs (as a submission): 0.0 — expected, reference is the 32647 comparison target, not a submission. Solvability is proven instead by two live 1.0 runs (Opus + Gemma).
- grader on broken_wrong_format: 0.0 (Gate-1 JSON-sniff; intended).
- grader on broken_not_intersected: 0.0 (Gate-1 CRS; intended 0.4 — stale, see HR-001).
- grader on broken_area_in_km2: 0.0 (Gate-1 CRS; intended 0.8 — stale, see HR-001).
- live runs: run-20260526-1753Z (opus) 1.0; run-20260526-1922Z (gemma) 1.0; run-20260526-0748Z (gemma) 0.0 (wrong output CRS, correctly caught).
- pytest: **pass** (35 / 35 in `benchmark/eval/`).

## Evaluator review 2026-05-27 (third pass)  (evaluator-commit <pending>)

### 1. Design history

One new design-affecting commit since the second-pass block, and it is the
human resolution of the prior pass's HR-001/HR-002:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-27 | 1f4a85c6 | mixed (reference-change + grader-change + docs-change) | `reference/solution/generate.py` now computes `area_m2` in EPSG:32647 then `to_crs(EPSG:4326)` before the GeoJSON write (new `WORK_CRS`/`OUTPUT_CRS` split); the reference output `bma_landcover_intersect.geojson` was regenerated in WGS84/CRS84; `grade.py` dropped `REF_EPSG = 32647` and the one-sided `sub = sub.to_crs(epsg=REF_EPSG)` reproject so geometric comparison is now done in WGS84 on both sides; `README.md` Output section + failure-mode #2 + "what this probes" rewritten to the WGS84 contract. | Commit msg: "Store bangkok/nyc-park reference output in WGS84, drop one-sided grader reproject … align everything on WGS84 … reference self-grades 1.0 and existing opus/gemma runs score unchanged." |

Note: this commit did **not** touch `metadata.yaml` and did **not** regenerate
`reference/failures/broken_*/outputs/` — those broken fixtures remain in EPSG:32647
(see Step 2 below). `reference/failures/_make_brokens.py` still pins `TARGET_CRS = "EPSG:32647"`.

The full change log in the first-pass block remains accurate for everything up to
commit `db638f4f`; commit `1f4a85c6` is appended above.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-27T14:06:03+00:00** (commit `1f4a85c6`, class: mixed — reference output regenerated to WGS84 + grader one-sided reproject removed). This advances the cutoff from the second pass's `db638f4f`.

#### 2c-CRS consistency check (new in evaluator prompt)
All four sides now agree on the output CRS contract:
- Reference output `bma_landcover_intersect.geojson` CRS: **WGS84 / CRS84** (verified by reading the file's `crs` member).
- `task.json` `expected_outputs[0].crs`: **EPSG:4326**.
- `grade.py` Gate 1: requires `is_wgs84(sub.crs)`; geometric IoU is computed in WGS84 on **both** sides equally (no one-sided reproject anymore) — compliant with the 2c-CRS rule. `area_m2` is the stored attribute column (projected metres²) on both sides; total-area subcheck sums the column without reprojecting, so it is symmetric.
- `README.md` Output section: "GeoJSON, WGS84 (EPSG:4326)" and failure-mode #2 ("left in projected EPSG:32647") — consistent.

The only residual CRS disagreement is `benchmark/authoring/inventory.md` (CRS out = EPSG:32647, line 581) — outside the task directory; carried as HR-002.

#### Runs considered
All three runs from the second pass predate the new cutoff and are therefore now **stale**. There are **no current runs** (none started after 2026-05-27T14:06:03Z).

| Run | Adapter | Started | Score (recorded) | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1922Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T19:44:55Z | 1.0 | done | stale (pre-cutoff) |
| run-20260526-1753Z | claude-code-opus-basic (opus / claude-opus-4-7) | 2026-05-26T19:01:51Z | 1.0 | done | stale (pre-cutoff) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T09:00:36Z | 0.0 | done (Gate-1 CRS fail) | stale (pre-cutoff) |

Earlier runs 2026-05-12 → 2026-05-17 are stale as before.

No current runs exist, but I have a concrete, reproducible basis for the verdict that does not depend on run state: the reference self-grades 1.0 under the current grader, and I re-graded all three stale run outputs under the **current** grader to confirm the grader change in `1f4a85c6` is score-preserving for them.

#### Verdict
**calibrated** — confirms the second pass; the prior HR-001 ("reference grades 0.0", "non-format brokens collapse") is now resolved on the live side by commit `1f4a85c6`.

Evidence:
- Grader on `reference/solution/outputs/` now returns **1.0** (5/5): 3453 features, class Jaccard 1.0, total area 980 020 971 m² (rel diff 0.0000 vs reference, i.e. self-identical), unioned IoU 1.0. The "reference grades 0.0 as a submission" pathology from the first/second pass is gone — the reference output is itself WGS84 now and passes Gate 1.
- Re-grading the three stale run outputs under the **current** grader reproduces their recorded scores exactly: run-20260526-1753Z (opus, CRS84 output) → 1.0 (5/5); run-20260526-1922Z (gemma, CRS84 output) → 1.0 (5/5); run-20260526-0748Z (gemma, **EPSG::32647** output) → 0.0 on the Gate-1 CRS check. So the grader change is score-preserving, and the task still spans {0.0 (wrong output CRS), 1.0, 1.0} with a meaningful, fair CRS-convention discriminator — exactly README failure mode #2 working as designed.
- pytest: 35/35 pass under the current tree.

#### Specific findings
- Reference, grader, `task.json`, and README now agree on the WGS84 output contract (resolved by commit `1f4a85c6`). No action needed on solvability or CRS consistency within the task directory.
- The two non-format broken fixtures (`broken_not_intersected`, `broken_area_in_km2`) are **still** stored in EPSG:32647 (commit `1f4a85c6` regenerated only the reference solution output, not the broken fixtures; `_make_brokens.py` still pins `TARGET_CRS = "EPSG:32647"`). They consequently still fail Gate 1's WGS84 CRS check (score 0.0) before reaching the subchecks they were authored to fail (intended 0.4 / 0.8). `broken_wrong_format` still correctly scores 0.0 (JSON-sniff, before the CRS check). `metadata.yaml > broken_solutions > measured_score` already records 0.0 for all three with STALE rationale notes — those notes remain accurate, so no metadata edit is warranted this pass. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" --> Regenerate the two non-format broken outputs in EPSG:4326 by mirroring the reference fix in `reference/failures/_make_brokens.py` (compute `area_m2` in EPSG:32647, then `to_crs(EPSG:4326)` before `out.to_file(...)`), then re-measure that they land at 0.4 / 0.8 under the current grader and refresh `metadata.yaml`. Forbidden for this evaluator (`reference/failures/`). Severity `low`: affects only offline broken-solution calibration fixtures, not live agent grading (proven by the re-graded runs).
- `benchmark/authoring/inventory.md` row for this task (line 581) still records CRS out = EPSG:32647 while `task.json`, the reference, and the README all now say EPSG:4326. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Update the inventory CRS-out to EPSG:4326. Outside the task directory; out of scope for this evaluator to edit.
- README still lists an `id` column in its Output table. This is now *accurate* (the reference carries `id` through — `generate.py:88`) even though the grader does not require it; not load-bearing and not stale. No action.

### 3. Changes applied this run

#### Unilateral edits
- (none) — the task directory is internally CRS-consistent after commit `1f4a85c6`; the only remaining issues are the forbidden broken-fixture regeneration (HR-001) and the out-of-directory inventory row (HR-002). `metadata.yaml`'s broken-solution `measured_score`/STALE notes already match the current grader output (0.0 for all three), so no refresh is warranted.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — regenerate `broken_not_intersected` + `broken_area_in_km2` outputs in EPSG:4326 via `_make_brokens.py` (forbidden here), then refresh `metadata.yaml`.
- HR-002 — inventory-mismatch — update the `benchmark/authoring/inventory.md` CRS-out for this row to EPSG:4326.

#### Tests run
- grader on reference outputs (as a submission): **1.0** (5/5) — reference is now WGS84 and self-grades cleanly.
- grader on broken_wrong_format: 0.0 (Gate-1 JSON-sniff; intended).
- grader on broken_not_intersected: 0.0 (Gate-1 CRS; intended 0.4 — stale, see HR-001).
- grader on broken_area_in_km2: 0.0 (Gate-1 CRS; intended 0.8 — stale, see HR-001).
- re-grade of stale run outputs under current grader: opus run-20260526-1753Z 1.0; gemma run-20260526-1922Z 1.0; gemma run-20260526-0748Z 0.0 (EPSG:32647 output, correctly caught). Confirms grader change is score-preserving.
- pytest: **pass** (35 / 35 in `benchmark/eval/`).

## Evaluator review 2026-05-28 (fourth pass)  (evaluator-commit <pending>)

### 1. Design history

Two new commits since the third-pass block, neither materially design-affecting on its own merits but one needs to be classified carefully:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-27 | bae995ff | docs-change (audit-only) | Third-pass evaluator's own artefact commit: `audit/AUTHORING_HISTORY.md`, `coverage.yaml`, `audit/status.json`. No prompt/grader/data change. | Commit msg: "Re-evaluate geo-l2-bangkok-landuse-intersect: calibrated — WGS84 contract now consistent after 1f4a85c6, reference self-grades 1.0". |
| 2026-05-28 | 622342be | docs-change (metadata-only, repo-wide) | Repo-wide refactor: introduce `task.json.version` integer field, drop unused `metadata.yaml > prompt_version`. For this task: `metadata.yaml` lost the `prompt_version: 2026-05-08-a` line; `task.json` was unchanged. Not a grader/prompt/data change — does not affect what the agent sees nor how it is scored. | Commit msg: "Add task content versioning; drop unused prompt_version". |

The third-pass change log captured through commit `1f4a85c6` remains accurate; the two appended commits above complete the picture.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-27T14:06:03+00:00** (commit `1f4a85c6`, class: mixed — reference output regenerated to WGS84 + grader one-sided reproject removed). Unchanged from the third pass; the two newer commits are docs/audit-only and metadata-only and do not move the cutoff.

#### 2c-CRS consistency check
All four sides agree on the output CRS contract (verified again this pass):
- Reference output `bma_landcover_intersect.geojson` CRS: WGS84 / CRS84.
- `task.json` `expected_outputs[0].crs`: `EPSG:4326`.
- `grade.py` Gate 1: requires `is_wgs84(sub.crs)`; geometric IoU is computed in WGS84 on both sides (no one-sided reproject); `area_m2` is an attribute column, summed symmetrically.
- `README.md` Output section: "GeoJSON, WGS84 (EPSG:4326)".

The only residual disagreement (`benchmark/authoring/inventory.md` row, line 581 — CRS out = EPSG:32647) is outside the task directory; carried as HR-002 again, unchanged severity.

#### Runs considered
Four new `current` runs (all post-cutoff `1f4a85c6`):

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T04:07:32Z | **1.0** | done (5/5) | current |
| run-20260528-0113Z | claude-code-opus-basic (opus / claude-opus-4-7) | 2026-05-28T02:42:44Z | **1.0** | done (5/5) | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T00:55:58Z | **1.0** | done (5/5) | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T22:21:14Z | **1.0** | done (5/5) | current |

Stale (pre-cutoff) runs from earlier 2026-05 dates listed in prior passes are unchanged; not used as evidence.

#### Verdict
**calibrated** — confirms third pass. Four current runs, two adapters (Opus + Gemma 4 26B), all 5/5 with healthy margins on every subcheck (counts 3450–3453 vs reference 3453; total-area rel diff ≤ 0.0001; unioned IoU 0.9772–1.0000 vs threshold 0.9; class Jaccard 1.0). Reference self-grades 1.0 under the current grader.

Strictly the new evidence is "too-easy-suspected" by the letter of Step 2d (every current run ≥ 0.95), but the second clause of that test — "AND the instruction appears to over-specify the answer" — is not satisfied here. The instruction is already maximally stripped (post `f40e39e`, `6500d9a`, `64740d0` all peeled deducible CRS / tolerance / unit hints; the live runs prove a small model can solve it without those nudges), and the prior pass already empirically resolved the "is requiring WGS84 fair to a weak model" question by showing the same Gemma model can both pass and fail on the CRS gate depending on its choice. The remaining unilateral redundancy I could find is the geometry-type and column-name double-statement in para 2, which I apply this pass (see Section 3); no further "gift" candidates remain. Verdict therefore stays `calibrated`, not `too-easy`.

The grader-side caveat from prior passes still holds: the two non-format broken fixtures (`broken_not_intersected`, `broken_area_in_km2`) remain stored in EPSG:32647 and continue to fail Gate-1 CRS at 0.0 instead of their intended 0.4 / 0.8 — verified again this pass by re-running the grader on each fixture. This is unchanged from the third pass and remains HR-001. It does **not** affect live agent grading.

#### Specific findings
- Task is solvable and calibrated. Four current runs (2 Opus + 2 Gemma), all 1.0; subchecks have healthy headroom.
- Instruction has a redundant geometry-type pin ("Every feature must be MultiPolygon") that `expected_outputs[0].geometry_type = "MultiPolygon"` already encodes; and a redundant column-list ("carry both the `class` and numeric `area_m2` columns described above") that duplicates the persona-voice column mention in para 1. Applied unilaterally per Step-4's "Tighten redundant statements within the instruction" rule (geometry-type case is the exact example; column-name case is the named "Identity key" / "Attribute preservation" pattern). Persona voice in para 1 is concrete ("original `class` string", "per-feature", "in square metres") and is the one kept; para 2 collapses to the canonical filename + format sentence. See Section 3.
- `broken_not_intersected` and `broken_area_in_km2` still in EPSG:32647 — HR-001 unchanged. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" --> Regenerate the two non-format broken outputs in EPSG:4326 by mirroring the reference fix in `reference/failures/_make_brokens.py` (compute `area_m2` in EPSG:32647, then `to_crs(EPSG:4326)` before `out.to_file(...)`), then re-measure that they land at 0.4 / 0.8 under the current grader and refresh `metadata.yaml`. Forbidden for this evaluator (`reference/failures/`). Severity `low`: affects only offline broken-solution calibration fixtures, not live agent grading. The human applying the fix must also bump `task.json.version` if the broken-fixture regeneration is paired with any prompt/grader/inputs change (it is not, on its own).
- `benchmark/authoring/inventory.md` row (line 581) still records CRS out = EPSG:32647 — HR-002 unchanged. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Update the inventory CRS-out for this row to EPSG:4326. Outside the task directory; out of scope for this evaluator to edit.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: stripped redundant geometry-type pin ("Every feature must be MultiPolygon") and redundant column-list ("carry both the `class` and numeric `area_m2` columns described above") from the second paragraph of `instruction`. Result: para 2 collapses to "Write the result to `bma_landcover_intersect.geojson` as a GeoJSON FeatureCollection." (canonical filename + format sentence). The MultiPolygon constraint remains enforced by `expected_outputs[0].geometry_type` and the `all_multipolygon` subcheck; column requirements remain in the persona-voice para 1. Re-grade on reference: **1.0** (5/5, unchanged). Reason: Step-4 "Tighten redundant statements within the instruction" rule, both the geometry-type bullet and the column-list pattern apply mechanically; prefer the persona-voice version (para 1) per the rule.
- `task.json`: added `version: 2` field (initial generation was implicit v1). Per Step-4 versioning rule, the first unilateral edit that changes the prompt contract in this evaluator pass bumps version exactly once. Bumped once, covers the instruction edit above.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — regenerate `broken_not_intersected` + `broken_area_in_km2` outputs in EPSG:4326 via `_make_brokens.py` (forbidden here), then refresh `metadata.yaml > broken_solutions > measured_score`.
- HR-002 — inventory-mismatch — update the `benchmark/authoring/inventory.md` CRS-out for this row to EPSG:4326.

#### Tests run
- grader on reference outputs (as a submission): **1.0** (5/5) — unchanged after the prompt edit (prompt edit does not touch reference output).
- grader on broken_wrong_format: 0.0 (Gate-1 JSON-sniff; intended).
- grader on broken_not_intersected: 0.0 (Gate-1 CRS; intended 0.4 — stale, see HR-001).
- grader on broken_area_in_km2: 0.0 (Gate-1 CRS; intended 0.8 — stale, see HR-001).
- live current runs (post-cutoff, pre-instruction-edit): run-20260527-2016Z opus 1.0; run-20260527-2321Z gemma 1.0; run-20260528-0113Z opus 1.0; run-20260528-0317Z gemma 1.0.
- pytest: **pass** (41 / 41 in `benchmark/eval/`).

## Evaluator review 2026-06-06 (fifth pass)  (evaluator-commit <pending>)

### 1. Design history

One new design-affecting commit and one prior-evaluator artefact commit since the fourth-pass block:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 4496d920 | prompt-change | Fourth-pass evaluator strip: removed "Every feature must be MultiPolygon and carry both the `class` and numeric `area_m2` columns described above" from para 2 of `instruction`; bumped `task.json.version` 1 → 2. | Commit msg: "strip redundant geometry-type + column-list from instruction (v1→v2)". Rationale invoked Step-4 'Tighten redundant statements', arguing `expected_outputs[0].geometry_type = MultiPolygon` already pins the constraint. |
| 2026-05-28 | 05aabd64 | grader-change | Repo-wide softening of the CRS gate: `is_wgs84()` Gate-1 hard-fail replaced with `grade_crs_soft()` (gate only on no-CRS-at-all submissions; downstream geometric subchecks reprojected to canonical; two new subchecks `crs_is_canonical` and `crs_in_meaningful_set` dock points for wrong-but-parseable CRS). Subcheck count 5 → 7. `MEANINGFUL_EPSGS = {4326}` for this task. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders". Wrong-CRS submissions previously scored 0 even when geometry was correct; this is a recoverable failure mode and the soft grader spreads its detection across subchecks. |

The fourth-pass change log captured through 2026-05-28 (commit `622342be`) remains accurate; the two appended commits above complete the picture.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57+00:00** (commit `05aabd64`, class: grader-change — CRS gate softened, two new CRS subchecks added). Advances the cutoff from the fourth pass's `1f4a85c6`. Commit `4496d920` is the immediately-preceding prompt-change, also post-cutoff for prior runs.

#### 2c-CRS consistency check
Output CRS contract is still WGS84 across all four sides, and the soft-CRS grader keeps that contract:
- Reference output `bma_landcover_intersect.geojson`: WGS84 / CRS84 (unchanged since `1f4a85c6`).
- `task.json` `expected_outputs[0].crs`: `EPSG:4326`.
- `grade.py` Gate 1: only fails on unrecoverable no-CRS-at-all submissions; otherwise reprojects to canonical (4326) for geometric subchecks, and docks two CRS subchecks if the original CRS isn't 4326. `CANONICAL_EPSG = 4326`, `MEANINGFUL_EPSGS = {4326}` — narrow accept-list by design.
- `README.md` Output section: "GeoJSON, WGS84 (EPSG:4326)" — unchanged, still consistent. Note: README's Failure mode #2 still says "Gate 1's CRS check rejects" which under the soft grader now means "loses both CRS subchecks (2/7 of the score) and gets reprojected for the rest" — still accurate as a discriminator description but the wording is mildly stale. Minor; left to a later docs pass.

Residual external disagreement (`benchmark/authoring/inventory.md` line 581 — CRS out = EPSG:32647) is unchanged; outside the task directory; carried as HR-002 again.

#### Runs considered
All four runs from the fourth-pass block (run-20260527-2016Z, run-20260527-2321Z, run-20260528-0113Z, run-20260528-0317Z) predate the new cutoff `05aabd64` AND predate the fourth-pass prompt edit `4496d920` — both stale.

Six current runs post-date both `4496d920` and `05aabd64`:

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T21:50:59Z | **0.857** (6/7) | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T23:16:44Z | **0.571** (4/7) | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:27:24Z | grader-error | done (grader threw) | current — see note |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T07:03:09Z | **0.857** (6/7) | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic (deepseek/deepseek-v4-pro) | 2026-05-31T17:07:45Z | **0.571** (4/7) | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed (google/gemma-4-26b-a4b-it) | 2026-06-06T12:35:05Z | **0.857** (6/7) | done | current |

Two further post-cutoff runs (run-20260606-0953Z, run-20260606-1334Z) are not evidence:
- run-20260606-0953Z: model-side UnicodeDecodeError 4.6 s into the session (failed before producing an output) — model-side failure, per Step-2d "model-side failures are not task problems".
- run-20260606-1334Z: cancelled, no output.

Note on run-20260528-2332Z: `grade.py:218` threw `shapely.errors.GEOSException: TopologyException: found non-noded intersection` inside `unary_union(sub.geometry.tolist())` because the agent's output contains a self-intersecting MultiPolygon. This is a **grader-robustness** issue (the IoU subcheck can crash on a pathological-but-valid-looking submission, sinking the whole grade run to a recorded `null`/`grader-error`) rather than a model-side failure. Flagged HR-003.

#### Verdict
**prompt-grader-inconsistent** (overturns fourth-pass `calibrated`).

The post-`4496d920` instruction does not tell the agent to coerce single Polygons to MultiPolygon, yet `grade.py:160-169` has an `all_multipolygon` subcheck that fails when the output mixes Polygon and MultiPolygon. The fourth pass justified the strip by appealing to `expected_outputs[0].geometry_type = "MultiPolygon"`, claiming Step-4's "Tighten redundant statements" rule mechanically applied. Empirically, the agent never sees `expected_outputs[]`: the harness sends only `task.instruction` to the model (`benchmark/eval/eval/core/runner.py:258` posts `{"instruction": task.instruction}`; `benchmark/harness/openrouter/run.py:78` puts that string verbatim as the user message). So `expected_outputs[].geometry_type` is grader-side bookkeeping, not part of the agent's prompt — the strip removed the only place the constraint was visible to the agent.

The post-strip evidence is unambiguous. Every current run with a graded output (Opus, Gemma×3, DeepSeek) fails the `all_multipolygon` subcheck with the identical detail string `geometry types: ['MultiPolygon', 'Polygon']` — i.e. the agents do intersect and simplify correctly, return a valid GeoDataFrame, and even arrive at the right feature count (3453 vs reference 3453), but leave single-component results as Polygon. That is exactly the "agent picks a defensible default the grader doesn't accept" shape of `prompt-grader-inconsistent`. Across five graded current runs the score range is {0.571, 0.571, 0.857, 0.857, 0.857} — strong models lose 1 point on the hidden MultiPolygon subcheck, weaker models lose 1 + 2 more on CRS (32647 instead of 4326). No current run scores 1.0; the ceiling is the hidden subcheck.

This also explains why the fourth pass thought stripping was safe: the four runs it cited (all dated 2026-05-27/28) predated the strip — they were scored against the *original* instruction, which still named MultiPolygon. Once the strip landed, the ceiling dropped.

The right fix is to re-add the MultiPolygon constraint to the instruction's output-contract paragraph. Author-context's instruction-stripping guide (`benchmark/authoring/instruction-stripping-guide.md`) explicitly puts "geometry types" in the **KEEP** bucket: "Output schema. Column names, file names, formats, CRS, geometry types. This is the contract the agent must fulfil." The fourth-pass strip violated that guide.

I treat this as the inverse of Step-4's "Strip a clear gift" — restoring an over-stripped constraint that the grader actually checks. The constraint is not a procedural hint (it does not tell the agent how to coerce, just what shape the output must take), and it does not give away any analysis strategy (`make_valid → intersect → simplify` ordering is still implicit). Applied unilaterally; version bumped 2 → 3.

The CRS softening from `05aabd64` is a separate, properly-scoped change: it correctly turns "wrong CRS" from a 0.0 hard-fail into a 2/7 deduction with the geometric subchecks still computed. Agents that submit EPSG:32647 (the input CRS) now score 4/7 instead of 0/7 — a clear improvement in calibration of a recoverable failure mode. Combined with the MultiPolygon re-add, the task should span roughly {0.43-1.0} across capability tiers post-edit (strong agents at 1.0, agents with one mistake at 0.86, agents with two at 0.57-0.71).

Sub-finding from prior passes carried forward, but now narrowed: the two non-format broken fixtures (`broken_not_intersected`, `broken_area_in_km2`) are stored in EPSG:32647 and under the soft-CRS grader they no longer collapse to Gate-1 0.0; they now score 0.286 and 0.571 respectively, exercising their intended subchecks plus the new CRS subchecks. That actually works fine — the fixtures discriminate as intended, only the scoreband shifted. Refreshed `metadata.yaml > broken_solutions > measured_score` and `expected_score_range` accordingly per Step-4 allowance. The previously-flagged HR-001 (regenerate broken outputs in WGS84) is **no longer needed**: the fixtures already work under the soft grader; regenerating them would over-fit to the old hard-fail policy. Dropped.

#### Specific findings
- Instruction over-stripped: `all_multipolygon` subcheck fails for every current agent because the prompt no longer mentions MultiPolygon. Restored the constraint in `task.json.instruction`. See Section 3.
- The two non-format broken fixtures now discriminate correctly under the soft-CRS grader (0.286 / 0.571). Refreshed `metadata.yaml > broken_solutions > measured_score` + `expected_score_range`. See Section 3. Previously-flagged HR-001 (regenerate fixtures) dropped.
- Grader can crash on pathological submission geometries: `grade.py:218` runs `unary_union(sub.geometry.tolist())` directly, which raised `TopologyException: non-noded intersection` on run-20260528-2332Z (Opus) and turned the whole grade into `score=null`. The fix is to wrap the union in a safety net (e.g. `make_valid` each submission geometry before `unary_union`, or catch the exception and fail the IoU subcheck cleanly). Not on the Step-4 unilateral edit list. <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="med" --> Wrap `unary_union(sub.geometry.tolist())` in `grade.py:218` with `make_valid` (apply to each geometry first) or a try/except that fails the IoU subcheck rather than the whole grade. The current behaviour records a `null` score for an output that should at minimum be partially graded.
- `benchmark/authoring/inventory.md` row (line 581) still records CRS out = EPSG:32647. <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" --> Update the inventory CRS-out for this row to EPSG:4326. Outside the task directory; out of scope for this evaluator to edit.
- README's Failure mode #2 ("Output in the wrong CRS … Gate 1's CRS check rejects") is now mildly stale under the soft-CRS grader — wrong CRS no longer rejects at Gate 1; it docks two CRS subchecks. Wording is mildly misleading but the discriminator still exists and the wrong-CRS broken fixtures still score below 0.7. Left for a later docs pass; not a flag because the README's overall narrative is still correct.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: re-added "with every feature stored as a MultiPolygon" to para 2 of `instruction`, restoring the constraint stripped by commit `4496d920`. Re-grade on reference: **1.0** (7/7, unchanged — reference already writes MultiPolygons). Reason: the instruction is the only place the agent sees the output contract; the `all_multipolygon` subcheck was unscorable by every current agent (5 graded current runs across 3 model families, none scored on it). Phrasing kept short and contract-shaped (not procedural).
- `task.json`: added `analyst_notes` field (was missing) describing what the task tests, the high-level approach, and the dominant pitfalls. Per Step-4 `analyst_notes` rules; not seen by the agent at runtime; surfaced in the eval UI alongside the prompt.
- `task.json`: bumped `version` 2 → 3 per Step-4 versioning rule (instruction edit changes what the agent sees).
- `metadata.yaml`: refreshed `broken_solutions > {not_intersected,area_in_km2}` `measured_score` (0.0 → 0.286 / 0.0 → 0.571) and `expected_score_range` to match the soft-CRS grader's actual scoring. Cleared the STALE notes. Reason: Step-4 explicitly permits refreshing `broken_solutions.measured_score` with one re-run; the previously-flagged "regenerate fixtures in EPSG:4326" path is no longer needed because the soft grader now grades these fixtures correctly.

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — grader-miscalibration-suspected — wrap `unary_union` in `grade.py:218` with `make_valid` or a try/except so a pathological submission geometry fails only the IoU subcheck, not the whole grade.
- HR-002 — inventory-mismatch — update `benchmark/authoring/inventory.md` CRS-out for this row to EPSG:4326.

#### Tests run
- grader on reference outputs: **1.0** (7/7).
- grader on broken_wrong_format: 0.0 (Gate-1 JSON-sniff; intended).
- grader on broken_not_intersected: **0.286** (2/7) — intended discriminator now works.
- grader on broken_area_in_km2: **0.571** (4/7) — intended discriminator now works.
- live current runs (pre-instruction-edit, post-soft-CRS-grader): see runs table — score range {0.571, 0.857} across 5 graded runs; one grader-error.
- pytest: **pass** (41 / 41 in `benchmark/eval/`).


---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Row-count-non-zero and row-count-within-±50% checks deleted; the
  existing `count_within_tolerance` subcheck (±5%) already covers the
  same property at a tighter bound, and 0-row submissions naturally
  fail every downstream subcheck.
- Unused `GATE2_ROW_TOL` constant removed.
- Subcheck count unchanged: 7.

### Verification
- Reference solution re-graded: 1.0 (7/7 subchecks).

## Evaluator review 2026-06-12 (sixth pass)  (evaluator-commit <pending>)

### 1. Design history

Three design-affecting commits and one prior-evaluator artefact commit since the
fifth-pass block (the "Manual cleanup 2026-06-06" section above documents the
gate-2 removal from the grader-maintainer's side):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 447eba74 | mixed (prompt-change + docs-change) | Fifth-pass evaluator's own commit: restored MultiPolygon constraint to the instruction (v2→v3), added `analyst_notes`, refreshed broken-fixture scores under the soft-CRS grader, wrote audit artefacts. | Commit msg: "Re-evaluate geo-l2-bangkok-landuse-intersect: prompt-grader-inconsistent — restore MultiPolygon constraint (v2→v3); refresh broken-fixture scores under soft-CRS grader". |
| 2026-06-06 | 39c07693 | grader-change | Library `_coerce_to_geometry` hardened (defensive `make_valid` per geometry, GEOSException caught at the union step, empty GeometryCollection on failure); this task's `grade.py` refactored to pass GeoDataFrames straight to `iou_with_tolerance` instead of pre-unioning inline; `task.json.version` 3 → 4. | Commit msg: "Harden _coerce_to_geometry against GEOSException; route bangkok through it … a pathological submission fails only its IoU subcheck rather than nulling the whole grade run". Resolves fifth-pass HR-001. |
| 2026-06-06 | 363aed21 | grader-change | Repo-wide: dropped the `structural_correctness` Gate 2 (0-row and ±50 % row-count early-returns deleted, `GATE2_ROW_TOL` removed); single hard gate `format_schema_valid` remains; subcheck count unchanged at 7. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" — Gate 2 was inconsistent across the 36 graders and duplicated subcheck logic at looser tolerances. |
| 2026-06-07 | c749e57b | grader-change | Repo-wide: `Subcheck` gained a `weight` kwarg and `ScoreReport.score` became weight-normalised; this task's four data-content subchecks (`count_within_tolerance`, `class_set_jaccard`, `total_area_within_tolerance`, `unioned_geometry_iou`) tagged `weight=3.0`; `all_multipolygon` + the two CRS subchecks stay at 1.0 (total weight 15). | Commit msg: "Weight data-content subchecks 3x across all categories" — data-content checks should dominate schema/structural checks in the score. |

Neither `363aed21` nor `c749e57b` bumped `task.json.version` (still 4) despite
both changing grader scoring semantics — see HR-002.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:32:38+00:00** (commit `c749e57b`, class: grader-change — 3x weighting of data-content subchecks). Advances the cutoff from the fifth pass's `05aabd64`/`4496d920`.

#### 2c-CRS consistency check
- Reference output `bma_landcover_intersect.geojson`: WGS84/CRS84 (unchanged since `1f4a85c6`).
- `task.json` `expected_outputs[0].crs`: `EPSG:4326`.
- `grade.py`: soft-CRS gate (only no-CRS submissions hard-fail); submission reprojected to canonical 4326 for geometric subchecks; `crs_is_canonical` + `crs_in_meaningful_set` dock wrong-but-parseable CRS. No one-sided paper-over; compliant.
- `README.md`: "GeoJSON, WGS84 (EPSG:4326)" — consistent. Failure-mode #2 wording ("Gate 1's CRS check rejects") was stale under the soft grader; fixed this pass (docs-change).

Residual external disagreement: `benchmark/authoring/inventory.md` (task row, "CRS out: EPSG:32647" and the output-artifact line "crs: EPSG:32647") still contradicts the live EPSG:4326 contract — carried again as HR-001 (inventory-mismatch), unresolved since the third pass.

#### Runs considered
Validity = started_at ≥ cutoff (2026-06-07T18:32:38Z) AND run task_version ≥ current version 4.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T12:22:49Z | **0.867** (13/15) | done | current |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:57:59Z | **0.867** (13/15) | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T15:48:19Z | 1.0 | done | stale by timestamp (pre-`c749e57b`), but its recorded score.json already carries the 3x weights, and re-grading its output under the current grader reproduces 1.0 — used as supporting evidence only |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T19:26:40Z | 0.714 (5/7 unweighted) | done | stale (pre-gate-removal, pre-weighting); re-graded under current grader → 0.867 — supporting evidence only |

Earlier runs (2026-05-12 → 2026-06-06, listed in prior passes) remain stale.

#### Verdict
**calibrated**

Strictly, the two timestamp-current runs come from one model family (DeepSeek V4 Flash), which by the letter of Step 2d alone would be `insufficient-evidence`. Following the third pass's precedent, I supplement with reproducible re-grades under the current grader: the reference self-grades **1.0** (15/15 weighted), the gemma-detailed output from run-20260607-112430Z re-grades **1.0**, and the gemma output from run-20260606-1733Z re-grades **0.867**. Across two model families under the current grader the task spans {0.867, 0.867, 0.867, 1.0}, and the broken fixtures span {0.0, 0.267, 0.667}. Every 0.867 has the identical cause: output left in the inputs' EPSG:32647 instead of the RFC-7946 WGS84 convention, costing exactly the two unit-weight CRS subchecks (2/15). That is the task's deliberate hidden gotcha being priced as a minor deduction rather than a hard fail — the soft-CRS + weighting design working as intended. All graded current/supporting runs pass `all_multipolygon` (the fifth-pass restoration of the MultiPolygon constraint took effect: every post-v3 run produces uniform MultiPolygons, where every pre-restoration run failed that subcheck). No run scored a spurious 0; no correct-looking output was rejected.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `bma_landcover_intersect.geojson` | instruction, para 2 | stated |
| GeoJSON FeatureCollection format | instruction, para 2 | stated |
| required columns `class`, `area_m2` | instruction, para 1 ("original `class` string and a per-feature `area_m2`") | stated |
| `area_m2` in square metres | instruction, para 1 | stated |
| every feature MultiPolygon (`all_multipolygon`) | instruction, para 2 | stated |
| output CRS EPSG:4326 (2 CRS subchecks) | not stated; RFC 7946 GeoJSON convention | inferable (deliberate gotcha; soft-graded at 2/15) |
| intersection against study area (count/area/IoU subchecks) | instruction, para 1 ("the land-cover within the study area") | stated |
| simplification (IoU ≥ 0.9 head-room) | instruction, para 1 ("simplified enough that the file is small") | stated (tolerance choice left to the agent; grader headroom absorbs any sane pick) |
| ±5 % count/area tolerances, Jaccard ≥ 0.9, IoU ≥ 0.9 | grader-internal | inferable (standard drift margins) |
| invalid input geometries must be repaired | not stated; discoverable from the input data | inferable (the data itself is the signal; count tolerance is the detector) |

Factual claims checked: the instruction's backticked input names `landcover` and `study_area` are the `task.json.inputs[].name` values; the files land in the sandbox under their real filenames (`bangkok_landcover.parquet`, `bma_study_area.geojson` — `runner.py` uploads by filename). The mapping is unambiguous (only two inputs, names are substrings of the filenames) and every recent run resolved it without friction (all produced the exact 3453-feature result), so I classify it as inferable rather than a house-style violation worth a version-invalidating rewrite. Columns, units, output filename, and format all verified against `inputs/` and the reference output schema — no inaccurate claims.

#### Reference faithfulness
`reference/solution/generate.py` (unchanged since `1f4a85c6`) is faithful: it repairs invalid geometries with `make_valid`, intersects against the unioned study-area geometry, drops empties, coerces to MultiPolygon, simplifies at 5 m in the metric work CRS, computes `area_m2` in EPSG:32647 metres², and reprojects to WGS84 for the GeoJSON write. The two extras — carrying the `id` column through and sorting by it — are determinism/practicality choices that the grader does not score and that contradict nothing in the prompt; not deviations worth a flag. CRS choices are optimal (metric UTM 47N for area/simplify, WGS84 for the GeoJSON file).

#### Specific findings
- Fifth-pass HR-001 (grader `unary_union` crash nulling the whole grade) is **resolved** by commit `39c07693`: the library's `_coerce_to_geometry` now defensively `make_valid`s and catches `GEOSException`, and this task's `grade.py` routes the IoU subcheck through `iou_with_tolerance` so the defense applies. No flag carried.
- Broken-fixture `measured_score` values in `metadata.yaml` were stale under the weighted grader (recorded 0.286 / 0.571; actual 0.267 / 0.667, and 0.667 fell outside the recorded `expected_score_range` [0.50, 0.65]). Refreshed both `measured_score` and `expected_score_range`, and updated the score arithmetic in the descriptions (unilateral per Step 4).
- `metadata.yaml > tolerances > rationale` still described the removed Gate 2 ±50 % row gate; reworded to note the gate's removal (prose-only, no tolerance value changed, no bump).
- `README.md` had four stale spots: `data/` input paths (folder renamed to `inputs/` in `29a9ae3`), failure-mode #2 still claiming a Gate-1 CRS rejection (soft-graded since `05aabd64`), and broken-solution scores 0.400 / 0.800 (now 0.267 / 0.667 weighted). All fixed (docs-change).
- `benchmark/authoring/inventory.md` task row still records "CRS out: EPSG:32647" (table row and output-artifact line) versus the live EPSG:4326 contract. <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Update the inventory row's CRS-out (and the output-artifact line's `crs:`) to EPSG:4326. Outside the task directory; out of scope for this evaluator to edit. Carried unresolved since the third pass.
- Commits `363aed21` (gate-2 removal) and `c749e57b` (3x weighting) both changed this task's scoring semantics without bumping `task.json.version` (still 4), so the eval UI's version-based de-emphasis will not mark pre-weighting runs as outdated even though their scores are not comparable (e.g. run-20260606-1733Z recorded 0.714 for an output that scores 0.867 today). This is repo-wide (36 graders), not specific to this task, and retro-bumping here alone would mis-mark runs that were in fact scored under the weighted grader. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="low" --> Decide whether repo-wide grader-semantics changes should bump every affected task's `version` (and whether to do so retroactively for `363aed21`/`c749e57b`); a per-task evaluator should not make that call unilaterally for one task out of 36.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > {not_intersected,area_in_km2}` `measured_score` (0.286 → 0.267, 0.571 → 0.667) and `expected_score_range` ([0.25,0.35] → [0.20,0.35], [0.50,0.65] → [0.60,0.75]) under the weighted grader; updated description arithmetic; reworded the stale Gate-2 sentence in the tolerances rationale (no tolerance value changed). Re-grade on reference: 1.0. Reason: Step 4 permits refreshing `measured_score` with one re-run; rationale fix is mechanical staleness (Gate 2 no longer exists).
- `README.md`: `data/` → `inputs/` paths; failure-mode #2 rewritten for the soft-CRS grader (2/15 deduction, not a Gate-1 rejection); broken-solution scores 0.400/0.800 → 0.267/0.667; weak-agent paragraph updated with weighted scores and the empirically dominant wrong-CRS failure (0.867). Re-grade on reference: 1.0. Reason: docs-change, README must match the live contract.
- No `task.json` or `grade.py` edits; no version bump required (measured-score refreshes and docs are exempt). Version stays 4.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — update `benchmark/authoring/inventory.md` CRS-out (row + output-artifact line) to EPSG:4326.
- HR-002 — design-rationale — decide repo-wide policy on version bumps for shared-grader-semantics commits (`363aed21`, `c749e57b`).

#### Tests run
- grader on reference outputs: **1.0** (15/15 weighted).
- grader on broken_wrong_format: 0.0 (gate; intended).
- grader on broken_not_intersected: **0.267** (4/15; intended discriminator).
- grader on broken_area_in_km2: **0.667** (10/15; intended discriminator).
- re-grades under current grader: run-20260607-112430Z (gemma) → 1.0; run-20260606-1733Z (gemma, EPSG:32647 output) → 0.867.
- pytest: **pass** (41 / 41 in `benchmark/eval/`).

## Evaluator review 2026-06-14 (seventh pass — weight recalibration)  (evaluator-commit <pending>)

**One-line:** RECALIBRATED — replaced the blunt repo-wide `weight=3.0` on all four
"data-content" subchecks (commit `c749e57b`) with severity-reasoned weights that put
the central geometric-correctness checks highest and demote the structural class-set
check. Grading-only; no `task.json` / inputs / reference / version change.

### Why
This is a geometric-ops (landuse intersection/overlay) task. The central skill is
performing the intersection/overlay correctly in a projected CRS and reporting area
in metric m². Commit `c749e57b` had tagged all four of `count_within_tolerance`,
`class_set_jaccard`, `total_area_within_tolerance`, `unioned_geometry_iou` at 3.0 —
but `class_set_jaccard` is an attribute-preservation (structural) check, not a
geometric-correctness check. It passes for *both* the skipped-intersection and the
wrong-unit failures, so it never discriminates the central skill yet carried the
same weight as the checks that do. That is the one-size-fits-all miscalibration.

### Weight changes
| Subcheck | Old | New | Rationale |
|---|---|---|---|
| `unioned_geometry_iou` | 3.0 | **4.0** | Most direct detector of correct intersection/overlay — the central skill. |
| `total_area_within_tolerance` | 3.0 | **4.0** | Central: metric-CRS area + the explicit km²/m² unit gotcha + magnitude. |
| `count_within_tolerance` | 3.0 | 3.0 | Strong proxy for the central operation (skipped intersection → ~21 k vs ~3.5 k features); slightly less direct than IoU/area, kept high. |
| `class_set_jaccard` | 3.0 | **1.0** | Attribute-preservation / structural, not geometric-correctness; passes for both non-format brokens, barely discriminates. Demoted to structural weight. |
| `all_multipolygon` | 1.0 | 1.0 | Structural geometry-type coercion. |
| `crs_is_canonical` | 1.0 | 1.0 | Cosmetic RFC-7946 WGS84 convention (recoverable). |
| `crs_in_meaningful_set` | 1.0 | 1.0 | Same CRS axis, second point. |

Total weight unchanged at 15 (4+4+3+1+1+1+1), so the CRS-only deduction stays 2/15
(0.867) and a MultiPolygon-only slip stays 1/15 (0.933) — cosmetic slips remain near
the top, as intended.

### Broken-score before → after
| Fixture | Before | After | Severity note |
|---|---|---|---|
| `broken_wrong_format` | 0.000 | 0.000 | Gate fail (GeoParquet bytes); unaffected by weights. |
| `broken_not_intersected` | 0.267 | **0.133** | Most severe: skips the central intersection → fails count+area+IoU+both CRS. Now drops harder, correctly. |
| `broken_area_in_km2` | 0.667 | **0.600** | Moderate: geometry correct, only area-unit + CRS wrong. Stays well above the skipped-intersection failure. |
| reference | 1.000 | **1.000** | Unchanged (all subchecks pass). |

**Ordering check:** monotone and defensible — 0.000 (gate/format) < 0.133
(skipped intersection, fails the whole central geometric group) < 0.600 (correct
geometry, wrong units only) < 1.000 (reference). No disjoint-failure inversion: the
gap between the most-severe geometric failure and the cosmetic-only failures widened
(0.133 vs 0.600) without overshooting, and CRS-only / MultiPolygon-only slips sit at
0.867 / 0.933.

### Prior-run re-grade summary
Re-graded the timestamp-current and supporting runs (all output uniform MultiPolygons,
post-v3 restoration). Scores essentially unchanged because the reweighting only bites
when a *geometric* subcheck fails — and all these runs pass every geometric subcheck:
| Run | Adapter | old → new | Note |
|---|---|---|---|
| run-20260607-112430Z | gemma4-26b-detailed | 1.0 → 1.0 | full pass |
| run-20260608-074701Z | deepseek-v4-flash-detailed | 0.867 → 0.867 | wrong-CRS-only (2/15), unaffected |
| run-20260609-084636Z | deepseek-v4-flash-basic | 0.867 → 0.867 | wrong-CRS-only (2/15), unaffected |
| run-20260606-1733Z | gemma4-26b-detailed | 0.867* → 0.867 | wrong-CRS-only; *re-graded value under weighted grader |

No notable shifts among prior runs — the recalibration sharpens discrimination of the
*central-skill failures* (visible in the brokens) without disturbing runs whose only
defect is the cosmetic CRS convention.

### Notes (not changed)
- Thresholds and check logic untouched (count ±5 %, area ±5 %, Jaccard ≥ 0.9,
  IoU ≥ 0.9). No threshold appears miscalibrated for the central skill given the
  headroom seen in live runs.
- Carried HRs (HR-001 inventory-mismatch, HR-002 design-rationale on shared-grader
  version bumps) are not weighting HRs and are retained.

### Changes applied this run
- `grade.py`: weight= edits only (table above); expanded the docstring with the
  severity rationale. No logic/threshold/gate change.
- `metadata.yaml`: `broken_solutions > {not_intersected,area_in_km2}` `measured_score`
  (0.267 → 0.133, 0.667 → 0.600) + `expected_score_range` ([0.20,0.35] → [0.08,0.20],
  [0.60,0.75] → [0.50,0.70]) + weight-arithmetic prose.
- `README.md`: refreshed broken scores (0.267/0.667 → 0.133/0.600) and the weak-agent
  paragraph fractions.
- No `task.json` / version bump (grading-only).

### Tests run
- grader on reference: **1.0** (15/15 weighted).
- grader on broken_wrong_format: 0.0 (gate).
- grader on broken_not_intersected: **0.133** (2/15).
- grader on broken_area_in_km2: **0.600** (9/15).
- prior-run re-grades: see table above.
- pytest: not run (orchestrator runs the suite).
