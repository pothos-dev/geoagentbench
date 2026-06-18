"""Reference solution for spa-l1-vienna-pip-count.

Reads two bundled EPSG:31287 GeoJSON layers (``stations.geojson`` —
49 monitoring-station Points; ``districts.geojson`` — 23 Vienna Bezirk
Polygons), spatial-joins stations to the district that contains them,
groups by district to count, and writes a flat CSV with one row per
Bezirk. **Every Bezirk appears in the output, including the ones with
zero stations** — the persona's explicit instruction, and the
implementation hinge that distinguishes a join-then-aggregate solution
from a left-join-then-fill-na solution.

Determinism: rows sorted by ``district_code``; integer dtypes for the
two numeric columns; CSV has no embedded timestamp. Two consecutive
runs produce byte-identical output.

Output: ``outputs/stations_per_district.csv``, columns
``district_code, district_name, station_count``.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
STATIONS_IN = TASK_DIR / "inputs" / "stations.geojson"
DISTRICTS_IN = TASK_DIR / "inputs" / "districts.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "stations_per_district.csv"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    stations = gpd.read_file(STATIONS_IN)
    districts = gpd.read_file(DISTRICTS_IN)

    if stations.crs is None or stations.crs.to_epsg() != 31287:
        raise RuntimeError(f"Expected stations CRS EPSG:31287; got {stations.crs}.")
    if districts.crs is None or districts.crs.to_epsg() != 31287:
        raise RuntimeError(f"Expected districts CRS EPSG:31287; got {districts.crs}.")

    joined = gpd.sjoin(
        stations[["station_id", "geometry"]],
        districts[["district_code", "district_name", "geometry"]],
        how="left",
        predicate="within",
    )

    counts = (
        joined.dropna(subset=["district_code"])
        .groupby(["district_code", "district_name"])
        .size()
        .rename("station_count")
        .reset_index()
    )

    # Left-join the count onto the full district list so districts
    # that received zero stations still appear in the output.
    full = districts[["district_code", "district_name"]].merge(
        counts, on=["district_code", "district_name"], how="left"
    )
    full["station_count"] = full["station_count"].fillna(0).astype("int64")
    full["district_code"] = full["district_code"].astype("int64")

    full = full.sort_values("district_code", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    full.to_csv(OUT, index=False)

    print(f"Wrote {len(full)} district-count rows to {OUT}")
    print(full.to_string(index=False))


if __name__ == "__main__":
    main()
