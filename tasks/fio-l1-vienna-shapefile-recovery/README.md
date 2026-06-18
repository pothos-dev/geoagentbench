# fio-l1-vienna-shapefile-recovery

## Story

Stefan Ebner, a cadastre intern at Austria's BEV (federal mapping
agency), is helping migrate a 1990s Vienna parcel snapshot from
Shapefile into the modern web-tiles pipeline. The shapefile's dBase
columns truncated the original attribute names to 10 characters, the
encoding is CP1252, and the geometry is in MGI Lambert (EPSG:31287). He
has a `column_map.csv` listing the original full names. He needs a
clean WGS84 GeoJSON with the full names restored and German umlauts
intact, so the front-end developer can drop it into the new viewer
without any post-processing.

## What this task probes

Three composed format-I/O skills:

1. **Reading a CP1252-encoded shapefile.** The `.cpg` sidecar declares
   the encoding; pyogrio / fiona / ogr2ogr respect it automatically,
   but a naïve agent that reads the `.dbf` bytes directly (or that
   passes `encoding="utf-8"`) Mojibake's the German diacritics.
2. **Recovering truncated dBase column names.** dBase's silent 10-char
   truncation is the canonical Shapefile gotcha. The agent must
   consume the `column_map.csv` lookup table and apply it to the
   loaded GeoDataFrame.
3. **Reprojecting EPSG:31287 → EPSG:4326.** A standard CRS move but
   the input CRS is non-WGS84 (Austria-specific) so a lazy agent that
   skips the reprojection ships parcels at coordinates in the millions
   of metres rather than ~16°E / 48°N.

## Why this difficulty

L1: a single primary GIS operation (Shapefile → GeoJSON conversion)
on a fully bundled 60-parcel input. No fetching, no chained spatial
work, no joins. The three sub-skills are each one-liner library
calls; what's tested is whether the agent strings them together
correctly given the bundled `column_map.csv`.

## Input / output formats

### Input

`inputs/parcels.shp` (+ `.shx`, `.dbf`, `.prj`, `.cpg`) — 60 parcel
polygons in EPSG:31287, dBase columns:

| dBase column | Type | Notes |
|---|---|---|
| `KATASTRALG` | string | truncated `KATASTRALGEMEINDE_NAME` |
| `GRUNDSTUEC` | string | truncated `GRUNDSTUECKSNUMMER` (unique parcel id) |
| `EIGENTUEME` | string | truncated `EIGENTUEMER_NAME` |
| `WIDMUNG_BE` | string | truncated `WIDMUNG_BEZEICHNUNG` |
| `STRASSE_NA` | string | truncated `STRASSE_NAME` |
| `FLAECHE_M2` | float | parcel area in m²; already 10 chars (untruncated) |

`inputs/column_map.csv` — two columns, `truncated,original`, listing
the recovery for each dBase alias above.

`inputs/parcels.cpg` — single line `CP1252` declaring the dBase encoding.

### Output

`outputs/parcels.geojson` — single GeoJSON FeatureCollection with:

| Field | Type | Notes |
|---|---|---|
| `KATASTRALGEMEINDE_NAME` | string | German place names with diacritics |
| `GRUNDSTUECKSNUMMER` | string | parcel id |
| `EIGENTUEMER_NAME` | string | owner names with diacritics & em-dash |
| `WIDMUNG_BEZEICHNUNG` | string | zoning class with diacritics |
| `STRASSE_NAME` | string | street names with diacritics |
| `FLAECHE_M2` | number | parcel area, m² |
| `geometry` | Polygon | reprojected to EPSG:4326 |

## Failure modes

1. **Output written as Shapefile / CSV / something other than GeoJSON.**
   *Detection:* the hard gate `format_schema_valid` fails (file
   `parcels.geojson` absent / unreadable).
   Covered by `broken_wrong_format` (score 0.000).
2. **Agent ignored `column_map.csv` and shipped the dBase 10-char
   aliases.** *Detection:* the five `column_renamed_*` subchecks all
   fail (weight 1 each; the weight-3 value subchecks still pass via
   the truncated-alias fallback). Covered by `broken_truncated_columns`
   (score 0.808).
3. **Agent didn't honour the `.cpg` sidecar and read the dBase as
   UTF-8.** Every CP1252 diacritic byte is replaced with U+FFFD or
   re-decodes into Mojibake. *Detection:* `diacritics_decoded` plus
   the two per-id text-value subchecks fail — all three are weight-3
   data-content detectors of the encoding skill. Covered by
   `broken_mojibake_encoding` (score 0.654).
4. **Agent skipped reprojection — kept geometry in EPSG:31287.**
   *Detection:* the soft-CRS policy reprojects the submission to
   canonical for the geometric subchecks and docks `crs_is_canonical`
   (EPSG:31287 stays in the meaningful set, so `crs_in_meaningful_set`
   passes); if the agent instead relabelled the CRS without
   transforming, `geometry_reprojected_per_id` (3x) rejects because
   centroids land at ~625 000 m / ~483 000 m instead of ~16°E / ~48°N.
   Not covered by a broken solution; principled detectors are the
   soft-CRS subchecks + the geometry subcheck.
5. **Agent dropped or duplicated rows.** *Detection:* the
   `row_count_exact` subcheck (3x) rejects. Not covered by a broken
   solution.
6. **Agent renamed but mistyped the recovered names** (e.g.,
   `KATASTRALGEMEINDE` instead of `KATASTRALGEMEINDE_NAME`).
   *Detection:* the corresponding `column_renamed_<x>` subcheck fails
   because the expected full name is absent. Not covered by a broken
   solution; principled detector is the per-column rename subcheck.
7. **Agent stripped diacritics** (ASCII-folded "Währing" → "Wahring"
   "for safety"). *Detection:* `diacritics_decoded` fails because
   none of ä/ö/ü/ß are present in any text column, and the per-id
   text-value subchecks fail because folded names don't match the
   reference. Not covered by a broken solution; principled detector
   is `diacritics_decoded` + per-id text checks.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#3 — Mojibake encoding**.
A model that knows "shapefile attributes can have an encoding"
sometimes still reaches for the wrong default (UTF-8 because that's
the modern default, not CP1252 which the persona's `.cpg` declares).
The output looks structurally fine, the column names are recovered
correctly, but every "Währing" becomes "W?hring" (or a U+FFFD blob)
and the front-end map shows replacement characters next to every
parcel label. That submission lands on 0.654 - distinguishable from a
fully correct one (1.00), a "skipped column rename" miss (0.808), and
a wrong-format one (0.00). The data-content weighting (weight 3 on the
value/geometry/row-count/diacritics subchecks, weight 1 on the cosmetic
column-rename and CRS-label subchecks) places the mojibake miss
*below* the rename miss: corrupted data content costs more than a
cosmetic schema slip. The `diacritics_decoded` weight was raised from
1 to 3 on 2026-06-14 so the encoding skill's most direct detector
carries data-content weight, widening the gap between the two
recoverable failure classes.
