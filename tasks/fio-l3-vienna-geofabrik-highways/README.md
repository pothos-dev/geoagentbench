# fio-l3-vienna-geofabrik-highways

## Story

Ingrid Maier runs a small environmental consultancy commissioned by the City of Vienna to model traffic noise around the Gürtel ring road.  She needs every Vienna `highway=*` segment that intersects a 500 m buffer of the ring road, plus every public-transport route relation passing through the same band — extracted from OSM and saved as a multi-layer GPKG in MGI Lambert, with full untruncated OSM tag names so her acoustician-collaborator can join speed and lane-count data without guessing column meanings.

## What this task probes

Multi-layer GeoPackage I/O from live OSM data, combining several GIS skills: Overpass / PBF querying, tag-filtered extraction of ways and relations, CRS reprojection to a national projected system (EPSG:31287), planar buffering, spatial intersection filtering, attribute preservation including non-ASCII (German diacritics), and correctly assembling route-relation member ways into MultiLineString features.

## Why this difficulty

**L3** — requires fetching live data from an external source (Overpass API or Geofabrik PBF), composing multiple operations (fetch → identify ring road → buffer → spatial filter → relation assembly → multi-layer GPKG write), and handling real-world encoding issues (German umlauts in street names).  No bundled input data is provided.

## Input / output formats

**Inputs:** None bundled.  Agent fetches from OpenStreetMap (Overpass API or Geofabrik Austria PBF).

**Outputs:**
- `vienna_network.gpkg` — GeoPackage with two layers:
  - `highways` (LineString, EPSG:31287): `osm_id`, `name`, `highway`, `maxspeed`, `lanes`, `surface`, `oneway`
  - `pt_routes` (MultiLineString, EPSG:31287): `osm_id`, `ref`, `name`, `operator`, `route`

## Failure modes

1. **Missing layer** — agent writes only the `highways` layer and omits `pt_routes`.  Detection: Gate 1 fails (`broken_no_pt_layer`).

2. **Wrong CRS / stamped without reprojection** — agent stamps CRS metadata as EPSG:31287 but coordinates remain in EPSG:4326 (degrees).  Detection: `highway_coords_range` and `pt_route_projected` subchecks fail (`broken_wrong_crs`).

3. **Diacritic corruption** — agent strips or mangles German umlauts (ü→u, ö→o, ß→ss) during text processing or encoding.  Detection: `diacritics_preserved` subcheck fails (`broken_truncated_attrs`).

4. **Buffer in degrees** — agent computes the 500 m buffer in EPSG:4326 (geographic degrees) instead of the projected CRS, producing a vastly wrong buffer polygon that captures too many or too few highways.  Detection: `highway_count` subcheck (count will be far outside ±15 % tolerance); principled-reasoning — coordinate range checks would also catch the wrong spatial extent.

5. **PT routes split into individual ways** — agent writes one feature per way member instead of one MultiLineString per route relation.  Detection: `pt_multilinestring` subcheck (MultiLineString fraction < 0.90) and `pt_route_count` (inflated count).

6. **Shapefile-style column truncation** — agent round-trips through Shapefile (10-char column names), losing `maxspeed`→`maxspd`, `surface`→`srface`, etc.  Detection: Gate 1 column check (missing required columns).

7. **Wrong Gürtel identification** — agent fails to identify the ring road correctly (e.g., searches for "Ring" instead of streets ending in "Gürtel"), capturing the wrong set of highways.  Detection: `highway_count` (wrong magnitude) and `diacritics_preserved` (no "ürtel" pattern in names if wrong area).

## Expected weak-agent failure mode

The most likely failure is computing the 500 m buffer in geographic coordinates (EPSG:4326) instead of the projected CRS, or failing to assemble PT route relations into MultiLineString features (outputting individual ways instead).
