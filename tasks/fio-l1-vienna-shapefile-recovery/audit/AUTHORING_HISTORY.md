# Implementation notes — fio-l1-vienna-shapefile-recovery

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 format-I/O task: a hand-crafted CP1252-encoded Vienna parcel
shapefile (60 polygons in EPSG:31287, dBase columns pre-truncated to
10 chars) plus a `column_map.csv` → WGS84 GeoJSON with original
attribute names restored and German diacritics intact. Reference,
grader, and three broken solutions built and verified inside the
project Docker container.

## Verification results
- Reference grader score: 1.00 (10 / 10 subchecks pass)
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    (output written as `parcels.shp`; `parcels.geojson` absent).
  - truncated_columns: 0.500 (expected range [0.45, 0.55]) — 5 / 10
    pass; the five `column_renamed_*` subchecks fail, the four
    value/geometry subchecks still pass via the truncated-alias
    fallback, plus `diacritics_decoded`.
  - mojibake_encoding: 0.700 (expected range [0.65, 0.75]) — 7 / 10
    pass; `diacritics_decoded`, `katastralgemeinde_values_match`, and
    `eigentuemer_values_match` fail because the dBase bytes were
    re-decoded as UTF-8 with replacement.
- Second-run output match: bit-identical (verified with `diff -q` on
  `reference/outputs/parcels.geojson` before / after a second
  `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Wrong output format (Shapefile / CSV / not-a-GeoJSON):
  broken_wrong_format
- Skipped column-name recovery, kept dBase 10-char aliases:
  broken_truncated_columns
- Ignored .cpg sidecar, read dBase as UTF-8 (Mojibake):
  broken_mojibake_encoding
- Skipped reprojection / wrong CRS source: principled — Gate 1 CRS
  check + `geometry_reprojected_per_id`
- Dropped or duplicated rows: principled — Gate 2 strict-equality row
  count
- Mistyped recovered column name (`KATASTRALGEMEINDE` vs
  `KATASTRALGEMEINDE_NAME`): principled — per-column rename subcheck
- ASCII-folded diacritics: principled — `diacritics_decoded` plus
  per-id text-value subchecks

## Open issues
(none)

## Suggested prompt changes
(none)

## Inventory change proposals
(none)

## Library extensions
(none — the grader uses `Gate`, `Subcheck`, `ScoreReport`, plus inline
geopandas / shapely / pyarrow primitives. No new shared comparison
primitives were needed.)

## Runtime
~15 minutes (no live data fetch; all work is local Docker runs).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
An L1 format-I/O task that probes three composed Shapefile-recovery skills on a bundled 60-parcel Vienna cadastre snapshot: (1) honour the `.cpg` sidecar declaring CP1252 so German diacritics survive, (2) consume `column_map.csv` to recover dBase 10-char-truncated column names back to full names, and (3) reproject geometry from EPSG:31287 (MGI / Austria Lambert) to EPSG:4326 for the web viewer. Hand-crafted bundled inputs (60 polygons on a deterministic 6x10 grid, Vienna-flavoured attributes with ae/oe/ue/ss). The first commit (`6ab70b2`, 2026-05-08) ships the original task with an instruction that named both EPSG codes, listed the full and truncated column names, listed `FLAECHE_M2`, named "Mojibake" as the encoding failure, and pointed at the `.cpg` sidecar.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 6ab70b2 | initial-authoring | Initial task: bundled CP1252 shapefile, `column_map.csv`, grader with 2 gates + 10 subchecks, three broken solutions (wrong_format, truncated_columns, mojibake_encoding) | (initial) |
| 2026-05-08 | fbd20f2 | mixed (path rename) | Moved task into `benchmark/eval/tasks/` as part of repo restructure | Commit msg: split repo into thesis/ benchmark/ references/ — repo layout only |
| 2026-05-13 | a3a8d53 | mixed (path rename) | Moved task to `benchmark/tasks/` | Commit msg: move benchmark/eval/tasks/ to benchmark/tasks/ — repo layout only |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: add image-prompt.md to all 36 task directories |
| 2026-05-13 | 1b8dda1 | docs-change | Added `image.webp` | Commit msg: generate image.webp for all 36 task directories |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` via FLUX schnell | Commit msg: regenerate all 36 task card images via fal.ai FLUX schnell |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` via nano-banana-2 | Commit msg: regenerate task card images with nano-banana-2 (0.5K, 3:2) |
| 2026-05-13 | 9b1fb11 | prompt-change | Inlined the "Column renames" / "Geometry" / "Diacritics" blocks into prose; kept all factual content (EPSG codes, full + truncated column names, `FLAECHE_M2`, ".cpg sidecar", "Mojibake on Waehring / Mueller"). ASCII-folded the in-prompt examples (Währing → Waehring) | Commit msg: merge output schema blocks into prose for 7 task instructions |
| 2026-05-14 | 68384e4 | prompt-change | Stripped: input CRS (`EPSG:31287`), explicit umlaut examples, the ".cpg sidecar tells you the encoding" pointer, the "dBase columns got truncated to 10 chars in the 90s" framing, and the named truncated/full column lists. Kept: output CRS, `parcels.geojson` filename, "no Mojibake", row count, EPSG:4326, Polygon/MultiPolygon | Commit msg: remove input CRS mentions, geometry type descriptions, explicit column enumerations, format descriptions, and data value examples that models can discover by reading file metadata |
| 2026-05-15 | d65f3d9 | prompt-change | Round 2 stripping: removed "ae, oe, ue, and ss" diacritic enumeration; condensed two paragraphs into one. Still kept "no Mojibake", "full names restored", "row count must match" | Commit msg: strip deducible information from FIO task instructions (round 2) |
| 2026-05-17 | b4583b4 | prompt-change | Stripped row-count, no-Mojibake-mentioned-by-name, and the "none of the truncated aliases should remain" hard rule. Reduced to: "WGS84 GeoJSON `parcels.geojson` with the correct full column names and proper character encoding. Polygon or MultiPolygon in EPSG:4326." | Commit msg: remove CRS/operation nudges from 5 CRS task prompts |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `sub.crs is not None and sub.crs.to_epsg() == 4326` with shared `is_wgs84(sub.crs)`. Semantic shift: `is_wgs84` returns `True` for `None` CRS (RFC 7946) where the old check returned False | Commit msg: consolidate WGS 84 CRS checks into shared geo_grading package |
| 2026-05-26 | 29a9ae3 | mixed (path rename + docs) | Folder layout reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/{generate.py,outputs/}` → `reference/solution/`, `tests/` → `reference/failures/`, `image.*` → `assets/`. `grade.py` only path constant updated | Commit msg: reorganize task folder layout |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit `29a9ae3`, class: mixed — paths only, grader semantics unchanged on a submitter's `parcels.geojson`)
- semantic cutoff (last commit that could change scoring on the same submission): 2026-05-18T06:35:57Z (commit `f0c244a`, grader-change — `is_wgs84(None)` now passes Gate 1 where the old inline check did not)
- prompt cutoff: 2026-05-17T12:48:37Z (commit `b4583b4`)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:41:27Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:52:59Z | 1.0 | done | stale (pre-cutoff, post-prompt) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:33:57Z | 1.0 | done | stale |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T08:40:01Z | 1.0 | done | stale (pre-final prompt) |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T04:21:32Z | 1.0 | done | stale (pre-final prompt) |
| run-20260516-2248Z .. run-20260514-0946Z | claude-code-opus-basic, openrouter-deepseek-v4-flash-basic, openrouter-hy3-preview-basic | various | 1.0 (all) | done | stale (pre-prompt-cutoff) |
| run-20260513-0922Z..0937Z | openrouter-gemma4-26b-basic | 2026-05-13 | None | failed/cancelled | stale (infra failures: missing API key, ConnectError) |
| run-20260512-2259Z | claude-code-sonnet-basic | 2026-05-12T22:59:56Z | 0.0 | done | stale (pre-final prompt) |
| run-20260512-0833Z | claude-code-haiku-basic | 2026-05-12T08:36:02Z | 0.0 | done | stale (pre-final prompt) |

Stale-run footnote: across all 25 runs spanning 2026-05-12 → 2026-05-26, eight different adapters appear; 22 of 22 successful runs from 2026-05-14 onward scored 1.0; two pre-prompt-cutoff runs scored 0.0 (haiku on 05-12 and sonnet on 05-12 with the original verbose instruction). Only one run (gemma4-26b, 2026-05-26, score 1.0) is current under the strict cutoff.

#### Verdict
**insufficient-evidence**

Only one run (gemma4-26b at 1.0) started after the 2026-05-18 semantic grader cutoff. The strict definition in the evaluator prompt (fewer than 2 current runs, or all from one agent family) puts this task in `insufficient-evidence`. That said, the stale-run pattern is suggestive: every run after the final prompt strip on 2026-05-17 — eight runs across four agent families (claude-opus, deepseek-v4-flash, gemma4-26b, hy3-preview) — scored 1.0. The instruction was deliberately stripped in three rounds (`68384e4`, `d65f3d9`, `b4583b4`) and the gemma4-26b 26B-A4B-IT model still solved it cleanly with a five-step `solve.py`. This is consistent with the author's own stated expectation ("the three sub-skills are each one-liner library calls"; README/Why-this-difficulty section), but it does not rule out `too-easy`. The current instruction reads: "Migrating an old parcel shapefile (`parcels`) into our web viewer — a reference file `column_map` is provided alongside it. Need a clean WGS84 GeoJSON `parcels.geojson` with the correct full column names and proper character encoding. Polygon or MultiPolygon in EPSG:4326." All four gifts are gone (no input CRS, no `.cpg` mention, no column-name enumeration, no "no Mojibake" warning, no row-count rule). What remains is the output contract and the existence of `column_map`. The grader retains all 10 subchecks and the gate-level row-count + CRS + geometry-type checks (which are part of the contract, not gifts). Flagged below as a borderline "task may be too easy" item for human review.

#### Specific findings
- Reference grader still scores 1.0 (10/10) on `reference/solution/outputs/`. <!-- HUMAN-REVIEW id="HR-001" category="task-too-easy-suspected" severity="low" --> Pre-cutoff runs after the final prompt strip (2026-05-17) show 8/8 score = 1.0 across four agent families; only one current run exists (also 1.0). The instruction is now minimal and the persona reasonably keeps `column_map` and the output contract. Recommend a re-sweep with weak agents (haiku, low-tier OpenRouter models) under the current prompt to confirm whether any weak-agent failure mode is still reachable — particularly the Mojibake failure (`broken_mojibake_encoding`, currently the principal failure-mode story).
- Broken-solution measured scores still match `metadata.yaml`: wrong_format=0.0, truncated_columns=0.5, mojibake_encoding=0.7. No grader drift detected.
- Grader change `f0c244a` (is_wgs84 swap) has a semantic side-effect: a submission with CRS=None on a GeoJSON would now pass Gate 1 (RFC 7946 implicit-WGS84) where previously it would have failed. This is correct behaviour for GeoJSON and is consistent with how the grader's Gate-1 rationale reads in the README, so it does not require action.
- The `task.json > tags` block lists CRS `EPSG:31287` and `EPSG:4326` and `operations: [format_conversion, reprojection]` — these are tag metadata, not part of the instruction shown to the agent, so they do not gift information. No action.
- All `coverage.yaml` slugs validate against `coverage-vocabulary.yaml`. The task uses two CRSes (WGS84 output and a conformal-projection input — MGI Lambert), both of which exist in the vocabulary. No vocabulary gap.

### 3. Changes applied this run

#### Unilateral edits
(none — the verdict is `insufficient-evidence` for the strict-cutoff window; the borderline "may be too easy" signal is flagged for human review rather than acted on, because the prompt is already aggressively stripped and any further trimming would touch the persona voice or the output contract.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — task-too-easy-suspected — Suggest a low-tier-model re-sweep under the current prompt to confirm whether the Mojibake failure mode is still reachable; if no weak agent can fail this task, consider whether the L1 calibration target has drifted.

#### Tests run
- grader on reference: 1.0 (10/10)
- grader on broken_wrong_format: 0.0 (within [0.0, 0.0])
- grader on broken_truncated_columns: 0.5 (within [0.45, 0.55])
- grader on broken_mojibake_encoding: 0.7 (within [0.65, 0.75])
- pytest: pass (35/35)

---

## Evaluator review 2026-05-26 (second pass)  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/fio-l1-vienna-shapefile-recovery/` since the prior evaluator commit (`caa3d1f`, 2026-05-26T13:54Z). `git log caa3d1f..HEAD -- <task dir>` is empty; the only intervening commits are other tasks' evaluator passes. The design history reconstructed in the first evaluator-review block above is therefore still complete and accurate. No re-derivation needed.

This second pass was triggered because two fresh runs (claude-code opus and openrouter gemma) were added after the prior evaluation, which was stuck at `insufficient-evidence` (only one current run).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit `29a9ae3`, class: mixed — folder-layout paths only; no change to grader semantics on a submitter's `parcels.geojson`)
- semantic cutoff (last commit that could change scoring on the same submission): 2026-05-18T06:35:57Z (commit `f0c244a`, grader-change — `is_wgs84(None)` now passes Gate 1 where the old inline check did not)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-26T18:59:52Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T19:42:34Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:41:27Z | 1.0 | done | post-semantic-cutoff, pre-paths-cutoff (the 09:51Z commit is paths-only, so scoring-valid) |
| (25 earlier runs 2026-05-12 .. 2026-05-17) | 8 adapters across 4+ families | various | 1.0 (22/22 successful from 05-14 on); 0.0 (haiku & sonnet on 05-12, original verbose prompt); None (infra failures 05-13) | done/failed | stale (pre-cutoff) |

Stale-run footnote: the full run history was reviewed in the first evaluator-review block. The two pre-cutoff 0.0 scores (haiku, sonnet, both 2026-05-12) predate the three prompt-strip rounds and the grader consolidation, so they are not evidence about the current task. Every successful run from 2026-05-14 onward scored 1.0.

#### Per-run output inspection (current runs)
Both current runs wrote `outputs/parcels.geojson` plus intermediate artefacts (the downloaded shapefile sidecars + a `solve.py`). Light comparison against `reference/solution/outputs/parcels.geojson`:

| Property | Reference | run-...1753Z (opus) | run-...1922Z (gemma) |
|---|---|---|---|
| feature count | 60 | 60 | 60 |
| CRS | EPSG:4326 | EPSG:4326 | EPSG:4326 |
| geometry types | {Polygon} | {Polygon} | {Polygon} |
| columns | full names restored (KATASTRALGEMEINDE_NAME … FLAECHE_M2) | identical | identical |

Both `score.json` files show all 2 gates + all 10 subchecks passing, including `diacritics_decoded`, the five `column_renamed_*` checks, and `geometry_reprojected_per_id`. The 1.0 scores are legitimate: both agents performed the CP1252 read, the column-name recovery, and the EPSG:31287→4326 reprojection correctly.

#### Verdict
**calibrated**

Two current runs from two different agent families now exist (claude-code opus + openrouter gemma-4-26b), both at 1.0 — this clears the `insufficient-evidence` bar that blocked the prior pass. The decision is therefore between `calibrated` and `too-easy`. The `too-easy` verdict requires *both* that all current runs score ≥0.95 *and* that the instruction over-specifies the answer. The first conjunct holds; the second does not. The instruction has already been stripped of every gift across three documented rounds (commits `68384e4`, `d65f3d9`, `b4583b4`): no input CRS, no `.cpg`/encoding pointer, no column-name enumeration, no umlaut examples, no "no Mojibake" warning, no row-count rule. What remains is the bundled input handles (`parcels`, `column_map`), the output filename, the goal statement ("correct full column names and proper character encoding"), and the output contract (WGS84 / Polygon-or-MultiPolygon GeoJSON). None of these names the *mechanism* — the agent must still discover the truncation (read the dbf), the CP1252 declaration (read the .cpg), and the source CRS (read the .prj) on its own. Per the design prompt this is correct L1 framing (name the goal, not the chain). An L1 task being cleanly solved by a capable agent — even a 26B-parameter one — is the intended L1 ≫ L2 ≫ L3 gradient, not miscalibration. The Mojibake failure mode remains reachable and the grader still resolves it (broken_mojibake_encoding = 0.7). No defensible unilateral edit exists: any further trimming would touch the persona voice or the output contract, both off-limits.

This resolves the prior pass's HR-001 (`task-too-easy-suspected`, which had requested exactly this second-family / weak-agent re-sweep): the weak 26B model has now been re-run under the current minimal prompt and still scored 1.0, confirming the instruction is not the bottleneck and the task is calibrated for L1.

#### Specific findings
- Reference re-graded at 1.0 (10/10). Broken solutions re-graded at 0.0 / 0.5 / 0.7, all matching `metadata.yaml` — no grader drift since authoring. No action.
- Both current runs (opus, gemma) produce outputs structurally identical to the reference (60 Polygon features, EPSG:4326, full column names, diacritics intact). The 1.0 scores are corroborated by direct output inspection, not just the harness number. No action.
- All current runs scored 1.0. This is expected L1 behaviour given the genuinely one-liner sub-skills and the already-minimal prompt; it is *not* treated as a miscalibration flag because the second `too-easy` conjunct (over-specifying instruction) is not met. No edit and no human-review flag raised.
- `coverage.yaml` slugs all validate against `coverage-vocabulary.yaml` (re-checked: format-io, l1, shapefile+csv in, geojson out, wgs84+conformal CRS, bundled-local, shapefile-column-truncation + encoding-issues, polygon, vienna, small). No vocabulary gap.

### 3. Changes applied this run

#### Unilateral edits
(none — verdict is `calibrated`; the grader/reference/brokens triplet is internally consistent and no gift remains to strip.)

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.0 (10/10)
- grader on broken_wrong_format: 0.0 (within [0.0, 0.0])
- grader on broken_truncated_columns: 0.5 (within [0.45, 0.55])
- grader on broken_mojibake_encoding: 0.7 (within [0.65, 0.75])
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

No new commits have touched `benchmark/tasks/fio-l1-vienna-shapefile-recovery/` since the prior evaluator commit (`7db25a3`, 2026-05-26T20:39:13Z, the `calibrated` second-pass commit). `git log 7db25a3..HEAD -- <task dir>` is empty; the only intervening commits on `main` are other tasks' evaluator passes (e.g. `fio-l1-paris-kml-pois`, `fio-l1-nyc-csvwkt-addresses`, the `dd-*`/`dc-*` series). The design history reconstructed in the two prior evaluator-review blocks above is therefore still complete and accurate. No re-derivation needed. The full change log (initial authoring `6ab70b2` → three prompt-strip rounds `68384e4`/`d65f3d9`/`b4583b4` → `is_wgs84` grader consolidation `f0c244a` → folder-layout reorg `29a9ae3`) stands.

This third pass is a routine sweep re-confirmation; no fresh runs or commits triggered it.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit `29a9ae3`, class: mixed — folder-layout paths only; cannot change scoring on a submitter's `parcels.geojson`)
- semantic cutoff (last commit that could change scoring on the same submission): 2026-05-18T06:35:57Z (commit `f0c244a`, grader-change — `is_wgs84(None)` now passes Gate 1 where the old inline check did not)

#### Runs considered
No new runs have appeared since the second pass; the most recent run directory is still `run-20260526-1922Z`. The run set is unchanged.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-1753Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-26T18:59:52Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T19:42:34Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:41:27Z | 1.0 | done | post-semantic-cutoff, pre-paths-cutoff (the 09:51Z commit is paths-only, so scoring-valid) |
| (25 earlier runs 2026-05-12 .. 2026-05-17) | 8 adapters across 4+ families | various | 1.0 (22/22 successful from 05-14 on); 0.0 (haiku & sonnet on 05-12, original verbose prompt); None (infra failures 05-13) | done/failed | stale (pre-cutoff) |

Stale-run footnote: the full 28-run history was reviewed in the first two evaluator-review blocks. The two pre-cutoff 0.0 scores (haiku, sonnet, both 2026-05-12) predate the three prompt-strip rounds and the grader consolidation, so they are not evidence about the current task. Every successful run from 2026-05-14 onward scored 1.0.

#### Per-run output inspection (current runs)
Re-confirmed by direct read of both current outputs against `reference/solution/outputs/parcels.geojson`:

| Property | Reference | run-...1753Z (opus) | run-...1922Z (gemma) |
|---|---|---|---|
| feature count | 60 | 60 | 60 |
| CRS | EPSG:4326 | EPSG:4326 | EPSG:4326 |
| geometry types | {Polygon} | {Polygon} | {Polygon} |
| columns | full names restored (KATASTRALGEMEINDE_NAME … FLAECHE_M2) | identical | identical |

Both `score.json` files show all 2 gates + all 10 subchecks passing (including `diacritics_decoded`, the five `column_renamed_*` checks, and `geometry_reprojected_per_id`). The 1.0 scores are corroborated by direct output inspection.

CRS/format consistency (Step 2c-CRS): the reference output (EPSG:4326), `expected_outputs[].crs` (EPSG:4326), the README's stated output CRS (EPSG:4326), and the instruction (WGS84 / EPSG:4326) all agree. The grader's CRS handling is a Gate-1 `is_wgs84(sub.crs)` check plus per-id centroid comparison in the common 4326 space for both sides — no one-sided reprojection. Consistent; no finding.

#### Verdict
**calibrated**

Unchanged from the prior pass and re-confirmed. Two current runs from two different agent families (claude-code opus + openrouter gemma-4-26b) both score 1.0, clearing the `insufficient-evidence` bar. The `too-easy` verdict needs *both* all-current-runs ≥0.95 *and* an over-specifying instruction; the first holds but the second does not. The instruction was stripped of every gift across three documented rounds (`68384e4`, `d65f3d9`, `b4583b4`): no input CRS, no `.cpg`/encoding pointer, no column-name enumeration, no umlaut examples, no "no Mojibake" warning, no row-count rule. What remains — the bundled handles (`parcels`, `column_map`), the output filename, the goal ("correct full column names and proper character encoding"), and the output contract (WGS84 / Polygon-or-MultiPolygon GeoJSON) — names the goal, not the mechanism: the agent must still discover the truncation (read the .dbf), the CP1252 declaration (read the .cpg), and the source CRS (read the .prj) itself. A capable agent cleanly solving an L1 task is the intended L1≫L2≫L3 gradient, not miscalibration. The Mojibake failure mode remains reachable and the grader resolves it (broken_mojibake_encoding = 0.7). No defensible unilateral edit exists; any further trimming would touch the persona voice or the output contract, both off-limits.

#### Specific findings
- Reference re-graded at 1.0 (10/10). Broken solutions re-graded at 0.0 / 0.5 / 0.7, all matching `metadata.yaml` — no grader drift since authoring. No action.
- Both current runs (opus, gemma) produce outputs structurally identical to the reference (60 Polygon features, EPSG:4326, full column names, diacritics intact). The 1.0 scores are corroborated by direct output inspection, not just the harness number. No action.
- All current runs scored 1.0. Expected L1 behaviour given the genuinely one-liner sub-skills and the already-minimal prompt; not a miscalibration flag because the `too-easy` over-specification conjunct is not met. No edit, no flag.
- `coverage.yaml` slugs all re-validate against `coverage-vocabulary.yaml` (format-io; l1; shapefile+csv in; geojson out; wgs84+conformal CRS; bundled-local; shapefile-column-truncation + encoding-issues; polygon; vienna; small). No vocabulary gap. Cross-checked against the inventory row: matches on category, difficulty, region, data source, formats, CRS, geometry, scale, and quality issues.

### 3. Changes applied this run

#### Unilateral edits
(none — verdict is `calibrated`; the grader/reference/brokens triplet is internally consistent and no gift remains to strip.)

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.0 (10/10)
- grader on broken_wrong_format: 0.0 (within [0.0, 0.0])
- grader on broken_truncated_columns: 0.5 (within [0.45, 0.55])
- grader on broken_mojibake_encoding: 0.7 (within [0.65, 0.75])
- pytest: pass (35/35)


---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

One new commit has touched `benchmark/tasks/fio-l1-vienna-shapefile-recovery/` since the prior evaluator commit (`24f0707`, 2026-05-27T15:44Z, the third-pass `calibrated` re-confirmation): `622342b` (2026-05-28T07:07Z) "Add task content versioning; drop unused prompt_version". The repo-wide change introduces an optional `task.json.version` integer and removes the historical `prompt_version` field. For this task it only touched `metadata.yaml` — a single-line deletion of `prompt_version: 2026-05-08-a`. No edit to `task.json`, `grade.py`, `inputs/`, `reference/`, or tolerances. Classification: **docs-change** (the `prompt_version` field was metadata about the orchestrator template, not about the agent-visible task content). The task is now implicitly version 1 per the new versioning semantics; no explicit `version` key is present in `task.json`.

The design history reconstructed in the three prior evaluator-review blocks remains complete and accurate (initial authoring `6ab70b2` → three prompt-strip rounds `68384e4`/`d65f3d9`/`b4583b4` → `is_wgs84` grader consolidation `f0c244a` → folder-layout reorg `29a9ae3` → docs-only `622342b`). No re-derivation needed.

#### Change log (appended)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | docs-change | Removed `prompt_version: 2026-05-08-a` line from `metadata.yaml` as part of repo-wide drop of the field | Commit msg: prompt_version "tagged the orchestrator's authoring template, not the task content, and has no runtime relevance" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit `29a9ae3`, class: mixed — folder-layout paths only; `622342b` is docs-change and does not advance the cutoff)
- semantic cutoff (last commit that could change scoring on the same submission): 2026-05-18T06:35:57Z (commit `f0c244a`, grader-change — `is_wgs84(None)` now passes Gate 1)

#### Runs considered
Four new runs have appeared since the third pass (two opus, two gemma). All started after both cutoffs and are therefore `current`.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T03:46:40Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:17:58Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-27T23:56:58Z | 1.0 | done | current (parent run.json marked failed at sweep level, but the per-task block is `status: done, score: 1.0`) |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T21:31:15Z | 1.0 | done | current |
| run-20260526-1922Z | openrouter-gemma4-26b-basic | 2026-05-26T19:42:34Z | 1.0 | done | current |
| run-20260526-1753Z | claude-code-opus-basic | 2026-05-26T18:59:52Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:41:27Z | 1.0 | done | post-semantic-cutoff, pre-paths-cutoff (paths-only commit; scoring-valid) |
| (25 earlier runs 2026-05-12 .. 2026-05-17) | 8 adapters across 4+ families | various | 1.0 (22/22 successful from 05-14); 0.0 (haiku, sonnet on 05-12 with original verbose prompt); None (infra failures 05-13) | done/failed | stale (pre-cutoff) |

Stale-run footnote: the full 32-run history was reviewed across the three prior evaluator-review blocks. The two pre-cutoff 0.0 scores predate the three prompt-strip rounds and the grader consolidation. Every successful run from 2026-05-14 onward scored 1.0.

#### Per-run output inspection (current runs)
Both 2026-05-28 current runs wrote `outputs/parcels.geojson` plus the downloaded shapefile sidecars and a `solve.py`. Light comparison against `reference/solution/outputs/parcels.geojson`:

| Property | Reference | run-...0317Z (gemma) | run-...0113Z (opus) |
|---|---|---|---|
| feature count | 60 | 60 | 60 |
| CRS | EPSG:4326 | EPSG:4326 | EPSG:4326 |
| geometry types | {Polygon} | {Polygon} | {Polygon} |
| columns | KATASTRALGEMEINDE_NAME … FLAECHE_M2 | identical | identical |

Both `score.json` files show all 2 gates + all 10 subchecks passing (including `diacritics_decoded`, the five `column_renamed_*` checks, and `geometry_reprojected_per_id` with `60/60 centroids within 1e-05°`). The 1.0 scores are corroborated by direct output inspection.

CRS/format consistency (Step 2c-CRS): the reference output (EPSG:4326), `expected_outputs[].crs` (EPSG:4326), the README's stated output CRS (EPSG:4326), and the instruction (WGS84 / EPSG:4326) all agree. The grader's CRS handling is a Gate-1 `is_wgs84(sub.crs)` check plus per-id centroid comparison in the common 4326 space for both sides — no one-sided reprojection. Consistent; no finding.

#### Verdict
**calibrated**

Unchanged and re-confirmed across a fourth pass. Six current runs from two agent families (claude-code opus + openrouter gemma-4-26b) all score 1.0 — well over the `insufficient-evidence` bar. The `too-easy` verdict needs *both* all-current-runs ≥0.95 *and* an over-specifying instruction; the first holds, the second does not. The instruction was stripped of every gift across three documented rounds (`68384e4`, `d65f3d9`, `b4583b4`); what remains names the goal (full column names + proper encoding + WGS84 GeoJSON) without naming the mechanism (truncation, CP1252, source CRS). A capable agent cleanly solving an L1 task is the intended L1≫L2≫L3 gradient. The Mojibake failure mode remains reachable (broken_mojibake_encoding=0.7), and the truncated-columns failure remains distinguishable (broken_truncated_columns=0.5). No defensible unilateral edit exists; any further trimming would touch the persona voice or the output contract.

The new repo-wide versioning commit `622342b` did not change anything about this task that an agent or the grader can see (single line removed from `metadata.yaml` notes). No version bump is required this pass because no unilateral edit was made.

#### Specific findings
- Reference re-graded at 1.0 (10/10). Broken solutions re-graded at 0.0 / 0.5 / 0.7, all matching `metadata.yaml` — no grader drift. No action.
- Four fresh current runs (two opus on 05-27/05-28, two gemma on 05-27/05-28) all score 1.0 with identical output shape to the reference (60 Polygon features, EPSG:4326, full column names, diacritics intact). No action.
- All current runs scored 1.0. Expected L1 behaviour given the genuinely one-liner sub-skills and the already-minimal prompt; not a miscalibration flag because the `too-easy` over-specification conjunct is not met. No edit, no flag.
- `coverage.yaml` slugs all re-validate against `coverage-vocabulary.yaml`. Cross-checked against the inventory row: matches on category, difficulty, region, data source, formats, CRS, geometry, scale, and quality issues. No vocabulary gap.
- Task does not currently carry an explicit `task.json.version` field; per the new versioning semantics it is implicitly v1. Will be made explicit (`version: 2`) on the first future unilateral edit that touches prompt/grader/inputs/tolerances. No action this pass.

### 3. Changes applied this run

#### Unilateral edits
(none — verdict is `calibrated`; the grader/reference/brokens triplet is internally consistent and no gift remains to strip. Per Step 4 versioning rules a `task.json.version` bump is only required on the first unilateral edit that meaningfully changes the prompt, grader, tolerances, or input contract; no such edit was applied.)

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.0 (10/10)
- grader on broken_wrong_format: 0.0 (within [0.0, 0.0])
- grader on broken_truncated_columns: 0.5 (within [0.45, 0.55])
- grader on broken_mojibake_encoding: 0.7 (within [0.65, 0.75])
- pytest: pass (41/41)


---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

One new commit has touched `benchmark/tasks/fio-l1-vienna-shapefile-recovery/` since the prior evaluator commit (`2930b9a`, 2026-05-28T14:35Z): `05aabd64` (2026-05-28T19:02:57Z) "Soften CRS hard-fail to subcheck deductions across 21 graders". Classification: **grader-change**. The repo-wide change swaps the inline `is_wgs84(sub.crs)` Gate-1 check for the shared `grade_crs_soft(sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True)` helper, and adds two new subchecks at the end (`crs_is_canonical`, `crs_in_meaningful_set`). The new Gate-1 only hard-fails when the submission has no usable CRS at all; otherwise the submission is reprojected to canonical for downstream subchecks and CRS quality is graded via the two new subchecks. For this task `CANONICAL_EPSG = 4326` and `MEANINGFUL_EPSGS = {4326, 31287}`, so a submission left in EPSG:31287 (the source CRS) now scores higher than a random projected CRS but still loses the canonical subcheck and the geometry subcheck (centroids land at projected coordinates). Net effect on the grader's denominator: 10 → 12 subchecks. The reference still scores 12/12 = 1.0; the brokens shift from 0.0 / 0.5 / 0.7 to 0.0 / 7-of-12 = 0.583 / 9-of-12 = 0.75.

#### Change log (appended)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 05aabd64 | grader-change | Replaced inline Gate-1 CRS check with `grade_crs_soft`; added two CRS subchecks (`crs_is_canonical`, `crs_in_meaningful_set`); added module constants `CANONICAL_EPSG=4326`, `MEANINGFUL_EPSGS={4326, 31287}` | Commit msg: a CRS mismatch previously hard-failed Gate 1 even when geometric work was correct; the new policy reprojects to canonical and docks via subchecks instead |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T19:02:57Z (commit `05aabd64`, class: grader-change — adds two subchecks, changes Gate-1 semantics on non-WGS84 submissions, advances both prior cutoffs)
- semantic cutoff coincides with design-affecting cutoff for this pass

#### Runs considered
Eight runs touched this task between the new cutoff (2026-05-28T19:02:57Z) and today (2026-06-06). Six are current with usable scores; two are cancelled/no-task-block.

| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1129Z | openrouter-gemma4-26b-detailed (google/gemma-4-26b-a4b-it) | 2026-06-06T12:02:08Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed (google/gemma-4-26b-a4b-it) | 2026-06-06T10:07:24Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic (deepseek/deepseek-v4-pro) | 2026-05-31T12:32:52Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-29T02:18:07Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-29T00:11:49Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T23:06:11Z | 1.0 | done | current |
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T21:33:09Z | 1.0 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56Z | None | cancelled | current but no useful score |
| run-20260606-0942Z / -1259Z / -1311Z | openrouter-gemma4-26b-detailed | various 2026-06-06 | n/a | (no task block in run.json) | excluded |
| run-20260528-1624Z and earlier | various | various | various | done/failed | stale (pre-grader-cutoff) |

Stale-run footnote: the full 41-run history was reviewed across the four prior evaluator-review blocks. Every successful run before the new grader-cutoff scored 1.0 from 2026-05-14 onward; runs before the prompt-strip rounds (haiku & sonnet on 2026-05-12) scored 0.0. None of the pre-cutoff scores are usable now because the denominator and Gate-1 semantics both changed on 2026-05-28.

#### Per-run output inspection (current runs)
Sampled both the most-recent current runs against `reference/solution/outputs/parcels.geojson`:

| Property | Reference | run-...1129Z (gemma) | run-...1927Z (opus) |
|---|---|---|---|
| feature count | 60 | 60 | 60 |
| CRS | EPSG:4326 | EPSG:4326 | EPSG:4326 |
| geometry types | {Polygon} | {Polygon} | {Polygon} |
| columns | KATASTRALGEMEINDE_NAME … FLAECHE_M2 | identical | identical |

The score.json under each current run shows all 2 gates + all 12 subchecks passing, including the new `crs_is_canonical` and `crs_in_meaningful_set`. The 1.0 scores are corroborated by direct output inspection.

CRS/format consistency (Step 2c-CRS): the reference output (EPSG:4326), `expected_outputs[].crs` (EPSG:4326), the README's stated output CRS (EPSG:4326), and the instruction (WGS84 / EPSG:4326) all agree. The grader's CRS handling under `grade_crs_soft` reprojects the submission to canonical EPSG:4326 if needed and then does per-id centroid comparison in the common 4326 space for both sides — symmetric, not a one-sided paper-over. Consistent; no finding.

#### Verdict
**calibrated**

Six current runs from three agent families (claude-code opus, openrouter gemma-4-26b, openrouter deepseek-v4-pro) all score 1.0 on the new 12-subcheck grader, well over the `insufficient-evidence` bar. The `too-easy` verdict needs *both* all-current-runs ≥0.95 *and* an over-specifying instruction; the first holds, the second does not. The instruction was already stripped of every gift across three documented rounds (`68384e4`, `d65f3d9`, `b4583b4`); what remains names the goal (full column names + proper encoding + WGS84 GeoJSON) without naming the mechanism (truncation, CP1252, source CRS). A capable agent cleanly solving an L1 task is the intended L1≫L2≫L3 gradient. The Mojibake failure mode remains reachable (broken_mojibake_encoding=0.75) and distinguishable from the truncated-columns failure (broken_truncated_columns=0.583). The grader-change is internally consistent.

`metadata.yaml > broken_solutions` was carrying stale measured_score and expected_score_range values from the 10-subcheck era. Updated unilaterally per Step 4: truncated_columns from 0.50 → 0.5833 with range [0.45, 0.55] → [0.55, 0.65]; mojibake_encoding from 0.70 → 0.75 with range [0.65, 0.75] → [0.70, 0.80]. Updated the rationale block in `metadata.yaml > tolerances` to mention the new soft-CRS subcheck policy. No grader logic edit (the grader had already been changed in `05aabd64`); these are documentation refreshes flowing from that earlier commit. No version bump triggered: the prompt/grader/inputs/tolerance contract is unchanged this pass; the grader-change commit `05aabd64` is what would have triggered the bump, but it predates the explicit-version convention's adoption.

Added `analyst_notes` to `task.json` (was missing). This is a human-facing field and per Step 4 does not require a version bump.

#### Specific findings
- Reference re-graded at 1.0 (12/12). Broken solutions re-graded at 0.0 / 0.5833 / 0.75, all matching the refreshed `metadata.yaml` ranges. No grader drift. No action.
- Six fresh current runs (two opus, three gemma, one deepseek-v4-pro) all score 1.0 with output shape identical to the reference (60 Polygon features, EPSG:4326, full column names, diacritics intact). No action.
- All current runs scored 1.0. Expected L1 behaviour given the genuinely one-liner sub-skills and the already-minimal prompt; not a miscalibration flag because the `too-easy` over-specification conjunct is not met. No edit, no flag.
- `coverage.yaml` slugs all re-validate against `coverage-vocabulary.yaml`. Cross-checked against the inventory row: matches on category, difficulty, region, data source, formats, CRS, geometry, scale, and quality issues. No vocabulary gap.
- `task.json` does not carry an explicit `version` field; per Step 4 versioning rules it is implicitly v1. The 2026-05-28 grader-change `05aabd64` would have triggered a bump but predates this pass; current pass changes only `metadata.yaml > broken_solutions` (measured/range refresh, allowed without bump per Step 4) and `task.json > analyst_notes` (explicitly excluded from bumps). No version bump applied this pass.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions.truncated_columns.measured_score` (0.50 → 0.5833) and `expected_score_range` ([0.45, 0.55] → [0.55, 0.65]); refreshed `broken_solutions.mojibake_encoding.measured_score` (0.70 → 0.75) and `expected_score_range` ([0.65, 0.75] → [0.70, 0.80]); added soft-CRS policy note to `tolerances.rationale`. Reason: absorb the 10→12 subcheck denominator change from grader-commit `05aabd64`.
- `task.json`: added `analyst_notes` (description + 4-step approach + 5 pitfalls). Reason: field was missing; refreshes the human-facing UI block to match the current grader and prompt. Re-grade on reference: 1.0.

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.0 (12/12)
- grader on broken_wrong_format: 0.0 (within [0.0, 0.0])
- grader on broken_truncated_columns: 0.5833 (within [0.55, 0.65])
- grader on broken_mojibake_encoding: 0.75 (within [0.70, 0.80])
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
- Geometry-type uniformity (Polygon/MultiPolygon only) migrated to a
  new `geometry_type_polygonal` subcheck.
- Row-count exact-match migrated to a new `row_count_exact` subcheck.
- Subcheck total grew from 12 to 14.

### Verification
- Reference solution re-graded: 1.0 (14/14 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

Two new commits have touched `benchmark/tasks/fio-l1-vienna-shapefile-recovery/` since the prior evaluator commit (`68c1734`, 2026-06-06T16:34Z, the 5th-pass `calibrated` re-confirmation). Both are repo-wide grader refactors, already partially documented in the "Manual cleanup 2026-06-06" block above:

1. `363aed2` (2026-06-06T20:11Z) "Drop Gate 2 from graders; one hard gate, rest are subchecks" - grader-change. Removed `Gate("structural_correctness", ...)` and its early return; geometry-type uniformity and exact row count migrated to subchecks `geometry_type_polygonal` and `row_count_exact`. Subcheck count 12 -> 14. Rationale stated in commit message: the second gate was inconsistent across the 36 graders (34 effectively hard, 2 soft) and shape-recoverable misses should cost points, not collapse the score.
2. `c749e57` (2026-06-07T18:32:38Z) "Weight data-content subchecks 3x across all categories" - grader-change. Added `weight=3.0` to `row_count_exact`, `katastralgemeinde_values_match`, `eigentuemer_values_match`, `flaeche_values_match`, and `geometry_reprojected_per_id`; schema/structural checks stay at weight 1. Score is now sum(weight passed)/sum(weight); this task's denominator is 24 weighted points across 14 subchecks. Rationale stated in commit message: data-content subchecks tagged 3x across fio/geo/spa/dc.

The earlier design history (initial authoring `6ab70b2` -> three prompt-strip rounds `68384e4`/`d65f3d9`/`b4583b4` -> `is_wgs84` consolidation `f0c244a` -> layout reorg `29a9ae3` -> soft-CRS `05aabd64`) stands as reconstructed in the five prior blocks.

#### Change log (appended)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change | Dropped Gate 2; geometry-type + row-count moved to subchecks (12 -> 14) | Commit msg: single hard gate policy; recoverable shape misses cost a point instead of zeroing the score |
| 2026-06-07 | c749e57 | grader-change | weight=3.0 on the five data-content subchecks (denominator now 24 weighted) | Commit msg: data-content subchecks weighted 3x across all categories |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38Z (commit `c749e57`, class: grader-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic (deepseek/deepseek-v4-flash) | 2026-06-09T10:51:07Z | 1.0 | done | current (suite sha `ec540aa` contains `c749e57`; task_version 1 == pre-pass version) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed (deepseek/deepseek-v4-flash) | 2026-06-08T10:39:00Z | 1.0 | done | current (suite sha `6510297` contains `c749e57`; task_version 1) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T14:59:53Z | 1.0 | done | stale (pre-weighting); re-graded under current grader: 1.0 |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T18:33:50Z | 1.0 | done | stale (pre-cutoff); re-graded under current grader: 1.0 |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:02:08Z | 1.0 | done | stale (pre-cutoff); re-graded under current grader: 1.0 |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | None | cancelled | no usable score |

Stale-run footnote: the full pre-2026-06-06 history (40+ runs, 8+ adapters) was reviewed across the five prior evaluator-review blocks; every successful run since the 2026-05-17 prompt strip scored 1.0. Because both new commits are pure grader-side changes (the prompt and inputs are untouched since 2026-05-17), the stale gemma outputs remain valid agent behaviour and were re-graded under the current weighted grader - all three score 1.0, restoring cross-family evidence (google/gemma + deepseek) on the current grader.

#### Per-run output inspection (current runs)
Both current runs wrote `outputs/parcels.geojson` (plus fetched sidecars and a `solve.py`). Direct comparison against `reference/solution/outputs/parcels.geojson`: 60 rows vs 60, CRS EPSG:4326, geometry types {Polygon}, column list identical (KATASTRALGEMEINDE_NAME, GRUNDSTUECKSNUMMER, EIGENTUEMER_NAME, WIDMUNG_BEZEICHNUNG, STRASSE_NAME, FLAECHE_M2, geometry). Re-graded both under the current grader: 1.0, no failed subchecks.

CRS/format consistency (2c-CRS): reference output (EPSG:4326), `expected_outputs[]` (geojson / EPSG:4326 / Polygon), and the README output table (EPSG:4326) all agree. `grade_crs_soft` reprojects a non-canonical submission to canonical before the spatial subchecks - declared accept-list policy, not a paper-over. Consistent.

#### Verdict
**calibrated**

Two current runs (deepseek-v4-flash, basic + detailed prompt variants) score 1.0 on the weighted 14-subcheck grader, and the three freshest gemma outputs re-graded under the current grader also score 1.0, so the cross-family evidence carries over (the weighting change provably cannot alter an all-pass score). The `too-easy` verdict still requires an over-specifying instruction; after this pass's edits the instruction is thinner than ever (the output-CRS mention is gone too), so that conjunct fails. The broken-solution spread remains resolvable: wrong_format 0.0, mojibake 0.7083, truncated_columns 0.7917, correct 1.0. One deliberate consequence of the 3x data-content weighting is that the two graded failure classes swapped order (truncated-names ~0.79 now scores above mojibake ~0.71, where it used to be 0.58 vs 0.75); this matches the stated policy that preserved data content outweighs schema cosmetics, and the two classes remain distinguishable from each other and from 1.0/0.0, so it is recorded as intentional, not flagged.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `parcels.geojson`, GeoJSON | instruction | stated |
| output CRS EPSG:4326 | GeoJSON pins WGS84 per RFC 7946 (mention stripped this pass) | inferable |
| full column names restored, aliases absent | instruction ("correct full column names") + `column_map.csv` content | stated |
| diacritics decoded (CP1252 via .cpg) | instruction ("proper character encoding"); mechanism discoverable from `parcels.cpg` | inferable |
| per-id value/geometry preservation | conversion task, no mutation requested; standard contract | inferable |
| exact row count | same (no filtering asked) | inferable |
| geometry Polygon/MultiPolygon | instruction | stated |
| reprojection from EPSG:31287 | discoverable from `parcels.prj` + format-pinned output CRS | inferable |

Factual claims verified: `parcels.shp` + `.shx`/`.dbf`/`.prj`/`.cpg` and `column_map.csv` exist under `inputs/`; the cpg says `CP1252`; the prj resolves to EPSG:31287; the shapefile has 60 rows with exactly the five truncated aliases plus `FLAECHE_M2`; `column_map.csv` maps each alias to the full name the grader expects. No missing or inaccurate claim.

#### Reference faithfulness
`reference/solution/generate.py` reads the shapefile (cpg-respecting), applies the column map, reprojects to EPSG:4326, and writes `parcels.geojson` - exactly the instruction. It additionally sorts rows by GRUNDSTUECKSNUMMER and fixes the column order; these are documented determinism measures for byte-stable regeneration, the instruction does not constrain row or column order, and the grader is per-id and order-insensitive, so they sit inside the prompt-compliant output space rather than deviating from it. Faithful; no flag.

#### Specific findings
- `metadata.yaml > broken_solutions` carried stale numbers from the unweighted 12-subcheck era (truncated 0.5833 in [0.55, 0.65]; mojibake 0.75 in [0.70, 0.80]). Re-measured under the weighted grader: truncated 0.7917, mojibake 0.7083. Refreshed measured_score, expected_score_range, and the description arithmetic (precedent: the 5th pass did the same refresh after the soft-CRS change). Applied.
- The instruction contained an em-dash and stated the output CRS twice ("WGS84 GeoJSON", "in EPSG:4326") although `expected_outputs[]` writes `.geojson`, which pins WGS84 by RFC 7946. Per the mechanical GeoJSON-CRS strip rule and house-style rules, rewrote the instruction in full sentences with actual filenames (`parcels.shp`, `column_map.csv`), no em-dash, no CRS mention. Persona framing ("our web viewer") and all factual constraints preserved. `version` bumped 1 -> 2. Applied; reference re-grades 1.0.
- `analyst_notes` refreshed: fixed the broken pitfall parenthetical ("Waehring instead of Waehring"), corrected the soft-CRS pitfall (a declared-31287 submission is reprojected and only loses `crs_is_canonical`; the centroid check catches mislabelled coordinates, not declared ones), used the real diacritic names (Währing, Müller), and noted the prompt now also omits the output CRS. Applied (no bump needed, but covered by this pass's bump anyway).
- README carried stale `data/` paths and pre-refactor grader structure (Gate-2 row count, Gate-1 CRS rejection) plus old scores (0.500/0.700). Updated to the single-gate + weighted-subcheck reality and the new measured scores. Docs-change; applied.
- `coverage.yaml` slugs re-validated against `coverage-vocabulary.yaml` (format-io; l1; shapefile+csv in; geojson out; wgs84+conformal; bundled-local; shapefile-column-truncation + encoding-issues; polygon; vienna; small) and against the inventory row. Unchanged except the timestamp. No vocabulary gap.
- Note for the next pass: the version bump to 2 makes all runs listed above stale evidence for the v2 prompt; fresh runs are needed before the next verdict can rely on run data.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: instruction rewritten to house style (full sentences, real filenames, no em-dash) with the redundant GeoJSON CRS mentions stripped; `version` 1 -> 2; `analyst_notes` refreshed. Re-grade on reference: 1.0. Reason: mechanical GeoJSON-CRS strip + house-style rules; notes had a typo and a soft-CRS inaccuracy.
- `metadata.yaml`: broken-solution measured scores/ranges/descriptions refreshed for the weighted grader (truncated 0.5833 -> 0.7917 in [0.75, 0.85]; mojibake 0.75 -> 0.7083 in [0.65, 0.75]); tolerances rationale updated (Gate 2 -> weighted subcheck; ordering-flip note). Reason: absorb grader commits `363aed2` + `c749e57`.
- `README.md`: failure-mode and score documentation updated to the single-gate weighted grader; `data/` -> `inputs/` paths. Reason: stale docs.
- `coverage.yaml`: evaluator_run_at refreshed; tags unchanged.

#### Proposed but not applied (see HUMAN-REVIEW items)
(none)

#### Tests run
- grader on reference: 1.0 (14/14 subchecks, 24/24 weighted)
- grader on broken_wrong_format: 0.0 (within [0.0, 0.0])
- grader on broken_truncated_columns: 0.7917 (within [0.75, 0.85])
- grader on broken_mojibake_encoding: 0.7083 (within [0.65, 0.75])
- pytest: pass (41/41)

---

## Evaluator review 2026-06-14 — weight recalibration  (evaluator-commit <pending>)

**Change in one line:** RECALIBRATED. Raised `diacritics_decoded` from
weight 1 to weight 3 so the encoding skill's most direct detector
carries data-content weight; the central data-corruption failure
(mojibake) now drops the score meaningfully more than the cosmetic
schema slip (truncated columns). Grading-only; no version bump.

### Rationale

This is a FORMAT-I/O (shapefile recovery) task. Its central skill is
recovering the shapefile's *data content* through the conversion:
correct CP1252 decoding (diacritics + per-id text values), correct
reprojection geometry, correct numeric areas, and the full row set.
The schema side (restoring full column names from `column_map.csv`)
and the CRS-label / geometry-type checks are cosmetic/structural: a
"kept the truncated dBase names but otherwise correct" submission
preserves every value and is trivially fixable downstream.

The blunt repo-wide `c749e57` weighting put weight 3 on the four
value/geometry checks and `row_count_exact`, but left
`diacritics_decoded` at 1 alongside the five cosmetic
`column_renamed_*` checks. `diacritics_decoded` is the most direct
detector of the encoding skill — the task's stated principal
weak-agent failure mode (mojibake). Leaving it at weight 1 understated
the severity of data corruption: under the old weights the
data-corruption failure (mojibake, 0.708) sat only 0.083 below the
cosmetic schema slip (truncated, 0.792). Bumping `diacritics_decoded`
to 3 (it is a data-content check) widens that gap to 0.154 and makes
the "central mistake = meaningful drop; cosmetic slip = light drop"
principle explicit, while keeping the already-correct severity
ordering (data corruption below cosmetic slip) intact.

### Weight change

| Subcheck | Old | New | Class |
|---|---|---|---|
| `diacritics_decoded` | 1.0 | 3.0 | data-content (encoding skill) |

All other weights unchanged: `row_count_exact`,
`katastralgemeinde_values_match`, `eigentuemer_values_match`,
`flaeche_values_match`, `geometry_reprojected_per_id` stay at 3
(central data-content); the five `column_renamed_*`,
`geometry_type_polygonal`, `crs_is_canonical`, `crs_in_meaningful_set`
stay at 1 (cosmetic/structural). Weighted denominator 24 → 26.

### Broken scores before → after

| Class | Before | After | Severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | hard gate — output not GeoJSON; unrecoverable |
| mojibake_encoding | 0.7083 | 0.6538 | central data corruption (encoding); every name garbled — should drop hardest of the recoverable misses |
| truncated_columns | 0.7917 | 0.8077 | cosmetic schema slip; values/geometry/encoding intact — should drop least |
| reference | 1.0 | 1.0 | all-pass; weight-invariant |

**Ordering:** 0.0 < 0.654 (data corruption) < 0.808 (cosmetic) < 1.0 —
monotone by severity and defensible. No disjoint-failure inversion: the
two recoverable classes fail disjoint subcheck groups (mojibake fails
the 3 weight-3 encoding/value checks; truncated fails the 5 weight-1
cosmetic checks), so up-weighting the encoding detector widens rather
than inverts the gap.

### Prior-run re-grade summary

Re-graded all 41 run outputs found under
`runs/*/fio-l1-vienna-shapefile-recovery/outputs/`. Every passing run
(all current-version runs, including the two v2 `current` runs
run-20260608-074701Z and run-20260609-084636Z, plus all post-05-14
gemma/opus/deepseek runs) stays at 1.0 — an all-pass score is
weight-invariant, so the weight edit cannot move them. Two stale
2026-05-12 runs shifted (run-20260512-0833Z 0.0→0.2308,
run-20260512-2259Z 0.0→1.0), but those shifts are attributable to the
cumulative grader evolution (soft-CRS Gate-1 change, no longer
hard-failing CRS=None), not to this weight edit; they are pre-prompt-
cutoff stale evidence and not used for the verdict. No current run
shifted.

### Threshold note

No thresholds or check logic changed. One observation flagged, not
acted on: the per-id text/numeric/geometry subchecks use a ≥ 0.99
pass threshold and are pass/fail (not graded-fractional), so a partial
corruption that affects, say, half the rows scores identically to a
total corruption. That is a binary-subcheck design choice, not a
weight issue, and is out of scope for this grading-only pass.

### Tests run
- grader on reference: 1.0 (14/14 subchecks, 26/26 weighted)
- grader on broken_wrong_format: 0.0 (within [0.0, 0.0])
- grader on broken_truncated_columns: 0.8077 (within [0.78, 0.84])
- grader on broken_mojibake_encoding: 0.6538 (within [0.60, 0.70])
- pytest: not-run (orchestrator runs the suite)
