"""Generate broken-solution outputs for fio-l1-paris-kml-pois.

Three illustrative failure modes against the v2 (verified_date) schema:

  * broken_wrong_format       — agent never converted; output is the
                                untouched KML. Gate 1 rejects, score 0.
  * broken_axis_swap          — agent built the right schema, extracted
                                the date, but read KML coordinates as
                                (lat,lon). Only `geometry_preserved_per_name`
                                fails → 5/6 ≈ 0.833.
  * broken_verified_date_missing — agent built the schema and extracted
                                names/categories but left `verified_date`
                                empty. Both `verified_date_iso_format`
                                and `verified_date_values_match` fail
                                → 4/6 ≈ 0.667.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l1-paris-kml-pois/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from shapely.geometry import Point

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_KML = TASK_DIR / "inputs" / "paris_late_night_pois.kml"
OUTPUT_NAME = "paris_pois.geojson"

# Re-use the reference's date extractor so the "right way" stays in one place.
sys.path.insert(0, str(TASK_DIR / "reference" / "solution"))
from generate import extract_verified_date  # noqa: E402


def _ensure(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / OUTPUT_NAME


def _load_layers() -> list[gpd.GeoDataFrame]:
    layer_info = pyogrio.list_layers(INPUT_KML)
    frames = []
    for layer_name, _ in layer_info:
        layer = gpd.read_file(INPUT_KML, layer=layer_name)
        if layer.empty:
            continue
        layer = layer.rename(columns={"Name": "name", "Description": "description"})
        layer["category"] = layer_name
        frames.append(layer)
    return frames


def make_wrong_format() -> None:
    """Agent left the output as KML (just copied the input through).
    Gate 1 rejects (cannot read as GeoJSON, no required columns).
    Score = 0.
    """
    target = _ensure(HERE / "broken_wrong_format" / "outputs")
    if target.exists():
        target.unlink()
    shutil.copyfile(INPUT_KML, target)


def make_axis_swap() -> None:
    """Agent built the right schema, extracted the date, preserved
    categories, but read KML coordinates as (lat,lon) instead of
    (lon,lat). Only `geometry_preserved_per_name` fails.
    Expected score: 5 / 6 ≈ 0.833.
    """
    target = _ensure(HERE / "broken_axis_swap" / "outputs")
    frames = []
    for layer in _load_layers():
        layer["verified_date"] = layer["description"].map(extract_verified_date)
        layer["geometry"] = layer.geometry.map(
            lambda g: Point(g.y, g.x) if g else None
        )
        frames.append(layer[["name", "category", "verified_date", "geometry"]])
    gdf = gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), geometry="geometry", crs="EPSG:4326"
    )
    gdf = gdf.sort_values(["category", "name"], kind="stable").reset_index(drop=True)
    gdf["verified_date"] = gdf["verified_date"].map(
        lambda d: d.isoformat() if d else None
    )
    if target.exists():
        target.unlink()
    gdf.to_file(target, driver="GeoJSON")


def make_verified_date_missing() -> None:
    """Agent built the schema and extracted name/category/geometry but
    never pulled the date out of the HTML — `verified_date` is empty on
    every row. Both `verified_date_iso_format` and
    `verified_date_values_match` fail. Expected score: 4 / 6 ≈ 0.667.
    """
    target = _ensure(HERE / "broken_verified_date_missing" / "outputs")
    frames = []
    for layer in _load_layers():
        layer["verified_date"] = None
        layer["geometry"] = layer.geometry.map(
            lambda g: Point(g.x, g.y) if g else None
        )
        frames.append(layer[["name", "category", "verified_date", "geometry"]])
    gdf = gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), geometry="geometry", crs="EPSG:4326"
    )
    gdf = gdf.sort_values(["category", "name"], kind="stable").reset_index(drop=True)
    if target.exists():
        target.unlink()
    gdf.to_file(target, driver="GeoJSON")


def main() -> None:
    # Clean up the obsolete v1 broken (html_not_stripped) if present.
    legacy = HERE / "broken_html_not_stripped"
    if legacy.exists():
        shutil.rmtree(legacy)

    make_wrong_format()
    make_axis_swap()
    make_verified_date_missing()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
