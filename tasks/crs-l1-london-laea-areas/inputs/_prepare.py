"""Authoring-time helper: slice London-area administrative polygons from Overture.

Run once at authoring time inside the project's Docker container. The output
`london_admin.geojson` is committed to the repo and served to systems
under test by the harness. Do not run this at grading time.

Source: Overture Maps release 2026-04-15.0, theme=divisions / type=division_area.
We pull two subtypes that together make up the "London-area administrative
units" Sophia would receive: `county` (the 32 London boroughs + the City of
London = 33 borough-level features) and `locality` (civil parishes and small
towns inside the bbox that fall in the surrounding home counties). The bbox
filter keeps each feature's bounding box entirely inside the Greater London
window, so we don't pull half-overlapping admin areas from outside the area
of interest. The combined slice is ~10² features, matching the task's stated
data scale.

Run:
    docker run --rm -v "$PWD":/work geo-bench-author \
        uv run python tasks/crs-l1-london-laea-areas/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "london_admin.geojson"
RELEASE = "2026-04-15.0"

XMIN, YMIN, XMAX, YMAX = -0.65, 51.20, 0.45, 51.78


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
            COALESCE(names.primary, '') AS name,
            COALESCE(subtype, '') AS subtype,
            COALESCE(country, '') AS country,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=divisions/type=division_area/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND bbox.xmax BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymax BETWEEN {YMIN} AND {YMAX}
          AND country = 'GB'
          AND subtype IN ('county', 'locality')
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
    gdf.to_file(OUT, driver="GeoJSON")
    print(f"Wrote {len(gdf)} features to {OUT}")
    print(gdf[["name", "subtype"]].head(20).to_string())


if __name__ == "__main__":
    main()
