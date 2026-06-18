"""Authoring-time helper: build the bundled Tokyo connectors GeoJSON.

Slices a small bbox around Tokyo Station (Marunouchi / Yaesu) out of
Overture's `theme=transportation/type=connector` collection, reprojects
the connector points to EPSG:6677 (JGD2011 Plane IX, the canonical
metric CRS for Tokyo), and writes a GeoJSON file with the connector
ids preserved as `connector_id`. The slice is committed into `data/`
and served to systems under test by the harness; this helper is not
run at grading time.

The output GeoJSON declares EPSG:6677 explicitly via geopandas /
pyogrio (the `crs` member is non-RFC-7946 but the GDAL GeoJSON driver
honours it on read). The persona's downstream tooling already works
in that CRS, so the input is shipped projected to match — the agent
only needs to buffer in the same metric CRS, no reprojection round-
trip required.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/geo-l1-tokyo-busstop-buffer/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
GEOJSON_OUT = HERE / "tokyo_connectors.geojson"
RELEASE = "2026-04-15.0"

# A small Tokyo Station / Marunouchi bbox (lon/lat). Chosen to land
# roughly 10² connectors — enough to make the buffer task meaningful
# without ballooning the bundled file. Connectors are very dense in
# central Tokyo so the bbox is intentionally small.
XMIN, YMIN, XMAX, YMAX = 139.766, 35.681, 139.769, 35.683


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
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=transportation/type=connector/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
        """
    ).fetchdf()

    print(f"Fetched {len(df)} connectors from Overture {RELEASE}")

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    # Keep only Point geometries (connectors are always Point but be
    # defensive against schema drift).
    gdf = gdf[gdf.geometry.geom_type == "Point"].copy()

    # Stable ordering by Overture id, then a short opaque connector_id.
    # The Overture id is preserved in `connector_id` directly because
    # GeoJSON has no column-name limit; carrying the full id keeps the
    # join-back to upstream Overture trivial.
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    gdf = gdf.rename(columns={"id": "connector_id"})
    gdf = gdf[["connector_id", "geometry"]]

    # Reproject to JGD2011 Plane IX (EPSG:6677). The persona's planning
    # team already operates in this CRS; the bundled input is shipped
    # in 6677 to match.
    gdf = gdf.to_crs("EPSG:6677")

    if GEOJSON_OUT.exists():
        GEOJSON_OUT.unlink()
    gdf.to_file(GEOJSON_OUT, driver="GeoJSON")

    print(f"Wrote {len(gdf)} connector points → {GEOJSON_OUT}")
    print(f"Output CRS: {gdf.crs}")
    if len(gdf):
        print(f"Sample row: {gdf.iloc[0].to_dict()}")


if __name__ == "__main__":
    main()
