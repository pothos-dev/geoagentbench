"""Reference solution for dd-l1-vienna-gpkg-manifest.

Walks every layer of the bundled multi-layer GPKG and emits a JSON
list of `{layer_name, crs, geometry_type, feature_count, bbox}`
records. No reprojection: bounds are reported in each layer's
declared CRS (EPSG:31287, MGI / Austria Lambert).

Determinism notes: layers are sorted alphabetically by name; bbox
floats are rounded to two decimals (centimetres), so two consecutive
runs produce a byte-identical manifest.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pyogrio

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "vienna_planning.gpkg"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "manifest.json"

BBOX_DECIMALS = 2


def _layer_record(path: Path, layer_name: str) -> dict:
    info = pyogrio.read_info(path, layer=layer_name)
    gdf = gpd.read_file(path, layer=layer_name)
    xmin, ymin, xmax, ymax = (round(float(v), BBOX_DECIMALS) for v in gdf.total_bounds)
    return {
        "layer_name": layer_name,
        "crs": str(info["crs"]),
        "geometry_type": str(info["geometry_type"]),
        "feature_count": int(info["features"]),
        "bbox": [xmin, ymin, xmax, ymax],
    }


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    layer_names = sorted(pyogrio.list_layers(INPUT)[:, 0].tolist())
    manifest = [_layer_record(INPUT, name) for name in layer_names]

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Read {len(manifest)} layers from {INPUT}")
    for rec in manifest:
        print(
            f"  {rec['layer_name']}: {rec['geometry_type']} "
            f"({rec['feature_count']} features, {rec['crs']})"
        )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
