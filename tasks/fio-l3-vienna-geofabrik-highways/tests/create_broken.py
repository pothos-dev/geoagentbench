"""Generate broken solutions for fio-l3-vienna-geofabrik-highways.

Run from eval/:
    uv run python tasks/fio-l3-vienna-geofabrik-highways/tests/create_broken.py
"""

from pathlib import Path

import geopandas as gpd

TASK_DIR = Path(__file__).resolve().parent.parent
REF_PATH = TASK_DIR / "reference" / "solution" / "outputs" / "vienna_network.gpkg"
FAILURES_DIR = TASK_DIR / "reference" / "failures"


def _write(gdf_layers: list[tuple[gpd.GeoDataFrame, str]], out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    for i, (gdf, layer) in enumerate(gdf_layers):
        mode = "w" if i == 0 else "a"
        gdf.to_file(out_path, layer=layer, driver="GPKG", mode=mode)
    print(f"Written: {out_path}")


def create_broken_no_pt_layer():
    """Missing pt_routes layer entirely. Should fail Gate 1 → score 0."""
    out_dir = FAILURES_DIR / "broken_no_pt_layer" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    hw = gpd.read_file(REF_PATH, layer="highways")
    _write([(hw, "highways")], out_dir / "vienna_network.gpkg")


def create_broken_wrong_crs():
    """Coordinates actually in EPSG:4326 but CRS metadata stamped as
    EPSG:31287 (agent reprojected name/geometry separately, or just stamped
    the CRS without reprojecting). Passes gates but fails coordinate-range
    and projected-coordinates subchecks → partial score."""
    out_dir = FAILURES_DIR / "broken_wrong_crs" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    hw = gpd.read_file(REF_PATH, layer="highways").to_crs("EPSG:4326")
    pt = gpd.read_file(REF_PATH, layer="pt_routes").to_crs("EPSG:4326")
    # Stamp CRS as 31287 without actually reprojecting
    hw = hw.set_crs("EPSG:31287", allow_override=True)
    pt = pt.set_crs("EPSG:31287", allow_override=True)
    _write([(hw, "highways"), (pt, "pt_routes")], out_dir / "vienna_network.gpkg")


def create_broken_truncated_attrs():
    """Correct structure/CRS but attributes garbled: highway names replaced
    with ASCII transliterations (ü→u), route/operator emptied, diacritics
    stripped. Should pass gates, fail attribute and diacritic subchecks →
    partial score."""
    out_dir = FAILURES_DIR / "broken_truncated_attrs" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    hw = gpd.read_file(REF_PATH, layer="highways")
    pt = gpd.read_file(REF_PATH, layer="pt_routes")

    # Strip German diacritics from highway names
    hw["name"] = (
        hw["name"]
        .fillna("")
        .str.replace("ü", "u", regex=False)
        .str.replace("Ü", "U", regex=False)
        .str.replace("ä", "a", regex=False)
        .str.replace("Ä", "A", regex=False)
        .str.replace("ö", "o", regex=False)
        .str.replace("Ö", "O", regex=False)
        .str.replace("ß", "ss", regex=False)
    )
    # Clear maxspeed and surface columns
    hw["maxspeed"] = ""
    hw["surface"] = ""

    # Clear operator in PT routes
    pt["operator"] = ""
    # Strip diacritics from PT names too
    pt["name"] = (
        pt["name"]
        .fillna("")
        .str.replace("ü", "u", regex=False)
        .str.replace("Ü", "U", regex=False)
        .str.replace("ä", "a", regex=False)
        .str.replace("ö", "o", regex=False)
        .str.replace("ß", "ss", regex=False)
    )

    _write([(hw, "highways"), (pt, "pt_routes")], out_dir / "vienna_network.gpkg")


if __name__ == "__main__":
    create_broken_no_pt_layer()
    create_broken_wrong_crs()
    create_broken_truncated_attrs()
    print("\nAll broken solutions created.")
