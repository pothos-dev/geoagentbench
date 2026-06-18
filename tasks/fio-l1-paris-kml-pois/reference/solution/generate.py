"""Reference solution for fio-l1-paris-kml-pois.

Reads the bundled Google-My-Maps style KML
(`data/paris_late_night_pois.kml`) and writes
`outputs/paris_pois.geojson` — a flat GeoJSON with three preserved
attributes plus an extracted date:

  * `name`          — the Placemark's <name>
  * `category`      — the parent <Folder>'s <name>
  * `verified_date` — the "Dernière vérification : YYYY-MM-DD" date
                      pulled out of the HTML description, as ISO date

The HTML description is a Google-My-Maps info card carrying four lines
(name, category, link, verified date). Three are redundant with the
structural fields or display-only; the only piece worth keeping is the
verification date, which the persona needs as a queryable column to
identify stale entries.

Determinism: layers are read in `pyogrio.list_layers` order which is
the source XML order, rows within each layer are sorted by `name` for
stability, and the final frame is sorted by `(category, name)` before
serialisation.
"""
from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from shapely.geometry import Point

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "paris_late_night_pois.kml"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "paris_pois.geojson"

_TAG_RE = re.compile(r"<[^>]+>")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def extract_verified_date(description_html: str | None) -> date | None:
    """Pull the YYYY-MM-DD date out of a Google-My-Maps HTML blurb."""
    if description_html is None:
        return None
    decoded = html.unescape(_TAG_RE.sub(" ", str(description_html)))
    match = _DATE_RE.search(decoded)
    if not match:
        return None
    return date.fromisoformat(match.group(1))


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    layer_info = pyogrio.list_layers(INPUT)
    frames: list[gpd.GeoDataFrame] = []
    for layer_name, _geom_type in layer_info:
        layer = gpd.read_file(INPUT, layer=layer_name)
        if layer.empty:
            continue
        layer = layer.rename(columns={"Name": "name", "Description": "description"})
        layer["verified_date"] = layer["description"].map(extract_verified_date)
        layer["name"] = layer["name"].fillna("").astype(str)
        layer["category"] = layer_name
        layer["geometry"] = layer.geometry.map(lambda g: Point(g.x, g.y) if g else None)
        frames.append(layer[["name", "category", "verified_date", "geometry"]])

    gdf = gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True),
        geometry="geometry",
        crs="EPSG:4326",
    )

    gdf = gdf.sort_values(["category", "name"], kind="stable").reset_index(drop=True)
    # GeoJSON serialises date objects via str() → ISO-8601 YYYY-MM-DD.
    gdf["verified_date"] = gdf["verified_date"].map(lambda d: d.isoformat() if d else None)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GeoJSON")

    print(f"Read {len(gdf)} placemarks from {INPUT}")
    print(f"Wrote {OUT}")
    print("Sample row:")
    print(gdf.iloc[0].to_dict())


if __name__ == "__main__":
    main()
