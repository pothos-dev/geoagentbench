"""Reference solution for dc-l1-tokyo-ring-orientation.

Reads the bundled `tokyo_buildings_legacy.geojson` (whose rings are in
OGC orientation: exterior CW, interior CCW), re-orients every polygon
to RFC 7946 §3.1.6 (exterior CCW, interior CW), preserves every
attribute verbatim, and writes the result as GeoJSON in EPSG:4326.

Determinism: features are sorted by `feature_id` (ascending) before
serialisation; the file is written with `json.dump` rather than
pyogrio's GeoJSON driver so coordinate-array layout is fully under our
control. Two consecutive runs produce byte-identical output.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import mapping
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "tokyo_buildings_legacy.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "tokyo_buildings_fixed.geojson"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)
    gdf = gdf.sort_values("feature_id", kind="stable").reset_index(drop=True)

    features: list[dict] = []
    for _, row in gdf.iterrows():
        geom = orient(row.geometry, sign=1.0)
        properties = {col: row[col] for col in gdf.columns if col != "geometry"}
        # Pandas reads JSON ints as int64, JSON floats as float; height
        # may be NaN where the input had null. Normalise NaN → None for
        # round-trip-clean JSON output.
        for k, v in list(properties.items()):
            if isinstance(v, float) and v != v:  # NaN check
                properties[k] = None
            elif hasattr(v, "item"):  # numpy scalar
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

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(features)} features to {OUT}")


if __name__ == "__main__":
    main()
