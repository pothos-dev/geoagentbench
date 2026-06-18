"""Reference solution for crs-l1-paris-lambert93.

Reads the bundled WGS84 GeoJSON of Paris (Marais) building footprints,
reprojects to EPSG:2154 (RGF93 / Lambert-93), and writes the result as
a GeoPackage. Attributes are passed through unchanged — Camille asked for
the file back with attributes preserved.

Determinism: input is already sorted by `id` at authoring time; we sort
again defensively so two consecutive runs of this script produce
byte-identical output.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "paris_buildings_wgs84.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "paris_buildings_lambert93.gpkg"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)

    gdf = gdf.to_crs("EPSG:2154")

    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GPKG")
    print(f"Wrote {len(gdf)} features to {OUT}")
    print(f"CRS: {gdf.crs.to_epsg()}")
    print(f"Bounds: {tuple(round(v, 2) for v in gdf.total_bounds)}")


if __name__ == "__main__":
    main()
