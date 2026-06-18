"""Generate broken-solution outputs for crs-l1-paris-lambert93.

Run inside Docker:
    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/crs-l1-paris-lambert93/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "paris_buildings_lambert93.gpkg"
INPUT_WGS84 = TASK_DIR / "inputs" / "paris_buildings_wgs84.geojson"
OUTPUT_NAME = "paris_buildings_lambert93.gpkg"


def _write_gpkg(gdf: gpd.GeoDataFrame, path: Path) -> None:
    if path.exists():
        path.unlink()
    gdf.to_file(path, driver="GPKG")


def make_wrong_format() -> None:
    """The agent forgot to reproject: output is still in EPSG:4326.

    Schema looks plausible (file readable, geometry column present) but
    Gate 1's CRS check fails. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT_WGS84)
    _write_gpkg(gdf, out_dir / OUTPUT_NAME)


def make_wrong_crs_metadata_only() -> None:
    """The agent stamped CRS as EPSG:2154 without actually reprojecting —
    coordinates are still in WGS84 degrees.

    Gate 1 passes (CRS reads as 2154). Gate 2 passes (Polygon, same count).
    Subchecks that fail: Lambert-93 envelope (lon/lat ~2/49 not in metres
    band), IoU (geometries are ~6e6 m apart from reference), per-feature
    area match (degrees² is ~1e-10 of m²), total area. Geometry type,
    id-jaccard, attributes, and column-presence subchecks still pass.
    """
    out_dir = HERE / "broken_wrong_crs" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT_WGS84)
    # Force the CRS metadata to 2154 even though coordinates are still in
    # WGS84 degrees — what an SUT does when it calls `set_crs` instead of
    # `to_crs`.
    gdf = gdf.set_crs("EPSG:2154", allow_override=True)
    _write_gpkg(gdf, out_dir / OUTPUT_NAME)


def make_wrong_attributes() -> None:
    """The agent reprojected correctly but dropped the `height` and
    `num_floors` columns when round-tripping through a thin GeoDataFrame.

    Gates pass. Most subchecks pass. Fails: `original_columns_preserved`
    (height + num_floors missing). The id-set, geometry, area, identifying-
    attribute (string-only) subchecks all still pass.
    """
    out_dir = HERE / "broken_wrong_attributes" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(REFERENCE_OUT)
    gdf = gdf[["id", "class", "subtype", "name", "geometry"]].copy()
    _write_gpkg(gdf, out_dir / OUTPUT_NAME)


def main() -> None:
    make_wrong_format()
    make_wrong_crs_metadata_only()
    make_wrong_attributes()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
