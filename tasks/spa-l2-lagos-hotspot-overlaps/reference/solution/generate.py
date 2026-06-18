"""Reference solution for spa-l2-lagos-hotspot-overlaps.

Pipeline:
  1. Read `lagos_landuse.geojson` and `lagos_hex_grid.geojson` from
     `data/` (both EPSG:4326).
  2. Reproject both to EPSG:26331 (Minna / Nigeria West Belt) for
     metric area arithmetic.
  3. Split land-use polygons into the *kept* set (area ≥ 100 m²) and
     the *sliver* set (area < 100 m²). Slivers are recorded per-hex
     for traceability (`n_slivers_filtered`) but excluded from the
     area-weighted aggregation.
  4. Overlay (intersection) the kept land-use set with the hex grid;
     for each (hex, polygon) pair compute the intersection area in m².
  5. Per hex, compute the area-weighted mean of `pop_density` weighted
     by intersection area, plus `n_overlap_polygons` (count of kept
     polygons whose intersection with the hex is positive).
  6. Per hex, count how many sliver polygons intersect it →
     `n_slivers_filtered`.
  7. Discard hex cells with `n_overlap_polygons == 0` (no kept land-use
     polygon overlaps), then rank the remaining cells by
     `area_weighted_density` descending. Tie-break by `hex_id` ascending.
  8. Take the top 10% (`ceil(0.10 * n_eligible)`) and emit:
       - `hotspots.geoparquet` — Polygon geometries + hex_id + rank +
         area_weighted_density. CRS = EPSG:26331.
       - `hotspot_ranking.parquet` — tabular: hex_id, rank,
         area_weighted_density, n_overlap_polygons, n_slivers_filtered.

Determinism:
  - Inputs are bundled and sliver injection is seeded.
  - Output frames are sorted by `rank` (1..N) and serialised with
    pyarrow's default Parquet writer; two consecutive runs produce
    byte-identical files.
"""
from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
LANDUSE = TASK_DIR / "inputs" / "lagos_landuse.geojson"
HEX = TASK_DIR / "inputs" / "lagos_hex_grid.geojson"
OUTPUTS = HERE / "outputs"

SLIVER_AREA_THRESHOLD_M2 = 100.0
TOP_FRACTION = 0.10
METRIC_CRS = "EPSG:26331"

DENSITY_DECIMALS = 4  # round area_weighted_density to .0001 ppl/km²


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    landuse = gpd.read_file(LANDUSE).to_crs(METRIC_CRS)
    hex_grid = gpd.read_file(HEX).to_crs(METRIC_CRS)

    # 1. Filter slivers by area in EPSG:26331.
    landuse_area = landuse.geometry.area
    is_sliver = landuse_area < SLIVER_AREA_THRESHOLD_M2
    kept = landuse.loc[~is_sliver, ["id", "pop_density", "geometry"]].copy()
    slivers = landuse.loc[is_sliver, ["id", "geometry"]].copy()
    print(
        f"Land-use polygons: {len(landuse)} total; "
        f"kept {len(kept)}; filtered {len(slivers)} slivers"
    )

    # 2. Per-hex sliver intersection counts via sjoin (predicate=intersects).
    if len(slivers) > 0:
        sliver_join = gpd.sjoin(
            hex_grid[["hex_id", "geometry"]],
            slivers[["id", "geometry"]],
            predicate="intersects",
            how="inner",
        )
        n_slivers = (
            sliver_join.groupby("hex_id").size().rename("n_slivers_filtered")
        )
    else:
        n_slivers = pd.Series(dtype=int, name="n_slivers_filtered")

    # 3. Overlay (intersection) of kept polygons with hex grid.
    overlay = gpd.overlay(
        hex_grid[["hex_id", "geometry"]],
        kept[["id", "pop_density", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    overlay["intersect_area_m2"] = overlay.geometry.area
    # Drop any zero-area artefacts from overlay.
    overlay = overlay[overlay["intersect_area_m2"] > 0].copy()

    # 4. Per-hex area-weighted aggregation.
    overlay["weighted"] = overlay["intersect_area_m2"] * overlay["pop_density"]
    grouped = overlay.groupby("hex_id").agg(
        sum_weighted=("weighted", "sum"),
        sum_area=("intersect_area_m2", "sum"),
        n_overlap_polygons=("id", "nunique"),
    )
    grouped["area_weighted_density"] = (
        grouped["sum_weighted"] / grouped["sum_area"]
    )

    agg = grouped.reset_index()[
        ["hex_id", "area_weighted_density", "n_overlap_polygons"]
    ]

    # 5. Attach sliver counts (zero where missing).
    sliver_df = n_slivers.reset_index()
    agg = agg.merge(sliver_df, on="hex_id", how="left")
    agg["n_slivers_filtered"] = (
        agg["n_slivers_filtered"].fillna(0).astype("int64")
    )
    agg["n_overlap_polygons"] = agg["n_overlap_polygons"].astype("int64")

    # 6. Sort + rank: density desc, hex_id asc.
    agg = agg.sort_values(
        by=["area_weighted_density", "hex_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    n_eligible = len(agg)
    n_top = max(1, math.ceil(TOP_FRACTION * n_eligible))
    top = agg.iloc[:n_top].copy()
    top.insert(1, "rank", range(1, len(top) + 1))
    top["area_weighted_density"] = top["area_weighted_density"].round(
        DENSITY_DECIMALS
    )

    # 7. Build the GeoParquet (geometry + a few attributes).
    hex_geom = hex_grid.set_index("hex_id")["geometry"]
    top["geometry"] = top["hex_id"].map(hex_geom)
    hotspots_gdf = gpd.GeoDataFrame(
        top[
            [
                "hex_id",
                "rank",
                "area_weighted_density",
                "geometry",
            ]
        ],
        geometry="geometry",
        crs=METRIC_CRS,
    )

    # 8. Tabular ranking file.
    ranking_df = top[
        [
            "hex_id",
            "rank",
            "area_weighted_density",
            "n_overlap_polygons",
            "n_slivers_filtered",
        ]
    ].reset_index(drop=True)

    geoparquet_out = OUTPUTS / "hotspots.geoparquet"
    parquet_out = OUTPUTS / "hotspot_ranking.parquet"
    if geoparquet_out.exists():
        geoparquet_out.unlink()
    if parquet_out.exists():
        parquet_out.unlink()

    hotspots_gdf.to_parquet(geoparquet_out)
    ranking_df.to_parquet(parquet_out, index=False)

    print(
        f"Eligible hex cells (≥1 kept polygon overlap): {n_eligible}; "
        f"top {TOP_FRACTION:.0%} = {n_top}"
    )
    print(
        f"Density range in top-N: "
        f"{top['area_weighted_density'].min():.2f} – "
        f"{top['area_weighted_density'].max():.2f} ppl/km²"
    )
    print(f"Wrote {geoparquet_out} ({len(hotspots_gdf)} rows)")
    print(f"Wrote {parquet_out} ({len(ranking_df)} rows)")


if __name__ == "__main__":
    main()
