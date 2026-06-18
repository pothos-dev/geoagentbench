"""Authoring-time helper: build the bundled CP1252 shapefile + column map.

Hand-crafts a small Vienna parcel snapshot in EPSG:31287 (MGI / Austria
Lambert) that mimics a 1990s BEV cadastre export:

  * dBase columns are pre-truncated to 10 characters (the Shapefile
    silent limit). Full names are recoverable only from the companion
    `column_map.csv`.
  * Text attributes contain German diacritics (ä, ö, ü, ß, em-dash) and
    are encoded as CP1252. A `.cpg` file declares the encoding so a
    correct reader (pyogrio / fiona / ogr2ogr) will decode it.

This input is hand-crafted (not Overture-derived) because:
  * Overture has no parcel/cadastre theme — the persona's source domain
    has no Overture analogue.
  * The task is *about* the malformed input shape (10-char truncation,
    CP1252 encoding) rather than about real-world feature accuracy.
  * The story explicitly references a 1990s BEV snapshot — historical
    fidelity matters for the persona's voice but the geometric content
    is incidental.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l1-vienna-shapefile-recovery/inputs/_prepare.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import geopandas as gpd
import pyogrio
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
SHP_OUT = HERE / "parcels.shp"
CPG_OUT = HERE / "parcels.cpg"
MAP_OUT = HERE / "column_map.csv"

# Truncated → original full attribute names. The truncated names mirror
# what a 1990s shapefile writer would have produced (first 10 chars of
# each original). FLAECHE_M2 is exactly 10 chars so the "truncation" is
# an identity — kept in the map for completeness.
COLUMN_MAP = [
    ("KATASTRALG", "KATASTRALGEMEINDE_NAME"),
    ("GRUNDSTUEC", "GRUNDSTUECKSNUMMER"),
    ("EIGENTUEME", "EIGENTUEMER_NAME"),
    ("WIDMUNG_BE", "WIDMUNG_BEZEICHNUNG"),
    ("STRASSE_NA", "STRASSE_NAME"),
    ("FLAECHE_M2", "FLAECHE_M2"),
]

# Deterministic per-row vocabulary. All strings carry German diacritics
# or the em-dash so a UTF-8-decoded-as-Latin-1 (or vice versa) read
# produces visibly garbled text.
KATASTRAL_NAMES = [
    "Innere Stadt",
    "Mariahilf",
    "Währing",
    "Döbling",
    "Hütteldorf",
    "Floridsdorf",
    "Brigittenau",
    "Schönbrunn",
]
EIGENTUEMER_NAMES = [
    "Müller GmbH",
    "Bäcker & Söhne KG",
    "Stadt Wien — MA 28",
    "Schönbrunner Bauges. m.b.H.",
    "Großbauer KG",
    "Österreichische Bundesbahnen",
]
WIDMUNG_VALUES = [
    "Wohngebiet",
    "Grünland-Schutzgebiet",
    "Bauland gemischt",
    "Öffentlicher Raum",
    "Bauland Kerngebiet",
]
STRASSE_NAMES = [
    "Mariahilfer Straße",
    "Währinger Gürtel",
    "Schönbrunner Allee",
    "Naschmarkt",
    "Döblinger Hauptstraße",
    "Höfergasse",
    "Bäckerstraße",
]

# Vienna-area MGI/Austria-Lambert anchor (≈ 1st district). Coordinates in
# metres in EPSG:31287.
ANCHOR_X = 625_700.0
ANCHOR_Y = 483_400.0

N_PARCELS = 60
PARCEL_W = 30.0
PARCEL_H = 25.0
GRID_COLS = 10  # 60 parcels = 6 rows x 10 cols


def _build_features() -> gpd.GeoDataFrame:
    rows = []
    geoms = []
    for i in range(N_PARCELS):
        col = i % GRID_COLS
        row = i // GRID_COLS
        # Add a small per-row offset so the parcels aren't a perfect
        # rectangle — mimics a real cadastre with irregular blocks.
        x0 = ANCHOR_X + col * (PARCEL_W + 2.0) + (row * 0.5)
        y0 = ANCHOR_Y + row * (PARCEL_H + 2.0)
        poly = Polygon([
            (x0, y0),
            (x0 + PARCEL_W, y0),
            (x0 + PARCEL_W, y0 + PARCEL_H),
            (x0, y0 + PARCEL_H),
            (x0, y0),
        ])
        # Deterministic attribute selection by index.
        kat = KATASTRAL_NAMES[i % len(KATASTRAL_NAMES)]
        # Parcel number formatted like Austrian cadastre IDs.
        gnr = f"{(i * 7 + 13) % 9999:04d}/{(i % 9) + 1}"
        owner = EIGENTUEMER_NAMES[(i * 3) % len(EIGENTUEMER_NAMES)]
        widmung = WIDMUNG_VALUES[(i * 5) % len(WIDMUNG_VALUES)]
        strasse = STRASSE_NAMES[(i * 11) % len(STRASSE_NAMES)]
        flaeche = round(PARCEL_W * PARCEL_H + (i % 5) * 1.25, 2)

        rows.append({
            "KATASTRALG": kat,
            "GRUNDSTUEC": gnr,
            "EIGENTUEME": owner,
            "WIDMUNG_BE": widmung,
            "STRASSE_NA": strasse,
            "FLAECHE_M2": flaeche,
        })
        geoms.append(poly)

    gdf = gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:31287")
    # Stable row order keyed on the unique parcel id.
    gdf = gdf.sort_values("GRUNDSTUEC", kind="stable").reset_index(drop=True)
    # Lock column order so the dbf schema is identical between runs.
    gdf = gdf[[
        "KATASTRALG", "GRUNDSTUEC", "EIGENTUEME",
        "WIDMUNG_BE", "STRASSE_NA", "FLAECHE_M2", "geometry",
    ]]
    return gdf


def main() -> None:
    gdf = _build_features()
    print(f"Built {len(gdf)} parcels in EPSG:31287")

    # Remove any prior shapefile sidecars before writing.
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        f = HERE / f"parcels.{ext}"
        if f.exists():
            f.unlink()

    # Write CP1252-encoded shapefile via pyogrio. The OGR driver writes
    # the .cpg file automatically when a non-default encoding is set.
    pyogrio.write_dataframe(
        gdf,
        SHP_OUT,
        driver="ESRI Shapefile",
        encoding="CP1252",
    )
    # Defensive: if OGR didn't drop a .cpg, write it ourselves.
    if not CPG_OUT.exists():
        CPG_OUT.write_text("CP1252\n", encoding="ascii")

    # Write the column-name recovery map.
    if MAP_OUT.exists():
        MAP_OUT.unlink()
    with MAP_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["truncated", "original"])
        for trunc, full in COLUMN_MAP:
            writer.writerow([trunc, full])

    print(f"Wrote {SHP_OUT.name} (+ sidecars) and {MAP_OUT.name}")
    print(f"Sample row: {gdf.iloc[0].to_dict()}")


if __name__ == "__main__":
    main()
