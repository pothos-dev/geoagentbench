"""Authoring-time helper: construct the four broken solutions.

Each broken sample lives in reference/failures/broken_<class>/outputs/<name>.

  * broken_wrong_format        -- writes a GeoJSON instead of CSV.
                                  Gate 1 fails (CSV-parse). Score 0.
  * broken_no_reprojection     -- honestly declares crs_epsg=4326 with
                                  area / bbox computed in degrees.
                                  Gate 1 fails (4326 not in accepted
                                  North-Pole-origin set). Score 0.
  * broken_conformal_pick      -- picks EPSG:3995 (Arctic Polar
                                  Stereographic) — accepted but
                                  conformal-not-equal-area, so the
                                  equal_area_crs_used subcheck fails;
                                  all other subchecks pass. Score 7/8.
  * broken_offset_topN         -- 20 rows in EPSG:3575 (canonical),
                                  but ranks 6-25 instead of 1-20
                                  (drops the actual top 5; adds ranks
                                  21-25 from the full-reprojected list).
                                  Area/bbox values for the rows present
                                  are correct; only the membership +
                                  area-totals tests fail. Score 6/8.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent  # reference/failures/
TASK_DIR = HERE.parent.parent  # task root
INPUT = TASK_DIR / "inputs" / "svalbard_glaciers_wgs84.gpkg"
REFERENCE = TASK_DIR / "reference" / "solution" / "outputs" / "svalbard_glaciers_top20.csv"

CANONICAL_EPSG = 3575  # WGS 84 / North Pole LAEA Europe — equal-area
CONFORMAL_EPSG = 3995  # WGS 84 / Arctic Polar Stereographic — accepted but not equal-area

OUTPUT_COLUMNS = [
    "name",
    "area_km2",
    "bbox_minx_polar",
    "bbox_miny_polar",
    "bbox_maxx_polar",
    "bbox_maxy_polar",
    "crs_epsg",
]


def _write_csv(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "svalbard_glaciers_top20.csv"
    if out.exists():
        out.unlink()
    df.to_csv(out, index=False)


def _build_csv(target_epsg: int) -> pd.DataFrame:
    """Correct pipeline against a chosen target EPSG."""
    gdf = gpd.read_file(INPUT).to_crs(epsg=target_epsg)
    gdf["area_km2"] = gdf.geometry.area / 1_000_000.0
    bounds = gdf.geometry.bounds.rename(
        columns={
            "minx": "bbox_minx_polar",
            "miny": "bbox_miny_polar",
            "maxx": "bbox_maxx_polar",
            "maxy": "bbox_maxy_polar",
        }
    )
    df = pd.concat([gdf.drop(columns="geometry"), bounds], axis=1)
    df["crs_epsg"] = target_epsg
    df = df.sort_values(
        ["area_km2", "name", "id"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    return df


def _wrong_format() -> None:
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Write a GeoJSON under the expected name -- the grader expects CSV
    # and will fail Gate 1.
    gdf = gpd.read_file(INPUT).to_crs(epsg=CANONICAL_EPSG).head(20)
    out = out_dir / "svalbard_glaciers_top20.csv"
    if out.exists():
        out.unlink()
    gdf.to_file(out, driver="GeoJSON")


def _no_reprojection() -> None:
    """Agent skips reprojection entirely and honestly declares 4326.
    Gate 1 rejects 4326 from the accepted polar set. Score = 0.0."""
    out_dir = HERE / "broken_no_reprojection" / "outputs"
    gdf = gpd.read_file(INPUT)  # remains EPSG:4326
    gdf["area_km2"] = gdf.geometry.area  # nonsense: degrees^2
    bounds = gdf.geometry.bounds.rename(
        columns={
            "minx": "bbox_minx_polar",
            "miny": "bbox_miny_polar",
            "maxx": "bbox_maxx_polar",
            "maxy": "bbox_maxy_polar",
        }
    )
    df = pd.concat([gdf.drop(columns="geometry"), bounds], axis=1)
    df["crs_epsg"] = 4326  # honestly declared — Gate 1 rejects it
    df = df.sort_values(
        ["area_km2", "name", "id"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    _write_csv(df.head(20)[OUTPUT_COLUMNS], out_dir)


def _conformal_pick() -> None:
    """Agent picks EPSG:3995 — accepted (polar, North-Pole-origin) but
    conformal not equal-area. equal_area_crs_used subcheck fails; all
    other subchecks pass against ref reprojected to 3995. Score = 7/8."""
    out_dir = HERE / "broken_conformal_pick" / "outputs"
    df = _build_csv(CONFORMAL_EPSG)
    _write_csv(df.head(20)[OUTPUT_COLUMNS], out_dir)


def _offset_topN() -> None:
    """Agent picks the canonical CRS and does correct per-glacier work,
    but ranks rows 6-25 instead of 1-20. Score = 6/8."""
    out_dir = HERE / "broken_offset_topN" / "outputs"
    df = _build_csv(CANONICAL_EPSG)
    out_df = df.iloc[5:25][OUTPUT_COLUMNS].reset_index(drop=True)
    _write_csv(out_df, out_dir)


def main() -> None:
    # Wipe and rebuild so retired brokens don't linger.
    for sub in ("broken_wrong_format", "broken_no_reprojection",
                "broken_conformal_pick", "broken_offset_topN"):
        d = HERE / sub
        if d.exists():
            shutil.rmtree(d)
    _wrong_format()
    _no_reprojection()
    _conformal_pick()
    _offset_topN()
    print("broken solutions written")


if __name__ == "__main__":
    main()
