"""Reference solution for dd-l2-bangkok-multicrs-audit.

Walks every layer of the bundled multi-layer GPKG and emits a single
audit CSV — one row per layer, with declared CRS, geometry type,
feature count, a sample coordinate (taken from the first feature's
representative point in the layer's own CRS), and the detected text
encoding (`utf-8` vs `latin1-mojibake`).

Encoding heuristic: a layer is flagged `latin1-mojibake` when at
least one non-id text attribute on the first feature, treated as
Latin-1 bytes and re-decoded as UTF-8, yields a string containing
characters in the Thai Unicode block (U+0E00–U+0E7F). This is the
standard signature of a UTF-8→Latin-1→UTF-8 double-decode bug.

Determinism notes:
- Layers are sorted alphabetically by name in the output CSV.
- Sample coordinates are taken from the representative point of the
  first feature after sorting features by `id` (stable lexical sort).
- Coordinates are rounded to 2 decimals (1 cm in metres, ~1 m at the
  equator in degrees).
"""
from __future__ import annotations

import csv
from pathlib import Path

import geopandas as gpd
import pyogrio

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "bangkok_contractor_delivery.gpkg"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "crs_audit.csv"

COORD_DECIMALS = 2
ID_COLUMN_CANDIDATES = ("id", "fid", "ogc_fid")

CSV_FIELDS = (
    "layer_name",
    "declared_crs",
    "geometry_type",
    "feature_count",
    "sample_x",
    "sample_y",
    "encoding_detected",
)


def _detect_encoding(values: list) -> str:
    """Classify a list of attribute strings as utf-8 or latin1-mojibake.

    A value is flagged when its bytes-as-Latin-1 re-decode as valid
    UTF-8 *and* the result contains at least one Thai-block character
    that the original did not. We require the comparison so plain
    ASCII strings never trip the heuristic.
    """
    for v in values:
        if not isinstance(v, str) or not v:
            continue
        try:
            redecoded = v.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if redecoded == v:
            continue
        if any("฀" <= c <= "๿" for c in redecoded):
            return "latin1-mojibake"
    return "utf-8"


def _first_feature(gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
    id_col = next((c for c in ID_COLUMN_CANDIDATES if c in gdf.columns), None)
    if id_col is not None:
        gdf = gdf.sort_values(id_col, kind="stable")
    return gdf.iloc[0]


def _audit_layer(path: Path, layer_name: str) -> dict:
    info = pyogrio.read_info(path, layer=layer_name)
    gdf = gpd.read_file(path, layer=layer_name)

    first = _first_feature(gdf)
    rep = first.geometry.representative_point()
    sample_x = round(float(rep.x), COORD_DECIMALS)
    sample_y = round(float(rep.y), COORD_DECIMALS)

    text_cols = [
        c for c in gdf.columns
        if c != "geometry"
        and c not in ID_COLUMN_CANDIDATES
        and gdf[c].dtype == object
    ]
    sample_values = [first[c] for c in text_cols]
    encoding = _detect_encoding(sample_values)

    return {
        "layer_name": layer_name,
        "declared_crs": str(info["crs"]),
        "geometry_type": str(info["geometry_type"]),
        "feature_count": int(info["features"]),
        "sample_x": sample_x,
        "sample_y": sample_y,
        "encoding_detected": encoding,
    }


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    layer_names = sorted(pyogrio.list_layers(INPUT)[:, 0].tolist())
    rows = [_audit_layer(INPUT, name) for name in layer_names]

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Audited {len(rows)} layers from {INPUT}")
    for r in rows:
        print(
            f"  {r['layer_name']}: {r['geometry_type']} "
            f"({r['feature_count']} feat, {r['declared_crs']}, "
            f"sample=({r['sample_x']}, {r['sample_y']}), "
            f"encoding={r['encoding_detected']})"
        )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
