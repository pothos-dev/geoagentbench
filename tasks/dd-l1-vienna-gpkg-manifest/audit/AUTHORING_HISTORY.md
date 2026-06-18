# Implementation notes — dd-l1-vienna-gpkg-manifest

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 data-discovery task: enumerate the seven layers of a bundled
multi-layer Vienna GPKG (EPSG:31287) and emit a JSON manifest of
each layer's name, CRS, geometry type, feature count, and native
bounding box. Reference, grader, and three broken solutions built
and verified inside the project Docker container.

## Verification results
- Reference grader score: 1.00 (29 / 29 subchecks pass)
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    the CSV body (top-level not a JSON list), no subcheck runs.
  - partial_layers: 0.414 (expected range [0.35, 0.50]) — agent
    submitted only districts / parks / schools; `layers_complete`
    plus the four absent layers' 16 subchecks fail; the three
    covered layers' 12 subchecks pass.
  - wrong_crs_bbox: 0.517 (expected range [0.45, 0.60]) — agent
    declared EPSG:4326 with degree-scale bboxes; every layer's
    `crs_correct` and `bbox_correct` flips; the layer set, geometry
    types, and counts pass.
- Second-run output match: bit-identical (verified with `diff -q`
  on `reference/outputs/manifest.json` before and after a second
  `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Partial layer enumeration (only the inventory's primary trio):
  broken_partial_layers
- Silent reprojection to EPSG:4326 (CRS + bbox both wrong):
  broken_wrong_crs_bbox
- Wrong output format (CSV / wrong top-level type / missing keys):
  broken_wrong_format
- Single-layer treatment (only the default-first layer): principled —
  `layers_complete` plus per-layer subchecks
- Per-layer bbox computed over the whole-GPKG union: principled —
  per-layer `bbox_correct` subchecks
- Geometry type from the first feature instead of the layer schema:
  principled — `<layer>_geom_type_correct`
- Non-canonical CRS string (`"31287"` etc.): principled —
  `<layer>_crs_correct` (case-insensitive exact match on EPSG code)
- Off-by-one feature counts: principled — `<layer>_count_correct`

## Open issues
- [severity: low] — The inventory row tags the task with
  `boundary=administrative` (OSM) for the districts layer, but the
  bundled fixture is sliced from Overture's `divisions.division_area`
  (`subtype IN ('locality', 'microhood', 'neighborhood')`). Per
  AUTHOR_CONTEXT.md and OVERTURE_REFERENCE.md, Overture is the
  default authoring source and Overpass is a fallback only when no
  clean Overture equivalent exists; `divisions.division_area` is the
  structural equivalent of `boundary=administrative` for inventory
  purposes. The GPKG container, EPSG:31287 CRS, and multi-layer
  structure are properties of the bundled file and independent of
  the upstream source.
- [severity: low] — The inventory row lists "Polygon, Point" as the
  geometry-type axis but a "districts/parks/schools" multi-layer
  GPKG with a bicycle-network reform backstory naturally pulls in a
  LineString cycleway layer (matching the persona's story exactly).
  The grader treats LineString as a first-class geometry type for
  the manifest; this does not contradict the inventory but extends
  it slightly for realism.

## Suggested prompt changes
(none)

## Inventory change proposals
(none — see Open issues for two minor extensions)

## Library extensions
(none — the grader uses only `Gate`, `Subcheck`, and `ScoreReport`
from `geo_grading`. Per-layer attribute checks, set-membership
checks, and bbox componentwise tolerance checks are simple JSON-
shape comparisons rather than geometric primitives.)

## Runtime
~14 minutes (one Overture slice fetch ~30 s plus several local
Docker reference / grader runs).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row at `benchmark/authoring/inventory.md:30`, this is an
L1 data-discovery task: a junior planner inherits a multi-layer Vienna GPKG
(EPSG:31287, MGI / Austria Lambert) and must produce a one-page manifest
of each layer's name, declared CRS, geometry type, feature count, and
bounding box. The task probes GPKG multi-layer enumeration plus per-layer
schema introspection — the GIS-literate move of opening a multi-layer
container with a schema-aware tool (pyogrio / fiona / ogrinfo / DuckDB-
spatial) rather than treating it as a single-layer file. Bounds must be
reported in the layer's *own* CRS (no reprojection). The bundled GPKG
holds seven layers (the inventory-named primary trio districts / parks /
schools plus four auxiliary cuts: waterbodies, cafes, supermarkets,
cycleway_segments), so an agent that pattern-matches the inventory's
named trio without opening the file produces a recognisably partial
manifest.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 0a7e5e1 | initial-authoring | Initial task: task.json, grade.py, metadata.yaml, README.md, reference/generate.py + outputs/, data/_prepare_input.py + vienna_planning.gpkg, tests/_make_brokens.py + three broken_* outputs, IMPLEMENTATION_NOTES.md | (initial) |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" bullet to `instruction` listing the five record keys and types | Commit msg: "declare exact output schema in prompts to match graders ... No grader changes; no subchecks loosened." |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dictionary (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) to `task.json`; no behavioural change | Commit msg: "add structured tags to all 36 task.json files ... Values derived from the inventory axes." |
| 2026-05-13 | 9e79176 | prompt-change | Refactored the "Output schema:" bullet block into a single fluent paragraph in `instruction` (same five keys, prose form) | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | b04e9f0 | prompt-change | Dropped the word "multi-layer" from "Inherited a multi-layer GPKG" — the persona no longer pre-discloses that the file holds multiple layers | Commit msg: "strip deducible information from DD task instructions ... Remove input CRS, geometry types, column names, format descriptions, data hints, and encoding specifics ... Output requirements and narrative framing preserved." |
| 2026-05-17 | 88530c5 | prompt-change | Replaced "Walk every layer and give me one record per layer with the layer name, declared CRS, geometry type, feature count, and bounding box (in the layer's own CRS, no reprojection)" with the terse "Catalog the contents and give me one record per layer." Trailing "in the layer's own CRS" tightened to "in the layer's native CRS" in the schema sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorganisation: IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, data/ -> inputs/, reference/{generate.py,outputs/} -> reference/solution/, tests/ -> reference/failures/, image* -> assets/. Path constants in grade.py, generate.py, _make_brokens.py, _prepare.py, and the task.json input URL adjusted accordingly. No behavioural / schema / data changes | Commit msg: "Reorganize task folder layout ... Adjusts all path references ... Also lands the task-evaluator agent prompt + coverage vocabulary + authoring-history template." |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:18:31Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:22:35Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:34Z | 1.0 | done | current |
| (21 earlier runs) | mixed | pre-cutoff | mixed | mixed | stale (pre-cutoff) |

Stale-run footnote: pre-cutoff runs span 2026-05-12 → 2026-05-17 across haiku / sonnet / opus / gemma / hy3 / deepseek adapters; sonnet & haiku scored 0.0, opus scored 1.0, openrouter adapters were mostly infra-failed before keys were configured. Those scores were against earlier, more procedurally-verbose instruction wordings (1710715 / 9e79176 / b04e9f0 / 88530c5) — they are evidence about the prior task state, not the current one.

#### Verdict
**calibrated**

Three current runs across three independent agent families (Anthropic Claude Opus, DeepSeek v4 Flash via OpenRouter, Google Gemma-4-26B via OpenRouter) all score 1.0 on the post-strip instruction. For an L1 schema-introspection task this is the calibration target, not a defect: the L1 contract is "a competent agent should reliably succeed on a single-op, bundled task." The instruction (`task.json:14`) contains no procedural gifts — it neither names the tool, the CRS, the layer set, nor a step-by-step recipe; it does spell out the output record shape (five keys, types, bbox order), which Step 4 of the evaluator prompt explicitly classifies as a necessary redundant output-schema sentence. The output-file name `manifest.json` is bundled-input metadata the agent cannot infer. The grader (`grade.py:117-218`) checks layer-set membership plus four per-layer attribute subchecks (CRS, geometry type, feature count, bbox) with the tolerances justified in `metadata.yaml:14-39`; the bbox 1 m window absorbs pyogrio/fiona float drift while still catching unit/CRS-confusion errors (degree-vs-metre slip ≈ 6×10⁵ off, whole-file union bbox ≈ 10³ m off). The score.json inspection for run-20260526-0748Z confirms all 29 subchecks pass with bbox max-|Δ| around 0.003–0.004 m — well inside tolerance. Three broken-set outputs (`reference/failures/broken_*/`) still anchor the lower end of the scoring range with measured scores 0.000 / 0.414 / 0.517, giving the subcheck composition real discrimination power even with the all-1.0 current evidence.

#### Specific findings
- Instruction stripping has converged on a clean form: "Catalog the contents and give me one record per layer" + a five-key schema paragraph. No further gift-stripping is warranted — removing the schema paragraph would push the task into prompt-grader-inconsistent territory because the grader requires exact key names (`grade.py:27`).
- Inventory row at `inventory.md:30` lists geometry types as "Polygon, Point" but the bundled GPKG (and grader) also includes LineString (`cycleway_segments`) and MultiPolygon (`parks`). This is acknowledged in the author block's Open issues; the prior author flagged it as a deliberate realism extension to the persona's bicycle-network-reform story. Treating this as a low-severity inventory mismatch rather than a task defect.
  <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" -->
  Inventory `geometry_type` lists "Polygon, Point" but the fixture (and grader) also exercise LineString (`cycleway_segments`) and MultiPolygon (`parks`). The author block already noted this as a deliberate extension; either update the inventory row to add LineString + MultiPolygon, or accept the extension as-is.
- Inventory row's OSM-tag axis lists `boundary=administrative` for the districts layer but the fixture is sliced from Overture's `divisions.division_area` (`subtype IN ('locality','microhood','neighborhood')`). Per AUTHOR_CONTEXT.md Overture is the authoring default and `divisions.division_area` is the structural equivalent. This is the original author's open issue (Open issues bullet 1) and reads as expected — flagging at low severity for visibility.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  Inventory's OSM-tag axis lists `boundary=administrative` for districts but the fixture uses Overture `divisions.division_area`. Either update the inventory row's OSM-tag column to "—" (and rely on the Overture-theme column), or document that the two are interchangeable for inventory coverage purposes.

### 3. Changes applied this run

#### Unilateral edits
- (none — task is calibrated, no grader or prompt edits warranted)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — Inventory geometry_type axis disagrees with fixture (missing LineString + MultiPolygon).
- HR-002 — inventory-mismatch — Inventory OSM-tag axis for districts disagrees with the Overture provenance of the fixture.

#### Tests run
- grader on reference: 1.0 (29/29 subchecks pass) — `cd benchmark/eval && uv run python ../tasks/dd-l1-vienna-gpkg-manifest/grade.py ../tasks/dd-l1-vienna-gpkg-manifest/reference/solution/outputs`
- pytest: not-run (no unilateral edits made; pytest gate only required after edits per evaluator prompt Step 4)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row at `benchmark/authoring/inventory.md:30`, this is an L1
data-discovery task: a junior planner (Lukas Hofer, MA 18) inherits a
multi-layer Vienna GPKG (EPSG:31287, MGI / Austria Lambert) from a retired
colleague and must produce a one-page manifest of each layer's name, declared
CRS, geometry type, feature count, and bounding box, so he can decide which
layers feed next month's councillor briefing and which are stale. The probed
skill is GPKG multi-layer enumeration plus per-layer schema introspection —
the GIS-literate move of opening a multi-layer container with a schema-aware
tool (pyogrio / fiona / ogrinfo / DuckDB-spatial) rather than treating it as a
single-layer file — and reporting each bbox in the layer's *own* CRS (no
reprojection). The bundled GPKG holds seven layers: the inventory-named primary
trio (districts / parks / schools) plus four auxiliary cuts (waterbodies,
cafes, supermarkets, cycleway_segments), so an agent that pattern-matches the
named trio without opening the file yields a recognisably partial manifest.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 0a7e5e1 | initial-authoring | Initial task: task.json, grade.py, metadata.yaml, README.md, reference generate.py + outputs/, _prepare input + vienna_planning.gpkg, _make_brokens + three broken_* outputs, IMPLEMENTATION_NOTES.md | (initial) |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict (region/data_source/formats/crs/geometry_type/operations/themes/quality_issues/scale) to `task.json`; values derived from inventory axes, no behavioural/instruction/answer-key change | Commit msg: "add structured tags to all 36 task.json files ... Values derived from the inventory axes." |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" bullet to `instruction` listing the five record keys and types | Commit msg: "declare exact output schema in prompts to match graders ... No grader changes; no subchecks loosened." |
| 2026-05-13 | 9e79176 | prompt-change | Refactored the "Output schema:" bullet block into a single fluent paragraph in `instruction` (same five keys, prose form) | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | b04e9f0 | prompt-change | Dropped "multi-layer" from "Inherited a multi-layer GPKG" — the persona no longer pre-discloses that the file holds multiple layers | Commit msg: "strip deducible information from DD task instructions ... Remove input CRS, geometry types, column names, format descriptions, data hints, and encoding specifics ... Output requirements and narrative framing preserved." |
| 2026-05-17 | 88530c5 | prompt-change | Replaced the procedural "Walk every layer ... (in the layer's own CRS, no reprojection)" sentence with terse "Catalog the contents and give me one record per layer."; tightened schema sentence's "in the layer's own CRS" to "in the layer's native CRS" | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, data/ → inputs/, reference/{generate.py,outputs/} → reference/solution/, tests/ → reference/failures/, image* → assets/; path constants adjusted in grade.py, generate.py, _make_brokens.py, _prepare.py and the task.json input URL. No behavioural/schema/data change | Commit msg: "Reorganize task folder layout ... Adjusts all path references ... Also lands the task-evaluator agent prompt + coverage vocabulary + authoring-history template." |
| 2026-05-26 | a80e59e | docs-change | Prior evaluator review: appended evaluator-review block to audit/AUTHORING_HISTORY.md, wrote coverage.yaml + audit/status.json; no task-behaviour edits | Commit msg: "Re-evaluate dd-l1-vienna-gpkg-manifest: calibrated; 2 low-severity inventory-mismatch flags" |

Note: the directory-level `git log --follow` form omitted the early
pre-folder-reorg commits (paths lived under `benchmark/eval/tasks/...` then
`benchmark/tasks/...`); cross-checked by searching commit messages and the
slug, recovering 0a7e5e1, 284b843, 1710715, 9e79176, b04e9f0. The `tags`-dict
commit (284b843) touches `task.json` but neither the `instruction` nor
`expected_outputs[]` (the answer key), so it is classed docs-change and does
not move the cutoff; even if treated as prompt-adjacent its 2026-05-13
timestamp precedes the cutoff.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:18:31Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:22:35Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:34Z | 1.0 | done | current |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T08:19:41Z | 1.0 | done | stale (pre-cutoff) |
| (21 earlier runs) | mixed | pre-cutoff | mixed | mixed | stale (pre-cutoff) |

Stale-run footnote: `run-20260517-0614Z` started 2026-05-17T08:19:41Z — about
4.5 h before the cutoff — so although it scored 1.0 it is not current evidence.
The remaining pre-cutoff runs span 2026-05-12 → 2026-05-17 across
haiku/sonnet/opus/gemma/hy3/deepseek adapters against earlier, more
procedurally-verbose instruction wordings; they describe prior task states,
not the current one.

#### Verdict
**calibrated**

Three current runs across three independent agent families (Anthropic Claude
Opus, DeepSeek v4 Flash via OpenRouter, Google Gemma-4-26B via OpenRouter) all
score 1.0 on the post-strip instruction. For an L1 single-op bundled task this
is the calibration target, not a defect — the L1 contract is "a competent agent
should reliably succeed." Independent per-output inspection of all three
confirms a 7-record list, exact layer-set match, correct CRS/geometry/count for
every layer, and bbox componentwise deltas of ~0.002–0.005 m (far inside the
1 m tolerance at `grade.py:25`/`metadata.yaml:13`). The instruction
(`task.json:14`) carries no procedural gifts: it names neither the tool, the
CRS, the layer set, nor a step-by-step recipe; it does spell out the five-key
output record shape, which Step 4 of the evaluator prompt explicitly classifies
as a necessary redundant output-schema sentence (the grader at `grade.py:27`
requires the exact key names, so stripping it would create a
prompt-grader-inconsistency). The bundled `vienna_planning.gpkg` was
independently introspected with pyogrio and matches the reference manifest
exactly (7 layers; districts 22 Polygon, parks 119 MultiPolygon, waterbodies
33 Polygon, schools 40 Point, cafes 392 Point, supermarkets 87 Point,
cycleway_segments 271 LineString; all EPSG:31287). The three broken sets in
`reference/failures/broken_*/` re-graded at 0.000 / 0.4138 / 0.5172 — matching
the `metadata.yaml > broken_solutions > measured_score` values — giving the
subcheck composition real discrimination power despite the all-1.0 current
evidence.

CRS/format consistency (Step 2c-CRS): reference output CRS (`EPSG:31287`),
`expected_outputs[].crs` (`EPSG:31287`), and README's stated output CRS
(EPSG:31287 metres) all agree. The grader compares CRS strings and bbox numbers
in the native CRS with no reprojection on either side — there is no one-sided
reprojection. Consistent.

#### Specific findings
- Instruction has converged on a clean, gift-free form ("Catalog the contents
  and give me one record per layer." + a five-key schema paragraph). No further
  stripping warranted; removing the schema paragraph would break the
  prompt↔grader contract.
- Inventory `geometry_type` axis (`inventory.md:44`) lists "Polygon, Point" but
  the fixture and grader also exercise LineString (`cycleway_segments`) and
  MultiPolygon (`parks`). The author block (Open issues) and the prior
  evaluator both flagged this as a deliberate realism extension tied to the
  bicycle-network-reform persona. Persisting, low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" -->
  Inventory `geometry_type` lists "Polygon, Point" but the fixture (and grader) also exercise LineString (`cycleway_segments`) and MultiPolygon (`parks`). Either extend the inventory row's geometry-type axis to add LineString + MultiPolygon, or accept the documented extension as-is. Editing `inventory.md` is outside the per-task authority boundary, so this remains a flag rather than a unilateral edit.
- Inventory OSM-tag axis (`inventory.md:48`) lists `boundary=administrative` for
  the districts layer, but the fixture is sliced from Overture's
  `divisions.division_area` (`subtype IN ('locality','microhood','neighborhood')`).
  Per author-context.md Overture is the authoring default and
  `divisions.division_area` is the structural equivalent. Persisting,
  low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  Inventory's OSM-tag axis lists `boundary=administrative` for districts but the fixture uses Overture `divisions.division_area`. Either change the inventory row's OSM-tag column to "—" (relying on the Overture-theme column), or document that the two are interchangeable for inventory coverage purposes. Editing `inventory.md` is outside the per-task authority boundary.

### 3. Changes applied this run

#### Unilateral edits
- (none — task is calibrated; grader, tolerances, and instruction are all sound, so no edit is warranted)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — Inventory geometry_type axis ("Polygon, Point") omits the fixture's LineString + MultiPolygon layers.
- HR-002 — inventory-mismatch — Inventory OSM-tag axis (`boundary=administrative`) disagrees with the fixture's Overture `divisions.division_area` provenance.

#### Tests run
- grader on reference: 1.0 (29/29 subchecks pass) — `cd benchmark/eval && uv run python ../tasks/dd-l1-vienna-gpkg-manifest/grade.py ../tasks/dd-l1-vienna-gpkg-manifest/reference/solution/outputs`
- broken-set re-grade: broken_wrong_format 0.000, broken_partial_layers 0.4138, broken_wrong_crs_bbox 0.5172 (all match metadata measured_score)
- pytest: not-run (no unilateral edits made; pytest gate only required after edits per evaluator prompt Step 4)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row at `benchmark/authoring/inventory.md:30`, this is an L1
data-discovery task: junior planner Lukas Hofer (Vienna MA 18) inherits a
multi-layer Vienna GPKG (EPSG:31287, MGI / Austria Lambert) and must emit a
one-page manifest — one record per layer with `layer_name`, `crs`,
`geometry_type`, `feature_count`, and `bbox` (in the layer's own CRS). The
probed skill is GPKG multi-layer enumeration + per-layer schema introspection:
opening a multi-layer container with a schema-aware tool (pyogrio / fiona /
ogrinfo / DuckDB-spatial) rather than treating it as single-layer, and
reporting metadata exactly as declared (no reprojection of bboxes). The
bundled file holds seven layers — the inventory's primary trio
(districts / parks / schools) plus four auxiliary cuts (waterbodies, cafes,
supermarkets, cycleway_segments) — so an agent that pattern-matches the
trio without opening the file yields a recognisably partial manifest
(broken_partial_layers anchors that at 0.414).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 0a7e5e1 | initial-authoring | Initial task: task.json, grade.py, metadata.yaml, README.md, reference generate.py + outputs/, _prepare input + vienna_planning.gpkg, _make_brokens + three broken_* outputs, IMPLEMENTATION_NOTES.md | (initial) |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json`; no behavioural change | Commit msg: "add structured tags to all 36 task.json files ... Values derived from the inventory axes." |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" bullet to `instruction` listing five record keys + types | Commit msg: "declare exact output schema in prompts to match graders ... No grader changes; no subchecks loosened." |
| 2026-05-13 | 9e79176 | prompt-change | Refactored the "Output schema:" bullets into a single fluent paragraph (same five keys, prose form) | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | b04e9f0 | prompt-change | Dropped "multi-layer" from "Inherited a multi-layer GPKG" — persona no longer pre-discloses multi-layer structure | Commit msg: "strip deducible information from DD task instructions ... Output requirements and narrative framing preserved." |
| 2026-05-17 | 88530c5 | prompt-change | Replaced procedural "Walk every layer ... (in the layer's own CRS, no reprojection)" with terse "Catalog the contents and give me one record per layer."; "in the layer's own CRS" tightened to "in the layer's native CRS" in the schema sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorganisation: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, data/ → inputs/, reference/{generate.py,outputs/} → reference/solution/, tests/ → reference/failures/, image* → assets/. Path constants in grade.py, generate.py, _make_brokens.py, _prepare.py, and task.json input URL adjusted. No behavioural/schema/data change | Commit msg: "Reorganize task folder layout ..." |
| 2026-05-26 | a80e59e | docs-change | First evaluator-review block + coverage.yaml + audit/status.json. No task-behaviour edits | Commit msg: "Re-evaluate dd-l1-vienna-gpkg-manifest: calibrated; 2 low-severity inventory-mismatch flags" |
| 2026-05-27 | 82770e2 | docs-change | Second evaluator-review block appended; coverage.yaml + status.json refreshed. No task-behaviour edits | Commit msg: "Re-evaluate dd-l1-vienna-gpkg-manifest: calibrated; 2 low-severity inventory-mismatch flags" |
| 2026-05-28 | 622342b | docs-change | Repo-wide infra change: dropped unused `prompt_version` from this task's metadata.yaml (1-line deletion). Adds task-content `version` field machinery to runtime/UI, but task.json here is unchanged. No prompt / grader / inputs / tolerances impact | Commit msg: "Add task content versioning; drop unused prompt_version" |

Note: directory-level `git log --follow` continues to omit the pre-folder-reorg
commits (paths lived under `benchmark/eval/tasks/...` then `benchmark/tasks/...`);
cross-checked by `git log --all --grep='dd-l1-vienna-gpkg-manifest'` and recovered
0a7e5e1, 1710715, 9e79176. The 2026-05-28 metadata.yaml edit (622342b) is
docs-change: it deletes `prompt_version: 2026-05-08-a` only; the field tags the
authoring template, not the task contract. No instruction / grader / inputs /
tolerance change → cutoff is unchanged.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-28T03:35:50Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:02:44Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:46:50Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:54:29Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:34Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:22:35Z | 1.0 | done | current |
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:18:31Z | 1.0 | done | current |
| (22 earlier runs) | mixed | pre-cutoff | mixed | mixed | stale (pre-cutoff) |

Stale-run footnote: 22 pre-cutoff runs span 2026-05-12 → 2026-05-17 across
haiku/sonnet/opus/gemma/hy3/deepseek adapters against earlier, more
procedurally-verbose instruction wordings; they describe prior task states,
not the current one.

#### Verdict
**calibrated**

Seven current runs across three independent agent families (Anthropic Claude
Opus 4-6 and 4-7, DeepSeek v4 Flash via OpenRouter, Google Gemma-4-26B via
OpenRouter) all score 1.0 on the post-strip instruction; the four newest
(both adapters across two days) repeat the result against the very latest
prompt. For an L1 single-op bundled task this is the calibration target,
not a defect — the L1 contract is "a competent agent should reliably succeed."
Per-output inspection of every current run shows a 7-record list with exact
layer-set match (cafes, cycleway_segments, districts, parks, schools,
supermarkets, waterbodies), correct CRS / geometry / count for every layer,
and bbox componentwise deltas well inside the 1 m tolerance — score.json
reports 29/29 subchecks passing for all four new runs. The instruction
(`task.json:14`) carries no procedural gifts: it names neither the tool, the
CRS, the layer set, nor a step-by-step recipe; it does spell out the five-key
output record shape, which Step 4 explicitly classifies as a necessary
redundant output-schema sentence (the grader at `grade.py:27` requires the
exact key names — stripping the schema paragraph would create a
prompt-grader-inconsistency). Re-grading the reference yields 1.0 (29/29
subchecks pass); broken-set scores still anchor the lower end of the scoring
range at 0.000 / 0.4138 / 0.5172 per `metadata.yaml > broken_solutions`.

CRS/format consistency (Step 2c-CRS): reference output CRS (`EPSG:31287`),
`expected_outputs[].crs` (`EPSG:31287`), and README's stated output CRS
(EPSG:31287 metres) all agree. The grader compares CRS strings and bbox
numbers in the native CRS with no reprojection on either side — there is no
one-sided reprojection. Consistent.

#### Specific findings
- Instruction has converged on a clean, gift-free form ("Catalog the contents
  and give me one record per layer." + a five-key schema paragraph). No
  further stripping warranted; removing the schema paragraph would break the
  prompt↔grader contract.
- The 2026-05-28 infra commit (622342b) dropped `prompt_version` from this
  task's `metadata.yaml`; the field tagged the authoring template, not the
  task content, and has no runtime relevance. `task.json` does not yet carry
  the new `version` field — per the new Step 4 wording, tasks without it are
  implicitly v1 and the next meaningful edit must bump to v2. This evaluator
  pass makes no meaningful edits, so no bump is required.
- Inventory `geometry_type` axis (`inventory.md:44`) lists "Polygon, Point" but
  the fixture and grader also exercise LineString (`cycleway_segments`) and
  MultiPolygon (`parks`). Author block + prior evaluators flagged this as a
  deliberate realism extension tied to the bicycle-network-reform persona.
  Persisting, low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" -->
  Inventory `geometry_type` lists "Polygon, Point" but the fixture (and grader) also exercise LineString (`cycleway_segments`) and MultiPolygon (`parks`). Either extend the inventory row's geometry-type axis to add LineString + MultiPolygon, or accept the documented extension as-is. Editing `inventory.md` is outside the per-task authority boundary.
- Inventory OSM-tag axis (`inventory.md:48`) lists `boundary=administrative` for
  the districts layer, but the fixture is sliced from Overture's
  `divisions.division_area` (`subtype IN ('locality','microhood','neighborhood')`).
  Per author-context.md Overture is the authoring default and
  `divisions.division_area` is the structural equivalent. Persisting,
  low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  Inventory's OSM-tag axis lists `boundary=administrative` for districts but the fixture uses Overture `divisions.division_area`. Either change the inventory row's OSM-tag column to "—" (relying on the Overture-theme column), or document that the two are interchangeable for inventory coverage purposes. Editing `inventory.md` is outside the per-task authority boundary.

### 3. Changes applied this run

#### Unilateral edits
- (none — task is calibrated; grader, tolerances, instruction, and inputs are all sound, so no edit is warranted)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — Inventory geometry_type axis ("Polygon, Point") omits the fixture's LineString + MultiPolygon layers.
- HR-002 — inventory-mismatch — Inventory OSM-tag axis (`boundary=administrative`) disagrees with the fixture's Overture `divisions.division_area` provenance.

#### Tests run
- grader on reference: 1.0 (29/29 subchecks pass) — `cd benchmark/eval && uv run python ../tasks/dd-l1-vienna-gpkg-manifest/grade.py ../tasks/dd-l1-vienna-gpkg-manifest/reference/solution/outputs`
- pytest: not-run (no unilateral edits made; pytest gate only required after edits per evaluator prompt Step 4)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row at `benchmark/authoring/inventory.md:30`, an L1 data-discovery task: junior planner Lukas Hofer (Vienna MA 18) inherits a multi-layer GPKG (EPSG:31287, MGI / Austria Lambert) from a retired colleague and must emit a one-page manifest — one record per layer with `layer_name`, `crs`, `geometry_type`, `feature_count`, `bbox` in the layer's own CRS. Probes GPKG multi-layer enumeration plus per-layer schema introspection: open a multi-layer container with a schema-aware tool (pyogrio / fiona / ogrinfo / DuckDB-spatial) rather than treating it as single-layer, and report metadata as declared (no reprojection). The bundled fixture has seven layers (primary trio districts / parks / schools plus four auxiliary cuts: waterbodies, cafes, supermarkets, cycleway_segments), so an agent that pattern-matches the trio without opening the file yields a partial manifest (anchored at 0.414 by broken_partial_layers).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 0a7e5e1 | initial-authoring | Initial task: task.json, grade.py, metadata.yaml, README.md, reference generate.py + outputs/, _prepare input + vienna_planning.gpkg, _make_brokens + three broken_* outputs, IMPLEMENTATION_NOTES.md | (initial) |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json`; no behavioural change | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | 1710715 | prompt-change | Appended "Output schema:" bullet to `instruction` listing five record keys + types | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | 9e79176 | prompt-change | Refactored schema bullets into a fluent paragraph (same keys, prose form) | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | b04e9f0 | prompt-change | Dropped "multi-layer" qualifier from the persona sentence | Commit msg: "strip deducible information from DD task instructions" |
| 2026-05-17 | 88530c5 | prompt-change | Replaced procedural "Walk every layer ..." with terse "Catalog the contents and give me one record per layer."; "in the layer's own CRS" tightened to "native CRS" in schema sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md, data/ → inputs/, reference/{generate.py,outputs/} → reference/solution/, tests/ → reference/failures/, image* → assets/; path constants in grade.py/generate.py/_make_brokens.py/_prepare.py and task.json input URL adjusted | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | a80e59e | docs-change | First evaluator-review block + coverage.yaml + audit/status.json | Commit msg: "Re-evaluate dd-l1-vienna-gpkg-manifest: calibrated; 2 low-severity inventory-mismatch flags" |
| 2026-05-27 | 82770e2 | docs-change | Second evaluator-review block; coverage.yaml + status.json refreshed | Commit msg: "Re-evaluate dd-l1-vienna-gpkg-manifest: calibrated; 2 low-severity inventory-mismatch flags" |
| 2026-05-28 | 622342b | docs-change | Repo-wide: dropped unused `prompt_version` from this task's metadata.yaml; introduced task-content `version` field machinery to runtime/UI but task.json here untouched | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 4ccd7f1 | docs-change | Third evaluator-review block; coverage.yaml + status.json refreshed | Commit msg: "Re-evaluate dd-l1-vienna-gpkg-manifest: calibrated; 2 low-severity inventory-mismatch flags persist" |

Note: directory-level `git log --follow` continues to omit pre-folder-reorg commits (paths lived under `benchmark/eval/tasks/...`); cross-checked via `git log --all --grep='dd-l1-vienna-gpkg-manifest'` and slug-scan. No design-affecting commit has landed since 88530c5, so the cutoff is unchanged from prior reviews.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47+00:00 (commit 88530c5, class: prompt-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled | current (no score) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:49:41Z | 1.0 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:01:40Z | 1.0 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T10:57:54Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:27:21Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-28T23:56:05Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:59:20Z | 1.0 | done | current |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T20:17:58Z | 1.0 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:14:46Z | 1.0 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:35:50Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T02:02:44Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:46:50Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T20:54:29Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:25:34Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:22:35Z | 1.0 | done | current |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:18:31Z | 1.0 | done | current |
| (22 earlier runs) | mixed | pre-cutoff | mixed | mixed | stale (pre-cutoff) |

Stale-run footnote: pre-cutoff runs span 2026-05-12 → 2026-05-17 across haiku / sonnet / opus / gemma / hy3 / deepseek adapters against earlier procedurally-verbose instruction wordings; they describe prior task states, not the current one. The single cancelled run on 2026-06-06 has no score and contributes no evidence.

#### Verdict
**calibrated**

Fifteen current runs across four agent families (Anthropic Claude Opus 4-6/4-7, DeepSeek v4 Flash, DeepSeek v4 Pro, Google Gemma-4-26B) all score 1.0 on the post-strip instruction. For an L1 single-op bundled task this is the calibration target. The new runs since the prior review (deepseek-v4-pro on 2026-05-29, gemma-detailed on 2026-06-06) reproduce the result against the same prompt and grader. The instruction (`task.json:14`) carries no procedural gifts — no tool name, no CRS, no layer set, no recipe. The five-key output schema sentence is the necessary redundant contract that `grade.py:27` requires by exact key name; stripping it would break the prompt↔grader contract. The bbox 1 m tolerance (`grade.py:25`, `metadata.yaml:13`) absorbs pyogrio / fiona float drift while still catching unit / CRS-confusion errors (degree-vs-metre slip ≈ 6×10⁵ off, whole-file-union ≈ 10³ m off). Broken sets in `reference/failures/broken_*/` still anchor the lower end of the scoring range at 0.000 / 0.4138 / 0.5172.

CRS/format consistency (Step 2c-CRS): reference output CRS (`EPSG:31287`), `expected_outputs[].crs` (`EPSG:31287`), and README's stated output CRS (EPSG:31287 metres) all agree. Grader compares CRS strings and bbox numbers in the native CRS with no reprojection on either side. Consistent.

#### Specific findings
- Instruction has converged on a clean, gift-free form. No further stripping warranted; removing the schema paragraph would break the prompt↔grader contract.
- README referenced the stale pre-reorg input path `data/vienna_planning.gpkg` (actual location since commit 29a9ae3 is `inputs/vienna_planning.gpkg`). Fixed unilaterally as docs-change; no version bump required.
- `task.json` was missing `analyst_notes`. Authored per the Step 4 schema (description + 4-step approach + 7 pitfalls). Human-facing UI metadata only, not seen by the agent at run time, so no version bump required per the bump-not-required list.
- `task.json` does not yet carry the new `version` field. Per Step 4, tasks without it are implicitly v1; the next *meaningful* (prompt / grader / inputs / tolerances) edit must bump to v2. The README path fix and `analyst_notes` authoring are both on the no-bump list, so v1 is preserved this pass.
- Inventory `geometry_type` axis (`inventory.md:44`) lists "Polygon, Point" but the fixture and grader also exercise LineString (`cycleway_segments`) and MultiPolygon (`parks`). Author block + three prior evaluators flagged this as a deliberate realism extension. Persisting, low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" -->
  Inventory `geometry_type` lists "Polygon, Point" but the fixture (and grader) also exercise LineString (`cycleway_segments`) and MultiPolygon (`parks`). Either extend the inventory row's geometry-type axis, or accept the documented extension as-is. Editing `inventory.md` is outside the per-task authority boundary.
- Inventory OSM-tag axis (`inventory.md:48`) lists `boundary=administrative` for districts but the fixture is sliced from Overture's `divisions.division_area` (`subtype IN ('locality','microhood','neighborhood')`). Per author-context.md Overture is the authoring default and `divisions.division_area` is the structural equivalent. Persisting, low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  Inventory's OSM-tag axis lists `boundary=administrative` for districts but the fixture uses Overture `divisions.division_area`. Either change the inventory OSM-tag column to "—" (relying on the Overture-theme column), or document that the two are interchangeable. Editing `inventory.md` is outside the per-task authority boundary.

### 3. Changes applied this run

#### Unilateral edits
- `README.md`: corrected stale input path `data/vienna_planning.gpkg` → `inputs/vienna_planning.gpkg` (left over from the 2026-05-26 folder reorg). Re-grade on reference: 1.0 (29/29). Reason: docs hygiene; the README pointed readers at a non-existent path.
- `task.json`: authored `analyst_notes` (description + 4-step approach + 7 pitfalls covering the multi-layer gotcha, the partial-trio shortcut, silent reprojection, whole-file-union bbox, geom-type-from-first-feature, non-canonical CRS string, and wrong output container). Re-grade on reference: 1.0 (29/29). Reason: field was missing; Step 4 requires authoring when absent. No version bump (analyst_notes is human-facing only, on the bump-not-required list).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — Inventory geometry_type axis ("Polygon, Point") omits the fixture's LineString + MultiPolygon layers.
- HR-002 — inventory-mismatch — Inventory OSM-tag axis (`boundary=administrative`) disagrees with the fixture's Overture `divisions.division_area` provenance.

#### Tests run
- grader on reference: 1.0 (29/29 subchecks pass) — `cd benchmark/eval && uv run python ../tasks/dd-l1-vienna-gpkg-manifest/grade.py ../tasks/dd-l1-vienna-gpkg-manifest/reference/solution/outputs`
- pytest: pass (41 passed, 1 warning) — `cd benchmark/eval && uv run pytest`

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Old Gate-2 per-record shape checks (`layer_name`/`crs`/`geometry_type`
  are strings, `feature_count` is int, `bbox` is list of 4 numbers) are
  now absorbed into defensive coercion inside the existing per-layer
  CRS / geom-type / count / bbox subchecks via new `_coerce_int` /
  `_coerce_bbox` helpers. A wrong-typed field now costs the relevant
  per-layer subcheck instead of zeroing the score; dict-shaped bboxes
  with xmin/ymin/xmax/ymax-style keys are recovered.
- The `_record_shape_ok` helper was removed (no longer needed).
- No new subchecks added; subcheck count unchanged at 29
  (1 layers_complete + 4 × 7 layers).

### Verification
- Reference solution re-graded: 1.0 (29/29 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Per the inventory row at `benchmark/authoring/inventory.md:30`, an L1 data-discovery task: junior planner Lukas Hofer (Vienna MA 18) inherits a multi-layer GPKG (EPSG:31287, MGI / Austria Lambert) from a retired colleague and must emit a one-page manifest with one record per layer (`layer_name`, `crs`, `geometry_type`, `feature_count`, `bbox` in the layer's own CRS). Probes GPKG multi-layer enumeration plus per-layer schema introspection: open the container with a schema-aware tool and report metadata as declared, with no reprojection. The bundled fixture holds seven layers (primary trio districts / parks / schools plus four auxiliary cuts: waterbodies, cafes, supermarkets, cycleway_segments), so an agent that pattern-matches the trio without opening the file yields a recognisably partial manifest.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 0a7e5e1 | initial-authoring | Initial task: task.json, grade.py, metadata.yaml, README.md, reference generate.py + outputs/, _prepare input + vienna_planning.gpkg, _make_brokens + three broken_* outputs, IMPLEMENTATION_NOTES.md | (initial) |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json`; no behavioural change | Commit msg: "add structured tags to all 36 task.json files" |
| 2026-05-13 | 1710715 | prompt-change | Appended "Output schema:" bullet to `instruction` listing five record keys + types | Commit msg: "declare exact output schema in prompts to match graders" |
| 2026-05-13 | 9e79176 | prompt-change | Refactored schema bullets into a fluent paragraph (same keys, prose form) | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | b04e9f0 | prompt-change | Dropped "multi-layer" qualifier from the persona sentence | Commit msg: "strip deducible information from DD task instructions" |
| 2026-05-17 | 88530c5 | prompt-change | Replaced procedural "Walk every layer ..." with "Catalog the contents and give me one record per layer."; "own CRS" tightened to "native CRS" in the schema sentence | Commit msg: "Remove CRS, operation, and encoding nudges from 5 data-discovery task prompts" |
| 2026-05-26 | 29a9ae3 | docs-change | Folder reorg (IMPLEMENTATION_NOTES.md -> audit/AUTHORING_HISTORY.md, data/ -> inputs/, reference layout, assets/); path constants adjusted | Commit msg: "Reorganize task folder layout" |
| 2026-05-26 | a80e59e | docs-change | First evaluator-review block + coverage.yaml + audit/status.json | Commit msg: "Re-evaluate ... calibrated; 2 low-severity inventory-mismatch flags" |
| 2026-05-27 | 82770e2 | docs-change | Second evaluator-review block; coverage.yaml + status.json refreshed | Commit msg: "Re-evaluate ... calibrated; 2 low-severity inventory-mismatch flags" |
| 2026-05-28 | 622342b | docs-change | Repo-wide: dropped unused `prompt_version` from metadata.yaml; introduced task-content `version` machinery (task.json here untouched) | Commit msg: "Add task content versioning; drop unused prompt_version" |
| 2026-05-28 | 4ccd7f1 | docs-change | Third evaluator-review block; coverage.yaml + status.json refreshed | Commit msg: "Re-evaluate ... calibrated; 2 low-severity inventory-mismatch flags persist" |
| 2026-06-06 | 6765e64 | docs-change | Fourth evaluator-review block; fixed stale README input path; authored `analyst_notes` in task.json | Commit msg: "Re-evaluate dd-l1-vienna-gpkg-manifest: calibrated; authored analyst_notes, fixed stale README path" |
| 2026-06-06 | 363aed2 | grader-change | Dropped `Gate("structural_correctness", ...)`; per-record type-shape checks absorbed into `_coerce_int` / `_coerce_bbox` defensive coercion inside the existing subchecks; subcheck count unchanged at 29 | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks ... shape-recoverable inputs ... cost a point each instead of collapsing the score" |
| 2026-06-07 | 632ad1a | grader-change | Added `weight=3.0` to `layers_complete` and every per-layer `count_correct` / `bbox_correct` subcheck; `crs_correct` / `geom_type_correct` stay weight 1. Total weight now 59 (was 29 equal points) | Commit msg: "Weight data-content subchecks 3x in dd graders ... so a schema-clean but data-wrong submission scores visibly lower than a data-correct one with minor schema drift" |

Note: directory-level `git log --follow` continues to omit pre-folder-reorg commits (paths lived under `benchmark/eval/tasks/...`); cross-checked via slug-grep of commit messages. The 363aed2 Gate-2 removal is documented in the "Manual cleanup 2026-06-06" block above; the 632ad1a 3x-weighting commit carried no per-task AUTHORING_HISTORY entry, so this change log is its first per-task documentation. Neither grader commit bumped `task.json > version` (still implicitly v1); the run-validity analysis below therefore relies on the timestamp cutoff.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:28:21+00:00 (commit 632ad1a, class: grader-change)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:23:53Z | 1.0 | done | current (suite ec540aa includes 632ad1a) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:15:45Z | 1.0 | done | current (suite 6510297 includes 632ad1a) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T13:37:32Z | 1.0 | done | stale (pre-weighting; suite 06fd6c0) — output re-graded 1.0 (29/29) under the current grader |
| (38 earlier runs) | mixed | pre-cutoff | mixed | mixed | stale (pre-cutoff) |

Stale-run footnote: the 16 runs the 2026-06-06 review classed current (Claude Opus 4-6/4-7, DeepSeek v4 Flash/Pro, Gemma-4-26B; all 1.0) predate the 632ad1a weighting commit. The weighting change cannot alter a 1.0 score (all subchecks passed, so weights cancel), and the instruction and inputs are unchanged since 88530c5 (2026-05-17), so their outputs remain valid submissions; the newest of them (run-20260607-112430Z, gemma) was re-graded with the current grader and still scores 1.0 (29/29). Earlier pre-2026-05-17 runs were against more verbose instruction wordings and stay stale.

#### Verdict
**calibrated**

Two strictly-current runs (DeepSeek v4 Flash under both the basic and gis_detailed harness prompts) score 1.0 against the weighted grader, and a third post-Gate-2-drop run (Gemma-4-26B, started 5 h before the weighting commit) re-grades to 1.0 (29/29) under the current grader, giving cross-family evidence under the exact current scoring code. Both grader changes since the last review are score-shape refactors, not contract changes: the Gate-2 drop converts type-shape failures from hard zeros into per-subcheck deductions, and the 3x weighting re-balances data-content vs. schema subchecks (total weight 29 -> 59); neither alters what a correct submission looks like, and a 1.0 stays 1.0 under both. Per-output inspection of the current runs confirms 7-record manifests, exact layer-set match, all-EPSG:31287 CRS strings, correct geometry types (case differences absorbed by the grader's case-insensitive match at `grade.py:96-99`), correct counts, and bbox deltas inside the 1 m tolerance. The broken sets re-anchor under the weighted grader at 0.000 / 0.4068 / 0.5254 (previously 0.000 / 0.4138 / 0.5172), all still inside their `expected_score_range` bands, so the discrimination structure is intact and slightly sharpened in the intended direction (data-wrong submissions now score relatively lower per the 632ad1a rationale).

CRS/format consistency (Step 2c-CRS): reference output CRS (`EPSG:31287`), `expected_outputs[].crs` (`EPSG:31287`), and the README's stated output CRS (EPSG:31287 metres) all agree. The grader compares CRS strings and bbox numbers in the native CRS with no reprojection on either side. Consistent.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `manifest.json`, top-level JSON list | instruction ("Output manifest.json — a JSON list of these records") | stated |
| five exact record keys | instruction, schema paragraph | stated |
| `crs` in `EPSG:NNNN` form | instruction ("a string in `EPSG:NNNN` form") | stated |
| native geometry type per layer | instruction ("matching the layer's native type") + GPKG layer schema | stated |
| `feature_count` integer equality | instruction (integer) + the file itself | stated / inferable |
| `bbox` `[xmin, ymin, xmax, ymax]` in native CRS | instruction, schema paragraph | stated |
| complete layer set (7 layers) | the input file itself (open and enumerate) | inferable — deliberately unstated, this is the gotcha |
| bbox 1 m componentwise tolerance | grader-internal | inferable (standard drift margin) |
| 3x weighting of layers_complete / count / bbox | grader-internal scoring shape | not needed by the agent |

Factual claims checked: input referenced as "a GPKG (vienna_planning)" matches `inputs/vienna_planning.gpkg`; output filename `manifest.json` matches `expected_outputs[]`; the five key names and types match the reference output schema exactly. No inaccurate claims found.

#### Reference faithfulness
`reference/solution/generate.py` enumerates all layers via `pyogrio.list_layers`, reads declared CRS / geometry type / feature count from `pyogrio.read_info`, and computes each layer's bbox from its own features in the native CRS with no reprojection — exactly what the instruction asks. The two extras (alphabetical layer ordering, bbox rounding to 2 decimals) are determinism measures explicitly documented in the module docstring; the grader is order-insensitive and the 1 m tolerance dwarfs the 1 cm rounding, so neither penalises a non-rounding, non-sorting agent. Faithful.

#### Specific findings
- The 632ad1a weighting commit staled `metadata.yaml > broken_solutions > measured_score` (0.4138 / 0.5172 were the unweighted values) and the README's failure-mode arithmetic ("12 / 29", scores 0.414 / 0.517). Re-measured under the current grader: partial_layers 0.4068, wrong_crs_bbox 0.5254 (both inside their expected ranges). Fixed unilaterally (measured_score refresh + README docs-change; no version bump required per the bump-not-required list).
- Neither 363aed2 nor 632ad1a bumped `task.json > version` despite being grader-changes. Both are score-shape refactors that leave a correct submission's 1.0 unchanged, the eval UI's de-emphasis relies on version only as a secondary signal, and the timestamp cutoff fully covers run-validity here, so no retroactive bump is made; recording for transparency.
- `analyst_notes` (authored 2026-06-06) still matches the task: the grader changes did not alter what the agent is tested on, so no refresh needed.
- Instruction remains in its converged gift-free form; no further stripping warranted (the schema paragraph is the necessary prompt-grader contract for the exact key names at `grade.py:31`).
- Inventory `geometry_type` axis (`inventory.md`) lists "Polygon, Point" but the fixture and grader also exercise LineString (`cycleway_segments`) and MultiPolygon (`parks`). Author block + four prior evaluators flagged this as a deliberate realism extension. Persisting, low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" -->
  Inventory `geometry_type` lists "Polygon, Point" but the fixture (and grader) also exercise LineString (`cycleway_segments`) and MultiPolygon (`parks`). Either extend the inventory row's geometry-type axis, or accept the documented extension as-is. Editing `inventory.md` is outside the per-task authority boundary.
- Inventory OSM-tag axis lists `boundary=administrative` for districts but the fixture is sliced from Overture's `divisions.division_area`. Per author-context.md Overture is the authoring default and `divisions.division_area` is the structural equivalent. Persisting, low-severity inventory mismatch.
  <!-- HUMAN-REVIEW id="HR-002" category="inventory-mismatch" severity="low" -->
  Inventory's OSM-tag axis lists `boundary=administrative` for districts but the fixture uses Overture `divisions.division_area`. Either change the inventory OSM-tag column to "—" (relying on the Overture-theme column), or document that the two are interchangeable. Editing `inventory.md` is outside the per-task authority boundary.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` for the weighted grader (partial_layers 0.4138 -> 0.4068, wrong_crs_bbox 0.5172 -> 0.5254) and updated the score-derivation prose in both descriptions to the weighted arithmetic. Re-grade on reference: 1.0 (29/29). Reason: the 632ad1a 3x-weighting commit staled the recorded values; both remain inside their expected_score_range bands. No version bump (measured_score refresh is on the bump-not-required list; no tolerance changed).
- `README.md`: updated the three broken-set scores (0.414 -> 0.407, 0.517 -> 0.525) and the failure-mode subcheck arithmetic to the weighted totals (also corrected the pre-existing "1 + 4 = 5 / 29" miscount for the single-layer mode). Re-grade on reference: 1.0 (29/29). Reason: docs staled by the weighting commit.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — Inventory geometry_type axis ("Polygon, Point") omits the fixture's LineString + MultiPolygon layers.
- HR-002 — inventory-mismatch — Inventory OSM-tag axis (`boundary=administrative`) disagrees with the fixture's Overture `divisions.division_area` provenance.

#### Tests run
- grader on reference: 1.0 (29/29 subchecks pass) — `cd benchmark/eval && uv run python ../tasks/dd-l1-vienna-gpkg-manifest/grade.py ../tasks/dd-l1-vienna-gpkg-manifest/reference/solution/outputs`
- broken-set re-grade: broken_wrong_format 0.000, broken_partial_layers 0.4068, broken_wrong_crs_bbox 0.5254 (recorded in metadata.yaml)
- re-grade of recent run outputs under current grader: run-20260607-112430Z, run-20260608-074701Z, run-20260609-084636Z all 1.0 (29/29)
- pytest: pass (41 passed, 1 warning)

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Summary
**Recalibrated subcheck weights** to reflect error severity, replacing the blunt repo-wide 2026-06-07 "3x data-content" weighting (632ad1a). That commit weighted `layers_complete`, `count_correct`, and `bbox_correct` at 3.0 while leaving `crs_correct` and `geom_type_correct` at 1.0 — an unprincipled split that treated CRS and geometry-type as cosmetic when, for a metadata-manifest task, all four declared-metadata fields are equally the substance of the deliverable. Grading-only change; no `task.json > version` bump.

### Reasoning
The central skill this DATA-DELIVERY task probes is treating the GPKG as a **multi-layer container** and enumerating every layer (the #1 expected weak-agent failure is partial enumeration). The set-membership check `layers_complete` is therefore the single most central subcheck and is weighted highest (4.0). The four per-layer metadata fields (`crs`, `geometry_type`, `feature_count`, `bbox`) are all "read a declared field off the layer schema" — equally central, equally the content of the manifest — so they are equalised at weight 1.0 each. There is no principled basis for the old count/bbox-vs-crs/geom 3:1 split; CRS confusion (silent reprojection) is itself a flagged central pitfall (failure mode #2), so under-weighting `crs_correct` was the core miscalibration. `layers_complete` at 4 stays clearly above any single field but well below the collective weight of the seven layers' content (4 vs 56), so missing one layer's metadata never swamps the completeness signal and vice versa.

### Weight changes
| Subcheck | Old | New |
|---|---|---|
| `layers_complete` | 3.0 | 4.0 |
| per-layer `count_correct` (×7) | 3.0 | 1.0 |
| per-layer `bbox_correct` (×7) | 3.0 | 1.0 |
| per-layer `crs_correct` (×7) | 1.0 | 1.0 (unchanged) |
| per-layer `geom_type_correct` (×7) | 1.0 | 1.0 (unchanged) |

Total weight 59 -> 32 (= 4 + 7×4). Subcheck count unchanged at 29.

### Broken scores before -> after
| Broken | Before | After | Severity note |
|---|---|---|---|
| wrong_format | 0.000 | 0.000 | Gate failure (CSV body); unaffected by weights — most severe. |
| partial_layers | 0.4068 | 0.3750 | Missed 4 of 7 layers — fundamental multi-layer misread; correctly the lowest non-zero score. Still inside expected_score_range [0.35, 0.50]. |
| wrong_crs_bbox | 0.5254 | 0.5625 | All 7 layers + counts + geom-types correct, but systematically reprojected (CRS + bbox wrong on every layer). Recovered-but-real error; correctly above partial_layers. Still inside [0.45, 0.60]. |

Ordering check: monotone and defensible — wrong_format (0.000) < partial_layers (0.375) < wrong_crs_bbox (0.5625) < reference (1.000). The recalibration sharpened the intended gradient: equalising the four metadata fields means a systematic single-field error (e.g. non-canonical CRS string on all layers, failure mode #7) now models to ~0.78 instead of the old ~0.88 (no longer near-cosmetic), while a one-layer single-field slip stays near the top (~0.97) regardless of which of the four fields slipped. No disjoint-failure inversion: wrong_crs_bbox's failures are a strict superset relationship with crs-only, and it remains above partial_layers because enumerating all layers correctly is the harder, more central achievement.

### Prior-run re-grade summary
All 42 prior run directories under `benchmark/eval/runs/*/dd-l1-vienna-gpkg-manifest/` were re-graded against the new weights. Every run resolves to either 1.0 (all subchecks pass) or 0.0 (gate failure / empty-or-missing output); none land in the partial-credit band, so the weight change moves no prior-run score. The three current-version runs (run-20260607-112430Z, run-20260608-074701Z, run-20260609-084636Z) all stay 1.0 (29/29). No significant shifts.

### Specific findings
- HR-001 and HR-002 are inventory-mismatch flags, NOT weighting HRs — left in place untouched.
- Reference re-grade: 1.0 (29/29).

### Changes applied this run
#### Unilateral edits
- `grade.py`: recalibrated subcheck weights (table above). Weights only — no check logic, threshold, gate, or subcheck-count change.
- `metadata.yaml`: refreshed `broken_solutions > measured_score` (partial_layers 0.4068 -> 0.375, wrong_crs_bbox 0.5254 -> 0.5625) and rewrote the weight-arithmetic prose in both descriptions to the new totals (weight 59 -> 32). expected_score_range bands unchanged (both brokens still inside). No version bump.
- `README.md`: updated stale broken-set score fractions (0.407 -> 0.375, 0.525 -> 0.5625) and the failure-mode subcheck-weight arithmetic (of 59 -> of 32; single-layer weight 8 -> 4).
- `audit/status.json`: refreshed unilateral_edits / grader_score_after_edits / pytest_status / evaluator_finished_at (see status.json).

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — Inventory geometry_type axis ("Polygon, Point") omits the fixture's LineString + MultiPolygon layers.
- HR-002 — inventory-mismatch — Inventory OSM-tag axis (`boundary=administrative`) disagrees with the fixture's Overture `divisions.division_area` provenance.

#### Tests run
- grader on reference: 1.0 (29/29 subchecks pass) — `cd benchmark/eval && uv run python ../tasks/dd-l1-vienna-gpkg-manifest/grade.py ../tasks/dd-l1-vienna-gpkg-manifest/reference/solution/outputs`
- broken-set re-grade: broken_wrong_format 0.000, broken_partial_layers 0.375, broken_wrong_crs_bbox 0.5625 (recorded in metadata.yaml)
- prior-run re-grade: all 42 run dirs -> 1.0 or 0.0 (none in partial-credit band); no score moved
- pytest: not-run (orchestrator runs the suite)
