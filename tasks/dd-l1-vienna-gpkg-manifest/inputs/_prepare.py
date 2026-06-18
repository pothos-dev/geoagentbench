"""Authoring-time helper: build the bundled multi-layer GPKG from Overture.

Slices seven layers out of Overture across an inner-Vienna bbox and
writes them into a single GPKG with each layer reprojected to
EPSG:31287 (MGI / Austria Lambert) — the canonical Austrian CRS for
municipal datasets, as referenced by the inventory row.

Layer mix (matches the story of a retired bicycle-network analyst's
multi-layer dataset; primary = districts/parks/schools per the
inventory; the rest are auxiliary cuts the persona suspects are
stale):

    1. districts            — admin polygons (locality-level) for Vienna
    2. parks                — base.land_use class='park'
    3. waterbodies          — base.water (Polygon)
    4. schools              — places.place category='school'
    5. cafes                — places.place category='cafe' (stale)
    6. supermarkets         — places.place category='supermarket' (stale)
    7. cycleway_segments    — transportation.segment class='cycleway'

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l1-vienna-gpkg-manifest/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
OUT = HERE / "vienna_planning.gpkg"
RELEASE = "2026-04-15.0"

# Inner-Vienna bbox over the historic core (districts 1, 4, 6, 7).
XMIN, YMIN, XMAX, YMAX = 16.345, 48.190, 16.380, 48.220


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


def _fetch_wkt(con: duckdb.DuckDBPyConnection, sql: str) -> gpd.GeoDataFrame:
    df = con.execute(sql).fetchdf()
    if df.empty:
        return gpd.GeoDataFrame(df, geometry=[], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    return gdf


def _slice_districts(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    return _fetch_wkt(
        con,
        f"""
        SELECT
            id,
            COALESCE(names.primary, '') AS name,
            subtype,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=divisions/type=division_area/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND country = 'AT'
          AND subtype IN ('locality', 'microhood', 'neighborhood')
        """,
    )


def _slice_parks(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    return _fetch_wkt(
        con,
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
        """,
    )


def _slice_water(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    return _fetch_wkt(
        con,
        f"""
        SELECT
            id,
            COALESCE(names.primary, '') AS name,
            class,
            subtype,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=water/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
        """,
    )


def _slice_places(
    con: duckdb.DuckDBPyConnection, categories: list[str]
) -> gpd.GeoDataFrame:
    cat_list = ", ".join(f"'{c}'" for c in categories)
    return _fetch_wkt(
        con,
        f"""
        SELECT
            id,
            COALESCE(names.primary, '') AS name,
            categories.primary AS category,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND categories.primary IN ({cat_list})
        """,
    )


def _slice_cycleways(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    return _fetch_wkt(
        con,
        f"""
        SELECT
            id,
            class,
            subclass,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=transportation/type=segment/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND class = 'cycleway'
        """,
    )


def _prepare(gdf: gpd.GeoDataFrame, geom_types: tuple[str, ...]) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    gdf = gdf[gdf.geometry.geom_type.isin(geom_types)].copy()
    gdf = gdf.to_crs("EPSG:31287")
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    return gdf


def main() -> None:
    con = _connect()

    layers: dict[str, gpd.GeoDataFrame] = {}
    layers["districts"] = _prepare(
        _slice_districts(con), ("Polygon", "MultiPolygon")
    )
    layers["parks"] = _prepare(
        _slice_parks(con), ("Polygon", "MultiPolygon")
    )
    layers["waterbodies"] = _prepare(
        _slice_water(con), ("Polygon", "MultiPolygon")
    )
    layers["schools"] = _prepare(_slice_places(con, ["school"]), ("Point",))
    layers["cafes"] = _prepare(_slice_places(con, ["cafe"]), ("Point",))
    layers["supermarkets"] = _prepare(
        _slice_places(con, ["supermarket"]), ("Point",)
    )
    layers["cycleway_segments"] = _prepare(
        _slice_cycleways(con), ("LineString", "MultiLineString")
    )

    for name, gdf in layers.items():
        print(f"  {name}: {len(gdf)} features")

    if OUT.exists():
        OUT.unlink()

    # Stable layer order: insertion order (matches the dict above).
    for name, gdf in layers.items():
        if gdf.empty:
            print(f"WARNING: layer {name!r} is empty; writing schema-only layer")
            # GPKG can carry zero-feature layers; write a schema row.
            gdf = gpd.GeoDataFrame(
                {"id": [], "name": []},
                geometry=gpd.GeoSeries([], crs="EPSG:31287"),
            )
        gdf.to_file(OUT, driver="GPKG", layer=name)

    print(f"Wrote multi-layer GPKG → {OUT}")


if __name__ == "__main__":
    main()
