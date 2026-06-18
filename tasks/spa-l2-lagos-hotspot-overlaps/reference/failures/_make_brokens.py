"""Authoring-time helper: build the broken-solution outputs.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l2-lagos-hotspot-overlaps/reference/failures/_make_brokens.py

Each broken solution targets a distinct failure class so the grader's
scores land in disjoint ranges.

  - broken_wrong_format: emits a CSV in place of the GeoParquet —
    Gate 1 rejects on the missing GeoParquet → score 0.
  - broken_wrong_density_values: emits the correct hex_id top-N with
    correct geometries, ranks, overlap counts, and sliver counts, but
    multiplies every `area_weighted_density` by 1.5 (a stand-in for
    using the wrong reduction or wrong unit). density_values_match
    fails; everything else passes.
  - broken_no_sliver_filter: re-runs the reference pipeline without
    filtering slivers (treats <100 m² polygons as real). The
    resulting top-N drifts because synthetic high-density slivers
    pull individual hex cells onto the top list, the n_overlap_polygons
    includes slivers, and n_slivers_filtered is 0 everywhere.
"""
from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REF_GEO = TASK_DIR / "reference" / "solution" / "outputs" / "hotspots.geoparquet"
REF_TAB = TASK_DIR / "reference" / "solution" / "outputs" / "hotspot_ranking.parquet"
LANDUSE_IN = TASK_DIR / "inputs" / "lagos_landuse.geojson"
HEX_IN = TASK_DIR / "inputs" / "lagos_hex_grid.geojson"

WF_DIR = HERE / "broken_wrong_format" / "outputs"
WD_DIR = HERE / "broken_wrong_density_values" / "outputs"
NS_DIR = HERE / "broken_no_sliver_filter" / "outputs"

METRIC_CRS = "EPSG:26331"
TOP_FRACTION = 0.10


def make_wrong_format() -> None:
    """Write hotspots as CSV (not GeoParquet). Gate 1 rejects."""
    WF_DIR.mkdir(parents=True, exist_ok=True)
    geo = gpd.read_parquet(REF_GEO)
    tab = pd.read_parquet(REF_TAB)
    csv_path = WF_DIR / "hotspots.csv"
    if csv_path.exists():
        csv_path.unlink()
    # Drop geometry — emit attributes only.
    geo.drop(columns=["geometry"]).to_csv(csv_path, index=False)
    # Write a parquet ranking too — only the geoparquet is missing.
    tab.to_parquet(WF_DIR / "hotspot_ranking.parquet", index=False)
    print(f"Wrote {csv_path}")


def make_wrong_density_values() -> None:
    """Schema-valid output but `area_weighted_density` × 1.5 across the board."""
    WD_DIR.mkdir(parents=True, exist_ok=True)
    geo = gpd.read_parquet(REF_GEO).copy()
    tab = pd.read_parquet(REF_TAB).copy()
    geo["area_weighted_density"] = (geo["area_weighted_density"] * 1.5).round(4)
    tab["area_weighted_density"] = (tab["area_weighted_density"] * 1.5).round(4)
    geo.to_parquet(WD_DIR / "hotspots.geoparquet")
    tab.to_parquet(WD_DIR / "hotspot_ranking.parquet", index=False)
    print(f"Wrote density-perturbed outputs → {WD_DIR}")


def make_no_sliver_filter() -> None:
    """Re-run the pipeline without sliver filtering."""
    NS_DIR.mkdir(parents=True, exist_ok=True)
    landuse = gpd.read_file(LANDUSE_IN).to_crs(METRIC_CRS)
    hex_grid = gpd.read_file(HEX_IN).to_crs(METRIC_CRS)

    overlay = gpd.overlay(
        hex_grid[["hex_id", "geometry"]],
        landuse[["id", "pop_density", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    overlay["intersect_area_m2"] = overlay.geometry.area
    overlay = overlay[overlay["intersect_area_m2"] > 0].copy()
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
    agg["n_overlap_polygons"] = agg["n_overlap_polygons"].astype("int64")
    # Naïve agent records 0 slivers filtered (skipped that step entirely).
    agg["n_slivers_filtered"] = 0

    agg = agg.sort_values(
        by=["area_weighted_density", "hex_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    # Take exactly the same row count as the reference so the row-count
    # gate doesn't collapse this broken to 0; the failure modes we want
    # to surface are subcheck-level (drifted hex_ids, wrong densities,
    # wrong sliver/overlap counts) rather than the gate.
    ref_n = len(pd.read_parquet(REF_TAB))
    n_top = ref_n
    top = agg.iloc[:n_top].copy()
    top.insert(1, "rank", range(1, len(top) + 1))
    top["area_weighted_density"] = top["area_weighted_density"].round(4)

    hex_geom = hex_grid.set_index("hex_id")["geometry"]
    top["geometry"] = top["hex_id"].map(hex_geom)
    geo = gpd.GeoDataFrame(
        top[["hex_id", "rank", "area_weighted_density", "geometry"]],
        geometry="geometry",
        crs=METRIC_CRS,
    )
    tab = top[
        [
            "hex_id",
            "rank",
            "area_weighted_density",
            "n_overlap_polygons",
            "n_slivers_filtered",
        ]
    ].reset_index(drop=True)

    geo.to_parquet(NS_DIR / "hotspots.geoparquet")
    tab.to_parquet(NS_DIR / "hotspot_ranking.parquet", index=False)
    print(f"Wrote no-sliver-filter outputs → {NS_DIR} (top-N = {n_top})")


if __name__ == "__main__":
    make_wrong_format()
    make_wrong_density_values()
    make_no_sliver_filter()
