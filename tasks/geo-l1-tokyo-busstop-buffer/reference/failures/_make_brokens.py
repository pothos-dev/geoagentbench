"""Authoring-time helper: build the four broken-solution outputs.

Run inside the project Docker container:

    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \
        geo-bench-author uv run python \
        tasks/geo-l1-tokyo-busstop-buffer/reference/failures/_make_brokens.py

Each broken solution targets a distinct failure class.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "tokyo_connectors.geojson"
REF = TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_stop_catchments.geoparquet"


def _write_parquet(gdf: gpd.GeoDataFrame, name: str) -> None:
    out = HERE / name / "outputs" / "tokyo_stop_catchments.geoparquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    gdf.to_parquet(out)
    print(f"Wrote {out}")


def make_wrong_format() -> None:
    """Output as CSV-WKT instead of GeoParquet. Gate 1 must reject."""
    ref = gpd.read_parquet(REF)
    out = HERE / "broken_wrong_format" / "outputs" / "tokyo_stop_catchments.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    ref_csv = ref.copy()
    ref_csv["wkt"] = ref_csv.geometry.to_wkt()
    ref_csv.drop(columns=["geometry"]).to_csv(out, index=False)
    print(f"Wrote {out}")


def make_degrees_buffer() -> None:
    """Buffer 400 in WGS84 degrees without reprojecting.

    This is the primary failure this task redesign is designed to catch.
    The model calls .buffer(400) on WGS84 geometry, producing buffers
    of 400 *degrees* radius — enormous polygons covering much of the globe.

    After the grader reprojects to EPSG:6677:
    - Areas are vastly larger than pi*400^2 -> buffer_area_400m fails
    - IoU vs reference is ~0 -> per_id_iou_high fails
    - Buffers trivially contain source points -> buffer_contains_source_point passes
    - IDs preserved -> connector_id checks pass

    Expected: 3/5 = 0.6... but wait, the buffer of 400 degrees from a
    point on Earth wraps the entire globe. Shapely might clip or error.
    Let's use a smaller but still wrong radius: 0.01 degrees (~1.1 km).
    This simulates a model that tried to convert but got the math wrong,
    or just used a small-ish degree value.

    Actually, the most realistic failure is calling .buffer(400) in
    degrees. Let's clip to valid bounds to avoid shapely issues.
    """
    inp = gpd.read_file(INPUT)
    # Input is now WGS84. Buffer 400 in degrees — catastrophically wrong.
    # Clip to [-180, 180] x [-90, 90] to avoid shapely topology errors.
    from shapely.geometry import box
    clip_box = box(-180, -90, 180, 90)
    buffered = inp.geometry.buffer(400).intersection(clip_box)
    out = gpd.GeoDataFrame(
        {
            "connector_id": inp["connector_id"].astype(str),
            "geometry": buffered,
        },
        geometry="geometry",
        crs="EPSG:4326",
    )
    out = out.sort_values("connector_id", kind="stable").reset_index(drop=True)
    _write_parquet(out, "broken_degrees_buffer")


def make_wrong_radius() -> None:
    """Buffer with the wrong radius (200 m instead of 400 m) in a correct
    projected CRS. Schema/CRS/ids valid; area and IoU fail."""
    inp = gpd.read_file(INPUT)
    inp = inp.to_crs("EPSG:6677")
    out = gpd.GeoDataFrame(
        {
            "connector_id": inp["connector_id"].astype(str),
            "geometry": inp.geometry.buffer(200.0),
        },
        geometry="geometry",
        crs="EPSG:6677",
    )
    out = out.sort_values("connector_id", kind="stable").reset_index(drop=True)
    _write_parquet(out, "broken_wrong_radius")


def make_shifted_centers() -> None:
    """Buffer correct radius but centred on shifted points — simulates
    wrong geometry column or misplaced join. Uses 200 m radius AND
    1000 m shift to produce a distinct score from wrong_radius."""
    inp = gpd.read_file(INPUT)
    inp = inp.to_crs("EPSG:6677")
    shifted = inp.geometry.translate(xoff=1000.0, yoff=0.0)
    out = gpd.GeoDataFrame(
        {
            "connector_id": inp["connector_id"].astype(str),
            "geometry": shifted.buffer(200.0),
        },
        geometry="geometry",
        crs="EPSG:6677",
    )
    out = out.sort_values("connector_id", kind="stable").reset_index(drop=True)
    _write_parquet(out, "broken_shifted_centers")


if __name__ == "__main__":
    make_wrong_format()
    make_degrees_buffer()
    make_wrong_radius()
    make_shifted_centers()
