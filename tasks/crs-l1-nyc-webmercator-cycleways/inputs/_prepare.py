"""Authoring-time helper: slice NYC cycleway segments from Overture and store
them in EPSG:3857 (Web Mercator) GeoParquet, matching the upstream-tool output
described in Marcus's persona story.

Source: Overture Maps release 2026-04-15.0, theme=transportation /
type=segment. We pull `class = 'cycleway'` segments inside a Manhattan-and-
inner-Brooklyn bbox so the slice lands in the small-data tier (~10² features)
without requiring topology-aware filtering. The fetched WGS84 geometry is then
reprojected to Web Mercator so the bundled input shows up to systems-under-
test exactly as Marcus's tile-rendering tool emitted it.

Run once at authoring time (committed output is `nyc_cycleways_webmercator.geoparquet`):

    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/crs-l1-nyc-webmercator-cycleways/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "nyc_cycleways_webmercator.geoparquet"
RELEASE = "2026-04-15.0"

# Manhattan + inner Brooklyn / Queens. Chosen to land at ~10² cycleway segments.
XMIN, YMIN, XMAX, YMAX = -74.020, 40.700, -73.930, 40.790


def main() -> None:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute(
        """
        CREATE OR REPLACE SECRET overture (
          TYPE s3,
          PROVIDER config,
          KEY_ID '',
          SECRET '',
          REGION 'us-west-2',
          USE_SSL true,
          URL_STYLE 'path'
        );
        """
    )

    df = con.execute(
        f"""
        SELECT
            id,
            COALESCE(class, '') AS class,
            COALESCE(subclass, '') AS subclass,
            COALESCE(names.primary, '') AS name,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=transportation/type=segment/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND bbox.xmax BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymax BETWEEN {YMIN} AND {YMAX}
          AND class = 'cycleway'
        """
    ).fetchdf()

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    # The upstream tool emits Web Mercator (EPSG:3857) — this is what Marcus
    # actually receives. Reproject from Overture's native WGS84 to 3857 so the
    # bundled input matches the persona story.
    gdf = gdf.to_crs("EPSG:3857")

    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_parquet(OUT)
    print(f"Wrote {len(gdf)} features to {OUT}")
    print(f"CRS: {gdf.crs}")
    print(f"Geom types: {sorted(set(gdf.geometry.geom_type.unique()))}")
    print(f"Bounds: {tuple(round(v, 2) for v in gdf.total_bounds)}")


if __name__ == "__main__":
    main()
