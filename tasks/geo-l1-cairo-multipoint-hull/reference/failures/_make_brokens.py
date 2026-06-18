"""Generate broken-solution outputs for geo-l1-cairo-multipoint-hull.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/geo-l1-cairo-multipoint-hull/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "cairo_metro_stations.geojson"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "cairo_metro_hulls.geojson"
OUTPUT_NAME = "cairo_metro_hulls.geojson"


def _ensure(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / OUTPUT_NAME


def make_wrong_format() -> None:
    """Agent wrote the output as a flat CSV-WKT instead of GeoJSON.

    Gate 1 rejects: GeoPandas cannot read a `.geojson`-named CSV;
    even if it could, the file would not parse as GeoJSON.
    Score = 0.
    """
    target = _ensure(HERE / "broken_wrong_format" / "outputs")
    if target.exists():
        target.unlink()
    ref = gpd.read_file(REFERENCE_OUT)
    # Write as plain CSV with a WKT geometry column (no spatial header).
    ref_csv = ref.copy()
    ref_csv["geometry_wkt"] = ref_csv.geometry.to_wkt()
    ref_csv.drop(columns=["geometry"]).to_csv(target, index=False)


def make_bbox_instead_of_hull() -> None:
    """Agent returned the axis-aligned bounding box of each MultiPoint
    instead of the convex hull. Schema and attributes are correct;
    only `hull_iou_against_reference` fails (bbox area is ~30 % larger
    than the hull on average for 4–5 random points).

    Expected: 5/6 ≈ 0.833.
    """
    target = _ensure(HERE / "broken_bbox_instead_of_hull" / "outputs")
    inp = gpd.read_file(INPUT)
    bboxes = inp.geometry.bounds.apply(
        lambda r: box(r.minx, r.miny, r.maxx, r.maxy), axis=1
    )
    out = gpd.GeoDataFrame(
        {
            "station_name_en": inp["station_name_en"],
            "station_name_ar": inp["station_name_ar"],
            "geometry": bboxes,
        },
        geometry="geometry",
        crs="EPSG:4326",
    ).sort_values("station_name_en", kind="stable").reset_index(drop=True)
    if target.exists():
        target.unlink()
    out.to_file(target, driver="GeoJSON")


def make_empty_arabic() -> None:
    """Agent produced the right hulls and English names but blanked the
    Arabic name column (e.g. dropped non-ASCII during a CSV roundtrip
    and refilled with empty strings to keep the schema). Two subchecks
    fail: `station_name_ar_populated` and `arabic_names_match`.

    Expected: 4/6 ≈ 0.667.
    """
    target = _ensure(HERE / "broken_empty_arabic" / "outputs")
    ref = gpd.read_file(REFERENCE_OUT).copy()
    ref["station_name_ar"] = ""
    if target.exists():
        target.unlink()
    ref.to_file(target, driver="GeoJSON")


def main() -> None:
    make_wrong_format()
    make_bbox_instead_of_hull()
    make_empty_arabic()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
