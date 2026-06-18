"""Reference solution for dc-l2-cairo-invalid-dedup.

Pipeline:
  1. Read `cairo_parcels_legacy.geojson` (EPSG:22992, mix of Polygon /
     MultiPolygon, several invalid self-intersecting rings, exact
     duplicate geometries with conflicting attributes, sliver polygons
     under 1 m²).
  2. Repair invalid geometries with shapely.make_valid, then keep only
     polygonal parts (drop any line / point fragments make_valid may
     emit for degenerate inputs).
  3. Drop slivers — features whose repaired geometry has total area
     below 1 m².
  4. Deduplicate exact-equal geometries: group by repaired-geometry WKB,
     keep the row with the lowest `record_seq`, recompute `area_m2`
     from the kept geometry.
  5. Coerce every kept geometry to MultiPolygon for schema consistency.
  6. Sort by `parcel_id` and write GeoParquet (CRS preserved).

Determinism: feature ordering is stable (sort by `parcel_id`), the
group-by uses WKB equality on geometries that are themselves
deterministic functions of the input file, and pyarrow writes the
GeoParquet with a fixed schema. Two consecutive runs produce
byte-identical output.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "cairo_parcels_legacy.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "parcels_canonical.geoparquet"

SLIVER_AREA_THRESHOLD_M2 = 1.0


def _polygonal_parts_only(geom: BaseGeometry) -> Polygon | MultiPolygon | None:
    """Reduce a make_valid result to its polygonal content.

    `make_valid` can emit a GeometryCollection containing lines or
    points alongside polygons (e.g., for a polygon whose ring touches
    itself at a single vertex). Real parcel data should reduce to
    polygonal content; we discard non-polygonal fragments and re-pack
    polygonal parts into a single Polygon or MultiPolygon.
    """
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
    """Promote a single Polygon to a 1-part MultiPolygon."""
    if geom.geom_type == "MultiPolygon":
        return geom
    return MultiPolygon([geom])


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT)
    if gdf.crs is None or gdf.crs.to_epsg() != 22992:
        raise RuntimeError(
            f"Expected EPSG:22992 input, got {gdf.crs}"
        )

    # 1. Repair invalid geometries; drop non-polygonal fragments.
    repaired: list[Polygon | MultiPolygon | None] = []
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            repaired.append(None)
            continue
        if geom.is_valid:
            repaired.append(_polygonal_parts_only(geom))
        else:
            repaired.append(_polygonal_parts_only(make_valid(geom)))
    gdf = gdf.assign(geometry=gpd.GeoSeries(repaired, crs=gdf.crs))
    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].reset_index(
        drop=True
    )

    # 2. Drop slivers below the 1 m² threshold.
    gdf = gdf[gdf.geometry.area >= SLIVER_AREA_THRESHOLD_M2].reset_index(
        drop=True
    )

    # 3. Deduplicate exact-equal geometries on WKB. Sort by record_seq
    #    ascending so the first row in each group is the earliest record.
    gdf = gdf.sort_values("record_seq", kind="stable").reset_index(drop=True)
    gdf["_wkb"] = gdf.geometry.apply(lambda g: g.wkb)
    gdf = gdf.drop_duplicates(subset=["_wkb"], keep="first").drop(
        columns=["_wkb"]
    )

    # 4. Coerce every kept geometry to MultiPolygon.
    gdf = gdf.assign(
        geometry=gpd.GeoSeries(
            [_to_multipolygon(g) for g in gdf.geometry], crs=gdf.crs
        )
    )

    # 5. Recompute area_m2 from the kept geometry.
    gdf = gdf.assign(area_m2=gdf.geometry.area.round(4))

    # 6. Sort by parcel_id and emit canonical column order.
    gdf = gdf.sort_values("parcel_id", kind="stable").reset_index(drop=True)
    gdf = gdf[
        ["parcel_id", "record_seq", "parcel_class", "district", "area_m2", "geometry"]
    ]

    if OUT.exists():
        OUT.unlink()
    gdf.to_parquet(OUT, index=False)
    print(f"Wrote {len(gdf)} canonical parcels to {OUT}")


if __name__ == "__main__":
    main()
