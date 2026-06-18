"""Generate broken-solution outputs for crs-l3-tokyo-jgd-crossings.

Three classes, chosen so the grader's three measured scores live in
distinct ranges:

  - broken_wrong_format        — Gate 1 fail. We swap the multi-layer
                                 GPKG for a CSV under the .gpkg name,
                                 so pyogrio cannot list its layers.
                                 Score = 0.

  - broken_unprojected_pipeline — Gate 1 / 2 pass. The agent skipped
                                 the EPSG:4326 -> EPSG:6677
                                 reprojection: every "engineering"
                                 layer is left in WGS84 (degrees) with
                                 CRS metadata stamped 4326, and the
                                 50 m buffer was applied directly to
                                 lat/lon coordinates (so the buffer
                                 disc is ~50 *degrees* across, an
                                 order-of-magnitude geographic
                                 disaster). Density layer is in WGS84
                                 already so it slips through. Six of
                                 the thirteen subchecks fail
                                 (the four CRS subchecks for the
                                 engineering layers, the JGD envelope,
                                 the buffer planar-area sanity check,
                                 and the intersection ceiling). Score
                                 around 0.46.

  - broken_wrong_density_metric — Gate 1 / 2 pass. Engineering layers
                                 are correct, but the agent populated
                                 the public-facing density layer's
                                 ``crossings_per_km2`` column with the
                                 raw crossing *count* (forgot to divide
                                 by area). Schema-shape and CRS
                                 subchecks all pass; only the
                                 rank-correlation and top-5 subchecks
                                 fail because Tokyo's 23 wards vary in
                                 area by an order of magnitude (Ota at
                                 ~100 km^2 vs Taito at ~10 km^2), so
                                 ranking by count flips the top of the
                                 dashboard list. Score around 0.85.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/crs-l3-tokyo-jgd-crossings/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_GPKG = TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_crossings.gpkg"
OUTPUT_NAME = "tokyo_crossings.gpkg"

LAYERS = [
    "wards_jgd",
    "crossing_points",
    "crossing_buffers_50m",
    "buffer_ward_intersection",
    "ward_crossing_density_wgs84",
]


def _reset(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()


def make_wrong_format() -> None:
    """Write a CSV under the .gpkg filename. pyogrio cannot list_layers
    it, so Gate 1 fails immediately and the score collapses to 0.
    """
    target = HERE / "broken_wrong_format" / "outputs" / OUTPUT_NAME
    _reset(target)
    pd.DataFrame(
        {
            "ward_id": [1, 2, 3],
            "ward_name_en": ["A Ward", "B Ward", "C Ward"],
            "crossings_per_km2": [1.0, 2.0, 3.0],
        }
    ).to_csv(target, index=False)


def make_unprojected_pipeline() -> None:
    """Engineering layers in WGS84 (CRS stamped 4326), buffer applied
    in degrees. Walks through the reference layers, rewrites geometry
    in WGS84 with a degree-radius buffer for the 50 m layer, and re-
    derives the intersection in WGS84. Density layer left as-is in
    WGS84.
    """
    target = HERE / "broken_unprojected_pipeline" / "outputs" / OUTPUT_NAME
    _reset(target)

    wards = gpd.read_file(REFERENCE_GPKG, layer="wards_jgd").to_crs("EPSG:4326")
    crossings = gpd.read_file(REFERENCE_GPKG, layer="crossing_points").to_crs(
        "EPSG:4326"
    )
    # Apply a 0.005-degree buffer to the lon/lat geometries. A
    # literal-minded agent who forgets the reprojection might also
    # reach for a "small" radius -- 0.005 in degrees works out to
    # ~550 m at Tokyo's latitude, so the planar-area sanity check
    # still fires (target ~7854 m^2; observed ~950k m^2). We use
    # this rather than radius=50 (the spec value, which would mean
    # 50 degrees of arc in this broken's frame and a 110 MB output)
    # purely to keep the committed broken under a megabyte.
    buffers = crossings.copy()
    buffers["geometry"] = buffers.geometry.buffer(0.005)
    inter_rows = []
    ward_geom_by_id = dict(zip(wards["ward_id"], wards.geometry))
    for _, b in buffers.iterrows():
        wgeom = ward_geom_by_id.get(int(b.ward_id))
        if wgeom is None:
            continue
        clipped = b.geometry.intersection(wgeom)
        if clipped.is_empty:
            continue
        row = b.to_dict()
        row["geometry"] = clipped
        inter_rows.append(row)
    inter = gpd.GeoDataFrame(inter_rows, geometry="geometry", crs="EPSG:4326")

    density = gpd.read_file(REFERENCE_GPKG, layer="ward_crossing_density_wgs84")

    wards.to_file(target, layer="wards_jgd", driver="GPKG")
    crossings.to_file(target, layer="crossing_points", driver="GPKG")
    buffers.to_file(target, layer="crossing_buffers_50m", driver="GPKG")
    inter.to_file(target, layer="buffer_ward_intersection", driver="GPKG")
    density.to_file(target, layer="ward_crossing_density_wgs84", driver="GPKG")


def make_wrong_density_metric() -> None:
    """Engineering layers correct; density column populated with raw
    crossing count instead of count / area_km2.
    """
    target = HERE / "broken_wrong_density_metric" / "outputs" / OUTPUT_NAME
    _reset(target)

    for layer in LAYERS[:-1]:
        gdf = gpd.read_file(REFERENCE_GPKG, layer=layer)
        gdf.to_file(target, layer=layer, driver="GPKG")

    density = gpd.read_file(REFERENCE_GPKG, layer="ward_crossing_density_wgs84")
    # The classic "forgot to divide by area" bug.
    density["crossings_per_km2"] = density["crossing_count"].astype(float)
    density.to_file(target, layer="ward_crossing_density_wgs84", driver="GPKG")


def main() -> None:
    if not REFERENCE_GPKG.exists():
        raise SystemExit(
            f"Reference output {REFERENCE_GPKG} not found. "
            "Run reference/solution/generate.py first."
        )
    make_wrong_format()
    make_unprojected_pipeline()
    make_wrong_density_metric()
    print("Wrote broken solutions:")
    for d in (
        "broken_wrong_format",
        "broken_unprojected_pipeline",
        "broken_wrong_density_metric",
    ):
        print(f"  {HERE / d / 'outputs' / OUTPUT_NAME}")


if __name__ == "__main__":
    main()
