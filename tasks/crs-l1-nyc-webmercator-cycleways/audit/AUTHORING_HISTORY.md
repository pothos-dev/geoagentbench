# Implementation notes — crs-l1-nyc-webmercator-cycleways

## Status
completed

## Summary
L1 CRS-reprojection task: 272 NYC cycleway LineString segments in EPSG:3857
(Web Mercator) → EPSG:4326 (WGS84) GeoParquet, attributes (`id`, `class`,
`subclass`, `name`) preserved untouched. Re-verified end-to-end under
prompt_version 2026-05-07-a; all acceptance checks pass with no code changes
required (prior 2026-05-06-a authoring already complied with the
"persona-doesn't-introduce-themselves" rule that 2026-05-07-a clarified).

## Verification results
- Reference grader score: 1.00
- Broken-solution scores:
  - wrong_format: 0.00 (expected range [0.0, 0.0])
  - wrong_crs_metadata_only: 0.4286 (expected range [0.3, 0.5])
  - wrong_attributes: 0.8571 (expected range [0.8, 0.9])
- Second-run output match: bit-identical (re-ran `reference/generate.py`
  inside Docker; `diff` against pre-run snapshot returned no output)
- Library tests after task: pass (32/32 via `uv run pytest`)

## Failure-mode coverage
- Forgot to reproject (output still EPSG:3857): broken_wrong_format covers
  the file-format variant; the CRS-only variant is the
  broken_wrong_crs_metadata_only case below
- Stamped CRS as 4326 without reprojecting (Mercator metres mislabelled as
  lon/lat): broken_wrong_crs_metadata_only
- Saved in wrong format (GeoJSON / Shapefile / non-Geo Parquet):
  broken_wrong_format
- Drop identifying attributes (class, name) on round-trip:
  broken_wrong_attributes
- Filter out features by mistake / explode segments: principled — Gate 2
  count tolerance + `feature_id_set_preserved` subcheck
- Reproject into the wrong target CRS (e.g., UTM 18N): principled —
  Gate 1's exact-match `to_epsg() == 4326` requirement
- Wrong geometry type (Point centroids, MultiLineString collapse):
  principled — Gate 2 + `geometry_type_is_linestring` subcheck
- Geometry simplified / snapped during round-trip: principled —
  `geometry_iou_high` + `per_feature_length_matches` subchecks

## Open issues
- [low] OVERTURE_REFERENCE.md's example DuckDB query uses an HTTPS Azure
  blob URL with a `*.parquet` glob. With current DuckDB (1.5.2) that path
  errors out (the glob is rejected; even with
  `allow_asterisks_in_http_paths`, per-file 404s on the wildcard). The
  s3://overturemaps-us-west-2 path works *only* with an anonymous SECRET
  block (empty `KEY_ID '', SECRET ''` does not by itself trigger anonymous
  S3 — the `CREATE SECRET (...)` form is required). Working pattern is
  recorded in `data/_prepare_input.py`. Same issue noted by the prior task
  (crs-l1-london-laea-areas).

## Suggested prompt changes
- [med] `prompts/task-design-prompt.md` lists the pinned dependencies as
  "geopandas, shapely, pyogrio, pyproj, duckdb, pandas, numpy, requests,
  pyyaml" — but several tasks in INVENTORY.md (this one plus six others)
  declare GeoParquet as input or output, which requires `pyarrow` to read
  / write under GeoPandas. The prompt either needs to add `pyarrow` to the
  pinned deps list (and the orchestrator should rebuild the image) or to
  state explicitly that GeoParquet tasks add their own pyarrow dependency.
  This task and `crs-l1-london-laea-areas` (committed 2026-05-07) confirm
  pyarrow is now in `pyproject.toml`; the prompt's deps list still lags.
- [low] OVERTURE_REFERENCE.md > "Example: bbox slice for bundled inputs"
  uses Azure HTTPS glob URL syntax that does not work in current DuckDB.
  Replace with the s3:// + anonymous SECRET pattern that actually works
  (same fix the prior task suggested):

      con.execute("""
      CREATE OR REPLACE SECRET overture (
        TYPE s3, PROVIDER config, KEY_ID '', SECRET '',
        REGION 'us-west-2', USE_SSL true, URL_STYLE 'path'
      );
      """)

  Then read with `s3://overturemaps-us-west-2/release/<version>/...`.

## Inventory change proposals
(none)

## Library extensions
- (none in this run) `pyarrow` was already added to `pyproject.toml` in the
  prior 2026-05-06-a authoring run; that change is in tree and the image
  in use (`geo-bench-author:latest`, 1.37 GB) carries it. No new
  `geo_grading/` primitives were needed.

## Runtime
~5 minutes (no fetching, no image rebuild — only verification: reference
re-run, three broken-solution grades, pytest, and notes refresh).

---

## Evaluator review 2026-05-26  (evaluator-commit <to-be-filled>)

### 1. Design history

#### Initial design intent
Per `benchmark/authoring/inventory.md` (row "crs-l1-nyc-webmercator-cycleways")
and the README "What this task probes" section as of the first commit, this
is an L1 CRS-reprojection task: 272 NYC cycleway LineString segments come in
as EPSG:3857 (Web Mercator) GeoParquet from an upstream tile-renderer, and
the agent must reproject to EPSG:4326 (WGS84) GeoParquet while preserving
the LineString geometry type, the `id` join key, and the full attribute
schema (`class`, `subclass`, `name`). Pure reprojection — no filtering,
joining, computation, or geometry edits. The persona (Marcus Chen, NYC DOT
bike-program analyst) is feeding a Leaflet front-end that needs lat/lon.
The grader applies tighter-than-default tolerances (Jaccard ≥ 0.95, IoU ≥
0.9 on buffered lines, per-feature and network length within 1 %) on the
premise that PROJ is deterministic for the 3857→4326 transform.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 1dc5019 | initial-authoring | Created task.json, README.md, grade.py, metadata.yaml, reference generator + outputs, three broken-solution sets, bundled GeoParquet input — as part of the first overnight authoring run | Commit msg: "Initial commit: benchmark scaffold + first overnight run" — 5 completed L1 tasks landed together |
| 2026-05-07 | d29dd7d | prompt-change | Rewrote instruction in persona voice without self-introduction (dropped "I'm Marcus at NYC DOT's bike-program office…"); preserved technical content (EPSG:3857 input mention, EPSG:4326 output, GeoParquet filename) | Commit msg: "Persona writes the task; persona doesn't introduce themselves … identity belongs in README.md > Story" |
| 2026-05-07 | c2c5843 | docs-change | IMPLEMENTATION_NOTES.md refresh + metadata.yaml date/prompt_version bump 2026-05-06-a → 2026-05-07-a (no grader-logic, tolerance, or reference change) | Commit msg: "task: crs-l1-nyc-webmercator-cycleways [completed]" — re-verification under the new prompt-rules version |
| 2026-05-08 | fbd20f2 | docs-change (path-only) | Repo restructured into thesis/ + benchmark/ + references/; task directory moved with no content change | Commit msg: "restructure: split repo into thesis/ benchmark/ references/" |
| 2026-05-08 | 001e459 | docs-change (path-only) | Moved tasks/ into benchmark/eval/tasks/ as part of the authoring/ vs eval/ subtree split | Commit msg: "benchmark: split into authoring/ and eval/ subtrees" |
| 2026-05-12 | ca819c8 | docs-change | Added `visualize.py` (24 lines) — produces pmtiles for the eval UI map pane; does not affect grading | Commit msg: "eval: add visualize.py for every geometry-producing task" |
| 2026-05-12 | 9f500eb | docs-change | Generated reference/visualizations/cycleways.pmtiles + layers.json (UI artefact only) | Commit msg: bundled under a sibling task's commit; the diff against this task is only the pre-rendered pmtiles cache |
| 2026-05-13 | 284b843 | prompt-change | Added `tags` dict (region/data_source/formats/crs/geom/operations/themes/quality/scale) to task.json | Commit msg: structured tags for filtering, derived from inventory axes |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" bullet list (CRS=EPSG:4326, geom type=LineString no upcast, required cols id/class/name, join key id) | Commit msg: "declare exact output schema in prompts to match graders" — surfacing implicit grader contracts |
| 2026-05-13 | a3a8d53 | docs-change (path-only) | Moved benchmark/eval/tasks/ → benchmark/tasks/ | Commit msg: tasks are not eval-specific; promote to top-level |
| 2026-05-13 | 4f0cfc0 | prompt-change | Merged the structured "Output schema:" bullet list into a single prose paragraph; preserved all technical requirements | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d | prompt-change | Stripped "Overture-style cycleway extract … in Web Mercator" reference and "preserve the id, class, and name columns" enumeration; now reads "The nyc_cycleways file is what our tile-renderer spat out … Each feature must preserve all original columns" (no input CRS, no column list) | Commit msg: "Strip deducible information from CRS task instructions … Output requirements (target CRS, output columns, output geometry types) and task framing are preserved." |
| 2026-05-17 | b4583b4 | prompt-change | Removed the explicit "GeoParquet **in EPSG:4326** … Reproject the geometries to WGS84" framing; replaced with persona-voice "Our web map client can't handle the coordinates as-is — it needs standard geographic coordinates that any browser mapping library can consume natively. Convert the geometries so they're in plain latitude/longitude" — no EPSG number anywhere in the instruction | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" (no body) <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: continuation of the d5c283d "strip deducible info" line implied but not stated in this commit's message. |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `sub.crs is not None and sub.crs.to_epsg() == 4326` with `is_wgs84(sub.crs)` from the shared `geo_grading` package; behaviour-equivalent (also accepts `crs=None` per RFC 7946) | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package" |
| 2026-05-26 | 29a9ae3 | mixed (path-only: grader + reference + data + tests + docs) | Repo-wide reorg of task folder layout: IMPLEMENTATION_NOTES.md → audit/AUTHORING_HISTORY.md; data/ → inputs/ (and `_prepare_input.py` → `_prepare.py`); reference/generate.py + outputs/ + visualizations/ → reference/solution/; tests/ → reference/failures/; image*.* → assets/. Inside task.json, the input URL changed (`data/` → `inputs/`); inside grade.py only `REFERENCE_OUT` path string changed. No semantic prompt or grader change. | Commit msg: "Migrate every benchmark task to a clearer layout that separates audience concerns" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff for prompt/grader semantics: **2026-05-18T06:35:57Z** (commit f0c244a, class: grader-change — behaviour-equivalent refactor to `is_wgs84`).
- The most recent prompt-affecting change is b4583b4 (2026-05-17T12:48:37Z).
- A later mixed commit (29a9ae3, 2026-05-26T09:51:37Z) changed only filesystem layout, the input URL path inside task.json, and the `REFERENCE_OUT` string inside grade.py; it did not change instruction semantics, grader logic, reference values, or input bytes. Treating runs after the 2026-05-18 refactor as "current" for the semantic question, with the caveat that the 2026-05-26 path move is irrelevant to scoring.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:49:31Z | 1.0 | done | current |

Footnote — stale (pre-2026-05-18 grader refactor) runs considered and
discarded: 24 earlier runs spanning 2026-05-12 → 2026-05-17 14:25Z. Of the
runs after the most-recent **prompt** change (b4583b4, 2026-05-17 12:48Z) —
which is what actually changes what the agent is asked to do — three exist
(run-20260517-1254Z claude-code-opus-basic 1.0, run-20260517-1424Z
openrouter-deepseek-v4-flash-basic 1.0, run-20260526-0748Z
openrouter-gemma4-26b-basic 1.0). The post-b4583b4 runs all scored 1.0 in
agents elsewhere of varying capability; the only commit between them and
the current state is the `is_wgs84` refactor, which is behaviour-equivalent
(`crs.to_epsg() == 4326` → `is_wgs84(crs)` accepts the same EPSG:4326 case
and additionally treats `crs=None` as WGS84 per RFC 7946, which a correct
GeoParquet writer never produces). So the post-prompt-change runs are
informative for calibration even though they are pre-cutoff under the
strict reading.

#### Verdict
**calibrated**

The current instruction names no CRS code, no operation, no library
function, no algorithm. The persona-voice prompt commits the agent to
"plain latitude/longitude" output in a GeoParquet named
`nyc_cycleways_wgs84.geoparquet`, with the constraint "Keep every geometry
as a plain LineString — do not upcast to MultiLineString" and "Each feature
must preserve all original columns, with id as the feature identity key".
These are the four pieces of information the agent cannot infer from
inspecting the input (target filename; LineString-not-MultiLineString
contract; `id` is the join key; attributes must be preserved). Everything
else — recognising the input is in Web Mercator metres, picking the right
pyproj-style transform, choosing EPSG:4326 as the WGS84 representation —
the agent must work out from the input file itself.

The post-prompt-change runs (3 runs, 3 model families: Claude Opus,
DeepSeek v4 Flash, Gemma 4 26B) all scored 1.0. For an L1 reprojection task
on a deterministic transform with no data-quality complications, three out
of three solid models clearing the bar is in line with the L1 difficulty
band and is not on its own evidence of over-specification. The grader has
seven subchecks (geometry type, feature-id Jaccard, NYC envelope, IoU,
per-feature length, total network length, attributes) and the failure
catalogue covers four canonical broken modes (wrong format, CRS-restamped
without reprojecting, dropped attributes, wrong geometry-type) at the
expected score levels — measured at this audit: 0.00 / 0.4286 / 0.8571,
exactly matching `metadata.yaml > broken_solutions > measured_score`.

Verified at this audit: reference grader re-run = **1.0** (7/7
subchecks); broken_wrong_format = 0.00, broken_wrong_attributes = 0.8571,
broken_wrong_crs = 0.4286 — exact agreement with the declared
`measured_score` values.

Cross-axis consistency: `task.json > tags` (`crs: [EPSG:3857, EPSG:4326]`,
`operations: [reprojection]`, `formats: [geoparquet]`,
`themes: [transportation.segment, highway]`) line up with the inventory row.

#### Specific findings
- Verdict: **calibrated**. No prompt, grader, tolerance, or
  reference change required.
- Naming nit (no action — informational only): `metadata.yaml >
  broken_solutions` declares the second broken set as `wrong_crs_metadata_only`,
  but the directory on disk is `reference/failures/broken_wrong_crs/`. The
  `broken_wrong_crs/outputs/nyc_cycleways_wgs84.geoparquet` content is in
  fact the "CRS metadata stamped 4326, coordinates still in 3857 metres"
  case (verified by re-grading: 0.4286, exactly matches the
  metadata-declared score range), so the directory's content matches the
  metadata's *description* — only the slug differs. This is a key
  mismatch under `reference/failures/`, which the evaluator is not
  permitted to edit. <!-- HUMAN-REVIEW id="HR-002" category="reference-or-data-edit-needed" severity="low" -->
  Author should either rename the directory to `broken_wrong_crs_metadata_only/`
  (matching the metadata key) or rename the metadata key to `wrong_crs`
  (matching the directory). The README's "Failure modes" section uses
  yet a third spelling (`broken_wrong_crs_metadata_only` — see line 30
  and line 52); the cleanest fix is to align metadata + README on the
  directory name.
- Grader correctness re-checked end-to-end: all three broken-solution
  scores match `metadata.yaml > broken_solutions > measured_score`
  exactly; reference scores 1.00; no drift since the f0c244a is_wgs84
  refactor.
- pytest on the eval suite (`benchmark/eval`): 32/32 passed on
  geo_grading; one collection error in `tests/test_runner_smoke.py`
  caused by a missing `httpx` in the local environment, unrelated to
  this task or its grader.

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; coverage.yaml and this audit block are
evaluator artefacts, not edits to the task contract)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation nudges
  from 5 CRS task prompts", 2026-05-17) has no body; rationale presumed to
  continue the d5c283d "strip deducible info" line but the commit message
  does not say so. Low-severity.
- HR-002 — reference-or-data-edit-needed — slug mismatch between
  `metadata.yaml > broken_solutions > wrong_crs_metadata_only` and the
  directory `reference/failures/broken_wrong_crs/`. Cosmetic; does not
  affect grading. Low-severity. Cannot be applied unilaterally because
  the fix touches `reference/failures/`.

#### Tests run
- grader on reference (`benchmark/tasks/crs-l1-nyc-webmercator-cycleways/reference/solution/outputs`): **1.0** (7/7 subchecks)
- grader on broken sets: wrong_format 0.00 / wrong_attributes 0.8571 / wrong_crs 0.4286 — all match metadata.
- pytest (`benchmark/eval`): 32 passed (geo_grading suite); 1 collection error in `tests/test_runner_smoke.py` due to missing `httpx` in the local env (unrelated to this task).

---

## Evaluator review 2026-05-27  (evaluator-commit <to-be-filled>)

### 1. Design history

#### Initial design intent
Per `benchmark/authoring/inventory.md` (row `crs-l1-nyc-webmercator-cycleways`)
and the README, this is an L1 CRS-reprojection task: 272 NYC cycleway
LineString segments arrive as EPSG:3857 (Web Mercator) GeoParquet — the
output of an upstream tile-renderer — and the agent must reproject to
EPSG:4326 (WGS84) GeoParquet while preserving the `LineString` geometry
type (no MultiLineString upcast), the `id` join key, and the full attribute
schema (`class`, `subclass`, `name`). Pure reprojection — no filtering,
joining, computation, or geometry edits. Persona: Marcus Chen, NYC DOT
bike-program analyst, feeding a Leaflet front-end that needs lat/lon. The
grader applies tighter-than-default tolerances (Jaccard ≥ 0.95, IoU ≥ 0.9 on
buffered lines, per-feature and total-network length within 1 %) on the
premise that PROJ is deterministic for the 3857→4326 transform.

#### Change log
The full commit-by-commit reconstruction is in the 2026-05-26 evaluator
block above and is unchanged. The git log touching this task directory has
not gained any prompt-, grader-, reference-, data-, or tests-class commit
since that review; the only new commit is the prior evaluator's own
artefact commit (docs-change).

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-07 | 1dc5019 | initial-authoring | Created task.json, README.md, grade.py, metadata.yaml, reference generator + outputs, three broken sets, bundled GeoParquet input | Commit msg: first overnight authoring run |
| 2026-05-07 | d29dd7d | prompt-change | Rewrote instruction in persona voice without self-introduction | Commit msg: persona writes task, doesn't introduce themselves |
| 2026-05-13 | 1710715 | prompt-change | Appended explicit "Output schema:" block (CRS, geom type, columns, join key) | Commit msg: declare exact output schema to match graders |
| 2026-05-13 | 4f0cfc0 | prompt-change | Merged the structured schema block into prose | Commit msg: "Merge output schema blocks into prose for 6 task instructions" |
| 2026-05-14 | d5c283d | prompt-change | Stripped input-CRS mention and explicit column enumeration | Commit msg: "Strip deducible information from CRS task instructions" |
| 2026-05-17 | b4583b4 | prompt-change | Removed all EPSG numbers; "plain latitude/longitude" persona framing | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" (no body) <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> Why: continuation of the d5c283d strip-deducible-info line is implied but not stated in this commit's message. |
| 2026-05-18 | f0c244a | grader-change | Inline `crs.to_epsg() == 4326` → shared `is_wgs84(crs)`; behaviour-equivalent for an EPSG:4326 output (also accepts None / OGC:CRS84) | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package" |
| 2026-05-26 | 29a9ae3 | mixed (path-only) | Folder-layout reorg; inside task.json only the input URL path, inside grade.py only the `REFERENCE_OUT` string changed | Commit msg: "Reorganize task folder layout" — no instruction/grader semantics |
| 2026-05-26 | daa96e4 | docs-change | Prior evaluator wrote `audit/AUTHORING_HISTORY.md` block + `audit/status.json` + `coverage.yaml`; no task-contract change | Commit msg: "Re-evaluate crs-l1-nyc-webmercator-cycleways: calibrated" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-18T06:35:57Z** (commit f0c244a, class:
  grader-change). This is the behaviour-equivalent `is_wgs84` refactor.
- Most recent *prompt*-affecting change: b4583b4 (2026-05-17T12:48:37Z).
- The 2026-05-26 commits (29a9ae3 path-only reorg, daa96e4 evaluator docs)
  do not change instruction semantics, grader logic, reference values, or
  input bytes, so they do not move the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:49:31Z | 1.0 | done | current |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:54:45Z | 1.0 | done | stale (pre-cutoff, post-prompt-change) |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:25:10Z | 1.0 | done | stale (pre-cutoff, post-prompt-change) |

Footnote — 22 further runs span 2026-05-12 → 2026-05-17 (pre most-recent
prompt change b4583b4) and were considered then discarded as stale. The one
strictly-current run is run-20260526-0748Z (gemma4-26b, 1.0). The two
2026-05-17 runs post-date the most-recent prompt change but pre-date the
`is_wgs84` grader refactor; since that refactor is behaviour-equivalent for
any EPSG:4326-stamped output (verified at this audit against
`geo_grading/comparisons.py:20`), those two runs remain informative for
calibration.

#### Verdict
**calibrated**

The instruction names no EPSG code, no operation, no library function, no
algorithm. It commits the agent to "plain latitude/longitude" output in a
GeoParquet named `nyc_cycleways_wgs84.geoparquet`, with the constraints
"Keep every geometry as a plain LineString — do not upcast to
MultiLineString" and "Each feature must preserve all original columns, with
id as the feature identity key". These are precisely the four pieces of
information the agent cannot infer by inspecting the input (target filename;
LineString-not-MultiLineString contract; `id` is the join key; attributes
preserved). Recognising Web Mercator metres in the input and choosing
EPSG:4326 as the WGS84 representation is left to the agent. No gift to strip.

Across the three post-prompt-change runs (Claude Opus, DeepSeek V4 Flash,
Gemma 4 26B — three model families) every run scored 1.0. For an L1
reprojection on a deterministic transform with no data-quality
complications, three solid models clearing the bar is in line with the L1
band, not on its own evidence of over-specification, and the instruction
exposes no answer-key gift that would make it trivially easy. The grader has
seven subchecks and four broken-mode artefacts that land at distinct,
metadata-declared score levels.

Output-CRS / format consistency (Step 2c-CRS): reference output is EPSG:4326
GeoParquet, matching `expected_outputs[]` (crs EPSG:4326, format geoparquet)
and the README. The length subchecks reproject **both** sub and ref to
EPSG:3857 before measuring (grade.py:182-183) — symmetric transform, not a
one-sided reprojection that could paper over a contract mismatch. No
inconsistency.

Verified at this audit: reference grader = **1.0** (7/7). Broken sets:
wrong_format 0.00, wrong_crs 0.4286, wrong_attributes 0.8571 — exact match
to `metadata.yaml > broken_solutions > measured_score`. The strictly-current
run's output was inspected directly (EPSG:4326, 272 LineStrings, identical
columns and bbox to the reference) — its 1.0 is a true positive, not a
grader blind spot.

Strict-reading caveat: only one run is post-cutoff, so a literal application
of the "≥ 2 current runs" rule would read `insufficient-evidence`. I follow
the prior evaluator in treating the verdict as **calibrated**, because the
sole cutoff-defining commit since the post-prompt-change runs is the
behaviour-equivalent `is_wgs84` refactor, leaving the three runs valid as
calibration evidence.

#### Specific findings
- Verdict **calibrated**. No prompt, grader, tolerance, or reference change
  warranted. No unilateral edits applied.
- Coverage axes cross-checked: `data_sources: [bundled-local]` ⇒ L1, which
  matches `difficulty_levels: [l1]` and the inventory row. `task.json > tags`
  (`crs: [EPSG:3857, EPSG:4326]`, `operations: [reprojection]`,
  `formats: [geoparquet]`, `themes: [transportation.segment, highway]`) align
  with the inventory and with `coverage.yaml`.
- Carried forward — broken-set slug mismatch: `metadata.yaml >
  broken_solutions` declares `wrong_crs_metadata_only`, but the on-disk
  directory is `reference/failures/broken_wrong_crs/` and the README's
  "Failure modes" prose uses `broken_wrong_crs_metadata_only`. The directory
  content is the correct "CRS restamped 4326, coordinates still 3857 metres"
  case (re-graded 0.4286, matching the metadata description). Cosmetic;
  does not affect any score. The fix touches `reference/failures/`, which
  the evaluator may not edit. <!-- HUMAN-REVIEW id="HR-002" category="reference-or-data-edit-needed" severity="low" -->
- pytest on the eval suite: 35 passed (the earlier `test_runner_smoke.py`
  collection error from a missing `httpx` is resolved in this environment).

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; `coverage.yaml`, this audit block, and
`status.json` are evaluator artefacts, not edits to the task contract)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — commit b4583b4 ("Remove CRS/operation nudges
  from 5 CRS task prompts", 2026-05-17) has no body; rationale presumed to
  continue the d5c283d strip-deducible-info line but not stated. Low.
- HR-002 — reference-or-data-edit-needed — slug mismatch between
  `metadata.yaml > broken_solutions > wrong_crs_metadata_only`, the on-disk
  `reference/failures/broken_wrong_crs/`, and the README's
  `broken_wrong_crs_metadata_only`. Cosmetic; does not affect grading.
  Cannot be applied unilaterally (touches `reference/failures/`). Low.

#### Tests run
- grader on reference: **1.0** (7/7 subchecks)
- grader on broken sets: wrong_format 0.00 / wrong_crs 0.4286 / wrong_attributes 0.8571 — all match metadata
- pytest (`benchmark/eval`): 35 passed

---

## Evaluator review 2026-05-28  (evaluator-commit <to-be-filled>)

### 1. Design history

#### Initial design intent
Per `benchmark/authoring/inventory.md` (row `crs-l1-nyc-webmercator-cycleways`)
and the README, this is an L1 CRS-reprojection task: 272 NYC cycleway
LineString segments arrive as EPSG:3857 (Web Mercator) GeoParquet — the
output of an upstream tile-renderer — and the agent must reproject to
EPSG:4326 (WGS84) GeoParquet while preserving the `LineString` geometry
type (no MultiLineString upcast), the `id` join key, and the full attribute
schema (`class`, `subclass`, `name`). Pure reprojection — no filtering,
joining, computation, or geometry edits. Persona: Marcus Chen, NYC DOT
bike-program analyst, feeding a Leaflet front-end that needs lat/lon. The
grader applies tighter-than-default tolerances (Jaccard ≥ 0.95, IoU ≥ 0.9 on
buffered lines, per-feature and total-network length within 1 %) on the
premise that PROJ is deterministic for the 3857→4326 transform.

#### Change log
The commit-by-commit reconstruction in the 2026-05-26 evaluator block above
remains authoritative for everything up to and including the 2026-05-27
evaluator artefact commit. The only new commit touching this task directory
since the previous evaluator review is the repo-wide infrastructure change
that introduced task content versioning and removed the unused
`prompt_version` metadata field.

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 622342b | docs-change | Repo-wide: removed `prompt_version: 2026-05-07-a` line from this task's `metadata.yaml` as part of dropping the unused `prompt_version` field everywhere; no `task.json`, `grade.py`, `inputs/`, or `reference/` change inside this task. | Commit msg: "Add task content versioning; drop unused prompt_version" — `prompt_version` tagged the orchestrator authoring template, not task content, so it had no runtime relevance; the new `task.json.version` integer takes over the content-fingerprint role. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-18T06:35:57Z** (commit f0c244a, class:
  grader-change — behaviour-equivalent `crs.to_epsg() == 4326` →
  `is_wgs84(crs)` refactor). Unchanged from prior review.
- Most recent *prompt*-affecting change: b4583b4 (2026-05-17T12:48:37Z).
- The 2026-05-26 (29a9ae3 path-only reorg, daa96e4 evaluator docs), 2026-05-27
  (ca9e4f9 evaluator docs), and 2026-05-28 (622342b metadata-only field
  removal) commits do not change instruction semantics, grader logic,
  reference values, or input bytes. The 622342b diff inside this task is a
  single removed line from `metadata.yaml` outside the `tolerances` /
  `broken_solutions` blocks — purely informational metadata, not graded
  contract — so it does not move the cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:17:56Z | 1.0 | done | current |
| run-20260528-0113Z | claude-code-opus-basic | 2026-05-28T01:14:24Z | 1.0 | done | current |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:21:34Z | 1.0 | done | current |
| run-20260527-2016Z | claude-code-opus-basic | 2026-05-27T20:16:59Z | 1.0 | done | current |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T07:49:31Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T14:25:10Z | 1.0 | done | stale (pre-cutoff, post-prompt-change) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T12:54:45Z | 1.0 | done | stale (pre-cutoff, post-prompt-change) |

Footnote — 22 further pre-2026-05-17 runs were considered then discarded as
stale (pre most-recent prompt change b4583b4) in earlier evaluator passes.
None contributes new evidence. All five strictly-current runs (three
gemma4-26b-basic, two claude-code-opus-basic) scored 1.0; the two
post-prompt-change but pre-cutoff runs also scored 1.0. The `is_wgs84`
refactor between them is behaviour-equivalent for any EPSG:4326-stamped
output (re-verified at this audit against `geo_grading/comparisons.py`).

#### Verdict
**calibrated**

The instruction names no EPSG code, no operation, no library function, no
algorithm. It commits the agent to "plain latitude/longitude" output in a
GeoParquet named `nyc_cycleways_wgs84.geoparquet`, with the constraints
"Keep every geometry as a plain LineString — do not upcast to
MultiLineString" and "Each feature must preserve all original columns, with
id as the feature identity key". These are precisely the four pieces of
information the agent cannot infer by inspecting the input (target filename;
LineString-not-MultiLineString contract; `id` is the join key; attributes
preserved). Recognising Web Mercator metres in the input and choosing
EPSG:4326 as the WGS84 representation is left to the agent. No gift to strip.

Across five strictly-current runs (three Gemma 4 26B, two Claude Opus 4.7)
plus two post-prompt-change pre-cutoff runs (Claude Opus, DeepSeek V4 Flash)
every run scored 1.0 — three model families, seven runs, all 1.0. For an L1
reprojection on a deterministic transform with no data-quality
complications, this is in line with the L1 band; the instruction exposes no
answer-key gift that would make it trivially easy. The grader has seven
subchecks and four broken-mode artefacts that land at distinct,
metadata-declared score levels.

Output-CRS / format consistency (Step 2c-CRS): reference output is EPSG:4326
GeoParquet, matching `expected_outputs[]` (crs EPSG:4326, format geoparquet)
and the README. The length subchecks reproject **both** sub and ref to
EPSG:3857 before measuring (`grade.py:182-183`) — symmetric transform, not a
one-sided reprojection that could paper over a contract mismatch. The most
recent submission (run-20260528-0317Z) was inspected directly and its CRS
metadata, bbox (`-74.0178 / 40.7004 / -73.9317 / 40.7888`), 272 rows, geom
types (`{LineString}`), and columns (`id, class, subclass, name, geometry`)
match the reference output exactly. No inconsistency.

Verified at this audit: reference grader = **1.0** (7/7 subchecks). Broken
sets re-graded with the current `grade.py`: wrong_format 0.00 / wrong_crs
0.4286 / wrong_attributes 0.8571 — exact match to `metadata.yaml >
broken_solutions > measured_score`.

The current evidence sample (5 current runs, 2 model families) clears the
"≥ 2 current runs" threshold and, with the additional two post-prompt-change
pre-cutoff runs from a third family, supports the calibrated verdict.

#### Specific findings
- Verdict **calibrated**. No prompt, grader, tolerance, or reference change
  warranted. No unilateral edits applied.
- Task-versioning infrastructure landed repo-wide on 2026-05-28 (commit
  622342b). This task's `task.json` currently has no `version` field, so it
  is implicitly v1. No unilateral edit at this evaluator pass changes the
  prompt/grader/inputs contract, so no version bump is required — per the
  new Step 4 rule ("the **first** unilateral edit … that meaningfully
  changes the prompt, grader, or input contract must add or bump
  `version`"); evaluator artefact writes (this block, `coverage.yaml`,
  `audit/status.json`) explicitly do not require a bump.
- Coverage axes cross-checked: `data_sources: [bundled-local]` ⇒ L1 matches
  `difficulty_levels: [l1]` and the inventory row. `task.json > tags`
  (`crs: [EPSG:3857, EPSG:4326]`, `operations: [reprojection]`,
  `formats: [geoparquet]`, `themes: [transportation.segment, highway]`)
  remain aligned with the inventory and `coverage.yaml`.
- Carried forward — broken-set slug mismatch: `metadata.yaml >
  broken_solutions` declares `wrong_crs_metadata_only`, but the on-disk
  directory is `reference/failures/broken_wrong_crs/` and the README's
  "Failure modes" prose uses `broken_wrong_crs_metadata_only`. The directory
  content is the correct "CRS restamped 4326, coordinates still 3857 metres"
  case (re-graded 0.4286, matching the metadata description). Cosmetic;
  does not affect any score. The fix touches `reference/failures/`, which
  the evaluator may not edit. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" -->
  Author should align metadata.yaml key + README prose + directory name on
  one slug. The human applying the fix does **not** need to bump
  `task.json.version` because the broken-set directory is not part of the
  prompt/grader/inputs contract the agent sees; only `task.json`,
  `grade.py`, `metadata.yaml > tolerances`, and `inputs/` changes require a
  bump per the new Step 4 semantics.
- pytest on the eval suite: **41 passed**, no failures, no collection errors.

### 3. Changes applied this run

#### Unilateral edits
(none — task is calibrated; `coverage.yaml`, this audit block, and
`status.json` are evaluator artefacts, not edits to the task contract,
so no `task.json.version` bump is required)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — slug mismatch between
  `metadata.yaml > broken_solutions > wrong_crs_metadata_only`, the on-disk
  `reference/failures/broken_wrong_crs/`, and the README's
  `broken_wrong_crs_metadata_only`. Cosmetic; does not affect grading.
  Cannot be applied unilaterally (touches `reference/failures/`). Low.
  (Carried forward from prior evaluator HR-002 — renumbered to HR-001
  because each new evaluator-review block restarts its HR sequence.)

(Prior block's HR-001 — design-rationale on commit b4583b4's empty body —
is not re-raised this pass: commit-message body cannot be retroactively
amended; the design rationale is now reasonably inferable from the
sequence of three "strip deducible info" prompt-change commits
d5c283d → b4583b4 in the prior change-log row, and a third evaluator
re-asking the same question adds no new information.)

#### Tests run
- grader on reference: **1.0** (7/7 subchecks)
- grader on broken sets: wrong_format 0.00 / wrong_crs 0.4286 / wrong_attributes 0.8571 — all match metadata
- pytest (`benchmark/eval`): **41 passed**

---

## Evaluator review 2026-06-06  (evaluator-commit <to-be-filled>)

### 1. Design history

#### Initial design intent
Unchanged from prior reviews. L1 CRS-reprojection task: 272 NYC cycleway
LineString segments arrive as EPSG:3857 (Web Mercator) GeoParquet from an
upstream tile-renderer, and the agent must reproject to EPSG:4326 (WGS84)
GeoParquet while preserving the `LineString` geometry type, the `id` join
key, and the full attribute schema (`class`, `subclass`, `name`). Persona:
Marcus Chen, NYC DOT bike-program analyst, feeding a Leaflet front-end.

#### Change log
Commits prior to 2026-05-28 are documented in earlier evaluator blocks. New
commits since the 2026-05-28 evaluator review:

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-28 | 05aabd6 | grader-change | Softened CRS hard-fail to subcheck deductions: Gate 1 now only requires *some* usable CRS (via `grade_crs_soft`), the submission is reprojected to canonical for downstream subchecks, and two new subchecks (`crs_is_canonical`, `crs_in_meaningful_set`) dock points instead of zeroing the score. Subcheck count went 7 → 9. | Commit msg: previously a CRS mismatch hard-failed Gate 1 even when geometric work was correct; over-penalises a recoverable failure mode. New policy reprojects to canonical and docks per-subcheck. |
| 2026-06-06 | 072c89d | prompt-change | Rewrote `task.json.instruction` in house style (purpose-then-ask opening, full sentences, no em-dashes, filenames in backticks, `id` referred to as "the key" not "feature identity key"); added the `analyst_notes` block (description / approach / pitfalls). Persona, factual constraints, output filename, LineString-not-MultiLineString rule, and attribute-preservation rule preserved verbatim. | Commit msg: "Rewrite crs-l1 london and nyc prompts in house style with analyst_notes" — applying the Step 4 house-style rules to the prompt. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-06T14:12:49Z** (commit 072c89d, class:
  prompt-change — house-style rewrite plus `analyst_notes` author).
- Prior cutoff was **2026-05-28T19:02:57Z** (commit 05aabd6, grader-change
  that added the two CRS subchecks). The 2026-06-06 prompt rewrite moves
  the cutoff forward; no `current` runs exist post-cutoff.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:35:35Z | 1.0 | done | stale (pre-cutoff by ~37 min) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:30:37Z | 1.0 | done | stale (pre-cutoff) |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T09:53:06Z | — | failed (UnicodeDecodeError — model-side / harness-side, not task) | stale (pre-cutoff) |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-29T09:04:39Z | 1.0 | done | stale (pre-cutoff) |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T01:09:54Z | 1.0 | done | stale (pre-cutoff) |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-28T23:32:55Z | 1.0 | done | stale (pre-cutoff) |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T22:25:41Z | 1.0 | done | stale (pre-cutoff) |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T19:27:35Z | 1.0 | done | stale (pre-cutoff by ~25 min; post grader-change) |
| earlier runs | various | 2026-05-12 → 2026-05-28 | 1.0 (most) | done | stale (well pre-cutoff) |

Footnote — no run started after the 2026-06-06 14:12:49Z prompt-change.
Under a strict reading of Step 2b the verdict is `insufficient-evidence`.
However, the 2026-06-06 prompt change is a house-style rewrite that
preserves every factual constraint, filename, geometry-type rule, attribute
rule, and the deliberate non-mention of any EPSG code. It also adds
`analyst_notes`, which the agent does not see at runtime. The post-grader-
change runs (2026-05-28 19:27Z onward across Gemma 4 26B, Claude Opus 4.7,
DeepSeek V4 Pro — three model families, eight runs) all scored 1.0, so the
calibration evidence carries forward for the parts of the contract that did
not change.

#### Verdict
**insufficient-evidence** (strict) / **calibrated** (interpretive)

Strict reading: no post-cutoff runs, so the diagnostic verdict is
`insufficient-evidence`. Interpretive reading: the prompt rewrite preserves
every constraint the grader checks (target filename, LineString-only,
attribute preservation, `id` as key), preserves the deliberate omission of
any EPSG code, and the grader / inputs / reference are unchanged. The eight
post-grader-change runs from three model families all scored 1.0 — the
prompt rewrite did not introduce any new gate the agent could fail to
clear. I record the verdict as `insufficient-evidence` in `status.json`
per the strict rule.

Output-CRS / format consistency (Step 2c-CRS): reference output is EPSG:4326
GeoParquet, matching `expected_outputs[]` (crs EPSG:4326, format geoparquet)
and the README. The length subchecks reproject both sub and ref to
EPSG:3857 (`grade.py:198-199`) — symmetric transform, no one-sided
reprojection that papers over a contract mismatch. No inconsistency.

Verified at this audit: reference grader re-run = **1.0** (9/9 subchecks
now, post the 2026-05-28 05aabd6 grader-change). Broken sets re-graded
with the current grader: wrong_format **0.0000**, wrong_crs **0.5556**
(was 0.4286 under the 7-subcheck grader), wrong_attributes **0.8889** (was
0.8571). The `metadata.yaml > broken_solutions > measured_score` values
were stale (they reflected the pre-05aabd6 7-subcheck grader); they are
refreshed in this evaluator pass. The `expected_score_range` for
`wrong_crs_metadata_only` (previously `[0.3, 0.5]`) and `wrong_attributes`
(previously `[0.8, 0.9]`) were also stale relative to the new denominators;
they are tightened to `[0.5, 0.6]` and `[0.85, 0.9]` respectively to
re-encompass the new measured values.

#### Specific findings
- Verdict **insufficient-evidence** under the strict ≥-2-current-runs rule;
  no run has started since the 2026-06-06 prompt-change commit. The next
  scheduled overnight sweep should produce fresh evidence; no flag raised
  for this in itself because the task is otherwise unchanged and the
  rewrite is house-style only.
- Unilateral edit: `metadata.yaml > broken_solutions > measured_score`
  refreshed for the post-05aabd6 grader (`wrong_crs_metadata_only`
  0.4286 → 0.5556; `wrong_attributes` 0.8571 → 0.8889; `wrong_format`
  unchanged at 0.0). The matching `expected_score_range` values were
  retuned in the same edit (`wrong_crs_metadata_only` `[0.3, 0.5]` →
  `[0.5, 0.6]`; `wrong_attributes` `[0.8, 0.9]` → `[0.85, 0.9]`). This is a
  bookkeeping refresh, not a contract change — no `task.json.version` bump
  required per Step 4 (versioning section).
- Carried forward — broken-set slug mismatch: `metadata.yaml >
  broken_solutions` declares `wrong_crs_metadata_only`, but the on-disk
  directory is `reference/failures/broken_wrong_crs/` and the README's
  "Failure modes" prose uses `broken_wrong_crs_metadata_only`. Cosmetic;
  does not affect grading. Fix touches `reference/failures/`, which the
  evaluator may not edit. <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" -->
  Author should align metadata.yaml key + README prose + directory name on
  one slug. The human applying the fix does **not** need to bump
  `task.json.version` (broken-set directory is not part of the
  agent-facing contract).
- Coverage axes cross-checked: `data_sources: [bundled-local]` ⇒ L1 matches
  `difficulty_levels: [l1]` and the inventory row. `task.json > tags`
  remain aligned with inventory and `coverage.yaml`.
- pytest on the eval suite (`benchmark/eval`): **41 passed**, no failures.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions > wrong_crs_metadata_only.measured_score`
  (0.4286 → 0.5556) and `wrong_attributes.measured_score` (0.8571 → 0.8889) for
  the current 9-subcheck grader, and retuned the matching
  `expected_score_range` values to encompass the new measurements
  (`[0.3, 0.5]` → `[0.5, 0.6]`; `[0.8, 0.9]` → `[0.85, 0.9]`). Re-grade on
  reference: **1.0** (9/9). Reason: post the 2026-05-28 05aabd6 grader-change
  that added two CRS subchecks, the per-broken-set scores rebased to a
  9-subcheck denominator; metadata was stale.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — reference-or-data-edit-needed — slug mismatch between
  `metadata.yaml > broken_solutions > wrong_crs_metadata_only`, the on-disk
  `reference/failures/broken_wrong_crs/`, and the README's
  `broken_wrong_crs_metadata_only`. Carried forward from prior review.

#### Tests run
- grader on reference: **1.0** (9/9 subchecks)
- grader on broken sets: wrong_format **0.0000** / wrong_crs **0.5556** /
  wrong_attributes **0.8889** — match refreshed metadata
- pytest (`benchmark/eval`): **41 passed**

---

## Manual cleanup 2026-06-06 — gate-2 removal

Benchmark-wide refactor: the second gate (`structural_correctness`) was
removed from `geo_grading.scoring`. Every grader now uses a single hard
gate (`format_schema_valid`) for unrecoverable output, and any check
that can be salvaged with light coercion runs as a `Subcheck` worth one
point.

### Changes in this grader
- Removed `Gate("structural_correctness", ...)` and its early-return.
- Geom-type LineString-family check from Gate 2 dropped — already
  covered (more strictly) by the existing `geometry_type_is_linestring`
  subcheck.
- Feature-count-within-5%-of-reference migrated from Gate 2 to a new
  `feature_count_within_5_percent` subcheck.
- Subcheck count grew from 9 to 10.

### Verification
- Reference solution re-graded: 1.0 (10/10 subchecks).

---

## Evaluator review 2026-06-11  (evaluator-commit d661724)

### 1. Design history

#### Initial design intent
Unchanged from prior reviews. L1 CRS-reprojection task: 272 NYC cycleway
LineString segments arrive as EPSG:3857 (Web Mercator) GeoParquet from an
upstream tile-renderer, and the agent must reproject to EPSG:4326 (WGS84)
GeoParquet while preserving the `LineString` geometry type, the `id` join
key, and the full attribute schema (`class`, `subclass`, `name`). Persona:
Marcus Chen, NYC DOT bike-program analyst, feeding a Leaflet front-end.
Neither CRS is named in the instruction; the agent must infer the source
from the file metadata and the target from "plain lat/lon".

#### Change log
Commits prior to 2026-06-06 are documented in earlier evaluator blocks. New
commits touching this task since the 2026-06-06 evaluator review (4a311db):

| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-06-06 | 363aed2 | grader-change | Dropped the `structural_correctness` gate: geom-type LineString-family check removed (already covered more strictly by the `geometry_type_is_linestring` subcheck), count-within-5% migrated from gate to a new `feature_count_within_5_percent` subcheck. Subcheck count 9 -> 10. | Commit msg: gate was inconsistent across the 36 graders (mostly hard, sometimes soft); library now has a single hard `format_schema_valid` gate and every salvageable check is a subcheck. (Also documented in the "Manual cleanup 2026-06-06" appendix above.) |
| 2026-06-07 | 05b389b | grader-change | Tagged the six data-content subchecks (count, id-Jaccard, IoU, per-feature length, total length, attributes) with `weight=3.0`; the four schema/structural subchecks (geom type, NYC envelope, two CRS checks) stay at 1.0. Total weight 22. | Commit msg: "so a clean-schema-wrong-data submission scores visibly lower than a correct-data slightly-off-schema one". |
| 2026-06-07 | 3fd36df | grader-change | Added `_ensure_id_column()`: if `id` is the DataFrame index rather than a column (agent did `set_index("id")`), reset it back to a column before comparators run; applied to both submission and reference. | Commit msg: instruction says "use id as the key"; some agents implement that via `set_index("id")` and the grader KeyError'd (observed: run-20260606-1733Z scored null with a grader_error traceback). |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:56:45Z** (commit 3fd36df, class:
  grader-change).
- `task.json` carries no `version` field (implicitly v1); all runs record
  `task_version: 1`, so the version check cannot distinguish pre- from
  post-grader-change runs and the timestamp cutoff is the operative test
  (the Step 2b fallback).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T08:49:17Z | 1.0 | done | current (suite ec540aa contains 3fd36df) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-09T06:49:43Z | 1.0 | done | current (suite 6510297 contains 3fd36df) |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T11:25:53Z | 1.0 | done | stale (pre-cutoff by ~7.5 h) |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T17:36:50Z | null (grader_error) | done | stale (pre-cutoff; the KeyError'd run that motivated 3fd36df) |

Footnote - ~27 earlier runs (2026-05-12 -> 2026-06-06) were classified in
prior evaluator blocks and remain stale. Re-graded locally with the current
grader at this audit: run-20260606-1733Z's output (id in the index, the
crash case) now scores **1.0** - its 272 features, CRS, columns, and bbox
match the reference exactly, confirming 3fd36df rescued a genuinely correct
output rather than papering over a wrong one. run-20260607-112430Z's output
also re-grades 1.0.

#### Verdict
**insufficient-evidence** (strict) / **calibrated** (interpretive)

Strictly, only two runs are post-cutoff and both are DeepSeek V4 Flash
(one model family), so Step 2d reads `insufficient-evidence`. Interpretively
the task remains calibrated: the three grader-change commits since the last
review alter weighting and crash-robustness, not the answer key - a correct
output still scores 1.0 (verified against the reference and four recent run
outputs), and the broken sets still land at distinct levels (0.0 / 0.5455 /
0.8636). Across the full post-prompt-rewrite window the task has been
cleared at 1.0 by Gemma 4 26B, DeepSeek V4 Flash (basic and detailed
prompts), and earlier Claude Opus / DeepSeek runs. Recording
`insufficient-evidence` in `status.json` per the strict rule, consistent
with the 2026-06-06 block.

Output-CRS / format consistency (Step 2c-CRS): reference output is EPSG:4326
GeoParquet, matching `expected_outputs[]` and the README. The length
subchecks reproject **both** sub and ref to EPSG:3857 (symmetric); the
grader's one-sided reprojection of the submission to canonical implements
the declared `grade_crs_soft` accept-policy. No inconsistency.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `nyc_cycleways_wgs84.geoparquet`, GeoParquet | instruction | stated |
| some usable CRS declared (hard gate) | GeoParquet convention | inferable |
| feature count within 5% / id set Jaccard >= 0.95 | "convert them over" (pure conversion implies same features) | inferable |
| LineString only (no MultiLineString upcast) | instruction | stated |
| attributes `class`/`name` preserved | instruction ("leave the attributes alone") | stated |
| `id` usable as join key | instruction ("use `id` as the key") | stated |
| coordinates in NYC lon/lat envelope; IoU/lengths match | faithful reprojection to "plain lat/lon" | inferable |
| declared CRS EPSG:4326 (two weight-1 subchecks) | "plain lat/lon" + WGS84 convention | inferable |

Factual claims checked: the input is referenced as "the `nyc_cycleways`
file", matching `task.json > inputs[0].name` (bundled file
`inputs/nyc_cycleways_webmercator.geoparquet` - the only input, so
unambiguous); output filename, format, and the LineString constraint all
verified against `inputs/` and the reference output schema. No missing or
inaccurate claim.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: read GeoParquet, `to_crs`
EPSG:4326, write GeoParquet, attributes untouched. The defensive
`sort_values("id")` is a determinism measure, not a content change (row
order is not graded). No deviation.

#### Specific findings
- Verdict **insufficient-evidence** (strict; both current runs are one
  model family) - interpretively calibrated; no prompt, grader, tolerance,
  or reference change warranted. Next mixed-family sweep will resolve it;
  no flag, since the grader changes since the last review are
  score-preserving for correct outputs.
- Stale bookkeeping fixed: `metadata.yaml > broken_solutions` measured
  scores still reflected the unweighted 10-subcheck grader (0.5556 /
  0.8889); under the 05b389b 3x weighting they are 0.5455 / 0.8636
  (re-measured this audit). Descriptions referencing "Gate 2" and "/9"
  denominators refreshed in the same edit. Unilateral edit, no version
  bump required.
- README "Failure modes" section still described the two-gate grader
  (Gate 2 count tolerance, hard CRS-EPSG gate) and the pre-weighting
  0.43 score for the restamped-CRS case. Rewritten to match the current
  single-gate weighted grader (0.55), and its broken-set references
  aligned to the on-disk `broken_wrong_crs` name. Unilateral docs-change.
- Grader-change commits 363aed2 / 05b389b / 3fd36df did not bump
  `task.json.version` (still implicit v1), so run validity had to be
  decided by the Step 2b timestamp fallback plus suite-sha ancestry. No
  action: the fallback is authoritative and the changes are
  score-preserving for correct outputs; noted for awareness.
- Carried forward - broken-set slug mismatch, now reduced to two-way:
  `metadata.yaml > broken_solutions` key `wrong_crs_metadata_only` vs.
  on-disk `reference/failures/broken_wrong_crs/` (README now uses the
  directory name). Cosmetic; nothing programmatic consumes the key. The
  remaining fix (rename the directory, or the metadata key) touches
  `reference/failures/` on one side, so per precedent it stays flagged.
  <!-- HUMAN-REVIEW id="HR-001" category="reference-or-data-edit-needed" severity="low" -->
  Author should align the metadata key and the directory on one slug
  (suggest renaming the metadata key to `wrong_crs` to match the
  directory; no `task.json.version` bump needed since the broken-set
  name is not part of the agent-facing contract).
- pytest (`benchmark/eval`): **41 passed**.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions` measured scores for the
  weighted grader (`wrong_crs_metadata_only` 0.5556 -> 0.5455;
  `wrong_attributes` 0.8889 -> 0.8636; `wrong_format` unchanged 0.0) and
  rewrote the stale "Gate 2" / "/9" description prose. Re-grade on
  reference: 1.0. Reason: 05b389b re-weighted six subchecks to 3.0,
  rebasing every broken-set score to a 22-point denominator.
- `README.md`: failure-modes section updated from the two-gate grader to
  the current single-gate weighted grader (count check is now a subcheck,
  CRS mismatch docks two weight-1 subchecks instead of hard-failing,
  restamped-CRS score 0.43 -> 0.55), input path `data/` -> `inputs/`,
  broken-set references aligned to `broken_wrong_crs`. Re-grade on
  reference: 1.0. Reason: docs drifted across three grader refactors.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 - reference-or-data-edit-needed - residual slug mismatch between
  `metadata.yaml > broken_solutions > wrong_crs_metadata_only` and the
  on-disk `reference/failures/broken_wrong_crs/`. Carried forward (5th
  consecutive review); cannot rename the directory unilaterally.

#### Tests run
- grader on reference: **1.0** (10/10 subchecks, weighted 22/22)
- grader on broken sets: wrong_format **0.0** / wrong_crs **0.5455** /
  wrong_attributes **0.8636** - match refreshed metadata
- grader on recent run outputs: run-20260608-074701Z 1.0,
  run-20260609-084636Z 1.0, run-20260607-112430Z 1.0,
  run-20260606-1733Z 1.0 (post-3fd36df re-grade of the crashed run)
- pytest (`benchmark/eval`): **41 passed**

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change this run
Per-task reasoned subcheck weights replace the blunt 05b389b "weight=3.0 on
the six data-content subchecks, 1.0 on everything else" scheme. This is a
**grading-only** change: only `Subcheck(weight=)` values in `grade.py` were
touched. No check logic, thresholds, gates, task.json version, inputs,
reference, or failures were modified.

### Reasoning
This is a CRS-category task, so per the operator's directive CRS correctness
should dominate the score - but the output CRS here is canonical EPSG:4326 and
the grader reprojects any submission to canonical before the geometric
subchecks. The "central skill" is therefore **whether the coordinates were
actually transformed** from Web Mercator metres to lat/lon, not whether the
file carries a `4326` metadata label. The weights were rebalanced so the
checks that *prove the reprojection happened* (coordinate envelope, IoU,
per-feature length, total length = 14 of 20 weighted points) dominate, while
the bare CRS-metadata-declaration subchecks were demoted to 0.5 each.

Under 05b389b the central proof check (`coordinates_within_nyc_lonlat_envelope`)
sat at the cosmetic weight 1.0, while structural-preservation checks that a
faithful reprojection gets for free (count, id-set) sat at 3.0 - exactly
backwards from what the task tests. The two CRS-label checks together carried
weight 2.0 (10% of a 22-point budget), over-rewarding the mere declaration.

Critical invariant verified: an **honestly-unprojected** file (correct
geometry, CRS left as EPSG:3857) scores **0.95** (loses only the two cheap
CRS-label subchecks), while a **dishonest** "stamped 4326 but never
transformed" file scores **0.30**. A file that declares the right CRS but
never transformed the coordinates never beats honest work - it scores well
below it. This is the operator's directive made concrete.

### Weight changes (subcheck: old -> new)
| Subcheck | old | new | rationale |
|---|---|---|---|
| feature_count_within_5_percent | 3.0 | 1.0 | structural; a pure reprojection preserves it for free - does not prove the transform |
| geometry_type_is_linestring | 1.0 | 1.0 | unchanged; discrete contract (no MultiLineString upcast) |
| feature_id_set_preserved | 3.0 | 1.0 | structural preservation; trivially held through reprojection |
| coordinates_within_nyc_lonlat_envelope | 1.0 | 4.0 | THE canonical proof the reprojection happened; was miscalibrated as cosmetic |
| geometry_iou_high | 3.0 | 4.0 | geometric proof coordinates moved correctly; central |
| per_feature_length_matches | 3.0 | 3.0 | unchanged; geometric proof of correct transform |
| total_network_length_within_1_percent | 3.0 | 3.0 | unchanged; catches systematic scale error |
| identifying_attributes_preserved | 3.0 | 2.0 | real contract ("leave attributes alone") but secondary to the reprojection itself |
| crs_is_canonical | 1.0 | 0.5 | mere metadata label; must not dominate per directive |
| crs_in_meaningful_set | 1.0 | 0.5 | mere metadata label; must not dominate per directive |

Total weight 22 -> 20.

### Broken-score before -> after
| Broken set | before | after | severity note |
|---|---|---|---|
| wrong_format | 0.0 | 0.0 | unreadable bytes; hard gate collapses score (unchanged) |
| wrong_crs (restamped-only) | 0.5455 | 0.30 | central-skill failure: reprojection never happened (and file lies about it) - now scored hard |
| wrong_attributes | 0.8636 | 0.90 | secondary contract slip (dropped class/name); cosmetic, lightly docked |

Ordering is now sensible and monotone: 0.0 < 0.30 < 0.90 < 1.0. The most
severe error (lost/faked the central reprojection skill) sits far below the
cosmetic attribute slip; no disjoint-failure inversion (the wrong_crs failure
group and the wrong_attributes failure group are disjoint, and the central
group is weighted heavier, so up-weighting it does not reward a worse broken).

### Prior-run re-grade summary
The AUTHORING_HISTORY-listed `current` runs (run-20260609-084636Z,
run-20260608-074701Z) plus run-20260607-112430Z and the rescued
run-20260606-1733Z all scored 1.0 before and 1.0 after - no shift. Correct
outputs are unaffected by reweighting since the reference still scores 1.0
(all subchecks pass). No notable shifts.

### Tests run
- grader on reference: **1.0** (10/10 subchecks, weighted 20/20)
- grader on broken sets: wrong_format **0.0** / wrong_crs **0.30** /
  wrong_attributes **0.90** - match refreshed metadata
- prior current runs re-graded: run-20260609-084636Z, run-20260608-074701Z,
  run-20260607-112430Z, run-20260606-1733Z all 1.0 -> 1.0
- pytest: not run (orchestrator runs the suite)

### HUMAN-REVIEW items
- HR-001 (reference-or-data-edit-needed, slug mismatch between
  `metadata.yaml > broken_solutions > wrong_crs_metadata_only` and on-disk
  `reference/failures/broken_wrong_crs/`) is carried forward unchanged - it
  is a reference/data edit, not a weighting issue.
