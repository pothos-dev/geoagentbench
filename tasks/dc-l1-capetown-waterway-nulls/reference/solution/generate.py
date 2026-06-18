"""Reference solution for dc-l1-capetown-waterway-nulls.

Reads the bundled contractor-style waterways GeoJSON, drops every
feature whose geometry is null or empty, drops every feature whose
required `waterway_type` attribute is null, sorts the survivors by
`feature_id`, and writes the cleaned GeoJSON back in EPSG:4326. The
output FeatureCollection carries a `dropped_count` foreign member at
the top level so the persona can audit the contractor.

Determinism: the input is a fully bundled fixture, the cleaning rules
are deterministic, features are sorted by `feature_id` (ascending)
before serialisation, and the dropped-count foreign member is injected
via a json round-trip with stable formatting. Two consecutive runs
produce byte-identical output.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "capetown_waterways.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "waterways_clean.geojson"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)
    total_in = len(gdf)

    geom_ok = ~(gdf.geometry.isna() | gdf.geometry.is_empty)
    type_ok = gdf["waterway_type"].notna()
    keep = geom_ok & type_ok

    cleaned = gdf.loc[keep].copy()
    cleaned = cleaned.sort_values("feature_id", kind="stable").reset_index(drop=True)

    dropped_count = int(total_in - len(cleaned))

    if OUT.exists():
        OUT.unlink()
    cleaned.to_file(OUT, driver="GeoJSON")

    # Inject the `dropped_count` foreign member at the top level of the
    # FeatureCollection. pyogrio's GeoJSON driver does not write foreign
    # members, so we re-serialise the file with a stable formatting.
    with OUT.open("r", encoding="utf-8") as f:
        fc = json.load(f)
    fc["dropped_count"] = dropped_count
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Read {total_in} features from {INPUT}")
    print(f"Kept {len(cleaned)}; dropped {dropped_count}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
