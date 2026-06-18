"""Reference solution for dc-l1-bangkok-attribute-coercion.

Reads the bundled `bangkok_aq_stations.geojson` (where every numeric
column is serialised as a JSON string), coerces each numeric column to
its proper JSON type, and writes the result back as GeoJSON in
EPSG:4326.

Coercion rules (per inventory and persona):

  - `station_id` → integer
  - `sensor_value` → float
  - `pm25_ug_m3`  → float
  - `elevation_m` → float
  - `name_th`     → string, unchanged (Thai script preserved verbatim)
  - `name_en`     → string, unchanged
  - geometry      → unchanged Point coordinates

Determinism: features are sorted by `station_id` (numeric ascending)
before serialisation; we read the file with stdlib `json` (rather than
GeoPandas) to keep complete control over property order and the
distinction between `int` and `float` in the output, which pyogrio's
GeoJSON driver does not always preserve. Two consecutive runs produce
byte-identical output.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "bangkok_aq_stations.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "bangkok_aq_typed.geojson"

INT_FIELDS = ("station_id",)
FLOAT_FIELDS = ("sensor_value", "pm25_ug_m3", "elevation_m")
STRING_FIELDS = ("name_th", "name_en")
PROPERTY_ORDER = (
    "station_id",
    "name_th",
    "name_en",
    "sensor_value",
    "pm25_ug_m3",
    "elevation_m",
)


def _coerce_properties(props: dict) -> dict:
    """Coerce numeric-as-string properties to int / float; pass strings
    through unchanged.

    Property order in the output dict follows `PROPERTY_ORDER` so the
    serialised GeoJSON is stable across runs.
    """
    out: dict = {}
    for field in PROPERTY_ORDER:
        value = props[field]
        if field in INT_FIELDS:
            out[field] = int(value)
        elif field in FLOAT_FIELDS:
            out[field] = float(value)
        else:  # STRING_FIELDS
            out[field] = value
    return out


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    with INPUT.open("r", encoding="utf-8") as f:
        fc = json.load(f)

    features_in = fc["features"]

    coerced: list[dict] = []
    for feature in features_in:
        new_props = _coerce_properties(feature["properties"])
        coerced.append(
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": new_props,
            }
        )

    coerced.sort(key=lambda feat: feat["properties"]["station_id"])

    out_fc = {
        "type": "FeatureCollection",
        "name": "bangkok_aq_typed",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": coerced,
    }

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(out_fc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(coerced)} features to {OUT}")


if __name__ == "__main__":
    main()
