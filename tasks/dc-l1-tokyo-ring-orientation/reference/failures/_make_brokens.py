"""Generate broken-solution outputs for dc-l1-tokyo-ring-orientation.

Three classes, chosen to give the grader resolution along the
*orientation-awareness* axis (the central skill of the task):

  - broken_wrong_format       — Gate 1 fail (missing required column).
  - broken_wrong_orientation  — agent passed the input through unchanged;
                                exteriors are still CW, interiors still CCW.
  - broken_partial_orientation — agent fixed exteriors but forgot interiors;
                                 RFC 7946 §3.1.6 only half satisfied.

Each broken score range is recorded in metadata.yaml.

Run inside Docker:
    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/dc-l1-tokyo-ring-orientation/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon, mapping
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_buildings_fixed.geojson"
LEGACY_INPUT = TASK_DIR / "inputs" / "tokyo_buildings_legacy.geojson"
OUTPUT_NAME = "tokyo_buildings_fixed.geojson"


def make_wrong_format() -> None:
    """The agent produced GeoJSON in EPSG:4326 with corrected ring
    orientation, but dropped the `overture_id` column on the way out
    (e.g., projected `gdf[["feature_id", "name_primary", "building_class",
    "height", "geometry"]]` before writing).

    Gate 1's required-column check fails. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(REFERENCE_OUT)
    gdf = gdf.drop(columns=["overture_id"])
    target = out_dir / OUTPUT_NAME
    if target.exists():
        target.unlink()
    gdf.to_file(target, driver="GeoJSON")


def make_wrong_orientation() -> None:
    """The agent passed the legacy input through unchanged: exteriors
    are still CW, interior rings still CCW — the bug the persona asked
    to fix is still present.

    Gates pass (file readable, CRS=4326, schema present, Polygon
    geometry, count match). Subchecks: exterior_rings_ccw fails,
    interior_rings_cw fails. The other five pass — orientation is a
    no-op on geometry, so id-set, extent, holes, attributes, and per-id
    geometry are all preserved. → 5/7 ≈ 0.714.
    """
    out_dir = HERE / "broken_wrong_orientation" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    if target.exists():
        target.unlink()
    # The simplest "didn't fix orientation" failure is a verbatim copy of
    # the legacy input under the expected output name. Property values
    # and geometry are unchanged; the file is otherwise valid GeoJSON.
    shutil.copyfile(LEGACY_INPUT, target)


def _flip_exterior_only(geom: Polygon) -> Polygon:
    """Return a Polygon whose exterior ring is CCW but whose interior
    rings are left in their original orientation (still CCW from the
    legacy input — wrong by RFC 7946 §3.1.6, which mandates CW).
    """
    if geom.geom_type != "Polygon":
        return geom
    ext_coords = list(geom.exterior.coords)
    if not geom.exterior.is_ccw:
        ext_coords = list(reversed(ext_coords))
    interior_coords = [list(r.coords) for r in geom.interiors]  # left as-is
    return Polygon(ext_coords, interior_coords)


def make_partial_orientation() -> None:
    """The agent fixed exterior rings (CCW) but did not touch the
    interior rings (still CCW from the legacy input).

    Gates pass. Subchecks: exterior_rings_ccw passes,
    interior_rings_cw fails. Everything else passes (geometry shape is
    untouched, hole count preserved, attributes preserved, per-id IoU
    preserved). → 6/7 ≈ 0.857.
    """
    out_dir = HERE / "broken_partial_orientation" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    if target.exists():
        target.unlink()

    # Read the legacy input (rings are CW exterior, CCW interior).
    gdf = gpd.read_file(LEGACY_INPUT)
    gdf = gdf.sort_values("feature_id", kind="stable").reset_index(drop=True)

    features: list[dict] = []
    for _, row in gdf.iterrows():
        geom = _flip_exterior_only(row.geometry)
        properties = {col: row[col] for col in gdf.columns if col != "geometry"}
        for k, v in list(properties.items()):
            if isinstance(v, float) and v != v:
                properties[k] = None
            elif hasattr(v, "item"):
                properties[k] = v.item()
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": properties,
            }
        )

    fc = {
        "type": "FeatureCollection",
        "name": "tokyo_buildings_fixed",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    with target.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    make_wrong_format()
    make_wrong_orientation()
    make_partial_orientation()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
