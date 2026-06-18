"""Reference solution for fio-l1-vienna-shapefile-recovery.

Reads the bundled CP1252-encoded shapefile (with truncated dBase column
names), restores the original full attribute names from
`column_map.csv`, reprojects geometry from EPSG:31287 (MGI / Austria
Lambert) to EPSG:4326 (WGS84), and writes a single GeoJSON feature
collection.

Determinism: the bundled shapefile is committed with stable row order
(sorted by GRUNDSTUECKSNUMMER); the column rename is a deterministic
dict; geopandas-to-GeoJSON output is byte-identical for fixed input on
a fixed pyogrio version.
"""
from __future__ import annotations

import csv
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
SHP = TASK_DIR / "inputs" / "parcels.shp"
MAP = TASK_DIR / "inputs" / "column_map.csv"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "parcels.geojson"


def _load_column_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["truncated"]] = row["original"]
    return mapping


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    # pyogrio reads the .cpg sidecar automatically and decodes CP1252.
    gdf = gpd.read_file(SHP)

    # Restore the original full attribute names.
    mapping = _load_column_map(MAP)
    gdf = gdf.rename(columns=mapping)

    # Reproject to WGS84.
    gdf = gdf.to_crs("EPSG:4326")

    # Stable row order.
    gdf = gdf.sort_values("GRUNDSTUECKSNUMMER", kind="stable").reset_index(drop=True)

    # Stable column order, geometry last.
    cols = [
        "KATASTRALGEMEINDE_NAME",
        "GRUNDSTUECKSNUMMER",
        "EIGENTUEMER_NAME",
        "WIDMUNG_BEZEICHNUNG",
        "STRASSE_NAME",
        "FLAECHE_M2",
        "geometry",
    ]
    gdf = gdf[cols]

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GeoJSON")

    print(f"Read {len(gdf)} parcels from {SHP.name}")
    print(f"Wrote {OUT}")
    print(f"Sample: {gdf.iloc[0].to_dict()}")


if __name__ == "__main__":
    main()
