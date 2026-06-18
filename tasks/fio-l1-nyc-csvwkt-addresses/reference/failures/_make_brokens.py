"""Generate broken-solution outputs for fio-l1-nyc-csvwkt-addresses.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l1-nyc-csvwkt-addresses/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_CSV = TASK_DIR / "inputs" / "nyc_addresses.csv"
OUTPUT_NAME = "addresses.geoparquet"


def _read_input() -> pd.DataFrame:
    return pd.read_csv(INPUT_CSV, dtype=str, keep_default_na=False)


def _to_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    geom = gpd.GeoSeries.from_wkt(df["geometry_wkt"], crs="EPSG:4326")
    return gpd.GeoDataFrame(
        df.drop(columns=["geometry_wkt"]).copy(),
        geometry=geom,
        crs="EPSG:4326",
    ).sort_values("id", kind="stable").reset_index(drop=True)


def make_wrong_format() -> None:
    """Agent wrote the result as plain CSV-with-WKT instead of GeoParquet.
    Gate 1 rejects (cannot read as parquet). Score = 0."""
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    df = _read_input()
    target.write_text(df.to_csv(index=False), encoding="utf-8")


def make_no_type_coercion() -> None:
    """Agent converted to GeoParquet but kept every column as string —
    `recorded_at` and `unit_count` are still string-typed.

    Type subchecks (recorded_at_is_timestamp_us, unit_count_is_int32)
    fail. The values still parse correctly so the value-preservation
    subchecks pass. Schema/CRS/structure all pass.
    Expected: 6 / 8 ≈ 0.75.
    """
    out_dir = HERE / "broken_no_type_coercion" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    df = _read_input()
    gdf = _to_gdf(df)
    if target.exists():
        target.unlink()
    gdf.to_parquet(target, index=False)


def make_dropped_geometry_wkt() -> None:
    """Agent typed recorded_at and unit_count correctly *but* widened
    `unit_count` to int64 (the default pyarrow inference) instead of
    int32 — the canonical "forgot the explicit cast" failure for a
    persona who explicitly asked for int32.

    `unit_count_is_int32` fails; everything else passes.
    Expected: 7 / 8 ≈ 0.875.
    """
    out_dir = HERE / "broken_int64_unit_count" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    df = _read_input()
    df["unit_count"] = pd.to_numeric(df["unit_count"]).astype("int64")
    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"], format="%Y-%m-%dT%H:%M:%SZ", utc=True
    ).dt.tz_convert(None).astype("datetime64[us]")
    gdf = _to_gdf(df)
    if target.exists():
        target.unlink()
    gdf.to_parquet(target, index=False)


def main() -> None:
    make_wrong_format()
    make_no_type_coercion()
    make_dropped_geometry_wkt()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
