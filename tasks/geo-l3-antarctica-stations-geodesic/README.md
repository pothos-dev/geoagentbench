# geo-l3-antarctica-stations-geodesic

## What this task probes

This task exercises **geodesic buffering** at extreme southern latitudes where planar buffers are severely distorted, **land-mask clipping** against a complex Antarctic coastline, **cascaded union** to detect overlapping buffer coalitions, and **spatial intersection** of over-water buffer portions against water/bathymetry features. It also tests the agent's ability to identify Antarctic research stations from a noisy POI dataset (Overture places.place) where no explicit "research station" category exists.

## Why this difficulty

**L3** because the task requires live data fetching from multiple Overture themes (places.place, base.land, base.water, base.bathymetry), non-trivial data discovery (identifying research stations from a general POI dataset), a multi-step geometric pipeline (geodesic buffer → clip → union → difference → intersection), and output in a non-default CRS (EPSG:3031). The station-identification ambiguity and the geodesic-vs-planar distinction at polar latitudes make this a genuine real-world challenge.

## Story

Dr. Ellis Whitford, environmental compliance officer at the British Antarctic Survey, is preparing the cross-station logistics-overlap submission for the Antarctic Treaty Consultative Meeting. Each station has a notional 200 km operational sphere; at high southern latitudes that radius cannot be honestly drawn with planar buffering — it must be geodesic and then projected to EPSG:3031.

## Input / output formats

### Inputs (live fetch)
- Overture `places.place` (GeoParquet, EPSG:4326, Point) — Antarctic POIs filtered to research stations
- Overture `base.land` (GeoParquet, EPSG:4326, Polygon) — Antarctic landmass
- Overture `base.water` (GeoParquet, EPSG:4326, Polygon) — Antarctic water bodies
- Overture `base.bathymetry` (GeoParquet, EPSG:4326, Polygon) — Antarctic seabed features

### Outputs
- `station_spheres.geoparquet` (EPSG:3031, MultiPolygon)
  - Columns: `station_id`, `station_name`, `coalition`, `geometry`
  - 200 km geodesic buffer around each station, clipped to land, with overlapping spheres assigned a shared coalition integer ID
- `station_water_overlap.geoparquet` (EPSG:3031, MultiPolygon)
  - Columns: `station_id`, `station_name`, `water_id`, `water_name`, `water_subtype`, `water_source`, `geometry`
  - Over-water portion of each station's sphere, attributed with intersecting water/bathymetry features

## Failure modes

1. **Planar buffer instead of geodesic.** At polar latitudes, a 200 km planar buffer in EPSG:4326 (degrees) produces a tiny ellipse rather than a proper circle. In EPSG:3031 it's better but still distorted away from the standard parallel. → Detection: `geodesic_buffer_check` and `buffer_area_reasonable` subchecks catch undersized areas. Covered by `broken_planar_buffer`.

2. **Wrong output CRS.** Agent outputs in EPSG:4326 instead of EPSG:3031, or forgets to reproject. → Detection: the `sphere_coords_projected` subcheck catches degree-range coordinates; `crs_is_3031` validates CRS metadata; the area subchecks fail on degree-unit areas. Covered by `broken_wrong_crs`.

3. **No coalition detection.** Agent assigns each station its own coalition ID instead of unioning overlapping spheres. → Detection: `coalition_exists` subcheck requires >1 distinct coalition value (since Antarctic Peninsula stations form a large cluster). Covered by `broken_no_coalition`.

4. **Station identification failure.** Agent fetches all 2300+ Antarctic POIs instead of filtering to research stations, or filters too aggressively and gets <5 stations. → Detection: the `min_station_count` subcheck requires ≥5 stations; `station_count_tolerance` catches gross over/under-counting; `station_name_overlap` catches wrong station sets. Partially covered by `broken_no_coalition` (half stations).

5. **Missing land clip.** Agent outputs raw geodesic buffers without clipping to the landmass, including ocean areas in the spheres output. → Detection: `buffer_area_reasonable` would show inflated area (buffers extend far over ocean). Not directly covered by a broken solution — principled-reasoning via area subcheck.

6. **Missing water overlap computation.** Agent produces station_spheres but skips or botches the water overlap output. → Detection: `water_output_present`, `water_station_overlap`, and `water_area_reasonable` subchecks. Not directly covered by a broken solution — principled-reasoning.

7. **No water/bathymetry attribution.** Agent computes over-water portions but doesn't intersect with water/bathymetry features (missing water_source column values). → Detection: `water_source_attribution` subcheck requires at least one of base.water/base.bathymetry in the output. Not directly covered — principled-reasoning.

## Expected weak-agent failure mode

The weakest baseline will likely use a planar buffer (in EPSG:4326 degrees or even EPSG:3031 metres without geodesic correction), producing dramatically undersized buffers, and may fail to identify research stations from the noisy Overture POI data.
