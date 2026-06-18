"""Authoring-time helper: build the four broken-solution outputs.

Run inside the project Docker container:

    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \
        geo-bench-author uv run python \
        tasks/spa-l1-capetown-hospital-nn/reference/failures/_make_brokens.py

Each broken solution targets a distinct failure class.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REF = TASK_DIR / "reference" / "solution" / "outputs" / "nearest_hospital.gpkg"
ADDR_IN = TASK_DIR / "inputs" / "addresses.parquet"
HOSP_IN = TASK_DIR / "inputs" / "hospitals.parquet"

FIXED_GPKG_TIMESTAMP = "2026-05-08T00:00:00.000Z"


def _stamp(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            "UPDATE gpkg_contents SET last_change = ?", (FIXED_GPKG_TIMESTAMP,)
        )
        con.commit()
    finally:
        con.close()


def _write_gpkg(gdf: gpd.GeoDataFrame, name: str) -> None:
    out = HERE / name / "outputs" / "nearest_hospital.gpkg"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    gdf.to_file(out, driver="GPKG", layer="nearest_hospital")
    _stamp(out)
    print(f"Wrote {out}")


def make_wrong_format() -> None:
    """Output as GeoJSON instead of GPKG. Gate 1 rejects."""
    ref = gpd.read_file(REF)
    out = HERE / "broken_wrong_format" / "outputs" / "nearest_hospital.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    ref.to_crs("EPSG:4326").to_file(out, driver="GeoJSON")
    print(f"Wrote {out}")


def make_degrees_distance() -> None:
    """Compute NN in WGS84 without reprojecting — distances in degrees.

    This is the primary failure the task redesign catches. The model
    computes sjoin_nearest on WGS84 data, getting distances in degrees
    (~0.01-0.1) instead of metres (~1000-10000). The hospital assignment
    may also differ since lat/lon distance ordering can diverge from
    metric ordering at Cape Town's latitude.

    Gates pass (GPKG with correct columns). distance_m_matches_reference
    fails (values off by ~10^5). nearest_hospital_name may partially
    match (some addresses have the same nearest in both CRSes).
    """
    addresses = gpd.read_parquet(ADDR_IN)
    hospitals = gpd.read_parquet(HOSP_IN)
    # Both are now WGS84 — compute NN in degrees
    joined = gpd.sjoin_nearest(
        addresses,
        hospitals[["name", "geometry"]],
        how="left",
        distance_col="distance_m",
    )
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
    # Reproject to UTM for GPKG output (model might do this for output)
    out = out.to_crs("EPSG:32734")
    _write_gpkg(out, "broken_degrees_distance")


def make_wrong_hospital() -> None:
    """Pick a constant hospital for every address."""
    addresses = gpd.read_parquet(ADDR_IN)
    hospitals = gpd.read_parquet(HOSP_IN)
    addresses = addresses.to_crs("EPSG:32734")
    hospitals = hospitals.to_crs("EPSG:32734")
    pick = hospitals[hospitals["name"] == "Groote Schuur Hospital"].iloc[0]
    out = gpd.GeoDataFrame(
        {
            "address_id": addresses["address_id"].astype(str),
            "nearest_hospital_name": [pick["name"]] * len(addresses),
            "distance_m": [g.distance(pick.geometry) for g in addresses.geometry],
            "geometry": addresses.geometry,
        },
        geometry="geometry",
        crs=addresses.crs,
    )
    out = out.sort_values("address_id", kind="stable").reset_index(drop=True)
    _write_gpkg(out, "broken_wrong_hospital")


def make_distance_in_km() -> None:
    """Correct hospital, but distance in kilometres."""
    ref = gpd.read_file(REF)
    out = ref.copy()
    out["distance_m"] = out["distance_m"] / 1000.0
    _write_gpkg(out, "broken_distance_in_km")


if __name__ == "__main__":
    make_wrong_format()
    make_degrees_distance()
    make_wrong_hospital()
    make_distance_in_km()
