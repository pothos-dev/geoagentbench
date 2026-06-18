"""Authoring-time helper: build the bundled Cape Town hospital + address GeoParquets.

Slices two layers out of Overture release 2026-04-15.0 over a Cape Town
metropolitan bounding box and writes them as GeoParquet in
EPSG:32734 (Hartebeesthoek94 / UTM 34S — the canonical metric CRS for
the south-western Cape):

    hospitals.parquet   — places.place where categories.primary='hospital'
                          and the place name contains the word "Hospital"
                          (Overture's hospital category is wide and also
                          contains clinics, nursing practices, day hospitals;
                          the persona's question is specifically about
                          full hospitals, so we narrow by name).
                          Attributes: hospital_id, name, geometry.
    addresses.parquet   — sample of "residential pickup addresses" derived
                          from Overture building footprints in a Cape Town
                          residential bbox. Overture's `addresses.address`
                          collection has no usable South-African coverage
                          at release 2026-04-15.0 (the Cape Town bbox
                          returns 0 rows), so we substitute building
                          centroids — the realistic stand-in the persona
                          would actually use to anonymise pickup
                          locations. Attributes: address_id, geometry.

The persona is the Western Cape EMS-coverage team; they receive both
layers in UTM 34S because that's how their PostGIS workflow already
stores them. The output GPKG must stay in EPSG:32734.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l1-capetown-hospital-nn/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
HOSP_OUT = HERE / "hospitals.parquet"
ADDR_OUT = HERE / "addresses.parquet"
RELEASE = "2026-04-15.0"

# Cape Town inner-city + southern-suburbs bbox — tight enough to keep
# the hospital count near ~10 (the inventory's data-scale tier) while
# still spanning enough geography that nearest-neighbour assignment is
# non-trivial across the address sample.
HOSP_XMIN, HOSP_YMIN, HOSP_XMAX, HOSP_YMAX = 18.40, -34.00, 18.55, -33.88

# A smaller residential band over Cape Town's southern suburbs and
# City Bowl, where Overture address coverage is reliable. ~10² rows
# after a fixed-seed sample.
ADDR_XMIN, ADDR_YMIN, ADDR_XMAX, ADDR_YMAX = 18.40, -34.00, 18.55, -33.90
ADDR_SAMPLE_N = 120
ADDR_SEED = 20260508


def _connect() -> duckdb.DuckDBPyConnection:
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
    return con


def fetch_hospitals(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    df = con.execute(
        f"""
        SELECT
            id,
            names.primary AS name,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {HOSP_XMIN} AND {HOSP_XMAX}
          AND bbox.ymin BETWEEN {HOSP_YMIN} AND {HOSP_YMAX}
          AND categories.primary = 'hospital'
          AND names.primary IS NOT NULL
          AND regexp_matches(names.primary, '\\bHospital\\b')
          AND NOT regexp_matches(names.primary, '(?i)\\b(day hospital|clinic|practice|pharmacy|centre|center|surgery)\\b')
        """
    ).fetchdf()
    print(f"Fetched {len(df)} hospital places from Overture {RELEASE}")
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    # Overture places contain near-duplicates of the same hospital from
    # different upstream sources. De-duplicate by exact name (keeping
    # the first sorted-by-Overture-id occurrence) so each name resolves
    # to one hospital point.
    gdf = gdf.sort_values("id", kind="stable")
    gdf = gdf.drop_duplicates(subset="name", keep="first").reset_index(drop=True)
    gdf["hospital_id"] = [f"H{i:03d}" for i in range(1, len(gdf) + 1)]
    gdf = gdf[["hospital_id", "name", "geometry"]]
    gdf = gdf.to_crs("EPSG:32734")
    return gdf


def fetch_addresses(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    """Sample residential building centroids as proxy "pickup addresses".

    Overture's `addresses.address` collection has no Cape-Town coverage
    in release 2026-04-15.0; substitute residential building centroids
    over a southern-suburbs bbox. This is the kind of anonymised
    proxy a real EMS-planning analyst would actually feed into a
    coverage study.
    """
    df = con.execute(
        f"""
        SELECT
            id,
            ST_AsText(ST_Centroid(geometry)) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=buildings/type=building/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {ADDR_XMIN} AND {ADDR_XMAX}
          AND bbox.ymin BETWEEN {ADDR_YMIN} AND {ADDR_YMAX}
          AND (class IS NULL OR class = 'residential')
        """
    ).fetchdf()
    print(f"Fetched {len(df)} residential-building centroids from Overture {RELEASE}")
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    gdf = gdf[gdf.geometry.geom_type == "Point"].copy()
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    if len(gdf) > ADDR_SAMPLE_N:
        gdf = gdf.sample(n=ADDR_SAMPLE_N, random_state=ADDR_SEED).copy()
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    gdf["address_id"] = [f"A{i:04d}" for i in range(1, len(gdf) + 1)]
    gdf = gdf[["address_id", "geometry"]]
    gdf = gdf.to_crs("EPSG:32734")
    return gdf


def main() -> None:
    con = _connect()

    hospitals = fetch_hospitals(con)
    addresses = fetch_addresses(con)

    if HOSP_OUT.exists():
        HOSP_OUT.unlink()
    if ADDR_OUT.exists():
        ADDR_OUT.unlink()

    hospitals.to_parquet(HOSP_OUT, index=False)
    addresses.to_parquet(ADDR_OUT, index=False)

    print(f"Wrote {len(hospitals)} hospitals → {HOSP_OUT}")
    print(f"Wrote {len(addresses)} addresses → {ADDR_OUT}")
    print("Hospitals sample:")
    print(hospitals.head().to_string())


if __name__ == "__main__":
    main()
