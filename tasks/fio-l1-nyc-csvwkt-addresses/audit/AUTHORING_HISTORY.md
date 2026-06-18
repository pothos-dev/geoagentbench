# Implementation notes — fio-l1-nyc-csvwkt-addresses

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 format-I/O task: an all-quoted CSV-with-WKT slice of Overture NYC
addresses → GeoParquet with `recorded_at` typed as `timestamp[us]`,
`unit_count` typed as `int32`, geometry parsed from `geometry_wkt` as
Point in EPSG:4326. Reference, grader, and three broken solutions
built and verified inside the project Docker container.

## Verification results
- Reference grader score: 1.00 (8 / 8 subchecks pass)
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    the CSV body (cannot parse as parquet), no subcheck runs.
  - no_type_coercion: 0.750 (expected range [0.70, 0.80]) — 6 / 8
    pass; both type subchecks (`recorded_at_is_timestamp_us` and
    `unit_count_is_int32`) fail because the columns stayed string.
  - int64_unit_count: 0.875 (expected range [0.85, 0.92]) — 7 / 8
    pass; only `unit_count_is_int32` fails (column is int64 instead
    of int32).
- Second-run output match: bit-identical (verified with `diff -q` on
  `reference/outputs/addresses.geoparquet` before / after a second
  `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Wrong output format (CSV / GeoJSON / not-a-geoparquet):
  broken_wrong_format
- Skipped attribute type coercion entirely: broken_no_type_coercion
- int64 instead of int32 for unit_count: broken_int64_unit_count
- timestamp[ns] instead of timestamp[us]: principled —
  `recorded_at_is_timestamp_us`
- Numeric-looking string columns aggressively re-typed to int:
  principled — `address_columns_are_strings`
- Residual `geometry_wkt` column kept alongside parsed geometry:
  principled — `no_residual_geometry_wkt_column`
- Dropped or duplicated rows during conversion: principled — Gate 2
  row-count check
- Reprojected to non-WGS84: principled — Gate 1 CRS check +
  `geometry_preserved_per_id`

## Open issues
(none)

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — the grader uses `Gate`, `Subcheck`, `ScoreReport`, and the
existing `feature_set_equality_by_id` primitive. Arrow-schema-type
checks are JSON-shape-style comparisons against pyarrow's type API
and are kept inline in `grade.py`.)

## Runtime
~10 minutes (one Overture slice fetch ~25 s for 8 441 rows over
lower-Manhattan, the rest local Docker runs).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent

Per the `inventory.md` row and the original author block above, this is the
L1 format-I/O slot for the `addresses.address` Overture theme. The agent gets
a 1 056-row CSV-with-WKT slice of NYC addresses with every column quoted
(forcing `pd.read_csv` to return `object` dtype for the integer and timestamp
columns), and must produce a GeoParquet with the geometry parsed from WKT,
`recorded_at` typed as `timestamp[us]`, `unit_count` typed as `int32`, and
the remaining text columns kept as Arrow string. The grader has two gates
(`format_schema_valid`, `structural_correctness`) plus eight subchecks
covering Arrow schema typing, id Jaccard, per-id value preservation, per-id
geometry preservation, and absence of a residual `geometry_wkt` column.

#### Change log

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 6620867 | initial-authoring | Initial task: CSV-with-WKT → GeoParquet with type coercion; 8-subcheck grader; 3 broken solutions (wrong_format, no_type_coercion, int64_unit_count). | Initial authoring per inventory row. |
| 2026-05-13 | 284b843 | mixed (prompt-change: adds `tags`) | Added `tags` dictionary to `task.json` (region, formats, crs, etc.) for filtering. No grader change. | Commit msg: "Adds a `tags` dictionary to each task.json with 9 keys for filtering." |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit output-schema paragraph to the instruction enumerating every Arrow type per column and the row-count/geometry_wkt-drop rules. | Commit msg: "Add explicit column names, geometry types, layer names, value vocabularies, and join-key declarations to task prompts where the grader was already enforcing them implicitly. No grader changes; no subchecks loosened." |
| 2026-05-13 | 9e79176 | prompt-change | Reflowed the structured "Output schema:" bullets into a prose paragraph (no semantic change — same column type list, same `geometry_wkt`-drop sentence, same row-count constraint). | Commit msg: "fold the structured 'Output schema:' bullet lists into fluent concluding paragraphs." |
| 2026-05-14 | 68384e4 | prompt-change | Round 1 strip: removed "dumped every column as a quoted string" lead, replaced explicit column enumeration with "the rest of the Overture address columns" / "all other columns as string", replaced `geometry_wkt` reference with "the WKT column" / "the original WKT text column". Kept the geometry-wkt-drop sentence and the row-count sentence. | Commit msg: "Remove input CRS mentions, geometry type descriptions, explicit column enumerations, format descriptions, and data value examples that models can discover by reading file metadata. Keep all output requirements, column_map references, and task narrative framing." |
| 2026-05-15 | d65f3d9 | prompt-change | Round 2 strip: collapsed the two prose paragraphs into a single sentence — "Convert it to addresses.geoparquet: Point geometry in EPSG:4326, recorded_at as timestamp[us], unit_count as int32, all other columns as string. Drop the source text geometry column. The row count must match the input exactly with no filtering or deduping." | Commit msg: "Strip deducible information from FIO task instructions (round 2)" — no body. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why the second strip cut the prose down further is not stated in the commit message; the diff does still preserve the geometry-drop and row-count sentences. |
| 2026-05-17 | b4583b4 | prompt-change | Removed the "Drop the source text geometry column." and "The row count must match the input exactly with no filtering or deduping." sentences entirely. Instruction now ends at "all other columns as string." | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" — no body. <!-- HUMAN-REVIEW id="HR-002" category="design-rationale" severity="med" --> Why a *FIO* task was included in a sweep titled "5 CRS task prompts" is not stated; and dropping the explicit "drop geometry_wkt" requirement removed information that the grader still checks via the `no_residual_geometry_wkt_column` subcheck. See current-state review §2 below. |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `sub.crs is not None and sub.crs.to_epsg() == 4326` with `is_wgs84(sub.crs)` from the shared `geo_grading` package. Behaviour preserved (None → True, EPSG 4326 → True). | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package. is_wgs84(crs): for pyproj CRS objects (None → True per RFC 7946) ..." |
| 2026-05-26 | 29a9ae3 | mixed (data-change: input URL; grader-change: reference path) | Reorganized layout: `data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`. Updated `task.json` input URL and grader `REFERENCE_OUT` constant accordingly. No file contents changed; no answer key changed. | Commit msg: "Migrate every benchmark task to a clearer layout that separates audience concerns (machine contract, audit history, inputs, reference + failures, eval-UI assets)." |

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (commit 29a9ae3, class: mixed — input URL rename + grader reference-path rename).
- the most recent commit that could change the *answer* or the *instruction* (as opposed to mechanical file moves) is b4583b4 at 2026-05-17T12:48:37+00:00 (prompt-change).

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:37:55Z | 0.875 | done | current (post-b4583b4 prompt; the 29a9ae3 reorg only renames paths, no answer change — so this run is evidence about the current prompt) |

Stale runs (pre-b4583b4, when the instruction still said "Drop the source text geometry column"): 24 runs across `claude-code-haiku-basic`, `claude-code-sonnet-basic`, `claude-code-opus-basic`, `openrouter-deepseek-v4-flash-basic`, `openrouter-gemma4-26b-basic` (failed / cancelled), `openrouter-hy3-preview-basic` (0.0). Capable agents all scored 1.0 when the prompt explicitly required dropping `geometry_wkt`; gemma was cancelled / failed at that stage; hy3-preview scored 0.0 (likely wrong format).

#### Verdict

**prompt-grader-inconsistent**

The single `current` run (gemma 4 26B, score 0.875) failed exactly one subcheck: `no_residual_geometry_wkt_column`. The other 7 subchecks all passed (`recorded_at_is_timestamp_us`, `unit_count_is_int32`, all 7 address columns are Arrow string, id Jaccard 1.0, all 1056 unit_count and recorded_at values preserved, all 1056 geometries within 1e-9°). The grader at `grade.py:286-298` requires `geometry_wkt` to be absent from the output, but commit b4583b4 ("Remove CRS/operation nudges from 5 CRS task prompts") removed the explicit "Drop the source text geometry column." sentence from `task.json.instruction`. The current instruction reads only "...all other columns as string." which the gemma agent reasonably interpreted as "keep all input columns, just retype them" — leaving `geometry_wkt` alongside the parsed `geometry`. The README (untouched by b4583b4) and the grader still document the drop; the agent only sees `task.json.instruction`.

Capable agents (Opus, Sonnet, DeepSeek V4) historically inferred the drop even when the prompt was earlier reformulated, but the only current-prompt evidence we have is one less-capable agent that did not. Whether dropping `geometry_wkt` is "inferable convention" or "necessary information the agent cannot infer" is a judgment call: convention says yes (storing both parsed geometry and source WKT is wasteful and confuses downstream consumers — point 6 in `README.md > Failure modes` says exactly this), but the prompt's "all other columns as string" reads as keep-all and gives the wrong steer.

There is also a secondary concern: b4583b4 also removed the row-count sentence ("The row count must match the input exactly with no filtering or deduping."). The grader's Gate 2 enforces strict row-count equality. For a single-file CSV → GeoParquet rewrite this is also reasonable convention (a format conversion implies row-preservation), but it is another instance of the same pattern — a grader-enforced rule whose explicit statement was removed. The gemma run's row count was preserved (1056) so this is latent, not active, breakage.

#### Specific findings

- The current instruction omits the geometry-wkt drop requirement that the grader still checks. The fix is either to (a) re-add a short sentence to `task.json.instruction` (one-line: "Drop the source `geometry_wkt` column."), or (b) loosen `no_residual_geometry_wkt_column` to informational-only or remove it. Both are defensible; (a) preserves the existing 8-subcheck calibration (0.0 / 0.75 / 0.875 / 1.0 cohort) and is the smaller change. <!-- HUMAN-REVIEW id="HR-003" category="prompt-vs-grader-judgment" severity="med" --> Pick (a) re-add the drop sentence to the instruction, OR (b) loosen the grader subcheck. Either restores prompt-grader consistency. Not applying unilaterally because Step 4 only authorizes *stripping* gifts, not re-adding requirements, and the call between "agent should infer this from convention" and "agent needs to be told" is judgment.
- The b4583b4 commit message ("Remove CRS/operation nudges from 5 CRS task prompts") does not match what was actually changed here — this is a FIO task, not a CRS task, and the removed sentences are output-schema requirements, not CRS hints. Flagged in HR-002 above as a rationale gap; the human owner may want to audit the rest of that commit's 5-task sweep for the same overcorrection.
- Coverage tagging: the region slug `new-york` (per `coverage-vocabulary.yaml`) is used in `coverage.yaml`. The task's structured `tags.region` entry says `nyc`; that legacy filter tag is independent of the coverage matrix and is left as-is.

### 3. Changes applied this run

#### Unilateral edits

(none — the prompt-grader inconsistency around `geometry_wkt` is borderline per Step 4 rules and is flagged for human review instead.)

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — design-rationale — round-2 instruction strip (d65f3d9) has no commit-message rationale; diff is mechanical and the geometry-drop sentence was still preserved at that point, so low severity.
- HR-002 — design-rationale — b4583b4 was titled "Remove CRS/operation nudges from 5 CRS task prompts" but also dropped a non-CRS output-requirement sentence from this FIO task. Medium severity because it directly produces HR-003.
- HR-003 — prompt-vs-grader-judgment — current instruction does not tell the agent to drop `geometry_wkt`, but the grader checks for its absence. Pick (a) re-add the sentence to the instruction or (b) loosen the subcheck. Medium severity because it costs ~0.125 score on capable-but-literal agents.

#### Tests run

- grader on reference: 1.000 (8/8 subchecks; both gates pass).
- pytest (benchmark/eval): 35 passed, 0 failed.

---

## Evaluator review 2026-05-26 (re-eval)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/fio-l1-nyc-csvwkt-addresses/` since the
prior evaluator-review block above (last design-affecting commit remains
b4583b4, 2026-05-17; last task-dir commit before this re-eval is the prior
evaluator's own artefact commit c2df4cd, 2026-05-26T13:43Z). The design history
and change log in the block above are confirmed accurate against
`git log --follow` and `git show b4583b4`. This re-eval re-runs Step 2 against
**new run evidence** that arrived after the prior block was written.

### 2. Current-state review (re-run)

#### Cutoff

- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (commit 29a9ae3, class:
  mixed — input-URL + reference-path rename only, no answer-key/instruction
  change). The last commit that changed the *instruction* is b4583b4
  (2026-05-17T12:48:37Z); the last that changed the *grader* is f0c244a
  (2026-05-18, behaviour-preserving `is_wgs84` refactor). All three current
  runs below started 2026-05-26 evening, well after every candidate cutoff.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:58:53Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:41:29Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:37:55Z | 0.875 | done | current |

Two distinct agent families now have current runs (claude-code Opus + OpenRouter
Gemma). Stale runs (24, all pre-b4583b4) are catalogued in the prior block.

Per-run output inspection (from each run's `score.json`):
- **opus 1753Z (1.0):** dropped `geometry_wkt`; all 8 subchecks pass; 1056 rows;
  `recorded_at` = `timestamp[us]` (tz-naive), `unit_count` = `int32`, 7/7 text
  cols string, id Jaccard 1.0, 1056/1056 values + geometries preserved.
- **gemma 1922Z (1.0):** dropped `geometry_wkt`; all 8 subchecks pass; identical
  schema profile to opus (tz-naive `timestamp[us]`, `int32`).
- **gemma 0748Z (0.875):** kept `geometry_wkt` (Arrow `timestamp[us, tz=UTC]`,
  `int32`); 7/8 pass; only `no_residual_geometry_wkt_column` fails. Values,
  geometries, id-set, types all correct.

#### Verdict

**calibrated** (supersedes the prior block's `prompt-grader-inconsistent`)

The prior block reached `prompt-grader-inconsistent` on a *single* current run
(gemma 0748Z, 0.875) whose only failed subcheck was
`no_residual_geometry_wkt_column`, and reasoned that since b4583b4 removed the
explicit "Drop the source text geometry column." sentence, the grader was
checking something the instruction no longer told the agent to do. Two fresh
current runs now overturn the *evidentiary* basis for that verdict:

- The **same gemma 4 26B model** that retained `geometry_wkt` in run 0748Z
  *dropped* it in run 1922Z and scored 1.0. Inspecting the two agent scripts
  (`outputs/solve.py`) confirms this is pure sampling variance on a borderline
  decision the model debated with itself: in 0748Z it wrote "I will keep
  geometry_wkt as string just to be safe"; in 1922Z it wrote "Drop the original
  WKT column if it exists to keep it clean." Opus dropped it without hesitation.
- Dropping the source WKT text column when emitting an *Overture-schema*
  GeoParquet is inferable convention, not hidden knowledge: Overture
  `addresses.address` rows carry a binary `geometry`, never a `geometry_wkt`
  text column, and the inventory's output-artifact spec says the schema "matches
  Overture's address column set" (no `geometry_wkt`). The README's failure-mode
  #6 documents the residual-WKT mistake as a genuine quality defect (doubled
  storage, downstream confusion). The `no_residual_geometry_wkt_column` subcheck
  is therefore a legitimate principled detector, and the 0.125 it cost one gemma
  draw is the grader doing its job, not over-specification.

Scores across the three current runs (1.0 / 1.0 / 0.875) span a sensible range
driven by an agent-side judgment call that competent agents (and even the
weaker model, on a second draw) make correctly. No subcheck is mis-firing; the
reference re-grades 1.0; broken solutions still land 0.0 / 0.75 / 0.875 per
`metadata.yaml`. This is a well-calibrated L1 format-I/O task.

The prior block's borderline judgment (HR-003: "is the WKT-drop inferable or
must it be stated?") is preserved below at **lower** severity — the new evidence
shows the requirement *is* inferable in practice, so it no longer warrants the
prior `med`. The human owner may still elect to re-add a one-line drop sentence
to remove all ambiguity, but it is no longer a calibration defect.

#### Specific findings

- The `no_residual_geometry_wkt_column` subcheck is correctly calibrated. No
  change applied.
- The prior block's HR-002 (commit b4583b4 titled "Remove CRS/operation nudges
  from 5 CRS task prompts" but actually editing a FIO task and removing two
  output-schema sentences) is a real design-rationale gap that the new run
  evidence does not resolve. Carried forward below as HR-001 (re-eval scope).
- Coverage tagging unchanged from prior block (all slugs validate against
  `coverage-vocabulary.yaml`); only `evaluator_run_at` bumped.

### 3. Changes applied this run

#### Unilateral edits

(none — verdict is `calibrated`; the grader needs no loosening or tightening.
Re-adding the WKT-drop sentence to the instruction is a prompt change that Step 4
does not authorize unilaterally and that the new evidence shows is unnecessary
for calibration; left for the human owner as a low-severity option.)

#### Proposed but not applied (see HUMAN-REVIEW items)

- HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation nudges from
  5 CRS task prompts") mis-describes its effect on this FIO task: it removed the
  `geometry_wkt`-drop and row-count output-schema sentences, not a CRS nudge.
  The human owner may want to audit the rest of that 5-task sweep for the same
  over-correction. (Carries forward the prior block's HR-002.)
- HR-002 — prompt-vs-grader-judgment — the instruction no longer explicitly
  tells the agent to drop `geometry_wkt`, while the grader's
  `no_residual_geometry_wkt_column` subcheck checks for its absence. New evidence
  (gemma dropping it on a fresh draw, opus dropping it, inventory implying the
  Overture schema) shows this is inferable convention, so severity is **low**.
  Optional fix: re-add "Drop the source `geometry_wkt` column." to the
  instruction to remove residual ambiguity. (Carries forward the prior block's
  HR-003 at reduced severity.)

#### Tests run

- grader on reference: 1.000 (8/8 subchecks; both gates pass).
- pytest (benchmark/eval): 35 passed, 0 failed.

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/fio-l1-nyc-csvwkt-addresses/` since the
prior evaluator-review block. `git log --follow` shows the only task-dir commits
after the prior re-eval are the two evaluator artefact commits themselves
(c2df4cd, 2026-05-26T13:43Z, prompt-grader-inconsistent block; 9c86fcf,
2026-05-26T20:35Z, calibrated block). The last *design-affecting* commit remains
b4583b4 (2026-05-17, prompt-change: removed the `geometry_wkt`-drop and row-count
sentences); the last grader change remains f0c244a (2026-05-18, behaviour-
preserving `is_wgs84` refactor); the last layout-only change remains 29a9ae3
(2026-05-26, path renames, no answer-key change). The change log in the first
evaluator block above is confirmed accurate against `git log --follow` and
`git show b4583b4 -- benchmark/tasks/fio-l1-nyc-csvwkt-addresses/`. This block is a
fresh sweep pass; no new design history to record.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (commit 29a9ae3, class:
  mixed — input-URL + reference-path rename only, no answer-key/instruction
  change). The last commit that changed the *instruction* is b4583b4
  (2026-05-17T12:48:37Z); the last that changed the *grader* is f0c244a
  (2026-05-18). All three current runs below started 2026-05-26, after every
  candidate cutoff.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:58:53Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:41:29Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:37:55Z | 0.875 | done | current |

No new runs have arrived since the prior re-eval block; the run set is identical
(two agent families, three current runs). Stale runs (24, all pre-b4583b4) are
catalogued in the first evaluator block above.

#### 2c-CRS — output-CRS and format consistency

Re-verified: `expected_outputs[]` (EPSG:4326, geoparquet), the reference output
(`reference/solution/outputs/addresses.geoparquet`, EPSG:4326), and `README.md`
(WGS84 GeoArrow WKB Point) all agree. The grader compares geometry per id
directly in degrees with a 1e-9° epsilon (`grade.py:259-281`) and reprojects
*neither* side — no one-sided reprojection. Gate 1 enforces CRS == EPSG:4326 via
`is_wgs84(sub.crs)`. Consistent; no finding.

#### Verdict

**calibrated** (confirms the prior re-eval block)

State is unchanged from the prior re-eval and the diagnosis holds. The three
current runs span 1.0 / 1.0 / 0.875. The only failed subcheck across all three is
`no_residual_geometry_wkt_column` on gemma 0748Z, where that same gemma 4 26B
model *dropped* `geometry_wkt` on a fresh draw (1922Z, 1.0) and opus dropped it
without hesitation (1753Z, 1.0). Dropping the source WKT text column when emitting
an Overture-schema GeoParquet is inferable convention (Overture
`addresses.address` carries a binary `geometry`, never a `geometry_wkt` text
column; README failure-mode #6 documents the residual-WKT mistake as a genuine
quality defect). The 0.125 it cost one gemma draw is the grader doing its job.

I re-ran the full triplet this pass: reference re-grades 1.000 (8/8 subchecks,
both gates); the three broken solutions land 0.000 / 0.750 / 0.875, matching the
`metadata.yaml` ranges and remaining in three distinct bands; pytest 35 passed.
No subcheck mis-fires. This is a well-calibrated L1 format-I/O task.

#### Specific findings

- The `no_residual_geometry_wkt_column` subcheck (`grade.py:286-298`) is correctly
  calibrated; the residual-WKT failure is a real quality defect, and capable
  agents (and gemma on a second draw) avoid it. No change applied.
- HR-001 below carries forward the unresolved design-rationale gap on commit
  b4583b4 (mis-titled "Remove CRS/operation nudges from 5 CRS task prompts" while
  editing this FIO task's output-schema sentences). New run evidence does not bear
  on this; it remains for the human owner.
- HR-002 below carries forward the optional prompt-vs-grader-judgment item: the
  instruction no longer states "drop geometry_wkt" while the grader checks for its
  absence. New evidence keeps it at **low** severity (inferable convention).
- Coverage tagging re-validated against `coverage-vocabulary.yaml`: all 11 axis
  values resolve to canonical slugs (`format-io`, `l1`, `csv-wkt`, `geoparquet`,
  `wgs84`, `bundled-local`, `attribute-type-coercion`, `point`,
  `addresses.address`, `new-york`, `small`). Only `evaluator_run_at` bumped.

### 3. Changes applied this run

#### Unilateral edits

(none — verdict is `calibrated`; the grader needs no loosening or tightening, and
the reference/inputs/failures are off-limits. Re-adding the WKT-drop sentence to
the instruction is a prompt change Step 4 does not authorize unilaterally, and the
run evidence shows it is unnecessary for calibration.)

#### Proposed but not applied (see HUMAN-REVIEW items)

<!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" -->
HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation nudges from 5
CRS task prompts") mis-describes its effect on this FIO task: it removed the
`geometry_wkt`-drop and row-count output-schema sentences, not a CRS nudge. The
human owner may want to audit the rest of that 5-task sweep for the same
over-correction. (Carries forward prior block's HR-001/HR-002.)

<!-- HUMAN-REVIEW id="HR-002" category="prompt-vs-grader-judgment" severity="low" -->
HR-002 — prompt-vs-grader-judgment — the instruction no longer explicitly tells
the agent to drop `geometry_wkt`, while the grader's
`no_residual_geometry_wkt_column` subcheck checks for its absence. New evidence
(same gemma model dropped it on a fresh 1.0 run, opus dropped it, inventory
implies the Overture schema with no WKT text column) shows this is inferable
convention. Optional fix: re-add "Drop the source `geometry_wkt` column." to the
instruction to remove residual ambiguity. (Carries forward prior block's HR-002.)

#### Tests run

- grader on reference: 1.000 (8/8 subchecks; both gates pass).
- broken solutions: wrong_format 0.000, no_type_coercion 0.750, int64_unit_count
  0.875 (all within `metadata.yaml` ranges, three distinct bands).
- pytest (benchmark/eval): 35 passed, 0 failed.

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

One new commit has touched `benchmark/tasks/fio-l1-nyc-csvwkt-addresses/` since
the prior evaluator-review block: 622342b ("Add task content versioning; drop
unused prompt_version", 2026-05-28T07:07:03Z). For this task it only removes the
single `prompt_version: 2026-05-08-a` line from `metadata.yaml`; no change to
tolerances, gates, subchecks, or any contract-affecting field. Classification:
`docs-change` (the field was an authoring-template tag with no runtime
relevance, per the commit body). The change log in the first evaluator block
above stands; this block adds the row below for completeness.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | docs-change | Removed `prompt_version: 2026-05-08-a` from `metadata.yaml`. No tolerance / contract change. | Commit msg: "Drop `prompt_version` entirely — it tagged the orchestrator's authoring template, not the task content, and has no runtime relevance." |

The last design-affecting commit remains b4583b4 (2026-05-17, prompt-change);
the last grader change remains f0c244a (2026-05-18, behaviour-preserving
`is_wgs84` refactor); the last layout-only change remains 29a9ae3 (2026-05-26,
path renames).

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-26T11:51:37+02:00 (commit 29a9ae3, class:
  mixed — input-URL + reference-path rename only, no answer-key/instruction
  change). The last commit that changed the *instruction* is b4583b4
  (2026-05-17T12:48:37Z); the last that changed the *grader* is f0c244a
  (2026-05-18). The 622342b commit is `docs-change` and does not move the
  cutoff. All seven current runs below started 2026-05-26 or later.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:37:55Z | 0.875 | done | current |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:58:53Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:41:29Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T21:27:39Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:55:19Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T02:15:44Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:45:01Z | 0.875 | done | current |

Four new runs joined the set since the prior block (run-20260527-2016Z,
run-20260527-2321Z, run-20260528-0113Z, run-20260528-0317Z). Stale runs (22, all
pre-b4583b4) remain catalogued in the first evaluator block.

Per-run output inspection (from each run's `score.json`):
- **opus 2016Z (1.0), opus 0113Z (1.0):** all 8 subchecks pass; 1056 rows;
  `recorded_at` = `timestamp[us]` (tz-naive), `unit_count` = `int32`, 7/7 text
  cols string, id Jaccard 1.0, all values + geometries preserved,
  `geometry_wkt` dropped.
- **gemma 2321Z (1.0):** all 8 subchecks pass; identical schema profile to
  opus runs above.
- **gemma 0317Z (0.875):** new failure mode — `address_columns_are_strings`
  fails 6/7 because the agent typed `postal_city` as Arrow `null` (the column
  is all-empty in the bundled CSV — 1056/1056 rows blank — and the agent's
  type-inference path collapsed it to `null` instead of `string`). All other
  subchecks pass: 1056 rows, `geometry_wkt` dropped (good), `recorded_at` =
  `timestamp[us, tz=UTC]`, `unit_count` = `int32`, id Jaccard 1.0, values and
  geometries preserved. Both gates pass.

#### 2c-CRS — output-CRS and format consistency

Re-verified: `expected_outputs[]` (EPSG:4326, geoparquet), the reference output
(`reference/solution/outputs/addresses.geoparquet`, EPSG:4326), and `README.md`
(WGS84 GeoArrow WKB Point) all agree. The grader compares geometry per id
directly in degrees with a 1e-9° epsilon (`grade.py:259-281`) and reprojects
*neither* side. Gate 1 enforces CRS == EPSG:4326 via `is_wgs84(sub.crs)`.
Consistent; no finding.

#### Verdict

**calibrated** (confirms the prior two re-eval blocks; the diagnosis still
holds.)

Seven current runs span 0.875–1.0 across two agent families (claude-code Opus
4-7 and OpenRouter Gemma 4 26B). The two non-1.0 runs (both Gemma) fail
*different* single subchecks — 0748Z failed `no_residual_geometry_wkt_column`
(kept the source WKT text column); 0317Z failed `address_columns_are_strings`
(typed `postal_city` as Arrow `null` because every row's value is the empty
string). Both failures are legitimate quality defects that the grader's
principled subchecks rightly catch:

- Residual `geometry_wkt`: documented in README failure-mode #6 as a real
  defect (doubled storage, downstream confusion). The same Gemma 4 26B model
  dropped it in three of four current draws (1922Z, 2321Z = 1.0; 0317Z also
  dropped it though it failed a different check) and Opus dropped it in all
  three draws.
- `postal_city` typed `null`: a real type-inference bug. A column whose every
  row is the empty string is not the same as a column whose every row is null
  — the input CSV stores empty strings (length 0) under
  `csv.QUOTE_ALL`-quoted columns, and the reference solution and competent
  agents preserve those as Arrow string. The grader is right to require
  `string` here; the principled detector for this failure mode is listed in
  README failure-mode #5 (re-typing of text columns to the wrong type).

Scores 1.0 / 1.0 / 0.875 / 1.0 / 1.0 / 1.0 / 0.875 form a sensible cohort: 5/7
runs (all Opus + 2 Gemma) hit ceiling; 2/7 (same Gemma model on different
draws) fail one subcheck each, on two *different* judgment-call defects. No
subcheck mis-fires; the reference re-grades 1.000 (8/8 subchecks, both gates);
the three broken solutions in `metadata.yaml` still land 0.000 / 0.750 / 0.875
in three distinct bands; pytest 41 passed. The task remains well-calibrated.

The prior block's HR-001 (commit b4583b4 mis-titled "Remove CRS/operation
nudges from 5 CRS task prompts" while editing a FIO task's output-schema
sentences) is unresolved by the new run evidence and carried forward at the
same low severity. The prior block's HR-002 (optional re-add of "Drop the
source `geometry_wkt` column" sentence) is also carried forward at low
severity; the residual-WKT failure mode appeared exactly once this pass
(0748Z) and the same model recovered on subsequent draws, so the inferable-
convention conclusion holds.

#### Specific findings

- The `no_residual_geometry_wkt_column` and `address_columns_are_strings`
  subchecks (`grade.py:181-197`, `grade.py:286-298`) are correctly calibrated.
  Each caught exactly one Gemma draw's quality defect; the same model on
  different draws produced correct outputs. No change applied.
- The `null`-type-for-all-empty-`postal_city` failure (0317Z) is a finer-
  grained variant of README failure-mode #5 ("Agent re-typed numeric-looking
  text columns" — the more general "address text columns must remain Arrow
  string"); the principled `address_columns_are_strings` subcheck catches it
  the same way. No HR needed: the README's existing language covers it
  adequately for a benchmark README.
- HR-001 below carries forward the design-rationale gap on commit b4583b4
  (unchanged from the prior block).
- HR-002 below carries forward the optional prompt-vs-grader-judgment item:
  the instruction no longer states "drop geometry_wkt" while the grader checks
  for its absence (unchanged from the prior block, still **low**).
- Coverage tagging re-validated against `coverage-vocabulary.yaml`: all 11
  axis values resolve to canonical slugs (`format-io`, `l1`, `csv-wkt`,
  `geoparquet`, `wgs84`, `bundled-local`, `attribute-type-coercion`, `point`,
  `addresses.address`, `new-york`, `small`). Only `evaluator_run_at` bumped.

### 3. Changes applied this run

#### Unilateral edits

(none — verdict is `calibrated`; the grader needs no loosening or tightening,
and the reference/inputs/failures are off-limits. Re-adding the WKT-drop
sentence to the instruction is a prompt change Step 4 does not authorize
unilaterally, and the broader run evidence shows it is unnecessary for
calibration. No `task.json.version` bump because no contract-affecting edit was
made.)

#### Proposed but not applied (see HUMAN-REVIEW items)

<!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" -->
HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation nudges from 5
CRS task prompts") mis-describes its effect on this FIO task: it removed the
`geometry_wkt`-drop and row-count output-schema sentences, not a CRS nudge. The
human owner may want to audit the rest of that 5-task sweep for the same
over-correction. (Carries forward prior block's HR-001.)

<!-- HUMAN-REVIEW id="HR-002" category="prompt-vs-grader-judgment" severity="low" -->
HR-002 — prompt-vs-grader-judgment — the instruction no longer explicitly tells
the agent to drop `geometry_wkt`, while the grader's
`no_residual_geometry_wkt_column` subcheck checks for its absence. The two
non-1.0 runs this pass failed *different* subchecks (0748Z residual WKT, 0317Z
`postal_city` as `null`), so the residual-WKT defect is one of two competing
borderline failure modes rather than a dominant calibration issue. Inferable-
convention conclusion stands. Optional fix: re-add "Drop the source
`geometry_wkt` column." to the instruction to remove residual ambiguity.
(Carries forward prior block's HR-002.)

#### Tests run

- grader on reference: 1.000 (8/8 subchecks; both gates pass).
- pytest (benchmark/eval): 41 passed, 0 failed.

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

One new commit has touched `benchmark/tasks/fio-l1-nyc-csvwkt-addresses/`
since the prior evaluator-review block: 05aabd6 ("Soften CRS hard-fail to
subcheck deductions across 21 graders", 2026-05-28T19:02:57Z). For this
task it rewires Gate 1's CRS branch to use the new `grade_crs_soft`
helper (`treat_none_as_wgs84=False`), adds module-level `CANONICAL_EPSG
= 4326` / `MEANINGFUL_EPSGS = {4326}`, and appends two soft subchecks
(`crs_is_canonical`, `crs_in_meaningful_set`). For a WGS84-out task with
no broader accept-list this is a behaviour-preserving refactor when the
agent submits EPSG:4326 (reference still scores 10/10), but it does
*change the answer key for partial credit* — total subcheck count goes
from 8 to 10, so the broken-solution band shifts (see Step 2c below).
Classification: `grader-change`.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 05aabd6 | grader-change | Replaced `is_wgs84` Gate-1 branch with `grade_crs_soft` (treat_none_as_wgs84=False); added module-level `CANONICAL_EPSG`/`MEANINGFUL_EPSGS`; appended `crs_is_canonical` + `crs_in_meaningful_set` subchecks. Subcheck count 8 → 10. | Commit msg: "Previously a CRS mismatch hard-failed Gate 1 ... over-penalises a recoverable failure mode. New policy ... reprojected to canonical for all downstream subchecks, and two new subchecks dock points." |

The last design-affecting commit on the prompt remains b4583b4
(2026-05-17). The last grader change is now 05aabd6 (2026-05-28T19:02Z).

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-05-28T19:02:57Z (commit 05aabd6, class:
  grader-change). This supersedes the prior block's cutoff of 29a9ae3.
  Runs started before this timestamp are stale evidence for the current
  grader.

#### Runs considered

Post-cutoff runs only (six runs across three agent families):

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-2225Z | openrouter / gemma-4-26b | 2026-05-28T23:04:33Z | 0.9 | done | current |
| run-20260528-2332Z | claude-code (opus-4-7) | 2026-05-29T00:09:34Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter / gemma-4-26b | 2026-05-29T02:15:30Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter / deepseek-v4-pro | 2026-05-31T12:29:51Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter / gemma-4-26b | 2026-06-06T10:04:59Z | 0.9 | done | current |
| run-20260606-1129Z | openrouter / gemma-4-26b | 2026-06-06T11:54:14Z | 1.0 | done | current |

Per-run output inspection (from each run's `score.json`):
- **gemma 2225Z (0.9):** 9/10 subchecks pass; only
  `no_residual_geometry_wkt_column` fails (kept the WKT text column).
  `recorded_at` = `timestamp[us, tz=UTC]`, `unit_count` = `int32`,
  string columns 7/7, id Jaccard 1.0, values + geometries preserved,
  CRS is canonical EPSG:4326.
- **opus 2332Z (1.0), gemma 0109Z (1.0), deepseek 0902Z (1.0), gemma
  1129Z (1.0):** all 10/10 subchecks pass; dropped `geometry_wkt`.
- **gemma 0953Z (0.9):** 9/10 pass; same `no_residual_geometry_wkt_column`
  miss; `recorded_at` `timestamp[us]` (tz-naive), `unit_count` `int32`,
  all values + geometries + ids preserved.

Pre-cutoff (stale) runs: the seven 2026-05-26 / 2026-05-27 / 2026-05-28
runs catalogued in the prior block (scored under the old 8-subcheck
grader) are stale. Their relative shape — 5/7 at 1.0, 2/7 gemma draws
failing one subcheck each — is consistent with the current set.

#### 2c-CRS — output-CRS and format consistency

Re-verified under the new soft-CRS grader: `expected_outputs[]`
(EPSG:4326, geoparquet), the reference output
(`reference/solution/outputs/addresses.geoparquet`, EPSG:4326), the
grader's `CANONICAL_EPSG = 4326` / `MEANINGFUL_EPSGS = {4326}`, and the
README (WGS84 GeoArrow WKB Point) all agree. Gate 1 only hard-fails
when the submission has no usable CRS at all
(`treat_none_as_wgs84=False`); otherwise the submission is reprojected
to EPSG:4326 before all geometric subchecks and the original EPSG is
docked via the two soft CRS subchecks. The reprojection is two-sided
in the sense that the comparison happens in EPSG:4326 for both sides
(reference is already 4326). Consistent; no finding.

#### Verdict

**calibrated** (confirms the prior verdict under the new grader)

Six post-cutoff current runs span 0.9–1.0 across three agent families
(claude-code Opus, OpenRouter Gemma, OpenRouter DeepSeek). The two
non-1.0 runs are both Gemma draws failing exactly one subcheck —
`no_residual_geometry_wkt_column`, the same residual-WKT failure mode
the prior blocks flagged. The pattern is unchanged from the prior
calibrated blocks: capable agents (Opus, DeepSeek) and most Gemma draws
drop `geometry_wkt`; a minority of Gemma draws keep it and lose ~0.1.
The grader's other 9 subchecks fire correctly in every run; no
mis-firing detected. The new CRS soft subchecks
(`crs_is_canonical`, `crs_in_meaningful_set`) are tautologically green
in every current run (every agent picked EPSG:4326, which is canonical
and meaningful), so under the current evidence they're inert
deductions — but they're cheap to keep and immediately useful the day
an agent picks a metric CRS like Web Mercator. No subcheck dock
deserves a finding.

Re-graded the reference and three broken solutions under the new
grader:
- reference: **1.000** (10/10 subchecks, both gates pass) — unchanged
  from prior pass in absolute score; subcheck counts 10/10 vs prior
  8/8.
- broken_wrong_format: **0.000** (Gate 1 still rejects — can't parse
  parquet body).
- broken_no_type_coercion: **0.800** (8/10) — was 0.750 (6/8). The two
  type subchecks still fail; the two new CRS subchecks pass (the
  broken set was generated with EPSG:4326 declared on the output, so
  the soft-CRS recovery applies and the score creeps up from 0.75 to
  0.80). Still inside the documented expected_score_range [0.70, 0.80]
  (sits at the upper bound).
- broken_int64_unit_count: **0.900** (9/10) — was 0.875 (7/8). Same
  pattern: only `unit_count_is_int32` fails; CRS subchecks pass. Still
  inside [0.85, 0.92].

The three-band cohort (0.000 / 0.800 / 0.900 / 1.000) remains four
distinct bands and is well-shaped. The task is well-calibrated under
the new soft-CRS grader.

#### Specific findings

- `metadata.yaml > broken_solutions > measured_score` values are stale
  under the new grader. **Fix applied unilaterally** per Step 4's
  "Update measured_score to the current grader's score on each broken
  set, with one re-run": no_type_coercion 0.75 → 0.80,
  int64_unit_count 0.875 → 0.900. Description lines bumped to match.
  `expected_score_range` values were left as-is because both new
  scores remain inside the documented ranges; widening ranges is not
  in the Step 4 unilateral list.
- README's `data/nyc_addresses.csv` path was stale from the 29a9ae3
  reorg (now `inputs/nyc_addresses.csv`). **Fix applied unilaterally**
  (docs-change, no version bump).
- README failure-mode #8 (CRS reprojection) described the old Gate-1
  CRS check that 05aabd6 retired. **Fix applied unilaterally**: now
  describes the two soft CRS subchecks and the reproject-before-geom
  policy. Failure-mode #1's "CRS metadata is absent" wording remains
  accurate because `treat_none_as_wgs84=False` still hard-gates that
  case.
- README failure-mode #2 / #3 quoted the prior 0.750 / 0.875 scores;
  bumped to 0.800 / 0.900. The "Expected weak-agent failure mode"
  paragraph also bumped the band labels accordingly.
- HR-001 below carries forward the design-rationale gap on commit
  b4583b4 (mis-titled "Remove CRS/operation nudges from 5 CRS task
  prompts" while editing this FIO task's output-schema sentences). New
  grader evidence does not bear on it.
- HR-002 below carries forward the optional prompt-vs-grader-judgment
  item: the instruction no longer states "drop geometry_wkt" while the
  grader checks for its absence. The same residual-WKT failure mode
  appeared twice in this pass (gemma 2225Z, 0953Z), unchanged shape
  from prior blocks; inferable-convention conclusion stands.
- Coverage tagging re-validated against `coverage-vocabulary.yaml`:
  all 11 axis values resolve to canonical slugs (`format-io`, `l1`,
  `csv-wkt`, `geoparquet`, `wgs84`, `bundled-local`,
  `attribute-type-coercion`, `point`, `addresses.address`, `new-york`,
  `small`). Only `evaluator_run_at` bumped.
- No `task.json.version` bump applied. The unilateral edits this pass
  touch only `metadata.yaml > broken_solutions > measured_score`
  (Step 4 explicitly exempts) and README (docs-change, exempt). No
  prompt, grader-logic, input, or tolerance edit was made. The
  underlying grader change in 05aabd6 was a sweep-wide commit and did
  not bump versions there either; this evaluator pass does not unilaterally
  change that precedent.

### 3. Changes applied this run

#### Unilateral edits

- `metadata.yaml`: bumped `broken_solutions.no_type_coercion.measured_score`
  0.75 → 0.80, `broken_solutions.int64_unit_count.measured_score`
  0.875 → 0.900. Description text updated to match new 10-subcheck
  arithmetic. Reason: new grader 05aabd6 added two CRS soft subchecks;
  measured scores need to track. Re-grade on reference: 1.000.
- `README.md`: input path `data/nyc_addresses.csv` →
  `inputs/nyc_addresses.csv`; failure-mode #8 rewritten to describe
  the new soft-CRS grader; failure-mode #2 / #3 and the weak-agent
  paragraph re-cited scores 0.800 / 0.900. Re-grade on reference:
  1.000.
- `task.json`: an uncommitted `analyst_notes` block was present in the
  working tree from a prior evaluator session (`description` plus
  `approach` and `pitfalls` arrays — covers the WKT-drop hidden gotcha,
  the `timestamp[us]` vs `[ns]` trap, the int32 vs int64 trap, and the
  leading-zero ZIP / row-count failure modes). Per Step 4
  ("author or refresh `analyst_notes`") this is an allowed unilateral
  edit and is included in this commit so the eval UI surfaces it. No
  `version` bump required — `analyst_notes` is human-facing only and
  is not seen by the agent at run time.

#### Proposed but not applied (see HUMAN-REVIEW items)

<!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" -->
HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation nudges
from 5 CRS task prompts") mis-describes its effect on this FIO task: it
removed the `geometry_wkt`-drop and row-count output-schema sentences,
not a CRS nudge. The human owner may want to audit the rest of that
5-task sweep for the same over-correction. (Carries forward prior
block's HR-001.)

<!-- HUMAN-REVIEW id="HR-002" category="prompt-vs-grader-judgment" severity="low" -->
HR-002 — prompt-vs-grader-judgment — the instruction no longer
explicitly tells the agent to drop `geometry_wkt`, while the grader's
`no_residual_geometry_wkt_column` subcheck checks for its absence. The
two non-1.0 current runs both failed this exact subcheck (gemma 2225Z,
0953Z). Inferable-convention conclusion stands (capable agents and
most Gemma draws drop it). Optional fix: re-add "Drop the source
`geometry_wkt` column." to the instruction to remove residual
ambiguity. (Carries forward prior block's HR-002.)

#### Tests run

- grader on reference: 1.000 (10/10 subchecks; both gates pass).
- broken solutions re-graded: wrong_format 0.000, no_type_coercion
  0.800, int64_unit_count 0.900 (all within `metadata.yaml`
  expected_score_range; four distinct bands).
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
- Geometry-type uniformity ("Point only") migrated to a new
  `geometry_type_point_only` subcheck.
- Row-count exact-match migrated to a new `row_count_exact` subcheck.
- Subcheck total grew from 10 to 12.

### Verification
- Reference solution re-graded: 1.0 (12/12 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

Two new design-affecting commits have touched
`benchmark/tasks/fio-l1-nyc-csvwkt-addresses/` since the prior
evaluator-review block (2026-06-06, commit 62de95a):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change | Removed `Gate("structural_correctness", ...)` and its early-return; geometry-type uniformity and exact row count migrated to soft subchecks (`geometry_type_point_only`, `row_count_exact`). Subcheck total 10 → 12. | Commit msg: "The structural_correctness gate was inconsistent across the 36 graders ... Library now has a single hard Gate(format_schema_valid); every check that survives light coercion is a Subcheck worth one point." (Also pre-documented in the manual-cleanup block above.) |
| 2026-06-07 | c749e57 | grader-change | Tagged the five data-content subchecks (`row_count_exact`, `id_set_preserved`, `unit_count_values_preserved`, `recorded_at_values_preserved`, `geometry_preserved_per_id`) with `weight=3.0`; schema/structural subchecks stay at 1.0. Total subcheck weight is now 22 (5x3 + 7x1). | Commit msg: "Adds weight kwarg (default 1.0) to geo_grading.Subcheck and switches ScoreReport.score to sum(weight where passed) / sum(weight). Data-content subchecks across fio, geo, spa, and dc graders are tagged weight=3.0." |

The last prompt change remains b4583b4 (2026-05-17). The full change
log lives in the first evaluator block above and stands confirmed
against `git log --follow`.

### 2. Current-state review

#### Cutoff

- design-affecting cutoff: 2026-06-07T18:32:38Z (commit c749e57,
  class: grader-change). Supersedes the prior block's cutoff of
  05aabd6.

#### Runs considered

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter / deepseek-v4-flash (detailed) | 2026-06-08T10:37:01Z | 1.0 | done | current (suite 6510297, task_version 1 = current) |
| run-20260609-084636Z | openrouter / deepseek-v4-flash (basic) | 2026-06-09T10:48:05Z | 1.0 | done | current (suite ec540aa, task_version 1 = current) |
| run-20260607-112430Z | openrouter / gemma-4-26b (detailed) | 2026-06-07T14:56:23Z | 1.0 | done | stale (pre-c749e57 weighting; 12/12 profile maps to 1.0 under weights too) |
| run-20260606-1733Z | openrouter / gemma-4-26b (detailed) | 2026-06-06T18:28:51Z | 1.0 | done | stale (pre-cutoff) |
| run-20260606-1334Z | openrouter / gemma-4-26b (detailed) | 2026-06-06T13:56:29Z | — | cancelled | stale (pre-cutoff, no score) |

Older stale runs (2026-05-12 through 2026-06-06) are catalogued in the
prior evaluator blocks. Note the two stale gemma 12-subcheck runs both
passed 12/12, which maps deterministically to 1.0 under the new
weighting, so they corroborate (but per the validity rules do not
count as) current evidence.

Per-run output inspection (current runs):
- **deepseek 074701Z (1.0):** 12/12 subchecks; 1056 rows; schema
  `recorded_at = timestamp[us, tz=UTC]`, `unit_count = int32`, 7/7
  text columns Arrow large_string, `geometry_wkt` dropped, CRS
  EPSG:4326, all Point. Matches reference profile.
- **deepseek 084636Z (1.0):** 12/12 subchecks; identical profile but
  tz-naive `timestamp[us]`. Matches reference profile.

#### 2c-CRS — output-CRS and format consistency

Re-verified: `expected_outputs[]` (EPSG:4326, geoparquet), the
reference output (EPSG:4326), the grader's `CANONICAL_EPSG = 4326` /
`MEANINGFUL_EPSGS = {4326}`, and the README (WGS84 GeoArrow WKB Point)
all agree. Gate hard-fails only when no usable CRS is declared
(`treat_none_as_wgs84=False`); both current submissions declared
EPSG:4326. No one-sided reprojection. Consistent; no finding.

#### Verdict

**insufficient-evidence**

Only two runs post-date the c749e57 weighting cutoff and both come
from the same agent family (deepseek-v4-flash, basic + detailed
prompt variants), so per the validity rules the run evidence cannot
support a calibration verdict on its own. What evidence exists is
consistent with the prior blocks' `calibrated` verdicts: both current
runs are clean 12/12, and the two immediately-pre-cutoff gemma runs
passed 12/12 (score mapping is weight-invariant at 12/12, so they
would also have scored 1.0 under the current grader). No grader
mis-fire was observed in any inspected run.

The static checks did surface one real concern, introduced by the
sweep-wide c749e57 weighting and not by anything task-local: this
task's central skill is Arrow type coercion, but the type subchecks
(`recorded_at_is_timestamp_us`, `unit_count_is_int32`,
`address_columns_are_strings`) carry weight 1 while the five
value-preservation subchecks carry weight 3. Re-grading the broken
sets under the current grader gives wrong_format 0.000,
no_type_coercion 0.909 (was 0.800), int64_unit_count 0.955 (was
0.900). Both non-zero sets now sit *above* their documented
`expected_score_range` upper bounds ([0.70, 0.80] and [0.85, 0.92]),
and a submission that skips the task's central skill entirely
(no type coercion at all) loses only ~0.09. See HR-003.

#### Prompt information audit

| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `addresses.geoparquet`, GeoParquet format | instruction | stated |
| Point geometry, EPSG:4326 | instruction | stated |
| `recorded_at` as `timestamp[us]` | instruction | stated |
| `unit_count` as `int32` | instruction | stated |
| seven address columns stay Arrow string | instruction ("all other columns as string") | stated |
| row count exact (`row_count_exact`, weight 3) | not stated | inferable (a format conversion implies row preservation; persona's SUM/WHERE framing reinforces it) |
| id set / per-id values / per-id geometry preserved | not stated | inferable (same conversion-implies-preservation logic) |
| `geometry_wkt` column dropped (`no_residual_geometry_wkt_column`) | not stated | inferable per prior blocks' evidence, but residual ambiguity remains -> HR-002 (carried) |
| CRS canonical EPSG:4326 (2 soft subchecks) | instruction | stated |

Factual claims checked: input name `nyc_addresses` matches
`inputs[].name` and `inputs/nyc_addresses.csv`; `recorded_at` and
`unit_count` exist in the CSV; the output filename and types match the
reference schema. No inaccurate claims found. One wording note: "all
other columns as string" can be read as including `geometry_wkt`,
which feeds the residual-WKT ambiguity tracked in HR-002.

#### Reference faithfulness

`reference/solution/generate.py` is faithful to the instruction: it
reads the all-quoted CSV as strings, coerces `unit_count` to int32 and
`recorded_at` to tz-naive `timestamp[us]`, parses WKT into Point
geometry in EPSG:4326, drops `geometry_wkt`, and writes
`addresses.geoparquet`. The only unrequested operation is a stable
sort by `id` before writing; the bundled CSV is already id-sorted at
authoring time (per the script docstring), the grader compares per-id
(order-insensitive), and the sort exists purely as a byte-determinism
safeguard, so it cannot disadvantage any agent. Not flagged.

#### Specific findings

- `metadata.yaml > broken_solutions > measured_score` was stale under
  the c749e57 weighting. **Fix applied unilaterally** per Step 4:
  no_type_coercion 0.800 -> 0.909, int64_unit_count 0.900 -> 0.955;
  description arithmetic updated to the 22-weight denominator.
  `expected_score_range` values left untouched (not in the Step 4
  unilateral list) and now both violated -> HR-003.
- README still described the retired Gate 2 (failure mode #7), the
  old "Gate 1" naming (#1), and the pre-weighting broken-set scores
  (#2, #3, weak-agent paragraph). **Fix applied unilaterally**
  (docs-change): row-count failure now cites the `row_count_exact`
  subcheck (weight 3), scores re-cited as 0.909 / 0.955, and the
  weak-agent paragraph notes the band compression with a pointer to
  this block.
- The c749e57 band compression itself is flagged for human review
  (HR-003): the sweep-wide "data-content 3x" policy deprioritizes
  exactly the skill this task tests. Options for the human: accept the
  compressed bands and widen the two `expected_score_range` entries,
  or rebalance weights per-task (e.g. tag the two type subchecks
  weight 3 as well, since type coercion *is* this task's data
  content). The second option is a grader-logic change with sweep-wide
  policy implications, so it is not applied unilaterally.
- HR-001 and HR-002 from the prior blocks remain unresolved by the new
  evidence and are carried forward unchanged (both low).
- Coverage tagging re-validated against `coverage-vocabulary.yaml`:
  all 11 axis values resolve (`format-io`, `l1`, `csv-wkt`,
  `geoparquet`, `wgs84`, `bundled-local`, `attribute-type-coercion`,
  `point`, `addresses.address`, `new-york`, `small`). Only
  `evaluator_run_at` bumped.
- No `task.json.version` bump: this pass edits only
  `metadata.yaml > broken_solutions > measured_score` and the README,
  both explicitly exempt. (`task.json` remains implicitly version 1.)

### 3. Changes applied this run

#### Unilateral edits

- `metadata.yaml`: `broken_solutions.no_type_coercion.measured_score`
  0.8 -> 0.909, `broken_solutions.int64_unit_count.measured_score`
  0.9 -> 0.955; description arithmetic updated for the weighted
  22-point denominator. Re-grade on reference: 1.000. Reason: c749e57
  changed the score formula; measured scores must track the current
  grader.
- `README.md`: failure modes #1 and #7 rewritten for the single-gate
  grader (Gate 2 no longer exists; row count is now the weighted
  `row_count_exact` subcheck); broken-set scores re-cited (0.909 /
  0.955); weak-agent paragraph notes the band compression. Re-grade on
  reference: 1.000. Reason: docs drifted behind 363aed2 and c749e57.

#### Proposed but not applied (see HUMAN-REVIEW items)

<!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" -->
HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation
nudges from 5 CRS task prompts") mis-describes its effect on this FIO
task: it removed the `geometry_wkt`-drop and row-count output-schema
sentences, not a CRS nudge. The human owner may want to audit the rest
of that 5-task sweep for the same over-correction. (Carried forward
unchanged from the prior blocks.)

<!-- HUMAN-REVIEW id="HR-002" category="prompt-vs-grader-judgment" severity="low" -->
HR-002 — prompt-vs-grader-judgment — the instruction does not tell the
agent to drop `geometry_wkt`, while the grader's
`no_residual_geometry_wkt_column` subcheck checks for its absence, and
"all other columns as string" can even be read as keep-everything.
Prior-block evidence (capable agents and most gemma draws drop it)
keeps this at inferable-convention / low. Note the c749e57 weighting
reduced the cost of this miss from 0.125-0.1 to ~0.045, so the open
question matters less in score terms now. Optional fix: re-add "Drop
the source `geometry_wkt` column." to the instruction. (Carried
forward from the prior blocks.)

<!-- HUMAN-REVIEW id="HR-003" category="grader-miscalibration-suspected" severity="med" -->
HR-003 — grader-miscalibration-suspected — the sweep-wide c749e57
"data-content subchecks 3x" weighting compresses this task's
discriminative bands: broken_no_type_coercion (skips the task's
central type-coercion skill entirely) now scores 0.909 (was 0.800,
documented range [0.70, 0.80]) and broken_int64_unit_count scores
0.955 (was 0.900, range [0.85, 0.92]) — both above their documented
`expected_score_range`, and the int64 set now clears the 0.95
near-perfect threshold. For this task the "data content" *is* the
Arrow schema typing, so weighting value-preservation 3x while the type
subchecks stay at 1 inverts the task's emphasis. Decide: (a) accept
the compression and widen the two `expected_score_range` entries in
`metadata.yaml`, or (b) tag the three type subchecks
(`recorded_at_is_timestamp_us`, `unit_count_is_int32`,
`address_columns_are_strings`) `weight=3.0` as task-local data-content
checks and re-measure (this is a grader-logic change requiring a
`version` bump and possibly the same treatment in sibling fio/dc
type-coercion tasks, e.g. dc-l1-bangkok-attribute-coercion). Severity
med: per-task scoring quirk, but the policy question spans the c749e57
sweep.

#### Tests run

- grader on reference: 1.000 (12/12 subchecks; single gate passes).
- broken solutions re-graded: wrong_format 0.000, no_type_coercion
  0.909, int64_unit_count 0.955 (both non-zero sets above their stale
  `expected_score_range` — see HR-003).
- pytest (benchmark/eval): see status.json.

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change in one line

Replaced the sweep-wide c749e57 "data-content subchecks 3x" weighting
with per-task reasoned subcheck weights: the three Arrow-type subchecks
(the task's central skill) now carry the highest weight, value-
preservation carries a middle weight, and structural / CRS / cosmetic
checks carry the lowest. This resolves HR-003 (the c749e57 band
compression). Grading-only change; no `task.json.version` bump, no edit
to the reference, inputs, or failures.

### Reasoning

This is an L1 format-I/O task. Per the grader docstring and
`task.json.instruction`, the central skill is **correct format
parsing/conversion with attribute type coercion** — reading an
all-quoted CSV-with-WKT and emitting GeoParquet with `recorded_at` as
Arrow `timestamp[us]`, `unit_count` as `int32`, the seven Overture
address columns kept as Arrow `string`, and the WKT parsed to Point
geometry. The subchecks that detect failure of that central skill are
the three Arrow-type checks. Under c749e57 those three sat at weight 1
(the lowest band) while the five value-preservation subchecks sat at
weight 3 — exactly inverting the task's emphasis. A submission that
skipped the central type-coercion step entirely
(`broken_no_type_coercion`) therefore scored 0.909, and a one-type miss
(`broken_int64_unit_count`) scored 0.955 (above the near-perfect 0.95
line), both above their documented bands.

New weights, reasoned from what the task tests:

- **Type subchecks → weight 3** (central skill): `recorded_at_is_timestamp_us`,
  `unit_count_is_int32`, `address_columns_are_strings`.
- **Value-preservation → weight 2** (important, but secondary to the
  type-literacy this task is built to probe): `row_count_exact`,
  `id_set_preserved`, `unit_count_values_preserved`,
  `recorded_at_values_preserved`, `geometry_preserved_per_id`.
- **Structural / cosmetic / CRS → weight 1** (lowest): `geometry_type_point_only`,
  `no_residual_geometry_wkt_column`, `crs_is_canonical`,
  `crs_in_meaningful_set`.

Total weight = 3×3 + 5×2 + 4×1 = 23. This restores both brokens to
their original documented `expected_score_range` while giving a clean
severity ranking for single-failure modes: structural miss 0.957 >
value miss 0.913 > type miss 0.870 (central skill hurts most), and more
failures score lower (no_type_coercion 0.739 < int64 0.870). No
threshold, gate, or check logic was altered.

### Weight changes (changed subchecks only)

| Subcheck | Old | New | Band |
|---|---|---|---|
| `recorded_at_is_timestamp_us` | 1.0 | 3.0 | type (central) |
| `unit_count_is_int32` | 1.0 | 3.0 | type (central) |
| `address_columns_are_strings` | 1.0 | 3.0 | type (central) |
| `row_count_exact` | 3.0 | 2.0 | value-preservation |
| `id_set_preserved` | 3.0 | 2.0 | value-preservation |
| `unit_count_values_preserved` | 3.0 | 2.0 | value-preservation |
| `recorded_at_values_preserved` | 3.0 | 2.0 | value-preservation |
| `geometry_preserved_per_id` | 3.0 | 2.0 | value-preservation |

Unchanged at weight 1.0 (structural / cosmetic / CRS):
`geometry_type_point_only`, `no_residual_geometry_wkt_column`,
`crs_is_canonical`, `crs_in_meaningful_set`.

### Broken-score before → after

| Broken | Before (c749e57) | After | Severity note |
|---|---|---|---|
| `broken_wrong_format` | 0.000 | 0.000 | not a parquet — hard gate; unchanged |
| `broken_no_type_coercion` | 0.909 | 0.739 | skips the central skill entirely (both numeric/timestamp cols stay string) — now the largest non-zero drop |
| `broken_int64_unit_count` | 0.955 | 0.870 | one central-type miss (int64 not int32) — moderate drop, below the no-coercion case |

Reference re-grades **1.000** (12/12 subchecks; single gate passes).

Ordering is now sensible: 0.000 < 0.739 < 0.870 < 1.000, monotone in
error severity, with the central-skill failures separated from each
other and from the (much lighter) cosmetic band. No disjoint-failure
inversion: a single value-preservation miss (0.913) scores strictly
above a single type miss (0.870), and a cosmetic/structural miss
(0.957) above both.

### Prior-run re-grade summary

Re-graded every prior run with an `outputs/` directory at the current
task version. The two runs the prior block lists as `current`
(run-20260608-074701Z, run-20260609-084636Z; both deepseek, clean
12/12) stay at **1.000**. All capable-agent 1.0 runs stay 1.0. The
notable shifts are the four single-subcheck-miss runs:

| Run | Failed subcheck | Old recorded | New | Note |
|---|---|---|---|---|
| run-20260526-0748Z | `no_residual_geometry_wkt_column` | 0.875 (8-check era) | 0.957 | cosmetic slip — now lightly docked |
| run-20260528-2225Z | `no_residual_geometry_wkt_column` | 0.900 (10-check era) | 0.957 | cosmetic slip |
| run-20260606-0953Z | `no_residual_geometry_wkt_column` | 0.900 | 0.957 | cosmetic slip |
| run-20260528-0317Z | `address_columns_are_strings` (postal_city → Arrow null) | 0.875 | 0.870 | central type miss — now docked more than the cosmetic slips |

The key improvement: under c749e57 the cosmetic residual-WKT miss and
the central type-column miss both scored an identical 0.9545; the new
weights correctly separate them (0.957 cosmetic vs 0.870 central). No
run inverted relative to a more-correct sibling.

### HUMAN-REVIEW items

HR-003 (grader-miscalibration-suspected — the c749e57 3x band
compression) is **resolved by this change** and removed from
`status.json`. HR-001 (design-rationale, b4583b4 mis-titled commit) and
HR-002 (prompt-vs-grader-judgment, WKT-drop not stated in the
instruction) are **unaffected by this grading-only change and carried
forward unchanged** at low severity.

<!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" -->
HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation
nudges from 5 CRS task prompts") mis-describes its effect on this FIO
task: it removed the `geometry_wkt`-drop and row-count output-schema
sentences, not a CRS nudge. The human owner may want to audit the rest
of that 5-task sweep for the same over-correction. (Carried forward
unchanged.)

<!-- HUMAN-REVIEW id="HR-002" category="prompt-vs-grader-judgment" severity="low" -->
HR-002 — prompt-vs-grader-judgment — the instruction does not tell the
agent to drop `geometry_wkt`, while the grader's
`no_residual_geometry_wkt_column` subcheck checks for its absence, and
"all other columns as string" can even be read as keep-everything.
Prior-block evidence (capable agents and most gemma draws drop it)
keeps this at inferable-convention / low. Under the new weights this
cosmetic miss docks only ~0.04. Optional fix: re-add "Drop the source
`geometry_wkt` column." to the instruction. (Carried forward unchanged.)

### Note on possibly-miscalibrated checks (not changed)

No threshold or check logic was changed. One observation for the human
owner, not acted on: a column whose every row is the empty string being
typed Arrow `null` instead of `string` (run-20260528-0317Z's
`postal_city`) is caught by `address_columns_are_strings` as an all-or-
nothing check — failing the whole weight-3 subcheck for one of seven
columns. This is defensible (the subcheck already reports the k/7 ratio
in its detail and the failure is a real type bug) but a per-column
partial-credit variant could be considered in a future logic change.

### Changes applied this run

#### Unilateral edits

- `grade.py`: subcheck `weight=` values only (table above). No logic,
  threshold, or gate change.
- `metadata.yaml`: `broken_no_type_coercion.measured_score` 0.909 →
  0.739, `broken_int64_unit_count.measured_score` 0.955 → 0.870;
  weight-arithmetic prose in both descriptions rewritten for the
  23-weight denominator. `expected_score_range` values left as
  authored ([0.70, 0.80] and [0.85, 0.92]) — both measured scores now
  fall back inside them.
- `README.md`: failure-mode #2/#3 scores re-cited (0.739 / 0.870),
  failure-mode #7 row-count weight 3→2 and cost ~0.14→~0.09, weak-agent
  paragraph rewritten to describe the per-task reasoned weights.
- `audit/AUTHORING_HISTORY.md`: this block.
- `audit/status.json`: removed HR-003; see status.json.

#### Tests run

- grader on reference: 1.000 (12/12 subchecks; single gate passes).
- broken solutions re-graded: wrong_format 0.000, no_type_coercion
  0.739, int64_unit_count 0.870 (both non-zero sets back inside their
  documented `expected_score_range`; four distinct bands).
- pytest: not run (orchestrator runs the suite).
