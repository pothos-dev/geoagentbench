# Overture Maps — quick reference

Authoring-time reference for task agents preparing bundled inputs (`tasks/<slug>/data/`) and for L3 reference solutions that fetch live. **Overture is the default source** for any vector data a task needs. Do not pull data from random GitHub repos, ad-hoc gists, or other unvetted mirrors — the provenance must be auditable.

When a task is *intrinsically* about an OSM tag family that has no Overture equivalent (e.g. `waterway=stream`, niche `amenity=*` values, `boundary=protected_area`), fall back to OSM Overpass or Geofabrik — and record the rationale in `IMPLEMENTATION_NOTES.md > Open issues` so the orchestrator can surface it.

## Hosting

Overture publishes monthly releases as Hive-partitioned GeoParquet on AWS S3.

| Provider | Path |
|---|---|
| AWS S3 (us-west-2) | `s3://overturemaps-us-west-2/release/<version>/` |

Release version format: `YYYY-MM-DD.N` (e.g. `2026-04-15.0`). Look up the latest via <https://docs.overturemaps.org/release/latest/> at authoring time and **pin the version** in your `_prepare_input.py` so reruns are reproducible. The public mirror only retains recent releases (versions older than ~2 months return empty listings), so do not pin a release that is more than a month old at authoring time.

Partitioning under `<version>/`:

```
theme=<theme>/type=<type>/*.parquet
```

## Collections (themes × types)

| Theme | Type | Geometry | Description |
|---|---|---|---|
| `addresses` | `address` | Point | Postal address records (numbers, streets, postcodes). |
| `base` | `infrastructure` | Mixed | Bridges, dams, towers, utility installations, piers. |
| `base` | `land` | Polygon / Line | Terrestrial natural features (forests, sand, glaciers, etc.). |
| `base` | `land_cover` | Polygon | Generalised land-cover classes derived from satellite. |
| `base` | `land_use` | Polygon | Designated land use (residential, commercial, industrial, agricultural, recreational). |
| `base` | `water` | Polygon / Line | Water bodies and watercourses (rivers, lakes, oceans). |
| `base` | `bathymetry` | Polygon | Undersea depth contours. |
| `buildings` | `building` | Polygon | Building footprints with `height`, `class`, `roof_*`, `has_parts`. |
| `buildings` | `building_part` | Polygon | Sub-component polygons attached to a parent building. |
| `divisions` | `division` | Point | Administrative entity record (one row per entity). |
| `divisions` | `division_area` | Polygon | Polygon geometry of an administrative area (one or many per `division`). |
| `divisions` | `division_boundary` | Line | Boundary segments between adjacent divisions. |
| `places` | `place` | Point | Points of interest with `names`, `categories`, `brand`, `addresses`, `websites`, `socials`. |
| `transportation` | `segment` | Line | Road, path, rail segments with `class`, `subclass`, `road_flags`, restrictions, speed limits. |
| `transportation` | `connector` | Point | Junctions between segments. |

Common columns across all types: `id`, `geometry` (WKB), `bbox` (struct `{xmin, ymin, xmax, ymax}`), `version`, `sources`, `theme`, `type`.

## DuckDB setup

DuckDB's `spatial` and `httpfs` extensions are the standard way to query Overture. Both are pulled in by `eval/pyproject.toml`.

```sql
INSTALL httpfs;
INSTALL spatial;
LOAD httpfs;
LOAD spatial;
```

The S3 mirror is read-only and serves anonymously, but DuckDB's `SET s3_access_key_id=''` form does not by itself trigger the anonymous code path — you must declare an explicit empty-credentials secret with `CREATE SECRET`:

```sql
CREATE OR REPLACE SECRET overture (
  TYPE s3,
  PROVIDER config,
  KEY_ID '',
  SECRET '',
  REGION 'us-west-2',
  USE_SSL true,
  URL_STYLE 'path'
);
```

After the secret is created, `read_parquet('s3://overturemaps-us-west-2/...')` works without further configuration.

The S3 bucket is read-only public, but DuckDB's `httpfs` does not infer anonymous access from empty credentials. Register an anonymous secret explicitly:

```sql
CREATE OR REPLACE SECRET overture (
  TYPE s3,
  PROVIDER config,
  KEY_ID '',
  SECRET '',
  REGION 'us-west-2',
  USE_SSL true,
  URL_STYLE 'path'
);
```

Then query with the `s3://` URL:

```sql
SELECT count(*)
FROM read_parquet(
  's3://overturemaps-us-west-2/release/2026-04-15.0/theme=places/type=place/*',
  hive_partitioning=1
);
```

## Example: bbox slice for bundled inputs

The canonical authoring pattern: slice a small bbox at authoring time, commit the slice into `data/`, never re-fetch at grading time.

### London-area administrative polygons → GeoJSON

```python
"""Authoring-time helper: build the bundled input from Overture."""
from __future__ import annotations
from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "london_boroughs_wgs84.geojson"
RELEASE = "2026-04-15.0"

# Greater London bbox (approx)
XMIN, YMIN, XMAX, YMAX = -0.510, 51.280, 0.340, 51.690

con = duckdb.connect()
con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
con.execute("""
    CREATE OR REPLACE SECRET overture (
        TYPE s3, PROVIDER config, KEY_ID '', SECRET '',
        REGION 'us-west-2', USE_SSL true, URL_STYLE 'path'
    );
""")

df = con.execute(f"""
    SELECT
        id,
        names.primary AS name,
        ST_AsText(geometry) AS wkt
    FROM read_parquet(
        's3://overturemaps-us-west-2/release/{RELEASE}/theme=divisions/type=division_area/*',
        hive_partitioning=1
    )
    WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
      AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
      AND country = 'GB'
      AND subtype = 'locality'
""").fetchdf()

gdf = gpd.GeoDataFrame(
    df.drop(columns=["wkt"]),
    geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
    crs="EPSG:4326",
)
gdf = gdf.sort_values("name", kind="stable").reset_index(drop=True)
gdf.to_file(OUT, driver="GeoJSON")
```

### Buildings inside a small Vienna bbox → GeoParquet

```python
con.execute(f"""
    COPY (
        SELECT id, names.primary AS name, height, class, geometry
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=buildings/type=building/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN 16.36 AND 16.38
          AND bbox.ymin BETWEEN 48.20 AND 48.22
    ) TO 'vienna_buildings.parquet' (FORMAT PARQUET);
""")
```

### Restaurants in a Tokyo bbox → GeoJSON

```python
con.execute(f"""
    COPY (
        SELECT
            id,
            names.primary AS name,
            categories.primary AS category,
            confidence,
            geometry
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN 139.69 AND 139.71
          AND bbox.ymin BETWEEN 35.68 AND 35.70
          AND categories.primary = 'restaurant'
    ) TO 'tokyo_restaurants.geojson' WITH (FORMAT GDAL, DRIVER 'GeoJSON');
""")
```

## Pushdown notes

- **Always filter on `bbox.{xmin,ymin,xmax,ymax}` first** — DuckDB pushes these into Parquet row-group statistics, so a bbox-bounded query reads MBs not GBs.
- Prefer `read_parquet(...)` with the full `release/<version>/theme=.../type=.../*` glob over the per-file path — the planner uses Hive partitioning to prune.
- `bbox.xmin > X AND bbox.xmax < Y` (a true containment predicate) prunes more aggressively than `ST_Within(geometry, ...)`. Apply geometric predicates *after* the bbox filter.
- Common attribute paths are nested structs/arrays:
  - `names.primary` (top label), `names.common['en']` (translations).
  - `categories.primary`, `categories.alternate` (places).
  - `addresses.list[0].freeform` (places).
  - `road_flags` (transportation segments — array of strings: `is_link`, `is_bridge`, `is_tunnel`, ...).

## What not to do

- **Do not** use `urllib.urlretrieve` to pull data from `raw.githubusercontent.com`, gists, blog mirrors, or any source whose contents could change without notice.
- **Do not** commit the full Overture parquet partition — slice a small bbox.
- **Do not** leave `RELEASE` as "latest" in code that gets committed — pin a concrete `YYYY-MM-DD.N` so re-running the helper a year later still works.
- **Do not** re-run the authoring helper at grading time — bundled data is committed once, then served by the harness.

## See also

- Schema reference: <https://docs.overturemaps.org/schema/reference/>
- Latest release notes: <https://docs.overturemaps.org/release/latest/>
- DuckDB spatial: <https://duckdb.org/docs/extensions/spatial/overview.html>
