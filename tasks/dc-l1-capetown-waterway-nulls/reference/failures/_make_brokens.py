"""Generate broken-solution outputs for dc-l1-capetown-waterway-nulls.

Run inside Docker:
    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/dc-l1-capetown-waterway-nulls/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_RAW = TASK_DIR / "inputs" / "capetown_waterways.geojson"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "waterways_clean.geojson"
OUTPUT_NAME = "waterways_clean.geojson"


def make_wrong_format() -> None:
    """Agent wrote GeoJSON in EPSG:3857 (forgot the persona's CRS
    requirement) instead of EPSG:4326. Gate 1's CRS-equality check
    fails. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME

    gdf = gpd.read_file(REFERENCE_OUT)
    gdf = gdf.to_crs(3857)
    if target.exists():
        target.unlink()
    gdf.to_file(target, driver="GeoJSON")

    # Preserve the foreign member so the *only* failure is the CRS gate.
    with REFERENCE_OUT.open("r", encoding="utf-8") as f:
        ref_fc = json.load(f)
    with target.open("r", encoding="utf-8") as f:
        fc = json.load(f)
    fc["dropped_count"] = ref_fc.get("dropped_count")
    with target.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_under_drop() -> None:
    """Agent dropped only features whose geometry is JSON null and
    missed the empty-LineString defect *and* the null-waterway_type
    rows.

    Effect:
      * 5 empty LineStrings remain (subcheck 1 fails).
      * 5 rows with null waterway_type remain (subcheck 2 fails).
      * dropped_count is reported but wrong (10 instead of 20)
        (subcheck 4 fails).
      * Feature count: 90 vs 80 → 11.1 % over. Subcheck 5 fails.
      * Feature-id set: 90 ids vs 80 → Jaccard ≈ 0.889 (subcheck 6
        fails).
      * The 5 null-name rows survive (subcheck 7 passes).
      * Geometries and attributes match for the common 80 ids
        (subchecks 8 & 9 pass).

    → 4 / 9 ≈ 0.444.
    """
    out_dir = HERE / "broken_under_drop" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME

    # Read the raw input as JSON so we preserve the empty-LineString
    # geometries verbatim (gpd would coerce them on write).
    with INPUT_RAW.open("r", encoding="utf-8") as f:
        in_fc = json.load(f)

    kept = []
    for feat in in_fc["features"]:
        # Drop only features whose geometry is JSON null. Empty
        # LineStrings and null waterway_type rows pass through.
        if feat["geometry"] is None:
            continue
        kept.append(feat)

    out_fc = {
        "type": "FeatureCollection",
        "name": "waterways_clean",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": kept,
        "dropped_count": len(in_fc["features"]) - len(kept),
    }
    if target.exists():
        target.unlink()
    with target.open("w", encoding="utf-8") as f:
        json.dump(out_fc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_wrong_geometry() -> None:
    """Agent ran the cleanup correctly (right rows kept, dropped_count
    correct) but every kept LineString has been shifted by ~ 0.01° in
    lon / lat — the kind of drift a stray reprojection round-trip would
    introduce.

    Only `geometry_preserved_per_id` (subcheck 8) fails. → 8 / 9 ≈ 0.889.
    """
    out_dir = HERE / "broken_wrong_geometry" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME

    gdf = gpd.read_file(REFERENCE_OUT)
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.translate(xoff=0.01, yoff=0.01)
    if target.exists():
        target.unlink()
    gdf.to_file(target, driver="GeoJSON")

    # Re-inject the dropped_count foreign member to match the
    # reference; the only failure mode this broken solution exhibits
    # is the per-id geometry shift.
    with REFERENCE_OUT.open("r", encoding="utf-8") as f:
        ref_fc = json.load(f)
    with target.open("r", encoding="utf-8") as f:
        fc = json.load(f)
    fc["dropped_count"] = ref_fc.get("dropped_count")
    with target.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    make_wrong_format()
    make_under_drop()
    make_wrong_geometry()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
