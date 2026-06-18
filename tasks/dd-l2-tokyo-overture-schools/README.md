# dd-l2-tokyo-overture-schools

## Story

Aiko Tanaka, a researcher at the Tokyo Metropolitan Government's
Education Bureau, is preparing a summer briefing on school-density
disparities for children aged 8–14 across the 23 special wards. She
has a bundled Overture `places.place` GeoParquet sample and a bbox
polygon for the wards; she needs every school relevant to that age
range that lies inside the polygon, exported as GeoJSON with the
place name (CJK preserved), confidence, and address fields ready for
a colleague's R-based visualisation.

## What this task probes

* **Taxonomic judgment** — the persona's age-8–14 framing maps onto
  Japan's compulsory-education range (小学校 + 中学校). The agent has
  to read that framing and pick Overture's matching
  `categories.primary` set — `{school, elementary_school,
  middle_school, private_school, public_school}` — rather than the
  bare string `school` (too narrow; misses elementary / middle /
  private subtypes) or the broader school family with `preschool` /
  `high_school` (out of range) or specialty schools (`driving_school`,
  `language_school`, etc.).
* Reading **partitioned GeoParquet** — the bundled places slice is
  Hive-bucketed across four `bucket=N/part.parquet` directories. An
  agent that opens one part and ignores the rest gets a fraction of
  the answer.
* **Attribute filter on a nested struct** — the category lives at
  `categories.primary`, not as a top-level column.
* **Spatial join (polygon contains point)** — keep only the points
  whose geometry sits inside the supplied 23-wards polygon.
* **GeoJSON output with non-ASCII text** — Japanese place names must
  round-trip without transliteration or escape mangling.
* **Schema preservation** — confidence and three address sub-fields
  must reach the output.

## Why this difficulty

L2: chains four bounded operations (partitioned read → nested-struct
attribute filter → spatial-join crop → GeoJSON write with attribute
preservation). No discovery step (the Overture slice is bundled), no
fetching, no live data — that would make it L3. More than a single
operation, so above L1.

## Input / output formats

### Inputs

* `data/tokyo_places/bucket={0,1,2,3}/part.parquet` — Hive-partitioned
  GeoParquet, total ~13 400 rows. Schema follows Overture
  `places.place`: nested `categories` struct, `names` struct,
  `addresses` list-of-structs, `geometry` Point in EPSG:4326,
  `confidence` double.
* `data/tokyo_23wards_bbox.geojson` — single Polygon feature in
  EPSG:4326 covering 139.560–139.910 × 35.520–35.820 (the 23 special
  wards rectangle).

### Output

`outputs/tokyo_schools.geojson` — GeoJSON FeatureCollection in
EPSG:4326. Every feature is a Point with these properties:

| key | value |
|---|---|
| `id` | Overture place id |
| `name` | `names.primary` (often CJK, preserved verbatim) |
| `confidence` | float in [0, 1] |
| `address_freeform` | first address record's freeform string |
| `address_locality` | first address record's locality (ward) |
| `address_postcode` | first address record's postcode |

The reference contains 1506 features across four primary categories
(1456 `school`, 37 `elementary_school`, 7 `private_school`, 6
`middle_school`; `public_school` is in the accept-list but has zero
features inside the wards bbox).

## Failure modes

1. **Agent reads only one parquet partition.** Treats the bundled
   data as a single file or globs incorrectly, missing 3/4 of the
   slice. *Detection:* a partition miss yields a high-purity *subset*
   of the reference `school` ids, so under the 2026-06-14 catch-all
   rescue `count_within_tolerance` and `feature_set_jaccard_high` are
   rescued and the single weight-1 `generic_school_retained` flips
   instead (a clean subset is indistinguishable from a deliberately
   dropped catch-all by id-set shape alone). This mode is not reachable
   in practice — the agent-visible input is a single file holding all
   ~13 400 rows, so there is no partition to miss.
2. **Agent skips the spatial crop.** Outputs every school-family
   feature in the slice (~1808 instead of 1506). *Detection:*
   `bbox_crop_applied`, `feature_set_jaccard_high`, and
   `count_within_tolerance` all flip on the `school`-subset;
   `school_category_selection` still passes (right categories). The
   output is a *superset* of the reference (precision below 0.95), so
   the dropped-catch-all rescue does not apply. Covered by
   `broken_no_spatial_crop` (score 0.61).
3. **Agent uses a strict `categories.primary = 'school'` filter.**
   Misses the elementary / middle / private subtypes the age-framing
   implies; output is the 1456-feature `school`-only subset.
   *Detection:* `school_category_selection` flips (Jaccard 1/5 =
   0.2); every other subcheck passes (it keeps the full `school`
   catch-all, so the rescue is moot and `generic_school_retained`
   passes). Covered by `broken_strict_school_only` (score 0.89).
4. **Agent emits the output in the wrong format.** CSV / Parquet /
   plain text under the same filename. *Detection:* Gate 1 rejects
   on JSON-parse / FeatureCollection-shape check. Covered by
   `broken_wrong_format` (score 0.00).
5. **Agent strips schema fields.** Carries `id` + `name` only and
   drops `confidence` + the address fields. *Detection:* either Gate
   1 fails (if the keys are entirely absent) or
   `confidence_field_present` flips (if the keys are kept but
   nulled). Covered by `broken_dropped_attrs` (score 0.94 under the
   2026-06-14 severity weighting, which deliberately prices schema-only drift
   at one point) on the key-present-but-null variant.
6. **Agent overshoots the age range** — includes `preschool` (under
   8) or `high_school` (over 14) or both. *Detection:*
   `school_category_selection` flips (Jaccard between submission's
   category set and the accept-list drops below 0.6); pipeline
   subchecks all still pass. Not covered by a dedicated broken
   solution; principled detector is the category-selection subcheck.
7. **Agent uses a too-broad category filter** (e.g. `LIKE '%school%'`
   matches `driving_school`, `language_school`, `dance_school`).
   *Detection:* `school_category_selection` flips for the same
   reason. Not covered by a broken solution; principled detector is
   the category-selection subcheck.
8. **Agent transliterates CJK names** ("Shibuya Elementary" instead
   of "渋谷小学校") or escapes them with `ensure_ascii=True` and
   re-decodes wrong. *Detection:* `cjk_names_preserved` fails on the
   no-CJK-in-submission branch. Not covered by a broken solution;
   principled detector is the CJK subcheck.
9. **Agent reprojects geometry to a metric CRS** (e.g. EPSG:6677,
   the local JGD2011 plane CRS) before writing GeoJSON. *Detection:*
   the `coords_in_tokyo_window` subcheck fails — coordinates fall
   outside the Tokyo metropolis degree window (would be in the
   millions of metres). Not covered by a broken solution; principled
   detector is the coord-window subcheck.
10. **Agent confuses `categories.primary` with `categories.alternate`**
    and filters on the alternate-category list. *Detection:*
    `school_category_selection` flips because the alternate-tagged
    set diverges from the primary-tagged accept-list. Not covered by
    a broken solution; principled detector is the category-selection
    subcheck.
11. **Agent drops the generic `school` catch-all.** Picks the right
    category family and crops correctly, but within the bare `school`
    rows keeps only those carrying an explicit school-level
    `categories.alternate` tag, reasoning that the generic tag is too
    vague for the age-8-14 framing. Most real schools in the slice
    carry only the generic tag, so this discards the majority. Because
    the kept rows are a clean high-purity *subset* of the reference,
    `count_within_tolerance` and `feature_set_jaccard_high` are rescued
    and only the weight-1 `generic_school_retained` flips. This is a
    defensible-but-narrow reading (four runs across three agent
    families converged on it; see audit HR-001), so it is priced as a
    one-point drop rather than the full count + Jaccard cost. Covered
    by `broken_dropped_catch_all` (score 0.94).

## Expected weak-agent failure modes

Three failure modes are roughly equally likely for current-generation
agents and are designed to be distinguishable:

* **Mode #2 (skipped spatial crop)** — the agent reads the
  partitioned parquet, picks a reasonable category set, but
  overlooks the `tokyo_23wards_bbox` input or treats it as
  descriptive metadata. Scores ~0.61.
* **Mode #6 (over-broad age range)** — the agent reads "school" in
  the persona's plain-language sense and pulls in the
  school-by-level family without checking the 8–14 constraint, so
  the output includes `preschool` and/or `high_school`. Pipeline is
  otherwise perfect. Scores ~0.89.
* **Mode #11 (dropped generic catch-all)** — the agent over-reasons
  about the age framing and keeps only the explicitly-age-tagged
  bare-`school` rows. A defensible but narrow read; scores ~0.94.

Both score well above the wrong-format submission (0.00) and below
a fully correct submission (1.00); the failing subcheck identifies
which mode the agent fell into.
