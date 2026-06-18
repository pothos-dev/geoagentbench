"""Regenerate the three broken-solution fixtures for this task.

All three are derived deterministically from the reference outputs plus
one additional Overture fetch for the no-area-filter case.

* ``broken_wrong_format`` — the reference building file dumped as CSV
  but saved under a ``.geoparquet`` extension; Gate 1 rejects on
  Parquet read.  Score = 0.

* ``broken_wrong_crs_area`` — reference building set with
  ``footprint_area_m2`` recomputed in EPSG:4326 (degrees²) instead of
  EPSG:26331; summary ``total_footprint_m2`` recomputed from those
  bogus values.  Score ≈ 0.78.

* ``broken_no_area_filter`` — same workflow as the reference but
  without the ``> 1000 m²`` filter; building file is the full
  ``DEG2_PREFILTER`` candidate set joined to LGAs (dropping topology
  slivers as the reference does).  Score ≈ 0.55.

Run from the task directory::

    python reference/failures/_make_brokens.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REF_OUTPUTS = TASK_DIR / "reference" / "solution" / "outputs"

sys.path.insert(0, str(TASK_DIR / "reference" / "solution"))
import generate  # noqa: E402  — reuse the reference fetch helpers


def _summarise(joined: gpd.GeoDataFrame) -> pd.DataFrame:
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
    return summary


def _write_outputs(out_dir: Path, bldg: gpd.GeoDataFrame, summary: pd.DataFrame) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = ["id", "height", "footprint_area_m2", "lga", "geometry"]
    bldg[cols].to_parquet(out_dir / "lagos_buildings.geoparquet", index=False)
    summary.to_parquet(out_dir / "lagos_building_summary.parquet", index=False)


def make_wrong_format(ref_bldg: gpd.GeoDataFrame, ref_summary: pd.DataFrame) -> None:
    """CSV with WKT-text geometry, mis-extensioned as .geoparquet."""
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    bldg_csv = ref_bldg.copy()
    bldg_csv["geometry"] = bldg_csv.geometry.apply(lambda g: g.wkt)
    bldg_csv.to_csv(out_dir / "lagos_buildings.geoparquet", index=False)
    ref_summary.to_parquet(out_dir / "lagos_building_summary.parquet", index=False)
    print(f"  Wrote {out_dir}")


def make_wrong_crs_area(ref_bldg: gpd.GeoDataFrame) -> None:
    """Same buildings, but area computed in WGS84 (degrees²)."""
    out_dir = HERE / "broken_wrong_crs_area" / "outputs"
    bad = ref_bldg.copy()
    # area in EPSG:4326 degrees², orders of magnitude too small
    bad["footprint_area_m2"] = bad.geometry.area
    summary = _summarise(bad)
    _write_outputs(out_dir, bad, summary)
    print(f"  Wrote {out_dir}")


def make_no_area_filter() -> None:
    """All candidates (no > 1000 m² filter) joined to LGAs."""
    out_dir = HERE / "broken_no_area_filter" / "outputs"

    print("  Re-fetching candidates for no-area-filter broken...")
    con = generate._setup_duckdb()
    state = generate._fetch_lagos_state(con)
    xmin, ymin, xmax, ymax = state.total_bounds
    buildings = generate._fetch_buildings(con, xmin, ymin, xmax, ymax)
    lgas = generate._fetch_lga_boundaries(con, xmin, ymin, xmax, ymax)

    # Compute m² area but DO NOT filter
    buildings_proj = buildings.to_crs(generate.AREA_CRS)
    buildings["footprint_area_m2"] = buildings_proj.geometry.area

    lgas_for_join = lgas[["name", "geometry"]].rename(columns={"name": "lga"})
    pts = buildings.copy()
    pts = pts.set_geometry(pts.geometry.representative_point())
    joined = gpd.sjoin(pts, lgas_for_join, how="left", predicate="within")
    joined = joined.drop(columns=["index_right"], errors="ignore")
    joined = joined.set_geometry(buildings.loc[joined.index, "geometry"])
    joined = joined[joined["lga"].notna()].copy()
    joined = joined.drop_duplicates(subset="id", keep="first")
    joined = joined.sort_values("id", kind="stable").reset_index(drop=True)

    summary = _summarise(joined)
    _write_outputs(out_dir, joined, summary)
    print(f"  Wrote {out_dir} ({len(joined)} features)")


def main() -> None:
    if not (REF_OUTPUTS / "lagos_buildings.geoparquet").exists():
        raise SystemExit(
            "Reference outputs missing — run reference/solution/generate.py first."
        )

    print("Loading reference outputs...")
    ref_bldg = gpd.read_parquet(REF_OUTPUTS / "lagos_buildings.geoparquet")
    ref_summary = pd.read_parquet(REF_OUTPUTS / "lagos_building_summary.parquet")
    print(f"  Reference: {len(ref_bldg)} buildings, {len(ref_summary)} LGAs")

    # Clean previous outputs
    for name in ("broken_wrong_format", "broken_wrong_crs_area", "broken_no_area_filter"):
        sub = HERE / name / "outputs"
        if sub.exists():
            shutil.rmtree(sub)

    print("Building broken_wrong_format...")
    make_wrong_format(ref_bldg, ref_summary)
    print("Building broken_wrong_crs_area...")
    make_wrong_crs_area(ref_bldg)
    print("Building broken_no_area_filter...")
    make_no_area_filter()


if __name__ == "__main__":
    main()
