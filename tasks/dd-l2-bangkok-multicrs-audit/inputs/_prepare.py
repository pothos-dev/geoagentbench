"""Authoring-time helper: synthesise the multi-layer Bangkok GPKG.

Run once at authoring time inside the project's Docker container. The
output `bangkok_contractor_delivery.gpkg` is committed to the repo and
served to systems under test by the harness.

Why hand-crafted (rather than a slice of an Overture release):

The task is *about* a deliberately defective contractor deliverable —
multiple layers in disagreeing CRSes inside a single GPKG, plus
Latin-1 mojibake on Thai-script labels (the contractor's pipeline
took UTF-8 bytes, decoded them as Latin-1, then re-encoded as UTF-8,
producing the classic ``à¸ªà¸™à¸²à¸¡`` style garbage). Overture and
OSM both ship clean, single-CRS, properly-encoded text, so the
fixture has to be constructed. Hand-crafting also lets us pin every
geometry on a closed-form grid so two consecutive runs of this helper
produce a byte-identical bundled GPKG.

Layer mix (matches the inventory row's "Polygon, LineString, Point
across layers" + "EPSG:24047, EPSG:32647, EPSG:4326 mixed"):

    1. parcels   — Polygon,    EPSG:24047,  4000 features, latin1-mojibake
    2. roads     — LineString, EPSG:32647,  5000 features, latin1-mojibake
    3. markets   — Point,      EPSG:4326,   1000 features, utf-8 (clean)

Total: 10000 features (medium scale, per the inventory row).

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l2-bangkok-multicrs-audit/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
OUT = HERE / "bangkok_contractor_delivery.gpkg"

# Bangkok-area bbox in EPSG:4326 (deg). All synthetic geometry is laid
# out on grids inside this bbox before per-layer reprojection.
LON_MIN, LON_MAX = 100.45, 100.78
LAT_MIN, LAT_MAX = 13.65, 13.85

# A small rotating list of real Thai labels. Cycled deterministically by
# row index so every run produces the same attribute values. The
# Latin-1 mojibake transform is applied at write time on the layers
# that simulate the contractor's broken pipeline.
THAI_PARCEL_NAMES: tuple[str, ...] = (
    "แปลงที่ดิน บางรัก",
    "แปลงที่ดิน ปทุมวัน",
    "แปลงที่ดิน วัฒนา",
    "แปลงที่ดิน คลองเตย",
    "แปลงที่ดิน ดินแดง",
    "แปลงที่ดิน ห้วยขวาง",
    "แปลงที่ดิน พระโขนง",
    "แปลงที่ดิน บางกะปิ",
)
THAI_ROAD_NAMES: tuple[str, ...] = (
    "ถนนสุขุมวิท",
    "ถนนพระราม 4",
    "ถนนพระราม 9",
    "ถนนรัชดาภิเษก",
    "ถนนเพชรบุรี",
    "ถนนสาทร",
    "ถนนสีลม",
    "ถนนวิทยุ",
    "ถนนพหลโยธิน",
    "ถนนลาดพร้าว",
)
THAI_MARKET_NAMES: tuple[str, ...] = (
    "ตลาดนัดจตุจักร",
    "ตลาดอ.ต.ก.",
    "ตลาดคลองเตย",
    "ตลาดสะพานขาว",
    "ตลาดบางรัก",
    "ตลาดน้อย",
    "ตลาดบางกะปิ",
    "ตลาดมีนบุรี",
)


def _to_mojibake(s: str) -> str:
    """Apply the contractor's UTF-8→Latin-1→UTF-8 double-decode bug.

    The visible string after this transform is the Latin-1 reading of
    the original UTF-8 bytes (each Thai 3-byte sequence becomes three
    Latin-1 chars in the Latin-1 supplement block, e.g.
    "ส" → "à¸ª"). Stored as UTF-8 inside the GPKG.
    """
    return s.encode("utf-8").decode("latin-1")


def _build_parcels() -> gpd.GeoDataFrame:
    """4000 small rectangle parcels on a 50×80 grid (4000 features).

    Generated in EPSG:4326 then reprojected to EPSG:24047 (Indian 1975
    / UTM 47N). Names are mojibake-corrupted.
    """
    n_cols, n_rows = 50, 80
    dx = (LON_MAX - LON_MIN) / n_cols
    dy = (LAT_MAX - LAT_MIN) / n_rows
    # Parcels are 80% of pitch in each direction so they don't tile.
    pad_x = dx * 0.1
    pad_y = dy * 0.1

    rows = []
    for r in range(n_rows):
        for c in range(n_cols):
            idx = r * n_cols + c
            x0 = LON_MIN + c * dx + pad_x
            x1 = LON_MIN + (c + 1) * dx - pad_x
            y0 = LAT_MIN + r * dy + pad_y
            y1 = LAT_MIN + (r + 1) * dy - pad_y
            poly = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            name = THAI_PARCEL_NAMES[idx % len(THAI_PARCEL_NAMES)]
            rows.append(
                {
                    "id": f"P{idx:05d}",
                    "name_th": _to_mojibake(name),
                    "owner_class": ["private", "state", "religious"][idx % 3],
                    "geometry": poly,
                }
            )

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf = gdf.to_crs("EPSG:24047")
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    return gdf


def _build_roads() -> gpd.GeoDataFrame:
    """5000 short LineStrings on a 100×50 grid (5000 features).

    Generated in EPSG:4326 then reprojected to EPSG:32647 (WGS84 /
    UTM 47N). OSM-style highway= attribute; Thai names corrupted.
    """
    n_cols, n_rows = 100, 50
    dx = (LON_MAX - LON_MIN) / n_cols
    dy = (LAT_MAX - LAT_MIN) / n_rows

    rows = []
    for r in range(n_rows):
        for c in range(n_cols):
            idx = r * n_cols + c
            x0 = LON_MIN + c * dx
            y0 = LAT_MIN + r * dy
            # Alternate horizontal / vertical short segments.
            if idx % 2 == 0:
                line = LineString([(x0, y0), (x0 + dx * 0.9, y0)])
            else:
                line = LineString([(x0, y0), (x0, y0 + dy * 0.9)])
            name = THAI_ROAD_NAMES[idx % len(THAI_ROAD_NAMES)]
            highway_class = [
                "primary", "secondary", "tertiary", "residential",
                "service",
            ][idx % 5]
            rows.append(
                {
                    "id": f"R{idx:05d}",
                    "name": _to_mojibake(name),
                    "highway": highway_class,
                    "geometry": line,
                }
            )

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf = gdf.to_crs("EPSG:32647")
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    return gdf


def _build_markets() -> gpd.GeoDataFrame:
    """1000 Points on a 50×20 grid (1000 features), kept in EPSG:4326.

    The clean layer in the deliverable: encoding is proper UTF-8.
    """
    n_cols, n_rows = 50, 20
    dx = (LON_MAX - LON_MIN) / n_cols
    dy = (LAT_MAX - LAT_MIN) / n_rows

    rows = []
    for r in range(n_rows):
        for c in range(n_cols):
            idx = r * n_cols + c
            x = LON_MIN + (c + 0.5) * dx
            y = LAT_MIN + (r + 0.5) * dy
            name = THAI_MARKET_NAMES[idx % len(THAI_MARKET_NAMES)]
            rows.append(
                {
                    "id": f"M{idx:05d}",
                    "name_th": name,
                    "kind": ["fresh", "wet", "night"][idx % 3],
                    "geometry": Point(x, y),
                }
            )

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    return gdf


def main() -> None:
    layers = {
        "parcels": _build_parcels(),
        "roads": _build_roads(),
        "markets": _build_markets(),
    }

    if OUT.exists():
        OUT.unlink()

    for name, gdf in layers.items():
        print(f"  {name}: {len(gdf)} features in {gdf.crs.to_string()}")
        gdf.to_file(OUT, driver="GPKG", layer=name)

    print(f"Wrote multi-layer GPKG → {OUT}")


if __name__ == "__main__":
    main()
