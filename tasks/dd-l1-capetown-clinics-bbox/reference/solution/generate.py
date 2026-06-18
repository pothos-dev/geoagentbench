"""Reference solution for dd-l1-capetown-clinics-bbox.

Reads the bundled CSV-with-WKT clinic export, parses the `wkt_geom`
column as Points in EPSG:4326, and writes a JSON inventory with three
top-level keys: `count`, `bbox` (as `[xmin, ymin, xmax, ymax]`), and
`count_per_subdistrict` (a mapping from subdistrict name to clinic
count).

Determinism: the input is a fully bundled, deterministic fixture; the
operations (count, bbox, group-by) are exact; output keys are written
in a fixed order (`count`, `bbox`, `count_per_subdistrict`) and the
`count_per_subdistrict` mapping is sorted alphabetically by subdistrict
name. Two consecutive runs produce byte-identical output.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "capetown_clinics.csv"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "clinic_inventory.json"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT)
    geom = gpd.GeoSeries.from_wkt(df["wkt_geom"], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(df.drop(columns=["wkt_geom"]), geometry=geom, crs="EPSG:4326")

    count = int(len(gdf))
    xmin, ymin, xmax, ymax = (float(v) for v in gdf.total_bounds)

    counts = (
        gdf.groupby("subdistrict").size().sort_index().to_dict()
    )
    counts = {str(k): int(v) for k, v in counts.items()}

    inventory = {
        "count": count,
        "bbox": [xmin, ymin, xmax, ymax],
        "count_per_subdistrict": counts,
    }

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Read {count} clinics from {INPUT}")
    print(f"bbox: [{xmin}, {ymin}, {xmax}, {ymax}]")
    print(f"Subdistricts: {counts}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
