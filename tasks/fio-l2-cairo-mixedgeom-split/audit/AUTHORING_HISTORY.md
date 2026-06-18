# Implementation notes — fio-l2-cairo-mixedgeom-split

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L2 format-I/O task: a hand-crafted mixed-geometry GeoJSON of 50
features across 10 Cairo heritage sites → multi-layer GPKG
(`points` / `lines` / `polygons`) in EPSG:22992 with multi-part
polygons exploded into singletons and `site_id` preserved as a
foreign key on every layer. Reference, grader, and three broken
solutions built and verified inside the project Docker container.

## Verification results
- Reference grader score: 1.000 (9 / 9 subchecks pass).
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1
    rejects (output is the original mixed GeoJSON, not a GPKG with
    the three expected layers).
  - geom_corruption: 0.667 (expected range [0.55, 0.72]) — three
    geometry subchecks fail (`polygons_geometry_iou`,
    `points_geometry_per_site`, `lines_geometry_per_site`) after
    x/y axis swap; structural and attribute subchecks all pass.
  - no_explode: 0.778 (expected range [0.72, 0.85]) — two
    subchecks fail (`polygons_singletons_only` and
    `polygons_count_within_tolerance`); MultiPolygons left
    unexploded in the polygons layer drop the count from 15 to 10.
- Second-run output match: bit-identical (verified with `diff -q`
  on `reference/outputs/heritage.gpkg` before / after a second
  `reference/generate.py` run inside Docker; the script normalises
  `gpkg_contents.last_change` and VACUUMs the SQLite container so
  the GPKG byte-stream is stable across runs).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Output not converted (still GeoJSON / not GPKG): broken_wrong_format
- Stratification missing (single layer): principled — Gate 1
  layer-name check
- MultiPolygons left unexploded: broken_no_explode
- Wrong CRS / no reprojection: principled — Gate 1 per-layer CRS
  check
- x/y axis-swapped reprojection: broken_geom_corruption
- site_id column dropped: principled — Gate 1 column check
- Whole geometry kind dropped (e.g. no points layer): principled —
  Gate 1 layer-name check + per-layer count subchecks
- feature_kind column lost: tolerated when geometry stays correct;
  the per-site subchecks fall back to site_id-only keying.

## Open issues
(none)

## Suggested prompt changes
(none)

## Inventory change proposals
(none — the inventory row's "Bundled local file" data source and
hand-crafted-mixed-geometry semantics matched cleanly. Used as
written.)

## Library extensions
(none — the grader uses `Gate`, `Subcheck`, `ScoreReport`,
`count_within_tolerance`, `iou_with_tolerance`, and
`jaccard_similarity_set`. The per-layer Hausdorff and per-point
distance loops are inline because they need per-feature keying that
no existing primitive provides.)

## Runtime
~10 minutes (no live fetches; all work runs inside the project
Docker container).

---

## Evaluator review 2026-05-26  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
The original spec (inventory row + first commit `e75b41c` + the README/IMPLEMENTATION_NOTES as initially landed) frames a Format-I/O L2 task: take a hand-curated mixed-geometry GeoJSON of 50 features across 10 Cairo heritage sites (a heritage analyst persona, Yusra Al-Sayed of Egypt's Ministry of Antiquities) and produce `heritage.gpkg` with three typed layers (`points`/`lines`/`polygons`), MultiPolygons exploded into singletons, every feature in EPSG:22992 (Egypt Red Belt), and `site_id` carried through as a cross-layer foreign key. The skill under test is composing four format operations — stratify by geometry type, explode multi-parts, reproject, write multi-layer GPKG — without losing the part-to-site link. Three broken solutions (`wrong_format`, `geom_corruption`, `no_explode`) plus principled gates (layer-name, per-layer CRS, `site_id` column presence) cover the full failure-mode list. Grader is 2 gates + 9 subchecks with ±5 % per-layer / ±10 % summed-count tolerance, 1 m geometry epsilon, and 0.9 IoU/Jaccard thresholds.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e75b41c | initial-authoring | Initial task landed: grader, reference GPKG, three broken solutions, hand-crafted 50-feature mixed-geom GeoJSON, README, IMPLEMENTATION_NOTES. | (initial) |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/`. Path-only relocation. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` (task-card image prompt). | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` task-card image. | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task-card image via FLUX schnell. | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task-card image via nano-banana-2 (0.5K, 3:2). | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | 68384e4 | prompt-change | Dropped the explicit "1 enclosure polygon, axial-street lines, marker points" decomposition and the "polygons are a mix of single Polygon and MultiPolygon" hint from the instruction. Kept persona, output schema, layer names, target EPSG, explode requirement. | Commit msg: "Remove input CRS mentions, geometry type descriptions, explicit column enumerations, format descriptions, and data value examples that models can discover by reading file metadata." |
| 2026-05-17 | b4583b4 | prompt-change | Replaced `EPSG:22992 (Egypt Red Belt)` with the deliberately vague "Use the region's standard metric coordinate system"; replaced "multi-part polygons exploded into singletons" with "each feature must have a single-part geometry"; dropped the trailing "Layers: points / lines / polygons in EPSG:22992, GPKG" reformulation in favour of "Layers: points / lines / polygons, GPKG". | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + structural) | Task-directory layout migration: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/generate.py + outputs/` → `reference/solution/`, `tests/` → `reference/failures/`, image assets → `assets/`. `task.json.inputs[0].url` updated to the new `inputs/` path. No change to instruction, expected outputs, tolerances, reference data, or broken solutions. | Commit msg: "Reorganize task folder layout" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37Z (commit b4583b4, class: prompt-change). The 2026-05-26 reorganize is structural (input URL rewrite only) and does not invalidate prior runs of the post-strip prompt.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:34:33Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:53:34Z | 0.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:42:06Z | 0.0 | done | current |
| run-20260517-0614Z and earlier (24 runs) | various | up to 2026-05-17T08:41Z | mixed | done/failed/cancelled | stale (pre-cutoff) |

#### Verdict
**calibrated**

Three current runs span the full 0.0–1.0 score range across three different model families. The capable model (Opus) reads the persona+input context, infers Egypt Red Belt (EPSG:22992) from "Cairo + Egypt heritage analyst" and produces the correct output (9/9 subchecks). Both 0.0 scores come from picking EPSG:32636 (UTM 36N — the international fallback for Cairo) instead of EPSG:22992; the grader rejects at Gate 1's per-layer CRS check. The post-`b4583b4` prompt deliberately removed the EPSG hint to test exactly this regional-CRS-knowledge skill, and the commit message states that intent (`"Remove CRS/operation nudges"`). The prompt still names the persona's domain ("Heritage analyst") and the input filename (`heritage_sites`), and the bundled GeoJSON has Arabic site names + Cairo bbox coordinates, which together are sufficient regional grounding for the agent to look up the national projection. The "explode" requirement is preserved by the `"each feature must have a single-part geometry"` rephrasing, which is operationally equivalent. Reference grades 1.0, broken solutions grade as documented (0.0 / 0.667 / 0.778), and per-task pytest is unaffected (35/35 pass).

#### Specific findings
- The two 0.0 runs are model-side CRS-inference failures, not task-calibration failures. The task design deliberately tests whether the agent maps "Cairo + Egypt heritage" → EPSG:22992 vs the generic UTM-36N fallback. No grader or prompt change warranted.
- Gate-1 rejection on wrong CRS is unforgiving (drops to 0.0 rather than partial credit). This is consistent with the task's "wrong CRS → desktop tool can't ingest the file" persona framing and with how other CRS tasks gate. No change.
- The `b4583b4` commit-message ("Remove CRS/operation nudges from 5 CRS task prompts") classifies this task under the CRS-strip refactor, which is consistent with the visible diff. No additional rationale needed.
- The instruction still names the output filename, layer names, and GPKG format — these are part of the contract the agent cannot infer, so they are not gifts. Keep.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (9/9 subchecks, both gates pass)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
The original spec (inventory row `fio-l2-cairo-mixedgeom-split` + first commit `e75b41c` + the README / author block of this file as they landed) frames a Format-I/O L2 task. A heritage analyst (persona Yusra Al-Sayed, Egypt Ministry of Antiquities — for the human reviewer, not spoken to the agent) supplies a single hand-crafted mixed-geometry GeoJSON of 50 features across 10 Cairo heritage sites; each site contributes an enclosure polygon (5 single Polygon, 5 MultiPolygon), one or two axial-street LineStrings, and two or three marker Points, all sharing a `site_id`. The deliverable is `heritage.gpkg` with three typed layers (`points` / `lines` / `polygons`), multi-part polygons exploded into singletons, every feature reprojected to EPSG:22992 (Egypt Red Belt), and `site_id` preserved as a cross-layer foreign key. The skill under test is composing four format operations — stratify by geometry type, explode multi-parts, reproject, write multi-layer GPKG — without losing the part-to-site link. Grader is 2 gates + 9 subchecks (±5 % per-layer / ±10 % summed-count tolerance, 1 m geometry epsilon, 0.9 IoU/Jaccard thresholds); three broken solutions (`wrong_format`, `no_explode`, `geom_corruption`) plus principled gates cover the failure-mode list.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e75b41c | initial-authoring | Initial task landed: grader, reference GPKG, three broken solutions, hand-crafted 50-feature mixed-geom GeoJSON, README, IMPLEMENTATION_NOTES. | (initial) |
| 2026-05-08 | 001e459 | docs-change | Repo split into `authoring/` and `eval/` subtrees (path relocation only). | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` (path relocation only). | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md`. | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp`. | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task-card image (FLUX schnell). | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task-card image (nano-banana-2, 0.5K, 3:2). | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | 68384e4 | prompt-change | Dropped the explicit per-site decomposition ("an enclosure polygon, a couple of axial-street lines, a few marker points") and the "polygons are a mix of single Polygon and MultiPolygon" hint from the instruction. Kept persona, output schema, layer names, EPSG:22992, and the explode requirement. | Commit msg: "Strip deducible information from FIO task instructions" |
| 2026-05-17 | b4583b4 | prompt-change | Replaced "We work in Egypt Red Belt, EPSG:22992" with "Use the region's standard metric coordinate system"; replaced "multi-part polygons exploded into singletons" with "each feature must have a single-part geometry"; dropped the trailing "in EPSG:22992" from the output-schema reformulation. | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + structural) | Task-directory layout migration: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/generate.py + outputs/` → `reference/solution/`, `tests/` → `reference/failures/`, image assets → `assets/`. `task.json.inputs[0].url` updated to the new `inputs/` path. No change to instruction text, expected outputs, tolerances, reference data, or broken solutions. | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 98fad7c | docs-change | Prior evaluator review: appended the `Evaluator review 2026-05-26` block, wrote `coverage.yaml` and `audit/status.json`. No task-behaviour edits. | Commit msg: "Re-evaluate fio-l2-cairo-mixedgeom-split: calibrated, no edits" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37Z (commit b4583b4, class: prompt-change). The 2026-05-26 reorganize (29a9ae3) only rewrote `task.json.inputs[0].url`; it does not change the answer key or instruction text, so it does not invalidate post-2026-05-17 runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:34:33Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:53:34Z | 0.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:42:06Z | 0.0 | done | current |

Stale runs (footnote — considered, pre-cutoff, not used as evidence): 24 runs started before 2026-05-17T12:48:37Z, spanning claude-code-sonnet/opus and openrouter deepseek-v4-flash / gemma4-26b / hy3-preview adapters. Scores were a mix of 1.0, 0.0, and failed/cancelled (Overpass/connection/API-key infra failures unrelated to this task). They predate the EPSG-strip prompt and are not evidence for the current task.

#### Verdict
**calibrated**

Three current runs span the full 0.0–1.0 range across three different model families. The capable model (Opus) reads the persona + bundled-input context, infers Egypt Red Belt (EPSG:22992) from "Cairo + Egypt heritage analyst", and produces a fully correct output (9/9 subchecks; `score.json` shows IoU 1.0000, site_id Jaccard 1.0000, 25/15/15 features, 0 MultiPolygons). Both 0.0 scores (deepseek-v4-flash, gemma4-26b) fail Gate 1's per-layer CRS check with the identical detail `layer 'points' CRS is 32636, expected EPSG:22992` — i.e. both picked EPSG:32636 (UTM 36N, the generic international fallback for Cairo) instead of the Egyptian national grid. The post-`b4583b4` prompt deliberately removed the EPSG hint (commit msg: "Remove CRS/operation nudges from 5 CRS task prompts") to test exactly this regional-CRS-knowledge skill; the prompt still names the persona's domain ("Heritage analyst"), the input handle (`heritage_sites`), and the bundled GeoJSON carries Arabic site names + Cairo bbox coordinates — sufficient regional grounding for an agent to look up the national projection. The explode requirement survives as "each feature must have a single-part geometry", operationally equivalent. Output-CRS consistency verified: reference outputs (all three layers EPSG:22992), `expected_outputs[].crs` (EPSG:22992), README (EPSG:22992), and the grader (gates on 22992, IoU unioned in the native CRS with no one-sided reprojection) all agree. Reference grades 1.0; brokens grade 0.0 / 0.778 / 0.667 in distinct ranges; per-task pytest 35/35.

#### Specific findings
- The two 0.0 runs are model-side CRS-inference failures (EPSG:32636 instead of EPSG:22992), not task-calibration failures. The task design intentionally tests whether the agent maps "Cairo + Egypt heritage" → the national Egypt Red Belt grid vs the generic UTM-36N fallback. No grader or prompt change warranted.
- Gate-1 rejection on wrong CRS collapses the score to 0.0 (no partial credit). This is consistent with the persona framing ("the desktop tool only ingests typed GPKG layers ... in Egypt Red Belt") — a file in the wrong CRS is unusable — and with how peer CRS tasks gate. No change.
- The instruction still names the output filename, layer names, and GPKG format. These are part of the design contract the agent cannot infer; they are not gifts. Keep.
- coverage.yaml validates fully against `authoring/coverage-vocabulary.yaml`; cross-axis check (`bundled-local` ⇒ L1/L2) is consistent with `difficulty_levels: [l2]`. No vocabulary gap.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (9/9 subchecks, both gates pass)
- broken solutions: wrong_format 0.0, no_explode 0.778, geom_corruption 0.667 (all match documented `measured_score`, distinct ranges)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
The original spec (inventory row `fio-l2-cairo-mixedgeom-split` + first commit `e75b41c` + the README / author block of this file as they first landed) frames a Format-I/O L2 task. A heritage analyst (persona Yusra Al-Sayed, Egypt Ministry of Antiquities — author-facing, not spoken to the agent) supplies a single hand-crafted mixed-geometry GeoJSON of 50 features across 10 Cairo heritage sites; each site contributes an enclosure polygon (5 single Polygon, 5 MultiPolygon), one or two axial-street LineStrings, and two or three marker Points, all sharing a `site_id`. The deliverable is `heritage.gpkg` with three typed layers (`points` / `lines` / `polygons`), multi-part polygons exploded into singletons, every feature reprojected to EPSG:22992 (Egypt Red Belt), and `site_id` preserved as a cross-layer foreign key. The skill under test is composing four format operations — stratify by geometry type, explode multi-parts, reproject, write multi-layer GPKG — without losing the part-to-site link. Grader is 2 gates + 9 subchecks (±5 % per-layer / ±10 % summed-count tolerance, 1 m geometry epsilon, 0.9 IoU/Jaccard thresholds); three broken solutions (`wrong_format`, `no_explode`, `geom_corruption`) plus principled gates cover the failure-mode list.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e75b41c | initial-authoring | Initial task landed: grader, reference GPKG, three broken solutions, hand-crafted 50-feature mixed-geom GeoJSON, README, IMPLEMENTATION_NOTES. | (initial) |
| 2026-05-08 | 001e459 | docs-change | Repo split into `authoring/` and `eval/` subtrees (path relocation only). | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` (path relocation only). | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md`. | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp`. | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task-card image (FLUX schnell). | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task-card image (nano-banana-2). | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | 68384e4 | prompt-change | Dropped explicit per-site decomposition and the "Polygon/MultiPolygon mix" hint from the instruction. Kept persona, output schema, layer names, EPSG, explode requirement. | Commit msg: "Strip deducible information from FIO task instructions" |
| 2026-05-17 | b4583b4 | prompt-change | Replaced "EPSG:22992 (Egypt Red Belt)" with "Use the region's standard metric coordinate system"; replaced "multi-part polygons exploded into singletons" with "each feature must have a single-part geometry"; dropped trailing "in EPSG:22992" from the output-schema reformulation. | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + structural) | Task-directory layout migration; `task.json.inputs[0].url` updated to the new `inputs/` path. No change to instruction text, expected outputs, tolerances, reference data, or broken solutions. | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 98fad7c | docs-change | Prior evaluator review (2026-05-26): appended block, wrote `coverage.yaml` and `audit/status.json`. No task-behaviour edits. | Commit msg: "Re-evaluate fio-l2-cairo-mixedgeom-split: calibrated, no edits" |
| 2026-05-27 | 4ee0724 | docs-change | Prior evaluator review (2026-05-27): appended block, refreshed `coverage.yaml` / `audit/status.json`. No task-behaviour edits. | Commit msg: "Re-evaluate fio-l2-cairo-mixedgeom-split: calibrated, no edits" |
| 2026-05-28 | 622342b | docs-change | Cross-suite task versioning: introduced `task.json.version` and dropped `metadata.yaml.prompt_version`. For this task only the `prompt_version` line was removed; no behaviour change. | Commit msg: "Add task content versioning; drop unused prompt_version" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:37Z (commit b4583b4, class: prompt-change). The 2026-05-26 reorganize, the two prior evaluator reviews, and the 2026-05-28 versioning commit are docs-only with respect to this task and do not invalidate post-2026-05-17 runs.

#### Runs considered
| Run | Adapter | Started | Pre-refactor score | Post-refactor score | Status | Validity |
|---|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:34:33Z | 1.0 | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:53:34Z | 0.0 | 0.9 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:42:06Z | 0.0 | 0.9 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T21:32:58Z | 0.0 | 0.9 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:57:16Z | 0.0 | 0.9 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T02:19:02Z | 0.0 | 0.9 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:46:55Z | 0.0 | 0.0 | done | current |

Stale runs (footnote — considered, pre-cutoff): 24 runs started before 2026-05-17T12:48:37Z across claude-code-sonnet/opus and openrouter deepseek-v4-flash / gemma4-26b / hy3-preview adapters. They predate the EPSG-strip prompt and are not used as evidence.

#### Verdict
**too-strict** (pre-refactor) → **calibrated** (post-refactor)

The 2026-05-27 and 2026-05-28 sweeps re-graded the post-`b4583b4` prompt across two more Opus and two more Gemma sweeps. Every Opus run after 2026-05-17 (three of them: 2016Z, 0113Z, plus the original 1424Z deepseek result) picked EPSG:32636 (UTM 36N) rather than the Egyptian national grid EPSG:22992, and Gate-1-rejected to 0.0. Even the capable model is not reliably retrieving "Cairo + Egyptian heritage analyst" → Egypt Red Belt under the post-strip prompt's deliberately flat phrasing "Use the region's standard metric coordinate system." Three of seven current runs picked UTM 36N (Opus×2, Gemma×1), one picked Web Mercator (Gemma 2028-0317), one picked the canonical EPSG:22992 (Opus 2026-05-17-1254Z, the only current run from before the issue surfaced consistently), one is deepseek-flash with 32636, one is gemma4-26b with 32636.

UTM 36N is independently defensible for Cairo (its band 30°E–36°E is dead-on for Cairo at ~31.2°E, the standard generic-international pick for the city), so a 32636 submission ought not Gate-1-collapse to 0.0 when the prompt did not pin an EPSG. Egypt Red Belt remains the regional canonical and the answer the test should reward most. Per Step 4's CRS accept-list refactor: replaced Gate-1's hard EPSG check with `check_and_normalize_crs(layer, {22992, 32636}, 22992)` so 32636 submissions are reprojected into 22992 before any spatial subcheck runs, added an `official_crs_used` subcheck that passes only when every layer's original CRS was 22992, and replaced the instruction's "Use the region's standard metric coordinate system" with the category-level hint "Use Egypt's national grid" (no EPSG, no datum name — mirrors the spa-l2-lagos "Nigeria's national grid" and crs-l2-fiji "Fiji's national metric grid" pattern). The accept list is deliberately short: 22992 (canonical) plus 32636 (the only generic alternative with concrete prior-run evidence). 3857 / 4326 / non-Egypt projected metrics still Gate-1-fail.

Re-grade of every prior current run after the refactor: the canonical Opus 1254Z stays at 1.0; the five 32636 submissions now score 9/10 = 0.9 (Gate-1 accepts, all nine remaining subchecks pass, `official_crs_used` fails); the one 3857 submission still scores 0.0 (3857 is not on the accept-list and is not a defensible metric pick for measurement). Reference grades 1.0 (10/10). Broken solutions update: wrong_format 0.0 (unchanged), no_explode 0.8 (was 0.778, 8/10 with the new subcheck passing), geom_corruption 0.7 (was 0.667, 7/10) — both still within their documented `expected_score_range` bands ([0.72, 0.85] and [0.55, 0.72] respectively, exactly the band-bracketing the bands were sized for).

Output-CRS/format consistency: reference outputs in EPSG:22992, README states EPSG:22992, `expected_outputs[].crs: "EPSG:22992"`, grader canonical EPSG:22992 — all four agree. The two-sided reprojection (the grader reprojects accepted-but-non-canonical submissions to 22992, leaving the reference unchanged at 22992) is the Step-4-sanctioned implementation of the accept-list policy, not a one-sided paper-over of a contract mismatch.

#### Specific findings
- The accept-list refactor brings the task in line with the spa-l2-lagos (377a593) and crs-l2-fiji (0888e6f) precedents. The prompt now uses the category-level hint "Egypt's national grid" — same form as Lagos's "Nigeria's national grid" — naming the family without naming the EPSG or datum.
- A correctly-implemented UTM 36N pipeline now scores 0.9 (was 0.0). The 0.1 gap is paid for by failing the `official_crs_used` subcheck, which is the discriminator the design wants. A correct Egypt Red Belt pipeline scores 1.0.
- Broken solutions' measured scores updated in `metadata.yaml` from 0.667 → 0.7 (geom_corruption) and 0.778 → 0.8 (no_explode); both remain inside `expected_score_range`. wrong_format stays at 0.0.
- coverage.yaml is unchanged in axis content; `evaluator_run_at` refreshed. No vocabulary gap.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: bumped `version: 1 → 2`; replaced "Use the region's standard metric coordinate system." with "Use Egypt's national grid." Re-grade on reference: 1.0. Reason: Step-4 category-level hint for the canonical's family, no EPSG / datum named — mirrors the spa-l2-lagos / crs-l2-fiji precedents.
- `grade.py`: added `OFFICIAL_CRS_EPSG=22992` and `ACCEPTED_CRS_EPSGS={22992, 32636}` as module-level constants; replaced the per-layer hard `epsg != 22992` Gate-1 check with `check_and_normalize_crs(layer, ACCEPTED_CRS_EPSGS, OFFICIAL_CRS_EPSG)`, reprojecting accepted-but-non-canonical layers into 22992 before any spatial subcheck; added subcheck `official_crs_used` (passes iff every layer's original CRS was 22992); docstring updated to document the accept-list and the 10-subcheck total. Re-grade on reference: 1.0 (10/10). Reason: Step-4 CRS accept-list refactor — 32636 is independently defensible for Cairo, the canonical 22992 is rewarded by the dedicated subcheck rather than by Gate-1 monopoly.
- `metadata.yaml`: updated `broken_solutions[geom_corruption].measured_score` 0.667 → 0.7 and `broken_solutions[no_explode].measured_score` 0.778 → 0.8 with one-line rationale appended to each description. Both still within their `expected_score_range`. Reason: subcheck count changed from 9 to 10; broken outputs' regional CRS pick still passes the new `official_crs_used` subcheck.
- `README.md`: added a "non-canonical CRS" failure-mode entry (4b) documenting the accept-list and the `official_crs_used` subcheck, mirroring the fiji README's accept-list paragraph. Reason: keep the README's failure-mode list synchronised with the grader.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (10/10 subchecks, both gates pass)
- broken solutions: wrong_format 0.0, no_explode 0.8, geom_corruption 0.7 (all within `expected_score_range`)
- prior current runs re-graded with new grader: Opus 1254Z 1.0, the five 32636 runs (deepseek/gemma/Opus×2/gemma×1) all 9/10 = 0.9, the 3857 gemma run 0.0
- pytest: pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <pending>)

### 1. Design history

#### Initial design intent
The original spec (inventory row `fio-l2-cairo-mixedgeom-split` + first commit `e75b41c` + the README / author block of this file as they first landed) frames a Format-I/O L2 task. A heritage analyst (persona Yusra Al-Sayed, Egypt Ministry of Antiquities — author-facing, not spoken to the agent) supplies a single hand-crafted mixed-geometry GeoJSON of 50 features across 10 Cairo heritage sites; each site contributes an enclosure polygon (5 single Polygon, 5 MultiPolygon), one or two axial-street LineStrings, and two or three marker Points, all sharing a `site_id`. The deliverable is `heritage.gpkg` with three typed layers (`points` / `lines` / `polygons`), multi-part polygons exploded into singletons, every feature reprojected to EPSG:22992 (Egypt Red Belt), and `site_id` preserved as a cross-layer foreign key. The skill under test is composing four format operations — stratify by geometry type, explode multi-parts, reproject, write multi-layer GPKG — without losing the part-to-site link. Grader is 2 gates + 11 subchecks (post-soft-CRS refactor: ±5 % per-layer / ±10 % summed-count tolerance, 1 m geometry epsilon, 0.9 IoU/Jaccard thresholds, plus `crs_is_canonical` and `crs_in_meaningful_set`); three broken solutions (`wrong_format`, `no_explode`, `geom_corruption`) plus principled gates cover the failure-mode list.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | e75b41c | initial-authoring | Initial task landed: grader, reference GPKG, three broken solutions, hand-crafted 50-feature mixed-geom GeoJSON, README, IMPLEMENTATION_NOTES. | (initial) |
| 2026-05-08 | 001e459 | docs-change | Repo split into `authoring/` and `eval/` subtrees (path relocation only). | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/`. | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md`. | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp`. | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task-card image (FLUX schnell). | Commit msg: "regenerate all 36 task card images via fal.ai FLUX schnell" |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task-card image (nano-banana-2). | Commit msg: "regenerate task card images with nano-banana-2 (0.5K, 3:2)" |
| 2026-05-14 | 68384e4 | prompt-change | Dropped explicit per-site decomposition and the "Polygon/MultiPolygon mix" hint from the instruction. Kept persona, output schema, layer names, EPSG, explode requirement. | Commit msg: "Strip deducible information from FIO task instructions" |
| 2026-05-17 | b4583b4 | prompt-change | Replaced "EPSG:22992 (Egypt Red Belt)" with "Use the region's standard metric coordinate system"; replaced "multi-part polygons exploded into singletons" with "each feature must have a single-part geometry"; dropped trailing "in EPSG:22992". | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" |
| 2026-05-26 | 29a9ae3 | mixed (docs-change + structural) | Task-directory layout migration; `task.json.inputs[0].url` updated to the new `inputs/` path. No change to instruction text, expected outputs, tolerances, reference data, or broken solutions. | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | 98fad7c | docs-change | Prior evaluator review (2026-05-26): appended block, wrote `coverage.yaml` and `audit/status.json`. No task-behaviour edits. | Commit msg: "Re-evaluate fio-l2-cairo-mixedgeom-split: calibrated, no edits" |
| 2026-05-27 | 4ee0724 | docs-change | Prior evaluator review (2026-05-27): appended block, refreshed `coverage.yaml` / `audit/status.json`. No task-behaviour edits. | Commit msg: "Re-evaluate fio-l2-cairo-mixedgeom-split: calibrated, no edits" |
| 2026-05-28 | 622342b | docs-change | Cross-suite task versioning: introduced `task.json.version` and dropped `metadata.yaml.prompt_version`. | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 2e4e372 | mixed (prompt-change + grader-change) | Step-4 CRS accept-list refactor: introduced `OFFICIAL_CRS_EPSG`/`ACCEPTED_CRS_EPSGS`, replaced Gate-1 hard EPSG check with `check_and_normalize_crs(layer, {22992,32636}, 22992)`, added `official_crs_used` subcheck (10 subchecks total). Instruction switched from "Use the region's standard metric coordinate system" to "Use Egypt's national grid". `version` bumped 1→2. README and metadata.yaml broken_solutions descriptions/scores refreshed. | Commit msg: "Re-evaluate fio-l2-cairo-mixedgeom-split: CRS accept-list refactor (22992 canonical, 32636 accepted)" |
| 2026-05-28 | 05aabd6 | grader-change | Cross-suite soft-CRS refactor (21 graders): Gate 1 now only hard-fails on no usable CRS at all. The CRS check moves to two subchecks (`crs_is_canonical`, `crs_in_meaningful_set`). For this task `check_and_normalize_crs` → `grade_crs_soft`, `OFFICIAL_CRS_EPSG`/`ACCEPTED_CRS_EPSGS` → `CANONICAL_EPSG`/`MEANINGFUL_EPSGS`, `official_crs_used` → `crs_is_canonical`, new `crs_in_meaningful_set` subcheck added. Subcheck total 10 → 11. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T19:02:57Z (commit 05aabd6, class: grader-change). Restricts the evidence set to runs graded after the soft-CRS refactor.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:35:38Z | 0.909 | done | current (graded 2026-05-28T19:19Z, after cutoff) |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T21:33:48Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:06:29Z | 0.909 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:12:50Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T02:18:24Z | 0.909 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T12:33:57Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:08:47Z | 1.0 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T12:03:57Z | 1.0 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | n/a | cancelled | model-side (excluded) |

Stale runs (footnote, pre-cutoff): all runs prior to 2026-05-28T19:02:57Z were graded under earlier grader generations and are not used as evidence.

#### Verdict
**calibrated**

Eight current runs span 0.909–1.0 across three model families (Opus, Gemma 4 26B in both basic and detailed prompt variants, DeepSeek V4 Pro). The three 0.909 = 10/11 scores are Gemma-basic submissions that did everything right except pick UTM 36N (EPSG:32636) instead of Egypt Red Belt; the score.json detail confirms `crs_is_canonical: False (32636)` while every other subcheck passes. Under the post-soft-CRS grader this is the desired shape: the geometric work earns full credit (the grader reprojected the 32636 layers into 22992 for the spatial subchecks), the regional-CRS pick costs exactly one subcheck, and the meaningful-set check still passes since 32636 is in the accept list. The 1.0 runs (Opus, DeepSeek V4 Pro, Gemma-detailed) correctly inferred Egypt Red Belt from the "Egypt's national grid" category hint. Reference grades 1.0 (11/11); broken solutions grade 0.0 / 0.727 / 0.818 in distinct bands (wrong_format / geom_corruption / no_explode); pytest 41/41.

Output-CRS/format consistency: reference outputs all three layers in EPSG:22992, README states EPSG:22992 throughout, `expected_outputs[].crs: "EPSG:22992"`, grader's `CANONICAL_EPSG = 22992` — all four agree. Two-sided reprojection (the grader reprojects accepted-but-non-canonical submissions to 22992; the reference is already in 22992) is the soft-CRS-sanctioned implementation, not a one-sided paper-over.

The README, the metadata.yaml rationale and broken_solutions descriptions, and the metadata's `measured_score` numbers were still written for the 10-subcheck CRS-accept-list grader. The 05aabd6 commit only touched `grade.py`, leaving the surrounding docs out of sync with the new 11-subcheck shape and the renamed `crs_is_canonical` subcheck (was `official_crs_used`). The Gemma-basic submissions that score 0.909 = 10/11 used to score 0.9 = 9/10 — the doc drift is purely cosmetic, but it confuses anyone reading the failure-mode list.

#### Specific findings
- README failure-mode list: the broken_no_explode score reference (0.778) and the broken_geom_corruption score reference (0.667) reflect the pre-CRS-accept-list grader. The 0.778 value also appears in the "weak-agent failure" paragraph. Refresh both to the post-soft-CRS values (0.818 and 0.727). Mechanical, apply unilaterally.
- README failure-mode #4 (no reprojection): pre-soft-CRS this hard-failed Gate 1 with "CRS not in accept-list"; under the soft-CRS grader Gate 1 accepts any usable CRS and the submission is reprojected. Rewrite the failure-mode paragraph to describe the new behaviour (two CRS subchecks dock points, geometry credits still earned via reprojection). Apply unilaterally.
- README failure-mode #4b: rename `official_crs_used` → `crs_is_canonical`, update score from 9/10 = 0.9 to 10/11 ≈ 0.909, mention `crs_in_meaningful_set` passes. Apply unilaterally.
- metadata.yaml broken_solutions descriptions: rewrite to reflect 11 subchecks and the two CRS subchecks (rather than `official_crs_used`). Update `measured_score`: geom_corruption 0.7 → 0.727, no_explode 0.8 → 0.818. The geom_corruption `expected_score_range` upper bound was 0.72 (sized for 7/10 = 0.7); the new measured score 0.727 lands just above it. Widen to [0.55, 0.75] so the new measurement is bracketed (still distinct from the no_explode band [0.72, 0.85]; the bands overlap by 0.03, which is acceptable because the two scenarios are documented separately and bracket distinct failure modes). no_explode range [0.72, 0.85] still brackets 0.818, no widening needed.
- task.json `analyst_notes` is missing — author it from scratch per the Step-4 schema. Cover the hidden gotcha (the agent must read "Egypt's national grid" as EPSG:22992, not pick UTM 36N), the standard composition order, and the principal failure modes. No instruction change ⇒ no version bump.
- coverage.yaml: axes unchanged; only refresh `evaluator_run_at`. The vocabulary still covers every axis used (operation_categories `format-io` + `crs-reprojection`, data_quality_issues `mixed-geometry-types` + `multipolygon-polygon-coercion`, geom types `point/linestring/polygon/multipolygon`, region `cairo`). No vocabulary gap.
- Inventory row says "Bundled local file" + mixed-geometry single FeatureCollection; current task matches exactly. No inventory mismatch.

### 3. Changes applied this run

#### Unilateral edits
- `README.md`: refreshed broken_no_explode (0.778 → 0.818) and broken_geom_corruption (0.667 → 0.727) score references; renamed `official_crs_used` → `crs_is_canonical`; rewrote failure-mode #4 for the soft-CRS Gate 1 (no hard-fail on 4326, two CRS subchecks dock points); rewrote failure-mode #4b for the 10/11 denominator and the new `crs_in_meaningful_set`. Re-grade on reference: 1.0. Reason: keep README in sync with the post-soft-CRS grader.
- `metadata.yaml`: rewrote broken_solutions descriptions for the 11-subcheck soft-CRS grader; updated `measured_score` (geom_corruption 0.7 → 0.727, no_explode 0.8 → 0.818); widened geom_corruption `expected_score_range` from [0.55, 0.72] to [0.55, 0.75] so the new measurement is inside. wrong_format unchanged (still 0.0 in [0.0, 0.0]). Reason: align scores with the post-soft-CRS grader.
- `task.json`: added `analyst_notes` (description + approach + pitfalls). No instruction change ⇒ no version bump (still version 2). Reason: human-facing reviewer note covering the hidden EPSG inference and the standard failure modes.
- `coverage.yaml`: refreshed `evaluator_run_at` to 2026-06-06T15:00:00Z. Axes unchanged. Reason: this evaluator pass.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.0 (11/11 subchecks, both gates pass)
- broken solutions: wrong_format 0.0, no_explode 0.818, geom_corruption 0.727 (all within `expected_score_range`)
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
- Per-layer geometry-type checks (points/lines/polygons match layer
  name) migrated to three new subchecks (`points_geometry_type`,
  `lines_geometry_type`, `polygons_geometry_type`).
- Summed-feature-count ±10 % migrated to a new
  `total_count_within_tolerance` subcheck.
- Subcheck total grew from 11 to 15.

### Verification
- Reference solution re-graded: 1.0 (15/15 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from prior reviews (see the 2026-06-06 block): a Format-I/O L2 task in which a heritage analyst supplies a hand-crafted 50-feature mixed-geometry GeoJSON of 10 Cairo heritage sites and the agent must stratify by geometry type, explode multi-part polygons, reproject to Egypt Red Belt (EPSG:22992, hinted only as "Egypt's national grid"), and write a multi-layer `heritage.gpkg` (`points` / `lines` / `polygons`) with `site_id` preserved as the cross-layer foreign key.

#### Change log (commits since the 2026-06-06 review block)
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | d90b43f | docs-change | Prior evaluator review (2026-06-06): appended block, refreshed README, metadata broken-solution scores, added `analyst_notes`, refreshed `coverage.yaml` / `audit/status.json`. | Commit msg: "Re-evaluate fio-l2-cairo-mixedgeom-split: calibrated; refresh soft-CRS docs and add analyst_notes" |
| 2026-06-06 | 363aed2 | grader-change | Gate 2 (`structural_correctness`) removed; per-layer geometry-type checks and the summed-count ±10 % check migrated to four new subchecks (`points/lines/polygons_geometry_type`, `total_count_within_tolerance`). Subcheck total 11 -> 15. Documented in the "Manual cleanup 2026-06-06" block above. | Commit msg: gate was inconsistent across the 36 graders; single hard `format_schema_valid` gate, salvageable checks become subchecks. |
| 2026-06-07 | c749e57 | grader-change | Eight data-content subchecks (`total_count_within_tolerance`, three per-layer counts, `site_id_jaccard_union`, `polygons_geometry_iou`, `points_geometry_per_site`, `lines_geometry_per_site`) tagged `weight=3.0`; seven schema/structural subchecks (geometry-type trio, `polygons_singletons_only`, `site_id_populated`, both CRS subchecks) stay at weight 1. Total weight 31. | Commit msg: "Weight data-content subchecks 3x across all categories" — score is now weighted-sum / total-weight, data-content failures cost more than schema slips. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38Z (commit c749e57, class: grader-change).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:39:30Z | 1.0 | done | current (task_version 2... see note) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:51:41Z | 1.0 | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T15:01:39Z | 1.0 | done | stale (pre-weighting cutoff; a 15/15 pass is weight-invariant) |

Note on the version check: both current runs record `task_version: 2`, equal to the pre-pass `task.json` version 2; the version this evaluator bumps to 3 (instruction house-style rewrite) postdates them, so they were current at audit time. Stale runs (footnote): 41 further runs from 2026-05-12 through 2026-06-07 across claude-code sonnet/opus, deepseek-v4-flash/pro, gemma4-26b, hy3-preview; they predate the Gate-2 removal and/or the 3x weighting and were graded by earlier grader generations. The near-cutoff stale picture (gemma-basic 0.909s from the 32636 pick, gemma-detailed / opus / deepseek 1.0s) is consistent with the prior "calibrated" verdicts.

#### Verdict
**insufficient-evidence**

Only two runs postdate the 2026-06-07 weighting commit and both come from one model family (deepseek-v4-flash, basic + detailed prompt variants). Both scored 1.0 with fully correct outputs (25/15/15 features, EPSG:22992 on all three layers, MultiPolygons exploded, `site_id` + `feature_kind` + names carried through), so nothing suggests miscalibration, but a single family cannot establish the score spread. The two grader changes since the last review are mechanical re-shapings (gate-to-subcheck migration, weighting) whose effect on this task's reference and brokens I re-measured directly: reference 1.0 (15/15, weight 31/31), `wrong_format` 0.0, `no_explode` 27/31 ≈ 0.871, `geom_corruption` 22/31 ≈ 0.710. The `no_explode` measurement had drifted above its documented `expected_score_range` upper bound (0.85), fixed in metadata.yaml this pass.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `heritage.gpkg`, GPKG format | instruction | stated |
| three layers named `points` / `lines` / `polygons` | instruction | stated |
| `site_id` column on every layer | instruction ("keeping the site_id on every feature") | stated |
| no MultiPolygon in polygons layer (explode) | instruction ("every feature has to be single-part") | stated |
| per-layer geometry type matches layer name | inferable from the layer names | inferable |
| per-layer / total feature counts within ±5 % / ±10 % | consequence of doing the split + explode correctly | inferable |
| CRS canonical EPSG:22992 (`crs_is_canonical`) | "Use Egypt's national grid" category hint + Cairo data | inferable (regional convention) |
| CRS meaningful set {22992, 32636} | grader-internal accept list | inferable (soft deduction only; 32636 is the generic defensible pick) |
| geometry agreement (IoU ≥ 0.9, 1 m per-site epsilon) | grader-internal tolerance | inferable (standard drift margin) |
| `site_id` Jaccard ≥ 0.9 | consequence of carrying site_id through | inferable |

Factual claims verified against the data: `heritage_sites.geojson` exists in `inputs/` (50 features, EPSG:4326, 25 Point / 15 LineString / 5 Polygon / 5 MultiPolygon, 10 distinct `site_id`s, columns `site_id`/`feature_kind`/`name_en`/`name_ar`); "every site is several features sharing a site_id" is accurate; the mixed-geometry and single-part claims match. No missing or inaccurate constraint.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it stratifies by geometry type, explodes multi-part polygons, reprojects to EPSG:22992, and writes the three named layers into one GPKG with all input attributes preserved. Two unrequested-but-benign mechanics: a `part_index` column added for explode provenance and a deterministic `(site_id, feature_kind, part_index)` sort plus `gpkg_contents.last_change` normalisation, both serving bit-stable reference builds rather than changing graded content (the grader checks neither `part_index` nor row order). Not flagged.

#### Specific findings
- metadata.yaml's broken-solution bookkeeping had drifted two grader generations behind (still 11-subcheck unweighted): `no_explode` measured 0.871 under the current grader, above its documented range [0.72, 0.85] and recorded score 0.818; `geom_corruption` measured 0.710 vs recorded 0.727. Refreshed both, widened the `no_explode` upper bound to 0.90 with a rationale line. Applied unilaterally.
- README still described "Gate 2", the 11-subcheck denominators (9/11, 10/11), the stale broken scores, and pre-reorganize paths (`data/`, `outputs/`). Rewrote the failure-mode section for the single-gate weighted grader and fixed the paths. Applied unilaterally.
- `task.json.instruction` violated house style: two em-dash constructions and a trailing spec-grammar fragment ("Layers: points / lines / polygons, GPKG.") that duplicated the layer-name and format constraints already stated in the same prompt. Rewrote in house style, preserving the persona, the `heritage_sites.geojson` reference (now by actual filename per house-style rule 5), the single-part requirement, all layer/file names, and the deliberately category-level "Use Egypt's national grid" hint. Version bumped 2 -> 3. Reference re-grade 1.0.
- `analyst_notes` referenced the removed Gate 2 and pre-weighting point arithmetic ("loses two points"); refreshed for the single-gate weighted grader.
- <!-- HUMAN-REVIEW id="HR-001" category="grader-miscalibration-suspected" severity="low" -->
  The cross-suite 3x data-content weighting (c749e57) diluted this task's regional-CRS discriminator: `crs_is_canonical` and `crs_in_meaningful_set` stay at weight 1 of a 31-weight total, so an otherwise-correct UTM 36N submission now scores 30/31 ≈ 0.968 (it scored 10/11 ≈ 0.909 before weighting, and the 2e4e372 accept-list refactor sized the canonical-pick penalty at ~0.1). If the suite wants the Egypt-Red-Belt-vs-UTM distinction to remain visible in headline scores, a human should decide whether CRS-pick subchecks deserve a higher weight class suite-wide; doing it only here would diverge from the deliberate c749e57 convention, so not applied unilaterally.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: house-style instruction rewrite (em-dashes removed, full sentences, actual filename `heritage_sites.geojson`, duplicate trailing layer/format fragment stripped); `version` 2 -> 3; `analyst_notes` refreshed for the single-gate weighted grader. Re-grade on reference: 1.0. Reason: house-style and redundancy rules; analyst_notes accuracy.
- `metadata.yaml`: `measured_score` refreshed (no_explode 0.818 -> 0.871, geom_corruption 0.727 -> 0.710), descriptions rewritten for the weighted 15-subcheck grader, `no_explode` `expected_score_range` upper bound widened 0.85 -> 0.90, tolerance rationale's stale "Gate 2" wording fixed. Reason: bookkeeping drifted two grader generations behind.
- `README.md`: failure-mode section rewritten for the single-gate weighted grader (scores 0.871 / 0.710 / 0.935 / 0.968, gate naming); stale `data/` / `outputs/` paths fixed. Reason: docs out of sync with grader.
- `coverage.yaml`: `evaluator_run_at` refreshed; axes unchanged (all slugs still validate against the vocabulary).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — grader-miscalibration-suspected (low) — 3x data-content weighting dilutes the canonical-CRS penalty to ~0.032; suite-wide weight-class decision needed if the regional-CRS discriminator should stay prominent.

#### Tests run
- grader on reference: 1.0 (15/15 subchecks, weight 31/31, gate passes)
- broken solutions: wrong_format 0.0, no_explode 0.871, geom_corruption 0.710 (all within their updated `expected_score_range`)
- pytest: pass (41/41)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change in one line
Replaced the blunt cross-suite 3x data-content weighting (c749e57) with per-task reasoned subcheck weights derived from what this Format-I/O task actually tests, and resolved HR-001. Grading-only: no check logic, threshold, gate, or task.json change; version stays 3.

### Reasoning
The central skills of this task are (a) the geometry split + multi-part explode and (b) reprojection to the *regional canonical* CRS (Egypt Red Belt, EPSG:22992). Subchecks that detect a central-skill failure get the highest weight; structural/cosmetic and pure-metadata-label checks get the lowest; geometry-agreement checks that prove the reprojection actually landed correctly sit in between (above pure label checks). The c749e57 pass had instead given a flat weight 3 to all eight "data-content" subchecks and weight 1 to everything else, which (i) left the explode skill's primary detector `polygons_singletons_only` at weight 1, and (ii) diluted the regional-CRS discriminator `crs_is_canonical` to 1/31, so an otherwise-correct UTM 36N submission scored 0.968 — the HR-001 complaint. Both CRS checks are metadata-label by nature; of the two, `crs_in_meaningful_set` is the *permissive* one (it passes for the defensible-but-wrong 32636 pick), so it stays at weight 1 while `crs_is_canonical` (the discriminator the design wants visible) goes to weight 4.

### Weight changes (subcheck: old -> new; unchanged omitted)
| Subcheck | old | new |
|---|---|---|
| `polygons_singletons_only` | 1.0 | 4.0 |
| `polygons_count_within_tolerance` | 3.0 | 4.0 |
| `crs_is_canonical` | 1.0 | 4.0 |
| `total_count_within_tolerance` | 3.0 | 1.0 |
| `points_count_within_tolerance` | 3.0 | 1.0 |
| `lines_count_within_tolerance` | 3.0 | 1.0 |

Unchanged: `points/lines/polygons_geometry_type` (1.0), `site_id_populated` (1.0), `crs_in_meaningful_set` (1.0), `site_id_jaccard_union` (3.0), `polygons_geometry_iou` (3.0), `points_geometry_per_site` (3.0), `lines_geometry_per_site` (3.0). Total weight 31 -> 32.

### Broken scores before -> after
| Class | before | after | note |
|---|---|---|---|
| `wrong_format` | 0.000 | 0.000 | gate rejects (not a GPKG / missing layers) — unchanged |
| `geom_corruption` | 0.710 | 0.719 | most severe non-gate failure: geometry wrong across all three layers; sits lowest |
| `no_explode` | 0.871 | 0.750 | central explode-skill miss (desktop tool rejects multi-parts); now a meaningful 0.25 drop |

Ordering is now sensible and monotone: `wrong_format` 0.0 < `geom_corruption` 0.719 < `no_explode` 0.750 < (UTM 36N pick 0.875) < (WGS84 no-reproject 0.844 — note this lands between no_explode and the UTM pick) < reference 1.0. The two CRS-only scenarios sit above the two geometry/structure-broken scenarios, which is correct: a defensible-CRS-label slip with otherwise-correct geometry is less damaging to the analyst than corrupted geometry or an un-ingestible multi-part file. No disjoint-failure inversion: the up-weighted explode group (no_explode) and the geometry group (geom_corruption) stay correctly ordered, and the up-weighted `crs_is_canonical` does not push the CRS scenarios below the broken-geometry ones.

### Prior-run re-grade summary
9 current/recent runs re-graded (the two `current` task_version-3 deepseek runs plus the post-soft-CRS family). The three gemma-basic UTM 36N runs (run-20260528-1624Z, run-20260528-2225Z, run-20260529-0109Z) move 0.968 -> 0.875 under the new weights (originally recorded 0.909 pre-weighting) — the regional-CRS discriminator is now visible in the headline score, which is exactly what HR-001 asked for. The six fully-correct EPSG:22992 runs (Opus, DeepSeek V4 Pro, Gemma-detailed, and the two `current` deepseek runs run-20260608-074701Z / run-20260609-084636Z) stay at 1.0 (weight-invariant on a full pass).

### Noted (not changed)
- No threshold, gate, or check-logic concern surfaced. The 1 m geometry epsilon, 0.9 IoU/Jaccard thresholds, and ±5 %/±10 % count tolerances are all left as-is.

### 3. Changes applied this run

#### Unilateral edits
- `grade.py`: subcheck `weight=` values only (table above). No logic/threshold/gate change.
- `metadata.yaml`: `broken_solutions` measured_score (no_explode 0.871 -> 0.750, geom_corruption 0.710 -> 0.719) and `expected_score_range` (no_explode [0.72,0.90] -> [0.70,0.80], geom_corruption [0.55,0.75] -> [0.60,0.75]); rewrote weight-arithmetic prose in the tolerance rationale and broken descriptions for the reasoned weights.
- `README.md`: refreshed the failure-mode weighting paragraph and the stale score fractions (no_explode 0.871 -> 0.750, geom_corruption 0.710 -> 0.719, WGS84 0.935 -> 0.844, UTM 36N 0.968 -> 0.875).
- `audit/status.json`: removed HR-001; recorded this pass.

#### HUMAN-REVIEW items
- HR-001 resolved and removed (per-task reasoned weights restore the regional-CRS penalty to a visible 0.125).

#### Tests run
- grader on reference: 1.0 (15/15 subchecks, weight 32/32, gate passes)
- broken solutions: wrong_format 0.0, no_explode 0.750, geom_corruption 0.719 (all within their updated `expected_score_range`)
- pytest: not run (orchestrator runs the suite)
