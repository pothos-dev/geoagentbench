"""Authoring-time helper: build the bundled FlatGeobuf input from Overture.

Slices `theme=base/type=land_use` for `class = 'park'` over a central-
London bbox, reprojects the polygons to EPSG:27700 (OSGB36 / British
National Grid, the canonical CRS for UK government datasets), and
writes a FlatGeobuf with stable feature ids. The slice is committed
into `data/` and served to systems under test by the harness; this
helper is not run at grading time.

Why Overture (not Overpass) even though the inventory row tags this
task with `leisure=park`: Overture's `base.land_use` has a first-class
`class='park'` value which is the structural equivalent of OSM
`leisure=park` for green-space inventory purposes. AUTHOR_CONTEXT.md
states that Overture is the default authoring source whenever an
equivalent collection exists; OSM Overpass is the fallback only when
no clean Overture equivalent is available. The FlatGeobuf format and
the EPSG:27700 CRS are properties of the *bundled file*, independent
of where the underlying features came from.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l1-london-parks-count/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "london_parks.fgb"
RELEASE = "2026-04-15.0"

# Inner-London bbox centred on Westminster and the City. Tight enough
# to keep the bundled file small (~10² polygons per the inventory's
# data-scale tier) while still bringing in the Royal Parks (Hyde,
# Regent's, Green, St James's, Kensington Gardens) plus a healthy
# spread of neighbourhood parks above and below the 1 ha threshold.
XMIN, YMIN, XMAX, YMAX = -0.200, 51.490, -0.080, 51.545


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
            COALESCE(names.primary, '') AS name,
            class,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=land_use/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND class = 'park'
        """
    ).fetchdf()

    print(f"Fetched {len(df)} park rows from Overture {RELEASE}")

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    # Keep only polygonal features (Overture land_use can occasionally
    # carry MultiPolygons; both are acceptable park footprints).
    gdf = gdf[gdf.geometry.geom_type.isin(("Polygon", "MultiPolygon"))].copy()

    # Reproject to British National Grid (the canonical UK CRS) — the
    # bundled file ships in EPSG:27700 so the agent has to think about
    # area in metres² (and convert to hectares) before reporting.
    gdf = gdf.to_crs("EPSG:27700")

    # Stable ordering by Overture id so two consecutive runs of this
    # helper produce a byte-identical FlatGeobuf.
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="FlatGeobuf")

    above = (gdf.geometry.area >= 10_000).sum()
    print(f"Wrote {len(gdf)} polygons → {OUT}")
    print(f"Of those, {above} have area ≥ 1 ha (10 000 m²)")


if __name__ == "__main__":
    main()
