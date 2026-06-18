"""Generate broken-solution outputs for crs-l1-nyc-webmercator-cycleways.

Run inside Docker:
    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/crs-l1-nyc-webmercator-cycleways/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "nyc_cycleways_wgs84.geoparquet"
INPUT_3857 = TASK_DIR / "inputs" / "nyc_cycleways_webmercator.geoparquet"
OUTPUT_NAME = "nyc_cycleways_wgs84.geoparquet"


def make_wrong_format() -> None:
    """The agent saved as GeoJSON instead of GeoParquet (same bytes, wrong
    container). The grader's read_parquet call fails — Gate 1 collapses the
    score to 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_parquet(REFERENCE_OUT)
    out_path = out_dir / OUTPUT_NAME
    if out_path.exists():
        out_path.unlink()
    # Write GeoJSON bytes under the expected GeoParquet filename. read_parquet
    # cannot decode a GeoJSON document, so Gate 1 fails on the read.
    gdf.to_file(out_path, driver="GeoJSON")


def make_wrong_crs_metadata_only() -> None:
    """The agent stamped CRS metadata as EPSG:4326 without actually
    reprojecting — coordinates are still in Web Mercator metres.

    Gate 1 passes (CRS reads as 4326). Gate 2 passes (geom type LineString,
    same count). Subchecks that fail: NYC envelope (Mercator metres are at
    -8.2e6 / 5.0e6, far from -74 / 40), IoU (geometries are millions of
    metres away from reference), per-feature length match (lengths are in
    different units now), total length, attributes still pass. ~3/7 → 0.42.
    """
    out_dir = HERE / "broken_wrong_crs" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_parquet(INPUT_3857)
    # Force the CRS to 4326 even though coordinates are still EPSG:3857 metres.
    gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    out_path = out_dir / OUTPUT_NAME
    if out_path.exists():
        out_path.unlink()
    gdf.to_parquet(out_path)


def make_wrong_attributes() -> None:
    """The agent reprojected correctly but dropped the identifying attributes
    (class + name) when round-tripping through a thin GeoDataFrame.

    Gates pass. Most subchecks pass. Fails: identifying_attributes_preserved.
    The id_jaccard subcheck still passes (id is retained). ~6/7 → 0.86.
    """
    out_dir = HERE / "broken_wrong_attributes" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_parquet(REFERENCE_OUT)
    # Drop class and name. id and geometry are retained.
    gdf = gdf[["id", "geometry"]].copy()
    out_path = out_dir / OUTPUT_NAME
    if out_path.exists():
        out_path.unlink()
    gdf.to_parquet(out_path)


def main() -> None:
    make_wrong_format()
    make_wrong_crs_metadata_only()
    make_wrong_attributes()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
