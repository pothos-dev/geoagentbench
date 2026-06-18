# Implementation notes — dd-l2-bangkok-multicrs-audit

## Status
completed

## Summary
L2 multi-layer CRS + encoding audit on a hand-crafted Bangkok GPKG
(3 layers, 3 different CRSes, 10000 features total). Reference
walks every layer, reads its declared CRS, geometry type, and feature
count straight from `pyogrio.read_info`, samples a representative
point in the layer's own CRS, and runs a UTF-8↔Latin-1 round-trip
heuristic to flag the two layers whose Thai labels were corrupted by
the contractor's UTF-8→Latin-1→UTF-8 double-decode pipeline.

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.0 (expected range [0.0, 0.0])
  - partial_layers: 0.3125 (expected range [0.25, 0.40])
  - wrong_encoding: 0.875 (expected range [0.80, 0.95])
- Second-run output match: bit-identical (verified via `cp` + `diff -q`
  on `crs_audit.csv`)
- Library tests after task: pass (32/32)

## Failure-mode coverage
- Single-layer enumeration (only opens default first layer):
  broken_partial_layers
- Skipped Latin-1 mojibake heuristic (everything reported as `utf-8`):
  broken_wrong_encoding
- Wrong output format (JSON instead of CSV): broken_wrong_format
- Silent reprojection to EPSG:4326 before introspection: principled —
  per-layer `declared_crs_correct` + `sample_coords_plausible` flip
  for the two non-4326 layers
- Sample coordinates from a different CRS than the declared one:
  principled — per-layer `sample_coords_plausible` subcheck
- Overzealous mojibake-flagging on the clean layer: principled —
  `markets_encoding_correct` subcheck
- Non-canonical CRS strings (`"24047"`, `"Indian 1975 UTM 47N"`):
  principled — case-insensitive `EPSG:NNNN` exact-match subcheck
- Off-by-one feature-count errors: principled — per-layer
  `feature_count_correct` subcheck

## Open issues
- [severity: low] — Bundled fixture is hand-crafted rather than sliced
  from Overture. Justification: the task is intrinsically about a
  defective deliverable (mixed CRSes inside a single GPKG, mojibake
  on Thai-script labels), neither of which Overture nor OSM ships.
  The hand-crafted policy matches `dc-l2-cairo-invalid-dedup`,
  `crs-l2-fiji-antimeridian`, and `fio-l2-cairo-mixedgeom-split`.

## Suggested prompt changes
(none)

## Inventory change proposals
(none — the inventory row's spec is internally consistent and matches
the task as built. Total feature count of 10000 hits the medium-scale
band; geometry mix Polygon/LineString/Point is realised one per layer;
all three named CRSes (`EPSG:24047`, `EPSG:32647`, `EPSG:4326`) appear
exactly once.)

## Library extensions
(none — the audit's primitives are CSV row diffing and a pure-Python
Latin-1 round-trip check, both inline in `grade.py` because the
underlying logic is one-liners and no peer task currently shares it.)

## Runtime
~20 minutes wall-clock for authoring inside the Docker container
(input prep ~10 s, reference ~10 s, grader ~10 s, brokens ~10 s,
manual inspection, documentation, and pytest verification).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
The task was authored 2026-05-08 as the data-discovery L2 case for Bangkok:
a hand-crafted multi-layer GPKG (parcels Polygon EPSG:24047, roads LineString
EPSG:32647, markets Point EPSG:4326, 10000 features total) deliberately
seeded with two encoding-quality defects — mixed CRSes across layers and
UTF-8→Latin-1→UTF-8 mojibake on Thai labels in two layers. The persona
(Krit Suwannarat, Ministry-of-Interior deliverables auditor) needs a CSV
audit sheet with one row per layer giving declared CRS, geometry type,
feature count, a sample (x, y) in the layer's own CRS, and a categorical
encoding flag. The inventory row, the README, and the original
IMPLEMENTATION_NOTES all agree on this framing; the grader was authored
with two gates (format/schema, structural correctness) plus a 16-subcheck
checklist (1 `layers_complete` + 5 per layer for 3 layers).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | f0628d2 | initial-authoring | Initial task (README, data, grader, metadata, reference, brokens, task.json) | (initial) |
| 2026-05-08 | 001e459 | docs-change | Repo-wide split into authoring/ and eval/ subtrees (no task-internal change) | Commit msg: structural reorg |
| 2026-05-13 | a3a8d53 | docs-change | Moved benchmark/eval/tasks/ to benchmark/tasks/ | Commit msg: relocation |
| 2026-05-13 | 8915010 | docs-change | Added image-prompt.md to all 36 task directories | Commit msg: per-task asset add |
| 2026-05-13 | 1b8dda1 | docs-change | Generated image.webp for all 36 task directories | Commit msg: per-task asset add |
| 2026-05-13 | 3c65373 | docs-change | Regenerated all 36 task card images via FLUX schnell | Commit msg: asset refresh |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card images with nano-banana-2 | Commit msg: asset refresh |
| 2026-05-14 | e732929 | prompt-change | Renamed CSV coord columns to `sample_x`/`sample_y` in instruction | Commit msg: models guessed `x`/`y` and lost the grader check |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped deducible info from the instruction (removed CRS-mismatch hint and explicit `utf-8`/`latin1-mojibake` enum mention) | Commit msg: strip deducible info from DD instructions |
| 2026-05-16 | 7c812d6 | prompt-change | Re-added explicit mojibake-detection description and the two label values in the instruction | Commit msg: instruction was too vague after the previous strip; describe mojibake detection and expected output values |
| 2026-05-17 | 88530c5 | prompt-change | Replaced the explicit mojibake description with a neutral "assess text attributes for encoding anomalies" phrasing while keeping the two allowed labels | Commit msg: remove CRS/operation/encoding nudges from 5 DD task prompts |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg (data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES→audit/AUTHORING_HISTORY, image* → assets/); path strings adjusted in grader, generator, broken-maker | Commit msg: reorganize task folder layout |

The three prompt-change commits in May 14-17 trace an explicit
de-gifting trajectory: the original instruction told the agent
the CRSes were mixed, told the agent to output `utf-8` or
`latin1-mojibake`, and named the UTF-8→Latin-1→UTF-8 round-trip
detector. The current instruction names *only* the two allowed
labels (`latin1-mojibake` / `utf-8`) and the output schema —
the agent must figure out from "encoding anomalies" what to look
for. This is consistent with the task-design rule of putting
output-schema language in the prompt but not the detection recipe.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47Z (commit 88530c5, class: prompt-change). The 2026-05-26 reorg commit is path-only and doesn't change behavior.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:18:55Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:23:27Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:26:49Z | 0.875 | done | current |

(Older runs from 2026-05-12 through 2026-05-17 12:54Z are stale: they predate the final prompt-change commit. They were not used as evidence.)

#### Verdict
**calibrated**

Three current runs span a useful capability range. The two stronger
models (Opus, DeepSeek V4 Flash) score a clean 1.00; their CSVs match
the reference layer-for-layer on declared CRS, geometry type, feature
count, sample-coord plausibility, and encoding label. Gemma 4 26B
scores exactly 0.875 by failing both `parcels_encoding_correct` and
`roads_encoding_correct` (it reports every layer as `utf-8`) — i.e. it
realises exactly the documented `broken_wrong_encoding` failure mode
and lands on the expected partial score for it. That is the
"weak-agent skipped the mojibake heuristic" case the grader was
designed to distinguish from the fully-correct case, and the grader
distinguishes it cleanly. No correct-looking output was rejected;
no broken output got full marks.

#### Specific findings
- Grader on reference: 1.00 (16/16 subchecks). Reference output bit-matches the expected layer set and values; both gates pass.
- Pytest: 35/35 pass on `benchmark/eval`.
- Instruction strikes a defensible balance: the two allowed encoding labels are named (so the agent isn't free-styling the categorical), but the detection recipe is left to the agent (no mention of UTF-8/Latin-1 round-trip).
- Plausibility-window sample-coord check is sound: both metric-CRS layers' coordinates land well inside (5e5–8e5, 1.40e6–1.62e6) and the 4326 layer inside (100, 13)–(101, 14). The grader correctly catches the degree-vs-metre slip described in the metadata.
- One minor data-source-tag observation: the inventory row lists `OSM tags: highway=*` and `task.json.tags.themes: ["highway"]`, but the bundled GPKG is hand-crafted (not from OSM). The `roads` layer carries a `highway`-style column to mimic OSM, which justifies the tag at the *feature-schema* level even though the data is synthetic. I'm including `osm_tag_families: [highway]` in `coverage.yaml` consistent with the inventory; not flagging because the inventory row is internally consistent with the README and the metadata note (#1).
- No `data-source-table` issue: `bundled-local` is the canonical slug for hand-crafted bundled fixtures and matches the README, metadata, and inventory.

### 3. Changes applied this run

#### Unilateral edits
- (none) — task is calibrated, grader+reference are at 1.00, and pytest is clean. The instruction has already been progressively de-gifted across three commits and now matches the design rule for DD tasks.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.00 (16/16 subchecks)
- pytest: pass (35/35)

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`f0628d2`) as the data-discovery L2 case for Bangkok: a
hand-crafted multi-layer GPKG (`parcels` Polygon EPSG:24047, `roads` LineString
EPSG:32647, `markets` Point EPSG:4326; 10000 features total) deliberately seeded
with two data-quality defects — mixed CRSes across layers and a
UTF-8→Latin-1→UTF-8 mojibake corruption of the Thai-script labels on two of the
three layers. The persona (Krit Suwannarat, a Ministry-of-Interior deliverables
auditor) needs a one-row-per-layer CSV cite-sheet giving declared CRS, geometry
type, feature count, a sample (x, y) coordinate in the layer's own CRS, and a
categorical encoding flag (`utf-8` / `latin1-mojibake`) so he can reject the
deliverable with each defect cited. The inventory row, the README, and the
author block of this file all agree on this framing. The grader uses two gates
(format/schema validity, structural type-correctness) plus a 16-subcheck
checklist (1 `layers_complete` + 5 per layer × 3 layers).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | f0628d2 | initial-authoring | Initial task (README, data, grader, metadata, reference, brokens, task.json) | (initial) |
| 2026-05-08 | 001e459 | docs-change | Repo-wide split into authoring/ and eval/ subtrees (no task-internal behaviour change) | Commit msg: structural reorg |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: relocation |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` across all 36 task dirs | Commit msg: per-task asset add |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` across all 36 task dirs | Commit msg: per-task asset add |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task card images (FLUX schnell) | Commit msg: asset refresh |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card images (nano-banana-2) | Commit msg: asset refresh |
| 2026-05-14 | e732929 | prompt-change | Renamed the CSV coordinate columns to `sample_x`/`sample_y` in the instruction | Commit msg: models guessed `x`/`y` and lost the grader check |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped deducible info from the instruction (dropped the CRS-mismatch + mojibake-on-every-layer hint and the explicit `utf-8`/`latin1-mojibake` enum) | Commit msg: strip deducible information from DD task instructions |
| 2026-05-16 | 7c812d6 | prompt-change | Re-added an explicit mojibake-detection description and the two allowed label values (instruction had become too vague) | Commit msg: describe mojibake detection and expected output values |
| 2026-05-17 | 88530c5 | prompt-change | Replaced the explicit mojibake recipe with neutral "assess text attributes for encoding anomalies"; dropped the `— do not reproject —` clause for "a sample coordinate from the layer as-is"; kept the two allowed labels | Commit msg: remove CRS/operation/encoding nudges from 5 DD task prompts |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg (data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES→audit/AUTHORING_HISTORY, image*→assets/); path strings adjusted in grader/generator/broken-maker | Commit msg: reorganize task folder layout |
| 2026-05-26 | 7e92284 | docs-change | Prior evaluator review: no unilateral edits (verdict calibrated); wrote coverage.yaml + audit artefacts | Commit msg: Re-evaluate dd-l2-bangkok-multicrs-audit: calibrated; no edits |

The four prompt-change commits (May 14–17) trace a deliberate de-gifting
trajectory verified against the diffs. The 2026-05-08 original told the agent
the CRSes were mixed and the labels were "garbage on every layer except one",
named the two allowed labels, and (after `7c812d6`) named the UTF-8→Latin-1→UTF-8
detector by name. The current instruction (post-`88530c5`) names *only* the two
allowed labels and the output schema; the agent must infer from "encoding
anomalies" what to look for, and "a sample coordinate … as-is" replaces the
explicit "do not reproject" clause. This is consistent with the DD design rule
of keeping output-schema language in the prompt but not the detection recipe.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47Z (commit 88530c5, class: prompt-change). The 2026-05-26 reorg (29a9ae3) and the prior evaluator commit (7e92284) are docs-only and do not invalidate runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:18:55Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:23:27Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T08:26:49Z | 0.875 | done | current |

(All 24 runs from 2026-05-12 through 2026-05-17 06:14Z are stale — they predate the final prompt-change commit 88530c5 — and were not used as evidence.)

#### Verdict
**calibrated**

Three current runs from three distinct model families span a useful capability
range. The two stronger models (Opus, DeepSeek V4 Flash) score a clean 1.00:
their CSVs match the reference layer-for-layer on declared CRS, geometry type,
feature count, sample-coord plausibility, and encoding label (verified by
re-reading all three submission CSVs). Gemma 4 26B scores exactly 0.875 by
failing precisely `parcels_encoding_correct` and `roads_encoding_correct` — it
reports every layer as `utf-8`, realising the documented `broken_wrong_encoding`
failure mode and landing on the expected partial score for it (confirmed against
its `score.json`: gates pass, 14/16 subchecks pass, the two encoding subchecks
flip). No correct-looking output was rejected; no broken output earned full
marks. The grader cleanly separates the "skipped the mojibake heuristic" case
from the fully-correct case.

#### Specific findings
- Grader on reference: 1.00 (16/16 subchecks); both gates pass (re-run this session).
- Pytest: 35/35 pass on `benchmark/eval` (re-run this session).
- Broken solutions re-graded this session: `broken_wrong_format` 0.0, `broken_partial_layers` 0.3125, `broken_wrong_encoding` 0.875 — exactly matching the `measured_score` values declared in `metadata.yaml`; the three ranges remain distinct. No `metadata.yaml` update needed.
- Output-CRS / format consistency (Step 2c-CRS): the deliverable is a CSV audit table with `expected_outputs[].crs: "n/a"` and `format: "csv"`; the reference output is a CSV with no geometry column. The grader does **not** reproject either side — it reads `declared_crs` as a string and checks `sample_x`/`sample_y` against per-CRS plausibility windows. No one-sided reprojection exists. README, reference output, and `expected_outputs[]` all agree (no output CRS, CSV format). No inconsistency.
- Plausibility-window sample-coord check is sound: both metric-CRS layers' coordinates land well inside (5e5–8e5, 1.40e6–1.62e6) and the 4326 layer inside (100, 13)–(101, 14). It catches the degree-vs-metre slip described in the metadata while absorbing benign agent-implementation differences (all three runs picked different representative points yet all passed).
- On the `88530c5` removal of "— do not reproject —": the current "a sample coordinate from the layer as-is" wording, combined with the required `declared_crs` column, still pins the intended behaviour — an agent that reprojects to 4326 before sampling lands outside the metric plausibility window and fails `sample_coords_plausible` for the two metric layers (failure mode #4/#5 in the README). The de-gifting is defensible and the grader still enforces the constraint. Not flagged.
- Data-source / OSM-tag note (carried from prior review, re-confirmed): the inventory lists `OSM tags: highway=*` and `task.json.tags.themes: ["highway"]`, but the GPKG is hand-crafted (not OSM-sourced). The `roads` layer carries a `highway`-style column to mimic OSM, justifying the tag at the feature-schema level. `coverage.yaml` keeps `osm_tag_families: [highway]` consistent with the inventory; `data_sources: [bundled-local]` is correct for a hand-crafted fixture. No contradiction to flag.

### 3. Changes applied this run

#### Unilateral edits
- (none) — task is calibrated, grader+reference at 1.00, pytest clean, all three broken scores match their declared `measured_score`. The instruction has already been progressively de-gifted to match the DD design rule; no gift remains to strip and no tolerance is mis-set.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.00 (16/16 subchecks)
- broken solutions: wrong_format 0.0, partial_layers 0.3125, wrong_encoding 0.875
- pytest: pass (35/35)

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`f0628d2`) as the data-discovery L2 case for Bangkok: a
hand-crafted multi-layer GPKG (`parcels` Polygon EPSG:24047, `roads` LineString
EPSG:32647, `markets` Point EPSG:4326; 10000 features total) deliberately seeded
with two defects — mixed CRSes across layers and a UTF-8→Latin-1→UTF-8 mojibake
corruption of Thai-script labels on two of three layers. The persona (Krit
Suwannarat, Ministry-of-Interior deliverables auditor) needs a one-row-per-layer
CSV cite-sheet with declared CRS, geometry type, feature count, a sample (x, y)
in the layer's own CRS, and a categorical encoding flag (`utf-8` /
`latin1-mojibake`). Inventory row, README, author block, and metadata all agree
on this framing. Grader = two gates (format/schema validity, structural
type-correctness) plus 16 subchecks (1 `layers_complete` + 5 per layer × 3
layers).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | f0628d2 | initial-authoring | Initial task (README, data, grader, metadata, reference, brokens, task.json) | (initial) |
| 2026-05-08 | 001e459 | docs-change | Repo-wide split into authoring/ and eval/ subtrees (no task-internal behaviour change) | Commit msg: structural reorg |
| 2026-05-13 | 284b843 | docs-change | Added structured `tags` dict to all 36 `task.json` files | Commit msg: add structured tags to all 36 task.json files |
| 2026-05-13 | a3a8d53 | docs-change | Moved `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: relocation |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` across all 36 task dirs | Commit msg: per-task asset add |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` across all 36 task dirs | Commit msg: per-task asset add |
| 2026-05-13 | 3c65373 | docs-change | Regenerated task card images (FLUX schnell) | Commit msg: asset refresh |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated task card images (nano-banana-2) | Commit msg: asset refresh |
| 2026-05-14 | e732929 | prompt-change | Renamed the CSV coordinate columns to `sample_x`/`sample_y` in the instruction | Commit msg: models guessed `x`/`y` and lost the grader check |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped deducible info from the instruction (dropped the CRS-mismatch + mojibake-on-every-layer hint and the explicit `utf-8`/`latin1-mojibake` enum) | Commit msg: strip deducible information from DD task instructions |
| 2026-05-16 | 7c812d6 | prompt-change | Re-added an explicit mojibake-detection description and the two allowed label values (instruction had become too vague) | Commit msg: describe mojibake detection and expected output values |
| 2026-05-17 | 88530c5 | prompt-change | Replaced the explicit mojibake recipe with neutral "assess text attributes for encoding anomalies"; dropped the "do not reproject" clause for "a sample coordinate from the layer as-is"; kept the two allowed labels | Commit msg: remove CRS/operation/encoding nudges from 5 DD task prompts |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg (data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES→audit/AUTHORING_HISTORY, image*→assets/); path strings adjusted in grader/generator/broken-maker | Commit msg: reorganize task folder layout |
| 2026-05-26 | 7e92284 | docs-change | Prior evaluator review: no unilateral edits (verdict calibrated); wrote `coverage.yaml` + audit artefacts | Commit msg: Re-evaluate dd-l2-bangkok-multicrs-audit: calibrated; no edits |
| 2026-05-27 | e218d35 | docs-change | Second evaluator review: no unilateral edits (verdict calibrated); refreshed `coverage.yaml` + audit artefacts | Commit msg: Re-evaluate dd-l2-bangkok-multicrs-audit: calibrated; no edits |
| 2026-05-28 | 622342b | docs-change | Repo-wide: dropped unused `prompt_version` field from this task's `metadata.yaml`; introduced the `task.json.version` versioning scheme (this task has no explicit field yet → implicit v1) | Commit msg: Add task content versioning; drop unused prompt_version |

The four prompt-change commits (May 14–17) trace a deliberate de-gifting
trajectory verified against the diffs. The 2026-05-08 original told the agent
the CRSes were mixed and the labels were "garbage on every layer except one",
named the two allowed labels, and (after `7c812d6`) named the
UTF-8→Latin-1→UTF-8 detector by name. The current instruction (post-`88530c5`)
names *only* the two allowed labels and the output schema; the agent must infer
from "encoding anomalies" what to look for, and "a sample coordinate … as-is"
replaces the explicit "do not reproject" clause. Consistent with the DD design
rule of keeping output-schema language in the prompt but not the detection
recipe.

The 2026-05-28 versioning commit (`622342b`) is repo-wide bookkeeping: it
removed the orphan `prompt_version: 2026-05-08-a` line from `metadata.yaml` and
added the new `task.json.version` semantic — tasks without the field are
implicitly v1. No behavioural change to this task's prompt, grader, or inputs.
Classed `docs-change` for cutoff purposes.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47Z (commit `88530c5`,
  class: prompt-change). The 2026-05-26 reorg (`29a9ae3`), the two prior
  evaluator commits (`7e92284`, `e218d35`), and the 2026-05-28 versioning
  commit (`622342b`) are docs-only and do not invalidate runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic (claude-opus-4-6) | 2026-05-17T13:18:55Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:23:27Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic (google/gemma-4-26b-a4b-it) | 2026-05-26T08:26:49Z | 0.875 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:55:07Z | 1.00 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:48:16Z | 1.00 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:03:29Z | 1.00 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:38:07Z | 0.875 | done | current |

(All 24 runs from 2026-05-12 through 2026-05-17 06:14Z are stale — they
predate `88530c5` — and were not used as evidence.)

#### Verdict
**calibrated**

Seven current runs across three model families (Claude Opus 4-6 / 4-7,
DeepSeek V4 Flash, Gemma 4 26B A4B IT) span a useful capability range and
remain internally consistent. Both Opus runs at the new 4-7 model continue
to score 1.00; the Gemma family produces a bimodal {0.875, 1.00} pattern —
when it skips the mojibake heuristic it lands exactly on the documented
`broken_wrong_encoding` partial score, when it executes the heuristic
(run-20260527-2321Z) it scores 1.00. That's a clean per-attempt variance
inside one model family, not a task miscalibration: the grader still
distinguishes the "skipped the mojibake heuristic" failure from the
fully-correct case at the same score boundary it was authored to. The
sample-coord plausibility windows accept all four metric-CRS samples
(657421.52, 1509162.37) / (656835.69, 1509487.00) / (657706.46, 1509274.70)
from the Opus and Gemma runs as well as the reference (657706.46,
1509274.70) / (657156.99, 1509488.92); the 4326 layer's (100.4533,
13.655) lands cleanly inside (100,101)×(13,14). No correct-looking output
was rejected; no broken output earned full marks.

#### Specific findings
- Grader on reference: 1.00 (16/16 subchecks); both gates pass (re-run this session).
- Pytest: 41/41 pass on `benchmark/eval` (re-run this session; the test count grew from 35 to 41 since the prior review, all incremental additions in `geo_grading`).
- Broken solutions re-graded this session: `broken_wrong_format` 0.0, `broken_partial_layers` 0.3125 (5/16), `broken_wrong_encoding` 0.875 (14/16) — matching the declared `measured_score` values in `metadata.yaml`. The three ranges remain distinct. No `metadata.yaml` update needed.
- Output-CRS / format consistency (Step 2c-CRS): deliverable is a CSV audit table with `expected_outputs[].crs: "n/a"` and `format: "csv"`; reference output is a CSV with no geometry column. Grader does **not** reproject either side — it reads `declared_crs` as a string and checks `sample_x`/`sample_y` against per-CRS plausibility windows. No one-sided reprojection exists. README, reference output, and `expected_outputs[]` all agree. No inconsistency.
- Gemma-family bimodality: looking across the three Gemma-26B current runs (2026-05-26, -27, -28), two reported every layer as `utf-8` (the documented partial-score failure) and one correctly reported `latin1-mojibake` on parcels+roads. This is per-attempt variance under temperature, not evidence of grader/prompt drift — the same prompt, the same grader, three runs, two distinct outcomes inside one model family. Calibration is not affected.
- Versioning field: `task.json` does not yet carry an explicit `version` integer. Per `622342b`'s policy this is implicit v1; the next unilateral edit by an evaluator would write `version: 2`. No unilateral edit applied this run, so no bump owed.
- Data-source / OSM-tag note (carried from prior reviews): inventory lists `OSM tags: highway=*` and `task.json.tags.themes: ["highway"]`, but the GPKG is hand-crafted. The `roads` layer carries a `highway`-style column to mimic OSM, justifying the tag at the feature-schema level. `coverage.yaml` keeps `osm_tag_families: [highway]` consistent with the inventory; `data_sources: [bundled-local]` is correct for a hand-crafted fixture. No contradiction to flag.

### 3. Changes applied this run

#### Unilateral edits
- (none) — task remains calibrated across an expanded evidence base (now 7 current runs, three model families). Grader+reference at 1.00, pytest clean, broken-solution scores match declared. The instruction has already been progressively de-gifted to match the DD design rule; no gift remains to strip and no tolerance is mis-set. No `task.json.version` bump owed (no unilateral edit triggered the requirement).

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.00 (16/16 subchecks)
- broken solutions: wrong_format 0.0, partial_layers 0.3125, wrong_encoding 0.875
- pytest: pass (41/41)

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`f0628d2`) as the data-discovery L2 case for Bangkok: a
hand-crafted multi-layer GPKG (`parcels` Polygon EPSG:24047, `roads` LineString
EPSG:32647, `markets` Point EPSG:4326; 10000 features total) seeded with two
defects — mixed CRSes across layers and a UTF-8→Latin-1→UTF-8 mojibake
corruption of Thai-script labels on two of three layers. Persona Krit
Suwannarat (Ministry-of-Interior deliverables auditor) needs a one-row-per-layer
CSV cite-sheet with declared CRS, geometry type, feature count, sample (x, y) in
the layer's own CRS, and a categorical encoding flag (`utf-8` /
`latin1-mojibake`). Grader = two gates (format/schema validity, structural
type-correctness) plus 16 subchecks (1 `layers_complete` + 5 per layer × 3
layers).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | f0628d2 | initial-authoring | Initial task (README, data, grader, metadata, reference, brokens, task.json) | (initial) |
| 2026-05-14 | e732929 | prompt-change | Renamed CSV coord columns to `sample_x`/`sample_y` in instruction | Commit msg: models guessed `x`/`y` and lost the grader check |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped deducible info from the instruction (dropped CRS-mismatch + per-layer mojibake hint and the explicit `utf-8`/`latin1-mojibake` enum) | Commit msg: strip deducible information from DD task instructions |
| 2026-05-16 | 7c812d6 | prompt-change | Re-added explicit mojibake-detection description and the two allowed label values (instruction had become too vague) | Commit msg: describe mojibake detection and expected output values |
| 2026-05-17 | 88530c5 | prompt-change | Replaced explicit mojibake recipe with neutral "assess text attributes for encoding anomalies"; dropped "do not reproject" clause for "a sample coordinate from the layer as-is"; kept the two allowed labels | Commit msg: remove CRS/operation/encoding nudges from 5 DD task prompts |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg (data/→inputs/, reference/→reference/solution/, tests/→reference/failures/, IMPLEMENTATION_NOTES→audit/AUTHORING_HISTORY, image*→assets/); path strings adjusted in grader/generator/broken-maker | Commit msg: reorganize task folder layout |
| 2026-05-26 | 7e92284 | docs-change | First evaluator review: no edits, verdict calibrated | Commit msg: Re-evaluate dd-l2-bangkok-multicrs-audit: calibrated; no edits |
| 2026-05-27 | e218d35 | docs-change | Second evaluator review: no edits, verdict calibrated | Commit msg: Re-evaluate dd-l2-bangkok-multicrs-audit: calibrated; no edits |
| 2026-05-28 | 622342b | docs-change | Repo-wide: dropped unused `prompt_version` from metadata, introduced `task.json.version` (this task implicit v1) | Commit msg: Add task content versioning; drop unused prompt_version |
| 2026-05-28 | 0943c84 | docs-change | Third evaluator review: no edits, verdict calibrated | Commit msg: Re-evaluate dd-l2-bangkok-multicrs-audit: calibrated; no edits |

No prompt-change, grader-change, reference-change, or data-change commits have
touched this task since `88530c5` on 2026-05-17. Between the third evaluator
pass (2026-05-28) and now the broader repo has shipped house-style and
analyst_notes requirements in the evaluator prompt (`42f4c0a` on 2026-06-06)
and a soft-CRS grader refactor that does not apply to this task because the
deliverable is a CSV audit table with `expected_outputs[].crs: "n/a"`.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-17T12:48:47Z (commit `88530c5`,
  class: prompt-change). All later task-touching commits (`29a9ae3`,
  `7e92284`, `e218d35`, `622342b`, `0943c84`) are docs/audit-only and do not
  invalidate runs.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:18:55Z | 1.00 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:23:27Z | 1.00 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:26:49Z | 0.875 | done | current |
| run-20260527-2016Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-27T20:55:07Z | 1.00 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:48:16Z | 1.00 | done | current |
| run-20260528-0113Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T02:03:29Z | 1.00 | done | current |
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:38:07Z | 0.875 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:16:10Z | 0.875 | done | current |
| run-20260528-1927Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T20:18:32Z | 1.00 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:00:26Z | 0.875 | done | current |
| run-20260528-2332Z | claude-code-opus-basic (claude-opus-4-7) | 2026-05-28T23:56:37Z | 1.00 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:29:09Z | 0.875 | done | current |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T10:59:32Z | 0.875 | done | current |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:03:17Z | n/a | failed (model-side UnicodeDecodeError) | current |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:50:33Z | 1.00 | done | current |
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | n/a | cancelled | current |

(All 24 runs from 2026-05-12 through 2026-05-17 06:14Z are stale and were not
used as evidence.)

#### Verdict
**calibrated**

The current-evidence base now spans four model families (Claude Opus 4-6 /
4-7, DeepSeek V4 Flash, DeepSeek V4 Pro, Gemma 4 26B A4B IT) with both `basic`
and `gis_detailed` prompt variants on the Gemma family. Strong models (Opus
4-7) score a consistent 1.00 across five runs. The Gemma family produces a
clean bimodal pattern at exactly {0.875, 1.00}: when it skips the mojibake
heuristic and reports every layer as `utf-8` it lands precisely on the
documented `broken_wrong_encoding` partial score, when it executes the
heuristic it scores 1.00. DeepSeek V4 Pro also landed on 0.875 with the same
two encoding subchecks flipped, which fits the same documented failure mode.
The 2026-06-06 `gis_detailed` Gemma runs include one fully-correct score
(1.00) and two model-side aborts (a UnicodeDecodeError raised inside the
agent's own pipeline and a cancellation), neither of which is task evidence.
No correct-looking output was rejected; no broken output earned full marks.

#### Specific findings
- Grader on reference: 1.00 (16/16 subchecks); both gates pass (re-run this session).
- Pytest: 41/41 pass on `benchmark/eval` (re-run this session).
- Broken solutions re-graded this session: `broken_wrong_format` 0.0, `broken_partial_layers` 0.3125 (5/16), `broken_wrong_encoding` 0.875 (14/16) — matching declared `measured_score`. No metadata update needed.
- Output-CRS / format consistency (Step 2c-CRS): the deliverable is a CSV audit table with `expected_outputs[].crs: "n/a"` and `format: "csv"`. The grader does **not** reproject either side — it reads `declared_crs` as a string and checks `sample_x`/`sample_y` against per-CRS plausibility windows. The soft-CRS refactor sweeping other tasks this week does not apply here.
- House style: the prior instruction carried an em-dash and a spec-grammar list (`For every layer in X: layer_name, declared_crs, ...`) — both flagged by the new evaluator-prompt rules. Rewrote in full sentences, dropped the em-dash, kept the persona voice, kept the two allowed encoding labels, kept all column names, kept the "from the layer as-is" non-reproject implication, and kept the deliberate omission of the detection recipe (still says "encoding anomalies", not "Latin-1 round trip"). Re-graded the reference at 1.00 (16/16).
- analyst_notes: authored from scratch — the field was missing. Description and pitfalls cover the multi-layer enumeration trap, the silent-reprojection trap, the mojibake-detection round-trip, and the canonical CRS-string format. Not seen by the agent at run time.
- Versioning: applied first prompt-changing edit this session; bumped `task.json.version` from implicit 1 to explicit `2`.
- Data-source / OSM-tag note (carried forward): inventory lists `OSM tags: highway=*` and `task.json.tags.themes: ["highway"]` but the GPKG is hand-crafted. The `roads` layer carries a `highway`-style column to mimic OSM, justifying the tag at feature-schema level. `coverage.yaml` keeps `osm_tag_families: [highway]` consistent with the inventory; `data_sources: [bundled-local]` is correct for a hand-crafted fixture. No flag.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: rewrote `instruction` in house style — dropped the em-dash, replaced the spec-grammar fragment with full sentences, used the actual filename `bangkok_contractor_delivery.gpkg`. Preserved persona, the two allowed encoding labels, every column name, the "as-is" non-reproject implication, and the deliberate omission of the detection recipe. Re-grade on reference: 1.00 (16/16). Reason: house-style rules added to evaluator prompt 2026-06-06.
- `task.json`: authored `analyst_notes` (description / approach / pitfalls). Re-grade on reference: 1.00. Reason: field was missing and is now required for the eval UI.
- `task.json`: bumped `version` from implicit 1 to `2`. Reason: instruction changed.
- `coverage.yaml`: refreshed `evaluator_run_at` timestamp. No slug changes — vocabulary was already current.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.00 (16/16 subchecks)
- broken solutions: wrong_format 0.0, partial_layers 0.3125, wrong_encoding 0.875
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
- Old Gate-2 row-shape checks (`layer_name` is a non-empty string,
  `feature_count` coerces to int, `sample_x`/`sample_y` coerce to
  float) are now absorbed by:
    * `_index_by_layer` already filters non-string `layer_name` rows,
      so they show up as failing `layers_complete` /
      per-layer-missing subchecks (one point each).
    * The existing `{name}_feature_count_correct` subcheck already
      uses `try/except ValueError` around `int()`, so a non-numeric
      count now fails that one subcheck instead of zeroing the score.
    * The existing `{name}_sample_coords_plausible` subcheck already
      uses `try/except ValueError` around `float()`, so non-numeric
      coords now fail that one subcheck instead of zeroing the score.
- No new subchecks added; subcheck count unchanged at 16
  (1 layers_complete + 5 × 3 layers).

### Verification
- Reference solution re-graded: 1.0 (16/16 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Authored 2026-05-08 (`f0628d2`) as the data-discovery L2 case for Bangkok: a
hand-crafted multi-layer GPKG (`parcels` Polygon EPSG:24047, `roads` LineString
EPSG:32647, `markets` Point EPSG:4326; 10000 features total) seeded with two
defects, mixed CRSes across layers and a UTF-8/Latin-1/UTF-8 mojibake
corruption of Thai-script labels on two of three layers. Persona Krit
Suwannarat (Ministry-of-Interior deliverables auditor) needs a one-row-per-layer
CSV cite-sheet with declared CRS, geometry type, feature count, sample (x, y) in
the layer's own CRS, and a categorical encoding flag (`utf-8` /
`latin1-mojibake`). Grader (today) = one hard gate (`format_schema_valid`) plus
16 subchecks (1 `layers_complete` + 5 per layer x 3 layers), with
`layers_complete` and the three `feature_count` subchecks weighted 3.0 since
2026-06-07 (total weight 24).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | f0628d2 | initial-authoring | Initial task (README, data, grader, metadata, reference, brokens, task.json) | (initial) |
| 2026-05-14 | e732929 | prompt-change | Renamed CSV coord columns to `sample_x`/`sample_y` in instruction | Commit msg: models guessed `x`/`y` and lost the grader check |
| 2026-05-14 | b04e9f0 | prompt-change | Stripped deducible info from the instruction | Commit msg: strip deducible information from DD task instructions |
| 2026-05-16 | 7c812d6 | prompt-change | Re-added explicit mojibake-detection description and the two allowed label values | Commit msg: describe mojibake detection and expected output values |
| 2026-05-17 | 88530c5 | prompt-change | Replaced explicit mojibake recipe with neutral "encoding anomalies" phrasing; kept the two allowed labels | Commit msg: remove CRS/operation/encoding nudges from 5 DD task prompts |
| 2026-05-26 | 29a9ae3 | docs-change | Folder-layout reorg; path strings adjusted in grader/generator/broken-maker | Commit msg: reorganize task folder layout |
| 2026-05-26 | 7e92284 | docs-change | First evaluator review: no edits, verdict calibrated | Commit msg: re-evaluate, calibrated |
| 2026-05-27 | e218d35 | docs-change | Second evaluator review: no edits, verdict calibrated | Commit msg: re-evaluate, calibrated |
| 2026-05-28 | 622342b | docs-change | Repo-wide: dropped unused `prompt_version`, introduced `task.json.version` (implicit v1) | Commit msg: add task content versioning |
| 2026-05-28 | 0943c84 | docs-change | Third evaluator review: no edits, verdict calibrated | Commit msg: re-evaluate, calibrated |
| 2026-06-06 | 8a275ae | mixed (prompt-change + docs-change) | Fourth evaluator review: house-style instruction rewrite, authored `analyst_notes`, `version` 1 -> 2 | Commit msg: house-style rewrite + analyst_notes per new evaluator-prompt rules |
| 2026-06-06 | 363aed2 | grader-change | Dropped Gate 2 (`structural_correctness`); type-shape failures (non-numeric count/coords, non-string layer_name) now fail individual subchecks instead of zeroing the score | Commit msg: gate was inconsistent across the 36 graders; one hard gate, rest are subchecks |
| 2026-06-07 | 632ad1a | grader-change | Weighted `layers_complete` and the three `{layer}_feature_count_correct` subchecks 3.0 (total weight 16 -> 24) | Commit msg: data-content subchecks 3x in dd graders so schema-clean but data-wrong submissions score visibly lower |

Note: `632ad1a` changed this grader's relative scoring without appending to this
file (the `363aed2` cleanup did append a block). Its effect on the documented
broken-set scores is absorbed by this review: `partial_layers` 0.3125 -> 0.2917
(7/24), `wrong_encoding` 0.875 -> 0.9167 (22/24); both still inside their
declared `expected_score_range`, and the four-way ordering wrong_format (0.0) <
partial_layers < wrong_encoding < reference (1.0) is preserved.

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-06-07T18:28:21Z (commit `632ad1a`,
  class: grader-change). Prior design-affecting commits: `363aed2`
  (grader-change, 2026-06-06T20:11:02Z) and `8a275ae` (prompt-change,
  2026-06-06T15:03:01Z).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T13:39:34Z | 0.9167 | done | current (see note) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:16:29Z | 1.00 | done | current |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:24:21Z | 1.00 | done | current |

Note on run-20260607-112430Z: its task start (13:39Z) predates the 632ad1a
cutoff (18:28Z), but its `score.json` carries the 3.0 subcheck weights, so it
was demonstrably scored with the post-cutoff grader, and the prompt it saw is
the current v2 instruction (last prompt change `8a275ae`, 06-06 15:03Z). Both
the agent-facing contract and the scoring match the current task, so it is
counted as current evidence. Version check: all three runs report
`task_version: 2` = current `task.json.version`.

Footnote on stale runs: 41 other run directories exist for this task
(2026-05-12 through 2026-06-06). 24 predate the 88530c5 prompt change; the rest
(including five Opus 1.00s, the Gemma bimodal {0.875, 1.00} set, and DeepSeek
V4 Pro's 0.875) were scored against the pre-weighting 16-point grader and are
stale under the 632ad1a cutoff. They were considered only as historical
context, not as evidence.

#### Verdict
**calibrated**

Three current runs from two model families. Both DeepSeek V4 Flash runs (basic
and gis_detailed variants) score 1.00 with CSVs that match the reference
layer-for-layer (same layer set, same declared CRS strings, same geometry
types, same counts; sample coordinates differ from the reference's but all fall
inside the per-CRS plausibility windows, which is the designed behaviour).
Gemma 4 26B scores exactly 0.9167 by reporting every layer as `utf-8`, which is
the documented `broken_wrong_encoding` failure mode landing precisely on its
newly-weighted partial score (22/24); its `score.json` shows exactly
`parcels_encoding_correct` and `roads_encoding_correct` failing. The grader
separates the skipped-mojibake case from the fully-correct case at the intended
boundary, no correct-looking output was rejected, and no broken output earned
full marks. The evidence base is thinner than the May reviews (3 runs, 2
families) but spans both prompt variants and reproduces the designed partial
score exactly, so calibrated rather than insufficient-evidence.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `crs_audit.csv`, CSV format | instruction ("write one row per layer to `crs_audit.csv`") | stated |
| 7 required columns by exact name | instruction lists all seven | stated |
| one row per layer / all 3 layers (`layers_complete`, weight 3) | instruction says "walk every layer"; layer set comes from the bundled file | stated + inferable from data |
| `declared_crs` as canonical `EPSG:NNNN` | instruction ("formatted as `EPSG:NNNN`") | stated |
| geometry type per layer (case-insensitive) | layer metadata in the GPKG | inferable from data |
| exact feature count per layer (weight 3) | GPKG layer headers | inferable from data |
| sample coords inside the declared CRS's plausibility window | instruction ("a sample coordinate taken from the layer as it sits on disk") | stated (the "as it sits on disk" phrasing pins no-reproject) |
| encoding label in {`latin1-mojibake`, `utf-8`} | instruction names both labels | stated |
| which layers are mojibake-corrupted | the data itself (Thai labels showing Latin-1 Supplement chars) | inferable from data |

Factual claims checked: `bangkok_contractor_delivery.gpkg` matches
`inputs/`; the seven column names match the reference CSV header exactly; the
two encoding labels match the reference's values verbatim. No missing or
inaccurate claim found.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it enumerates all layers via
`pyogrio.list_layers`, reads declared CRS / geometry type / feature count from
layer metadata without reprojecting, samples the first feature's representative
point in the layer's own CRS (the instruction's "a sample coordinate taken from
the layer as it sits on disk" does not pin vertex-vs-representative, and the
grader's plausibility window treats any in-region point identically), and
classifies encoding with a Latin-1 round-trip plus Thai-block check that maps
exactly to the two allowed labels. No unrequested operations, no skipped steps,
no CRS choice to second-guess (the deliverable is a non-spatial CSV). Faithful.

#### Specific findings
- Grader on reference: 1.00 (16/16 subchecks, weighted total 24/24); hard gate passes (re-run this session).
- Pytest: 41/41 pass on `benchmark/eval` (re-run this session).
- Broken sets re-graded under the weighted grader: `wrong_format` 0.0, `partial_layers` 0.2917 (7/24), `wrong_encoding` 0.9167 (22/24). Both shifted scores remain inside their declared `expected_score_range` ([0.25, 0.40] and [0.80, 0.95]); `metadata.yaml > measured_score` refreshed accordingly (unilateral, no version bump owed).
- README refreshed (docs-change): stale `data/` path -> `inputs/`, stale `outputs/` prefix on the deliverable, and the three pre-weighting score citations (0.3125 / 0.875) updated to the weighted values.
- Output-CRS / format consistency (2c-CRS): deliverable is a non-spatial CSV (`expected_outputs[].crs: "n/a"`); grader reprojects nothing on either side. README, reference output, and `expected_outputs[]` agree. No inconsistency.
- The 632ad1a weighting promotes `layers_complete` and `feature_count` to weight 3. For this task that slightly *raises* the skipped-mojibake partial score (0.875 -> 0.9167) because encoding subchecks stayed weight 1. The encoding heuristic is the L2-defining operation here, so its relative weight loss is worth noting, but the score ordering and the [0.80, 0.95] band both hold, and the repo-wide weighting rationale (data-content counts weighted up) was a deliberate benchmark-wide decision. Not flagged.
- `task.json.version` stays 2: this pass made no instruction/grader/inputs edit (measured_score and README refreshes are exempt per the bump rules), matching the sweep precedent on sibling dd tasks (e.g. dd-l1-vienna-gpkg-manifest stayed v1 after the same refresh).
- Data-source / OSM-tag note (carried forward): inventory lists `OSM tags: highway=*` though the GPKG is hand-crafted; the `roads` layer carries a `highway`-style column to mimic OSM, justifying `osm_tag_families: [highway]` at feature-schema level. `data_sources: [bundled-local]` remains correct. No flag.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > measured_score` for the weighted grader (partial_layers 0.3125 -> 0.2917, wrong_encoding 0.875 -> 0.9167) and corrected the score arithmetic in their descriptions. Re-grade on reference: 1.00. Reason: 632ad1a reweighting changed the broken-set scores; both stay inside their declared ranges.
- `README.md`: updated stale `data/` and `outputs/` path prefixes from the 2026-05-26 reorg and the three pre-weighting score citations. Reason: docs drifted from the current layout and grader.
- `coverage.yaml`: refreshed `evaluator_run_at`. No slug changes; all slugs re-validated against the vocabulary.

#### Proposed but not applied (see HUMAN-REVIEW items)
- (none)

#### Tests run
- grader on reference: 1.00 (16/16 subchecks)
- broken solutions: wrong_format 0.0, partial_layers 0.2917, wrong_encoding 0.9167
- pytest: pass (41/41)

---

## Evaluator review 2026-06-14 - subcheck weight recalibration  (evaluator-commit <pending>)

### Change (one line)
RECALIBRATED: re-weighted the 16 subchecks by error severity so a failure of
the central skill (correctly auditing/reporting each layer's CRS) drops the
score meaningfully, while cosmetic metadata slips (feature count, geometry
type) drop it only lightly. Grading-only; no version bump.

### Motivation
The 2026-06-07 repo-wide commit (632ad1a) bluntly set `layers_complete` and the
three `feature_count` subchecks to weight 3.0 and left everything else at 1.0.
For a multi-CRS audit that is miscalibrated: it elevated a pure metadata count
(`feature_count`, read straight off the GPKG header) to the same weight as the
enumeration prerequisite, while the two checks that actually prove the CRS audit
is *right* - `declared_crs_correct` (the literal answer) and
`sample_coords_plausible` (proves the reported coords are internally consistent
with the declared CRS; catches silent reprojection, the degree-vs-metre slip,
and wrong-CRS sampling) - stayed at weight 1.0. Under the old weights a
silent-reprojection / wrong-CRS error on the two metric layers scored 20/24 =
0.833, *higher-scoring than tolerable* and barely below the secondary
encoding-skip failure (0.917); a cosmetic feature-count off-by-one (3.0) was
weighted to look *more* severe than a CRS error. The severity ordering was
inverted.

### Weight changes
| Subcheck | old | new | rationale |
|---|---|---|---|
| `layers_complete` | 3.0 | 4.0 | enumeration is the prerequisite for auditing all inputs' CRS; missing it drops 2/3 of the audit |
| `{layer}_declared_crs_correct` (x3) | 1.0 | 3.0 | central - the literal CRS answer the deliverable exists to give |
| `{layer}_sample_coords_plausible` (x3) | 1.0 | 3.0 | central - proves the CRS report is *right*, not merely present (catches reproject / degree-metre / wrong-CRS) |
| `{layer}_encoding_correct` (x3) | 1.0 | 2.0 | secondary defect-detection skill (the L2 lift), below the CRS core |
| `{layer}_feature_count_correct` (x3) | 3.0 | 1.0 | pure metadata count off the header; an off-by-one is a minor slip, not a CRS-audit failure |
| `{layer}_geometry_type_correct` (x3) | 1.0 | 1.0 | unchanged - cosmetic metadata read |

Total weight 24 -> 34 (4 + 3 x (3+3+2+1+1)).

### Broken-score before -> after
| Class | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | catastrophic - wrong deliverable (gate fail), unchanged |
| partial_layers | 0.2917 | 0.2941 | severe - only audited 1/3 of inputs; central failure |
| wrong_encoding | 0.9167 | 0.8824 | secondary-skill miss - now drops slightly more (encoding weight 2 vs 1), still high |
| reference | 1.00 | 1.00 | unchanged |

Ordering check: monotone and defensible - wrong_format (0.0) < partial_layers
(0.2941) < wrong_encoding (0.8824) < reference (1.0). Crucially the recalibration
fixes the inverted ordering for the two CRS-failure modes that lack a broken
fixture: a silent-reprojection / wrong-CRS error on the two metric layers now
scores (34 - 2x(3+3))/34 = 22/34 = 0.6471 (was 0.833), landing *below* the
secondary encoding-skip score as severity demands; a cosmetic count off-by-one
on one layer now scores 33/34 = 0.9706 (was 21/24 = 0.875), correctly a lighter
drop than any CRS error. No disjoint-failure inversion remains.

### Prior-run re-grade (3 current runs, task v2, post-632ad1a cutoff)
| Run | Adapter | old | new |
|---|---|---|---|
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 0.9167 | 0.8824 |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 1.00 | 1.00 |
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 1.00 | 1.00 |

Only shift: the Gemma run (documented skipped-mojibake failure) moves 0.9167 ->
0.8824, tracking the wrong_encoding broken exactly. The two fully-correct
DeepSeek runs are unchanged at 1.00. No correct output rejected; no broken
output earns full marks.

### Notes / non-changes
- No check logic, threshold, or gate touched - only `weight=` values.
- The 41 pre-cutoff run directories were scored against earlier graders and
  remain stale; not used as evidence.
- No HR items existed and none were created (empty `human_review_items` stays
  empty).
- One threshold observation (not changed, per scope): the
  `sample_coords_plausible` window for `EPSG:24047` and `EPSG:32647` is
  identical (both UTM 47N), so a coordinate sampled from the wrong metric layer
  would still pass that layer's window. The degree-vs-metre slip is still
  caught; cross-metric-layer confusion is not. Out of scope for a weight pass;
  noted for a future logic review.

### Changes applied this run
- `grade.py`: subcheck `weight=` values only (table above).
- `metadata.yaml`: refreshed `partial_layers` / `wrong_encoding` measured_score
  and the weight-arithmetic prose in their descriptions.
- `README.md`: refreshed the three stale score citations (0.2941 / 0.8824).
- `audit/status.json`: recorded unilateral edits, grader_score_after_edits 1.0,
  pytest_status not-run, evaluator_finished_at 2026-06-14.

### Tests run
- grader on reference: 1.00 (16/16 subchecks, weighted 34/34)
- broken solutions: wrong_format 0.0, partial_layers 0.2941, wrong_encoding 0.8824
- pytest: not run (orchestrator runs the suite)
