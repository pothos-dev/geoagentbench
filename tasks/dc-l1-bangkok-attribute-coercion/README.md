# dc-l1-bangkok-attribute-coercion

## Story (for the human reviewer)

Suda Pongpan runs the Bangkok Metropolitan Administration's air-quality
monitoring programme. The vendor exports station readings as GeoJSON
with every numeric column stringified — even the sensor IDs — which
breaks the analytics team's dashboards that compute averages by
`parseFloat`-ing client-side and silently drop NaNs. She needs a
cleaned GeoJSON with the numeric columns properly typed and the
Thai-script station names preserved, so the dashboard's averages match
the figures the city director quotes in press briefings.

## What this task probes

Attribute type coercion on a malformed vendor export. The bundled
GeoJSON of Bangkok rail-station-mounted air-quality sensors encodes
every numeric column as a JSON *string* (`"sensor_value": "42.7"`)
rather than a JSON *number* (`"sensor_value": 42.7`). The agent must
read the malformed file, coerce four columns to their proper JSON
types, preserve the Thai-script `name_th` column verbatim, preserve
the point geometry, and write the result back as GeoJSON in
EPSG:4326. No projection, no filtering, no geometric edit — pure
attribute cleaning.

## Why this difficulty

L1: a single primary operation (attribute type coercion) on a fully
bundled input. No fetching, no chained operations, no
projection-sensitive numerics. The persona's question admits exactly
one correct answer family — every correct solution produces the same
set of `station_id`s, the same point coordinates, the same `name_th`
strings, and four numeric columns properly typed.

## Input / output formats

### Input

`inputs/bangkok_aq_stations.geojson` — 100 air-quality sensor stations
in EPSG:4326, all `Point` geometry. Every numeric column is serialised
as a JSON string. The geographic anchor is a curated list of real
Bangkok BTS / MRT / Airport Rail Link stations (the first ~50
features) plus deterministic synthesised "sensor sites" tied to those
stations.

| Field | JSON type in input | Description |
|---|---|---|
| `station_id` | string | Stable per-task primary key (1–100), arrives as `"1"` |
| `name_th` | string | Thai-script station name (preserved as-is) |
| `name_en` | string | English transliteration (helper column) |
| `sensor_value` | string | Sensor raw value, arrives as `"84.55"` |
| `pm25_ug_m3` | string | PM₂.₅ in µg/m³, arrives as `"63.6"` |
| `elevation_m` | string | Site elevation in metres, arrives as `"11.0"` |

### Output

`outputs/bangkok_aq_typed.geojson` — same 100 features in EPSG:4326,
identical schema, with:

- `station_id` typed as integer
- `sensor_value`, `pm25_ug_m3`, `elevation_m` typed as floats (or any
  JSON number type, but never strings)
- `name_th` preserved verbatim (Thai script intact)
- Point coordinates unchanged

## Failure modes

1. **Forget to coerce — pass the file through unchanged.** A naive
   agent runs `gpd.read_file → gdf.to_file` and writes the same
   GeoJSON back. Counter-intuitively GeoPandas *does* infer numeric
   types for object columns when reading, but a quick round-trip
   through `to_file` with the GeoJSON driver may re-emit them as
   strings (the dtype is `object`), and even an `agent.copy_file()`
   shortcut produces the same defect. *Detection:* All four type
   subchecks (`station_id_is_integer`,
   `sensor_value_is_number_not_string`,
   `pm25_ug_m3_is_number_not_string`,
   `elevation_m_is_number_not_string`) fail; the
   content / geometry / set subchecks all pass because the underlying
   values are unchanged. Covered by `broken_no_coercion` (score ≈ 0.368
   under the per-task reasoned weights — the four type subchecks are the
   central skill and carry weight 6 each, 24 of a total weight of 38).
2. **Coerce floats but forget `station_id`.** The agent loops the
   numeric columns and casts each to `float`, but `station_id` is
   logically an integer and ends up as either a string (untouched)
   or a float (`1.0` instead of `1`). RFC-style ID semantics demand
   integers. *Detection:* `station_id_is_integer` subcheck fails,
   everything else passes. Covered by `broken_partial_coercion`
   (score ≈ 0.842 under the per-task reasoned weights — one of the four
   weight-6 central type subchecks misses).
3. **Drop one of the required attribute columns.** The agent
   projected a subset of properties (e.g., kept only `station_id`,
   `name_th`, `sensor_value`, `elevation_m`) before writing.
   *Detection:* the `format_schema_valid` gate's required-property
   check rejects the file before any subchecks run. Covered by
   `broken_wrong_format` (score 0.0).
4. **Coerce numeric values incorrectly (lossy parse).** The agent
   uses a regex or a CSV intermediate that loses precision (e.g.,
   `int(float("42.7"))` → 42; `Decimal("42.7000000000001")`).
   *Detection:* `numeric_values_preserved` subcheck fails (per-cell
   relative tolerance 1e-3, ≥ 0.99 cell pass-rate required). Not
   covered by a broken solution; this is the principled
   content-correctness detector.
5. **Mangle the Thai `name_th` script via a non-UTF-8 stage.** The
   agent re-encodes the file through Shapefile / KML / Latin-1 and
   the Thai script is corrupted to `?` glyphs or mojibake.
   *Detection:* `name_th_preserved_verbatim` subcheck fails (≥ 0.95
   per-id exact-match rate required). Not covered by a broken
   solution; the per-id name comparison is the principled detector.
6. **Edit the point coordinates.** A stray `to_crs(3857).to_crs(4326)`
   round-trip nudges every coordinate by floating-point noise; an
   agent that "rounds to 4 decimal places to clean things up" loses
   ~10 m of precision. *Detection:* `geometry_preserved_per_id`
   subcheck fails (per-id coordinate epsilon 1e-6°). Not covered by
   a broken solution; the per-id point comparison is the principled
   detector.
7. **Re-orient and accidentally change CRS.** The agent calls
   `to_crs(3857)` thinking projected coordinates are required.
   *Detection:* the soft-CRS gate accepts any parseable CRS and
   normalises the submission back to WGS84 for the spatial subchecks,
   but the `crs_is_canonical` and `crs_in_meaningful_set` subchecks
   both fail for any non-4326 pick (2 of 38 weight points). Not
   covered by a broken solution; the two CRS subchecks are the
   principled detectors.
8. **Drop or duplicate features.** The agent applied a filter
   predicate (e.g., "stations with non-zero `pm25_ug_m3`") before
   writing. *Detection:* the `feature_count_within_tolerance`
   subcheck (±5 %) catches gross drops; the
   `station_id_set_preserved` Jaccard subcheck
   (≥ 0.95) catches subtler set differences; the
   `feature_id_set_via_geopandas` Jaccard subcheck is a
   complementary detector via the GeoPandas-readable view. Not
   covered by a broken solution; both detectors are principled.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — read, write, no coercion
fix**. A naive `gpd.read_file → gdf.to_file` round trip preserves
attribute order, geometry, and feature count, and the file looks
superficially correct. Pyogrio's GeoJSON driver round-trips the
object-typed string columns straight back as strings; the agent does
not realise that the analytics dashboard sees the same defect after
the cleanup. Only an explicit coercion (`pd.to_numeric`,
`int(...)`, `float(...)`) catches it. The grader awards ≈ 0.368 for
this failure (all four central type subchecks fail, all preservation /
content / set subchecks pass), so it is distinguishable from a
correct solution (1.0), from a missing-column solution (0.0), and
from a partial-coercion solution (≈ 0.842). Note: under the per-task
reasoned weights the four type subchecks (the central skill) carry
24 of the 38 total weight points, so a do-nothing pass-through drops
substantially even though the weight-2 content-preservation subchecks
pass trivially on the unmodified input. This replaces the earlier
repo-wide 3x content weighting, under which the same pass-through
scored 0.84 because the central skill was diluted to 4/25 of the
weight.
