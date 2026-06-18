# Implementation notes — spa-l2-cairo-shop-knn

## Status
completed

## Summary
L2 spatial-analysis task: per-anchor 5-NN + within-1 km filter + 5×3
distance matrix to closest sibling anchors over a bundled Cairo
shops + anchors GPKG (EPSG:22992) with synthetic chain-transliteration
variants. Output is JSON; grader scores 1.0 on the reference and
0.0 / 0.83 / 0.5 on three distinct broken classes.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.0 (expected range [0.0, 0.0])
  - no_chain_normalisation: 0.833 (expected range [0.78, 0.88])
  - wrong_knn_set: 0.5 (expected range [0.45, 0.55])
- Second-run output match: bit-identical
- Library tests after task: pass (32/32)

## Failure-mode coverage
- Wrong output format: broken_wrong_format
- No chain canonicalisation: broken_no_chain_normalisation
- Wrong knn set / distances: broken_wrong_knn_set
- Distance reported in wrong unit (km/ft): principled-reasoning
  (subcheck 2 — `knn_distances_agree_with_coords` recomputes
  distance from coords, so any unit mismatch trips it)
- Constant within_1km flag: principled-reasoning (subcheck 3)
- Cross-chain over-collapse: not-handled (grader checks per-chain
  distinct-count = 1 but does not enforce across-chain distinctness)
- Dropped / duplicated anchors: principled-reasoning (Gate 2)

## Open issues
- [severity: low] Inventory says `OSM tags: shop=*` but the bundled
  data is sourced from Overture `places.place` with synthetic chain
  names overwritten on top of the real geometry. The shop semantics
  (chain-name normalisation) are realised through the synthetic
  variant injection in `data/_prepare_input.py`. AUTHOR_CONTEXT.md
  guidance permits this fallback so long as it's recorded; the
  category-filter route would have been brittle (Overture's retail
  categorisation in Cairo is sparse and inconsistent).
- [severity: low] The 100 anchors are placed on a synthetic 10×10
  grid rather than sampled from a real "client target market" data
  source. Overture-derived candidate anchors collocated with shop
  POIs would have made the 5-NN ranking ambiguous (dozens of POIs
  per coordinate). The grid is documented in
  `data/_prepare_input.py` and `metadata.yaml > notes`.

## Suggested prompt changes


## Inventory change proposals


## Library extensions


## Runtime
~6 minutes (mostly Overture S3 fetch + reference JSON serialisation).

---

# Evaluator review log

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task originated as the sole `spatial_analysis` L2 entry in `authoring/inventory.md` exercising k-nearest neighbours (k=5) with a within-distance flag and a small distance matrix, plus an attribute-cleaning step (chain-name canonicalisation across Arabic / Latin / casing variants) — Cairo region, bundled GPKG in EPSG:22992, JSON output. The original instruction (commit `4d45517`) explicitly named the EPSG, the layer feature counts, the transliteration scripts, and the full output schema as a separate block.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 4d45517 | initial-authoring | Created task: inputs (10k shops + 100-anchor grid GPKG, EPSG:22992), grader (2 gates + 6 subchecks), reference + 3 brokens, README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | mixed (path-only rename) | Moved task into `benchmark/eval/tasks/...` subtree | Commit msg: "split into authoring/ and eval/ subtrees" |
| 2026-05-13 | 89150101 | docs-change | Added image-prompt.md | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | a3a8d53 | mixed (path-only rename) | Moved `benchmark/eval/tasks/` to `benchmark/tasks/` | Commit msg: "Tasks are not eval-specific" |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: "generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated card image (FLUX schnell) | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated card image (nano-banana-2) | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-13 | 9b1fb11 | prompt-change | Merged the explicit `Output schema (exact keys):` bullet block into running prose; no requirement changes | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped `EPSG:22992`, layer feature counts (`(~10k)`, `(100 target-markets)`), and the explicit transliteration-script enumeration `(Latin / Arabic / casing)` from the instruction | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 7f31f98 | prompt-change | Softened phrasing further: dropped the "collapse to one canonical name per chain before serialising" directive and replaced with a results-oriented statement about consistent names; reworded "metric distance" to "distance in metres" | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (path-only rename + grader path updates) | Reorganised folder layout (`data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, image moved to `assets/`); grader path constants updated accordingly. Answer key, instruction, broken outputs unchanged | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit `7f31f98`, class: `prompt-change`).
- The 2026-05-26 folder reorg only moves files and rewires grader paths; it does not change the answer key, the prompt text, the brokens, or any tolerance, so prior runs that target the old paths would still be valid for the *task design* — but they were spawned against the old harness layout. I conservatively treat only post-2026-05-17T12:49Z runs as `current`.

#### Runs considered
| Run | Adapter (model) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | `claude-opus-4-6` | 2026-05-17T14:13:22Z | 1.0 | done | current |
| run-20260517-1424Z | `deepseek/deepseek-v4-flash` | 2026-05-17T18:57:25Z | 1.0 | done | current |
| run-20260526-0748Z | `google/gemma-4-26b-a4b-it` | 2026-05-26T09:14:58Z | 0.833 | done | current |

(24 earlier runs exist but were started before the 2026-05-17 cutoff and are therefore stale. They are listed in `find /home/nhp/project/benchmark/eval/runs -name spa-l2-cairo-shop-knn` and were considered only for sanity-checking that the current grader behaviour matches.)

#### Verdict
**calibrated**

Three current runs span Claude (Opus 4.6, score 1.0), an OpenRouter Anthropic-class model (DeepSeek v4 flash, 1.0), and a smaller open-weight model (Gemma-4-26b-a4b, 0.833). The score spread is the textbook one designed in by the author: capable agents do the full pipeline (knn + within-flag + matrix + chain canonicalisation) and score 1.0; the weaker agent emits the per-row `raw_name` verbatim (including Arabic-script variants like "كارفور" alongside "Carrefour", and mixed-case variants like "metro" / "Metro Market" / "Metro Markets" / "Seoudi" / "seoudi supermarket" / "Seoudi Market") so its `chain_variants_collapsed` subcheck reports `0/8 chains collapsed` while `per-shop_id consistency 480/480` passes — the precise expected weak-agent failure mode the README documents as mode #2. All five other subchecks (anchor name populated, knn-distances-from-coords, within_1km flag, knn-distance-vector-matches-reference, distance-matrix-consistent-with-coords) pass for every current run, indicating the geometric core of the task is well-specified and the L2 partial-credit structure is doing its job.

The reference grader re-run scores 1.0 (6/6 subchecks); `uv run pytest` passes 35/35. Broken-solution `measured_score` values in `metadata.yaml` (0.0 / 0.833 / 0.5) match the documented expected ranges and match the live grader behaviour on the gemma run for the no-chain-normalisation pattern.

#### Specific findings
- Prompt-stripping history (commits 1bc112e and 7f31f98) is principled and well-aimed: the EPSG hint, feature counts, and the explicit Latin-vs-Arabic enumeration were all model-deducible from the GPKG (CRS metadata, layer rowcounts, attribute inspection) and the post-strip instruction still lets the strong models reach 1.0 — no over-stripping.
- The 0.833 gemma score lands inside the `no_chain_normalisation` expected range `[0.78, 0.88]` and is achieved by the exact mechanism the grader was designed to penalise. This is positive evidence of grader calibration, not a flag.
- `task.json > tags.quality_issues` includes `"non_latin_script"`, which is not on the thesis data-quality axis (the Cairo region row already covers Arabic script). Internal tag, no vocabulary impact for `coverage.yaml`; I record the data-quality axis value as `inconsistent-attribute-values` only.
- Author-block "Open issues" flag the Overture-`places.place`-as-shop-fallback and the synthetic 10×10 anchor grid. Both are documented design choices recorded under `metadata.yaml > notes` per AUTHOR_CONTEXT guidance; they are not actionable evaluator issues, just provenance notes for the human auditor.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (6/6 subchecks)
- pytest: pass (35/35)

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the sole `spatial_analysis` L2 entry in `authoring/inventory.md` exercising k-nearest neighbours (k=5) plus a within-distance flag (1 km) and a small 5×3 distance matrix to each anchor's three closest sibling anchors, layered with an attribute-cleaning step (chain-name canonicalisation across Arabic / Latin / casing transliterations) — Cairo region, bundled two-layer GPKG in EPSG:22992 (Egypt Red Belt), JSON output. The first commit (`4d45517`, 2026-05-08) created the inputs (10 000 shop points + a synthetic 10×10 / 100-anchor grid), a grader with 2 gates + 6 subchecks, the reference solution, 3 broken solutions, the README, and the implementation notes. The original instruction explicitly named the EPSG code, the per-layer feature counts, the transliteration scripts, and the output schema as a separate block.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 4d45517 | initial-authoring | Created task: inputs (10k shops + 100-anchor grid GPKG, EPSG:22992), grader (2 gates + 6 subchecks), reference + 3 brokens, README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | mixed (path-only rename) | Moved task into `benchmark/eval/tasks/...` subtree | Commit msg: "split into authoring/ and eval/ subtrees" |
| 2026-05-13 | 89150101 | docs-change | Added image-prompt.md | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | a3a8d53 | mixed (path-only rename) | Moved `benchmark/eval/tasks/` to `benchmark/tasks/` | Commit msg: "Tasks are not eval-specific" |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: "generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated card image (FLUX schnell) | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated card image (nano-banana-2) | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-13 | 9b1fb11 | prompt-change | Merged the explicit `Output schema (exact keys):` bullet block into running prose; no requirement changes | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped `EPSG:22992`, layer feature counts (`(~10k)`, `(100 target-markets)`), and the explicit transliteration-script enumeration `(Latin / Arabic / casing)` from the instruction; verified against the diff | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 7f31f98 | prompt-change | Softened phrasing: dropped the "collapse to one canonical name per chain before serialising" directive, replaced with a results-oriented statement about consistent names; "metric distance" reworded to "distance in metres"; verified against the diff | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (path-only rename + grader path updates) | Reorganised folder layout (`data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, image to `assets/`); grader path constants updated. Answer key, instruction, brokens unchanged | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | ad79b9c | docs-change (prior evaluator) | First evaluator review: verdict calibrated, no edits, 0 flags; wrote `coverage.yaml`, `status.json`, appended evaluator block | Commit msg: "Re-evaluate spa-l2-cairo-shop-knn: calibrated, no edits, 0 flags" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit `7f31f98`, class: `prompt-change`).
- Commits after the cutoff (`29a9ae3` folder reorg + grader-path rewire, `ad79b9c` prior-evaluator docs/coverage) do not change the answer key, instruction text, brokens, or any tolerance, so the cutoff is unchanged from the prior review.

#### Runs considered
| Run | Adapter (model) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | `claude-opus-4-6` | 2026-05-17T14:13:22Z | 1.0 | done | current |
| run-20260517-1424Z | `deepseek/deepseek-v4-flash` | 2026-05-17T18:57:25Z | 1.0 | done | current |
| run-20260526-0748Z | `google/gemma-4-26b-a4b-it` | 2026-05-26T09:14:58Z | 0.833 | done | current |

(24 earlier runs are pre-cutoff and therefore stale; they were sanity-checked only — the stale set is 11× claude-opus-4-6 / claude-sonnet-4-6 at 1.0, 3× deepseek-v4-flash at 1.0, 1× tencent/hy3-preview at 0.0, plus several failed/cancelled openrouter runs with `started_at` < 2026-05-17T12:49Z. Enumerated via `find benchmark/eval/runs -name spa-l2-cairo-shop-knn`.)

#### Verdict
**calibrated**

The three `current` runs span three distinct model families of varying capability — Claude Opus 4.6 (1.0), DeepSeek V4 Flash via OpenRouter (1.0), and a small open-weight model, Gemma-4-26b-a4b (0.833). All three emit structurally valid output (100 records, correct top-level keys, `knn` length 5, 5×3 matrix, anchor-id set identical to the reference). The two 1.0 runs pass all six subchecks including `chain_variants_collapsed` (8/8 chains, per-shop consistency 480/480). The 0.833 gemma run fails *only* `chain_variants_collapsed` (`0/8 chains collapsed; per-shop_id consistency 480/480`) while passing the five geometric/structural subchecks (`distances_agree_with_coords` 500/500, `within_1km_flag` 500/500, `distance_vector_matches_reference` 500/500, `distance_matrix_consistent_with_coords` 1500/1500) — i.e. it computed knn / within-flag / matrix correctly but never canonicalised the chain transliterations, the precise weak-agent failure mode the README documents (mode #2) and the broken set `no_chain_normalisation` models. This is the textbook partial-credit spread the L2 design intends. The reference re-grades to 1.0 (6/6); the three brokens re-grade to 0.0 / 0.833 / 0.5, matching `metadata.yaml > broken_solutions.measured_score` exactly; `uv run pytest` passes 35/35.

#### Specific findings
- The JSON output is non-spatial; there is no output-CRS contract to verify (Step 2c-CRS). The grader recomputes all distances from the bundled EPSG:22992 GPKG coords (`grade.py:171-178`, `:218-219`), so submission and reference distances are derived from the same metric CRS — no one-sided reprojection. No CRS/format inconsistency between README, `expected_outputs[]`, and reference.
- Prompt-stripping history (`1bc112e`, `7f31f98`) is principled: the EPSG hint, feature counts, and Latin-vs-Arabic enumeration were all model-deducible from the GPKG (CRS metadata, rowcounts, attribute inspection), and after the strip the strong models still reach 1.0 — no over-stripping, no gift remaining to remove.
- `task.json > tags.quality_issues` includes the internal tag `"non_latin_script"`, which has no thesis data-quality axis slug (Arabic script is already covered by the Cairo region row). This is an internal task tag, not a coverage-vocabulary gap; `coverage.yaml > data_quality_issues` records only `inconsistent-attribute-values`.
- Author-block "Open issues" (Overture `places.place` geometry reused as a shop layer with synthetic names overwritten; synthetic 10×10 anchor grid) are documented design choices under `metadata.yaml > notes` per AUTHOR_CONTEXT guidance — provenance notes, not actionable evaluator issues. The inventory's `OSM tags: shop=*` is realised through the synthetic chain-variant injection rather than a real category filter; recorded, not flagged.
- EPSG:22992 (Egypt 1907 / Red Belt) is a Transverse Mercator projection — confirmed conformal via pyproj — so `crs_variants: [conformal]` is correct.

### 3. Changes applied this run

#### Unilateral edits
- (none) — the task is calibrated; no gift to strip, no tolerance to loosen, no subcheck to tighten.

#### Proposed but not applied (HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (6/6 subchecks)
- brokens re-graded: wrong_format 0.0, no_chain_normalisation 0.833, wrong_knn_set 0.5 (all match metadata.yaml)
- pytest: pass (35/35)

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the sole `spatial_analysis` L2 entry in `authoring/inventory.md` exercising k-nearest neighbours (k=5) plus a within-distance flag (1 km) and a small 5×3 distance matrix to each anchor's three closest sibling anchors, layered with an attribute-cleaning step (chain-name canonicalisation across Arabic / Latin / casing transliterations) — Cairo region, bundled two-layer GPKG in EPSG:22992 (Egypt Red Belt), JSON output. The first commit (`4d45517`, 2026-05-08) created the inputs (10 000 shop points + a synthetic 10×10 / 100-anchor grid), a grader with 2 gates + 6 subchecks, the reference solution, 3 broken solutions, the README, and the implementation notes. The original instruction explicitly named the EPSG code, the per-layer feature counts, the transliteration scripts, and the output schema as a separate block.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 4d45517 | initial-authoring | Created task: inputs (10k shops + 100-anchor grid GPKG, EPSG:22992), grader (2 gates + 6 subchecks), reference + 3 brokens, README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | mixed (path-only rename) | Moved task into `benchmark/eval/tasks/...` subtree | Commit msg: "split into authoring/ and eval/ subtrees" |
| 2026-05-13 | 89150101 | docs-change | Added image-prompt.md | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | a3a8d53 | mixed (path-only rename) | Moved `benchmark/eval/tasks/` to `benchmark/tasks/` | Commit msg: "Tasks are not eval-specific" |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: "generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated card image (FLUX schnell) | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated card image (nano-banana-2) | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-13 | 9b1fb11 | prompt-change | Merged the explicit `Output schema (exact keys):` bullet block into running prose; no requirement changes | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped `EPSG:22992`, layer feature counts (`(~10k)`, `(100 target-markets)`), and the explicit transliteration-script enumeration `(Latin / Arabic / casing)` from the instruction | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 7f31f98 | prompt-change | Softened phrasing: dropped the "collapse to one canonical name per chain before serialising" directive, replaced with a results-oriented statement about consistent names; "metric distance" reworded to "distance in metres" | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (path-only rename + grader path updates) | Reorganised folder layout (`data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, image to `assets/`); grader path constants updated. Answer key, instruction, brokens unchanged | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | ad79b9c | docs-change (prior evaluator) | First evaluator review: verdict calibrated, no edits, 0 flags; wrote `coverage.yaml`, `status.json`, appended evaluator block | Commit msg: "Re-evaluate spa-l2-cairo-shop-knn: calibrated, no edits, 0 flags" |
| 2026-05-27 | e625a48 | docs-change (prior evaluator) | Second evaluator review: verdict calibrated, no edits, 0 flags; refreshed `coverage.yaml`, `status.json`, appended evaluator block | Commit msg: "Re-evaluate spa-l2-cairo-shop-knn: calibrated, no edits, 0 flags" |
| 2026-05-28 | 622342b | mixed (metadata + task.json `prompt_version` removal across all tasks, plus harness-wide versioning support) | Removed the stale `prompt_version` field from `task.json.tags` (actually from `task.json` root) and `metadata.yaml` for this task; added no `version` field yet (task is implicitly v1). No change to instruction, grader logic, tolerances, inputs, brokens, or reference | Commit msg: "Add task content versioning; drop unused prompt_version" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit `7f31f98`, class: `prompt-change`).
- Commits after the cutoff (`29a9ae3` folder reorg + grader-path rewire, `ad79b9c` / `e625a48` prior-evaluator docs/coverage, `622342b` harness-wide `prompt_version` removal) do not change the answer key, instruction text, brokens, or any tolerance; the cutoff is unchanged from the prior reviews.

#### Runs considered
| Run | Adapter (model) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | `claude-opus-4-6` | 2026-05-17T14:13:22Z | 1.0 | done | current |
| run-20260517-1424Z | `deepseek/deepseek-v4-flash` | 2026-05-17T18:57:25Z | 1.0 | done | current |
| run-20260526-0748Z | `google/gemma-4-26b-a4b-it` | 2026-05-26T09:14:58Z | 0.833 | done | current |
| run-20260527-2016Z | `claude-opus-4-7` | 2026-05-27T23:04:52Z | 1.0 | done | current |
| run-20260527-2321Z | `google/gemma-4-26b-a4b-it` | 2026-05-28T01:01:15Z | 0.833 | done | current |
| run-20260528-0113Z | `claude-opus-4-7` | 2026-05-28T03:07:52Z | 1.0 | done | current |
| run-20260528-0317Z | `google/gemma-4-26b-a4b-it` | 2026-05-28T04:13:16Z | 0.833 | done | current |

(24 earlier runs are pre-cutoff and stale; previously enumerated. Newest sweeps add four additional `current` runs since the last evaluator pass: two Claude Opus 4.7 runs at 1.0 and two more Gemma-4-26b-a4b-it runs at 0.833.)

#### Verdict
**calibrated**

The `current` runs now span four model families/generations (Claude Opus 4.6, Claude Opus 4.7, DeepSeek V4 Flash, Gemma-4-26b-a4b-it) and reinforce the spread the prior reviewers documented. All Opus runs and the DeepSeek run score 1.0 by passing every subcheck including `chain_variants_collapsed` (8/8 chains, 480/480 per-shop consistency). Every Gemma-4-26b-a4b-it run lands at exactly 0.833 = 5/6, failing only `chain_variants_collapsed` (`0/8 chains collapsed; per-shop_id consistency 480/480`) — i.e. it executes the knn / within-flag / matrix correctly but does not canonicalise transliteration variants, the exact weak-agent failure mode the README documents (mode #2) and the broken set `no_chain_normalisation` models. Two independent Gemma runs producing identical 0.833 scores is positive evidence that the grader is deterministic on a stable failure profile, not borderline. The reference re-grades to 1.0 (6/6); `uv run pytest` passes 41/41 (test count grew because the geo_grading library added the `check_and_normalize_crs` test suite — unrelated to this task).

#### Specific findings
- The JSON output is non-spatial; there is no output-CRS contract to verify (Step 2c-CRS). The grader recomputes all distances from the bundled EPSG:22992 GPKG coords, so submission and reference distances are derived from the same metric CRS — no one-sided reprojection. No CRS/format inconsistency between README, `expected_outputs[]`, and reference.
- Instruction review for redundant statements (Step 4 unilateral rule): the persona paragraph and schema paragraph each mention "metres" once but in different roles — persona names the *unit requirement* ("distance in metres"), schema pins the *field type* (`distance_m (finite numeric, in metres)`). Not a duplicate canonical statement; both pull weight. No EPSG/CRS mention to strip (output is JSON, not GeoJSON). Output filename, identity-key (`shop_id`), and geometry type (n/a; JSON output) each appear once. Nothing to tighten.
- `622342b` (harness-wide versioning change) is mechanical and design-neutral for this task: removed the `prompt_version` field from `task.json` and `metadata.yaml` and did not add `version`. The task is implicitly v1 per the new convention. This evaluator pass makes no unilateral edits, so no version bump is required.
- The four new `current` runs do not change the verdict; they only add evidence weight. The prior reviewers' findings about Overture `places.place` as geometry source with synthetic names, the synthetic 10×10 anchor grid, the internal `non_latin_script` tag (no thesis slug), and the EPSG:22992 conformal classification all still hold and need no re-statement here.

### 3. Changes applied this run

#### Unilateral edits
- (none) — task is calibrated; no gift to strip, no redundancy to tighten, no tolerance to loosen, no subcheck to tighten. No `task.json.version` bump is required because no unilateral edit was made.

#### Proposed but not applied (HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (6/6 subchecks)
- pytest: pass (41/41)

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the sole `spatial_analysis` L2 entry in `authoring/inventory.md` exercising k-nearest neighbours (k=5) plus a within-distance flag (1 km) and a small 5×3 distance matrix to each anchor's three closest sibling anchors, layered with an attribute-cleaning step (chain-name canonicalisation across Arabic / Latin / casing transliterations). Cairo region, bundled two-layer GPKG in EPSG:22992 (Egypt Red Belt), JSON output. First commit (`4d45517`, 2026-05-08) created the inputs (10 000 shop points + a synthetic 10×10 / 100-anchor grid), a grader with 2 gates + 6 subchecks, the reference solution, 3 broken solutions, the README, and the implementation notes.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 4d45517 | initial-authoring | Created task: inputs (10k shops + 100-anchor grid GPKG, EPSG:22992), grader (2 gates + 6 subchecks), reference + 3 brokens, README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | mixed (path-only rename) | Moved task into `benchmark/eval/tasks/...` subtree | Commit msg: "split into authoring/ and eval/ subtrees" |
| 2026-05-13 | 89150101 | docs-change | Added image-prompt.md | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | a3a8d53 | mixed (path-only rename) | Moved `benchmark/eval/tasks/` to `benchmark/tasks/` | Commit msg: "Tasks are not eval-specific" |
| 2026-05-13 | 1b8dda1 | docs-change | Added image.webp | Commit msg: "generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated card image (FLUX schnell) | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated card image (nano-banana-2) | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-13 | 9b1fb11 | prompt-change | Merged the explicit `Output schema (exact keys):` bullet block into running prose; no requirement changes | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped `EPSG:22992`, layer feature counts, and the explicit transliteration-script enumeration from the instruction | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 7f31f98 | prompt-change | Softened phrasing: dropped the "collapse to one canonical name per chain before serialising" directive, replaced with a results-oriented statement; "metric distance" reworded to "distance in metres" | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (path-only rename + grader path updates) | Reorganised folder layout (`data/` → `inputs/`, `reference/outputs/` → `reference/solution/outputs/`, `tests/` → `reference/failures/`, image to `assets/`); grader path constants updated. Answer key, instruction, brokens unchanged | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | ad79b9c | docs-change (prior evaluator) | First evaluator review: calibrated, 0 edits, 0 flags; wrote `coverage.yaml`, `status.json` | Commit msg: "Re-evaluate spa-l2-cairo-shop-knn: calibrated, no edits, 0 flags" |
| 2026-05-27 | e625a48 | docs-change (prior evaluator) | Second evaluator review: calibrated, 0 edits, 0 flags; refreshed `coverage.yaml`, `status.json` | Commit msg: "Re-evaluate spa-l2-cairo-shop-knn: calibrated, no edits, 0 flags" |
| 2026-05-28 | 622342b | mixed (harness-wide) | Removed stale `prompt_version` from `task.json` and `metadata.yaml`; no `version` added (implicitly v1). No design change for this task | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 841ae57 | docs-change (prior evaluator) | Third evaluator review: calibrated, 0 edits, 0 flags; refreshed `coverage.yaml`, `status.json` | Commit msg: "Re-evaluate spa-l2-cairo-shop-knn: calibrated, no edits, 0 flags" |

No commits have touched `benchmark/tasks/spa-l2-cairo-shop-knn/` since 2026-05-28 (verified with `git log --since=2026-05-28 -- benchmark/tasks/spa-l2-cairo-shop-knn/`).

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:49:06Z (commit `7f31f98`, class: `prompt-change`).
- Commits after the cutoff (`29a9ae3` folder reorg, `ad79b9c` / `e625a48` / `841ae57` prior-evaluator artefacts, `622342b` harness-wide `prompt_version` removal) do not change the answer key, instruction text, brokens, or any tolerance; the cutoff is unchanged.

#### Runs considered
| Run | Adapter (model) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | `claude-opus-4-6` | 2026-05-17T14:13:22Z | 1.0 | done | current |
| run-20260517-1424Z | `deepseek/deepseek-v4-flash` | 2026-05-17T18:57:25Z | 1.0 | done | current |
| run-20260526-0748Z | `google/gemma-4-26b-a4b-it` | 2026-05-26T09:14:58Z | 0.833 | done | current |
| run-20260527-2016Z | `claude-opus-4-7` | 2026-05-27T23:04:52Z | 1.0 | done | current |
| run-20260527-2321Z | `google/gemma-4-26b-a4b-it` | 2026-05-28T01:01:15Z | 0.833 | done | current |
| run-20260528-0113Z | `claude-opus-4-7` | 2026-05-28T03:07:52Z | 1.0 | done | current |
| run-20260528-0317Z | `google/gemma-4-26b-a4b-it` | 2026-05-28T04:13:16Z | 0.833 | done | current |
| run-20260528-1624Z | `google/gemma-4-26b-a4b-it` | 2026-05-28T17:55:57Z | 0.833 | done | current |
| run-20260528-1927Z | `claude-opus-4-7` | 2026-05-28T22:09:44Z | 1.0 | done | current |
| run-20260528-2225Z | `google/gemma-4-26b-a4b-it` | 2026-05-28T23:23:06Z | 0.667 | done | current |
| run-20260528-2332Z | `claude-opus-4-7` | 2026-05-29T00:50:41Z | 1.0 | done | current |
| run-20260529-0109Z | `google/gemma-4-26b-a4b-it` | 2026-05-29T07:10:30Z | 0.667 | done | current |
| run-20260529-0902Z | `deepseek/deepseek-v4-pro` | 2026-05-31T18:08:24Z | 1.0 | done | current |
| run-20260606-0953Z | `google/gemma-4-26b-a4b-it` | 2026-06-06T10:32:54Z | — | failed (model-side stall) | current |
| run-20260606-1129Z | `google/gemma-4-26b-a4b-it` | 2026-06-06T12:53:10Z | 0.0 | done (no output file written) | current |
| run-20260606-1334Z | (cancelled before agent ran) | 2026-06-06T13:56:29Z | — | cancelled | current |

(Stale pre-cutoff runs enumerated in prior evaluator blocks; not relisted here.)

#### Verdict
**calibrated**

The `current` window now covers four model families (Claude Opus 4.6, Claude Opus 4.7, DeepSeek V4 Flash/Pro, Gemma-4-26b-a4b-it) across 13 successfully-graded runs. All Opus and DeepSeek runs score 1.0 by passing every subcheck. Gemma-4-26b-a4b-it lands at 0.833 four times (failing only `chain_variants_collapsed` — the documented weak-agent failure mode #2) and at 0.667 twice (failing both `chain_variants_collapsed` and `distance_matrix_consistent_with_coords`). The two 0.667 Gemma runs filled the entire 5×3 matrix with zeros (verified by reading `outputs/market_neighbourhoods.json` of run-20260528-2225Z), which is a model-side execution bug rather than a task issue. The two 2026-06-06 Gemma runs are pure model-side failures: one stalled out before the agent finished, and the other completed without writing any output file (only the input GPKG present in `outputs/`). Per the evaluator-prompt rule, those do not count as evidence of mis-calibration. The reference re-grades to 1.0 (6/6); brokens re-grade to 0.0 / 0.833 / 0.5 matching `metadata.yaml > broken_solutions.measured_score`; `uv run pytest` passes 41/41.

#### Specific findings
- The JSON output is non-spatial; there is no output-CRS contract to verify (Step 2c-CRS). The grader recomputes all distances from the bundled EPSG:22992 GPKG coords, so submission and reference distances are derived from the same metric CRS, with no one-sided reprojection. No CRS or format inconsistency between README, `expected_outputs[]`, and reference.
- The instruction has no GeoJSON/EPSG/WGS84 reference to strip (output is JSON, not GeoJSON), and the persona-vs-schema redundancy check from Step 4 finds no duplicated canonical statement worth stripping (persona names the unit requirement, schema pins the field type; both pull weight). Output filename, identity key (`shop_id`), and geometry type each appear once. Nothing to tighten.
- `task.json.analyst_notes` was missing. Authored in this pass per Step 4's "Author or refresh `analyst_notes`" rule. The new field describes what the task tests (three chained primitives plus the hidden Arabic/Latin/casing transliteration gotcha), lays out a six-step approach in plain prose, and lists seven pitfalls covering the canonicalisation trap first, then unit mistakes, wrong-CRS distances, matrix transposition / zero-fill, over-collapse across chains, and wrong output format. `analyst_notes` is human-facing only and does not require a `task.json.version` bump.
- No prior commit's rationale was unclear; the design-history table inherits prior reviewers' analysis and adds the 2026-05-28 evaluator-artefact commit.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: added `analyst_notes` (description / approach / pitfalls). Re-grade on reference: 1.0. Reason: the field was missing and Step 4 permits authoring it unilaterally; it is human-facing only, so no `version` bump.

#### Proposed but not applied (HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (6/6 subchecks)
- brokens re-graded: wrong_format 0.0, no_chain_normalisation 0.833, wrong_knn_set 0.5 (all match metadata.yaml)
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
- Anchor-id Jaccard ≥0.95 migrated to a new `anchor_id_set_jaccard` subcheck.
- Record-count ±5% migrated to a new `record_count_within_5pct` subcheck.
- Subchecks now total 8 (was 6).

### Verification
- Reference solution re-graded: 1.0 (8/8 subchecks).

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task is the sole `spatial_analysis` L2 entry in `authoring/inventory.md` exercising k-nearest neighbours (k=5) plus a within-distance flag (1 km) and a small 5x3 distance matrix to each anchor's three closest sibling anchors, layered with an attribute-cleaning step (chain-name canonicalisation across Arabic / Latin / casing transliterations). Cairo region, bundled two-layer GPKG in EPSG:22992 (Egypt Red Belt), JSON output. First commit (`4d45517`, 2026-05-08) created the inputs (10 000 shop points + a synthetic 10x10 / 100-anchor grid), the grader, the reference solution, 3 broken solutions, the README, and the implementation notes.

#### Change log
The table below carries forward the prior reviewers' entries (verified against `git log --follow`) and adds the commits since the 2026-06-06 review.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 4d45517 | initial-authoring | Created task: inputs (10k shops + 100-anchor grid GPKG, EPSG:22992), grader (2 gates + 6 subchecks), reference + 3 brokens, README, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | mixed (path-only rename) | Moved task into `benchmark/eval/tasks/...` subtree | Commit msg: "split into authoring/ and eval/ subtrees" |
| 2026-05-13 | 89150101 / a3a8d53 / 1b8dda1 / 3c65373 / cfbdc7c | docs-change + path renames | Card image assets added/regenerated; tasks dir moved to `benchmark/tasks/` | Commit msgs (benchmark-wide housekeeping) |
| 2026-05-13 | 9b1fb11 | prompt-change | Merged the explicit output-schema bullet block into running prose; no requirement changes | Commit msg: "Merge output schema blocks into prose for 7 task instructions" |
| 2026-05-14 | 1bc112e | prompt-change | Stripped `EPSG:22992`, layer feature counts, and the transliteration-script enumeration from the instruction | Commit msg: "Strip deducible information from SPA task instructions" |
| 2026-05-17 | 7f31f98 | prompt-change | Dropped the "collapse to one canonical name per chain" directive in favour of a results-oriented statement; "metric distance" reworded to "distance in metres" | Commit msg: "Remove nudges from 6 spatial-analysis task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (path-only rename + grader path updates) | Folder layout reorg (`data/` -> `inputs/` etc.); grader path constants updated; answer key unchanged | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | ad79b9c | docs-change (prior evaluator) | First evaluator review: calibrated, 0 edits, 0 flags | Commit msg |
| 2026-05-27 | e625a48 | docs-change (prior evaluator) | Second evaluator review: calibrated, 0 edits, 0 flags | Commit msg |
| 2026-05-28 | 622342b | mixed (harness-wide) | Removed stale `prompt_version` field; task implicitly v1 | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 841ae57 | docs-change (prior evaluator) | Third evaluator review: calibrated, 0 edits, 0 flags | Commit msg |
| 2026-06-06 | 8d27b1d | docs-change (prior evaluator) | Fourth evaluator review: calibrated; authored `analyst_notes` in task.json (human-facing only, no version bump) | Commit msg |
| 2026-06-06 | 363aed2 | grader-change | Dropped `Gate("structural_correctness")`; anchor-id Jaccard and record-count migrated to subchecks `anchor_id_set_jaccard` / `record_count_within_5pct`; subchecks now total 8 | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" (benchmark-wide; the old gate was inconsistent across graders) |
| 2026-06-07 | c749e57 | grader-change | Tagged the 7 data-content subchecks `weight=3.0` (schema/structural `anchor_name_normalised_populated` stays 1.0); score is now weight-summed: total weight 22 | Commit msg: "Weight data-content subchecks 3x across all categories" (benchmark-wide reweighting) |

Neither 363aed2 nor c749e57 bumped `task.json > version` (the task stayed implicitly v1 through them), so the version check alone cannot separate pre/post-reweighting runs; the timestamp cutoff below does.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38Z (commit `c749e57`, class: grader-change).
- Both grader-change commits alter only scoring arithmetic (gate-to-subcheck migration, then 3x weighting), not any subcheck's pass/fail logic, the answer key, the instruction, or the inputs. Pre-cutoff runs are stale for *score* comparison but their per-subcheck pass/fail profiles remain deterministic evidence and map 1:1 onto new scores (1.0 stays 1.0; old gemma 5/6 = 0.833 maps to 19/22 = 0.864; old gemma 4/6 = 0.667 maps to 16/22 = 0.727).

#### Runs considered
| Run | Adapter (model) | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | `deepseek/deepseek-v4-flash` (basic prompt) | 2026-06-09T07:36:47Z | 1.0 | done | current (suite 6510297 contains c749e57; task_version 1 == current-at-run) |
| run-20260609-084636Z | `deepseek/deepseek-v4-flash` (basic prompt) | 2026-06-09T12:35:16Z | 1.0 | done | current (suite ec540aa contains c749e57) |
| run-20260607-112430Z | `google/gemma-4-26b-a4b-it` | 2026-06-07T16:52:44Z | 0.0 | done | stale (pre-cutoff by 100 min; model wrote no parseable output - model-side) |
| run-20260606-* / earlier | various | pre-cutoff | - | - | stale (enumerated in prior evaluator blocks: 11+ Opus/Sonnet and DeepSeek runs at 1.0, gemma at 0.833/0.667/0.0, plus model-side stalls/cancels) |

#### Verdict
**insufficient-evidence**

Only two runs post-date the 2026-06-07 reweighting cutoff and both come from one agent family (DeepSeek V4 Flash, both 1.0 with all 8 subchecks passing; outputs verified: 100 records, correct keys, knn length 5, 5x3 matrix, distances matching the reference to mm). By the letter of the rules that is one family, hence insufficient-evidence for the *current* scoring arithmetic. There is however no sign of mis-calibration: the reweighting changes no pass/fail logic, the deterministic remapping of the rich pre-cutoff evidence (four model families, scores 1.0 / 0.864 / 0.727 / 0.0 under the new arithmetic) preserves exactly the partial-credit spread the task was designed for, the reference re-grades to 1.0 (8/8), and the three brokens land at 0.0 / 0.8636 / 0.5909, consistent with their failure classes. No grader or tolerance action is warranted; the verdict will resolve itself as the post-reweighting sweep accumulates non-DeepSeek runs.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `market_neighbourhoods.json`, top-level JSON array | instruction, schema paragraph | stated |
| record keys incl. knn sub-keys and types | instruction, schema paragraph | stated |
| exactly 5 knn entries sorted ascending by `distance_m` | instruction | stated |
| 5x3 matrix, rows = knn order, cols = siblings distance-ascending | instruction | stated |
| distances in metres (grader recomputes from EPSG:22992 coords, 1.0 m tol) | instruction states metres; metric CRS readable from the GPKG | stated / inferable |
| `within_1km` == (`distance_m` <= 1000) | instruction ("true when `distance_m` is at most 1000") | stated |
| one canonical `normalised_name` per chain, >= 7/8 chains | instruction states consistency requirement; the variant spellings are discoverable in the data | stated / inferable |
| per-shop_id name consistency | instruction ("the same `shop_id` always carries the same `normalised_name`") | stated |
| `anchor_name_normalised` non-empty | instruction ("non-empty string", "Tidy the anchor names too") | stated |
| anchor-id set Jaccard >= 0.95 / count +-5% | one record per anchor; anchors enumerable from the GPKG | inferable |

Factual claims verified against the data: `cairo_retail` GPKG exists with exactly the two named layers (`shops`: 10 000 Points, columns `shop_id`/`raw_name`; `anchors`: 100 Points, columns `anchor_id`/`anchor_name`; both EPSG:22992); chain spellings are indeed inconsistent (8 chains x 4 variants per `reference/_chain_truth.json`). No missing constraints, no inaccurate claims.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads both layers, normalises anchor names (strip/collapse-whitespace/casefold), collapses the 8 known chain variant sets to one canonical lowercase label each (non-chain rows get a deterministic casefold fallback), computes Euclidean 5-NN in the native metric CRS with deterministic tie-breaking, derives the within-1 km flag from the metric distance, builds the 5x3 matrix to the 3 closest siblings, and serialises exactly the schema the instruction pins. Rounding distances to 3 decimals (mm) is a determinism measure well inside the 1.0 m grading tolerance, not an unrequested transformation. No skipped steps, no extra operations, no CRS concern (the bundled data is already metric and the output is non-spatial JSON). Faithful.

#### Specific findings
- The 2026-06-07 3x reweighting left `metadata.yaml > broken_solutions` stale: measured scores are now 0.0 / 0.8636 / 0.5909 (weights 22-total) versus the recorded 0.0 / 0.8333 / 0.5, and `wrong_knn_set`'s old range [0.45, 0.55] no longer bracketed its deterministic score. Refreshed measured_score per the unilateral rule and mechanically re-centred the two ranges and description arithmetic on the new weight-summed values (documentation only; no scoring behaviour touched).
- README staleness from the same two benchmark-wide refactors: failure mode 7 still described "Gate 2" and the "structural correctness gate" (both removed in 363aed2), the broken scores read 0.83 / 0.5, and the input path still said `data/cairo_retail.gpkg` from the pre-reorg layout. Fixed unilaterally (docs-change).
- `grade.py`'s inline section comments and the docstring's robustness notes still used the old 6-subcheck numbering after the Gate-2 migration ("Subcheck 3/4/5/6" for what are now subchecks 5/6/7/8). Renumbered, comment-only; no logic touched.
- House style: the instruction opened with a sentence fragment ("Retail-density readout for a downtown Cairo brief.") and contained two em-dashes, both banned by house style. Rewrote minimally: full-sentence opener ("I'm putting together a retail-density readout..."), em-dashes replaced with a comma, a colon clause, and a semicolon, "Write" softened to "Please write". Every factual constraint, filename, key name, threshold, and deliberate omission (no CRS mention, no EPSG, no script enumeration) is preserved verbatim. This is an instruction change, so `version` was bumped 1 -> 2.
- `analyst_notes` (authored 2026-06-06) still matches the task exactly, including the Gate-1 wrong-format pitfall; no refresh needed beyond the unchanged content.
- Coverage tags re-validated against `authoring/coverage-vocabulary.yaml`; all slugs present, content unchanged from the prior block, `evaluator_run_at` refreshed.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style rewrite of the instruction (fragment opener fixed, 2 em-dashes removed; content-preserving) and `version` added/bumped to 2. Re-grade on reference: 1.0. Reason: house-style rules ban em-dashes and fragment openers; the bump is mandated by the instruction change.
- `grade.py`: comment-only renumbering of stale subcheck references left over from the Gate-2 migration. Re-grade on reference: 1.0. Reason: internal documentation consistency; no logic change.
- `metadata.yaml`: `broken_solutions` measured_score refreshed to the reweighted grader's deterministic outputs (0.0 / 0.8636 / 0.5909) with ranges and description arithmetic re-centred accordingly. Reason: stale after benchmark-wide c749e57 reweighting; documentation only.
- `README.md`: fixed stale `data/` input path, stale broken scores (0.83 -> 0.86, 0.5 -> 0.59), and the failure-mode-7 description of the removed Gate 2. Reason: stale README fix (docs-change).

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (8/8 subchecks, weighted)
- brokens re-graded: wrong_format 0.0, no_chain_normalisation 0.8636, wrong_knn_set 0.5909 (recorded in metadata.yaml)
- pytest: pass (41/41)

## Evaluator review 2026-06-14 — subcheck weight recalibration  (evaluator-commit <pending>)

### Statement of change
**RECALIBRATED.** Replaced the benchmark-wide blunt flat `weight=3.0`
on all seven data-content subchecks (commit `c749e57`) with weights
reasoned from what this kNN task actually tests. The central skill is
correct k-nearest-neighbour assignment in the projected metric CRS
(EPSG:22992) with accurate metre distances; the two subchecks that
detect its failure are now weighted highest, the secondary distance
matrix primitive moderate, structural/derived/cosmetic checks low, and
the chain-canonicalisation attribute side-quest below the spatial core.

### Why the prior flat weighting was miscalibrated
Under flat `3.0` the central kNN distance check carried exactly the
same per-subcheck weight as the chain-canonicalisation side-quest and
the mechanical structural checks. The broad broken ordering happened to
come out right only because `wrong_knn_set` trips three subchecks while
`no_chain_normalisation` trips one — an artefact of failure cardinality,
not of severity weighting. A meaningful spatial mistake and a cosmetic
attribute slip were treated as equally severe per check.

### Weight changes
| Subcheck | Role | Old | New |
|---|---|---|---|
| `anchor_name_normalised_populated` | cosmetic (non-empty string) | 1.0 | 1.0 |
| `anchor_id_set_jaccard` | structural (right anchors present) | 3.0 | 2.0 |
| `record_count_within_5pct` | structural (right count) | 3.0 | 1.0 |
| `knn_distances_agree_with_coords` | **central kNN / distance accuracy** | 3.0 | **5.0** |
| `within_1km_flag_correct` | derived flag (trivial once distances right) | 3.0 | 1.0 |
| `knn_distance_vector_matches_reference` | **central kNN (found the true 5 nearest)** | 3.0 | **5.0** |
| `distance_matrix_consistent_with_coords` | secondary spatial primitive | 3.0 | 3.0 |
| `chain_variants_collapsed` | attribute-cleaning side-quest | 3.0 | 2.0 |

Total weight 22 -> 20.

### Broken scores before -> after
| Broken class | Before | After | Severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | gate failure (no JSON) — unchanged |
| no_chain_normalisation | 0.8636 | 0.90 | only the attribute side-quest missed; spatial core perfect -> light drop |
| wrong_knn_set | 0.5909 | 0.35 | entire spatial kNN core wrong (distances + vector + matrix) -> heavy drop |

Ordering: monotone and defensible. wrong_knn_set (0.35, central skill
failed) << wrong_knn-style matrix+chain partial (0.75, see prior runs)
< no_chain_normalisation (0.90, cosmetic side-quest miss) < reference
(1.0). The two central subchecks (4, 6) co-fail in the wrong-CRS/wrong-
unit case the broken models, and the matrix (7) co-fails because it is
built from the wrong kNN shops — a correlated, realistic failure cluster,
not a disjoint-failure trap. A hypothetical matrix-only miss scores
17/20 = 0.85, sitting just below the chain-only miss and far above a
total spatial failure — sensible.

### Prior-run re-grade summary
| Run | Model | old (flat 3x) | new |
|---|---|---|---|
| run-20260608-074701Z | deepseek-v4-flash | 1.0 | 1.0 |
| run-20260609-084636Z | deepseek-v4-flash | 1.0 | 1.0 |
| run-20260526-0748Z | gemma-4-26b-a4b-it | 0.8636 | 0.90 |
| run-20260528-2225Z | gemma-4-26b-a4b-it | 0.7273 | 0.75 |
| run-20260529-0109Z | gemma-4-26b-a4b-it | 0.7273 | 0.75 |
| run-20260607-112430Z | gemma (no output) | 0.0 | 0.0 |
| run-20260606-1129Z | gemma (no output) | 0.0 | 0.0 |

The two post-cutoff `current` DeepSeek runs (prior verdict
insufficient-evidence) pass all subchecks and are unchanged at 1.0. The
gemma partial-credit runs shift in the intended direction: the pure
chain-collapse miss rises (side-quest, light penalty) and the
chain+matrix run lands between the two brokens. No score inversion.

### Reasoning
This is a kNN task; the analytic payload is the per-anchor 5-nearest
assignment and accurate metric distances. An agent that nails the full
spatial pipeline but echoes raw chain names is far more useful than one
that canonicalises chains but reports garbage distances — the weights
now reflect that. The within_1km flag and record-count checks are
mechanical/derived and weighted at the cosmetic floor (1.0); the
anchor-id Jaccard guards against dropped anchors and keeps a small
structural weight (2.0); the distance matrix is a genuine secondary
spatial computation and keeps 3.0.

### Changes applied this run
#### Unilateral edits
- `grade.py`: subcheck `weight=` values only (table above). No check
  logic, threshold, or gate touched. Re-grade on reference: 1.0.
- `metadata.yaml`: `broken_solutions` measured_score + expected_score_range
  refreshed (no_chain 0.90 / [0.86,0.94]; wrong_knn 0.35 / [0.31,0.39])
  and the weight-arithmetic prose updated.
- `README.md`: stale broken score fractions (0.86 -> 0.90, 0.59 -> 0.35)
  and the failure-mode-7 weight note (weight 3 each -> 1 / 2).

#### Proposed but not applied (HUMAN-REVIEW items)
- (none; status.json human_review_items stays empty)

#### Notes (no change made)
- Thresholds and gate logic untouched; no threshold appeared miscalibrated.

#### Tests run
- grader on reference: 1.0 (8/8 subchecks, weighted)
- brokens re-graded: wrong_format 0.0, no_chain_normalisation 0.90, wrong_knn_set 0.35
- pytest: not run (orchestrator runs the suite)
