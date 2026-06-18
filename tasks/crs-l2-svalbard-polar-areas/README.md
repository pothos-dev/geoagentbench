# crs-l2-svalbard-polar-areas

## Story

Astrid Hansen, a glaciologist at the Norwegian Polar Institute, is updating her year-end glacier-retreat figure for the institute's outreach blog. The bundled OSM-derived named-glacier polygons for Svalbard are in WGS84 — useless for area-honest ranking at 78°N because cylindrical projections explode at high latitudes. She needs the polygons reprojected to a polar projection chosen for accurate area measurement, the area of each computed honestly in projected metres, and the top 20 returned as CSV with their per-glacier bounding boxes for the blog's accompanying static map. The CSV declares which CRS was used so downstream tools can validate the frame.

## What this task probes

CRS reprojection of polygons from a geographic CRS (EPSG:4326) to an appropriate polar projected CRS, composed with three additional operations:

* per-feature area calculation **in the projected CRS** (km²),
* per-feature axis-aligned bounding-box extraction **in the projected CRS**, and
* top-N ranking and CSV serialisation with a `crs_epsg` declaration column.

It exercises the agent's awareness that area calculations on lat/lon are meaningless, that the textbook-correct choice for "true geographic area" is an equal-area projection (LAEA), and that self-describing geodata declares its CRS so consumers can validate the frame.

## Why L2

Four chained operations on bundled data: reproject → compute area → compute bbox → rank top-20 → emit CSV. No data discovery, no live fetch, no malformed input — but enough composition that an agent that gets only the projection right (and forgets to compute area in the projected frame, say) still loses ground. Fits the L2 definition: 2–4 chained operations on bundled data.

## Input / output formats

**Input.** `inputs/svalbard_glaciers_wgs84.gpkg` — single layer `glaciers`, EPSG:4326, 169 Polygon / MultiPolygon features sliced from Overture release `2026-04-15.0` (`theme=base`, `type=land`, `subtype='glacier'`, `names.primary IS NOT NULL`) over Svalbard (10°–35°E, 76°–81°N). Columns: `id` (string), `name` (string, non-null), `subtype` (string, always `glacier`), `class` (string, always `glacier`), `geometry`.

**Output.** `outputs/svalbard_glaciers_top20.csv` — 20 rows ranked by `area_km2` descending, columns:

| Column | Type | Notes |
|---|---|---|
| `name` | string | Overture `names.primary`. |
| `area_km2` | float | Polygon area in the agent's chosen polar CRS, km². |
| `bbox_minx_polar` | float | Minimum easting in the agent's chosen CRS, metres. |
| `bbox_miny_polar` | float | Minimum northing in the agent's chosen CRS, metres. |
| `bbox_maxx_polar` | float | Maximum easting in the agent's chosen CRS, metres. |
| `bbox_maxy_polar` | float | Maximum northing in the agent's chosen CRS, metres. |
| `crs_epsg` | int | EPSG code of the polar projection the agent used. Must be the same value on every row. |

## Accepted projections

The grader accepts any WGS-84-datum North-Pole-origin projected CRS:

| EPSG | Family | Central meridian | Notes |
|---|---|---|---|
| 3573 | LAEA | –100°E | North Pole LAEA Canada |
| 3574 | LAEA | –40°E | North Pole LAEA Atlantic |
| **3575** | **LAEA (canonical)** | **+10°E** | **North Pole LAEA Europe — the reference pick for Svalbard** |
| 3576 | LAEA | +90°E | North Pole LAEA Russia |
| 6931 | LAEA | 0°E | NSIDC EASE-Grid 2.0 North |
| 3413 | Polar Stereographic | NSIDC convention | Conformal, not equal-area |
| 3995 | Polar Stereographic | EPSG Arctic convention | Conformal, not equal-area |

The five LAEA variants give mathematically-exact areas at every latitude (the central meridian only rotates the bbox values, it does not affect the area). The two Polar Stereographic variants are conformal. At Svalbard latitudes their per-glacier area distortion is well under 1%, so they pass the area subchecks, but they fail the `equal_area_crs_used` subcheck. The four data-content subchecks (`top20_name_set_matches`, `per_glacier_area_matches`, `total_top20_area_within_1_percent`, `per_glacier_bbox_matches`) carry weight 3; the five schema/structural subchecks carry weight 1, for 17 weighted points total. An LAEA pick scores 17/17 = 1.0; a Polar Stereographic pick scores 16/17 = 0.941.

CRSes outside this list (UTM 33N, Web Mercator, lat/lon, ETRS89 variants, and so on) are no longer hard-rejected at Gate 1. The grader passes Gate 1 for any parseable EPSG and soft-grades the CRS via two subchecks: `equal_area_crs_used` (LAEA family) and `crs_in_meaningful_set` (the seven-EPSG North-Pole-origin set above). Reference values are recomputed in the agent's declared CRS so the per-glacier area and bbox subchecks compare apples to apples, but a non-meaningful pick also tends to break `top20_name_set_matches` and the area subchecks because the ranking by projected area differs from the ranking the canonical CRSes produce.

## Failure modes

1. **Skipped reprojection, declared `crs_epsg=4326` with degrees² area.** Both CRS subchecks fail, area and total-area subchecks fail because the reference recomputed in 4326 produces tiny degree-squared values that the submission's km²-labelled degree² numbers do not match, and `top20_name_set_matches` collapses because the largest glaciers by degree² area are different from the largest by metric area. Net 6/17 = 0.353. Covered by `broken_no_reprojection`.

2. **Wrong family, UTM 33N (the Norwegian topo convention) or Web Mercator (the wrong-at-high-latitudes warning).** No longer hard-failed. Soft-graded via the two CRS subchecks plus whatever the agent's frame does to the per-glacier comparisons. Principled detector, not covered by a broken solution.

3. **Conformal pick: EPSG:3995 or EPSG:3413.** Mathematically defensible (polar, North-Pole-origin) but the instruction asks for "true geographic area", which is exact only under LAEA. The grader accepts the pick, recomputes the reference in 3995/3413, and lets all area/bbox subchecks pass. Only `equal_area_crs_used` (weight 1) fails. Net 16/17 = 0.941. Covered by `broken_conformal_pick`.

4. **Off-by-N ranking: emits ranks 6 to 25 instead of 1 to 20.** Per-glacier values for the rows present are correct, but the top-20 set Jaccard collapses to 0.60 and total area drops about 87% because the biggest five are missing; both failed subchecks carry weight 3. Net 11/17 = 0.647. Covered by `broken_offset_topN`.

5. **Wrong output format: GeoJSON or Parquet under the .csv name.** Gate 1 fails CSV-parse. Covered by `broken_wrong_format`.

6. **Inconsistent `crs_epsg` across rows.** Gate 1 fails with `crs_epsg is inconsistent across rows: [...]`. Principled detector.

7. **Unsorted output.** Even if the right 20 names are returned, the persona's "ranking" is broken if the CSV is unsorted. Caught by the `sorted_by_area_desc` subcheck.

8. **Swapped bbox columns (min/max reversed).** Schema looks right but min and max are swapped. Caught by the `bbox_min_less_than_max` subcheck plus a `per_glacier_bbox_matches` failure.

## Expected weak-agent failure mode

The most likely weak-agent error is **picking a Polar Stereographic CRS (3995 or 3413)** instead of an LAEA variant. Polar Stereographic is what most "Arctic GIS" tutorials show, what NSIDC ships sea-ice products in, and what the original version of this task pinned in its grader. An agent that pattern-matches on "Arctic projection" without reading the "true geographic area" cue picks one of the stereographic variants and scores 16/17 = 0.941, clearly above an agent that picks a non-polar CRS (lands in the 0.0 to 0.5 range under soft-grading depending on how badly the frame breaks the per-glacier and top-20 comparisons) and clearly below one that recognises the LAEA-for-area textbook answer (1.0).
