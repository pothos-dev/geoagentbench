# dc-l3-vienna-overpass-historical

## Story

Dr. Magdalena Reiter, historian at the Austrian Statistical Office, is
preparing a 10-year retrospective on Vienna's administrative geometry for
the 2026 statistical yearbook. She needs the symmetric difference between
Vienna's 2014 and current district boundaries, pulled live from Overpass
with a `[date:...]` directive against the 2014 snapshot.

## What this task probes

This task exercises five GIS / data-cleaning skills in a single pipeline:

1. **Live data acquisition** from the Overpass API, including use of the
   attic (historical snapshot) API with `[date:2014-01-01T00:00:00Z]`.
2. **Attribute-value normalisation** — district names changed casing and
   formatting between OSM snapshots (e.g. `Wien-Innere Stadt` vs `Innere
   Stadt`), so the agent must normalise before matching.
3. **Geometric set operations** — per-district intersection, difference,
   and symmetric difference to classify boundary fragments.
4. **Spatial join / adjacency** — determining which districts neighbour
   any changed geometry (the `touches_changed` flag).
5. **Data filtering** — the 2014 Overpass query may return non-Vienna
   municipalities that need to be excluded.

## Why this difficulty

**L3** because the task requires:
- Live data fetching from two different Overpass snapshots (no bundled inputs).
- Multi-step pipeline: fetch -> normalise -> match -> set-operations -> spatial-join -> output.
- Handling of real-world data quality issues (name drift, spurious results from area query).
- Domain knowledge about Vienna's administrative structure and OSM tagging conventions.

## Input / output formats

### Inputs

None bundled. The agent fetches live from Overpass:
- Current Vienna Bezirke: `boundary=administrative`, `admin_level=9`
- Historical (2014): same query with `[date:2014-01-01T00:00:00Z]`

### Output

| File | Format | CRS | Geometry |
|---|---|---|---|
| `vienna_boundary_changes.geojson` | GeoJSON | EPSG:4326 | MultiPolygon |

**Feature schema:**

| Property | Type | Description |
|---|---|---|
| `district_name` | string | Normalised Bezirk name (e.g. "Innere Stadt") |
| `change_type` | string | One of: `added_since_2014`, `removed_since_2014`, `unchanged` |
| `touches_changed` | boolean | Whether this district neighbours any changed geometry |

Each (district_name, change_type) pair produces at most one feature. A
district may appear up to three times (once per change_type it has
non-empty geometry for).

## Failure modes

1. **No historical query / wrong date directive** — agent fetches only
   current data or uses wrong date format. Detection: `per_type_feature_count`
   and `unchanged_area_dominates` subchecks (all features would be
   "unchanged" or all "added"). Covered by `broken_wrong_geometry`.

2. **Name normalisation skipped** — agent doesn't strip Wien- prefix or
   numbering from 2014 names, so districts fail to match. Detection:
   every district appears as both "added" (current name) and "removed"
   (2014 name) instead of having a small symmetric difference.
   `district_name_set_overlap` Jaccard drops; `unchanged_area_dominates`
   fails. Principled-reasoning check.

3. **Wrong geometry type** — agent outputs Points or LineStrings instead
   of (Multi)Polygons. Detection: Gate 2 rejects non-polygonal geometries.
   Principled-reasoning check.

4. **Missing required properties** — agent omits `change_type`,
   `district_name`, or `touches_changed` columns. Detection: Gate 1
   rejects missing columns. Covered by `broken_wrong_format`.

5. **Non-Vienna districts included** — agent doesn't filter out
   municipalities like Gerasdorf bei Wien that the 2014 Overpass query
   returns. Detection: `total_feature_count` subcheck (extra features);
   `district_name_set_overlap` Jaccard drops. Principled-reasoning check.

6. **Wrong CRS** — agent reprojects to a local CRS but forgets to
   convert back. Detection: `crs_is_wgs84` and
   `coordinates_in_vienna_envelope` subchecks. Principled-reasoning check.

7. **touches_changed always False** — agent computes geometry correctly
   but doesn't implement the spatial adjacency check. Detection:
   `touches_changed_accuracy` subcheck. Covered by
   `broken_wrong_attributes`.

## Expected weak-agent failure mode

The weakest baseline will likely fail to use the Overpass attic API
correctly (wrong date directive syntax, or omitting it entirely), and/or
will skip name normalisation — both of which produce dramatically wrong
symmetric differences that the grader catches via the
unchanged-area-dominance and per-type-count checks.
