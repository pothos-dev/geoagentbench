"""Authoring-time helper: slice Paris building footprints from Overture.

Run once at authoring time inside the project's Docker container. The output
`paris_buildings_wgs84.geojson` is committed to the repo and served to systems
under test by the harness. Do not run this at grading time.

Source: Overture Maps release 2026-04-15.0, theme=buildings / type=building.
We pull buildings inside a small Marais-area bbox (a few city blocks of the
4th arrondissement, just north of the Seine and east of the Pompidou). The
slice lands at ~10² polygons matching the task's stated data scale; the
bbox-containment filter avoids pulling buildings that straddle the edge of
the area of interest.

The output is GeoJSON in EPSG:4326 — the lat/lon container Camille's IGN
team receives from upstream. Her downstream heat-loss model expects
EPSG:2154 (Lambert-93), which is what the task is about.

Run:
    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/crs-l1-paris-lambert93/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "paris_buildings_wgs84.geojson"
RELEASE = "2026-04-15.0"

# A few city blocks of the Marais (4e arrondissement). Tight enough to land
# at ~10² buildings (small-data tier).
XMIN, YMIN, XMAX, YMAX = 2.355, 48.855, 2.360, 48.859


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
            COALESCE(subtype, '') AS subtype,
            COALESCE(names.primary, '') AS name,
            height,
            num_floors,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=buildings/type=building/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND bbox.xmax BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymax BETWEEN {YMIN} AND {YMAX}
        """
    ).fetchdf()

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GeoJSON")
    print(f"Wrote {len(gdf)} features to {OUT}")
    print(f"CRS: {gdf.crs}")
    print(f"Geom types: {sorted(set(gdf.geometry.geom_type.unique()))}")
    print(f"Bounds: {tuple(round(v, 6) for v in gdf.total_bounds)}")
    print(gdf[["id", "class", "name", "height"]].head(10).to_string())


if __name__ == "__main__":
    main()
