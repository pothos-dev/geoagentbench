# dd-l1-capetown-clinics-bbox

## Story

Naledi Mokoena, a data analyst at the City of Cape Town Health
Department, has been handed a legacy CSV export of public clinic
locations whose geometry is stored as a `wkt_geom` column. Before she
ingests the export into the case-management system she wants a quick
inventory — record count, bounding box of all the points, and a
count-per-subdistrict roll-up — so she can confirm the export covers
all eight Metropolitan Health Services subdistricts.

## What this task probes

CSV-with-WKT parsing (`POINT(lon lat)`) + total record count + overall
bounding box of the parsed points + group-by-attribute count, then
serialised as a small inventory JSON. The skill being measured is
basic literacy in a text geospatial export and the matching three-line
inventory that a real analyst would compute before pipeline ingest.

## Why this difficulty

L1: a single primary GIS operation (parse the WKT column into a Point
geometry) wrapped in three trivial reductions (count, bbox, group-by
count) over a fully bundled CSV fixture. No fetching, no chained
transforms, no projection-sensitive numerics, no data quality issues
to detect.

## Input / output formats

### Input

`inputs/capetown_clinics.csv` — 80 rows, UTF-8, comma-delimited,
RFC-4180 quoting. Schema:

| Field | Type | Description |
|---|---|---|
| `clinic_id` | int | Stable row id, 1..80 |
| `name` | string | Free-form clinic label, "<surname> <subdistrict> Clinic" |
| `subdistrict` | string | One of Western, Southern, Tygerberg, Northern, Eastern, Klipfontein, Mitchells Plain, Khayelitsha |
| `wkt_geom` | string | Point geometry as WKT, EPSG:4326, e.g. `POINT(18.4 -33.9)` |

Per-subdistrict row counts (intentionally non-uniform, so an "equal
split" guess is wrong):

| Subdistrict | Count |
|---|---|
| Western | 12 |
| Southern | 12 |
| Tygerberg | 11 |
| Northern | 10 |
| Eastern | 10 |
| Klipfontein | 9 |
| Mitchells Plain | 8 |
| Khayelitsha | 8 |

### Output

`outputs/clinic_inventory.json` — single JSON object with three
top-level keys:

```json
{
  "count": 80,
  "bbox": [xmin, ymin, xmax, ymax],
  "count_per_subdistrict": {"Eastern": 10, "Khayelitsha": 8, ...}
}
```

`bbox` is a 4-list of floats in EPSG:4326 in `[xmin, ymin, xmax, ymax]`
order (longitude first). `count_per_subdistrict` maps each subdistrict
name (verbatim from the input column) to its integer clinic count.

## Failure modes

1. **Lat / lon swap in the bbox.** Agent wrote
   `[ymin, xmin, ymax, xmax]` instead of `[xmin, ymin, xmax, ymax]`
   — the classic confusion when the output schema is a flat 4-list and
   the agent is used to lat-first APIs (e.g. `bounds` ordering in some
   spatial libraries). *Detection:* four bbox componentwise subchecks
   (`bbox_xmin_correct` … `bbox_ymax_correct`). Covered by
   `broken_wrong_bbox` (score 0.455).
2. **Equal-split guess for `count_per_subdistrict`.** Agent listed all
   eight subdistricts but wrote 10 for each (80 / 8). *Detection:*
   `subdistrict_counts_match` (per-key value equality) fails; the
   key-set and sum-consistency subchecks still pass. Covered by
   `broken_wrong_attributes` (score 0.864).
3. **Wrong output format.** Agent wrote the inventory as CSV (or as
   plain text, or as a different JSON shape with no `count` /
   `bbox` / `count_per_subdistrict` keys). *Detection:* Gate 1
   rejects the file (cannot parse as JSON object, or required keys
   missing). Covered by `broken_wrong_format` (score 0.0).
4. **Missing or extra subdistricts.** Agent reported only the
   subdistricts that contain at least N clinics, or invented an
   "Unknown" bucket. *Detection:* `subdistrict_keys_match` (set
   equality) flags both missing and extra keys. Not covered by a
   broken solution; the principled detector is `subdistrict_keys_match`.
5. **Off-by-one count.** Agent mistakenly counted the header line of
   the CSV as a row, or dropped one row to a parse error. *Detection:*
   `count_correct` (strict equality with 80) flags either direction.
   `count_equals_subdistrict_sum` would also surface a mis-count
   that's inconsistent with the reported per-subdistrict roll-up.
   Not covered by a broken solution; the principled detectors are
   `count_correct` and `count_equals_subdistrict_sum`.
6. **Bbox computed only over a subset of clinics** — e.g. agent
   forgot to parse rows whose `wkt_geom` had unusual whitespace and
   silently dropped them. *Detection:* one or more of the four bbox
   componentwise subchecks fail (the dropped rows would shift one or
   more extremes inward). Not covered by a broken solution; the four
   componentwise bbox subchecks are the principled detectors.
7. **Bbox in the wrong CRS** — agent reprojected the points to
   EPSG:3857 before computing the bbox, ending up with metres rather
   than degrees. *Detection:* all four bbox subchecks fail (values
   differ by ~ 10⁶× — far outside the 1e-6° tolerance). Not covered
   by a broken solution; the four bbox subchecks are the principled
   detectors.
8. **Internal inconsistency between top-level count and the per-
   subdistrict sum.** Agent reported `count = 80` but the per-
   subdistrict map sums to 79 (one row leaked in groupby). *Detection:*
   `count_equals_subdistrict_sum` flags it directly. Not covered by a
   broken solution; the principled detector is the consistency
   subcheck.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — lat / lon swap in the
bbox**. A naive `bbox = [min(lats), min(lons), max(lats), max(lons)]`
or a `total_bounds` call used without checking the documented order
is the shortest-string completion of a "compute bbox of these points"
prompt. The grader awards 0.455 for this failure (the four bbox
subchecks, weight 3.0 each, fail), so it is clearly distinguishable
from a correct solution (1.000), from a wrong-format solution (0.000),
and from an equal-split per-subdistrict guess (0.864).
