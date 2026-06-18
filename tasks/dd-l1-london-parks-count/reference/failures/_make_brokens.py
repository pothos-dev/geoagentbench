"""Generate broken-solution outputs for dd-l1-london-parks-count.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l1-london-parks-count/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "parks_summary.json"
INPUT = TASK_DIR / "inputs" / "london_parks.fgb"
OUTPUT_NAME = "parks_summary.json"


def _load_ref() -> dict:
    with REFERENCE_OUT.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_wrong_format() -> None:
    """Agent wrote the summary as CSV instead of JSON. Gate 1 (cannot
    parse JSON object) rejects the file before any subcheck runs.
    Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    ref = _load_ref()
    target.write_text(
        f"count,total_area_ha,bbox_wgs84\n"
        f"{ref['count']},{ref['total_area_ha']},"
        f"\"{ref['bbox_wgs84']}\"\n",
        encoding="utf-8",
    )


def make_wrong_filter() -> None:
    """Agent skipped the ≥ 1 ha filter and reported summary stats over
    *all* 317 polygons in the FlatGeobuf. count_correct fails, the total
    area is ~6× the reference (so total_area_ha_correct fails), and the
    bbox is wider on every component (the small parks reach further than
    the big ones do), so all four bbox componentwise subchecks fail too.
    Only `bbox_in_wgs84_range` passes (the agent did reproject correctly,
    just over the wrong subset). → 1 / 7 ≈ 0.143.
    """
    out_dir = HERE / "broken_wrong_filter" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME

    gdf = gpd.read_file(INPUT)
    count = int(len(gdf))
    total_area_ha = round(float(gdf.geometry.area.sum()) / 10_000.0, 4)
    gdf_wgs = gdf.to_crs("EPSG:4326")
    xmin, ymin, xmax, ymax = (float(v) for v in gdf_wgs.total_bounds)

    body = {
        "count": count,
        "total_area_ha": total_area_ha,
        "bbox_wgs84": [xmin, ymin, xmax, ymax],
    }
    with target.open("w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_wrong_units() -> None:
    """Agent applied the ≥ 1 ha filter and reprojected the bbox
    correctly, but forgot to convert the planar EPSG:27700 area from
    square metres to hectares. The reported `total_area_ha` is therefore
    `ref_area_ha * 10 000` — five-thousand-fold over tolerance. Only
    `total_area_ha_correct` fails; the count, all four bbox
    componentwise subchecks, and bbox_in_wgs84_range still pass.
    → 6 / 7 ≈ 0.857.
    """
    out_dir = HERE / "broken_wrong_units" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME

    ref = _load_ref()
    body = {
        "count": ref["count"],
        # m² instead of ha — the canonical "forgot the unit conversion"
        # failure mode.
        "total_area_ha": round(float(ref["total_area_ha"]) * 10_000.0, 2),
        "bbox_wgs84": list(ref["bbox_wgs84"]),
    }
    with target.open("w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    make_wrong_format()
    make_wrong_filter()
    make_wrong_units()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
