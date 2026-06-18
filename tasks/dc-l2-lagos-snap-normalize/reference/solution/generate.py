"""Reference solution for dc-l2-lagos-snap-normalize.

Pipeline:
  1. Read `lagos_zoning_legacy.gpkg` (EPSG:26331, 10 080 polygons:
     10 000 main-grid parcels with sub-mm vertex perturbations and
     variant class spellings, 50 blank-class extras, 30 zero-area
     ghost polygons).
  2. Snap vertices at 1 mm tolerance via shapely.set_precision with
     `grid_size=0.001`. Every coordinate rounds to the nearest
     millimetre, unifying the sub-mm offsets that would otherwise
     produce sliver gaps when adjacent parcels dissolve.
  3. Drop zero-area features (the snapped polygons whose `.area` is
     0 — collinear ghosts and any geometry the snap collapsed to
     null content).
  4. Normalise `zoning_class` to a four-value controlled vocabulary
     (Residential / Commercial / Industrial / Agricultural) by
     stripping whitespace, casefolding, and matching a fixed prefix
     table.
  5. Filter out rows whose normalised class is blank.
  6. Dissolve by canonical class — unary_union per group — and
     recompute `area_m2` from the dissolved polygon's `.area` in
     EPSG:26331 metres.
  7. Sort by `zoning_class` ascending and write GPKG. Pin
     `gpkg_contents.last_change` so two consecutive runs are
     byte-identical.

Determinism: feature ordering is stable (alphabetical class), the
snap operation is a pure coordinate function, the normaliser is a
deterministic prefix table, and the GPKG timestamp is overwritten
post-write with a fixed value.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "lagos_zoning_legacy.gpkg"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "zoning_aggregated.gpkg"

FIXED_GPKG_TIMESTAMP = "2026-05-08T00:00:00.000Z"

SNAP_TOLERANCE_M = 0.001  # 1 mm

CANONICAL_CLASSES = ("Residential", "Commercial", "Industrial", "Agricultural")

# Prefix lookup: a stripped, casefolded zoning_class value matches a
# canonical class iff it starts with the canonical's lowercase prefix.
# `resi`, `residential`, `resi.` all hit "Residential"; `comm`,
# `commercial`, `comm.` hit "Commercial"; etc. Order matters only
# because no canonical's prefix is itself a prefix of another's
# (they share no common stem).
_PREFIX_TABLE: tuple[tuple[str, str], ...] = (
    ("resi", "Residential"),
    ("comm", "Commercial"),
    ("indus", "Industrial"),
    ("ind", "Industrial"),
    ("agri", "Agricultural"),
)


def _normalise_class(raw: object) -> str:
    """Map a raw zoning_class value to one of the four canonical names,
    or to "" for blank / whitespace / None / unknown.
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    key = s.casefold().rstrip(".").rstrip()
    for prefix, canonical in _PREFIX_TABLE:
        if key.startswith(prefix):
            return canonical
    return ""


def _stamp_fixed_timestamp(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            "UPDATE gpkg_contents SET last_change = ?", (FIXED_GPKG_TIMESTAMP,)
        )
        con.commit()
    finally:
        con.close()


def _is_polygonal(geom: BaseGeometry | None) -> bool:
    return (
        geom is not None
        and not geom.is_empty
        and geom.geom_type in ("Polygon", "MultiPolygon")
    )


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)
    if gdf.crs is None or gdf.crs.to_epsg() != 26331:
        raise RuntimeError(f"Expected EPSG:26331 input, got {gdf.crs}")

    # 1. Snap vertices at 1 mm.
    snapped = shapely.set_precision(
        gdf.geometry.values, grid_size=SNAP_TOLERANCE_M
    )
    gdf = gdf.assign(geometry=gpd.GeoSeries(snapped, crs=gdf.crs))

    # 2. Drop zero-area / null / non-polygonal features.
    polygonal = gdf.geometry.apply(_is_polygonal)
    gdf = gdf[polygonal & (gdf.geometry.area > 0)].reset_index(drop=True)

    # 3. Normalise zoning_class.
    gdf = gdf.assign(zoning_class=gdf["zoning_class"].map(_normalise_class))

    # 4. Filter out blank-class rows.
    gdf = gdf[gdf["zoning_class"].astype(str).str.len() > 0].reset_index(drop=True)

    # 5. Dissolve per canonical class via unary_union; recompute area.
    out_rows: list[dict] = []
    for canonical in sorted(CANONICAL_CLASSES):
        sub = gdf[gdf["zoning_class"] == canonical]
        if sub.empty:
            continue
        merged = unary_union(sub.geometry.tolist())
        out_rows.append(
            {
                "zoning_class": canonical,
                "area_m2": float(merged.area),
                "geometry": merged,
            }
        )

    out = gpd.GeoDataFrame(
        pd.DataFrame(out_rows), geometry="geometry", crs=gdf.crs
    )
    out = out.sort_values("zoning_class", kind="stable").reset_index(drop=True)
    out["area_m2"] = out["area_m2"].astype(float).round(4)

    if OUT.exists():
        OUT.unlink()
    out.to_file(OUT, driver="GPKG", layer="zoning_aggregated")
    _stamp_fixed_timestamp(OUT)

    print(f"Wrote {len(out)} per-class rows to {OUT}")
    print(out[["zoning_class", "area_m2"]].to_string(index=False))
    print("Geometry types:", sorted(out.geometry.geom_type.unique()))


if __name__ == "__main__":
    main()
