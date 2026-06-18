# Task Inventory

Source of truth for the 36-task geospatial agent benchmark. Each task block lists axis assignments, output artifacts, and a one-paragraph realism story. The coverage matrix at the end of this document demonstrates that every variant on every axis is hit by ≥ 1 task.

## Schema

Each task block uses a fixed set of fields:

- **`task_id`** — slug used as the directory name under `tasks/`.
- **`category`** — one of `data_discovery`, `format_io`, `crs_reprojection`, `geometric_ops`, `spatial_analysis`, `data_cleaning`.
- **`difficulty`** — `L1` (single op, bundled), `L2` (chained, bundled), `L3` (live, full workflow).
- **`region`** — geographic region anchor.
- **`data_source`** — one of the five Axis 5 variants.
- **`primary_op`** / **`secondary_ops`** — operations from Axes 1–2.
- **`format_in`** / **`format_out`** — Axis 3 input / restricted-output formats.
- **`crs_in`** / **`crs_out`** — EPSG codes; `crs_chain` lists intermediate CRSes when the workflow reprojects more than once.
- **`geometry_type`** — input geometry type from Axis 7 (covers all of Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon across the inventory).
- **`data_scale`** — Small / Medium / Large.
- **`data_quality_issues`** — Axis 6 variants present in the bundled / fetched data.
- **`overture_themes`** / **`osm_tags`** — Axis 8 / Axis 9 variants exercised.
- **`output_artifacts`** — list of `{name, format, crs?, geometry_type?}` per the HTTP contract.
- **`story`** — one paragraph: named persona + their question + what they do with the answer.

Output formats are restricted to `JSON | CSV | GeoJSON | Parquet | GeoParquet | GPKG`. Input formats are unrestricted.

---

## Category: data_discovery

### Task: `dd-l1-vienna-gpkg-manifest`

| Field | Value |
|---|---|
| Category | data_discovery |
| Difficulty | L1 |
| Region | Vienna, Austria |
| Data source | Bundled local file |
| Primary op | Schema introspection (layer / CRS / count enumeration) |
| Secondary ops | — |
| Format in | GPKG (multi-layer: districts, parks, schools) |
| Format out | JSON |
| CRS in | EPSG:31287 (MGI / Austria Lambert) |
| CRS out | n/a (metadata only) |
| Geometry type | Polygon, Point (across layers) |
| Data scale | Small (~10² features per layer) |
| Data quality issues | — |
| Overture themes | `divisions.division_area` |
| OSM tags | `boundary=administrative` |

**Output artifacts:**
- `manifest.json` (format: `json`) — list of `{layer_name, crs, geometry_type, feature_count, bbox}` records.

**Story.** Lukas Hofer, a junior planner at Vienna's MA 18 urban-planning department, inherits a multi-layer GPKG from a retired colleague who maintained the bicycle-network reform dataset. Before scripting against it he wants a one-page manifest listing each layer's name, declared CRS, geometry type, and feature count, so he can decide which of the seven layers feed next month's briefing to the city councillor and which are stale auxiliary cuts.

### Task: `dd-l1-london-parks-count`

| Field | Value |
|---|---|
| Category | data_discovery |
| Difficulty | L1 |
| Region | London, United Kingdom |
| Data source | Bundled local file |
| Primary op | Attribute filter + feature count + bbox |
| Secondary ops | Bounding box (Axis 1) |
| Format in | FlatGeobuf |
| Format out | JSON |
| CRS in | EPSG:27700 (OSGB36 / British National Grid) |
| CRS out | EPSG:4326 (bbox reported in lat/lon) |
| Geometry type | Polygon |
| Data scale | Small (~10² parks) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `leisure=park` (`leisure=*`) |

**Output artifacts:**
- `parks_summary.json` (format: `json`) — `{count, total_area_ha, bbox_wgs84}`.

**Story.** Priya Shah at the Greater London Authority's parks team is sizing the corpus before commissioning a green-space accessibility study. She has a FlatGeobuf snapshot of OSM-derived parks and needs to know how many parks exceed 1 ha and the WGS84 bounding box of that subset, so the procurement officer can pick a study perimeter without having to open QGIS.

### Task: `dd-l1-capetown-clinics-bbox`

| Field | Value |
|---|---|
| Category | data_discovery |
| Difficulty | L1 |
| Region | Cape Town, South Africa |
| Data source | Bundled local file |
| Primary op | CSV-with-WKT parse + count + bbox |
| Secondary ops | Bounding box |
| Format in | CSV with WKT |
| Format out | JSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | Point |
| Data scale | Small (~10² clinics) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `amenity=clinic` (`amenity=*`) |

**Output artifacts:**
- `clinic_inventory.json` (format: `json`) — `{count, bbox, count_per_subdistrict}`.

**Story.** Naledi Mokoena, a data analyst at the City of Cape Town Health Department, has been handed a legacy CSV export of public clinic locations with geometry stored as a `wkt_geom` column. She wants a quick inventory — record count, bounding box, and counts per sub-district — to verify the export covers the full metropolitan area before she ingests it into the case-management system.

### Task: `dd-l2-bangkok-multicrs-audit`

| Field | Value |
|---|---|
| Category | data_discovery |
| Difficulty | L2 |
| Region | Bangkok, Thailand |
| Data source | Bundled local file |
| Primary op | Per-layer CRS audit + reconcile + tabular assembly |
| Secondary ops | Schema introspection, attribute decoding |
| Format in | GPKG (multi-layer with disagreeing CRSes) |
| Format out | CSV |
| CRS in | EPSG:24047 (Indian 1975 / UTM 47N), EPSG:32647 (WGS84 / UTM 47N), EPSG:4326 (mixed across layers) |
| CRS out | n/a (audit table only) |
| Geometry type | Polygon, LineString, Point (across layers) |
| Data scale | Medium (~10⁴ features total) |
| Data quality issues | Mixed CRSes in one source, Encoding issues (Latin-1 mojibake on Thai labels) |
| Overture themes | — |
| OSM tags | `highway=*` (one of the layers) |

**Output artifacts:**
- `crs_audit.csv` (format: `csv`) — one row per layer: `layer_name, declared_crs, geometry_type, feature_count, sample_x, sample_y, encoding_detected`.

**Story.** Krit Suwannarat audits contractor deliverables for Thailand's Ministry of Interior. A consortium has just shipped a multi-layer GPKG of ward-level infrastructure — but he suspects the layers were merged from sources with different CRSes and an in-house tool that mangled Thai-script labels into Latin-1 mojibake. He needs an audit CSV listing each layer's declared CRS, sample coordinates, and detected text encoding so he can reject the deliverable with specific defects cited.

### Task: `dd-l2-tokyo-overture-schools`

| Field | Value |
|---|---|
| Category | data_discovery |
| Difficulty | L2 |
| Region | Tokyo, Japan |
| Data source | Bundled local file (Overture-format sample) |
| Primary op | Attribute filter on partitioned Parquet |
| Secondary ops | Bounding-box crop, spatial join — contains (bbox polygon contains place point) |
| Format in | GeoParquet (Overture `places.place` schema, partitioned) |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | Point |
| Data scale | Medium (~10⁴ places in the bundled subset) |
| Data quality issues | — |
| Overture themes | `places.place` |
| OSM tags | — |

**Output artifacts:**
- `tokyo_schools.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `Point`) — places where `categories.primary == 'school'` inside the supplied bbox polygon.

**Story.** Aiko Tanaka, a researcher at the Tokyo Metropolitan Government's Education Bureau, is preparing a summer briefing on school-density disparities across wards. She has a bundled Overture `places.place` GeoParquet sample and a bbox polygon for the 23 special wards; she needs every place whose primary category is `school` and that lies inside the polygon, exported as GeoJSON with the place name (in CJK), confidence, and address fields preserved, ready for a colleague's R-based visualisation.

### Task: `dd-l3-lagos-overture-buildings`

| Field | Value |
|---|---|
| Category | data_discovery |
| Difficulty | L3 |
| Region | Lagos, Nigeria |
| Data source | Overture Maps current release (cloud-hosted partitioned Parquet) |
| Primary op | Partition-pushdown spatial+attribute filter at fetch time |
| Secondary ops | Bounding box, reprojection, area calculation |
| Format in | GeoParquet (Overture `buildings.building`, `buildings.building_part`) |
| Format out | GeoParquet, plain Parquet (summary) |
| CRS in | EPSG:4326 |
| CRS out | EPSG:26331 (Minna / Nigeria West Belt) for area; EPSG:4326 for geometry export |
| Geometry type | Polygon, MultiPolygon |
| Data scale | Large (10⁶+ buildings in greater Lagos) |
| Data quality issues | Null/missing attributes (Overture `height` often null in sparse regions) |
| Overture themes | `buildings.building`, `buildings.building_part` |
| OSM tags | — |

**Output artifacts:**
- `lagos_buildings.geoparquet` (format: `geoparquet`, crs: `EPSG:4326`, geometry_type: `Polygon`) — buildings with footprint area > 1000 m² inside the LGA bbox.
- `lagos_building_summary.parquet` (format: `parquet`) — tabular: `lga, n_buildings, total_footprint_m2, n_with_height, p50_height_m`.

**Story.** Adaeze Okafor at the Lagos State Emergency Management Agency is updating the flood-risk model for the rainy-season briefing to the governor. She needs every building larger than 1000 m² across greater Lagos plus a per-LGA summary table — but she cannot afford to download the full Overture buildings theme. The agent must filter at fetch time using partition pushdown on the Overture S3 bucket, reproject to Nigeria West Belt for area-correct sizing, and emit both the cleaned GeoParquet and a tabular Parquet roll-up that the agency's existing dashboard can consume directly.

---

## Category: format_io

### Task: `fio-l1-vienna-shapefile-recovery`

| Field | Value |
|---|---|
| Category | format_io |
| Difficulty | L1 |
| Region | Vienna, Austria |
| Data source | Bundled local file |
| Primary op | Format conversion (Shapefile → GeoJSON) with column-name recovery |
| Secondary ops | Reprojection |
| Format in | Shapefile (with companion `.cpg` declaring `CP1252`, plus `column_map.csv` mapping truncated → full names) |
| Format out | GeoJSON |
| CRS in | EPSG:31287 (MGI / Austria Lambert) |
| CRS out | EPSG:4326 |
| Geometry type | Polygon |
| Data scale | Small (~10² parcels) |
| Data quality issues | Shapefile column truncation, Encoding issues (Latin-1 / CP1252 attribute text with diacritics) |
| Overture themes | — |
| OSM tags | — |

**Output artifacts:**
- `parcels.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `Polygon`) — original full attribute names restored, German diacritics decoded correctly.

**Story.** Stefan Ebner, a cadastre intern at Austria's BEV (federal mapping agency), is helping migrate a 1990s Vienna parcel snapshot from Shapefile into the modern web-tiles pipeline. The shapefile's dBase columns truncated the original attribute names to 10 characters, the encoding is CP1252, and the geometry is in MGI Lambert. He has a `column_map.csv` listing the original full names. He needs a clean WGS84 GeoJSON with the full names restored and German umlauts intact, so the front-end developer can drop it into the new viewer without any post-processing.

### Task: `fio-l1-paris-kml-pois`

| Field | Value |
|---|---|
| Category | format_io |
| Difficulty | L1 |
| Region | Paris, France |
| Data source | Bundled local file |
| Primary op | Format conversion (KML → GeoJSON) preserving styling-independent attributes |
| Secondary ops | — |
| Format in | KML |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | Point |
| Data scale | Small (~10² POIs) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `amenity=*` (mix of cafes, libraries, tourist info booths) |

**Output artifacts:**
- `paris_pois.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `Point`) — `name` and `category` (parent Folder) preserved; `verified_date` extracted from the HTML "Dernière vérification" line as an ISO date.

**Story.** Margaux Léger, an intern in RATP's transport-planning unit, has received a Google My Maps export (`.kml`) from a colleague who hand-curated a list of late-night Métro-adjacent amenities. She needs it as a flat GeoJSON the team's internal map server can ingest, with the "last verified" date pulled out of the HTML info-card descriptions into its own queryable column so the team can identify stale records.

### Task: `fio-l1-nyc-csvwkt-addresses`

| Field | Value |
|---|---|
| Category | format_io |
| Difficulty | L1 |
| Region | New York City, USA |
| Data source | Bundled local file (Overture-format `addresses.address` sample) |
| Primary op | Format conversion (CSV-with-WKT → GeoParquet) with type coercion |
| Secondary ops | — |
| Format in | CSV with WKT (`geometry_wkt`, `recorded_at` as ISO string, `unit_count` as quoted string) |
| Format out | GeoParquet |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | Point |
| Data scale | Small (~10³ addresses) |
| Data quality issues | Attribute type coercion (date-as-string, numeric-as-string) |
| Overture themes | `addresses.address` |
| OSM tags | — |

**Output artifacts:**
- `addresses.geoparquet` (format: `geoparquet`, crs: `EPSG:4326`, geometry_type: `Point`) — `recorded_at` typed as `timestamp[us]`, `unit_count` typed as `int32`, schema matches Overture's address column set.

**Story.** Jamal Wright, an intern at NYC's Department of Health and Mental Hygiene, has been asked to convert a small Overture-style address sample from a CSV-with-WKT export into proper GeoParquet so the analytics team can consume it via DuckDB without re-typing every column. The CSV has the geometry in a `geometry_wkt` column, an ISO-formatted `recorded_at` string, and unit counts that the export tool quoted as text — he needs the output to type those columns correctly so SQL `WHERE recorded_at > '2024-01-01'` works without casts.

### Task: `fio-l2-cairo-mixedgeom-split`

| Field | Value |
|---|---|
| Category | format_io |
| Difficulty | L2 |
| Region | Cairo, Egypt |
| Data source | Bundled local file |
| Primary op | Geometry-type stratification + multi-layer GPKG write |
| Secondary ops | Explode (multi → single) |
| Format in | GeoJSON (mixed geometry types in a single FeatureCollection: points, lines, polygons, and multi-part variants intermingled) |
| Format out | GPKG (multi-layer: `points`, `lines`, `polygons`) |
| CRS in | EPSG:4326 |
| CRS out | EPSG:22992 (Egypt Red Belt) |
| Geometry type | Point, LineString, Polygon, MultiPolygon (mixed in source) |
| Data scale | Small (~10² features) |
| Data quality issues | Mixed geometry types, MultiPolygon / Polygon coercion |
| Overture themes | — |
| OSM tags | — |

**Output artifacts:**
- `heritage.gpkg` (format: `gpkg`, crs: `EPSG:22992`) — three layers `points`, `lines`, `polygons`; multi-part geometries exploded into singletons; the originating site ID preserved as a foreign key on every layer.

**Story.** Yusra Al-Sayed, a heritage analyst at Egypt's Ministry of Antiquities, has a hand-curated GeoJSON describing dozens of heritage sites: each site contributes its enclosure polygon, axial street lines, and significant point markers as separate features sharing a common `site_id`, and the file mixes Polygon and MultiPolygon variants in the same FeatureCollection. The downstream desktop tool only ingests typed GPKG layers in Egypt Red Belt; she needs the agent to sort the features into per-type layers, explode the multi-part polygons into singletons, and preserve the site ID linking everything together.

### Task: `fio-l2-capetown-landuse-dissolve`

| Field | Value |
|---|---|
| Category | format_io |
| Difficulty | L2 |
| Region | Cape Town, South Africa |
| Data source | Bundled local file |
| Primary op | Dissolve by attribute |
| Secondary ops | Collect (single → multi), format conversion (FlatGeobuf → GeoParquet) |
| Format in | FlatGeobuf |
| Format out | GeoParquet |
| CRS in | EPSG:32734 (WGS84 / UTM 34S) |
| CRS out | EPSG:32734 |
| Geometry type | Polygon → MultiPolygon |
| Data scale | Medium (~10⁴ parcels) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `landuse=*` |

**Output artifacts:**
- `landuse_dissolved.geoparquet` (format: `geoparquet`, crs: `EPSG:32734`, geometry_type: `MultiPolygon`) — one feature per `landuse` class with `area_m2` and `parcel_count` attributes.

**Story.** Sipho Dlamini, a transport-equity researcher at the University of Cape Town, has a parcel-level OSM `landuse=*` extract for the metropolitan area in FlatGeobuf and wants a tidy class-level summary for a transit-corridor study. He needs each landuse class collapsed into a single MultiPolygon with the total area and source-parcel count carried as attributes, exported as GeoParquet so the team's spatial-SQL notebooks can join it directly against the bus-route table.

### Task: `fio-l3-vienna-geofabrik-highways`

| Field | Value |
|---|---|
| Category | format_io |
| Difficulty | L3 |
| Region | Vienna, Austria |
| Data source | Geofabrik regional PBF (Austria extract) |
| Primary op | PBF read + tag-filtered export to GPKG |
| Secondary ops | Spatial join — intersects (highways that intersect the Vienna ring road buffer), public-transport relation extraction, attribute preservation |
| Format in | OSM PBF (`.osm.pbf`) |
| Format out | GPKG (multi-layer: `highways`, `pt_routes`) |
| CRS in | EPSG:4326 |
| CRS out | EPSG:31287 (MGI / Austria Lambert) |
| Geometry type | LineString, MultiLineString |
| Data scale | Medium (~10⁴ highway segments, ~10² PT route relations in Vienna) |
| Data quality issues | Encoding issues (German diacritics in `name` tags) |
| Overture themes | — |
| OSM tags | `highway=*`, public-transport route relations |

**Output artifacts:**
- `vienna_network.gpkg` (format: `gpkg`, crs: `EPSG:31287`) — `highways` layer (LineString) with full OSM `name`, `highway`, `maxspeed`, `lanes`, `surface`, `oneway` preserved untruncated; `pt_routes` layer (MultiLineString, one feature per route relation) with `ref`, `name`, `operator`, `route` tags.

**Story.** Ingrid Maier runs a small environmental consultancy commissioned by the City of Vienna to model traffic noise around the Gürtel ring road. She needs every Vienna `highway=*` segment that intersects a 500 m buffer of the ring road, plus every public-transport route relation passing through the same band — extracted from the latest Geofabrik Austria PBF and saved as a multi-layer GPKG in MGI Lambert, with full untruncated OSM tag names so her acoustician-collaborator can join speed and lane-count data without guessing column meanings.

---

## Category: crs_reprojection

### Task: `crs-l1-paris-lambert93`

| Field | Value |
|---|---|
| Category | crs_reprojection |
| Difficulty | L1 |
| Region | Paris, France |
| Data source | Bundled local file |
| Primary op | Reprojection |
| Secondary ops | — |
| Format in | GeoJSON |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:2154 (RGF93 / Lambert-93) |
| Geometry type | Polygon |
| Data scale | Small (~10² parcels) |
| Data quality issues | — |
| Overture themes | `buildings.building` |
| OSM tags | `building=*` |

**Output artifacts:**
- `paris_buildings_lambert93.geojson` (format: `geojson`, crs: `EPSG:2154`, geometry_type: `Polygon`) — coordinates rewritten in Lambert-93 metres, attributes unchanged.

**Story.** Camille Roux, an intern at IGN's cadastre service, is preparing a sample of Paris building footprints for a colleague's heat-loss model. The model expects coordinates in Lambert-93 metres and refuses anything in lat/lon. She has a small bundled GeoJSON in WGS84 and needs an equivalent file in EPSG:2154 with attributes preserved verbatim, ready for the model's expected file naming.

### Task: `crs-l1-nyc-webmercator-cycleways`

| Field | Value |
|---|---|
| Category | crs_reprojection |
| Difficulty | L1 |
| Region | New York City, USA |
| Data source | Bundled local file (Overture-format `transportation.segment` sample) |
| Primary op | Reprojection |
| Secondary ops | — |
| Format in | GeoParquet |
| Format out | GeoParquet |
| CRS in | EPSG:3857 (Web Mercator) |
| CRS out | EPSG:4326 |
| Geometry type | LineString |
| Data scale | Small (~10² cycleway segments) |
| Data quality issues | — |
| Overture themes | `transportation.segment` |
| OSM tags | `highway=cycleway` |

**Output artifacts:**
- `nyc_cycleways_wgs84.geoparquet` (format: `geoparquet`, crs: `EPSG:4326`, geometry_type: `LineString`) — coordinates reprojected from spherical-Mercator metres to WGS84 lat/lon.

**Story.** Marcus Chen, an analyst at NYC DOT's bike-program office, was handed an Overture-style cycleway extract whose geometries are in Web Mercator because the upstream tool defaults to 3857 for tile rendering. He needs the same data in WGS84 so his Streamlit dashboard's Leaflet layer can ingest it directly without a client-side transform that's been quietly mangling segments at the borough boundaries.

### Task: `crs-l1-london-laea-areas`

| Field | Value |
|---|---|
| Category | crs_reprojection |
| Difficulty | L1 |
| Region | London, United Kingdom |
| Data source | Bundled local file |
| Primary op | Area calculation (unprompted CRS reasoning) |
| Secondary ops | — |
| Format in | GeoJSON |
| Format out | CSV |
| CRS in | EPSG:4326 |
| CRS out | n/a (CSV output; model must independently choose a projected CRS for area computation) |
| Geometry type | MultiPolygon |
| Data scale | Small (~10² London boroughs and surrounding admin areas) |
| Data quality issues | — |
| Overture themes | `divisions.division` |
| OSM tags | `boundary=administrative` |

**Output artifacts:**
- `borough_areas.csv` (format: `csv`) — `id, name, area_km2`.

**Story.** Sophia Marchetti, a UK-based researcher at UCL's EU climate-policy unit, is preparing a comparative land-area table across European boroughs for a Horizon report. She has a WGS84 GeoJSON of London-area administrative units and needs a CSV listing each feature's area in square kilometres. The instruction deliberately omits any CRS guidance — the agent must independently recognise that computing area on geographic coordinates is meaningless and choose an appropriate projection.

### Task: `crs-l2-svalbard-polar-areas`

| Field | Value |
|---|---|
| Category | crs_reprojection |
| Difficulty | L2 |
| Region | Svalbard, Norway |
| Data source | Bundled local file |
| Primary op | Reprojection (WGS84 → polar stereographic) |
| Secondary ops | Bounding box, area calculation, top-N rank |
| Format in | GPKG |
| Format out | CSV |
| CRS in | EPSG:4326 |
| CRS out | EPSG:3995 (WGS 84 / Arctic Polar Stereographic) |
| Geometry type | Polygon |
| Data scale | Small (~10² glacier polygons) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `natural=glacier` (`natural=*`) |

**Output artifacts:**
- `svalbard_glaciers_top20.csv` (format: `csv`) — top 20 glaciers ranked by polar-stereographic area: `name, area_km2, bbox_minx_polar, bbox_miny_polar, bbox_maxx_polar, bbox_maxy_polar`.

**Story.** Astrid Hansen, a glaciologist at the Norwegian Polar Institute, is updating her year-end glacier-retreat figure for the institute's outreach blog. The bundled OSM-derived glacier polygons for Svalbard are in WGS84 — useless for area-honest ranking at 78°N because cylindrical projections explode at high latitudes. She needs the polygons reprojected to the Arctic Polar Stereographic CRS, the area of each computed honestly, and the top 20 returned as CSV with their polar-stereographic bounding boxes for the blog's accompanying static map.

### Task: `crs-l2-fiji-antimeridian`

| Field | Value |
|---|---|
| Category | crs_reprojection |
| Difficulty | L2 |
| Region | Fiji |
| Data source | Bundled local file |
| Primary op | Antimeridian-safe reprojection + length calculation |
| Secondary ops | Antimeridian splitting, MultiLineString assembly |
| Format in | GeoJSON (some LineStrings declared with longitudes spanning across ±180°, in violation of RFC 7946 §3.1.9) |
| Format out | GeoJSON |
| CRS in | EPSG:4326 (with antimeridian-crossing geometries) |
| CRS out | EPSG:3460 (Fiji 1986 / Fiji Map Grid) |
| Geometry type | LineString, MultiLineString |
| Data scale | Small (~10² transects) |
| Data quality issues | — (antimeridian crossings are an Axis 4 variant, not an Axis 6 quality issue) |
| Overture themes | — |
| OSM tags | — |

**Output artifacts:**
- `fiji_transects_fmg.geojson` (format: `geojson`, crs: `EPSG:3460`, geometry_type: `MultiLineString`) — transects split at the antimeridian when expressed in WGS84 and re-assembled as MultiLineString in Fiji Map Grid, with `length_m` attribute computed in the projected CRS.

**Story.** Mereani Tuilagi, a marine biologist at the University of the South Pacific, has GPS transects from a reef survey that several boats logged across the ±180° meridian. Her colleagues' tooling drew impossibly long lines around the globe whenever a transect crossed the date line. She needs the antimeridian-crossing LineStrings split correctly, reprojected to Fiji Map Grid (EPSG:3460), and reassembled as MultiLineStrings with honest length-in-metres so the bottom-trawl-impact paper can cite per-transect coverage figures that survive peer review.

### Task: `crs-l3-tokyo-jgd-crossings`

| Field | Value |
|---|---|
| Category | crs_reprojection |
| Difficulty | L3 |
| Region | Tokyo, Japan |
| Data source | OSM via Overpass API — current |
| Primary op | Conformal reprojection round-trip (WGS84 → JGD2011 Plane IX → WGS84) |
| Secondary ops | Spatial join — crosses (highways crossing ward boundaries), Buffer (planar, in JGD metres), Intersection |
| Format in | OSM Overpass JSON / XML response (highway network + administrative ward polygons) |
| Format out | GPKG (multi-layer mixing JGD2011 Plane IX and WGS84) |
| CRS in | EPSG:4326 |
| CRS out | EPSG:6677 (JGD2011 / Japan Plane Rectangular IX) for engineering layers; EPSG:4326 for the public-facing summary layer |
| Geometry type | LineString + Polygon → Point (crossings), Polygon (buffer ∩ ward) |
| Data scale | Medium (~10⁵ highway segments, 23 wards in Tokyo Metropolis) |
| Data quality issues | Null / missing attributes (some `name`, `lanes`, `surface` tags absent on segments) |
| Overture themes | — |
| OSM tags | `highway=*`, `boundary=administrative` |

**Output artifacts:**
- `tokyo_crossings.gpkg` (format: `gpkg`) — five layers: `wards_jgd` (Polygon, EPSG:6677), `crossing_points` (Point, EPSG:6677, where a `highway=*` LineString crosses a `boundary=administrative` polygon edge), `crossing_buffers_50m` (Polygon, EPSG:6677, 50 m planar buffer around each crossing point in JGD metres), `buffer_ward_intersection` (Polygon, EPSG:6677, intersection of each buffer with the ward polygon containing it), and `ward_crossing_density_wgs84` (Polygon, EPSG:4326, reprojected back to WGS84) carrying a `crossings_per_km2` attribute for the public dashboard.

**Story.** Yuki Nakamura, an urban-mobility analyst at the Tokyo Metropolitan Government, is rebuilding the road-safety dashboard for Tokyo's 23 special wards. For each ward she needs to know how often the highway network crosses the ward boundary, with a 50 m operational buffer around each crossing for jurisdictional reporting — and the work has to happen in JGD2011 Plane IX, the conformal national grid covering Tokyo, for honest distance-in-metres. But the public-facing dashboard ingests only WGS84, so the final per-ward density layer must be reprojected back. The agent must fetch Tokyo's `highway=*` and `boundary=administrative` from live Overpass, reproject to plane IX, identify crossing points, build planar buffers, intersect with wards, compute density, and emit a multi-layer GPKG that combines the engineering layers in JGD with the dashboard layer in WGS84.

---

## Category: geometric_ops

### Task: `geo-l1-tokyo-busstop-buffer`

| Field | Value |
|---|---|
| Category | geometric_ops |
| Difficulty | L1 |
| Region | Tokyo, Japan |
| Data source | Bundled local file (Overture-format `transportation.connector` sample) |
| Primary op | Buffer (planar) — unprompted CRS reasoning |
| Secondary ops | — |
| Format in | GeoJSON |
| Format out | GeoParquet |
| CRS in | EPSG:4326 |
| CRS out | n/a (model must independently choose a projected CRS for metric buffering) |
| Geometry type | Point → Polygon |
| Data scale | Small (~10² connectors) |
| Data quality issues | — |
| Overture themes | `transportation.connector` |
| OSM tags | `railway=station` (`railway=*`) |

**Output artifacts:**
- `tokyo_stop_catchments.geoparquet` (format: `geoparquet`, geometry_type: `Polygon`) — 400 m planar buffer around each connector point, attributes preserved.

**Story.** Hiroshi Sato, a service planner at Tokyo Metro Co., is updating the 400 m walkable-catchment layer for stations and bus connectors after a timetable revision. He has a WGS84 GeoJSON of connectors and needs a 400 m buffer around each, exported as GeoParquet. The instruction deliberately omits any CRS guidance — the agent must independently recognise that buffering in WGS84 produces degree-radius polygons and choose an appropriate projected CRS.

### Task: `geo-l1-capetown-building-centroids`

| Field | Value |
|---|---|
| Category | geometric_ops |
| Difficulty | L1 |
| Region | Cape Town, South Africa |
| Data source | Bundled local file |
| Primary op | Centroid |
| Secondary ops | — |
| Format in | Shapefile |
| Format out | GeoJSON |
| CRS in | EPSG:32734 (WGS84 / UTM 34S) |
| CRS out | EPSG:4326 |
| Geometry type | Polygon → Point |
| Data scale | Small (~10² buildings) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `building=*` |

**Output artifacts:**
- `building_centroids.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `Point`) — one Point per input Polygon, original `building_id` preserved.

**Story.** Thandi Nkosi, GIS lead on Cape Town's addressing-improvement project, is preparing a centroid-only layer of the latest building footprints so that the addressing team's lightweight web tool — which only renders points — can plot the city's housing stock. She needs a centroid for every building, exported as WGS84 GeoJSON with the original building ID preserved as the join key.

### Task: `geo-l1-cairo-multipoint-hull`

| Field | Value |
|---|---|
| Category | geometric_ops |
| Difficulty | L1 |
| Region | Cairo, Egypt |
| Data source | Bundled local file |
| Primary op | Convex hull |
| Secondary ops | — |
| Format in | GeoJSON |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | MultiPoint → Polygon |
| Data scale | Small (~10² stations, each station a MultiPoint of platform exits) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `railway=subway_entrance` (`railway=*`) |

**Output artifacts:**
- `cairo_metro_hulls.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `Polygon`) — one convex hull per station's MultiPoint of entrances; `station_name_ar` and `station_name_en` preserved.

**Story.** Hatem Ibrahim, a service-area analyst at the Cairo Metro Authority, has a station inventory in which each station is a MultiPoint geometry listing all its street-level entrance coordinates. For an upcoming accessibility report, he wants the convex hull of each station's entrances (a coarse "footprint" of the station box) so the report's static maps can show how widely each station extends underground, with the bilingual Arabic / English station names preserved.

### Task: `geo-l2-bangkok-landuse-intersect`

| Field | Value |
|---|---|
| Category | geometric_ops |
| Difficulty | L2 |
| Region | Bangkok, Thailand |
| Data source | Bundled local file (Overture-format `base.land_cover` sample) |
| Primary op | Intersection (between land-cover and a study-area polygon) |
| Secondary ops | Simplify, MakeValid (repair invalid input polygons) |
| Format in | GeoParquet |
| Format out | GeoJSON |
| CRS in | EPSG:32647 (WGS84 / UTM 47N) |
| CRS out | EPSG:32647 |
| Geometry type | Polygon → MultiPolygon |
| Data scale | Medium (~10⁴ land-cover polygons) |
| Data quality issues | Invalid geometries (self-intersecting rings in some land-cover features) |
| Overture themes | `base.land_cover` |
| OSM tags | — |

**Output artifacts:**
- `bma_landcover_intersect.geojson` (format: `geojson`, crs: `EPSG:32647`, geometry_type: `MultiPolygon`) — geometric intersection of each land-cover polygon with the BMA study-area polygon, simplified at 5 m tolerance, with `class` and `area_m2` attributes.

**Story.** Praphan Wongsa, a planner at the Bangkok Metropolitan Administration, is preparing a green-cover briefing for a flood-mitigation working group. He has an Overture-style `base.land_cover` sample in UTM 47N and a single study-area polygon for the BMA boundary. Several input polygons have self-intersecting rings that crash his GIS desktop tool. He needs the agent to repair invalid geometries first, intersect the cleaned land-cover with the study-area polygon, simplify at a 5 m tolerance, and export GeoJSON with per-class areas — small enough that the policy lead can preview it in a browser.

### Task: `geo-l2-nyc-park-symdiff`

| Field | Value |
|---|---|
| Category | geometric_ops |
| Difficulty | L2 |
| Region | New York City, USA |
| Data source | Bundled local file (Overture-format `base.infrastructure` sample) |
| Primary op | Symmetric difference (NYC Parks layer XOR an OSM-derived parks layer) |
| Secondary ops | Collect (single → multi), Point-on-surface |
| Format in | GPKG (two layers: `parks_official`, `parks_osm`) |
| Format out | GeoJSON |
| CRS in | EPSG:6539 (NAD83(2011) / New York State Plane Long Island) |
| CRS out | EPSG:6539 |
| Geometry type | Polygon → MultiPolygon, Point |
| Data scale | Medium (~10³ park polygons per source) |
| Data quality issues | — |
| Overture themes | `base.infrastructure` |
| OSM tags | — |

**Output artifacts:**
- `parks_disagreement.geojson` (format: `geojson`, crs: `EPSG:6539`, geometry_type: `MultiPolygon`) — symmetric difference between the two source layers, collected into one MultiPolygon per discrepancy cluster, with a `source` attribute indicating which side claimed it.
- `park_label_anchors.geojson` (format: `geojson`, crs: `EPSG:6539`, geometry_type: `Point`) — one point-on-surface per discrepancy cluster, suitable for placing labels.

**Story.** Rachel Goldberg, a landscape architect at NYC Parks, is reconciling the official NYC Parks polygon layer against an OSM-derived parks export from the open-data portal because both feed the city's "find a park" map and they disagree in dozens of places. She needs the symmetric difference between the two sources — every patch claimed by one but not the other — collected into discrepancy clusters with point-on-surface label anchors, both layers in NY State Plane (Long Island) so the cartographer can drop them straight into the Parks Department's print-ready template.

### Task: `geo-l3-antarctica-stations-geodesic`

| Field | Value |
|---|---|
| Category | geometric_ops |
| Difficulty | L3 |
| Region | Antarctica |
| Data source | Overture Maps current release |
| Primary op | Buffer (geodesic, large-extent — 200 km radius) |
| Secondary ops | Clip (to landmass), Cascaded union (overlapping station spheres) |
| Format in | GeoParquet (Overture `places.place` for stations, `base.land`, `base.water`, `base.bathymetry`) |
| Format out | GeoParquet |
| CRS in | EPSG:4326 |
| CRS out | EPSG:3031 (WGS 84 / Antarctic Polar Stereographic) |
| Geometry type | Point → Polygon, MultiPolygon |
| Data scale | Medium (handful of stations, ~10⁴ Antarctic land + water + bathymetry polygons) |
| Data quality issues | — |
| Overture themes | `base.land`, `base.water`, `base.bathymetry`, `places.place` |
| OSM tags | — |

**Output artifacts:**
- `station_spheres.geoparquet` (format: `geoparquet`, crs: `EPSG:3031`, geometry_type: `MultiPolygon`) — 200 km geodesic buffer around each Antarctic research station, clipped to the landmass, with overlapping spheres unioned into a `coalition` cluster id.
- `station_water_overlap.geoparquet` (format: `geoparquet`, crs: `EPSG:3031`, geometry_type: `MultiPolygon`) — the over-water portion of each station's sphere, attributed with the `base.water` and `base.bathymetry` features it intersects.

**Story.** Dr. Ellis Whitford, environmental compliance officer at the British Antarctic Survey, is preparing the cross-station logistics-overlap submission for the Antarctic Treaty Consultative Meeting. Each station has a notional 200 km operational sphere; at high southern latitudes that radius cannot be honestly drawn with planar buffering — it must be geodesic and then projected to EPSG:3031. The agent must fetch Overture station points and the base land / water / bathymetry layers, draw the geodesic buffers, clip them to the landmass, identify overlapping coalitions, and separately catalogue the over-water portion against the bathymetric layer for the treaty's marine-impact section.

---

## Category: spatial_analysis

### Task: `spa-l1-vienna-pip-count`

| Field | Value |
|---|---|
| Category | spatial_analysis |
| Difficulty | L1 |
| Region | Vienna, Austria |
| Data source | Bundled local file |
| Primary op | Point-in-polygon count |
| Secondary ops | — |
| Format in | GeoJSON (two files: monitoring stations, district polygons) |
| Format out | CSV |
| CRS in | EPSG:31287 (MGI / Austria Lambert) |
| CRS out | n/a (tabular output) |
| Geometry type | Point + Polygon |
| Data scale | Small (~10² stations, 23 districts) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `place=*` (district markers carry place tags), `boundary=administrative` |

**Output artifacts:**
- `stations_per_district.csv` (format: `csv`) — `district_code, district_name, station_count`, sorted by `district_code`.

**Story.** Ana Brković, an analyst at Austria's Umweltbundesamt (federal environment agency), needs a coverage diagnostic ahead of next year's air-quality budget round. The bundled point layer of monitoring stations and the polygon layer of Vienna's 23 districts are both in MGI Lambert. She wants a simple CSV listing each district's station count so the funding committee can see at a glance which districts are under-monitored relative to their population.

### Task: `spa-l1-capetown-hospital-nn`

| Field | Value |
|---|---|
| Category | spatial_analysis |
| Difficulty | L1 |
| Region | Cape Town, South Africa |
| Data source | Bundled local file |
| Primary op | Nearest neighbour — unprompted CRS reasoning |
| Secondary ops | — |
| Format in | GeoParquet (two files: residential addresses, hospital points) |
| Format out | GPKG |
| CRS in | EPSG:4326 |
| CRS out | n/a (model must independently choose a projected CRS for metric distance) |
| Geometry type | Point |
| Data scale | Small (~10² addresses, ~10 hospitals) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `amenity=hospital` (`amenity=*`) |

**Output artifacts:**
- `nearest_hospital.gpkg` (format: `gpkg`, geometry_type: `Point`) — one feature per address with `nearest_hospital_name` and `distance_m` attributes.

**Story.** Dr. Bongani Mthembu plans EMS coverage for the Western Cape provincial health department. He has WGS84 GeoParquet files of residential pickup addresses and hospitals, and wants each address tagged with its nearest hospital's name and the straight-line distance in metres. The instruction deliberately omits any CRS guidance — the agent must independently recognise that WGS84 distances are in degrees and choose an appropriate projected CRS for metric computation.

### Task: `spa-l1-paris-amenity-within`

| Field | Value |
|---|---|
| Category | spatial_analysis |
| Difficulty | L1 |
| Region | Paris, France |
| Data source | Bundled local file |
| Primary op | Spatial join — within |
| Secondary ops | — |
| Format in | GPKG (two layers: `amenities`, `arrondissements`) |
| Format out | CSV |
| CRS in | EPSG:2154 (RGF93 / Lambert-93) |
| CRS out | n/a (tabular output) |
| Geometry type | Point + Polygon |
| Data scale | Small (~10² amenities, 20 arrondissements) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `amenity=*` |

**Output artifacts:**
- `amenity_to_arrondissement.csv` (format: `csv`) — `osm_id, amenity_class, arrondissement_number, arrondissement_name`.

**Story.** Émilie Dubois on INSEE's municipal census team is tagging an amenity point dataset with the arrondissement each amenity falls within for a Parisian neighbourhood demographic crosswalk. She has both layers in Lambert-93 and needs a flat CSV with the OSM id, amenity class, and the arrondissement number and name — straightforward `within` join, no shenanigans, but the deliverable must list the 20th arrondissement as `20` not `20e` for the downstream join.

### Task: `spa-l2-cairo-shop-knn`

| Field | Value |
|---|---|
| Category | spatial_analysis |
| Difficulty | L2 |
| Region | Cairo, Egypt |
| Data source | Bundled local file |
| Primary op | k-nearest neighbours (k = 5) |
| Secondary ops | Within-distance filter (1 km), Distance matrix (full m × n for a small subset) |
| Format in | GPKG |
| Format out | JSON |
| CRS in | EPSG:22992 (Egypt Red Belt) |
| CRS out | n/a |
| Geometry type | Point |
| Data scale | Medium (~10⁴ shops, ~10² market anchors) |
| Data quality issues | Inconsistent attribute values (variant Arabic / Latin transliterations of the same chain name) |
| Overture themes | — |
| OSM tags | `shop=*` |

**Output artifacts:**
- `market_neighbourhoods.json` (format: `json`) — for each market anchor: `{anchor_id, anchor_name_normalised, knn: [{shop_id, normalised_name, distance_m, within_1km}], full_distance_matrix_m: [...]}`. The `normalised_name` field collapses transliteration variants into a canonical form per chain.

**Story.** Mona Saleh runs a retail-density consultancy advising landlords near downtown Cairo. She has a ~10 000-shop OSM extract and 100 anchor points (her client's target market locations); for each anchor she needs the five nearest shops, a 1 km within-distance flag, and a small full distance matrix to the anchor's three closest siblings, returned as JSON. Several shop chains appear under multiple Arabic / Latin transliterations — the deliverable must canonicalise those before grouping so the chain density figures aren't fragmented.

### Task: `spa-l2-lagos-hotspot-overlaps`

| Field | Value |
|---|---|
| Category | spatial_analysis |
| Difficulty | L2 |
| Region | Lagos, Nigeria |
| Data source | Bundled local file (Overture-format `base.land_use` sample) |
| Primary op | Hot-spot ranking (Getis-Ord-style cell ranking by density) |
| Secondary ops | Spatial join — overlaps (between adjacent land-use polygons), Spatial aggregation (area-weighted mean of population density across overlapping cells) |
| Format in | GeoJSON |
| Format out | GeoParquet, plain Parquet |
| CRS in | EPSG:4326 |
| CRS out | EPSG:26331 (Minna / Nigeria West Belt) |
| Geometry type | Polygon |
| Data scale | Medium (~10⁴ land-use polygons, plus a 1 km hex grid over greater Lagos) |
| Data quality issues | Sliver polygons (overlay artefacts where adjacent land-use polygons fail to align) |
| Overture themes | `base.land_use` |
| OSM tags | — |

**Output artifacts:**
- `hotspots.geoparquet` (format: `geoparquet`, crs: `EPSG:26331`, geometry_type: `Polygon`) — top 10 % hex cells ranked by area-weighted population density across overlapping land-use polygons.
- `hotspot_ranking.parquet` (format: `parquet`) — tabular: `hex_id, rank, area_weighted_density, n_overlap_polygons, n_slivers_filtered`.

**Story.** Adeola Bankole, a partner at a Lagos urban-density consultancy, is preparing a hot-spot map for a state-level housing-policy review. She has a `base.land_use` sample with population-density attributes and a 1 km hex grid; the land-use polygons overlap each other due to imperfect alignment between source layers, producing thousands of sliver polygons under 100 m² that distort area-weighted aggregations. The agent must filter those slivers, compute area-weighted mean density per hex via overlap-aware aggregation, rank the top 10 % cells, and emit both a GeoParquet of the hot-spot polygons and a plain-Parquet ranking table for the consultancy's tabular dashboard.

### Task: `spa-l3-paris-emergency-routing`

| Field | Value |
|---|---|
| Category | spatial_analysis |
| Difficulty | L3 |
| Region | Paris, France |
| Data source | OSM via Overpass API — current |
| Primary op | Closest facility (by network distance) |
| Secondary ops | Shortest path, Network distance matrix, Isochrone (15-minute drive-time) |
| Format in | OSM Overpass JSON / XML response (highway network + hospital amenities) |
| Format out | GPKG |
| CRS in | EPSG:4326 |
| CRS out | EPSG:2154 (RGF93 / Lambert-93) |
| Geometry type | LineString + Point → MultiPolygon (isochrones) |
| Data scale | Medium (~10⁵ highway segments and ~10² hospitals across Paris and the inner ring) |
| Data quality issues | — |
| Overture themes | — |
| OSM tags | `highway=*`, `amenity=hospital` (`amenity=*`) |

**Output artifacts:**
- `emergency_routing.gpkg` (format: `gpkg`, crs: `EPSG:2154`) — four layers: `incidents` (Point, sample emergency call points), `closest_hospital` (LineString, the shortest-path geometry from each incident to its closest hospital), `distance_matrix` (tabular, full m × n network distances between every incident and a small set of candidate hospitals), `isochrones_15min` (MultiPolygon, 15-minute drive-time isochrone around each hospital).

**Story.** Captain Julien Moreau, an emergency-response analyst at SAMU's Paris coordination centre, is rebuilding the dispatch model after a redistricting. He has a sample of historical emergency-call points; for each call he needs the closest hospital by network distance with the shortest-path geometry exported, plus a small full distance matrix between every call and its three closest candidate hospitals, plus a 15-minute isochrone around each hospital so management can see coverage gaps. The agent must fetch Paris's `highway=*` network and `amenity=hospital` points from live Overpass, build the routing graph, and ship a single multi-layer GPKG in Lambert-93 ready for the SAMU GIS team's next briefing.

---

## Category: data_cleaning

### Task: `dc-l1-tokyo-ring-orientation`

| Field | Value |
|---|---|
| Category | data_cleaning |
| Difficulty | L1 |
| Region | Tokyo, Japan |
| Data source | Bundled local file |
| Primary op | Ring-orientation repair (RFC 7946) |
| Secondary ops | — |
| Format in | GeoJSON (exterior rings encoded clockwise, interior rings CCW — opposite of RFC 7946) |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | Polygon |
| Data scale | Small (~10² building footprints) |
| Data quality issues | Wrong ring orientation |
| Overture themes | — |
| OSM tags | `building=*` |

**Output artifacts:**
- `tokyo_buildings_rfc7946.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `Polygon`) — exterior rings counter-clockwise, interior rings clockwise, attributes preserved.

**Story.** Kenji Yamamoto, a volunteer at the OpenStreetMap Japan community, has a small bundled GeoJSON of Tokyo building footprints exported by an old in-house tool that wrote rings in OGC orientation rather than RFC 7946 orientation. Modern web viewers shade the building interiors as the "outside" because of it. He needs the same file rewritten with rings reordered to comply with RFC 7946 §3.1.6 (exterior CCW, interior CW), attributes untouched, so the import script for the community tile server stops complaining about polygon winding.

### Task: `dc-l1-capetown-waterway-nulls`

| Field | Value |
|---|---|
| Category | data_cleaning |
| Difficulty | L1 |
| Region | Cape Town, South Africa |
| Data source | Bundled local file |
| Primary op | Drop empty / null geometries and rows with null required attributes |
| Secondary ops | — |
| Format in | GeoJSON (some features have `null` geometry, some have empty `LineString` `coordinates`, several have `null` in the `name` and `waterway_type` columns) |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | LineString |
| Data scale | Small (~10² waterways) |
| Data quality issues | Empty / null geometry, Null / missing attributes |
| Overture themes | — |
| OSM tags | `waterway=*` |

**Output artifacts:**
- `waterways_clean.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `LineString`) — only features with non-null, non-empty geometry and a non-null `waterway_type`; a `dropped_count` summary attribute on the FeatureCollection.

**Story.** Liam Visser, a junior on Cape Town's stormwater-management team, has been handed a contractor-supplied bundle of waterway centrelines containing dozens of features with null or empty geometries (artefacts of a buggy export) and another batch with null `waterway_type`, which his downstream model treats as "unknown" and silently drops anyway. He needs a cleaned GeoJSON with those rows removed plus a record of how many were dropped, so he can flag the contractor without redoing the analysis from scratch.

### Task: `dc-l1-bangkok-attribute-coercion`

| Field | Value |
|---|---|
| Category | data_cleaning |
| Difficulty | L1 |
| Region | Bangkok, Thailand |
| Data source | Bundled local file |
| Primary op | Attribute type coercion (numeric-as-string → float / int) |
| Secondary ops | — |
| Format in | GeoJSON (all numeric attributes serialised as JSON strings, e.g. `"sensor_value": "42.7"`) |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | Point |
| Data scale | Small (~10² stations) |
| Data quality issues | Attribute type coercion (numeric-as-string) |
| Overture themes | — |
| OSM tags | `railway=station` (`railway=*`) — air-quality sensors are mounted on Bangkok rail stations |
**Output artifacts:**
- `bangkok_aq_typed.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `Point`) — `sensor_value`, `pm25_ug_m3`, and `elevation_m` typed as numbers (float); `station_id` typed as integer; Thai `name_th` strings unchanged.

**Story.** Suda Pongpan runs the Bangkok Metropolitan Administration's air-quality monitoring programme. The vendor exports station readings as GeoJSON with every numeric column stringified — even the sensor IDs — which breaks the analytics team's dashboards that compute averages by `parseFloat`-ing client-side and silently drop NaNs. She needs a cleaned GeoJSON with the numeric columns properly typed and the Thai-script station names preserved, so the dashboard's averages match the figures the city director quotes in press briefings.

### Task: `dc-l2-cairo-invalid-dedup`

| Field | Value |
|---|---|
| Category | data_cleaning |
| Difficulty | L2 |
| Region | Cairo, Egypt |
| Data source | Bundled local file |
| Primary op | Make-valid + deduplicate + Polygon ↔ MultiPolygon coercion |
| Secondary ops | Dissolve, Sliver removal |
| Format in | GeoJSON (mix of `Polygon` and `MultiPolygon`, several invalid self-intersections, exact duplicate geometries with conflicting attributes, sliver polygons under 1 m²) |
| Format out | GeoParquet |
| CRS in | EPSG:22992 (Egypt Red Belt) |
| CRS out | EPSG:22992 |
| Geometry type | Polygon, MultiPolygon |
| Data scale | Medium (~10⁴ parcels) |
| Data quality issues | Invalid geometries, Duplicate geometries, MultiPolygon / Polygon coercion, Sliver polygons |
| Overture themes | — |
| OSM tags | — |

**Output artifacts:**
- `parcels_canonical.geoparquet` (format: `geoparquet`, crs: `EPSG:22992`, geometry_type: `MultiPolygon`) — all geometries valid, single-part Polygons promoted to MultiPolygon for schema consistency, slivers under 1 m² removed, exact duplicates collapsed into one feature with attribute-merge rules: `parcel_id` from earliest record, `area_m2` recomputed.

**Story.** Reem Farouk, a data steward at Egypt's Land Registry Authority, has inherited a parcel snapshot pulled from three legacy provincial systems before the registry's recent unification. The bundle is in Egypt Red Belt; geometry types mix Polygon and MultiPolygon, several rings self-intersect (the upstream tool didn't enforce simple-feature validity), some parcels appear twice with conflicting metadata, and the join produced sliver polygons under 1 m² along administrative seams. She needs a single canonical GeoParquet with everything valid, schema-consistent, deduped, and slivers removed — the foundation for the registry's new central repository.

### Task: `dc-l2-lagos-snap-normalize`

| Field | Value |
|---|---|
| Category | data_cleaning |
| Difficulty | L2 |
| Region | Lagos, Nigeria |
| Data source | Bundled local file |
| Primary op | Vertex snapping + zero-area polygon removal + attribute value normalisation |
| Secondary ops | Spatial aggregation with attribute work (filter, value normalisation, type coercion) |
| Format in | GPKG |
| Format out | GPKG |
| CRS in | EPSG:26331 (Minna / Nigeria West Belt) |
| CRS out | EPSG:26331 |
| Geometry type | Polygon |
| Data scale | Medium (~10⁴ zoning polygons) |
| Data quality issues | Unsnapped near-coincident vertices (sub-mm offsets that break dissolves), Zero-area polygons (collinear / coincident vertices), Inconsistent attribute values (variant spellings of zoning class: `RESIDENTIAL` / `Residential` / `residential` / `Resi.`) |
| Overture themes | — |
| OSM tags | — |

**Output artifacts:**
- `zoning_aggregated.gpkg` (format: `gpkg`, crs: `EPSG:26331`, geometry_type: `Polygon`) — vertices snapped at 1 mm tolerance, zero-area features removed, zoning class normalised to a controlled vocabulary (4 canonical classes), per-class total area computed by spatial aggregation that filters out zoned-as-blank rows, and a numeric `area_m2` recomputed in metres.

**Story.** Tunde Adeyemi leads a zoning-harmonisation pilot for Lagos State, merging zoning datasets from six LGAs that each used their own spelling conventions (`RESIDENTIAL`, `Residential`, `Resi.`, etc.) and whose contractor digitisation produced sub-millimetre vertex offsets between adjacent parcels. The dataset also contains zero-area "ghost" polygons that crash the dissolve. He needs the agent to snap vertices, drop zero-area features, normalise the zoning class to a four-value controlled vocabulary, filter out blank-class rows, and compute per-class total area — all delivered as GPKG that feeds straight into the state's new zoning portal.

### Task: `dc-l3-vienna-overpass-historical`

| Field | Value |
|---|---|
| Category | data_cleaning |
| Difficulty | L3 |
| Region | Vienna, Austria |
| Data source | OSM via Overpass API — historical (`[date:2014-01-01T00:00:00Z]`) compared against current |
| Primary op | Difference + Symmetric difference (boundary changes since 2014) |
| Secondary ops | Cascaded union (combining adjacent districts whose boundaries shifted), Spatial join — touches (which districts touch any changed segment), attribute-value normalisation |
| Format in | OSM Overpass JSON / XML responses (current + historical at 2014-01-01) |
| Format out | GeoJSON |
| CRS in | EPSG:4326 |
| CRS out | EPSG:4326 |
| Geometry type | Polygon, MultiPolygon |
| Data scale | Medium (~10² administrative polygons across the comparison) |
| Data quality issues | Inconsistent attribute values (district names recased / re-spelled between 2014 and current — e.g. `Wien-Innere Stadt` vs `Innere Stadt`) |
| Overture themes | `divisions.division_boundary` |
| OSM tags | `boundary=administrative` |

**Output artifacts:**
- `vienna_boundary_changes.geojson` (format: `geojson`, crs: `EPSG:4326`, geometry_type: `MultiPolygon`) — `added_since_2014` (areas in current but not 2014), `removed_since_2014` (areas in 2014 but not current), and `unchanged` (cascaded union of intersecting parts) sub-collections; each feature carries normalised district name plus a `touches_changed` boolean indicating whether the district neighbours any changed segment.

**Story.** Dr. Magdalena Reiter, historian at the Austrian Statistical Office, is preparing a 10-year retrospective on Vienna's administrative geometry for the 2026 statistical yearbook. She needs the symmetric difference between Vienna's 2014 and current `boundary=administrative` polygons (cascaded-unioned across overlapping district fragments), pulled live from Overpass with a `[date:...]` directive against the 2014 snapshot. District names changed casing and spelling between the two snapshots, so the agent must normalise them before reporting; the deliverable is a single GeoJSON with added / removed / unchanged sub-collections and a `touches_changed` flag for adjacency reporting.

---

## Coverage matrix

Every variant on every axis is hit by ≥ 1 task. Tasks are referenced by their slug (without the `tasks/` prefix). Where a variant has multiple sub-flavors that the brief requires (e.g. Buffer with both planar and geodesic), the relevant sub-flavor is noted on the row.

### Axis 1 — Geometric operations (14 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| Buffer (planar) | 2 | `geo-l1-tokyo-busstop-buffer`, `crs-l3-tokyo-jgd-crossings` |
| Buffer (geodesic, large-extent) | 1 | `geo-l3-antarctica-stations-geodesic` |
| Intersection | 2 | `geo-l2-bangkok-landuse-intersect`, `crs-l3-tokyo-jgd-crossings` |
| Union (cascaded) | 2 | `geo-l3-antarctica-stations-geodesic`, `dc-l3-vienna-overpass-historical` |
| Difference | 1 | `dc-l3-vienna-overpass-historical` |
| Symmetric difference | 2 | `geo-l2-nyc-park-symdiff`, `dc-l3-vienna-overpass-historical` |
| Clip | 1 | `geo-l3-antarctica-stations-geodesic` |
| Simplify | 1 | `geo-l2-bangkok-landuse-intersect` |
| Dissolve | 2 | `fio-l2-capetown-landuse-dissolve`, `dc-l2-cairo-invalid-dedup` |
| Convex hull | 1 | `geo-l1-cairo-multipoint-hull` |
| Centroid | 1 | `geo-l1-capetown-building-centroids` |
| Point-on-surface | 1 | `geo-l2-nyc-park-symdiff` |
| Bounding box | 4 | `dd-l1-london-parks-count`, `dd-l1-capetown-clinics-bbox`, `crs-l2-svalbard-polar-areas`, `dd-l3-lagos-overture-buildings` |
| Explode (multi → single) | 1 | `fio-l2-cairo-mixedgeom-split` |
| Collect (single → multi) | 2 | `fio-l2-capetown-landuse-dissolve`, `geo-l2-nyc-park-symdiff` |

### Axis 2 — Spatial analysis (17 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| Spatial join — within | 1 | `spa-l1-paris-amenity-within` |
| Spatial join — intersects | 1 | `fio-l3-vienna-geofabrik-highways` |
| Spatial join — contains | 1 | `dd-l2-tokyo-overture-schools` |
| Spatial join — touches | 1 | `dc-l3-vienna-overpass-historical` |
| Spatial join — crosses | 1 | `crs-l3-tokyo-jgd-crossings` |
| Spatial join — overlaps | 1 | `spa-l2-lagos-hotspot-overlaps` |
| Nearest neighbour | 1 | `spa-l1-capetown-hospital-nn` |
| k-nearest neighbours | 1 | `spa-l2-cairo-shop-knn` |
| Distance matrix | 1 | `spa-l2-cairo-shop-knn` |
| Within-distance filter | 1 | `spa-l2-cairo-shop-knn` |
| Point-in-polygon count | 1 | `spa-l1-vienna-pip-count` |
| Spatial aggregation — attribute work (filter / normalisation / type coercion) | 1 | `dc-l2-lagos-snap-normalize` |
| Spatial aggregation — area-weighted mean over polygon overlaps | 1 | `spa-l2-lagos-hotspot-overlaps` |
| Hot-spot ranking | 1 | `spa-l2-lagos-hotspot-overlaps` |
| Shortest path | 1 | `spa-l3-paris-emergency-routing` |
| Network distance matrix | 1 | `spa-l3-paris-emergency-routing` |
| Isochrone | 1 | `spa-l3-paris-emergency-routing` |
| Closest facility (network distance) | 1 | `spa-l3-paris-emergency-routing` |

### Axis 3 — Format I/O (input, 7 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| GeoJSON | 12 | `fio-l1-paris-kml-pois` (out only), `fio-l2-cairo-mixedgeom-split`, `crs-l1-paris-lambert93`, `crs-l1-london-laea-areas`, `crs-l2-fiji-antimeridian`, `geo-l1-tokyo-busstop-buffer`, `geo-l1-cairo-multipoint-hull`, `spa-l1-vienna-pip-count`, `spa-l2-lagos-hotspot-overlaps`, `dc-l1-tokyo-ring-orientation`, `dc-l1-capetown-waterway-nulls`, `dc-l1-bangkok-attribute-coercion`, `dc-l2-cairo-invalid-dedup` |
| GeoParquet | 6 | `dd-l2-tokyo-overture-schools`, `crs-l1-nyc-webmercator-cycleways`, `geo-l2-bangkok-landuse-intersect`, `geo-l3-antarctica-stations-geodesic`, `dd-l3-lagos-overture-buildings`, `spa-l1-capetown-hospital-nn` |
| Shapefile | 2 | `fio-l1-vienna-shapefile-recovery`, `geo-l1-capetown-building-centroids` |
| GPKG | 7 | `dd-l1-vienna-gpkg-manifest`, `dd-l2-bangkok-multicrs-audit`, `crs-l2-svalbard-polar-areas`, `geo-l2-nyc-park-symdiff`, `spa-l1-paris-amenity-within`, `spa-l2-cairo-shop-knn`, `dc-l2-lagos-snap-normalize` |
| CSV with WKT | 2 | `dd-l1-capetown-clinics-bbox`, `fio-l1-nyc-csvwkt-addresses` |
| FlatGeobuf | 2 | `dd-l1-london-parks-count`, `fio-l2-capetown-landuse-dissolve` |
| KML / KMZ | 1 | `fio-l1-paris-kml-pois` |

(Live-fetched OSM PBF and Overpass JSON / XML are handled under Axis 5 rather than Axis 3.)

### Axis 3 — Format I/O (output, 6 variants)

| Variant | Hit count | Tasks (selected) |
|---|---|---|
| JSON | 4 | `dd-l1-vienna-gpkg-manifest`, `dd-l1-london-parks-count`, `dd-l1-capetown-clinics-bbox`, `spa-l2-cairo-shop-knn` |
| CSV | 5 | `dd-l2-bangkok-multicrs-audit`, `crs-l2-svalbard-polar-areas`, `crs-l1-london-laea-areas`, `spa-l1-vienna-pip-count`, `spa-l1-paris-amenity-within` |
| GeoJSON | 13 | most L1/L2 geometric and cleaning tasks (see per-task `output_artifacts`; `crs-l1-london-laea-areas` moved to CSV) |
| Parquet (plain, non-geo) | 2 | `dd-l3-lagos-overture-buildings`, `spa-l2-lagos-hotspot-overlaps` |
| GeoParquet | 7 | `dd-l3-lagos-overture-buildings`, `fio-l1-nyc-csvwkt-addresses`, `fio-l2-capetown-landuse-dissolve`, `crs-l1-nyc-webmercator-cycleways`, `geo-l1-tokyo-busstop-buffer`, `geo-l3-antarctica-stations-geodesic`, `spa-l2-lagos-hotspot-overlaps`, `dc-l2-cairo-invalid-dedup` |
| GPKG | 6 | `fio-l2-cairo-mixedgeom-split`, `fio-l3-vienna-geofabrik-highways`, `crs-l3-tokyo-jgd-crossings`, `geo-l2-nyc-park-symdiff` (label points), `spa-l1-capetown-hospital-nn`, `spa-l3-paris-emergency-routing`, `dc-l2-lagos-snap-normalize` |

### Axis 4 — CRS reprojection (6 variants)

Datum shift was dropped from the axis after author / supervisor discussion: validating sub-metre datum-grid pipelines (NTv2 / OSTN15) requires PROJ-version-pinned tolerance management that exceeds the bachelor-thesis maintenance budget. The remaining six CRS variants still cover the projection-family skill space.

| Variant | Hit count | Tasks |
|---|---|---|
| WGS84 (EPSG:4326) | many | most tasks read or write WGS84 at some stage |
| Web Mercator (EPSG:3857) | 1 | `crs-l1-nyc-webmercator-cycleways` |
| Conformal (UTM / Lambert) | 14 | `crs-l1-paris-lambert93` (Lambert-93), `fio-l1-vienna-shapefile-recovery` (MGI Lambert), `fio-l3-vienna-geofabrik-highways` (MGI Lambert), `geo-l1-tokyo-busstop-buffer` (unprompted — model must choose a projected CRS for metric buffering), `crs-l3-tokyo-jgd-crossings` (JGD2011 Plane IX), `spa-l1-capetown-hospital-nn` (unprompted — model must choose a projected CRS for metric distance), `fio-l2-capetown-landuse-dissolve` (UTM 34S), `spa-l2-cairo-shop-knn` (Egypt Red Belt), `spa-l3-paris-emergency-routing` (Lambert-93), `dd-l3-lagos-overture-buildings` (Nigeria West Belt), `geo-l2-nyc-park-symdiff` (NY State Plane Long Island), `spa-l2-lagos-hotspot-overlaps` (Nigeria West Belt), `dc-l2-cairo-invalid-dedup` (Egypt Red Belt), `dc-l2-lagos-snap-normalize` (Nigeria West Belt), `dd-l2-bangkok-multicrs-audit` (UTM 47N) |
| Equal-area (LAEA / Mollweide / Albers) | 1 | `crs-l1-london-laea-areas` (unprompted — model must choose an equal-area or appropriate projected CRS for area calculation; no output CRS specified) |
| Polar | 2 | `crs-l2-svalbard-polar-areas` (EPSG:3995), `geo-l3-antarctica-stations-geodesic` (EPSG:3031) |
| Antimeridian-crossing geometries | 1 | `crs-l2-fiji-antimeridian` |

### Axis 5 — Data discovery and fetching (5 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| Overture Maps current release | 2 | `dd-l3-lagos-overture-buildings`, `geo-l3-antarctica-stations-geodesic` |
| OSM Overpass — current | 2 | `crs-l3-tokyo-jgd-crossings`, `spa-l3-paris-emergency-routing` |
| OSM Overpass — historical (`[date:...]`) | 1 | `dc-l3-vienna-overpass-historical` |
| Geofabrik regional PBF | 1 | `fio-l3-vienna-geofabrik-highways` |
| Bundled local file (HTTP-served) | 30 | all L1 and L2 tasks (18 + 12 = 30) |

### Axis 6 — Data quality issues (15 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| Invalid geometries | 2 | `geo-l2-bangkok-landuse-intersect`, `dc-l2-cairo-invalid-dedup` |
| Wrong ring orientation | 1 | `dc-l1-tokyo-ring-orientation` |
| Empty / null geometry | 1 | `dc-l1-capetown-waterway-nulls` |
| Zero-area polygons | 1 | `dc-l2-lagos-snap-normalize` |
| MultiPolygon / Polygon coercion | 2 | `fio-l2-cairo-mixedgeom-split`, `dc-l2-cairo-invalid-dedup` |
| Mixed geometry types | 1 | `fio-l2-cairo-mixedgeom-split` |
| Sliver polygons | 2 | `dc-l2-cairo-invalid-dedup`, `spa-l2-lagos-hotspot-overlaps` |
| Duplicate geometries | 1 | `dc-l2-cairo-invalid-dedup` |
| Unsnapped near-coincident vertices | 1 | `dc-l2-lagos-snap-normalize` |
| Mixed CRSes in one source | 1 | `dd-l2-bangkok-multicrs-audit` |
| Encoding issues | 3 | `fio-l1-vienna-shapefile-recovery`, `dd-l2-bangkok-multicrs-audit`, `fio-l3-vienna-geofabrik-highways` |
| Null / missing attributes | 3 | `dc-l1-capetown-waterway-nulls`, `dd-l3-lagos-overture-buildings`, `crs-l3-tokyo-jgd-crossings` |
| Attribute type coercion | 2 | `fio-l1-nyc-csvwkt-addresses`, `dc-l1-bangkok-attribute-coercion` |
| Inconsistent attribute values | 3 | `spa-l2-cairo-shop-knn`, `dc-l2-lagos-snap-normalize`, `dc-l3-vienna-overpass-historical` |
| Shapefile column truncation | 1 | `fio-l1-vienna-shapefile-recovery` |

### Axis 7 — Geometry type (6 variants)

GeometryCollection was dropped from the axis after author / supervisor discussion: real-world tooling rarely emits RFC-7946 GeometryCollections (most emitters split them on write), and the underlying skill — decomposing a heterogeneous geometry bag — is already covered by the **Mixed geometry types** variant on Axis 6 (data-quality issues), which is realistic.

| Variant | Hit count | Tasks |
|---|---|---|
| Point | many | `dd-l1-capetown-clinics-bbox`, `dd-l2-tokyo-overture-schools`, `fio-l1-paris-kml-pois`, `fio-l1-nyc-csvwkt-addresses`, `geo-l1-tokyo-busstop-buffer`, `spa-l1-capetown-hospital-nn`, `spa-l1-paris-amenity-within`, `spa-l2-cairo-shop-knn`, `dc-l1-bangkok-attribute-coercion`, `geo-l2-nyc-park-symdiff` (label points), `spa-l3-paris-emergency-routing`, `crs-l3-tokyo-jgd-crossings` (crossing points) |
| LineString | many | `crs-l1-nyc-webmercator-cycleways`, `crs-l2-fiji-antimeridian`, `crs-l3-tokyo-jgd-crossings`, `fio-l3-vienna-geofabrik-highways`, `dc-l1-capetown-waterway-nulls`, `spa-l3-paris-emergency-routing` |
| Polygon | many | most cleaning, geometric, and analysis tasks |
| MultiPoint | 1 | `geo-l1-cairo-multipoint-hull` |
| MultiLineString | 2 | `crs-l2-fiji-antimeridian`, `fio-l3-vienna-geofabrik-highways` |
| MultiPolygon | 7 | `crs-l1-london-laea-areas`, `fio-l2-capetown-landuse-dissolve`, `geo-l2-bangkok-landuse-intersect`, `geo-l3-antarctica-stations-geodesic`, `dc-l2-cairo-invalid-dedup`, `dc-l3-vienna-overpass-historical`, `spa-l3-paris-emergency-routing` (isochrones) |

### Axis 8 — Overture themes (15 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| `places.place` | 2 | `dd-l2-tokyo-overture-schools`, `geo-l3-antarctica-stations-geodesic` |
| `buildings.building` | 2 | `dd-l3-lagos-overture-buildings`, `crs-l1-paris-lambert93` |
| `buildings.building_part` | 1 | `dd-l3-lagos-overture-buildings` |
| `transportation.segment` | 1 | `crs-l1-nyc-webmercator-cycleways` |
| `transportation.connector` | 1 | `geo-l1-tokyo-busstop-buffer` |
| `base.water` | 1 | `geo-l3-antarctica-stations-geodesic` |
| `base.land` | 1 | `geo-l3-antarctica-stations-geodesic` |
| `base.land_cover` | 1 | `geo-l2-bangkok-landuse-intersect` |
| `base.land_use` | 1 | `spa-l2-lagos-hotspot-overlaps` |
| `base.infrastructure` | 1 | `geo-l2-nyc-park-symdiff` |
| `base.bathymetry` | 1 | `geo-l3-antarctica-stations-geodesic` |
| `addresses.address` | 1 | `fio-l1-nyc-csvwkt-addresses` |
| `divisions.division` | 1 | `crs-l1-london-laea-areas` |
| `divisions.division_area` | 1 | `dd-l1-vienna-gpkg-manifest` |
| `divisions.division_boundary` | 1 | `dc-l3-vienna-overpass-historical` |

### Axis 9 — OSM tag families (12 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| `highway=*` | 4 | `crs-l1-nyc-webmercator-cycleways` (`highway=cycleway`), `fio-l3-vienna-geofabrik-highways`, `spa-l3-paris-emergency-routing`, `crs-l3-tokyo-jgd-crossings` |
| `building=*` | 3 | `crs-l1-paris-lambert93`, `geo-l1-capetown-building-centroids`, `dc-l1-tokyo-ring-orientation` |
| `amenity=*` | 5 | `dd-l1-capetown-clinics-bbox`, `fio-l1-paris-kml-pois`, `spa-l1-paris-amenity-within`, `spa-l1-capetown-hospital-nn`, `spa-l3-paris-emergency-routing` |
| `shop=*` | 1 | `spa-l2-cairo-shop-knn` |
| `landuse=*` | 1 | `fio-l2-capetown-landuse-dissolve` |
| `natural=*` | 1 | `crs-l2-svalbard-polar-areas` |
| `waterway=*` | 1 | `dc-l1-capetown-waterway-nulls` |
| `railway=*` | 2 | `geo-l1-cairo-multipoint-hull` (`railway=subway_entrance`), `dc-l1-bangkok-attribute-coercion` (`railway=station`) |
| `boundary=administrative` | 4 | `dd-l1-vienna-gpkg-manifest`, `crs-l1-london-laea-areas`, `crs-l3-tokyo-jgd-crossings`, `dc-l3-vienna-overpass-historical` |
| `place=*` | 1 | `spa-l1-vienna-pip-count` |
| `leisure=*` | 1 | `dd-l1-london-parks-count` |
| Public-transport route relations | 1 | `fio-l3-vienna-geofabrik-highways` |

### Axis 10 — Geographic region (anchor requirements)

| Anchor requirement | Hit count | Tasks |
|---|---|---|
| ≥ 1 task in Vienna | 5 | `dd-l1-vienna-gpkg-manifest`, `fio-l1-vienna-shapefile-recovery`, `fio-l3-vienna-geofabrik-highways`, `spa-l1-vienna-pip-count`, `dc-l3-vienna-overpass-historical` |
| ≥ 1 task with non-Latin script | 10 | Tokyo: `dd-l2-tokyo-overture-schools`, `geo-l1-tokyo-busstop-buffer`, `dc-l1-tokyo-ring-orientation`, `crs-l3-tokyo-jgd-crossings`; Bangkok: `dd-l2-bangkok-multicrs-audit`, `geo-l2-bangkok-landuse-intersect`, `dc-l1-bangkok-attribute-coercion`; Cairo: `fio-l2-cairo-mixedgeom-split`, `geo-l1-cairo-multipoint-hull`, `spa-l2-cairo-shop-knn`, `dc-l2-cairo-invalid-dedup` |
| ≥ 1 task in southern hemisphere | 6 | Cape Town: `dd-l1-capetown-clinics-bbox`, `fio-l2-capetown-landuse-dissolve`, `geo-l1-capetown-building-centroids`, `spa-l1-capetown-hospital-nn`, `dc-l1-capetown-waterway-nulls`; Antarctica: `geo-l3-antarctica-stations-geodesic` |
| ≥ 1 task at high latitude | 2 | `crs-l2-svalbard-polar-areas` (Svalbard), `geo-l3-antarctica-stations-geodesic` (Antarctica) |
| ≥ 1 task crossing the antimeridian | 1 | `crs-l2-fiji-antimeridian` |
| ≥ 1 task in a sparsely-mapped region | 3 | `dd-l3-lagos-overture-buildings`, `spa-l2-lagos-hotspot-overlaps`, `dc-l2-lagos-snap-normalize` |

### Axis 11 — Data scale (3 variants)

| Variant | Hit count | Tasks |
|---|---|---|
| Small (~10² features) | many | most L1 tasks |
| Medium (~10⁴–10⁵ features) | 14 | `dd-l2-tokyo-overture-schools`, `dd-l2-bangkok-multicrs-audit`, `fio-l2-capetown-landuse-dissolve`, `fio-l3-vienna-geofabrik-highways`, `crs-l3-tokyo-jgd-crossings`, `geo-l2-bangkok-landuse-intersect`, `geo-l2-nyc-park-symdiff`, `geo-l3-antarctica-stations-geodesic`, `spa-l2-cairo-shop-knn`, `spa-l2-lagos-hotspot-overlaps`, `spa-l3-paris-emergency-routing`, `dc-l2-cairo-invalid-dedup`, `dc-l2-lagos-snap-normalize`, `dc-l3-vienna-overpass-historical` |
| Large (10⁶+ features, requires partition pushdown / intelligent filtering) | 1 | `dd-l3-lagos-overture-buildings` |

---

## Distribution summary

### Tasks per category × difficulty (target: 6 × (3 + 2 + 1) = 36)

| Category | L1 | L2 | L3 | Total |
|---|---|---|---|---|
| `data_discovery` | 3 | 2 | 1 | 6 |
| `format_io` | 3 | 2 | 1 | 6 |
| `crs_reprojection` | 3 | 2 | 1 | 6 |
| `geometric_ops` | 3 | 2 | 1 | 6 |
| `spatial_analysis` | 3 | 2 | 1 | 6 |
| `data_cleaning` | 3 | 2 | 1 | 6 |
| **Total** | **18** | **12** | **6** | **36** |

### L3 source allocation

All four non-bundled Axis-5 variants are exercised across the six L3 tasks (no L3 task is bundled):

| L3 task | Source |
|---|---|
| `dd-l3-lagos-overture-buildings` | Overture current |
| `fio-l3-vienna-geofabrik-highways` | Geofabrik PBF |
| `crs-l3-tokyo-jgd-crossings` | Overpass current |
| `geo-l3-antarctica-stations-geodesic` | Overture current |
| `spa-l3-paris-emergency-routing` | Overpass current |
| `dc-l3-vienna-overpass-historical` | Overpass historical |

### Authoring assumptions (resolved with supervisor)

The inventory rests on the following authoring assumptions, agreed during inventory review:

1. **Bundled "Overture-format" samples** for L1 / L2 tasks are constructed by sampling a real Overture release at authoring time and committing the slice into the task's `data/` directory. Schema mirrors the Overture column set verbatim. Live Overture access is exercised separately by `dd-l3-lagos-overture-buildings` and `geo-l3-antarctica-stations-geodesic`.
2. **Antimeridian fixtures** for `crs-l2-fiji-antimeridian` are constructed by pulling real `transportation.segment` features from Overture in the Fiji region (already split correctly at ±180°) and manually rejoining a subset of them into broken cross-meridian LineStrings, so both compliant and non-compliant variants are present in one file with real coordinates.

### Axis revisions (resolved with supervisor)

- **Axis 4 — CRS**: dropped the *Datum shift* variant. Validating sub-metre datum-grid pipelines (NTv2 / OSTN15) requires PROJ-version-pinned tolerance management that exceeds the bachelor-thesis maintenance budget. Six CRS variants remain.
- **Axis 7 — Geometry type**: dropped the *GeometryCollection* variant. Real-world tooling rarely emits RFC-7946 GeometryCollections; the underlying decomposition skill is already covered by *Mixed geometry types* on Axis 6. Six geometry-type variants remain.
- **L3 substitution**: `crs-l3-london-osgb-datumshift` is replaced by `crs-l3-tokyo-jgd-crossings`, a JGD2011 Plane-IX round-trip workflow over live Overpass data. London is no longer represented at L3 but remains anchored at L1 via `dd-l1-london-parks-count` and `crs-l1-london-laea-areas`.






