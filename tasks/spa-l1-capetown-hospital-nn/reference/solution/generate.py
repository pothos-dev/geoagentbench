"""Reference solution for spa-l1-capetown-hospital-nn.

Reads two bundled WGS84 GeoParquet files — residential addresses and hospitals
— reprojects to EPSG:32734 (UTM 34S) for metric distance computation, and
assigns each address its nearest hospital by straight-line distance.  Writes
one GPKG with one feature per address.

The task instruction does NOT specify which CRS to use — the model must
independently recognise that distance in WGS84 degrees is not metres and
choose an appropriate projected CRS.  The reference uses EPSG:32734.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import geopandas as gpd

FIXED_GPKG_TIMESTAMP = "2026-05-08T00:00:00.000Z"

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
ADDR_IN = TASK_DIR / "inputs" / "addresses.parquet"
HOSP_IN = TASK_DIR / "inputs" / "hospitals.parquet"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "nearest_hospital.gpkg"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    addresses = gpd.read_parquet(ADDR_IN)
    hospitals = gpd.read_parquet(HOSP_IN)

    # Reproject to metric CRS for honest distance computation
    addresses = addresses.to_crs("EPSG:32734")
    hospitals = hospitals.to_crs("EPSG:32734")

    joined = gpd.sjoin_nearest(
        addresses,
        hospitals[["name", "geometry"]],
        how="left",
        distance_col="distance_m",
    )

    # Deterministic tie-breaking
    joined = (
        joined.sort_values(["address_id", "name"], kind="stable")
        .drop_duplicates(subset="address_id", keep="first")
        .reset_index(drop=True)
    )

    out = gpd.GeoDataFrame(
        {
            "address_id": joined["address_id"].astype(str),
            "nearest_hospital_name": joined["name"].astype(str),
            "distance_m": joined["distance_m"].astype(float),
            "geometry": joined.geometry,
        },
        geometry="geometry",
        crs=addresses.crs,
    )
    out = out.sort_values("address_id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    out.to_file(OUT, driver="GPKG", layer="nearest_hospital")
    _stamp_fixed_timestamp(OUT)

    print(f"Read {len(addresses)} addresses and {len(hospitals)} hospitals")
    print(f"Wrote {len(out)} address->hospital records to {OUT}")
    print(f"Distance range: {out['distance_m'].min():.1f} m - {out['distance_m'].max():.1f} m")


def _stamp_fixed_timestamp(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            "UPDATE gpkg_contents SET last_change = ?", (FIXED_GPKG_TIMESTAMP,)
        )
        con.commit()
    finally:
        con.close()


if __name__ == "__main__":
    main()
