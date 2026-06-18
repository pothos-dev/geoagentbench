# spa-l1-vienna-pip-count

## Story (for the human reviewer)

Ana Brković is an analyst at Austria's *Umweltbundesamt* (federal
environment agency). Ahead of next year's air-quality budget round she
has to brief a funding committee on which Vienna Bezirke are
under-monitored relative to their population. She has the city's
monitoring-station point layer and the 23-Bezirk polygon layer ready in
MGI Lambert and just needs the simplest possible diagnostic: a CSV that
lists every Bezirk with its station count, sorted by district code, so
the committee can read the gaps at a glance. **Districts with zero
stations must still appear** — they're the whole point.

## What this task probes

A single spatial-analysis primary operation — *point-in-polygon count*
— over two metric-CRS GeoJSON layers, plus the implementation hinge
that distinguishes a join-and-count solution from a *complete*
join-and-count solution: the agent has to **left-join the station
count back onto the full 23-Bezirk list**, not just emit the rows that
fell out of the inner spatial join. Concretely, the agent must:

1. Read two layers (49 monitoring-station Points + 23 Vienna Bezirk
   Polygons) from EPSG:31287 GeoJSON files.
2. Spatially join each station to the Bezirk that *contains* it
   (within-predicate). Every station in the bundled fixture lies inside
   exactly one Bezirk — the bundling helper post-clips to the union of
   the 23 polygons so there are no boundary-edge or outside-Vienna
   points to disambiguate.
3. Group by Bezirk and count.
4. Emit one CSV row per Bezirk — including the four Bezirke that
   received zero stations (Mariahilf, Josefstadt, Simmering, Hernals)
   — with columns ``district_code, district_name, station_count``,
   sorted by ``district_code``.

The probe has two beats. *Spatial-join literacy*: recognising that the
right operation is point-in-polygon count over two metric-CRS layers,
not a nearest-neighbour or a buffer-and-aggregate. *Aggregation
literacy*: recognising that a coverage diagnostic needs **every
polygon in the polygon set**, not just the ones with at least one
point — i.e. left-joining the count onto the full Bezirk list and
filling missing counts with zero.

## Why this difficulty

L1: a single primary operation (point-in-polygon count) on two fully
bundled layers in a metric CRS. No fetching, no chained operations, no
reprojection (both inputs share EPSG:31287). The only twist is the
zero-count-districts contract, which since the 2026-05-17 nudge-strip
is no longer spelt out literally - the agent must infer it from the
persona's coverage-diagnostic framing ("listing every Bezirk", "spot
under-monitored areas at a glance"). That is an aggregation-literacy
beat, not a chained spatial operation.

## Input / output formats

### Input

`inputs/districts.geojson` (Polygon / MultiPolygon, EPSG:31287, 23
features):

| Column | Type | Notes |
|---|---|---|
| `district_code` | int | Vienna Bezirk number 1–23 |
| `district_name` | string | German Bezirk name (e.g. "Innere Stadt", "Währing", "Landstraße") |
| `osm_relation_id` | int | OSM relation id, kept for provenance |
| `geometry` | Polygon / MultiPolygon | Bezirk boundary, EPSG:31287 metres |

`inputs/stations.geojson` (Point, EPSG:31287, 49 features):

| Column | Type | Notes |
|---|---|---|
| `station_id` | int | OSM node id (verbatim) |
| `name` | string \| null | OSM `name` tag if present, otherwise null |
| `geometry` | Point | Station location, EPSG:31287 metres |

### Output

`outputs/stations_per_district.csv` (23 rows, sorted by
`district_code`):

| Column | Type | Notes |
|---|---|---|
| `district_code` | int (1..23) | Verbatim from input |
| `district_name` | string | Verbatim German name from input |
| `station_count` | int (≥ 0) | Number of stations whose geometry falls within this Bezirk; **zero is a valid value** |

## Failure modes

1. **Inner join only — zero-count districts disappear.** The agent
   joined stations to Bezirke, grouped by `district_code`, and emitted
   the resulting 19 rows — never left-joining back onto the full
   23-Bezirk list. Mariahilf, Josefstadt, Simmering, and Hernals
   vanish, defeating the persona's coverage diagnostic. *Detection:*
   `exact_count_match` (19 ≠ 23) and `district_code_set_complete`
   (codes ≠ {1..23}) both fail; per-row attribute and total subchecks
   still pass on the 19 districts present. Two weight-3.0 count/code
   subchecks fail out of a 13-point weight budget. Covered by
   `broken_inner_join` (score = 7/13 ≈ 0.538).
2. **Wrong attribute pulled into `district_name`.** The agent did the
   count correctly and produced 23 rows but, when carrying attributes
   through the spatial join, pulled the `osm_relation_id` (an integer)
   into `district_name` instead of the verbatim name string —
   classic left/right-of-the-merge column confusion. The downstream
   committee briefing now has integer relation ids where Bezirk names
   should be. *Detection:* `district_name_per_row_match` fails (0%
   match); the rest of the subchecks pass. The name check is the
   cosmetic weight-1.0 subcheck, so a name-only failure drops the
   score only lightly. Covered by `broken_name_used_id` (score =
   12/13 ≈ 0.923).
3. **Missing `station_count` column.** The agent wrote the schema as
   `district_code, district_name` but forgot the count itself —
   either silently dropped on a `to_csv` projection or lost in a
   pandas operation that aggregated without naming the result.
   *Detection:* the format gate's required-column check fails. Covered by
   `broken_wrong_format` (score = 0.0).
4. **Wrong CRS / lat-lon point arithmetic.** The agent reprojected one
   layer to WGS84 but not the other, then ran `sjoin` on mismatched
   CRSes. Geopandas would either raise (current versions) or
   produce wildly wrong matches (older versions); a few stations land
   inside the wrong Bezirk and the per-row count match drops. *Detection:*
   `station_count_per_row_match` falls below 95% if mis-matches
   exceed 1–2 stations; `station_count_total_match` may also fail if
   stations slide outside Vienna entirely. Not covered by a dedicated
   broken (the failure shape varies by which CRS axis was swapped),
   but principled — multiple subchecks degrade together.
5. **`intersects` predicate instead of `within`.** The agent used the
   inclusive `intersects` predicate. For a Point-vs-Polygon spatial
   join the two predicates are equivalent on points strictly inside a
   polygon (every Vienna station here is) — so this returns the
   correct counts in this fixture. *Detection:* not detected —
   intentional. The bundled inputs are constructed so this distinction
   does not change the answer; the persona's question is the count,
   not the predicate. Listed for completeness.
6. **Used station count from the input layer's row count instead of
   per-Bezirk count.** The agent wrote 49 (or 49/23 ≈ 2) into every
   row, never running the spatial join. *Detection:*
   `station_count_per_row_match` fails on most rows;
   `station_count_total_match` fails (49 × 23 = 1127, way off from
   49). Not covered by a dedicated broken (the constant-fill failure
   is shallower than `inner_join` and `name_used_id`, which exercise
   real implementation paths an agent might genuinely take), but
   principled — both per-row and total subchecks would catch it.
7. **`station_count` is a float (`station_count = 6.0`).** Agent left
   the count as a float because pandas defaulted there after a
   left-join+fillna. *Detection:* the grader coerces both sides to int
   via `_coerce_int`, so int-valued floats (`6.0`) pass; only
   fractional floats (which would never come out of a real PIP count)
   would fail. Not detected as a fault — by design, since the persona
   doesn't care whether the integer column is dtype int or
   int-valued float in a CSV.

## Expected weak-agent failure mode

The weakest baseline will get the join right but skip the zero-count
districts: it will compute `groupby('district_code').size()` and
emit the 19-row result, missing the zero-count contract implied by
the persona's coverage-diagnostic framing. That's the canonical L1
PIP-count gotcha and the score lands at 7/13 ≈ 0.538 via
`broken_inner_join`. Confirmed in the wild: `run-20260609-084636Z`
(deepseek-v4-flash, basic prompt) emitted exactly this 19-row
inner-join CSV; it scored 0.6 under the prior uniform-weight grader
and re-grades to ≈0.538 under the 2026-06-14 severity-weight
calibration (the central join failure now drops the score more).
