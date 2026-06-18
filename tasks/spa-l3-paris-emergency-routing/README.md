# spa-l3-paris-emergency-routing

## Story

Captain Julien Moreau, an emergency-response analyst at SAMU's Paris coordination centre, is rebuilding the dispatch model after a redistricting. He has a sample of historical emergency-call points; for each call he needs the closest hospital by network distance with the shortest-path geometry exported, plus a small full distance matrix between every call and its three closest candidate hospitals, plus a 15-minute isochrone around each hospital so management can see coverage gaps. The agent must fetch Paris's driveable road network and hospital locations from live OpenStreetMap data, build a routing graph, and ship a single multi-layer GPKG in Lambert-93.

## What this task probes

This task exercises four core spatial-analysis operations on a live-fetched road network:

1. **Closest facility** — for each incident, identify the network-nearest hospital (not Euclidean).
2. **Shortest path** — export the actual route geometry as a LineString.
3. **Network distance matrix** — compute pairwise distances between incidents and their top-3 hospitals.
4. **Isochrone generation** — build a 15-minute drive-time polygon around each hospital.

Secondary skills include: Overpass API querying, directed graph construction from OSM ways (oneway handling, maxspeed parsing), speed-based travel-time edge weighting, CRS reprojection to Lambert-93, and multi-layer GPKG output.

## Why L3

This task requires live data fetching from OpenStreetMap (only the eight incident points are bundled; all geodata is live-fetched), multi-step processing (fetch → graph build → four distinct routing analyses), and integration of several non-trivial GIS concepts (network routing vs Euclidean distance, directed graphs, travel-time vs distance weighting, isochrone computation). The pipeline has 4+ chained operations and uses a live data source, placing it firmly at L3.

## Input / output formats

**Inputs:** `inputs/incidents.csv` (8 rows: `incident_id`, `latitude`, `longitude`, `label`). The agent must fetch the rest:
- Driveable highway network from OSM Overpass (bbox 48.83,2.30 to 48.88,2.38)
- Hospital locations (`amenity=hospital`) from the same bbox

**Output:** `emergency_routing.gpkg` (EPSG:2154) with four layers:

| Layer | Geometry | Required columns |
|---|---|---|
| `incidents` | Point | `incident_id` |
| `closest_hospital` | LineString | `incident_id`, `hospital_name`, `network_distance_m` |
| `distance_matrix` | Point (dummy) or empty | `incident_id`, `hospital_name`, `rank`, `network_distance_m` |
| `isochrones_15min` | MultiPolygon | `hospital_name`, `travel_time_min` |

The reference outputs additionally carry a `hospital_osm_id` provenance column in the last three layers; it is not part of the graded contract.

## Failure modes

1. **Euclidean instead of network distance** — Agent computes straight-line distance instead of routing along roads. Detection: `closest_hospital_distances` subcheck catches inflated/deflated distances (±15% tolerance). Covered by `broken_wrong_geometry`.

2. **Wrong CRS / unprojected output** — Agent outputs in EPSG:4326, a non-canonical metric CRS, or with no declared CRS. Detection: a layer with no usable CRS fails the format gate; a defensible-but-non-canonical metric CRS (UTM 31N) is reprojected to Lambert-93 before the spatial subchecks and costs the `crs_is_canonical` subcheck; degree coordinates declared as a projected CRS trip the `incident_coords_in_metres` subcheck.

3. **Missing layers** — Agent produces only some of the four required layers. Detection: Gate 1 checks all four layer names exist in the GPKG. Covered by `broken_wrong_format`.

4. **Wrong format** — Agent outputs GeoJSON or multiple files instead of a single multi-layer GPKG. Detection: Gate 1 fails when expected layers are missing. Covered by `broken_wrong_format`.

5. **Undirected graph / ignored oneway** — Agent builds an undirected graph, allowing routing against oneway streets. Detection: `closest_hospital_distances` subcheck catches systematically shorter distances. Principled-reasoning — not directly covered by a broken solution but absorbed by the 15% distance tolerance.

6. **No speed-based travel time** — Agent uses uniform speed or distance-only routing for isochrones instead of travel-time weighting with maxspeed. Detection: `isochrone_coverage_iou` and `isochrone_area_plausible` catch incorrectly-sized isochrones. Principled-reasoning.

7. **Partial hospital coverage** — Agent finds only a subset of hospitals (e.g., only nodes, missing way/relation hospitals). Detection: `isochrone_count` and `isochrone_hospital_names` subchecks. Covered by `broken_partial`.

8. **Incorrect distance matrix structure** — Agent produces wrong number of candidate hospitals per incident or doesn't sort by rank. Detection: `distance_matrix_count` and `distance_matrix_rank_order` subchecks. Covered by `broken_partial`.

## Expected weak-agent failure mode

The weakest baseline will likely compute Euclidean distances instead of network distances, either because it doesn't build a routing graph at all or because it uses straight-line nearest-neighbour and fabricates "shortest path" geometries as direct lines.
