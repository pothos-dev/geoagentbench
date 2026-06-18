# spa-l1-capetown-hospital-nn

## Story

Dr. Bongani Mthembu plans EMS coverage for the Western Cape provincial
health department. He has a sample of residential pickup addresses and
a hospital-points layer, and wants each address tagged with its nearest
hospital's name and the straight-line distance in metres so the
operations-research team can join the result against shift schedules
and call-volume tables in their PostGIS workflow.

## What this task probes

**Unprompted CRS reasoning for metric distance computation.** The agent
receives WGS84 GeoParquet files of addresses and hospitals and is asked
to find the nearest hospital for each address with distance in metres —
but is given no guidance on coordinate reference systems. The agent must
independently recognise that computing distances on WGS84 (lat/lon)
coordinates gives values in degrees, not metres, and choose an appropriate
projected CRS (e.g. EPSG:32734 UTM 34S) for metric distance computation.

## Why this difficulty

L1: a single primary GIS operation (nearest-neighbour join across two
small point layers) on fully bundled GeoParquet inputs. No fetching,
no chained transforms. The twist — "you must reproject for metric
distances, but nobody told you to" — is the skill being tested.

## Input / output formats

### Input

- `inputs/addresses.parquet` — GeoParquet, EPSG:4326, 120 Point features.
  Columns: `address_id` (string, e.g. `A0001`), `geometry` (Point).
- `inputs/hospitals.parquet` — GeoParquet, EPSG:4326, 37 Point features.
  Columns: `hospital_id` (string, e.g. `H001`), `name` (string),
  `geometry` (Point).

### Output

`nearest_hospital.gpkg` — GPKG, 120 Point features.
No output CRS specified — the model chooses.

| Field | Type | Notes |
|---|---|---|
| `address_id` | string | preserved from input |
| `nearest_hospital_name` | string | name of the closest hospital |
| `distance_m` | numeric (float) | straight-line distance in metres |
| `geometry` | Point | the address point |

## Failure modes

1. **Agent computed NN in WGS84 without reprojecting.** Distances are in
   degrees (~0.01-0.1) instead of metres (~1000-10000). Hospital assignment
   may also differ since lat/lon distance ordering diverges from metric
   ordering at Cape Town's latitude.
   *Detection:* `distance_m_matches_reference` fails catastrophically.
   Covered by `broken_degrees_distance` (score 0.38).
2. **Agent assigned the wrong hospital** (constant hospital, centroid,
   reversed join direction).
   *Detection:* `distance_m_matches_reference` and
   `nearest_hospital_name_matches_reference` both fail.
   Covered by `broken_wrong_hospital` (score 0.38).
3. **Agent reported distance in wrong unit** (km, feet, degrees).
   *Detection:* `distance_m_matches_reference` fails.
   Covered by `broken_distance_in_km` (score 0.69).
4. **Agent wrote the wrong output format** (GeoJSON, Parquet, Shapefile).
   *Detection:* Gate 1 rejects. Covered by `broken_wrong_format` (score 0.0).
5. **Agent omitted or stringified distance_m.**
   *Detection:* Gate 1 or `distance_m_numeric_finite` subcheck.
6. **Agent dropped or duplicated address rows.**
   *Detection:* `address_set_preserved` subcheck.
7. **Agent computed NN in the wrong CRS** (read without CRS, ran in degrees).
   *Detection:* `distance_m_matches_reference` fails.

## Expected weak-agent failure mode

The likeliest failure is **#1** — the agent computes `sjoin_nearest` on
the WGS84 data without reprojecting, getting distances in degrees. A
geospatially literate agent recognises that the inputs are in WGS84 and
that metric distance requires a projected CRS.

## Grader tolerance

Distance tolerance is 50 m (vs the original 1 m) to accept any reasonable
projected CRS for Cape Town. All reasonable projections agree to well
within 50 m for the distances involved (~50-6000 m).
