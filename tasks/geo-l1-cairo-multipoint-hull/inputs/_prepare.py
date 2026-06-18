"""Authoring-time helper: build the bundled Cairo-Metro station inventory.

Hand-crafted GeoJSON with one MultiPoint geometry per station, where the
points are the synthetic street-level entrance coordinates the persona
(Hatem at the Cairo Metro Authority) would have collected over time.
The points are *not* drawn from Overture or OSM — neither source carries
"every entrance to a station, attributed to its parent station" cleanly:
- Overture has no `subway_entrance` analogue.
- OSM has `railway=subway_entrance` nodes but the parent-station link is
  modelled inconsistently (either via `station=*` tag on the node, via a
  `public_transport=stop_area` relation, or not at all). The persona's
  inventory has been curated by hand from years of station surveys.

The helper is deterministic: stations are listed in a fixed order, each
gets a seeded set of 3–5 entrance offsets around a published WGS84
station centre, and the file is sorted by `station_name_en` before
serialisation.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/geo-l1-cairo-multipoint-hull/inputs/_prepare.py
"""
from __future__ import annotations

import random
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPoint

HERE = Path(__file__).resolve().parent
OUT = HERE / "cairo_metro_stations.geojson"

# (en, ar, lon, lat, n_entrances) — 20 real Cairo Metro stations along
# Lines 1 and 2 with approximate WGS84 centre coordinates. Entrance
# counts vary 3–5 per station to give the convex hulls non-trivial shape
# variety (a 3-point hull is a triangle, a 5-point hull may be a
# pentagon if no points are interior).
STATIONS: list[tuple[str, str, float, float, int]] = [
    ("Helwan", "حلوان", 31.3343, 29.8485, 4),
    ("Saad Zaghloul", "سعد زغلول", 31.2488, 30.0376, 3),
    ("Sayeda Zeinab", "السيدة زينب", 31.2390, 30.0294, 4),
    ("Mar Girgis", "مار جرجس", 31.2304, 30.0061, 3),
    ("El Malek El Saleh", "الملك الصالح", 31.2336, 30.0182, 4),
    ("Maadi", "المعادي", 31.2576, 29.9601, 5),
    ("Sadat", "السادات", 31.2356, 30.0444, 5),
    ("Nasser", "عبد الناصر", 31.2434, 30.0532, 4),
    ("Al-Shohadaa", "الشهداء", 31.2473, 30.0625, 5),
    ("Ghamra", "غمرة", 31.2640, 30.0681, 3),
    ("El Demerdash", "الدمرداش", 31.2737, 30.0789, 4),
    ("Manshiet El-Sadr", "منشية الصدر", 31.2872, 30.0784, 3),
    ("Helmeyet El-Zaitoun", "حلمية الزيتون", 31.3029, 30.1116, 3),
    ("Hadayek El-Zaitoun", "حدائق الزيتون", 31.3070, 30.1226, 4),
    ("El-Marg", "المرج", 31.3338, 30.1474, 3),
    ("Cairo University", "جامعة القاهرة", 31.2010, 30.0260, 5),
    ("Dokki", "الدقي", 31.2125, 30.0383, 4),
    ("Opera", "الأوبرا", 31.2244, 30.0418, 3),
    ("Mohamed Naguib", "محمد نجيب", 31.2456, 30.0436, 4),
    ("Attaba", "العتبة", 31.2469, 30.0521, 5),
]

# 1e-3° ≈ 100 m at this latitude — typical street-block radius around a
# metro headhouse, which gives realistic station-box footprints.
OFFSET_DEG = 1.0e-3
SEED = 20260508


def main() -> None:
    rng = random.Random(SEED)
    rows: list[dict] = []
    for en, ar, lon, lat, n in STATIONS:
        # Deterministic offsets: rng.uniform on a per-station basis.
        coords = []
        for _ in range(n):
            dx = rng.uniform(-OFFSET_DEG, OFFSET_DEG)
            dy = rng.uniform(-OFFSET_DEG, OFFSET_DEG)
            coords.append((round(lon + dx, 6), round(lat + dy, 6)))
        # Sort points within each MultiPoint for stable serialisation.
        coords.sort()
        rows.append(
            {
                "station_name_en": en,
                "station_name_ar": ar,
                "geometry": MultiPoint(coords),
            }
        )

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    gdf = gdf.sort_values("station_name_en", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GeoJSON")

    print(f"Wrote {len(gdf)} stations → {OUT}")
    total_pts = sum(len(g.geoms) for g in gdf.geometry)
    print(f"Total entrance points: {total_pts}")


if __name__ == "__main__":
    main()
