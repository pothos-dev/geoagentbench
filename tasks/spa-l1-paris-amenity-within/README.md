# spa-l1-paris-amenity-within

## Story (for the human reviewer)

Émilie Dubois on INSEE's municipal census team is tagging an amenity
point dataset with the Paris arrondissement each amenity falls within
for a neighbourhood demographic crosswalk. She has both layers in
Lambert-93 and needs a flat CSV with the OSM id, amenity class, and the
arrondissement number and name — straightforward `within` join, no
shenanigans, but the deliverable must list the 20th arrondissement as
`20` not `20e` for the downstream join into the rest of INSEE's
infrastructure.

## What this task probes

A single spatial-analysis primary operation — *spatial join with the
`within` predicate* — over a multi-layer GPKG, plus an
attribute-parsing wrinkle: extracting an integer from a French ordinal
("Paris 20e Arrondissement" → `20`). The agent must:

1. Read two layers from the same GPKG: 85 amenity Points and 20
   arrondissement Polygons, both already in EPSG:2154 (RGF93 /
   Lambert-93 — France's national projected CRS).
2. Spatially join each amenity to the arrondissement that *contains*
   it (`within`). Every amenity in the bundled fixture lies inside
   exactly one arrondissement — there are no boundary-edge or
   outside-Paris points to disambiguate.
3. Parse the integer arrondissement number out of the
   `names.primary` value: "Paris 1er Arrondissement" → 1, "Paris 2e
   Arrondissement" → 2, …, "Paris 20e Arrondissement" → 20. The
   French ordinals use `1er` for the first and `Ne` for everything
   else.
4. Write a flat CSV with one row per amenity carrying `osm_id`,
   `amenity_class` (carried through from the input), the integer
   `arrondissement_number`, and the verbatim `arrondissement_name`.

The probe has two beats. *Spatial join literacy*: recognising that
this is a `within` join (not an `intersects`, not a nearest-neighbour,
not a centroid-of-polygon shortcut). *Attribute-parsing literacy*:
recognising that the integer number is the deliverable, not the
ordinal string the source layer carries.

## Why this difficulty

L1: a single primary operation (spatial join — within) on two fully
bundled layers in one GPKG. No fetching, no chained operations, no
reprojection (both inputs share EPSG:2154), no filtering upstream of
the join. The only twists are (a) two inputs in one GPKG container
(named layers, which the persona's instruction references explicitly),
and (b) a small string-parse to extract the integer from the
arrondissement name. Neither is a chained spatial operation.

## Input / output formats

### Input

`inputs/paris_amenities.gpkg` — two layers, both EPSG:2154.

`amenities` layer (85 features, Point):

| Column | Type | Notes |
|---|---|---|
| `osm_id` | int64 | Synthetic OSM-style integer id |
| `amenity_class` | string | One of `pharmacy`, `bakery`, `cafe`, `library`, `restaurant` |
| `name` | string | Overture `names.primary` (kept for realism, not required in output) |
| `geometry` | Point | Amenity location, EPSG:2154 metres |

`arrondissements` layer (20 features, Polygon):

| Column | Type | Notes |
|---|---|---|
| `id` | string | Overture id (UUID) |
| `name` | string | Verbatim Overture name, e.g. "Paris 1er Arrondissement", "Paris 13e Arrondissement", "Paris 20e Arrondissement" |
| `geometry` | Polygon | Arrondissement boundary, EPSG:2154 metres |

### Output

`outputs/amenity_to_arrondissement.csv` — 85 rows, one per amenity.

| Column | Type | Notes |
|---|---|---|
| `osm_id` | int | Verbatim from input |
| `amenity_class` | string | Verbatim from input |
| `arrondissement_number` | int (1–20) | Parsed from arrondissement name; **plain integer, not "20e"** |
| `arrondissement_name` | string | Verbatim Overture name (e.g. "Paris 13e Arrondissement") |

## Failure modes

1. **Kept the French ordinal suffix in `arrondissement_number`.** Agent
   joined correctly but wrote `"1er"`, `"2e"`, …, `"20e"` — the
   persona's hidden gotcha (the current prompt only declares
   `arrondissement_number (integer)`; the `20` not `20e` example is
   deliberately not given). The downstream INSEE join would
   silently fail on the type mismatch. *Detection:*
   `arrondissement_number_is_integer_1_to_20` and
   `arrondissement_number_per_row_match` both fail; `arrondissement_name_per_row_match`
   passes (the name is right). Covered by `broken_kept_ordinal_suffix`
   (score ≈ 0.69 under the severity weights).
2. **Wrote the arrondissement Overture id into the `arrondissement_name`
   column.** Agent confused the `id` and `name` columns of the
   arrondissement layer when projecting from the join (both layers
   carry both columns, and the join's `index_right` post-join boilerplate
   makes it easy to grab the wrong one). *Detection:*
   `arrondissement_name_per_row_match` fails; the integer number
   subchecks still pass. Covered by `broken_name_used_id`
   (score ≈ 0.85 under the severity weights).
3. **Dropped the `arrondissement_number` column.** Agent computed and
   reported only the name, treating the number as redundant.
   *Detection:* the format gate's required-column check fails; score = 0.
   Covered by `broken_wrong_format`.
4. **Used `intersects` instead of `within`.** For amenities lying
   strictly inside an arrondissement the two predicates agree, so on
   the bundled fixture this would not produce a different answer for
   any single amenity (the authoring helper pre-clips to the union of
   arrondissements). The failure mode would only surface on a fixture
   that placed a point exactly on a shared boundary; here the
   principled detector is reasoning from the persona's instruction
   ("within"), not a measurable subcheck. *Detection:* not-handled by
   a dedicated broken solution; the per-row name and number subchecks
   would catch any disagreement that did surface, but the fixture is
   not designed to provoke it.
5. **Output one row per arrondissement with a list of amenity ids.**
   Agent inverted the join and aggregated to 20 rows. *Detection:*
   if the required columns survive the inversion, the
   `exact_count_match` and `osm_id_set_jaccard` subchecks both fail
   (20 vs 85 rows); since the 2026-06-06 gate-2 removal this scores a
   partial (≈ 0.54 under the severity weights — both weight-3 join-shape
   subchecks fail, the most severe partial outcome) rather than 0 (if
   the columns do not survive, the format gate fails outright). Not
   covered by a dedicated broken
   solution; the count and id-set subchecks are the principled
   detector.
6. **Kept only amenities from one arrondissement.** Agent over-filtered
   (e.g. wrote `arr.iloc[0]` and joined to that single polygon),
   producing only the amenities from one arrondissement. *Detection:*
   `exact_count_match` and `osm_id_set_jaccard` both fail (~5 vs 85
   rows); since the 2026-06-06 gate-2 removal this scores a partial
   (≈ 0.54 under the severity weights — the two weight-3 join-shape
   subchecks fail) rather than 0. Not covered by a dedicated broken
   solution; the count and id-set subchecks are the principled detector.
7. **Reprojected the inputs to WGS84 before the join.** Lambert-93 is
   already metric and the join itself does not require metres; a
   reprojection round-trip is harmless for `within` but signals a
   missed cue (both layers already share Lambert-93, which the agent
   can read from the file metadata).
   *Detection:* not-handled — the CSV output carries no CRS, so the
   round-trip is invisible at grading time. The principled position is
   that as long as the answer is right, the round-trip costs nothing
   functionally; this entry is listed for completeness.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — kept the French ordinal
suffix in `arrondissement_number`.** A weak agent that does the
`within` join correctly is still likely to project the
`arrondissement_name` value verbatim into both columns (or a regex
that strips "Paris " and "Arrondissement" but leaves the ordinal in
the middle), missing the integer requirement that the prompt states
only via the `arrondissement_number` (integer) column declaration.
The grader awards ≈ 0.69 for this path under the severity weights
(the weight-3 number-per-row and weight-1 integer-shape subchecks fail;
the within-join itself is correct), clearly distinguishable from a
correct solution (1.0), from a wrong-format solution (0.0), and from the
name-vs-id-confusion solution (≈ 0.85).
