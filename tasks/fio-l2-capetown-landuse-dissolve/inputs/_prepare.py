"""Authoring-time helper: build the bundled FlatGeobuf input from Overture.

Slices `theme=base/type=land_use` over a wide Cape Town metro bbox,
reprojects to EPSG:32734 (Hartebeesthoek94 / UTM 34S — the canonical
projected CRS for Cape Town), and writes the slice as a FlatGeobuf.

Why Overture (not Overpass) even though the inventory row tags this
task with `landuse=*`: Overture's `base.land_use` is the schema-clean
equivalent of OSM `landuse=*` for designated-land-use mapping.
AUTHOR_CONTEXT.md states Overture is the default authoring source
whenever an equivalent collection exists. The output of this helper
ships in the FlatGeobuf format and EPSG:32734 CRS the inventory
declares — properties of the *bundled file*, independent of the
upstream source.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l2-capetown-landuse-dissolve/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "capetown_landuse.fgb"
RELEASE = "2026-04-15.0"

# Cape Town metropolitan bbox: covers the City Bowl, Atlantic Seaboard,
# Cape Flats, Northern Suburbs, and Helderberg — wide enough to land in
# the medium (~10^4) data-scale tier promised by the inventory row.
XMIN, YMIN, XMAX, YMAX = 18.30, -34.40, 19.00, -33.55


def main() -> None:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute(
        """
        CREATE OR REPLACE SECRET overture (
            TYPE s3, PROVIDER config, KEY_ID '', SECRET '',
            REGION 'us-west-2', USE_SSL true, URL_STYLE 'path'
        );
        """
    )

    df = con.execute(
        f"""
        SELECT
            id,
            class,
            subtype,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=land_use/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND class IS NOT NULL
        """
    ).fetchdf()

    print(f"Fetched {len(df)} land_use rows from Overture {RELEASE}")

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    # Polygons only — the dissolve target is areal.
    gdf = gdf[gdf.geometry.geom_type.isin(("Polygon", "MultiPolygon"))].copy()

    # Reproject to EPSG:32734 (UTM 34S) — projected metres for Cape Town.
    gdf = gdf.to_crs("EPSG:32734")

    # Stable ordering by Overture id so two consecutive runs of this
    # helper produce a byte-identical FlatGeobuf.
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="FlatGeobuf")

    n_classes = gdf["class"].nunique()
    print(f"Wrote {len(gdf)} polygons → {OUT}")
    print(f"Distinct landuse classes: {n_classes}")
    print(gdf["class"].value_counts().to_string())


if __name__ == "__main__":
    main()
