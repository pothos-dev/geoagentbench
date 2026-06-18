"""Authoring-time helper: slice named glacier polygons over Svalbard from Overture.

Run once at authoring time inside the project's Docker container. The output
`svalbard_glaciers_wgs84.gpkg` is committed to the repo and served to systems
under test by the harness. Do not run this at grading time.

Source: Overture Maps release 2026-04-15.0, theme=base / type=land,
filtered to ``subtype = 'glacier'`` over a Svalbard bbox
(10°–35°E, 76°–81°N). We keep only features with a non-null primary
name so the persona's "top 20 named glaciers" question is unambiguous;
the 169 named glacier polygons that result match the task's stated
``Small (~10²)`` scale tier.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work geo-bench-author \\
        uv run python tasks/crs-l2-svalbard-polar-areas/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "svalbard_glaciers_wgs84.gpkg"
RELEASE = "2026-04-15.0"

XMIN, YMIN, XMAX, YMAX = 10.0, 76.0, 35.0, 81.0


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
            names.primary AS name,
            COALESCE(subtype, '') AS subtype,
            COALESCE(class, '') AS class,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=land/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND bbox.xmax BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymax BETWEEN {YMIN} AND {YMAX}
          AND subtype = 'glacier'
          AND names.primary IS NOT NULL
        ORDER BY id
        """
    ).fetchdf()

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    gdf = gdf.sort_values(["name", "id"], kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GPKG", layer="glaciers")
    print(f"Wrote {len(gdf)} features to {OUT}")
    print(gdf[["name"]].head(20).to_string())


if __name__ == "__main__":
    main()
