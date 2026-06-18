"""Reference solution for dd-l3-lagos-overture-buildings.

Steps:
    1.  Fetch the Lagos State boundary polygon from Overture's
        ``divisions.division_area`` theme (``subtype='region'``).
    2.  Derive a bounding box from the state polygon for S3 partition
        pushdown on the buildings theme.
    3.  Fetch building footprints inside that bbox via DuckDB partition
        pushdown, with a coarse degree-area pre-filter to drop the
        millions of small footprints before the precise area pass.
    4.  Fetch the 20 Lagos LGAs (``subtype='county'``, ``region='NG-LA'``)
        for the per-LGA roll-up.
    5.  Reproject candidates to EPSG:26331 (Minna / Nigeria West Belt)
        for honest m² areas; keep only buildings > 1000 m².
    6.  Spatial-join each surviving building to its containing LGA by
        ``representative_point``; buildings whose point falls outside
        every LGA polygon (i.e. outside Lagos State, or in a topology
        sliver) are dropped — by construction every retained building
        belongs to exactly one LGA.
    7.  Write the EPSG:4326 GeoParquet of buildings plus a plain Parquet
        summary with one row per LGA.

Two consecutive runs may differ slightly due to Overture release drift.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
from shapely import wkt

HERE = Path(__file__).resolve().parent
OUTPUTS = HERE / "outputs"

OVERTURE_RELEASE = "2026-04-15.0"
OVERTURE_S3 = f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}"

AREA_CRS = "EPSG:26331"  # Minna / Nigeria West Belt
OUT_CRS = "EPSG:4326"
MIN_AREA_M2 = 1000

# At latitude ~6.5 N, 1° lon ≈ 110 574 m and 1° lat ≈ 111 320 m, so
# 1000 m² ≈ 8.1e-8 deg².  Use 3e-8 (~370 m²) as a safe lower bound for
# the cheap S3-side pre-filter.
DEG2_PREFILTER = 3e-8


def _setup_duckdb() -> duckdb.DuckDBPyConnection:
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
    return con


def _fetch_lagos_state(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    """Fetch the single Lagos State polygon (``subtype='region'``)."""
    url = f"{OVERTURE_S3}/theme=divisions/type=division_area/*"
    query = f"""
        SELECT
            id,
            names.primary AS name,
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE subtype = 'region'
          AND country = 'NG'
          AND names.primary = 'Lagos'
    """
    df = con.execute(query).fetchdf()
    df["geometry"] = df["geom_wkt"].apply(wkt.loads)
    df = df.drop(columns=["geom_wkt"])
    return gpd.GeoDataFrame(df, geometry="geometry", crs=OUT_CRS)


def _fetch_buildings(
    con: duckdb.DuckDBPyConnection,
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
) -> gpd.GeoDataFrame:
    """Fetch building candidates inside the state bbox."""
    url = f"{OVERTURE_S3}/theme=buildings/type=building/*"
    query = f"""
        SELECT
            id,
            height,
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE bbox.xmin <= {xmax} AND bbox.xmax >= {xmin}
          AND bbox.ymin <= {ymax} AND bbox.ymax >= {ymin}
          AND ST_Area(geometry) > {DEG2_PREFILTER}
    """
    df = con.execute(query).fetchdf()
    df["geometry"] = df["geom_wkt"].apply(wkt.loads)
    df = df.drop(columns=["geom_wkt"])
    return gpd.GeoDataFrame(df, geometry="geometry", crs=OUT_CRS)


def _fetch_lga_boundaries(
    con: duckdb.DuckDBPyConnection,
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
) -> gpd.GeoDataFrame:
    """Fetch Lagos LGA boundaries (``subtype='county'`` in NG-LA)."""
    url = f"{OVERTURE_S3}/theme=divisions/type=division_area/*"
    query = f"""
        SELECT
            id,
            names.primary AS name,
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE bbox.xmin <= {xmax} AND bbox.xmax >= {xmin}
          AND bbox.ymin <= {ymax} AND bbox.ymax >= {ymin}
          AND subtype = 'county'
          AND region = 'NG-LA'
    """
    df = con.execute(query).fetchdf()
    df["geometry"] = df["geom_wkt"].apply(wkt.loads)
    df = df.drop(columns=["geom_wkt"])
    return gpd.GeoDataFrame(df, geometry="geometry", crs=OUT_CRS)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    con = _setup_duckdb()

    # 1. Fetch the Lagos State polygon and derive its bbox
    print("Fetching Lagos State polygon...")
    state = _fetch_lagos_state(con)
    if len(state) != 1:
        raise RuntimeError(f"expected 1 Lagos State row, got {len(state)}")
    xmin, ymin, xmax, ymax = state.total_bounds
    print(f"  Lagos State bbox: [{xmin:.4f}, {ymin:.4f}, {xmax:.4f}, {ymax:.4f}]")

    # 2. Fetch building candidates
    print("Fetching buildings from Overture (with degree-area pre-filter)...")
    buildings = _fetch_buildings(con, xmin, ymin, xmax, ymax)
    print(f"  Candidates after pre-filter: {len(buildings)}")

    # 3. Fetch LGA boundaries
    print("Fetching LGA boundaries from Overture...")
    lgas = _fetch_lga_boundaries(con, xmin, ymin, xmax, ymax)
    print(f"  Lagos LGA polygons: {len(lgas)}")
    for _, row in lgas.iterrows():
        print(f"    {row['name']}")

    # 4. Reproject to EPSG:26331 for area calculation
    print("Reprojecting to EPSG:26331 for area calculation...")
    buildings_proj = buildings.to_crs(AREA_CRS)
    buildings["footprint_area_m2"] = buildings_proj.geometry.area

    # 5. Filter > 1000 m²
    large = buildings[buildings["footprint_area_m2"] > MIN_AREA_M2].copy()
    print(f"  Buildings > 1000 m²: {len(large)}")

    # 6. Spatial join to assign LGA via representative_point
    print("Spatial-joining buildings to LGAs...")
    lgas_for_join = lgas[["name", "geometry"]].rename(columns={"name": "lga"})
    large_pts = large.copy()
    large_pts = large_pts.set_geometry(large_pts.geometry.representative_point())
    joined = gpd.sjoin(large_pts, lgas_for_join, how="left", predicate="within")
    joined = joined.drop(columns=["index_right"], errors="ignore")
    # Restore the polygon geometry
    joined = joined.set_geometry(large.loc[joined.index, "geometry"])

    # 7. Drop buildings whose representative point matched no LGA polygon.
    #    By construction the 20 LGAs partition Lagos State, so any
    #    surviving null is a topology sliver — not a meaningful building.
    n_outside = int(joined["lga"].isna().sum())
    if n_outside:
        print(f"  Dropping {n_outside} building(s) outside the LGA partition (slivers)")
        joined = joined[joined["lga"].notna()].copy()

    # Drop duplicates (centroid in overlapping polygons — rare)
    joined = joined.drop_duplicates(subset="id", keep="first")

    # 8. Sort deterministically
    joined = joined.sort_values("id", kind="stable").reset_index(drop=True)

    # 9. Write lagos_buildings.geoparquet
    out_buildings = OUTPUTS / "lagos_buildings.geoparquet"
    cols = ["id", "height", "footprint_area_m2", "lga", "geometry"]
    joined[cols].to_parquet(out_buildings, index=False)
    print(f"  Wrote {out_buildings} ({len(joined)} features)")

    # 10. Per-LGA summary
    summary = (
        joined.groupby("lga", sort=True)
        .agg(
            n_buildings=("id", "count"),
            total_footprint_m2=("footprint_area_m2", "sum"),
            n_with_height=("height", lambda s: int(s.notna().sum())),
            p50_height_m=(
                "height",
                lambda s: float(s.dropna().median()) if s.notna().any() else None,
            ),
        )
        .reset_index()
    )
    summary["total_footprint_m2"] = summary["total_footprint_m2"].round(1)

    out_summary = OUTPUTS / "lagos_building_summary.parquet"
    summary.to_parquet(out_summary, index=False)
    print(f"  Wrote {out_summary}")
    print(f"\nPer-LGA summary:\n{summary.to_string()}")


if __name__ == "__main__":
    main()
