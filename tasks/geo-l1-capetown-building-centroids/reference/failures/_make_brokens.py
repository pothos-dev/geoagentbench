"""Authoring-time helper: build the three broken-solution outputs.

Run inside the project Docker container:

    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/geo-l1-capetown-building-centroids/reference/failures/_make_brokens.py

Each broken solution targets a distinct failure class so the grader's
three observed scores land in distinct ranges.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "capetown_buildings.shp"
REF = TASK_DIR / "reference" / "solution" / "outputs" / "building_centroids.geojson"

WRONG_FORMAT = HERE / "broken_wrong_format" / "outputs" / "building_centroids.csv"
BBOX_CORNER = (
    HERE / "broken_bbox_corner_instead_of_centroid" / "outputs" / "building_centroids.geojson"
)
WRONG_IDS = HERE / "broken_wrong_ids" / "outputs" / "building_centroids.geojson"


def _load_input_4326() -> gpd.GeoDataFrame:
    inp = gpd.read_file(INPUT)
    if "building_i" in inp.columns and "building_id" not in inp.columns:
        inp = inp.rename(columns={"building_i": "building_id"})
    return inp.to_crs("EPSG:4326")


def make_wrong_format() -> None:
    """Output as CSV-WKT instead of GeoJSON. Gate 1 must reject."""
    ref = gpd.read_file(REF)
    WRONG_FORMAT.parent.mkdir(parents=True, exist_ok=True)
    ref_csv = ref.copy()
    ref_csv["wkt"] = ref_csv.geometry.to_wkt()
    ref_csv.drop(columns=["geometry"]).to_csv(WRONG_FORMAT, index=False)
    print(f"Wrote {WRONG_FORMAT}")


def make_bbox_corner() -> None:
    """Use the upper-left bbox corner instead of the geometric centroid.

    Schema is correct; IDs are correct; centroids fall inside their own
    bbox (the corner is on the bbox boundary). The point-distance
    subchecks fail by tens of metres on most buildings.
    """
    inp = _load_input_4326()
    rows = []
    for _, row in inp.iterrows():
        bid = row["building_id"]
        minx, miny, maxx, maxy = row["geometry"].bounds
        rows.append({"building_id": bid, "geometry": Point(minx, maxy)})
    out = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    out = out.sort_values("building_id", kind="stable").reset_index(drop=True)
    BBOX_CORNER.parent.mkdir(parents=True, exist_ok=True)
    if BBOX_CORNER.exists():
        BBOX_CORNER.unlink()
    out.to_file(BBOX_CORNER, driver="GeoJSON")
    print(f"Wrote {BBOX_CORNER}")


def make_wrong_ids() -> None:
    """Re-number building IDs sequentially, losing the join key.

    Geometry is the correct centroid set, but the agent invented its
    own ids (`b_0001`, `b_0002`, ...) instead of preserving the
    originals. Set Jaccard against reference is 0; per-id distance
    subchecks fail because no ids match. Schema and CRS are still
    valid → Gate 1 passes; row count is identical → Gate 2 passes.
    """
    ref = gpd.read_file(REF)
    out = ref.copy()
    out["building_id"] = [f"b_{i:04d}" for i in range(1, len(out) + 1)]
    out = out[["building_id", "geometry"]]
    WRONG_IDS.parent.mkdir(parents=True, exist_ok=True)
    if WRONG_IDS.exists():
        WRONG_IDS.unlink()
    out.to_file(WRONG_IDS, driver="GeoJSON")
    print(f"Wrote {WRONG_IDS}")


if __name__ == "__main__":
    make_wrong_format()
    make_bbox_corner()
    make_wrong_ids()
