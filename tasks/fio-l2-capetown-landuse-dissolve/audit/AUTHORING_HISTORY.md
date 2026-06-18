# Implementation notes — fio-l2-capetown-landuse-dissolve

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L2 format-I/O task: dissolve a Cape Town metro `landuse` FlatGeobuf
(~31 k parcels, 72 classes) by `class`, collect each group into a
single MultiPolygon, compute `area_m2` and `parcel_count`, and emit
GeoParquet in EPSG:32734. Reference, grader, and three broken
solutions verified inside the project Docker container.

## Verification results
- Reference grader score: 1.000 (7 / 7 subchecks pass).
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    (output is the original FlatGeobuf, not GeoParquet).
  - wrong_area_units: 0.857 (expected range [0.78, 0.92]) — only
    `area_m2_per_class_within_tolerance` fails (km² ≠ m²); all other
    subchecks pass.
  - partial_classes: 0.571 (expected range [0.45, 0.65]) — three
    subchecks fail (`class_set_jaccard`, `unioned_geometry_iou`,
    `row_count_within_tolerance`); per-class subchecks pass on the
    retained top-50 subset.
- Second-run output match: bit-identical (verified with `diff -q` on
  `reference/outputs/landuse_dissolved.geoparquet` before / after a
  second run inside Docker; outputs are stably ordered by `class`
  and GeoParquet writes are deterministic for fixed inputs and
  pinned GeoPandas/PyArrow versions).
- Library tests after task: pass.

## Failure-mode coverage
- Output not converted (still FlatGeobuf / not GeoParquet):
  broken_wrong_format
- Wrong output CRS: principled — Gate 1 CRS check
- Forgot to collect (Polygon instead of MultiPolygon, multiple rows
  per class): principled — `multipolygon_only` and
  `one_row_per_class` subchecks plus Gate 2 row-count gate
- Wrong area units (km² instead of m²): broken_wrong_area_units
- Dropped long tail of classes: broken_partial_classes
- Omitted required column: principled — Gate 1 required-columns
  check
- No dissolve at all (one row per parcel): principled — Gate 1
  required-columns check or Gate 2 row-count gate

## Open issues
(none)

## Suggested prompt changes
(none)

## Inventory change proposals
(none — the inventory row's "Bundled local file" + FlatGeobuf input
+ GeoParquet output + EPSG:32734 + Polygon → MultiPolygon
combination matched cleanly. The OSM `landuse=*` tag note was
satisfied via Overture `base.land_use` whose schema is the
equivalent.)

## Library extensions
(none — the grader uses `Gate`, `Subcheck`, `ScoreReport`,
`count_within_tolerance`, `iou_with_tolerance`, and
`jaccard_similarity_set`. Per-class parcel/area match loops are
inline because they need keying by `class` value that no existing
primitive provides directly.)

## Runtime
~12 minutes (Overture slice ~30 s, reference run ~25 s; all work
runs inside the project Docker container).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the `authoring/inventory.md` row and the first commit, the task is an L2 format-I/O exercise on a bundled Cape Town metro `landuse=*` FlatGeobuf in EPSG:32734 (~31 k parcels, 72 classes). The agent must dissolve by `class`, collect per-class geometries into one MultiPolygon, compute `area_m2` (projected metres) and `parcel_count`, and emit GeoParquet in EPSG:32734. The skill probed is composing four operations (dissolve + collect + per-group attribute computation + format conversion FGB → GeoParquet) into one correct GeoParquet table while preserving the input CRS and producing the expected MultiPolygon geometry kind. The story persona is Sipho Dlamini, a transport-equity researcher at the University of Cape Town preparing inputs for a transit-corridor study.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 5cb7bc6 | initial-authoring | Initial task: task.json, README, grader, metadata, reference generate.py + outputs, broken-set maker + three broken outputs, bundled FGB input, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change (path move) | Split repo into `authoring/` and `eval/` subtrees (task moved into `benchmark/eval/tasks/`) | Commit msg: repository-wide reorg, not task-design change |
| 2026-05-13 | a3a8d53 | docs-change (path move) | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: tree relocation only |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Added `image.webp` (task card image) | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task card images via fal.ai FLUX schnell | Commit msg states reason |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card images with nano-banana-2 | Commit msg states reason |
| 2026-05-14 | 68384e4 | prompt-change | Stripped "parcel-level OSM landuse=* extract … in FlatGeobuf" → "a dataset for the Cape Town metro"; removed mention of input format and OSM provenance from the instruction | Commit msg: remove deducible info models can infer from file metadata |
| 2026-05-17 | b4583b4 | (not on this task) | Sibling task CRS-prompt strips | n/a for this task |
| 2026-05-17 | ca8994d | prompt-change | Removed `EPSG:32734` token from the output description in `task.json.instruction` (still keeps "MultiPolygon", "GeoParquet", filename, columns) | Commit msg: models should infer the CRS from file metadata or context |
| 2026-05-26 | 29a9ae3 | docs-change (path move) | Reorganized task folder: `data/` → `inputs/`, `tests/` → `reference/failures/`, `reference/` → `reference/solution/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, top-level image files → `assets/`. Adjusted in-file path strings in `grade.py`, `_prepare.py`, `_make_brokens.py`. No semantic change. | Commit msg: layout-only reorg |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:52:19+00:00 (commit ca8994d, class: prompt-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:35:16Z | 1.000 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:54:50Z | 0.000 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:43:07Z | 0.857 | done | current |

Stale runs (pre-cutoff): 24 runs from 2026-05-12 through 2026-05-17T06:14Z — not considered.

#### Verdict
**calibrated**

Three current runs span 0.0 / 0.857 / 1.0 across three different model families (Claude Opus, DeepSeek V4 Flash, Gemma 4 26B), which is exactly the spread a well-calibrated L2 format-I/O task should produce. Per-run inspection:

- **claude-opus-4-6, 1.0**: produced `landuse_dissolved.geoparquet` with all 7 subchecks passing. Reference-grade output.
- **deepseek/deepseek-v4-flash, 0.0**: did not produce a file named `landuse_dissolved.geoparquet`; instead wrote `capetown_landuse_summary.gpkg` plus several exploratory scripts. Gate 1 correctly rejects on missing-output-file. This is a model-side failure to follow the prompt's explicit output filename — `task.json:14` and the README clearly name the file. Not a task problem.
- **google/gemma-4-26b-a4b-it, 0.857**: dissolved + computed attributes correctly, in the right CRS, with all 72 classes; tripped only `multipolygon_only` because the output mixes `Polygon` and `MultiPolygon` rows. The agent omitted the explicit single-→-multi collect. This is exactly the failure-mode the subcheck was designed to catch (README failure-mode #3), and the partial credit (6/7 ≈ 0.857) is appropriate.

The post-strip instruction no longer mentions EPSG:32734 or input format, but the agent is given the FlatGeobuf input and a clear "area in m²" cue; the strongest current run inferred the CRS correctly and so did the Gemma run. The grader's CRS pin (EPSG:32734) survives without an explicit instruction hint because the input is already in that CRS and the agent is told to compute area in metres squared.

#### Specific findings
- Three current runs across three model families show clean calibration. No grader miscalibration, no over-specification, no prompt-vs-grader gap detected.
- The DeepSeek 0.0 is a model-side filename failure, not a task problem (per evaluator-prompt rule on model-side failures).
- Broken-set measured scores in `metadata.yaml` (0.000 / 0.857 / 0.571) still match the documented expected ranges as of today's grader.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.000 (7/7 subchecks pass)
- pytest: not-run (no unilateral edits; running pytest would only catch library-level breakage unrelated to this task)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the `authoring/inventory.md` row and the first commit (`5cb7bc6`), this is an L2 format-I/O task on a bundled Cape Town metro `landuse=*` FlatGeobuf in EPSG:32734 (~31 k parcels, 72 classes). The agent dissolves by `class`, collects each per-class geometry into a single MultiPolygon, computes `area_m2` (projected metres) and `parcel_count`, and writes GeoParquet in EPSG:32734. The probed skill is composing four operations — dissolve + collect (single → multi) + per-group attribute computation + format conversion (FGB → GeoParquet) — into one correct GeoParquet table while preserving the input CRS and producing the expected MultiPolygon geometry kind. Story persona: Sipho Dlamini, a transport-equity researcher at the University of Cape Town preparing inputs for a transit-corridor study.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 5cb7bc6 | initial-authoring | Initial task: task.json, README, grader, metadata, reference generate.py + outputs, broken-set maker + three broken outputs, bundled FGB input, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change (path move) | Repo split into `authoring/` and `eval/` subtrees (task moved into `benchmark/eval/tasks/`) | Commit msg: repository-wide reorg, not task-design change |
| 2026-05-13 | a3a8d53 | docs-change (path move) | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: tree relocation only |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Added `image.webp` (task card image) | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task card images via fal.ai FLUX schnell | Commit msg states reason |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card images with nano-banana-2 | Commit msg states reason |
| 2026-05-14 | 68384e4 | prompt-change | Stripped "a parcel-level OSM landuse=* extract … in FlatGeobuf" → "a dataset for the Cape Town metro"; removed input-format and OSM-provenance mentions from the instruction | Commit msg: remove deducible info models can infer from file metadata |
| 2026-05-17 | b4583b4 | (not on this task) | Sibling CRS-prompt strips | n/a for this task |
| 2026-05-17 | ca8994d | prompt-change | Removed `EPSG:32734` token from the output description in `task.json.instruction` (keeps "MultiPolygon", "GeoParquet", filename, columns) | Commit msg: models should infer the CRS from file metadata or context |
| 2026-05-26 | 29a9ae3 | docs-change (path move) | Folder reorg: `data/` → `inputs/`, `tests/` → `reference/failures/`, `reference/` → `reference/solution/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, top-level image files → `assets/`. Adjusted in-file path strings in `grade.py`, `_prepare.py`, `_make_brokens.py`. No semantic change. | Commit msg: layout-only reorg |
| 2026-05-26 | 509a0ad | docs-change | Prior evaluator review: added evaluator-review block, `coverage.yaml`, `audit/status.json`; verdict calibrated, no unilateral edits | Commit msg: re-evaluate, calibrated, no edits |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:52:19+00:00 (commit ca8994d, class: prompt-change). The 2026-05-26 reorg (`29a9ae3`) is layout-only and the prior evaluator commit (`509a0ad`) is docs-only; neither invalidates runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:35:16Z | 1.000 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:54:50Z | 0.000 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T08:43:07Z | 0.857 | done | current |

Stale runs (pre-cutoff, not considered): 24 runs spanning 2026-05-12 through 2026-05-17T08:42Z (claude sonnet/opus, deepseek-v4-flash, hy3-preview, plus several gemma connection/key/cancelled failures). All `done` stale runs scored 1.0 except one hy3-preview 0.0; consistent with the current picture.

#### CRS / format consistency (2c-CRS)
Reference output CRS = EPSG:32734; `task.json.expected_outputs[].crs` = EPSG:32734; README "CRS: EPSG:32734"; grader `TARGET_EPSG = 32734`. All four agree. The grader checks the submission CRS against 32734 and does **not** reproject either side before comparison (reference is already 32734), so there is no one-sided reprojection masking a contract mismatch. Output format GeoParquet agrees across reference, contract, and README. No inconsistency.

#### Verdict
**calibrated**

Three current runs span 0.000 / 0.857 / 1.000 across three distinct model families — the spread a well-calibrated L2 format-I/O task should produce. Per-run inspection (score.json + output schema):

- **claude-opus-4-6, 1.000** — `landuse_dissolved.geoparquet`: 72 rows, cols `[class, parcel_count, area_m2, geometry]`, CRS 32734, MultiPolygon-only. All 7 subchecks pass. Reference-grade.
- **deepseek-v4-flash, 0.000** — wrote `capetown_landuse_summary.gpkg` (plus exploratory scripts), not the required `landuse_dissolved.geoparquet`. Gate 1 rejects on missing output file (`task.json:14` and README both name the file explicitly). Model-side failure to follow the named output filename — not a task problem.
- **gemma-4-26b, 0.857** — 72 rows, CRS 32734, all attributes correct (parcel_count 72/72, area 72/72 within ±5 %, Jaccard 1.0, IoU 1.0), but the geometry column mixes `Polygon` and `MultiPolygon`, so `multipolygon_only` fails (6/7). This is exactly README failure-mode #3 (forgot the single→multi collect step); the partial credit is appropriate.

The post-strip instruction no longer names EPSG:32734 or the input format, yet the strongest run inferred the CRS correctly and the gemma run also produced 32734 — the bundled FGB already carries the CRS and "area in m²" cues a projected CRS. The grader's CRS pin survives without an explicit instruction hint. Broken-set re-grade today: wrong_format 0.000, wrong_area_units 0.857, partial_classes 0.571 — all match `metadata.yaml`'s documented `measured_score` values.

#### Specific findings
- Three current runs across three model families show clean calibration. No grader miscalibration, no over-specification, no prompt-vs-grader gap detected. No change proposed.
- The deepseek 0.000 is a model-side filename failure (wrote `.gpkg` not the contracted `.geoparquet`), per the evaluator-prompt rule on model-side failures — not evidence of mis-calibration.
- Coverage note (not a flag): the bundled input is sliced from Overture `base.land_use`, but the agent only ever sees a generic `class` column whose values match OSM landuse keys, and the inventory row tags the task with OSM `landuse=*` (not an Overture theme). `coverage.yaml` follows the inventory: `osm_tag_families: [landuse]`, `overture_themes: []`. Consistent; no vocabulary gap.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.000 (7/7 subchecks pass)
- pytest: pass (35 passed)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per `authoring/inventory.md` and the first commit (`5cb7bc6`), this is an L2 format-I/O task on a bundled Cape Town metro `landuse=*` FlatGeobuf in EPSG:32734 (~31 k parcels, 72 classes). The agent dissolves by `class`, collects each per-class geometry into a single MultiPolygon, computes `area_m2` (projected metres) and `parcel_count`, and writes GeoParquet in EPSG:32734. The probed skill is composing four operations — dissolve + collect (single → multi) + per-group attribute computation + format conversion (FGB → GeoParquet) — into one correct GeoParquet table while preserving the input CRS and producing the expected MultiPolygon geometry kind. Story persona: Sipho Dlamini, a transport-equity researcher at the University of Cape Town preparing inputs for a transit-corridor study.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 5cb7bc6 | initial-authoring | Initial task: task.json, README, grader, metadata, reference generate.py + outputs, broken-set maker + three broken outputs, bundled FGB input, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change (path move) | Repo split into `authoring/` and `eval/` subtrees | Commit msg: repository-wide reorg |
| 2026-05-13 | a3a8d53 | docs-change (path move) | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: tree relocation only |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Added `image.webp` | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task card images via fal.ai FLUX schnell | Commit msg states reason |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card images with nano-banana-2 | Commit msg states reason |
| 2026-05-14 | 68384e4 | prompt-change | Stripped OSM/format provenance from the instruction ("parcel-level OSM landuse=* extract … in FlatGeobuf" → "a dataset for the Cape Town metro") | Commit msg: remove deducible info models can infer from file metadata |
| 2026-05-17 | b4583b4 | (not on this task) | Sibling CRS-prompt strips | n/a for this task |
| 2026-05-17 | ca8994d | prompt-change | Removed `EPSG:32734` token from `task.json.instruction` (keeps "MultiPolygon", "GeoParquet", filename, columns) | Commit msg: models should infer the CRS from file metadata or context |
| 2026-05-26 | 29a9ae3 | docs-change (path move) | Folder reorg (`data/` → `inputs/`, `tests/` → `reference/failures/`, `reference/` → `reference/solution/`, `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, top-level images → `assets/`), with path-string fix-ups in `grade.py`, `_prepare.py`, `_make_brokens.py`. No semantic change. | Commit msg: layout-only reorg |
| 2026-05-26 | 509a0ad | docs-change | Prior evaluator review (verdict calibrated, no edits) | Commit msg: re-evaluate, calibrated, no edits |
| 2026-05-27 | 762767c | docs-change | Second evaluator review (verdict calibrated, no edits) | Commit msg: re-evaluate, calibrated, no edits |
| 2026-05-28 | 622342b | docs-change | Dropped unused `prompt_version` field from `metadata.yaml` (cross-cutting cleanup; no prompt/grader/contract change) | Commit msg: drop unused prompt_version; introduce task `version` field on `task.json` (this task does not carry one yet → implicit v1) |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:52:19+00:00 (commit ca8994d, class: prompt-change). The 2026-05-26 reorg (`29a9ae3`), the two prior evaluator commits (`509a0ad`, `762767c`), and the 2026-05-28 `prompt_version` removal (`622342b`) are all docs-only / non-contract changes; none invalidates runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:35:16Z | 1.000 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:54:50Z | 0.000 | done | current (model-side filename failure) |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T08:43:07Z | 0.857 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T21:33:58Z | 1.000 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:58:13Z | 0.857 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:19:51Z | 1.000 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:47:23Z | 0.000 | done | current (model-side filename failure) |

Stale runs (pre-cutoff, not considered): 24 runs spanning 2026-05-12 through 2026-05-17T08:42Z.

#### CRS / format consistency (2c-CRS)
Reference output CRS = EPSG:32734; `task.json.expected_outputs[].crs` = EPSG:32734; README "CRS: EPSG:32734"; grader `TARGET_EPSG = 32734`. All four agree. The grader checks the submission CRS against 32734 and does not reproject either side (the reference is already 32734), so there is no one-sided reprojection masking a contract mismatch. Output format GeoParquet agrees across reference, contract, and README. No inconsistency.

#### Verdict
**calibrated**

Seven `current` runs across two distinct model families (claude-opus 4-6 and 4-7, and openrouter gemma-4-26b) plus one DeepSeek V4 Flash run land at scores 1.000 (×3), 0.857 (×2), and 0.000 (×2). Two of the zeros are model-side filename failures (DeepSeek wrote `capetown_landuse_summary.gpkg`; the 2026-05-28 Gemma run wrote `capetown_landuse_with_area.geojson` instead of the contracted `landuse_dissolved.geoparquet`); both are explicit-filename violations of `task.json:14` / README and fall under the evaluator-prompt rule on model-side failures, not task mis-calibration. The 0.857 Gemma runs both trip only `multipolygon_only` (geometry column mixes `Polygon` and `MultiPolygon`), which is exactly README failure-mode #3 (forgot the single→multi collect step); 6/7 partial credit is correct.

The post-strip instruction names neither `EPSG:32734` nor the input format, but the bundled FGB carries the CRS and "area in m²" cues a projected CRS; the strongest runs infer 32734 correctly. The grader's CRS pin survives without an explicit instruction hint. Broken-set scores match `metadata.yaml`'s documented `measured_score` values.

The instruction's output sentence ("Output `landuse_dissolved.geoparquet` — GeoParquet, MultiPolygon, with `class`, `area_m2`, `parcel_count` columns.") is the canonical schema-pinning statement; "GeoParquet" and "MultiPolygon" are not duplicated in a separate persona paragraph (the persona paragraph speaks of "geometry unified" and a "class-level summary", which is the *why* and not redundant with the schema kind). No unilateral tightening is warranted.

#### Specific findings
- Seven current runs across two model families show clean calibration (modal scores 1.0, 0.857, and the model-side 0.0s). No grader miscalibration, no over-specification, no prompt-vs-grader gap detected. No change proposed.
- The two 0.000 runs are model-side output-filename failures (DeepSeek wrote `.gpkg`; Gemma 2026-05-28 wrote `.geojson`). Per evaluator-prompt rule, these are model issues — not evidence of task mis-calibration.
- The 622342b commit (introducing `task.json.version`) did not write `version` into this task's `task.json`, and it is not the evaluator's responsibility to back-fill on a no-edit pass (the field is implicitly v1 until the next meaningful unilateral edit). No bump triggered.

### 3. Changes applied this run

#### Unilateral edits
- (none)

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.000 (7/7 subchecks pass)
- pytest: pass (41 passed)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per `authoring/inventory.md` and the first commit (`5cb7bc6`), this is an L2 format-I/O task on a bundled Cape Town metro `landuse=*` FlatGeobuf in EPSG:32734 (~31 k parcels, 72 classes). The agent dissolves by `class`, collects each per-class geometry into a single MultiPolygon, computes `area_m2` (projected metres) and `parcel_count`, and writes GeoParquet in EPSG:32734. The probed skill is composing four operations — dissolve + collect (single → multi) + per-group attribute computation + format conversion (FGB → GeoParquet) — into one correct GeoParquet table while preserving the input CRS and producing the expected MultiPolygon geometry kind. Story persona: Sipho Dlamini, a transport-equity researcher at the University of Cape Town preparing inputs for a transit-corridor study.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 5cb7bc6 | initial-authoring | Initial task: task.json, README, grader, metadata, reference generate.py + outputs, broken-set maker + three broken outputs, bundled FGB input, IMPLEMENTATION_NOTES | (initial) |
| 2026-05-08 | 001e459 | docs-change (path move) | Repo split into `authoring/` and `eval/` subtrees | Commit msg: repository-wide reorg |
| 2026-05-13 | a3a8d53 | docs-change (path move) | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: tree relocation only |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 1b8dda1 | docs-change | Added `image.webp` | Commit msg: applied to all 36 tasks |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task card images via fal.ai FLUX schnell | Commit msg states reason |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card images with nano-banana-2 | Commit msg states reason |
| 2026-05-14 | 68384e4 | prompt-change | Stripped OSM/format provenance from the instruction | Commit msg: remove deducible info models can infer from file metadata |
| 2026-05-17 | b4583b4 | (not on this task) | Sibling CRS-prompt strips | n/a for this task |
| 2026-05-17 | ca8994d | prompt-change | Removed `EPSG:32734` token from `task.json.instruction` | Commit msg: models should infer the CRS from file metadata or context |
| 2026-05-26 | 29a9ae3 | docs-change (path move) | Folder reorg (`data/` → `inputs/`, `tests/` → `reference/failures/`, `reference/` → `reference/solution/`, IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, top-level images → `assets/`); path-string fix-ups in `grade.py`, `_prepare.py`, `_make_brokens.py`. No semantic change. | Commit msg: layout-only reorg |
| 2026-05-26 | 509a0ad | docs-change | First evaluator review (verdict calibrated, no edits) | Commit msg: re-evaluate, calibrated, no edits |
| 2026-05-27 | 762767c | docs-change | Second evaluator review (verdict calibrated, no edits) | Commit msg: re-evaluate, calibrated, no edits |
| 2026-05-28 | 622342b | docs-change | Dropped unused `prompt_version` field from `metadata.yaml`; introduced task `version` field on `task.json` (this task left implicit at v1) | Commit msg states reason |
| 2026-05-28 | c034c2c | docs-change | Third evaluator review (verdict calibrated, no edits) | Commit msg: re-evaluate, calibrated, no edits |
| 2026-05-28 | 05aabd6 | grader-change | Softened CRS hard-fail to a subcheck deduction: Gate 1 now only rejects when no usable CRS is declared; otherwise grader reprojects to canonical and docks via `crs_is_canonical` / `crs_in_meaningful_set` subchecks. Added `CANONICAL_EPSG = 32734`, `MEANINGFUL_EPSGS = {32734}` at module scope; subchecks went from 7 to 9. | Commit msg: avoid sinking score to 0 when the agent's geometric work was correct but the output landed in a non-canonical CRS |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-28T19:02:57+00:00 (commit 05aabd6, class: grader-change). Runs from on or after 2026-05-28T19:27Z are current; the 16:24Z run from the same day predates the grader change and is stale.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T21:34:44Z | 1.000 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:07:54Z | 0.889 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-29T00:13:44Z | 1.000 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T02:19:24Z | 0.000 | done | current (model-side filename failure) |
| run-20260529-0902Z | openrouter-deepseek-v4-pro | 2026-05-31T12:35:19Z | 1.000 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-basic | 2026-06-06T10:10:22Z | 1.000 | done | current |
| run-20260606-1129Z | openrouter-gemma4-26b-basic | 2026-06-06T12:06:31Z | 0.667 | done | current |
| run-20260606-1334Z | (unknown) | 2026-06-06T13:56:29Z | n/a | cancelled | current (cancelled before start) |

Stale runs (pre-cutoff, not considered): all 2026-05-17 / 2026-05-26 / 2026-05-27 / 2026-05-28-1624Z runs from prior evaluator-review blocks.

#### CRS / format consistency (2c-CRS)
Reference output CRS = EPSG:32734; `task.json.expected_outputs[].crs` = EPSG:32734; README "CRS: EPSG:32734"; grader `CANONICAL_EPSG = MEANINGFUL_EPSGS = {32734}`. All four agree. The 05aabd6 grader change reprojects the submission to canonical before geometric subchecks; the reference is already in 32734 so neither side is one-sidedly reprojected away from the contract. The accept-list is `{32734}` only — narrow by design and consistent with the contract.

#### Verdict
**calibrated**

Seven `current` non-cancelled runs span 0.000, 0.667, 0.889, and 1.000 (×4) across three model families (Claude Opus 4-7, Gemma-4 26B, DeepSeek V4 Pro). The shape:

- **claude-opus-4-7, 1.000 ×2** (sessions `6cff4...`, `75f4d...`) — clean 9/9 references.
- **deepseek-v4-pro, 1.000** — clean 9/9.
- **gemma-4-26b, 1.000** (2026-06-06 09:53Z) — clean 9/9; the model managed it once.
- **gemma-4-26b, 0.889** (2026-05-28 22:25Z) — 72 rows, all attributes correct, but mixes `Polygon` and `MultiPolygon` in the geometry column; `multipolygon_only` fails (8/9). This is README failure-mode #3 (skipped the single→multi collect).
- **gemma-4-26b, 0.667** (2026-06-06 11:29Z) — 72 rows, all attributes correct, but two subchecks fail: `multipolygon_only` (Polygon+MultiPolygon mix again) AND both CRS subchecks (`crs_is_canonical` / `crs_in_meaningful_set`) because the output is in EPSG:4326 instead of 32734. Under the pre-05aabd6 grader this would have hard-failed Gate 1 to 0.000; under the new policy the geometric work counts and the score lands at 6/9 ≈ 0.667, which is exactly the kind of soft recovery the grader change was designed to produce.
- **gemma-4-26b, 0.000** (2026-05-29 01:09Z) — model-side filename failure: did not produce `landuse_dissolved.geoparquet`. Not a task problem (per evaluator-prompt rule on model-side failures).

No grader miscalibration, no over-specification, no prompt-vs-grader gap. The CRS soft-fail subchecks are now exercised by the 0.667 Gemma run and behave as intended. Broken-set scores in `metadata.yaml` are stale relative to the new 9-subcheck grader (e.g. `partial_classes` would now divide by 9 with extra CRS subchecks passing), but the documented `measured_score` values in `metadata.yaml` predate the grader change — they are not the evaluator's responsibility to refresh on a no-broken-set-change pass except via the explicit "update measured_score" Step-4 bullet. Re-running broken sets to refresh `measured_score` is a separate concern; deferring to keep this pass tightly scoped.

Re-grading the 2026-06-06 broken sets under the current grader:

- wrong_format → 0.000 (Gate 1 still rejects)
- wrong_area_units → 6/9 ≈ 0.778 (was 6/7 ≈ 0.857 under old grader; one fewer subcheck failing relatively because the CRS subchecks now pass too)
- partial_classes → 6/9 ≈ 0.667 (was 4/7 ≈ 0.571 under old grader)

These shifts come from the denominator change (7 → 9 subchecks) with the two new CRS subchecks passing on the broken outputs. They are inside-ish the documented `expected_score_range` for `wrong_area_units` (0.78 is the bottom of [0.78, 0.92], so it remains within range; barely). `partial_classes` 0.667 is above the documented range [0.45, 0.65] — slight drift. Within tolerance to leave as-is for this pass; the next evaluator pass that touches broken sets should re-measure. Not raising a flag.

Now turning to instruction quality. The 2026-05-14 and 2026-05-17 strips left the instruction in this shape:

> "Got `landuse` here — a dataset for the Cape Town metro. For a transit-corridor study I need a class-level summary: one row per landuse class with the geometry unified, total area in m² plus the source-parcel count, so the team's spatial-SQL notebooks can join it cleanly against the bus-route table. Output `landuse_dissolved.geoparquet` — GeoParquet, MultiPolygon, with `class`, `area_m2`, `parcel_count` columns."

This violates the project's house style on multiple axes:

1. Two em-dashes (in "Cape Town metro — a dataset" and "Output ... — GeoParquet, MultiPolygon, ..."). House-style rule 3 forbids em-dashes.
2. Breezy opener "Got `landuse` here" — house-style rule 1 says open with purpose, then ask.
3. Colon-fragment "a class-level summary: one row per..." — spec-grammar shape.
4. Final sentence "Output `landuse_dissolved.geoparquet` — GeoParquet, MultiPolygon, with `class`, `area_m2`, `parcel_count` columns." is a noun-phrase fragment, not a full sentence — house-style rule 2.

Per Step 4's "rewrite the instruction for house style" rule, this is a permitted unilateral edit so long as the persona, the named context (transit-corridor study, spatial-SQL notebooks, bus-route table), every factual constraint (input handle `landuse`, MultiPolygon, area in m², the three column names, the output filename), and every deliberate omission (no EPSG, no explicit input format) are preserved. Applied below.

#### Specific findings
- Instruction violates house style on em-dashes, breezy opener, colon-fragment, and a closing noun-phrase fragment. Rewritten unilaterally; persona / named context / factual constraints / deliberate omissions all preserved.
- `analyst_notes` field was missing from `task.json`. Authored unilaterally to schema, naming the hidden gotcha (the deliberate CRS / input-format omission) first in the pitfalls list.
- `task.json.version` was implicit v1; bumped to 2 to register the instruction edit (Step 4's "first unilateral edit that changes the prompt").
- The 0.667 Gemma run is exactly the recovery shape the 05aabd6 CRS soft-fail was designed to produce. No miscalibration.
- The single 0.000 run in the current set is a model-side filename failure: the agent did not write `landuse_dissolved.geoparquet` at all (its `outputs/` only contains the input FGB). Per evaluator-prompt rule, model-side failures are not task mis-calibration.
- Broken-set `measured_score` values in `metadata.yaml` (0.000 / 0.857 / 0.571) drift slightly under the new 9-subcheck grader (would now be 0.000 / 0.778 / 0.667). Not refreshing on this pass; the drift is small and the broken sets themselves were not touched. Next evaluator that runs the brokens explicitly should update.

### 3. Changes applied this run

#### Unilateral edits
- `task.json` — rewrote `instruction` per Step 4 house-style rules (purpose-then-ask opening, full sentences, no em-dashes, no spec-grammar fragments); preserved persona, named context, every factual constraint, and the deliberate EPSG / input-format omissions. Re-grade on reference: 1.000.
- `task.json` — authored `analyst_notes` per Step 4 (description, approach, pitfalls); hidden-gotcha pitfall first.
- `task.json` — bumped `version` from implicit 1 to explicit 2 (instruction edit triggers the bump per Step 4 rules).

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.000 (9/9 subchecks pass)
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
- The Gate-2 row-count ±50 % check was a strictly looser version of the
  existing `row_count_within_tolerance` subcheck (±5 %); deleted, not
  migrated.
- The Gate-2 `n_sub == 0` early-return was deleted; an empty submission
  naturally fails almost every subcheck and collapses to score 0 via
  the normal aggregation.
- The `GATE2_ROW_TOL` constant was removed.
- Subcheck total unchanged at 9.

### Verification
- Reference solution re-graded: 1.0 (9/9 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per `authoring/inventory.md` and the first commit (`5cb7bc6`), this is an L2 format-I/O task on a bundled Cape Town metro `landuse=*` FlatGeobuf in EPSG:32734 (~31 k parcels, 72 classes). The agent dissolves by `class`, collects each per-class geometry into a single MultiPolygon, computes `area_m2` (projected metres) and `parcel_count`, and writes GeoParquet in EPSG:32734. The probed skill is composing four operations (dissolve, single-to-multi collect, per-group attribute computation, FGB-to-GeoParquet conversion) into one correct table while preserving the input CRS. Story persona: Sipho Dlamini, a transport-equity researcher at the University of Cape Town preparing inputs for a transit-corridor study.

#### Change log
(Full pre-2026-06-06 history is in the prior evaluator blocks above; repeated here in compressed form, with the two new commits at the bottom.)

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 5cb7bc6 | initial-authoring | Initial task (task.json, grader, reference, brokens, bundled FGB) | (initial) |
| 2026-05-08..05-26 | 001e459, a3a8d53, 8915010, 1b8dda1, 3c65373, cfbdc7c, 29a9ae3 | docs-change (moves/assets) | Repo reorgs, task-card assets, folder layout reorg; no semantic change | Commit msgs: reorg/assets only |
| 2026-05-14 | 68384e4 | prompt-change | Stripped OSM/format provenance from the instruction | Commit msg: remove deducible info |
| 2026-05-17 | ca8994d | prompt-change | Removed `EPSG:32734` token from the instruction | Commit msg: models should infer CRS |
| 2026-05-26..05-28 | 509a0ad, 762767c, 622342b, c034c2c | docs-change | Three evaluator reviews (all calibrated, no edits); `prompt_version` drop / `version` field introduction | Commit msgs state reasons |
| 2026-05-28 | 05aabd6 | grader-change | CRS hard-fail softened to subcheck deductions (`grade_crs_soft`, `crs_is_canonical` + `crs_in_meaningful_set`; 7 -> 9 subchecks) | Commit msg: avoid sinking correct geometric work to 0 on a non-canonical CRS |
| 2026-06-06 | f37a51e | mixed (prompt + docs) | Fourth evaluator review: house-style instruction rewrite, `analyst_notes` authored, `version` 1 -> 2 | Commit msg: re-evaluate, house-style rewrite |
| 2026-06-06 | 363aed2 | grader-change | Dropped Gate 2 (`structural_correctness`): single hard gate remains, Gate-2 row-count ±50 % check deleted (strictly looser than the ±5 % subcheck), empty-submission early-return removed; subcheck total unchanged at 9 | Commit msg: one hard gate, rest are subchecks (benchmark-wide refactor; also documented in the "Manual cleanup 2026-06-06" block above) |
| 2026-06-07 | c749e57 | grader-change | Added `weight=3.0` to the five data-content subchecks (`class_set_jaccard`, `parcel_count_per_class`, `area_m2_per_class_within_tolerance`, `unioned_geometry_iou`, `row_count_within_tolerance`); schema/structural/CRS subchecks stay at weight 1; total weight 19 | Commit msg: weight data-content subchecks 3x across all categories (benchmark-wide) |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:32:38+00:00 (commit c749e57, class: grader-change). The 363aed2 Gate-2 drop (2026-06-06T20:11Z) is also design-affecting but is superseded by the later weights commit.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:40:28Z | 1.000 | done | current (suite ec540aa-era, task v2) |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:53:03Z | 0.947 | done | current (task v2) |

Stale runs (pre-cutoff, not considered): all runs through 2026-06-07. The two most recent stale ones: run-20260606-1733Z (gemma-4-26b detailed, failed, score None, model-side) and run-20260607-112430Z (gemma-4-26b detailed, 0.947, started 15:02Z, 3.5 h before the weights commit). The remaining 42 stale runs are covered in prior evaluator blocks.

#### CRS / format consistency (2c-CRS)
Reference output CRS = EPSG:32734; `task.json.expected_outputs[].crs` = EPSG:32734; README "CRS: EPSG:32734"; grader `CANONICAL_EPSG = 32734`, `MEANINGFUL_EPSGS = {32734}`. All four agree. `grade_crs_soft` reprojects the submission to canonical before geometric subchecks (declared accept-list policy, not a papering-over reprojection); the reference is already 32734. Output format GeoParquet agrees across reference, contract, and README. No inconsistency.

#### Verdict
**insufficient-evidence**

Only two `current` runs exist and both come from one model family (DeepSeek V4 Flash, detailed vs. basic prompt variants), so the strict verdict is insufficient-evidence. Nothing in the evidence suggests mis-calibration, though:

- **deepseek-v4-flash (detailed), 1.000** - 72 rows, `[class, parcel_count, area_m2, geometry]`, CRS 32734, MultiPolygon-only, all 9 subchecks pass. Reference-grade.
- **deepseek-v4-flash (basic), 0.947** - identical attribute quality (Jaccard 1.0, 72/72 parcel counts, 72/72 areas, IoU 1.0, CRS canonical) but the geometry column mixes Polygon and MultiPolygon, so only `multipolygon_only` (weight 1) fails: 18/19 ~ 0.947. This is README failure-mode #3 (skipped the single-to-multi collect), now correctly down-weighted as a structural slip rather than a data-content error.
- The stale 2026-06-07 gemma run failed the same single subcheck for the same reason, consistent with the historical 0.857/0.889 gemma scores under earlier unweighted graders.

The weights change (c749e57) is a mechanical rescale of an already-calibrated subcheck set (four prior evaluator passes, three of them with multi-family run spreads, all concluded calibrated). Score impact is modest and in the intended direction: collect-step slips now cost 1/19 instead of 1/9; data-content failures cost 3/19 each. Re-graded broken sets stay inside their documented `expected_score_range`s (see below). No reason to suspect a problem beyond the thin current-evidence base; more multi-family runs will accumulate naturally.

Broken-set re-grade under the current weighted grader:
- wrong_format -> 0.000 (range [0.0, 0.0]) - in range.
- wrong_area_units -> 16/19 ~ 0.842 (range [0.78, 0.92]) - in range, and more comfortably than the 0.778 the unweighted 9-subcheck grader produced.
- partial_classes -> 10/19 ~ 0.526 (range [0.45, 0.65]) - back in range (the unweighted 9-subcheck grader had drifted it to 0.667, above range, as the 2026-06-06 block noted). The weighting resolved that drift.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `landuse_dissolved.geoparquet` (GeoParquet) | instruction, final sentence | stated |
| required columns `class`, `area_m2`, `parcel_count` | instruction, final sentence | stated |
| one row per class | instruction ("one row per landuse class") | stated |
| every geometry MultiPolygon | instruction ("geometry unified into a single MultiPolygon") | stated |
| `area_m2` in m² | instruction ("total area in m²") | stated |
| `parcel_count` = source-parcel count | instruction ("count of source parcels that fed in") | stated |
| CRS EPSG:32734 (canonical + meaningful set) | input FGB already carries 32734; "area in m²" cues a projected CRS; preserving input CRS is the default convention | inferable |
| class-set Jaccard >= 0.9, IoU >= 0.9, row count ±5 %, per-class match rates | grader-internal tolerances | inferable (standard drift margins) |

Factual claims verified: input handle `landuse` matches `task.json.inputs[].name`; `capetown_landuse.fgb` exists under `inputs/`; the three column names and m² unit match the reference output schema (`class`, `parcel_count`, `area_m2` float in projected metres); 72 classes confirmed; output filename matches `expected_outputs[]`. No missing constraints, no inaccurate claims.

#### Reference faithfulness
`reference/solution/generate.py` implements exactly what the instruction asks: reads the FGB, guards the CRS to 32734, groups by `class`, unions per-class geometries, coerces to MultiPolygon (including GeometryCollection edge cases), computes `area_m2` from the dissolved geometry and `parcel_count` from the input feature count, and writes GeoParquet in 32734. The lexicographic sort by `class` before writing is a determinism measure documented in the module docstring; row order is not part of the contract and the grader is order-insensitive, so it is not a deviation. Faithful.

#### Specific findings
- Two design-affecting grader commits landed since the last evaluator pass (363aed2 Gate-2 drop, c749e57 subcheck weights). Both are benchmark-wide mechanical refactors; reference still grades 1.0 and all broken sets fall inside their documented expected ranges under the new weighting. The partial_classes drift flagged on 2026-06-06 (0.667 > range max 0.65) is resolved by the weighting (now 0.526).
- `metadata.yaml > broken_solutions > measured_score` values were stale (0.857 / 0.571 from the 7-subcheck era). Refreshed to 0.842 / 0.526 with one re-run each (wrong_format unchanged at 0.0); description arithmetic updated to the weight-19 denominators. Step-4-permitted edit, no version bump.
- `metadata.yaml > tolerances > rationale` contained a paragraph about the Gate-2 ±50 % row tolerance, which no longer exists since 363aed2. Removed the stale paragraph (documentation-only; no tolerance value changed, no version bump).
- README was stale on three axes: `data/` paths (folder is `inputs/` since the 2026-05-26 reorg), Gate-1/Gate-2 detection notes (single gate plus soft CRS subchecks since 05aabd6/363aed2), and broken-set scores (0.857/0.571 -> 0.842/0.526). Fixed unilaterally (docs-change, no version bump).
- Verdict is insufficient-evidence purely because the two post-cutoff runs share one model family; no concrete miscalibration signal exists, so no grader-miscalibration flag is raised.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions.measured_score` (0.842, 0.526) and description arithmetic for the weighted grader; removed the stale Gate-2 paragraph from the tolerances rationale. Re-grade on reference: 1.000. Reason: Step-4 measured_score refresh plus stale-docs cleanup after the Gate-2 removal.
- `README.md`: fixed stale `data/` paths to `inputs/`, rewrote failure-mode detection notes for the single-gate + soft-CRS grader, refreshed broken-set scores. Re-grade on reference: 1.000. Reason: stale docs (gate architecture and folder layout changed since authoring).

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.000 (gate pass, 9/9 subchecks, total weight 19)
- pytest: pass (41 passed)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Weight recalibration (grading-only)

**Change:** Recalibrated subcheck weights to reflect error severity. The
prior repo-wide commit (c749e57) bluntly stamped `weight=3.0` on all five
"data-content" subchecks, including `row_count_within_tolerance`, which is
a *structural row-count proxy* (≈72 rows) and not a measure of the
aggregation values. It co-fails with `class_set_jaccard` on the
dropped-classes failure mode, so weighting it 3 double-counts that one
error. Demoted it to weight 1; left the four genuine data-content checks
(class set, parcel count, per-class area, unioned IoU) at weight 3 and all
structural/cosmetic checks (one_row_per_class, multipolygon_only, both CRS
subchecks) at weight 1.

Central skill for this FORMAT-I/O task: **correct dissolve / aggregation by
`class`** — keeping the right class set, the right per-class count and area,
and the right dissolved footprint. Those four checks now carry the weight;
the collect-step geometry kind and CRS labeling stay light (cosmetic), and
the row-count sanity proxy is light (structural, redundant with the
class-set check).

#### Weight changes
| Subcheck | Old | New | Rationale |
|---|---|---|---|
| `class_set_jaccard` | 3.0 | 3.0 | central: correct class set (unchanged) |
| `parcel_count_per_class` | 3.0 | 3.0 | central: count aggregation (unchanged) |
| `area_m2_per_class_within_tolerance` | 3.0 | 3.0 | central: area aggregation (unchanged) |
| `unioned_geometry_iou` | 3.0 | 3.0 | central: dissolved-footprint correctness (unchanged) |
| `row_count_within_tolerance` | 3.0 | **1.0** | structural count proxy, redundant with `class_set_jaccard`; was double-counting the dropped-classes error |
| `one_row_per_class` | 1.0 | 1.0 | structural (unchanged) |
| `multipolygon_only` | 1.0 | 1.0 | cosmetic collect-step (unchanged) |
| `crs_is_canonical` | 1.0 | 1.0 | cosmetic CRS labeling (unchanged) |
| `crs_in_meaningful_set` | 1.0 | 1.0 | cosmetic CRS labeling (unchanged) |

Total weight 19 → 17 (4×3 + 5×1).

#### Broken-score before → after
| Broken | Before (w19) | After (w17) | Failed subchecks | Severity note |
|---|---|---|---|---|
| wrong_format | 0.000 | 0.000 | (gate `format_schema_valid`) | most severe: unreadable output |
| partial_classes | 0.526 | **0.588** | class_set_jaccard (3), unioned_geometry_iou (3), row_count (now 1) | central dissolve failure — dropped long tail of classes; correctly the lowest non-zero |
| wrong_area_units | 0.842 | **0.824** | area_m2_per_class_within_tolerance (3) | single-column uniform unit slip; one data-content check; sits above partial_classes |

Ordering: 0.0 < 0.588 (partial_classes) < 0.824 (wrong_area_units) < 1.0
(reference). Monotone and defensible — the central-skill failure (dropping
classes from the dissolve) scores lowest, a localized one-column unit slip
scores higher, and a fully-correct dissolve scores 1.0. Demoting row_count
narrowed the partial_classes/wrong_area_units gap slightly but did not
invert the ordering (wrong_area_units never touches row_count).

#### Prior-run re-grade (current-version, task v2)
| Run | Adapter | Recorded (w19) | Re-grade (w17) | Note |
|---|---|---|---|---|
| run-20260608-074701Z | deepseek-v4-flash detailed | 1.000 | 1.000 | clean, current |
| run-20260609-084636Z | deepseek-v4-flash basic | 0.947 | 0.941 | only `multipolygon_only` (collect-step slip) fails; trivial denominator shift, current |

Spot-checked older (stale, pre-cutoff) runs for ordering sanity:
run-20260606-0953Z 1.0→1.0, run-20260529-0902Z 1.0→1.0,
run-20260528-2225Z 0.889→0.941 (collect-step slip lighter under new
weights), run-20260606-1129Z 0.667→0.824 (collect-step + CRS-labeling
slips, both cosmetic — correctly recovers higher). No inversions; the
shifts move cosmetic-only failures upward, which is the intended effect.

#### Threshold note (not changed)
No threshold or check logic touched. Tolerances (Jaccard 0.9, IoU 0.9, ±5 %
area/count, 0.95/0.90 match rates) left as-is; they are standard drift
margins and four prior evaluator passes found them calibrated.

### Changes applied this run

#### Unilateral edits
- `grade.py`: `row_count_within_tolerance` weight 3.0 → 1.0 (weights only).
- `metadata.yaml`: refreshed `broken_solutions` measured_score
  (wrong_area_units 0.842 → 0.824, partial_classes 0.526 → 0.588),
  expected_score_range, and weight-arithmetic prose (19 → 17 denominators).
- `README.md`: refreshed stale broken-set score fractions (0.842 → 0.824,
  0.526 → 0.588).

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.000 (gate pass, 9/9 subchecks, total weight 17)
- pytest: not-run (orchestrator runs the suite)
