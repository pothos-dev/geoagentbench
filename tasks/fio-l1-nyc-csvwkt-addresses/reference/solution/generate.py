"""Reference solution for fio-l1-nyc-csvwkt-addresses.

Reads `data/nyc_addresses.csv` (CSV-with-WKT, every value quoted so
default-typed reads infer `object` dtype on every column) and writes a
GeoParquet file with proper Arrow types:

  * `recorded_at` → timestamp[us]
  * `unit_count`  → int32
  * `geometry`    → Point in EPSG:4326 (parsed from `geometry_wkt`)

Other columns (`id`, `country`, `postcode`, `street`, `number`, `unit`,
`postal_city`) stay as strings — they are intentionally string-typed in
Overture's address column set.

Determinism notes: the bundled CSV is committed and stable, rows are
read in file order which is `id`-sorted at authoring time, and the
GeoParquet writer (pyarrow via geopandas) is deterministic for a fixed
schema and fixed row order.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "nyc_addresses.csv"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "addresses.geoparquet"

STRING_COLS = (
    "id", "country", "postcode", "street", "number", "unit", "postal_city",
)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    # Read every column as string first; the agent must explicitly coerce
    # the two columns the persona cares about. dtype=str keeps `unit_count`
    # and `recorded_at` as raw strings, plus stops pandas from corrupting
    # postcode "01234" to integer 1234 etc.
    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False)

    # Coerce types.
    df["unit_count"] = pd.to_numeric(df["unit_count"], errors="raise").astype("int32")
    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"], format="%Y-%m-%dT%H:%M:%SZ", utc=True
    )
    # Drop tz to land on Arrow `timestamp[us]` (without tz). The persona
    # only needs the comparison `WHERE recorded_at > '2024-01-01'` to
    # work, which doesn't require a timezone-aware type.
    df["recorded_at"] = df["recorded_at"].dt.tz_convert(None).astype("datetime64[us]")

    geometry = gpd.GeoSeries.from_wkt(df["geometry_wkt"], crs="EPSG:4326")
    df = df.drop(columns=["geometry_wkt"])
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # Ensure stable column order so two consecutive runs are byte-equal.
    ordered = list(STRING_COLS) + ["recorded_at", "unit_count", "geometry"]
    gdf = gdf[ordered]

    # Sort by id for stable row order even if a future re-prep changes
    # the CSV row order.
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    # Cast unit_count to int32 *on the dataframe* (geopandas → pyarrow
    # otherwise infers int64). recorded_at is already datetime64[us]; the
    # parquet writer preserves us-precision when the source dtype is us.
    gdf["unit_count"] = gdf["unit_count"].astype("int32")
    gdf.to_parquet(OUT, index=False)

    print(f"Read {len(gdf)} rows from {INPUT}")
    print(f"Wrote {OUT}")
    print("Sample row:")
    print(gdf.iloc[0].to_dict())


if __name__ == "__main__":
    main()
