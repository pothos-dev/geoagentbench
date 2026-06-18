"""Generate broken-solution outputs for crs-l2-fiji-antimeridian.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/crs-l2-fiji-antimeridian/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import transform as shp_transform
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "fiji_transects_fmg.geojson"
INPUT_WGS84 = TASK_DIR / "inputs" / "fiji_transects_wgs84.geojson"
OUTPUT_NAME = "fiji_transects_fmg.geojson"


def _write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    if path.exists():
        path.unlink()
    gdf.to_file(path, driver="GeoJSON")


def make_wrong_format() -> None:
    """The agent forgot to reproject — output is still EPSG:4326 and
    has no length_m column either. Gate 1 fails on both counts. Score 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT_WGS84)
    _write_geojson(gdf, out_dir / OUTPUT_NAME)


def make_wrong_crs_metadata_only() -> None:
    """The agent stamps the CRS as EPSG:3460 and adds a `length_m`
    column, but skips the actual reprojection — coordinates remain in
    WGS84 degrees and `length_m` is computed as `geom.length` in
    degrees rather than metres in the projected CRS. This is what
    happens when an SUT calls `set_crs(3460, allow_override=True)`
    instead of `to_crs(3460)`. Geometry stays as plain LineString
    (no splitting, no Multi assembly) since the SUT did not engage
    with the antimeridian problem at all.

    Gate 1 passes (CRS reads as 3460, length_m present, transect_id
    present). Gate 2 passes (count = 30, geom types ∈ {LineString}).
    Subchecks that fail:
      - geometry_type_is_multilinestring (LineString-only)
      - coordinates_within_fmg_fiji_envelope (lon/lat in degrees)
      - per_transect_length_matches (degrees vs metres)
      - total_length_within_1_percent
      - antimeridian_crossings_split_into_multi_parts (no Multi at all)
    Subchecks that pass:
      - transect_id_set_preserved
      - identifying_attributes_preserved
    → 2/7 ≈ 0.286.
    """
    out_dir = HERE / "broken_wrong_crs_metadata_only" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT_WGS84)
    # length_m computed in degrees (wrong) — what an SUT does when it
    # adds the column before reprojection.
    gdf = gdf.assign(length_m=gdf.geometry.length.astype(float))
    # Force CRS metadata to 3460 without transforming coordinates.
    gdf = gdf.set_crs("EPSG:3460", allow_override=True)
    gdf = gdf.sort_values("transect_id", kind="stable").reset_index(drop=True)
    _write_geojson(gdf, out_dir / OUTPUT_NAME)


def make_wrong_attributes() -> None:
    """The agent reprojects, splits, and assembles correctly, but
    drops the `vessel` and `survey_date` columns when round-tripping
    through a thinned GeoDataFrame.

    Gates pass. Subchecks failing: identifying_attributes_preserved.
    All other 6 subchecks pass. → 6/7 ≈ 0.857.
    """
    out_dir = HERE / "broken_wrong_attributes" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(REFERENCE_OUT)
    gdf = gdf[["transect_id", "length_m", "geometry"]].copy()
    _write_geojson(gdf, out_dir / OUTPUT_NAME)


def main() -> None:
    make_wrong_format()
    make_wrong_crs_metadata_only()
    make_wrong_attributes()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
