# Implementation notes — fio-l1-paris-kml-pois

## Status
completed

## Prompt version
2026-05-08-a

## Summary
L1 format-I/O task: a Google-My-Maps style KML with three Folders of
Paris late-night POIs → flat GeoJSON in EPSG:4326 carrying `name`,
HTML-stripped `description`, and parent-Folder-as-`category`. Reference,
grader, and three broken solutions built and verified inside the
project Docker container.

## Verification results
- Reference grader score: 1.00 (6 / 6 subchecks pass).
- Broken-solution scores:
  - wrong_format: 0.000 (expected range [0.0, 0.0]) — Gate 1 rejects
    (the original KML has no `name`/`description`/`category`
    columns).
  - html_not_stripped: 0.667 (expected range [0.55, 0.75]) — 4 / 6
    pass; both `description_html_stripped` and
    `description_content_preserved` fail (HTML noise tokens crowd
    out the stripped reference tokens).
  - axis_swap: 0.833 (expected range [0.78, 0.90]) — 5 / 6 pass; only
    `geometry_preserved_per_name` fails (Points mirrored across y=x).
- Second-run output match: bit-identical (verified with `diff -q` on
  `reference/outputs/paris_pois.geojson` before / after a second
  `reference/generate.py` run inside Docker).
- Library tests after task: pass (32 / 32).

## Failure-mode coverage
- Output not converted (still KML / wrong format): broken_wrong_format
- HTML left in description: broken_html_not_stripped
- KML axis-order swap (lat,lon ↔ lon,lat): broken_axis_swap
- Single-layer read losing two Folders entirely: principled — Gate 2
  row-count check
- All categories collapsed into one bucket: principled —
  `category_populated_and_recognised` + `category_values_match`
- Reprojected to non-WGS84: principled — Gate 1 CRS check
- Z dimension preserved (Point Z instead of Point 2-D): not directly
  graded; tolerated cosmetic deviation
- Entity decoding without tag stripping (or vice versa): principled —
  `description_html_stripped` checks both tag and entity regex

## Open issues
- [severity: low] The Overture release `2026-04-15.0` does not have a
  Paris-area `tourist_information_center` / `visitor_center` /
  `information_center` category in `places.place`. The folder
  "Tours et infos touristiques" instead pulls from
  `sightseeing_tour_agency` / `tours` / `boat_tours`. The persona
  story still works (a transport-planning intern's colleague would
  curate "where can night-bus riders find help" loosely), and the
  inventory's "tourist info booths" example was always indicative,
  but flagging here for review.

## Suggested prompt changes
(none)

## Inventory change proposals
(none — the row's `OSM tags` column says
`amenity=*` (mix of cafes, libraries, tourist info booths)`. Cafes
and libraries map cleanly; tourist info booths were swapped for
sightseeing-tour points to keep the bundled file populated. If the
orchestrator wants the row to reflect Overture availability the
"tourist info booths" wording could be relaxed to "tour /
information points".)

## Library extensions
(none — the grader uses `Gate`, `Subcheck`, `ScoreReport`, and the
existing `feature_set_equality_by_id` primitive. HTML and token
checks are inline regex/set work.)

## Runtime
~12 minutes (one Overture slice fetch ~30 s per category × 3, the
rest local Docker runs).

---

## Evaluator review 2026-05-26  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
A L1 format-I/O task: convert a hand-authored Google-My-Maps style KML (45
placemarks split across three `<Folder>` blocks) into a flat WGS84 GeoJSON
with `name`, HTML-stripped `description`, and the parent-Folder label
carried through as a `category` attribute. The persona is an RATP
transport-planning intern preparing data for an internal map server that
rejects HTML and only accepts GeoJSON / GeoParquet. The skill probed is
"format literacy": iterating KML layers (since pyogrio exposes Folders as
separate layers and the Folder name as a layer, not a Placemark column),
correctly stripping both raw `<…>` tags and HTML entities from
CDATA-wrapped descriptions, and respecting KML's `lon,lat` axis order.
This matches the inventory row's design intent verbatim (Paris, bundled
KML, EPSG:4326 in/out, Point, small scale, `amenity=*` mix).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 16422f3 | initial-authoring | Initial task: README, IMPLEMENTATION_NOTES, KML input + `_prepare_input.py`, grader, metadata, reference generator + outputs, three broken-solution sets (wrong_format, html_not_stripped, axis_swap), task.json | (initial) |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` | Commit msg: "tasks: add image-prompt.md to all 36 task directories" — repo-wide asset addition |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` task-card asset | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dictionary to `task.json` (region, data_source, formats, crs, geometry_type, operations, themes, quality_issues, scale) | Commit msg: "add structured tags... for filtering. Values derived from the inventory axes." Tags are metadata only — they do not appear in the prompt the agent sees, hence docs-class for design-affecting purposes |
| 2026-05-13 | a3a8d53 | docs-change | Moved tree from `benchmark/eval/tasks/` to `benchmark/tasks/` | Commit msg: "tasks: move benchmark/eval/tasks/ to benchmark/tasks/" |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` via fal.ai FLUX schnell | Commit msg: as titled |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` via nano-banana-2 | Commit msg: as titled |
| 2026-05-14 | 68384e4 | prompt-change | Stripped phrase "— a Google My Maps export with HTML-formatted descriptions and the categories sitting in the folder names" from the instruction | Commit msg: "Strip deducible information from FIO task instructions. Remove input CRS mentions, geometry type descriptions, explicit column enumerations, format descriptions, and data value examples that models can discover by reading file metadata." |
| 2026-05-17 | b4583b4 | prompt-change | Replaced "the description as plain text (no tags, no entities), and the parent folder label as a `category` attribute" with "the description as plain text, and include the classification/grouping from the source data as a `category` attribute" | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts" — but the same commit also softens the FIO description / folder hints. <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> The commit message names CRS tasks; the actual diff also touches this FIO task's instruction. Intent presumably matches the broader "strip-deducible-info" thrust of the earlier 68384e4 commit, but the message does not state it explicitly. |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `sub.crs.to_epsg() == 4326` with `is_wgs84(sub.crs)` import from `geo_grading` | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package... None → True per RFC 7946." Semantically a no-op for this task because the task pins EPSG:4326 explicitly; `is_wgs84(None)` would now return True but the reference and all submissions declare a CRS. |
| 2026-05-26 | 29a9ae3 | mixed (docs/grader/data path-rename) | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `data/_prepare_input.py` → `inputs/_prepare.py`, `reference/generate.py` + outputs → `reference/solution/`, `tests/` → `reference/failures/`, image assets → `assets/`. `grade.py` `REFERENCE_OUT` constant updated to the new path. | Commit msg: "Reorganize task folder layout... separates audience concerns (machine contract, audit history, inputs, reference + failures, eval-UI assets)." No behavioral change — only path strings. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: 2026-05-26T09:51:37Z (commit 29a9ae3, class: mixed — folder reorg with a touch on grade.py path constant). Note: this is a pure path-rename and does not change grader logic or the answer key. The last semantically-meaningful change is the prompt edit at b4583b4 (2026-05-17T12:48:37Z). I treat runs ≥ b4583b4 as "current" (the reorg cannot retroactively change the score of a run whose output already exists, since the grader still reads the same JSON file content), and runs after the prompt edit as evidence for the current prompt.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:39:10Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:50:20Z | 1.0 | done | current |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:33:26Z | 1.0 | done | current |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T08:39:01Z | 1.0 | done | stale (pre-b4583b4) |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T04:19:58Z | 1.0 | done | stale |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T02:24:06Z | 0.833 | done | stale (only description_content_preserved fails) |
| run-20260516-2248Z | claude-code-opus-basic | 2026-05-17T00:14:58Z | 0.833 | done | stale |
| run-20260516-1130Z | claude-code-opus-basic | 2026-05-16T20:59:50Z | 0.833 | done | stale |
| run-20260516-0743Z | claude-code-opus-basic | 2026-05-16T08:35:37Z | 0.833 | done | stale |
| run-20260515-2053Z | claude-code-opus-basic | 2026-05-16T06:45:40Z | 0.833 | done | stale |
| run-20260515-0926Z | openrouter-deepseek-v4-flash-basic | 2026-05-15T11:50:12Z | 1.0 | done | stale |
| run-20260515-0624Z | claude-code-opus-basic | 2026-05-15T07:41:11Z | 0.833 | done | stale |
| run-20260514-1554Z | claude-code-opus-basic | 2026-05-14T16:47:14Z | 0.833 | done | stale |
| run-20260514-1245Z | claude-code-opus-basic | 2026-05-14T13:51:12Z | 1.0 | done | stale |
| run-20260514-0946Z | claude-code-opus-basic | 2026-05-14T10:31:04Z | 0.833 | done | stale |
| (earlier runs from 2026-05-12 / 05-13, scores 0.833–1.0) | — | — | — | done | stale |

Three current runs, all from different adapter families (gemma-4-26B, deepseek-v4-flash, claude-opus), all scoring 1.0.

#### Verdict
**too-easy-suspected, but evidence is thin**

All three current runs score 1.0. Two prompt-stripping commits (68384e4 and b4583b4) deliberately removed gifts ("Google My Maps export", "HTML-formatted descriptions", "categories sitting in the folder names", "no tags, no entities", "parent folder label as a `category`") and softened the per-attribute hand-holding. The current instruction is appropriately spare: "convert it to `paris_pois.geojson` with one row per placemark, keeping `name`, the description as plain text, and include the classification/grouping from the source data as a `category` attribute. EPSG:4326 Points." The EPSG:4326 mention is defensible because GeoJSON conventionally pins WGS84 (RFC 7946) — keeping it harmless. The output filename and the field list are necessary contract; the persona voice is preserved. I see no further gifts to strip without dropping required information.

However, the stale-but-numerous opus 0.833 runs reveal a latent issue with the grader's `description_content_preserved` subcheck: any agent that strips HTML via BeautifulSoup `.get_text()` (default separator `""`) concatenates the four `<br/>`-separated phrases into a single token (e.g. `arabicacatégorie`, `tardvoir`, `fichedernière`). The verification date — the metadata.yaml rationale's stated "load-bearing token" — is still present, but the token-set overlap drops to ~45–55%, well below the 80% per-row threshold and the 95% aggregate threshold. The metadata explicitly promises this should pass ("an agent that reformats whitespace, uppercases, or normalises punctuation differently still passes"); the implementation does not match that promise. The newer opus runs (e.g. run-20260517-1254Z) score 1.0 because that agent inserted spaces when stripping — so the issue is intermittent, model-specific, and arguably an agent-engineering nit. Still, the metadata-vs-grader gap is real.

#### Specific findings
- The current instruction is appropriately stripped of giveaway hints (no mention of "KML", "Google My Maps", "Folder", "HTML"). Models still solve it cleanly. No further unilateral prompt edit is safe — additional stripping risks breaking the contract.
- <!-- HUMAN-REVIEW id="HR-002" category="grader-miscalibration-suspected" severity="med" --> `description_content_preserved` in `grade.py:248-254` uses a token-set overlap whose tokeniser regex `[A-Za-zÀ-ÿ0-9-]+` does NOT treat whitespace boundaries as separators independent of the surrounding text. When an agent strips `<br/>` to `""` (BeautifulSoup `.get_text()` default), neighbouring words concatenate (`ArabicaCatégorie`), and the per-row overlap drops well below 0.8 despite all "content" tokens (including the verification date) being preserved in raw form. The metadata.yaml rationale explicitly promises this case should pass ("an agent that reformats whitespace, uppercases, or normalises punctuation differently still passes — only an agent that drops content... fails"). Six opus runs between 2026-05-14 and 2026-05-17 hit exactly this path and scored 0.833. Possible fixes (a) widen the tokeniser to split on CamelCase boundaries before comparison, (b) require the agent to pass a tag-replacement test with a single canonical "load-bearing" token (the verification date) instead of bulk token overlap, (c) accept the grader as-is and tighten the metadata wording. I do not edit `grade.py` unilaterally because this is a judgment call between three plausible fixes and changes which side of the grader/instruction line gets adjusted.
- <!-- HUMAN-REVIEW id="HR-003" category="inventory-mismatch" severity="low" --> `authoring/inventory.md:228` lists `OSM tags: amenity=* (mix of cafes, libraries, tourist info booths)` but the third Folder is "Tours et infos touristiques" (sightseeing-tour points), not tourist info booths. The author's own `## Open issues` block in `audit/AUTHORING_HISTORY.md` flagged this same gap. Either soften the inventory wording to "tour / information points" or accept the discrepancy as inventory-shorthand.
- <!-- HUMAN-REVIEW id="HR-004" category="coverage-vocabulary-gap" severity="low" --> The task's `tags.quality_issues` is `["html_content"]` but `authoring/coverage-vocabulary.yaml > data_quality_issues` has no slug covering HTML-in-attribute-text (the closest, `inconsistent-attribute-values`, is for spelling/casing differences). I leave `data_quality_issues: []` in `coverage.yaml` and add a free-text `notes` entry.
- The HTML-stripping subcheck (`description_html_stripped`) and the per-name category / geometry checks all behave as designed and have caught the documented broken-solution failure modes (broken_html_not_stripped: 0.667; broken_axis_swap: 0.833; broken_wrong_format: 0.000) — these are still calibrated.

### 3. Changes applied this run

#### Unilateral edits
(none — every change considered was either a judgment call or affected a file outside the evaluator's authority)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit b4583b4 message names CRS tasks but also softens this FIO prompt; rationale not explicit.
- HR-002 — grader-miscalibration-suspected — `description_content_preserved` tokeniser is harsher on whitespace-removing HTML-stripping than the metadata rationale claims; three plausible fixes.
- HR-003 — inventory-mismatch — `inventory.md` row says "tourist info booths" but the actual third Folder is sightseeing-tour points.
- HR-004 — coverage-vocabulary-gap — No slug in `coverage-vocabulary.yaml > data_quality_issues` matches the HTML-in-attribute-text issue this task introduces.

#### Tests run
- grader on reference (`reference/solution/outputs`): 1.0 (6 / 6 subchecks pass).
- pytest: pass (35 / 35).

---

## Evaluator review 2026-05-27  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
An L1 format-I/O task: convert a hand-authored Google-My-Maps style KML (45
placemarks split across three `<Folder>` blocks) into a flat WGS84 GeoJSON
carrying `name`, an HTML-stripped `description`, and the parent-Folder label
carried through as a `category` attribute. The persona is Margaux Léger, an
RATP transport-planning intern, preparing data for an internal map server
that rejects HTML and only accepts GeoJSON / GeoParquet. The probed skill is
"format literacy": iterating KML layers (pyogrio exposes each `<Folder>` as a
separate layer, with the Folder name available only as the layer name, not as
a Placemark column), scrubbing both raw `<…>` tags and HTML entities from
CDATA-wrapped descriptions, and respecting KML's `lon,lat` axis order. This
matches the inventory row's design intent (Paris, bundled KML, EPSG:4326
in/out, Point, small scale, `amenity=*` mix). Verified against the first
commit (16422f3, 2026-05-08) and the README / author block.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 16422f3 | initial-authoring | Initial task: README, IMPLEMENTATION_NOTES, KML input + `_prepare_input.py`, grader, metadata, reference generator + outputs, three broken-solution sets (wrong_format, html_not_stripped, axis_swap), task.json | (initial) |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` (repo-wide) | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` task-card asset | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json` (metadata only — not shown to the agent) | Commit msg: "add structured tags... for filtering. Values derived from the inventory axes." |
| 2026-05-13 | a3a8d53 | docs-change | Moved tree `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: as titled |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` via fal.ai FLUX schnell | Commit msg: as titled |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` via nano-banana-2 | Commit msg: as titled |
| 2026-05-14 | 68384e4 | prompt-change | Removed phrase "— a Google My Maps export with HTML-formatted descriptions and the categories sitting in the folder names" from the instruction (diff verified) | Commit msg: "Strip deducible information from FIO task instructions. Remove input CRS mentions, geometry type descriptions, explicit column enumerations, format descriptions, and data value examples that models can discover by reading file metadata." |
| 2026-05-17 | b4583b4 | prompt-change | Replaced "the description as plain text (no tags, no entities), and the parent folder label as a `category` attribute" with "the description as plain text, and include the classification/grouping from the source data as a `category` attribute" (diff verified) | Commit msg: "Remove CRS/operation nudges from 5 CRS task prompts". <!-- HUMAN-REVIEW id="HR-001" category="design-rationale" severity="low" --> The commit message names CRS tasks only, but the same diff also softens this FIO instruction's HTML / folder hints. Intent presumably continues the strip-deducible-info thrust of 68384e4, but the message does not state it for this task. |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `sub.crs.to_epsg() == 4326` with shared `is_wgs84(sub.crs)` from `geo_grading` (diff verified) | Commit msg: "Consolidate WGS 84 CRS checks into shared geo_grading package... None → True per RFC 7946." Semantic no-op here: the reference and every submission declare a concrete CRS, so the `is_wgs84(None) → True` path is never exercised; the task still pins EPSG:4326 explicitly. |
| 2026-05-26 | 29a9ae3 | mixed (docs / data path-rename; grade.py path constant) | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/generate.py`+outputs → `reference/solution/`, `tests/` → `reference/failures/`, assets → `assets/`. `grade.py` `REFERENCE_OUT` path constant updated only (diff verified — single-line path string change, no logic change). | Commit msg: "Reorganize task folder layout..." |
| 2026-05-26 | 5ccf699 | docs-change (prior evaluator) | First evaluator-review block appended to `audit/AUTHORING_HISTORY.md`; `coverage.yaml` + `audit/status.json` written. No task-file edits. | Commit msg: "Re-evaluate fio-l1-paris-kml-pois: too-easy on current adapters, but description_content_preserved grader is overly strict on whitespace-removing HTML stripping" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-18T06:35:57Z** (commit f0c244a, class: grader-change). This is the most recent commit touching grader logic. Strictly applying the prompt's rule (max timestamp across prompt-/grader-/reference-/data-/tests-change), f0c244a sets the cutoff. The later 29a9ae3 (2026-05-26) touches `grade.py` but only the `REFERENCE_OUT` path string — verified no logic change — so it does not push the cutoff. Note: f0c244a is itself a semantic no-op for this task (CRS pinned, `is_wgs84(None)` path unreachable), so runs after the prior prompt edit b4583b4 (2026-05-17T12:48:37Z) are also informative; they are listed below and marked stale-but-corroborating.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:39:10Z | 1.0 | done | current |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:50:20Z | 1.0 | done | stale (pre-f0c244a; post-prompt) |
| run-20260517-1254Z | claude-code-opus-basic | 2026-05-17T13:33:26Z | 1.0 | done | stale (pre-f0c244a; post-prompt) |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T08:39:01Z | 1.0 | done | stale |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T04:19:58Z | 1.0 | done | stale |
| run-20260517-0134Z | claude-code-opus-basic | 2026-05-17T02:24:06Z | 0.833 | done | stale (description_content_preserved fails) |
| run-20260516-2248Z | claude-code-opus-basic | 2026-05-17T00:14:58Z | 0.833 | done | stale |
| run-20260516-1130Z | claude-code-opus-basic | 2026-05-16T20:59:50Z | 0.833 | done | stale |
| run-20260516-0743Z | claude-code-opus-basic | 2026-05-16T08:35:37Z | 0.833 | done | stale |
| run-20260515-2053Z | claude-code-opus-basic | 2026-05-16T06:45:40Z | 0.833 | done | stale |
| run-20260515-0926Z | openrouter-deepseek-v4-flash-basic | 2026-05-15T11:50:12Z | 1.0 | done | stale |
| run-20260515-0624Z | claude-code-opus-basic | 2026-05-15T07:41:11Z | 0.833 | done | stale |
| run-20260514-1554Z | claude-code-opus-basic | 2026-05-14T16:47:14Z | 0.833 | done | stale |
| run-20260514-1245Z | claude-code-opus-basic | 2026-05-14T13:51:12Z | 1.0 | done | stale |
| run-20260514-0946Z | claude-code-opus-basic | 2026-05-14T10:31:04Z | 0.833 | done | stale |
| (earlier runs 2026-05-12 / 05-13, scores 0.833–1.0) | — | — | — | done | stale |

Strictly current evidence is a single run (gemma4-26b, 1.0). The two run dirs created 2026-05-26 after this evaluation began (run-20260526-1753Z, run-20260526-1922Z) do not contain this task. Per-output inspection of the one current run: 45 rows (= reference 45), EPSG:4326, columns `{name, description, category, geometry}`, all `Point`, all three Folder categories present — a clean pass on every subcheck.

#### Output-CRS / format consistency (2c-CRS)
- Reference output declares `urn:ogc:def:crs:OGC:1.3:CRS84` (= WGS84) and is read by GeoPandas as EPSG:4326 — matches `expected_outputs[].crs` (EPSG:4326) and README ("EPSG:4326 GeoJSON"). Consistent.
- The grader's CRS check (`is_wgs84(sub.crs)`) reads only the submission's declared CRS; geometry comparison is done coordinate-wise in degrees with both sides in WGS84. No one-sided reprojection. Consistent.

#### Verdict
**too-easy** (strictly `insufficient-evidence` on count of post-f0c244a runs, but the larger corroborating body makes the calibration picture clear)

Only one run is strictly current, which by the letter of Step 2d is `insufficient-evidence`. However, the f0c244a grader change across the cutoff is a verified semantic no-op for this CRS-pinned task, so the 14 stale-but-post-prompt runs across three adapter families (gemma-4-26B, deepseek-v4-flash, claude-opus) remain informative. Every capable agent reaches the answer; scores cluster at 1.0 (full pass) or 0.833 (single subcheck fail). No agent failed a gate or scored below 0.833. The instruction is already appropriately spare after two strip-deducible-info edits (68384e4, b4583b4) — no mention of "KML", "Google My Maps", "Folder", or "HTML" — so there is no further safe gift to remove without breaking the output contract. I therefore record `too-easy` (consistent with the prior 2026-05-26 evaluator), with the grader caveat below. The retained `EPSG:4326 Points` clause is defensible (GeoJSON pins WGS84 by RFC 7946; harmless) and the output filename + field list are necessary contract.

The 0.833 cluster is the same latent grader issue the prior evaluator surfaced (HR-002 here): the `description_content_preserved` subcheck is over-strict against its own documented rationale. Re-confirmed this run by inspecting a stale opus output (run-20260517-0134Z, `too-strict` transcript inspection): the agent stripped tags to the empty string, so words concatenate across former `<br/>` boundaries (`% ArabicaCatégorie : Cafés ouverts tardVoir la ficheDernière vérification : 2026-01-01`) while the reference inserts a space (`% Arabica Catégorie : Cafés ouverts tard Voir la fiche Dernière vérification : ...`). The agent dropped *no* content — including the load-bearing verification date — yet per-row token-set overlap fell to 0.45–0.54, below the 0.8 threshold, so 42/43 rows "failed" and the subcheck reported 1/43. `metadata.yaml` explicitly promises this case passes ("an agent that reformats whitespace... still passes — only an agent that drops content... fails"). The grader contradicts that contract.

#### Specific findings
- The instruction is already stripped of giveaway hints; capable agents solve it cleanly and the lone current run scores 1.0. No further unilateral prompt edit is safe — additional stripping would drop required contract information.
- <!-- HUMAN-REVIEW id="HR-002" category="grader-miscalibration-suspected" severity="med" --> `description_content_preserved` (`grade.py:228-254`) tokenises with `[A-Za-zÀ-ÿ0-9-]+`, which does not treat former tag boundaries as token separators. When an agent strips HTML tags to `""` (e.g. BeautifulSoup `.get_text()` default), neighbouring words concatenate, dropping per-row token overlap to ~0.45–0.54 even though every content token (incl. the verification date) is preserved verbatim. `metadata.yaml` rationale promises this should pass. Six+ stale opus runs (2026-05-14 → 2026-05-17) scored 0.833 on exactly this path; the lone current run avoided it only because gemma inserted spaces. Plausible fixes: (a) normalise CamelCase / letter-boundary joins in both sides before tokenising; (b) replace bulk token overlap with a check for the single load-bearing token (the verification date) plus an HTML-free check; (c) keep the grader and soften the metadata wording. This is a which-side-of-the-line judgment call, so I do not edit `grade.py` unilaterally.
- <!-- HUMAN-REVIEW id="HR-003" category="inventory-mismatch" severity="low" --> `authoring/inventory.md:228` lists `OSM tags: amenity=* (mix of cafes, libraries, tourist info booths)` but the third KML Folder is "Tours et infos touristiques" (sightseeing-tour points), not tourist info booths — Overture 2026-04-15.0 lacked a Paris-area tourist-information category. The author's own `## Open issues` note flags the same gap. Either soften the inventory wording to "tour / information points" or accept it as inventory shorthand. (inventory.md is outside the task dir; flagged, not edited.)
- <!-- HUMAN-REVIEW id="HR-004" category="coverage-vocabulary-gap" severity="low" --> The task's central data twist is HTML-noise (CDATA tags + entities) inside an attribute column. `authoring/coverage-vocabulary.yaml > data_quality_issues` has no slug for HTML-in-attribute-text; the closest, `inconsistent-attribute-values`, is for spelling/casing. Not mechanical to derive from a thesis-table row, so I do not add it to the vocabulary — `coverage.yaml > data_quality_issues` is left empty with a free-text note.
- The HTML-stripping, name-set, per-name category, and per-name geometry subchecks all behave as designed and catch the documented broken-solution failure modes. Re-graded the three broken sets this run: broken_wrong_format 0.0, broken_html_not_stripped 0.667, broken_axis_swap 0.833 — all match `metadata.yaml > broken_solutions.measured_score` exactly. (Note: the docstring inside `reference/failures/_make_brokens.py` for `make_html_not_stripped` says "5/6 ≈ 0.833", but the live broken set scores 0.667 and `metadata.yaml` records 0.667 correctly; the stale docstring is in `reference/failures/`, which the evaluator may not edit. Low-impact, not separately flagged.)

### 3. Changes applied this run

#### Unilateral edits
(none — the only material calibration issue, HR-002, is a judgment call between three plausible fixes that change which side of the grader/instruction line is adjusted; per the prompt I flag rather than resolve it. All other proposed changes touch files outside the evaluator's authority.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — design-rationale — Commit b4583b4 message names only CRS tasks but the same diff softens this FIO instruction; rationale not stated for this task.
- HR-002 — grader-miscalibration-suspected — `description_content_preserved` is over-strict on whitespace-removing HTML stripping vs. its own metadata rationale; three plausible fixes.
- HR-003 — inventory-mismatch — inventory.md says "tourist info booths" but the third Folder is sightseeing-tour points.
- HR-004 — coverage-vocabulary-gap — no `data_quality_issues` slug for HTML-in-attribute-text.

#### Tests run
- grader on reference (`reference/solution/outputs`): 1.0 (6 / 6 subchecks pass).
- broken-set re-grade: wrong_format 0.0, html_not_stripped 0.667, axis_swap 0.833 (all match metadata).
- pytest: pass (35 / 35).

---

## Evaluator review 2026-05-28  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
An L1 format-I/O task: convert a hand-authored Google-My-Maps style KML (45
placemarks across three `<Folder>` blocks) into a flat WGS84 GeoJSON
preserving `name`, the parent-Folder label as `category`, and extracting
the "last verified" ISO date from each placemark's HTML info card. The
persona is Margaux Léger, an RATP transport-planning intern, preparing
data for an internal map server that only accepts GeoJSON or GeoParquet
and is flagging stale records. The probed skill is "format literacy":
iterating KML layers (pyogrio exposes each `<Folder>` as a separate
layer, with the Folder name available only as the layer name, not as a
Placemark column), respecting KML's `lon,lat` axis order, and plucking
one structured field out of a CDATA-wrapped HTML blob with mixed tags
and French entities. Matches the inventory row (Paris, bundled KML,
EPSG:4326 in/out, Point, small scale, `amenity=*` mix). Verified against
the initial commit (16422f3, 2026-05-08) and the README.

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 | 16422f3 | initial-authoring | Initial task: README, IMPLEMENTATION_NOTES, KML input + `_prepare_input.py`, grader, metadata, reference generator + outputs, three broken-solution sets (wrong_format, html_not_stripped, axis_swap), task.json | (initial) |
| 2026-05-13 | 8915010 | docs-change | Added `image-prompt.md` (repo-wide) | Commit msg: "tasks: add image-prompt.md to all 36 task directories" |
| 2026-05-13 | 1b8dda1 | docs-change | Generated `image.webp` task-card asset | Commit msg: "tasks: generate image.webp for all 36 task directories" |
| 2026-05-13 | 284b843 | docs-change | Added `tags` dict to `task.json` (metadata only — not shown to the agent) | Commit msg: "add structured tags... for filtering." |
| 2026-05-13 | a3a8d53 | docs-change | Moved tree `benchmark/eval/tasks/` → `benchmark/tasks/` | Commit msg: as titled |
| 2026-05-13 | 3c65373 | docs-change | Regenerated `image.webp` via fal.ai FLUX schnell | Commit msg: as titled |
| 2026-05-13 | cfbdc7c | docs-change | Regenerated `image.webp` via nano-banana-2 | Commit msg: as titled |
| 2026-05-14 | 68384e4 | prompt-change | Removed phrase "— a Google My Maps export with HTML-formatted descriptions and the categories sitting in the folder names" from the instruction | Commit msg: "Strip deducible information from FIO task instructions..." |
| 2026-05-17 | b4583b4 | prompt-change | Replaced "the description as plain text (no tags, no entities), and the parent folder label as a `category` attribute" with "the description as plain text, and include the classification/grouping from the source data as a `category` attribute" | Commit msg names CRS tasks only; same diff also softens this FIO instruction. Continues the strip-deducible-info thrust of 68384e4. |
| 2026-05-18 | f0c244a | grader-change | Replaced inline `sub.crs.to_epsg() == 4326` with shared `is_wgs84(sub.crs)` from `geo_grading` | Commit msg: "Consolidate WGS 84 CRS checks..." Semantic no-op here. |
| 2026-05-26 | 29a9ae3 | mixed (docs / data path-rename; grade.py path constant) | Folder reorg: `IMPLEMENTATION_NOTES.md` → `audit/AUTHORING_HISTORY.md`, `data/` → `inputs/`, `reference/generate.py`+outputs → `reference/solution/`, `tests/` → `reference/failures/`, assets → `assets/`. `grade.py` `REFERENCE_OUT` path constant only. | Commit msg: "Reorganize task folder layout..." |
| 2026-05-26 | 5ccf699 | docs-change (prior evaluator) | First evaluator-review block appended to `audit/AUTHORING_HISTORY.md`; `coverage.yaml` + `audit/status.json` written. No task-file edits. | Commit msg: "Re-evaluate fio-l1-paris-kml-pois: too-easy..." |
| 2026-05-27 | 70d80ac | docs-change (prior evaluator) | Second evaluator-review block appended (re-confirmed `too-easy` + carried HR-001/HR-002/HR-003/HR-004). | Commit msg: "Re-evaluate fio-l1-paris-kml-pois: too-easy on capable agents..." |
| 2026-05-28 | 622342b | docs-change | Added `version` field to `task.json` (implicit v1 before, set to `2` in the next functional edit). Removed unused `prompt_version` from `metadata.yaml`. No grader/instruction/input change. | Commit msg: "Add task content versioning..." |
| 2026-05-28 | b1480ba | mixed (prompt-change + grader-change + reference-change + tests-change) | **Resolved HR-002.** Redesigned the task: instruction now asks for a `verified_date` ISO column instead of a flat plain-text description; grader subcheck set rewritten around `verified_date` (name set, category populated/recognised, per-name category match, geometry, verified_date ISO-format on raw JSON, per-name verified_date value match — 6 total); `reference/solution/generate.py` extracts the date instead of stripping HTML; `reference/failures/_make_brokens.py` replaced `broken_html_not_stripped` with `broken_verified_date_missing`; metadata.yaml rationale + broken_solutions rewritten; README task contract refreshed; `task.json.version` bumped to 2; redundant "EPSG:4326 Points" suffix stripped from prompt. | Commit msg: "Resolve fio-l1-paris-kml-pois HR-002 via verified_date extraction redesign." Explicit, multi-paragraph rationale: prior description-stripping grader scored stripping idiom (BeautifulSoup `.get_text()` vs. tag-to-space regex) rather than data extraction; the only HTML line carrying non-redundant data was the verification date; collapsing the column down to that single load-bearing field tests the actual GIS-format-literacy skill without scoring whitespace heuristics. |
| 2026-05-28 | fbb3596 | docs-change | Drained the answered HR-002 entry from `audit/status.json` per the updated review-queue skill (bundle resolution into the Resolve commit going forward). | Commit msg: "review-queue: clear resolved-HR entries..." |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T11:55:07Z** (commit b1480ba, class: mixed prompt/grader/reference/tests change). This is the resolve-HR-002 redesign — instruction, grader, reference outputs, broken-set generator, and metadata all changed in one commit. Every prior run was scored under the v1 description-stripping contract and is no longer comparable.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260528-0317Z | openrouter-gemma4-26b-basic | 2026-05-28T03:45:44Z | 1.0 | done | stale (pre-cutoff; v1 schema) |
| run-20260528-0113Z | claude-code-opus-basic    | 2026-05-28T02:17:15Z | 1.0 | done | stale (pre-cutoff; v1 schema) |
| run-20260527-2321Z | openrouter-gemma4-26b-basic | 2026-05-27T23:55:49Z | 1.0 | done | stale |
| run-20260527-2016Z | claude-code-opus-basic    | 2026-05-27T21:30:06Z | 1.0 | done | stale |
| run-20260526-0748Z | openrouter-gemma4-26b-basic | 2026-05-26T08:39:10Z | 1.0 | done | stale |
| run-20260517-1424Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T15:50:20Z | 1.0 | done | stale |
| run-20260517-1254Z | claude-code-opus-basic    | 2026-05-17T13:33:26Z | 1.0 | done | stale |
| run-20260517-0614Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T08:39:01Z | 1.0 | done | stale |
| run-20260517-0304Z | openrouter-deepseek-v4-flash-basic | 2026-05-17T04:19:58Z | 1.0 | done | stale |
| run-20260517-0134Z | claude-code-opus-basic    | 2026-05-17T02:24:06Z | 0.833 | done | stale (v1 — description_content_preserved fail) |
| (and 19 earlier runs from 2026-05-12 → 05-16, mostly opus 0.833 / sonnet & deepseek 1.0) | — | — | — | — | stale |

No `current` runs exist post-b1480ba; the redesign just landed today and the next sweep has not yet run.

#### Output-CRS / format consistency (2c-CRS)
- Reference output declares `urn:ogc:def:crs:OGC:1.3:CRS84` (= WGS84), read by GeoPandas as EPSG:4326. Matches `expected_outputs[].crs` (EPSG:4326) and README ("EPSG:4326 GeoJSON"). Consistent.
- The grader's CRS check (`is_wgs84(sub.crs)`) reads only the submission's declared CRS; geometry comparison is done coordinate-wise in degrees with both sides in WGS84. No one-sided reprojection. Consistent.

#### Verdict
**insufficient-evidence**

The b1480ba redesign has zero post-cutoff runs. Diagnostic verdict from runs is therefore deferred until the next sweep produces samples against v2.

That said, the grader and broken-set sanity checks all pass cleanly:
- Reference scores 1.0 (6/6 subchecks pass).
- broken_wrong_format = 0.0, broken_axis_swap = 0.833 (5/6), broken_verified_date_missing = 0.667 (4/6) — all match `metadata.yaml > broken_solutions.measured_score` exactly. Three distinct ranges; grader has resolution.
- pytest passes 41/41.
- The redesign is well-targeted: the verified_date column is the single load-bearing piece of information in the HTML description, the format-vs-value split lands a partial-extract at 0.833 (a clear partial-credit signal), and the prompt cleanly asks for that single extraction without naming "KML"/"Folder"/"BeautifulSoup"/etc.
- HR-002 from prior reviews is **resolved** by b1480ba and dropped from `human_review_items`.
- HR-001 (rationale gap on b4583b4) was a historical-curiosity flag that the redesign overtakes — the strip of "EPSG:4326 Points" in b1480ba is justified explicitly in the commit body, so the lingering rationale concern on b4583b4 has no live consequence for the v2 grader/instruction. I drop HR-001 from the carried-forward list.

#### Specific findings
- Instruction is appropriately spare for an L1 (66 words, ≤ 80 budget). Names only the persona's problem, the input handle, the output filename, the three columns, and the date-extraction operation. No procedural decomposition, no library names, no CRS hand-holding. The "we want to flag stale records" tail is a why-line that motivates the persona's date column — it's not a gift, it's the legitimate framing of why the column exists. Keep.
- The instruction does not say `KML`, `HTML`, `Folder`, or `Google My Maps`; the agent must discover all three by reading the input file. The `category` column is described as "the source's classification/grouping" — sufficient for an agent to discover the Folder structure on inspection but not a gift. Keep.
- Grader subchecks are well-separated: schema, structural count, name set, category populated, category per-name match, geometry per-name match, date ISO format (raw JSON to bypass pyogrio auto-typing), date per-name value match. Each subcheck targets a distinct failure mode the broken set covers.
- 2c-CRS check: consistent (see above).
- <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Carried from prior reviews (was HR-003): `authoring/inventory.md:228` still reads `OSM tags: amenity=* (mix of cafes, libraries, tourist info booths)` but the third KML Folder is "Tours et infos touristiques" (sightseeing-tour points). The b1480ba commit updated the inventory's Output-artifacts line and Story but did not touch this OSM-tags line. Authors's own original Open-issues note flags the same gap. Either soften the inventory wording to "tour / information points" or accept it as inventory shorthand. inventory.md is outside the task dir; flagged, not edited.
- <!-- HUMAN-REVIEW id="HR-002" category="coverage-vocabulary-gap" severity="low" --> Carried from prior reviews (was HR-004): the task's `tags.quality_issues` is `["html_content"]`; the central data twist is that the verification date is buried inside CDATA-wrapped HTML with French entities. `authoring/coverage-vocabulary.yaml > data_quality_issues` has no slug for HTML-in-attribute-text (the closest, `inconsistent-attribute-values`, is for spelling/casing). Still not mechanical to derive from a thesis-table row, so I do not add it to the vocabulary unilaterally; `coverage.yaml > data_quality_issues` is left empty with the free-text note.

### 3. Changes applied this run

#### Unilateral edits
(none — the task-file contract is well-calibrated post-b1480ba; the two carried HR items both target files outside the evaluator's authority or require a controlled-vocabulary judgment call.)

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — inventory.md OSM-tags line still says "tourist info booths" but third Folder is sightseeing-tour points (carried from prior reviews' HR-003).
- HR-002 — coverage-vocabulary-gap — no `data_quality_issues` slug for HTML-in-attribute-text (carried from prior reviews' HR-004).

#### Tests run
- grader on reference (`reference/solution/outputs`): 1.0 (6 / 6 subchecks pass).
- broken-set re-grade: wrong_format 0.0, axis_swap 0.833, verified_date_missing 0.667 (all match metadata.yaml).
- pytest: pass (41 / 41).

---

## Evaluator review 2026-06-06  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
An L1 format-I/O task: convert a hand-authored Google-My-Maps style KML (45
placemarks across three `<Folder>` blocks) into a flat WGS84 GeoJSON
preserving `name`, the parent-Folder label as `category`, and extracting
the "last verified" ISO date from each placemark's HTML info card.
Persona: Margaux Léger, an RATP transport-planning intern preparing
data for an internal map server that only accepts GeoJSON or GeoParquet
and is flagging stale records. Probed skill: format literacy —
iterating KML layers (pyogrio exposes each `<Folder>` as a separate
layer), respecting KML's `lon,lat` axis order, and plucking one
structured field out of a CDATA-wrapped HTML blob with mixed tags and
French entities. Matches the inventory row (Paris, bundled KML,
EPSG:4326 in/out, Point, small scale, `amenity=*` mix).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 → 2026-05-28 | (see prior evaluator-review blocks) | — | All earlier commits up to and including b1480ba (verified_date redesign) and fbb3596 (status-drain) | Carried forward — see 2026-05-26 / 2026-05-27 / 2026-05-28 blocks. |
| 2026-05-28 | 05aabd6 | grader-change | Replaced the inline `is_wgs84(sub.crs)` Gate-1 hard-fail with `grade_crs_soft(sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True)`. Adds two new subchecks `crs_is_canonical` and `crs_in_meaningful_set`, both with `MEANINGFUL_EPSGS={4326}` / `CANONICAL_EPSG=4326`. Submission gets reprojected to canonical for downstream geometric subchecks. Subcheck total goes 6 → 8. | Commit msg: "Soften CRS hard-fail to subcheck deductions across 21 graders. Previously a CRS mismatch hard-failed Gate 1 and sank the score to 0 — even when the agent's geometric work was correct, just delivered in the wrong CRS." Repo-wide policy change, applied uniformly. For this task the meaningful set is `{4326}` so a non-WGS84 submission still scores `(N-2)/N` rather than 0; canonical (4326) still scores full. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-05-28T19:02:57Z** (commit 05aabd6, class: grader-change). Two new subchecks landed, raising the subcheck total to 8. Every prior run with `task_version: 2` was scored under the 6-subcheck grader and is no longer numerically comparable, but the underlying decision-tree (which submissions pass / fail) is unchanged because the two new subchecks both pass cleanly when the submission declares EPSG:4326 (which the contract demands and every observed agent does). I therefore mark pre-05aabd6 v2 runs as stale-but-corroborating where useful.

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260606-1334Z | openrouter-gemma4-26b-detailed | 2026-06-06T13:56:29Z | — | cancelled (sweep cancelled before this task started) | current (not informative) |
| run-20260606-1129Z | openrouter-gemma4-26b-detailed | 2026-06-06T11:55:44Z | 0.0 | done | current — Gate 2 fail: single-layer KML read returned 20 of 45 rows (failure mode #4) |
| run-20260606-0953Z | openrouter-gemma4-26b-detailed | 2026-06-06T10:05:13Z | 0.875 | done | current — `verified_date_iso_format` fails (agent wrote `YYYY-MM-DDTHH:MM:SS` not `YYYY-MM-DD`); values still match |
| run-20260529-0902Z | openrouter-deepseek-v4-pro-basic | 2026-05-31T12:31:01Z | 1.0 | done | current |
| run-20260529-0109Z | openrouter-gemma4-26b-basic | 2026-05-29T02:16:01Z | 1.0 | done | current |
| run-20260528-2332Z | claude-code-opus-basic | 2026-05-29T00:11:11Z | 1.0 | done | current |
| run-20260528-2225Z | openrouter-gemma4-26b-basic | 2026-05-28T23:05:30Z | 1.0 | done | current |
| run-20260528-1927Z | claude-code-opus-basic | 2026-05-28T21:32:25Z | 1.0 | done | current |
| run-20260528-1624Z | openrouter-gemma4-26b-basic | 2026-05-28T17:33:17Z | 1.0 | done | stale (post-redesign v2, pre-CRS-soft) |
| (29 earlier runs) | various | 2026-05-12 → 2026-05-28T03:45Z | 0.0 – 1.0 | done / failed | stale (v1 schema or pre-cutoff) |

7 current `done` runs across three adapter families (gemma4-26b basic + detailed, claude-opus, deepseek-v4-pro). 5 score 1.0; one scores 0.875 (subcheck #5 — date string formatted as ISO 8601 datetime instead of date — clean partial-credit signal); one scores 0.0 (Gate 2 row-count rejection from single-layer KML read — the canonical L1 failure mode this task is designed to catch). Adapter-family spread is good (claude, gemma, deepseek).

#### Output-CRS / format consistency (2c-CRS)
- Reference output declares `urn:ogc:def:crs:OGC:1.3:CRS84` (= WGS84), read by GeoPandas as EPSG:4326. Matches `expected_outputs[].crs` (EPSG:4326) and README ("EPSG:4326 GeoJSON"). Consistent.
- The grader's CRS gate (`grade_crs_soft`) only hard-fails when there is no usable CRS at all; otherwise the submission is reprojected to canonical 4326 for downstream geometric subchecks. Both sides of the geometry comparison are now in canonical EPSG:4326. No one-sided reprojection that papers over a contract mismatch — contract, README, and reference all agree on 4326. Consistent.

#### Verdict
**calibrated**

Three current adapter families span the full range the grader resolves: full pass (1.0), single-subcheck loss (0.875, ISO-vs-datetime), and Gate-2 reject (0.0, single-layer read). The grader gates and subchecks each fire on a distinct, principled failure mode and the broken-set re-grade lands at three well-separated tiers (0.0 / 0.75 / 0.875 / 1.0). The two CRS subchecks added in 05aabd6 don't change any observed verdict because every current submission declared EPSG:4326. The instruction is already spare (66 words, no mention of KML / Folder / HTML / Google My Maps) and the design intent — agent must discover the KML layer structure and the HTML extraction pattern by inspection — is intact. No latent grader/instruction inconsistency surfaced this sweep.

#### Specific findings
- The reference grader scores 1.0 (8/8) post-CRS-soft, broken sets re-grade to wrong_format 0.0, axis_swap 7/8=0.875, verified_date_missing 6/8=0.75. The previous `metadata.yaml > broken_solutions.measured_score` values (0.833 / 0.667) are pre-CRS-soft; refreshed unilaterally per Step 4. New values still fall within the author-set `expected_score_range`s (axis_swap [0.78, 0.90], verified_date_missing [0.55, 0.75]), so no range adjustment needed.
- The cancelled / Gate-2 / 0.875 runs from the 2026-06-06 gemma sweep are all legitimate signal: row-count rejection (failure mode #4 — single-layer KML read) and ISO-vs-datetime formatting (failure mode #8 — date kept in a longer string variant) are both the intended grader catches. The model-side issues in the 2026-06-06 sweep (context-length blow-ups, max-iteration runaways) hit other tasks; this task itself ran cleanly when it ran.
- The HTML-extraction skill is well-probed: agents that emit `2026-01-01T00:00:00` rather than `2026-01-01` correctly identify the date but lose the format subcheck, exactly the design intent.
- <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Carried from prior reviews: `authoring/inventory.md:228` still reads `OSM tags: amenity=* (mix of cafes, libraries, tourist info booths)` but the third KML Folder is "Tours et infos touristiques" (sightseeing-tour points). The b1480ba redesign updated the inventory's Output-artifacts and Story lines but not the OSM-tags line. inventory.md is outside the task dir; flagged, not edited.
- <!-- HUMAN-REVIEW id="HR-002" category="coverage-vocabulary-gap" severity="low" --> Carried from prior reviews: the task's central data twist (verification date buried in CDATA-wrapped HTML with French entities) has no slug in `authoring/coverage-vocabulary.yaml > data_quality_issues`. Closest existing slug `inconsistent-attribute-values` is for spelling / casing, not markup. Not mechanical to derive from a thesis-table row, so I do not add it unilaterally; `coverage.yaml > data_quality_issues` left empty with the free-text note.

### 3. Changes applied this run

#### Unilateral edits
- `metadata.yaml`: refreshed `broken_solutions.axis_swap.measured_score` 0.833 → 0.875 and `broken_solutions.verified_date_missing.measured_score` 0.667 → 0.75 to reflect the new 8-subcheck grader (post-05aabd6). Both still inside the author-set ranges. Re-grade on reference: 1.0 (8/8). Per Step 4, `measured_score` refresh does **not** require a `version` bump.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — inventory.md OSM-tags line still says "tourist info booths" but third Folder is sightseeing-tour points (carried from prior reviews).
- HR-002 — coverage-vocabulary-gap — no `data_quality_issues` slug for HTML-in-attribute-text (carried from prior reviews).

#### Tests run
- grader on reference (`reference/solution/outputs`): 1.0 (8 / 8 subchecks pass).
- broken-set re-grade: wrong_format 0.0, axis_swap 0.875, verified_date_missing 0.75 (all match the refreshed metadata.yaml).
- pytest: pass (41 / 41).

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
- Row-count ±5 % migrated to a new `row_count_within_tolerance`
  subcheck.
- Subcheck total grew from 8 to 10.

### Verification
- Reference solution re-graded: 1.0 (10/10 subchecks).

---

## Evaluator review 2026-06-12  (evaluator-commit <will-be-filled-after-commit>)

### 1. Design history

#### Initial design intent
Unchanged from the prior reviews (see the 2026-05-28 and 2026-06-06
blocks): an L1 format-I/O task converting a hand-authored
Google-My-Maps style KML (45 placemarks across three `<Folder>`
blocks) into a flat WGS84 GeoJSON carrying `name`, the parent-Folder
label as `category`, and the "Dernière vérification" ISO date
extracted from each placemark's CDATA-wrapped HTML info card.
Persona: Margaux Léger, RATP transport-planning intern. Probed skill:
format literacy (multi-layer KML reads, Folder-as-category, lon,lat
axis order, targeted extraction from HTML with French entities).

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| 2026-05-08 → 2026-05-28 | (see prior evaluator-review blocks) | — | All earlier commits up to 05aabd6 (CRS soft-fail) | Carried forward — see 2026-05-26 / 2026-05-27 / 2026-05-28 / 2026-06-06 blocks. |
| 2026-06-06 | b4878fd | docs-change (prior evaluator) | Fourth evaluator-review block appended (verdict calibrated); `metadata.yaml > broken_solutions.measured_score` refreshed to the 8-subcheck totals (0.875 / 0.75). | Commit msg: "Re-evaluate fio-l1-paris-kml-pois: calibrated post-CRS-soft; refresh broken_solution scores to 8-subcheck totals" |
| 2026-06-06 | 363aed2 | grader-change | Removed the `structural_correctness` gate and its early-return; geometry-type uniformity and row-count ±5 % migrated to two new subchecks (`geometry_type_point_only`, `row_count_within_tolerance`); subcheck total 8 → 10. The "Manual cleanup 2026-06-06" note above was appended in the same commit. | Commit msg: "Drop Gate 2 from graders; one hard gate, rest are subchecks" — repo-wide consistency refactor: 34 of 36 graders early-returned on the second gate, collapsing recoverable submissions to 0. |
| 2026-06-07 | c749e57 | grader-change | Tagged five data-content subchecks with `weight=3.0` (`row_count_within_tolerance`, `name_set_preserved`, `category_values_match`, `geometry_preserved_per_name`, `verified_date_values_match`); schema/structural checks stay at 1.0. Score becomes weighted: denominator 20. | Commit msg: "Weight data-content subchecks 3x across all categories" — repo-wide policy so data-content failures cost more than schema nits. |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: **2026-06-07T18:32:38Z** (commit c749e57, class: grader-change). The earlier 363aed2 (2026-06-06T20:11:02Z) is also design-affecting; c749e57 is the max. Neither commit changes the instruction, inputs, or answer key — they only re-shape scoring — so pre-cutoff v2 outputs remain meaningful when re-graded under the current grader (and run-20260607-112430Z's `score.json` demonstrably *was* re-scored: it carries `weight` fields and a 14/20 = 0.7 total despite a pre-cutoff `suite_git_sha`).

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-20260609-084636Z | openrouter-deepseek-v4-flash-basic | 2026-06-09T10:50:29Z | 1.0 | done | current (v2 ≥ run version; post-cutoff) |
| run-20260608-074701Z | openrouter-deepseek-v4-flash-detailed | 2026-06-08T10:37:52Z | 1.0 | done | current |
| run-20260607-112430Z | openrouter-gemma4-26b-detailed | 2026-06-07T14:57:43Z | 0.7 | done | stale by timestamp (pre-c749e57) but re-scored under the weighted grader (`score.json` carries weights) — corroborating |
| run-20260606-1733Z | openrouter-gemma4-26b-detailed | 2026-06-06T18:29:45Z | 0.875 | done | stale (pre-363aed2; 7/8 under the 8-subcheck grader) |
| (33 earlier runs, 2026-05-12 → 2026-06-06) | various | — | 0.0 – 1.0 | done / cancelled | stale (v1 schema or pre-cutoff; see prior blocks) |

Note: the current `task.json` version is 3 after this review's house-style edit; the two `current` runs above were scored against version 2. The version bump changes prompt punctuation only (em-dash removal), not any constraint, so they remain the best available evidence.

Per-output inspection of both current runs: 45 rows (= reference), EPSG:4326, columns `{name, category, verified_date, geometry}`, all `Point`, all three Folder categories present, all 10 subchecks pass. The corroborating gemma run is the canonical single-layer-read failure: 20 rows, name Jaccard 0.4186, loses `row_count_within_tolerance` + `name_set_preserved` (both weight 3) → 14/20 = 0.7, exactly the failure mode the task is designed to catch, now with partial credit instead of the old Gate-2 zero.

#### Output-CRS / format consistency (2c-CRS)
- Reference output declares `urn:ogc:def:crs:OGC:1.3:CRS84` (= WGS84), read as EPSG:4326. Matches `expected_outputs[].crs` (EPSG:4326) and README ("EPSG:4326 GeoJSON" / RFC 7946). Consistent.
- `grade_crs_soft` hard-fails only when no usable CRS exists; otherwise the submission is reprojected to canonical 4326 before geometric subchecks (declared accept-list policy, `MEANINGFUL_EPSGS={4326}`). No one-sided reprojection papering over a contract mismatch. Consistent.

#### Verdict
**calibrated**

Two strictly-current runs both score 1.0, but they are one agent family (deepseek-v4-flash, basic + detailed prompts) — by the letter of Step 2d that alone is `insufficient-evidence`. However, the cutoff commits changed only score shaping, not the contract, and the re-scored gemma run (0.7, single-layer read) plus the broken-set re-grade give the weighted grader demonstrable resolution across the intended failure ladder: 0.0 (no conversion) / 0.7 (single-layer read) / 0.8 (date never extracted) / 0.85 (axis swap) / 0.95 (date left embedded) / 1.0 (full pass). Each tier maps to a distinct, principled failure mode; capable agents reach 1.0 and the canonical weak-agent mistake now receives partial credit rather than a gate zero. That is the calibration the task was designed for.

#### Prompt information audit
| Grader constraint | Where the agent learns it | Status |
|---|---|---|
| output file `paris_pois.geojson`, GeoJSON | instruction | stated |
| columns `name`, `category`, `verified_date` | instruction | stated |
| `verified_date` literal `YYYY-MM-DD` string | instruction ("as an ISO date") | stated |
| one row per placemark (45 rows, ±5 %) | instruction ("one row per placemark") | stated |
| category = parent Folder label | instruction ("the source's classification/grouping") + input inspection | inferable |
| CRS WGS84 / EPSG:4326 | GeoJSON pins WGS84 by RFC 7946 | inferable |
| geometry Point, coordinates preserved (1e-5°) | conversion semantics + input data | inferable |
| date lives in the HTML blurb | instruction ("out of the HTML blurb") | stated |

Factual claims verified: `paris_late_night_pois` matches `inputs[].name` (extension deliberately omitted, the file is `inputs/paris_late_night_pois.kml`); column names and the ISO-date unit match the reference output schema; "one row per placemark" matches the 45-placemark input. No missing or inaccurate claims.

#### Reference faithfulness
`reference/solution/generate.py` is faithful: it reads every KML layer in source order, carries the layer (Folder) name as `category`, extracts the date by tag-stripping + entity-decoding + regex, writes `name`/`category`/`verified_date`/Point geometry to `paris_pois.geojson` in EPSG:4326. The only operation the prompt does not spell out is dropping the KML Z ordinate (`Point(g.x, g.y)`), which is justified by the instruction's "flat GeoJSON" wording and is grading-neutral (the geometry subcheck compares x/y only). No deviation worth a flag.

#### Specific findings
- The two post-cutoff grader commits (363aed2, c749e57) improved this task's failure ladder: the single-layer read that used to gate to 0.0 now lands at 0.7 with the heavyweight data-content subchecks doing the discrimination. Verified live in run-20260607-112430Z.
- `metadata.yaml > broken_solutions.measured_score` values were stale (8-subcheck totals). Refreshed to the weighted-grader totals: axis_swap 0.875 → 0.85, verified_date_missing 0.75 → 0.8 (wrong_format stays 0.0). Unilateral per Step 4.
- <!-- HUMAN-REVIEW id="HR-003" category="grader-miscalibration-suspected" severity="low" --> `broken_verified_date_missing` now measures 0.8 under the weighted grader, *outside* the author-set `expected_score_range` [0.55, 0.75], because `verified_date_iso_format` kept weight 1.0 while only `verified_date_values_match` got 3.0 in the repo-wide c749e57 sweep. Two resolutions, both above my authority: (a) re-baseline `expected_score_range` to the weighted scale (mechanical but the range is an author-set contract), or (b) decide that `verified_date_iso_format` is itself data-content for this task (its whole point is the literal string on disk) and weight it 3.0, which would put the broken set at 14/22 ≈ 0.64, back inside the range. I refreshed `measured_score` and noted the discrepancy inline in metadata.yaml; the range/weight decision is flagged.
- The instruction contained two em-dashes, violating house style. Rewrote minimally ("GeoParquet — please convert" → "GeoParquet, so please convert"; "ISO date — we want" → "ISO date. We want"); every constraint, the persona voice, and all deliberate omissions (no KML / Folder / HTML-structure / CRS mention) preserved. `version` bumped 2 → 3. Reference re-grade after the edit: 1.0.
- `analyst_notes` was missing from `task.json`; authored it (description + 5 approach steps + 5 pitfalls, no version-bump implication).
- README's failure-mode section still described the removed Gate 2, claimed non-WGS84 CRS "rejects" at Gate 1 (soft subchecks since 05aabd6), and quoted pre-redesign scores (0.667 / 0.833 / "5/6 ≈ 0.833"). Updated to the single-gate weighted-grader reality (docs-change, no bump).
- The stale docstring in `reference/failures/_make_brokens.py` (pre-redesign score math) persists; that file is outside evaluator authority and the discrepancy is cosmetic — noted, not flagged.
- <!-- HUMAN-REVIEW id="HR-001" category="inventory-mismatch" severity="low" --> Carried from prior reviews: `authoring/inventory.md` (row "fio-l1-paris-kml-pois", OSM-tags field) still reads `amenity=* (mix of cafes, libraries, tourist info booths)` but the third KML Folder is "Tours et infos touristiques" (sightseeing-tour points). inventory.md is outside the task dir; flagged, not edited.
- <!-- HUMAN-REVIEW id="HR-002" category="coverage-vocabulary-gap" severity="low" --> Carried from prior reviews: no slug in `coverage-vocabulary.yaml > data_quality_issues` covers HTML-in-attribute-text (CDATA-wrapped tags + French entities hiding the date payload). Closest slug `inconsistent-attribute-values` is for spelling/casing. Not mechanical to derive from the thesis table, so not added unilaterally; `coverage.yaml > data_quality_issues` stays empty with the free-text note.

### 3. Changes applied this run

#### Unilateral edits
- `task.json`: removed two em-dashes from the instruction per house style (content otherwise verbatim); authored the missing `analyst_notes`; bumped `version` 2 → 3. Re-grade on reference: 1.0. Reason: house-style compliance and the analyst-notes authoring duty.
- `metadata.yaml`: refreshed `broken_solutions.measured_score` to weighted-grader totals (axis_swap 0.85, verified_date_missing 0.8) and corrected the stale subcheck math in both descriptions. Re-grade on reference: 1.0. Reason: Step 4 measured_score refresh after the c749e57 weighting commit.
- `README.md`: failure-modes section updated from Gate-1/Gate-2 wording and pre-redesign scores to the single-gate weighted grader (docs-change, no bump). Reason: stale README vs. grader reality.

#### Proposed but not applied (see HUMAN-REVIEW items)
- HR-001 — inventory-mismatch — inventory.md OSM-tags line still says "tourist info booths"; third Folder is sightseeing-tour points (carried).
- HR-002 — coverage-vocabulary-gap — no `data_quality_issues` slug for HTML-in-attribute-text (carried).
- HR-003 — grader-miscalibration-suspected — `broken_verified_date_missing` measures 0.8, outside the author-set expected range [0.55, 0.75], after the repo-wide 3x weighting; re-baseline the range or weight `verified_date_iso_format` 3.0.

#### Tests run
- grader on reference (`reference/solution/outputs`): 1.0 (gate + 10/10 subchecks, weighted).
- broken-set re-grade: wrong_format 0.0, axis_swap 0.85, verified_date_missing 0.8.
- pytest: pass (41 / 41).

---

## Evaluator review 2026-06-14  (evaluator-commit <pending>)

### Change in one line
Replaced the blunt repo-wide 3x content weighting (c749e57) with per-task
reasoned subcheck weights that scale with error severity, so a central-skill
failure (HTML date extraction or Folder-aware multi-layer read) drops the
score meaningfully while a cosmetic slip (wrong CRS declaration, Z-point,
date-left-embedded) barely moves it. Resolves HR-003. Grading-only change;
`task.json` version untouched.

### What the task centrally tests
Per `task.json.analyst_notes`, the README "What this task probes", and the
metadata rationale, this is a KML→GeoJSON format-literacy task with two
distinctive twists: (1) the per-feature `category` lives in the parent
`<Folder>` (which pyogrio exposes only as a separate layer), so the agent
must iterate layers — a single-layer read drops 2 of 3 Folders; and (2) the
"last verified" date is buried in a CDATA-wrapped HTML info card and must be
extracted as a literal ISO `YYYY-MM-DD`. The classic KML `lon,lat` axis-order
trap is a third, more generic conversion-correctness hazard. Subchecks that
detect failure of the two central twists are weighted highest; the axis check
next; structural/cosmetic checks lowest.

### Weight changes (subcheck: old -> new)
| Subcheck | old | new | Rationale |
|---|---|---|---|
| `geometry_type_point_only` | 1.0 | 1.0 | Cosmetic (Z-points tolerated); unchanged. |
| `row_count_within_tolerance` | 3.0 | 3.0 | Central: detects single-layer-read row loss; unchanged. |
| `name_set_preserved` | 3.0 | **3.5** | Central: strongest signal of wholesale row/Folder loss; bumped 0.5 so the single-layer-read failure is the lowest non-gate tier. |
| `category_populated_and_recognised` | 1.0 | **2.0** | Central-ish: detects lost/collapsed Folder-as-category shape. |
| `category_values_match` | 3.0 | 3.0 | Central: per-name Folder-as-category correctness; unchanged. |
| `geometry_preserved_per_name` | 3.0 | 3.0 | Conversion correctness (axis swap); unchanged. |
| `verified_date_iso_format` | 1.0 | **2.0** | Medium: right value, wrong shape. Up-weighted (this was the HR-003 under-weight). |
| `verified_date_values_match` | 3.0 | **4.0** | Central twist: HTML date extraction is a headline skill; highest weight. |
| `crs_is_canonical` | 1.0 | **0.5** | Cosmetic: WGS84 is inferable (RFC 7946); a wrong CRS declaration is a minor slip. |
| `crs_in_meaningful_set` | 1.0 | **0.5** | Cosmetic, as above. |

Total weight: 20.0 -> 22.5.

### Broken / observed scores (before -> after)
| Class / mode | before | after | Severity note |
|---|---|---|---|
| `wrong_format` | 0.0 | 0.0 | Gate reject (no conversion). |
| single-layer read (run-20260607-112430Z) | 0.700 | 0.711 | Wholesale row/Folder loss — lowest non-gate tier. |
| `verified_date_missing` | 0.800 | 0.733 | Central column entirely empty — now below axis-swap and inside the re-set range (was the HR-003 out-of-range case). |
| `axis_swap` | 0.850 | 0.867 | One localised geometry error. |
| date-left-embedded (mode #8) | 0.950 | ~0.911 | Cosmetic shape slip; right value. |
| wrong-CRS (mode #6) | ~0.900 | ~0.956 | Cosmetic declaration slip; lightest. |
| reference | 1.0 | 1.0 | Full pass (unchanged). |

Ordering is now monotone and sensible:
`wrong_format` 0.0 < single-layer 0.711 < date-missing 0.733 < axis-swap
0.867 < date-embedded 0.911 < wrong-CRS 0.956 < reference 1.0. The more
central/severe the error, the lower the score; cosmetic slips cluster near
the top. No disjoint-failure inversion (verified date-missing stays below
axis-swap because the date pair 2.0+4.0=6.0 outweighs the single geometry
3.0; single-layer stays below date-missing because name_set 3.5 + row_count
3.0 = 6.5 > 6.0).

### Prior-run re-grade summary
Re-graded the three runs the prior block lists as current/corroborating
(at the unchanged task version):
| Run | old | new |
|---|---|---|
| run-20260609-084636Z (deepseek-v4-flash basic) | 1.0 | 1.0 |
| run-20260608-074701Z (deepseek-v4-flash detailed) | 1.0 | 1.0 |
| run-20260607-112430Z (gemma4-26b, single-layer read) | 0.700 | 0.711 |
No significant shifts: the two full-pass runs are invariant under any
weighting; the single-layer-read run moves +0.011 and remains the lowest
non-gate tier.

### Reasoning
The c749e57 sweep applied `weight=3.0` to five "data-content" subchecks and
left everything at 1.0, which made `verified_date_iso_format` (weight 1) too
cheap relative to its sibling value check — so a complete failure to extract
the date (`broken_verified_date_missing`) scored 0.8, *above* its author-set
range and barely below a single axis-swap. That under-weighted the headline
HTML-extraction skill and over-weighted cosmetic CRS nits. The new weights
rank subchecks by how central the skill they guard is: the two central twists
(date extraction; Folder/row preservation) sit at 3.0-4.0, the axis check at
3.0, and the cosmetic checks (geometry-type, both CRS) at 0.5-1.0. The
resulting severity ladder is monotone and each tier maps to a distinct,
principled failure mode.

### Threshold/check observations (noted, NOT changed)
- The metadata rationale (line ~21) still says an over-aggressive Folder drop
  "trips the gate" — stale wording since Gate 2 was removed (363aed2);
  row-count is now a subcheck. Prose nit, outside this grading-only weight
  change; not edited.
- No threshold or check logic was altered. The 1e-5° geometry tolerance, the
  ±5% row-count band, the 0.95 Jaccard floor, and the 0.99 per-name match
  rates are all unchanged.

### Changes applied this run
#### Unilateral edits
- `grade.py`: subcheck `weight=` values only (table above). No logic change.
- `metadata.yaml`: `broken_solutions.axis_swap` and `.verified_date_missing`
  `measured_score` + `expected_score_range` re-set to the new measured values
  (axis_swap 0.867 / [0.84, 0.89]; verified_date_missing 0.733 / [0.70, 0.75]);
  rationale extended with the weight-policy paragraph.
- `README.md`: stale score fractions and weight annotations in the
  failure-mode list refreshed (0.8→0.733, 0.85→0.867, 0.7→~0.711, 19/20=0.95→~0.911).
- `audit/status.json`: HR-003 removed (resolved); HR-001/HR-002 kept;
  unilateral_edits + status fields updated.

#### Carried HUMAN-REVIEW items
- HR-001 — inventory-mismatch — inventory.md OSM-tags line still says
  "tourist info booths"; third Folder is sightseeing-tour points.
- HR-002 — coverage-vocabulary-gap — no `data_quality_issues` slug for
  HTML-in-attribute-text.

#### Tests run
- grader on reference (`reference/solution/outputs`): 1.0 (gate + 10/10 subchecks, weighted).
- broken-set re-grade: wrong_format 0.0, axis_swap 0.867, verified_date_missing 0.733.
- prior-run re-grade: see table above.
- pytest: not run (orchestrator runs the suite).
