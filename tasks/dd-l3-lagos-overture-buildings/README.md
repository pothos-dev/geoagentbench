# dd-l3-lagos-overture-buildings

## Story

Adaeze Okafor at the Lagos State Emergency Management Agency is
updating the flood-risk model for the rainy-season briefing to the
governor. She needs every building larger than 1000 m² across Lagos
State plus a per-LGA summary table, but she cannot afford to download
the full Overture buildings theme. The agent must scope the fetch to
the actual state boundary (no hand-supplied bbox), use partition
pushdown on the Overture S3 bucket, reproject to Nigeria West Belt for
area-correct sizing, and emit both the cleaned GeoParquet and a
tabular Parquet roll-up.

## What this task probes

* **Polygon-driven scope** — discovering the Lagos State boundary from
  Overture's `divisions.division_area` theme (`subtype='region'`) and
  using it to define the area of interest. The task instruction does
  *not* hand the agent a bbox — they must derive it themselves from
  the state polygon for the S3 partition pushdown.
* **Partition-pushdown spatial fetch** — querying Overture's
  cloud-hosted GeoParquet directly via DuckDB (or equivalent) with
  bbox filtering derived from the state polygon, not downloading the
  entire ~1 TB buildings theme.
* **CRS reprojection for area calculation** — EPSG:4326 → EPSG:26331
  (Minna / Nigeria West Belt) for honest metre-squared areas, then
  back to WGS84 for the geometry export.
* **Area-based attribute filter** — keep only footprints > 1000 m²
  after reprojection.
* **Multi-source spatial join** — fetch LGA boundary polygons
  (`subtype='county'`, `region='NG-LA'`) and join buildings to LGAs.
  Because the 20 LGAs partition the state polygon, every retained
  building lands in exactly one LGA — no "outside any LGA" bucket.
* **Dual-output pipeline** — one GeoParquet (spatial) and one plain
  Parquet (tabular summary) with aggregation per LGA.
* **Null-aware aggregation** — Overture height is sparse in Lagos;
  `n_with_height` and `p50_height_m` must handle NaN correctly.

## Why this difficulty

L3: full real-world workflow with live data fetch from two Overture
themes (buildings + divisions, at two `subtype` levels — region for
scope, county for the roll-up), CRS round-trip, area calculation,
spatial join, and dual-format output. No bundled inputs and no
hand-supplied bounding box — the agent must discover and query the
Overture S3 endpoint and define its own spatial filter. Medium drift
sensitivity because Overture releases evolve quarterly.

## Input / output formats

### Inputs

No bundled inputs. The agent fetches live from Overture Maps:

* `divisions.division_area` — cloud-hosted GeoParquet on
  `s3://overturemaps-us-west-2/release/<version>/theme=divisions/type=division_area/`.
  Two slices needed: `subtype='region'` with `country='NG'` and
  `names.primary='Lagos'` for the state boundary (1 row, drives the
  bbox); and `subtype='county'` with `region='NG-LA'` for the 20
  Lagos State Local Government Areas.
* `buildings.building` — same bucket, `theme=buildings/type=building/`.
  Schema includes `id`, `geometry` (Polygon, EPSG:4326), `height`
  (nullable double), plus many other fields not needed here.

### Outputs

`lagos_buildings.geoparquet` — GeoParquet in EPSG:4326. Each feature
is a building footprint polygon with:

| column | type | description |
|---|---|---|
| `id` | string | Overture building id |
| `height` | float (nullable) | Overture height in metres |
| `footprint_area_m2` | float | footprint area in m² (EPSG:26331) |
| `lga` | string | Local Government Area name |
| `geometry` | Polygon / MultiPolygon | footprint in EPSG:4326 |

Reference contains one row per building in Lagos State, each
assigned to exactly one of the 20 LGAs (no "unassigned" bucket —
the LGAs partition the state polygon by construction).

`lagos_building_summary.parquet` — plain Parquet (no geometry):

| column | type | description |
|---|---|---|
| `lga` | string | LGA name |
| `n_buildings` | int | count of buildings > 1000 m² |
| `total_footprint_m2` | float | sum of footprint areas |
| `n_with_height` | int | buildings with non-null height |
| `p50_height_m` | float (nullable) | median height (null if none) |

Reference has one row per LGA that contains at least one
> 1000 m² building (up to 20 rows).

## Failure modes

1. **Agent downloads the entire buildings theme.** Tries to read all
   ~1 TB of Overture buildings instead of using bbox pushdown. Times
   out or runs out of memory. *Detection:* deadline_seconds exceeded
   (task-level). Not covered by a grader subcheck.

2. **Agent emits wrong output format.** Writes CSV, GeoJSON, or
   Shapefile instead of GeoParquet/Parquet. *Detection:* Gate 1
   rejects on read. Covered by `broken_wrong_format` (score 0.0).

3. **Agent skips the area filter.** Fetches buildings and writes
   them all without filtering to > 1000 m². Output has too many
   features. *Detection:* `building_count_tolerance`,
   `feature_set_jaccard`, and `area_filter_applied` all fail.
   Covered by `broken_no_area_filter` (score ≈ 0.42).

4. **Agent computes area in WGS84 (degrees²) instead of EPSG:26331.**
   The area values are ~10⁻⁸ instead of ~10³. The filter still
   applies (all buildings pass since degrees² > 1000 is false, or
   the agent uses a different threshold). *Detection:*
   `area_filter_applied` and `summary_area_reasonable` fail.
   Covered by `broken_wrong_crs_area` (score ≈ 0.73).

5. **Agent uses wrong CRS for area (e.g. Web Mercator EPSG:3857).**
   Web Mercator distorts area near the equator by ~0.6 %. Close but
   systematically biased. *Detection:* `summary_area_reasonable` may
   catch large deviations; smaller biases fall within the ±20 %
   tolerance. Principled-reasoning: Web Mercator area at 6.5°N is
   close to true area, so this failure mode may score nearly 1.0 —
   acceptable, since the grader tests the *concept* of computing
   area in a metric CRS rather than the choice of any specific EPSG
   (the instruction deliberately names no projected CRS).

6. **Agent fails to spatial-join with LGA boundaries.** Outputs
   buildings without LGA assignment or with a constant LGA value.
   *Detection:* `summary_lga_overlap` fails (0 % of reference LGA
   names found). Not covered by a dedicated broken solution;
   principled detector is the `summary_lga_overlap` subcheck.

7. **Agent fetches divisions but doesn't filter to Lagos State.**
   Includes Ogun State LGAs in the summary, or fetches a hand-drawn
   bbox that bleeds across the state boundary. *Detection:*
   `summary_lga_overlap` may still pass (Lagos LGAs are a subset),
   but `building_count_tolerance` and `summary_total_consistent`
   register the inflated count. Principled detector: count + LGA
   overlap checks.

8. **Agent drops the summary file entirely.** Writes only the
   buildings GeoParquet. *Detection:* Gate 1 fails on missing
   `lagos_building_summary.parquet`. Score = 0.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#4 — computing area in WGS84
degrees²**. A weak agent that successfully fetches from Overture and
applies the bbox filter is likely to skip the metric-CRS reprojection
step, computing area in the native WGS84 CRS. This produces a
structurally correct output with the right building set but
nonsensical area values, scoring ≈ 0.73.
