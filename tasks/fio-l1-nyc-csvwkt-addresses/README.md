# fio-l1-nyc-csvwkt-addresses

## Story

Jamal Wright, an intern at NYC's Department of Health and Mental
Hygiene, has been asked to convert a small Overture-style address
sample from a CSV-with-WKT vendor export into proper GeoParquet so the
analytics team can query it via DuckDB without re-typing every column.
The export tool quoted every value, so `recorded_at` arrives as a
string and `unit_count` arrives as a string — Jamal needs the output to
type both correctly so SQL like `WHERE recorded_at > '2024-01-01'` and
`SELECT SUM(unit_count) ...` works without per-query CASTs.

## What this task probes

CSV-with-WKT reading + WKT geometry parsing into a GeoSeries +
attribute type coercion (string → microsecond timestamp, string → int32)
+ GeoParquet writing with the right Arrow schema. The skill is format
literacy on both ends of the pipeline: knowing that `pd.read_csv` of an
all-quoted CSV returns `object` everywhere, knowing that GeoParquet
preserves Arrow types end-to-end, and knowing how to pin int32 vs the
pyarrow default of int64.

## Why this difficulty

L1: a single primary GIS operation (CSV → GeoParquet conversion) on a
fully bundled 1 056-row CSV. No fetching, no chained transforms, no
spatial joins. The two type-coercion steps and the WKT parse are
straightforward one-liners with the right library.

## Input / output formats

### Input

`inputs/nyc_addresses.csv` — 1 056 quoted CSV rows, columns:

| Field | Stored as | Description |
|---|---|---|
| `id` | quoted string | Stable Overture address id |
| `country` | quoted string | Always `US` |
| `postcode` | quoted string | 5-digit ZIP |
| `street` | quoted string | Street name |
| `number` | quoted string | House number (may include `1/2`, `B`, etc.) |
| `unit` | quoted string | Apartment / suite identifier (often empty) |
| `postal_city` | quoted string | Postal city (often empty in Overture) |
| `recorded_at` | quoted string | ISO-8601 timestamp `YYYY-MM-DDThh:mm:ssZ` |
| `unit_count` | quoted string | Non-negative integer (mostly `0`, occasional 1–12) |
| `geometry_wkt` | quoted string | Point WKT in EPSG:4326 |

### Output

`outputs/addresses.geoparquet` — single GeoParquet file with columns:

| Field | Arrow type | Notes |
|---|---|---|
| `id`, `country`, `postcode`, `street`, `number`, `unit`, `postal_city` | `string` | Overture address text columns |
| `recorded_at` | `timestamp[us]` | tz-naive or UTC, microsecond precision |
| `unit_count` | `int32` | Pinned at int32 |
| `geometry` | GeoArrow WKB | Point, EPSG:4326 |

## Failure modes

1. **Agent wrote the result as CSV / GeoJSON / plain Parquet** instead
   of a GeoParquet recognised by GeoPandas. *Detection:* the single
   hard gate (`format_schema_valid`) rejects (pyarrow read fails or
   geopandas read fails or the CRS metadata is absent). Covered by
   `broken_wrong_format` (score 0.000).
2. **Agent skipped attribute type coercion entirely.** Output is a
   structurally valid GeoParquet, but `recorded_at` is `string` and
   `unit_count` is `string`. *Detection:* `recorded_at_is_timestamp_us`
   and `unit_count_is_int32` both fail; value-preservation subchecks
   still pass because string→string round-trips cleanly. Covered by
   `broken_no_type_coercion` (score 0.739 under the weighted grader).
3. **Agent typed everything else but defaulted `unit_count` to int64**
   (the pyarrow inference for a Python int). *Detection:*
   `unit_count_is_int32` fails. Covered by `broken_int64_unit_count`
   (score 0.870 under the weighted grader).
4. **Agent typed `recorded_at` as `timestamp[ns]`** (the pandas
   default before an explicit `.astype('datetime64[us]')`) instead of
   `timestamp[us]`. *Detection:* `recorded_at_is_timestamp_us` fails
   because the unit is `ns`. Not covered by a broken solution;
   principled detector is the type subcheck.
5. **Agent re-typed numeric-looking text columns to integer** (e.g.
   `postcode` to int because it's all digits, mangling leading-zero
   ZIPs). *Detection:* `address_columns_are_strings` fails because
   `postcode` is no longer Arrow string. Not covered by a broken
   solution; principled detector is the per-string-column subcheck.
6. **Agent kept the original `geometry_wkt` text column alongside the
   parsed geometry.** *Detection:* `no_residual_geometry_wkt_column`
   fails. Not covered by a broken solution; principled detector is
   the residual-column subcheck.
7. **Agent dropped or duplicated rows during the conversion** (e.g.
   `pd.read_csv` with `error_bad_lines=False` silently dropped
   malformed lines, or a join doubled some rows). *Detection:* the
   `row_count_exact` subcheck fails (weight 2, so a row drop costs
   ~0.09 even before the per-id value subchecks degrade). Not covered
   by a broken solution; principled detector is the row-count
   subcheck.
8. **Agent reprojected the WKT to a non-WGS84 CRS** before writing.
   *Detection:* the soft CRS check deducts via `crs_is_canonical`
   and `crs_in_meaningful_set`, and the submission is reprojected to
   EPSG:4326 before the geometry subcheck so `geometry_preserved_per_id`
   still measures the agent's geometric work. Not covered by a broken
   solution; principled detector is the two CRS subchecks.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#3 — int64 instead of int32**.
The shortest-path completion of "convert this column to int" is
`df['unit_count'].astype(int)`, which on 64-bit Python yields int64.
An agent that doesn't read the inventory carefully enough to notice
the explicit `int32` request still produces a structurally clean
GeoParquet with correct values and correct timestamps — and lands on
0.870, distinguishable from a no-coercion solution (0.739), a
wrong-format solution (0.000), and a fully-correct one (1.000). The
subcheck weights are reasoned per-task (2026-06-14 review block):
the three Arrow-type subchecks (`recorded_at_is_timestamp_us`,
`unit_count_is_int32`, `address_columns_are_strings`) carry weight 3
because correct type coercion is the task's central skill, the five
value-preservation subchecks carry weight 2, and the structural / CRS
checks carry weight 1 — so a central type mistake drops the score
meaningfully while a cosmetic slip (e.g. a residual `geometry_wkt`
column) only docks ~0.04. See audit/AUTHORING_HISTORY.md.
