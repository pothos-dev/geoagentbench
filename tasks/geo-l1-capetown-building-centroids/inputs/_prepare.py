"""Authoring-time helper: build the bundled Cape Town buildings shapefile.

Slices a small Cape Town CBD bbox out of Overture's
`theme=buildings/type=building` collection, reprojects the polygons to
EPSG:32734 (Hartebeesthoek94 / UTM 34S — the canonical metric CRS for
the south-western Cape), and writes a Shapefile with stable
`building_id` values. The slice is committed into `data/` and served to
systems under test by the harness; this helper is not run at grading
time.

The persona's "latest building footprints" is plausibly a metric-CRS
shapefile because municipal addressing teams in South Africa routinely
work in UTM 34S — the addressing-improvement project would have
received the inventory in metric coordinates from the Surveyor-General
or from a private GIS vendor.

The Shapefile dBase 10-character column-name limit forces us to use a
short name (`building_id` is exactly 10 characters and survives
unchanged); the agent must preserve this column verbatim on the
GeoJSON output.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/geo-l1-capetown-building-centroids/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
SHP_OUT = HERE / "capetown_buildings.shp"
RELEASE = "2026-04-15.0"

# A small Cape Town CBD bbox (lon/lat). Chosen to land roughly 10²
# building footprints — enough to make the centroid task meaningful
# without ballooning the bundled file.
XMIN, YMIN, XMAX, YMAX = 18.420, -33.926, 18.426, -33.922


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
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=buildings/type=building/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
        """
    ).fetchdf()

    print(f"Fetched {len(df)} buildings from Overture {RELEASE}")

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    # Keep only polygonal footprints (Overture buildings are Polygon /
    # MultiPolygon; the centroid operation works on both).
    gdf = gdf[gdf.geometry.geom_type.isin(("Polygon", "MultiPolygon"))].copy()

    # Stable ordering by Overture id, then assign a short, opaque
    # `building_id` that survives the Shapefile 10-char column-name
    # limit ("building_id" is exactly 10 chars). The Overture id itself
    # is far longer than dBase will accept as a value — it would be
    # truncated silently on write — so we substitute a synthetic id.
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    gdf["building_id"] = [f"BLD{i:05d}" for i in range(1, len(gdf) + 1)]
    gdf = gdf[["building_id", "geometry"]]

    # Reproject to UTM 34S (metric, southern hemisphere — false northing
    # 10 000 000 m). The output GeoJSON must be back in WGS84.
    gdf = gdf.to_crs("EPSG:32734")

    # Remove any prior shapefile sidecars before writing.
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        f = HERE / f"capetown_buildings.{ext}"
        if f.exists():
            f.unlink()

    gdf.to_file(SHP_OUT, driver="ESRI Shapefile")

    print(f"Wrote {len(gdf)} polygons → {SHP_OUT}")
    print(f"Sample row: {gdf.iloc[0].to_dict()}")


if __name__ == "__main__":
    main()
