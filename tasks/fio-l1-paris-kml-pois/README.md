# fio-l1-paris-kml-pois

## Story

Margaux Léger, an intern in RATP's transport-planning unit, has
received a Google My Maps export (`.kml`) from a colleague who
hand-curated a list of late-night Métro-adjacent amenities — three
folders (cafés, libraries, sightseeing-tour points) of placemarks with
HTML-rich info-card descriptions. She needs it as a flat GeoJSON for
the team's internal map server, and — because the team is going to
weed out stale records — she wants the "last verified" date pulled
out of the HTML blurb into its own queryable column.

## What this task probes

KML reading + Folder-aware iteration + targeted extraction of one
structured field out of a CDATA-wrapped HTML info card + GeoJSON
writing. The skill is format literacy: knowing that Google My Maps
encodes the per-feature category as the parent `<Folder>` and not as
a Placemark attribute, knowing that pyogrio's KML driver exposes
Folders as separate layers, and being able to pluck a `YYYY-MM-DD`
date out of a CDATA blob of mixed tags, French labels, and HTML
entities (`Derni&egrave;re v&eacute;rification&nbsp;: 2026-01-01`).

## Why this difficulty

L1: a single primary GIS operation (KML → GeoJSON conversion) on a
fully bundled 45-placemark file. No fetching, no chained transforms,
no spatial joins. Two domain twists — Folder-as-category and
extract-one-field-from-HTML — keep the task from being trivial
without making it L2.

## Input / output formats

### Input

`data/paris_late_night_pois.kml` — KML 2.2, `<kml><Document><Folder>×3
<Placemark>×N`. Three Folders:

- `Cafés ouverts tard` (20 placemarks)
- `Bibliothèques de nuit` (15 placemarks)
- `Tours et infos touristiques` (10 placemarks)

Each Placemark has:

- `<name>` — the place name (Overture `names.primary`)
- `<description>` — CDATA-wrapped HTML info card with four logical
  lines: the place name (bold), a "Catégorie : …" line (duplicates
  the parent Folder), a "Voir la fiche" link, and a "Dernière
  vérification : YYYY-MM-DD" line — the only line that carries data
  worth keeping
- `<Point><coordinates>lon,lat,0</coordinates></Point>` (KML axis order
  is lon,lat — the standard trap)

### Output

`outputs/paris_pois.geojson` — single GeoJSON FeatureCollection with
columns:

| Field | Type | Notes |
|---|---|---|
| `name` | string | Placemark name |
| `category` | string | Parent folder label, one of the three above |
| `verified_date` | string (`YYYY-MM-DD`) | ISO date extracted from the HTML "Dernière vérification" line |
| `geometry` | Point | 2-D Point (Z dropped if present) |

## Failure modes

1. **Agent did not convert — output is the original KML or any
   non-GeoJSON.** *Detection:* the `format_schema_valid` gate rejects
   (required columns absent). Covered by `broken_wrong_format`
   (score 0.000).
2. **Agent never extracted the date.** `verified_date` column is
   missing, all-null, or all-empty. *Detection:*
   `verified_date_iso_format` (weight 2.0) fails (no row carries a
   YYYY-MM-DD string); `verified_date_values_match` (weight 4.0) also
   fails. Covered by `broken_verified_date_missing` (score 0.733 under
   the per-task reasoned weights).
3. **Agent swapped KML coordinates to (lat,lon) instead of
   (lon,lat).** *Detection:* `geometry_preserved_per_name` (weight 3.0)
   fails (every Point lands ~50° off in the Indian Ocean). Covered by
   `broken_axis_swap` (score 0.867 under the weighted grader).
4. **Agent read only the first KML layer** (pyogrio.read_file
   default-layer behaviour) and dropped the other two Folders.
   *Detection:* `row_count_within_tolerance` (weight 3.0) and
   `name_set_preserved` (weight 3.5) fail (20 vs 45 rows, name
   Jaccard ≈ 0.42). Score ~0.711 — observed live in
   run-20260607-112430Z. Not covered by a broken solution; principled
   detectors are the two subchecks.
5. **Agent collapsed all categories into a single bucket** because
   pyogrio's default-layer read loses the Folder hierarchy.
   *Detection:* `category_populated_and_recognised` fails if the
   bucket name is anything other than the three expected Folder
   labels; `category_values_match` fails because most rows would now
   carry the wrong category. Not covered by a broken solution;
   principled detectors are the two `category_*` subchecks.
6. **Agent reprojected to a non-WGS84 CRS** before writing.
   *Detection:* the soft-CRS subchecks `crs_is_canonical` and
   `crs_in_meaningful_set` both fail (two points docked); the
   submission is reprojected to EPSG:4326 before the geometric
   subchecks run. GeoJSON pins WGS84 by RFC 7946, so any other CRS is
   wrong, but it no longer zeroes the score. Not covered by a broken
   solution; principled detectors are the two CRS subchecks.
7. **Agent kept the KML 3-D `Point Z`** geometry verbatim. GeoJSON
   tolerates 3-D points; geometry types still register as `Point`,
   and shapely 2-D access on a Z-point ignores the Z so the geometry
   subcheck still works. *Detection:* Not directly graded — a
   tolerated cosmetic deviation.
8. **Agent extracted the date but left it embedded** in the source
   French label, e.g. `"Dernière vérification : 2026-01-01"` instead
   of `"2026-01-01"`. *Detection:* `verified_date_iso_format`
   (weight 2.0) fails (literal value isn't a `YYYY-MM-DD` string);
   `verified_date_values_match` still passes because the lenient
   extractor finds the date in either string. Score ~0.911
   under the weighted grader (a cosmetic shape slip — above the
   axis-swap and date-missing failures). Not covered by a dedicated
   broken solution; principled detector is the format/value split.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#5 — single-layer read losing
the per-feature category** combined with **#2 — failing to extract
the date** when overwhelmed by the HTML parsing detour. A baseline
agent that calls `gpd.read_file(kml_path)` without iterating layers
gets only the first Folder (Cafés ouverts tard), 20 of the 45 rows,
and either loses the heavyweight `row_count_within_tolerance` +
`name_set_preserved` subchecks (score ~0.711) or — if it noticed and
recovered to all three layers — still has to invent the `category`
attribute since pyogrio doesn't expose Folder names. Either branch
lands well below the reference's 1.0.
