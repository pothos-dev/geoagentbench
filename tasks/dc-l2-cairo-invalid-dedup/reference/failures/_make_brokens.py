"""Generate broken-solution outputs for dc-l2-cairo-invalid-dedup.

Three classes, chosen to give the grader resolution along the
*operation-completeness* axis:

  - broken_wrong_format      — Gate 1 fails (output written in EPSG:4326
                               instead of EPSG:22992). Score = 0.
  - broken_no_make_valid     — agent ran sliver removal, dedup, MP
                               coercion, area recompute, but skipped
                               shapely.make_valid; the 20 bowtie
                               polygons remain self-intersecting and
                               shapely reports their area as 0, so
                               valid-geometry, no-sliver, and extent
                               subchecks all fail.
  - broken_no_coerce         — agent ran make_valid, dedup, sliver
                               removal, area recompute, but skipped
                               the Polygon → MultiPolygon coercion;
                               only `all_multipolygon` fails.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dc-l2-cairo-invalid-dedup/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
LEGACY_INPUT = TASK_DIR / "inputs" / "cairo_parcels_legacy.geojson"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "parcels_canonical.geoparquet"
OUTPUT_NAME = "parcels_canonical.geoparquet"
SLIVER_AREA_THRESHOLD_M2 = 1.0


def _polygonal_parts_only(geom: BaseGeometry) -> Polygon | MultiPolygon | None:
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return geom
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "GeometryCollection":
        polys: list[Polygon] = []
        for part in geom.geoms:
            if part.is_empty:
                continue
            if part.geom_type == "Polygon":
                polys.append(part)
            elif part.geom_type == "MultiPolygon":
                polys.extend(part.geoms)
        if not polys:
            return None
        return polys[0] if len(polys) == 1 else MultiPolygon(polys)
    return None


def _to_multipolygon(geom: Polygon | MultiPolygon) -> MultiPolygon:
    if geom.geom_type == "MultiPolygon":
        return geom
    return MultiPolygon([geom])


def _read_input() -> gpd.GeoDataFrame:
    return gpd.read_file(LEGACY_INPUT)


def make_wrong_format() -> None:
    """Write the reference output but reproject to EPSG:4326. Gate 1's
    CRS check rejects the file → score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    if target.exists():
        target.unlink()
    gdf = gpd.read_parquet(REFERENCE_OUT).to_crs(4326)
    gdf.to_parquet(target, index=False)


def make_no_make_valid() -> None:
    """Skip shapely.make_valid: the 20 bowtie polygons remain
    self-intersecting in the output. Sliver removal, dedup, MP coercion,
    and area recompute are all done.

    Subcheck outcomes vs reference:
      - all_geometries_valid → fail (190/210 valid)
      - all_multipolygon → pass
      - no_slivers → fail (bowtie shapely.area == 0 < 1 m²)
      - no_exact_duplicate_geometries → pass
      - parcel_id_set_matches_reference → pass
      - area_m2_recomputed → pass (column matches own geometry.area)
      - identifying_attributes_match_reference → pass
      - geometric_extent_preserved → fail (union missing the 20
        bowtie repaired triangles)
    → 5/8 = 0.625.
    """
    out_dir = HERE / "broken_no_make_valid" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    if target.exists():
        target.unlink()

    gdf = _read_input()

    # Drop slivers using the unrepaired geometry's area. (For valid
    # rectangles area is correct; bowties report area 0 and would be
    # dropped here too — to match the broken's behaviour we filter on
    # the *bbox* area instead, the kind of mistake an agent that hasn't
    # made geometries valid might still make. We use envelope.area for
    # the threshold and shapely.area for everything else.)
    gdf = gdf[gdf.geometry.envelope.area >= SLIVER_AREA_THRESHOLD_M2].reset_index(
        drop=True
    )

    # Dedup on WKB.
    gdf = gdf.sort_values("record_seq", kind="stable").reset_index(drop=True)
    gdf["_wkb"] = gdf.geometry.apply(lambda g: g.wkb)
    gdf = gdf.drop_duplicates(subset=["_wkb"], keep="first").drop(columns=["_wkb"])

    # Coerce to MultiPolygon (wrap the still-invalid bowties verbatim —
    # MultiPolygon can hold an invalid polygon part without complaint).
    gdf = gdf.assign(
        geometry=gpd.GeoSeries(
            [_to_multipolygon(g) for g in gdf.geometry], crs=gdf.crs
        )
    )
    # Recompute area_m2 from .area (broken: bowties get 0 here).
    gdf = gdf.assign(area_m2=gdf.geometry.area.round(4))
    gdf = gdf.sort_values("parcel_id", kind="stable").reset_index(drop=True)
    gdf = gdf[
        ["parcel_id", "record_seq", "parcel_class", "district", "area_m2", "geometry"]
    ]
    gdf.to_parquet(target, index=False)


def make_no_coerce() -> None:
    """Skip the Polygon → MultiPolygon coercion: single-part repaired
    parcels stay as Polygon, multipart parcels are MultiPolygon. All
    other operations are correct.

    Subcheck outcomes vs reference:
      - all_geometries_valid → pass
      - all_multipolygon → fail (only 50/210 are MultiPolygon)
      - no_slivers → pass
      - no_exact_duplicate_geometries → pass
      - parcel_id_set_matches_reference → pass
      - area_m2_recomputed → pass
      - identifying_attributes_match_reference → pass
      - geometric_extent_preserved → pass
    → 7/8 = 0.875.
    """
    out_dir = HERE / "broken_no_coerce" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    if target.exists():
        target.unlink()

    gdf = _read_input()

    repaired: list[Polygon | MultiPolygon | None] = []
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            repaired.append(None)
        elif geom.is_valid:
            repaired.append(_polygonal_parts_only(geom))
        else:
            repaired.append(_polygonal_parts_only(make_valid(geom)))
    gdf = gdf.assign(geometry=gpd.GeoSeries(repaired, crs=gdf.crs))
    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].reset_index(drop=True)
    gdf = gdf[gdf.geometry.area >= SLIVER_AREA_THRESHOLD_M2].reset_index(drop=True)
    gdf = gdf.sort_values("record_seq", kind="stable").reset_index(drop=True)
    gdf["_wkb"] = gdf.geometry.apply(lambda g: g.wkb)
    gdf = gdf.drop_duplicates(subset=["_wkb"], keep="first").drop(columns=["_wkb"])

    # NO MultiPolygon coercion here.
    gdf = gdf.assign(area_m2=gdf.geometry.area.round(4))
    gdf = gdf.sort_values("parcel_id", kind="stable").reset_index(drop=True)
    gdf = gdf[
        ["parcel_id", "record_seq", "parcel_class", "district", "area_m2", "geometry"]
    ]
    gdf.to_parquet(target, index=False)


def main() -> None:
    make_wrong_format()
    make_no_make_valid()
    make_no_coerce()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
