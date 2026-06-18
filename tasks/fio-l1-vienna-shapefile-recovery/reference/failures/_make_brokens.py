"""Generate the three broken solutions deterministically from the reference.

  * broken_wrong_format       — writes a Shapefile (parcels.shp) instead
                                of GeoJSON. Gate 1 fails: parcels.geojson
                                is absent. Score 0.
  * broken_truncated_columns  — keeps the dBase truncated names instead
                                of restoring the originals. The full-name
                                subchecks (per-id match) all fail; only
                                geometry passes. Low partial.
  * broken_mojibake_encoding  — reads the .dbf bytes as UTF-8 (ignoring
                                the .cpg) so all CP1252 single-byte
                                diacritics become Mojibake. Diacritics
                                + per-id text subchecks fail; geometry
                                and FLAECHE_M2 still pass. Mid partial.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l1-vienna-shapefile-recovery/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pyogrio

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
SHP = TASK_DIR / "inputs" / "parcels.shp"

WRONG_FORMAT_DIR = HERE / "broken_wrong_format" / "outputs"
TRUNC_DIR = HERE / "broken_truncated_columns" / "outputs"
MOJI_DIR = HERE / "broken_mojibake_encoding" / "outputs"


def _load_correct() -> gpd.GeoDataFrame:
    """Reference-style read: respect .cpg, decode CP1252."""
    return gpd.read_file(SHP)


def _make_wrong_format() -> None:
    WRONG_FORMAT_DIR.mkdir(parents=True, exist_ok=True)
    gdf = _load_correct().to_crs("EPSG:4326")
    # Write as Shapefile under the wrong filename — task expected GeoJSON.
    out = WRONG_FORMAT_DIR / "parcels.shp"
    for ext in ("shp", "shx", "dbf", "prj", "cpg"):
        f = WRONG_FORMAT_DIR / f"parcels.{ext}"
        if f.exists():
            f.unlink()
    pyogrio.write_dataframe(gdf, out, driver="ESRI Shapefile")


def _make_truncated() -> None:
    TRUNC_DIR.mkdir(parents=True, exist_ok=True)
    # Skip the column-rename step entirely; everything else is correct.
    gdf = _load_correct()
    gdf = gdf.to_crs("EPSG:4326")
    gdf = gdf.sort_values("GRUNDSTUEC", kind="stable").reset_index(drop=True)
    out = TRUNC_DIR / "parcels.geojson"
    if out.exists():
        out.unlink()
    gdf.to_file(out, driver="GeoJSON")


def _make_mojibake() -> None:
    MOJI_DIR.mkdir(parents=True, exist_ok=True)
    # Read the shapefile while *forcing* UTF-8 decoding of the dBase
    # bytes — this is what an agent that ignores the .cpg sidecar
    # produces. pyogrio raises on undecodable bytes when decoding strictly,
    # so we read with cp1252 first and then re-encode/re-decode the
    # strings via the latin1↔utf-8 round-trip that produces the same
    # mojibake an actual UTF-8 reader would emit.
    gdf = _load_correct()
    text_cols = [
        "KATASTRALG", "EIGENTUEME", "WIDMUNG_BE", "STRASSE_NA",
    ]

    def _mojibake(s: str) -> str:
        # Encode the correctly-decoded string back to CP1252 raw bytes
        # (what the .dbf actually contains), then mis-decode as latin1
        # — this is the closest deterministic approximation to "agent
        # didn't set encoding=cp1252 and the byte 0xE4 came through as
        # U+00E4 anyway" *plus* the more interesting failure where the
        # multi-byte em-dash 0x97 gets turned into a control codepoint
        # that breaks any downstream tooling looking for "ä" via
        # explicit unicode comparison.
        try:
            raw = s.encode("cp1252")
        except UnicodeEncodeError:
            raw = s.encode("cp1252", errors="replace")
        # Decode as latin1 — this loses the proper diacritic *graphemes*
        # in display only when text is later re-encoded; pure latin1
        # decoding of a cp1252 byte 0xE4 *is* "ä" still. To produce a
        # genuinely Mojibake'd string (the kind a UTF-8 reader produces
        # when fed cp1252 input), decode as utf-8 with replacement.
        return raw.decode("utf-8", errors="replace")

    for c in text_cols:
        gdf[c] = gdf[c].astype(str).map(_mojibake)

    # Restore full column names (this broken's mistake is *encoding*,
    # not column renaming).
    rename_map = {
        "KATASTRALG": "KATASTRALGEMEINDE_NAME",
        "GRUNDSTUEC": "GRUNDSTUECKSNUMMER",
        "EIGENTUEME": "EIGENTUEMER_NAME",
        "WIDMUNG_BE": "WIDMUNG_BEZEICHNUNG",
        "STRASSE_NA": "STRASSE_NAME",
    }
    gdf = gdf.rename(columns=rename_map)
    gdf = gdf.to_crs("EPSG:4326")
    gdf = gdf.sort_values("GRUNDSTUECKSNUMMER", kind="stable").reset_index(drop=True)

    out = MOJI_DIR / "parcels.geojson"
    if out.exists():
        out.unlink()
    gdf.to_file(out, driver="GeoJSON")


def main() -> None:
    _make_wrong_format()
    _make_truncated()
    _make_mojibake()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
