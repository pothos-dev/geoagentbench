"""Authoring-time helper: synthesise the bundled Bangkok air-quality GeoJSON.

Run once at authoring time inside the project's Docker container. The
output `bangkok_aq_stations.geojson` is committed to the repo and served
to systems under test by the harness. Do not run this at grading time.

Why hand-crafted (rather than a slice of an Overture release):

This task is *about* a malformed vendor export — every numeric column is
serialised as a JSON string (e.g. `"sensor_value": "42.7"` rather than
`"sensor_value": 42.7`). Clean upstream sources (Overture, OSM) emit
properly typed numerics, so the bundled file we need to ship is
intentionally an artificial export, not a slice of canonical data.

The inventory anchors the task on the OSM `railway=station` tag family
("air-quality sensors are mounted on Bangkok rail stations"). Overture's
`places.place` does carry transit stations as POIs but does not preserve
the OSM railway-station semantics, and the persona's question is about
sensor readings — not station metadata — so we use a curated list of
real Bangkok BTS / MRT / Airport Rail Link stations as the geographic
anchor and synthesise the per-sensor numeric readings on top.

Hand-crafting is therefore both permitted (AUTHOR_CONTEXT.md >
"intentionally-malformed test files") and the realistic option here.

Determinism: every value is a closed-form function of the row index so
two consecutive runs of this helper produce byte-identical bundled
inputs.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dc-l1-bangkok-attribute-coercion/inputs/_prepare.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "bangkok_aq_stations.geojson"

# Curated list of real Bangkok rail stations (BTS Sukhumvit Line, BTS
# Silom Line, MRT Blue Line, MRT Purple Line, Airport Rail Link). Each
# tuple is (English name, Thai name, lon, lat). Coordinates are
# approximate but anchored to publicly-known station positions.
REAL_STATIONS: tuple[tuple[str, str, float, float], ...] = (
    # BTS Sukhumvit Line (selection)
    ("National Stadium", "สนามกีฬาแห่งชาติ", 100.5294, 13.7464),
    ("Siam", "สยาม", 100.5343, 13.7456),
    ("Chit Lom", "ชิดลม", 100.5436, 13.7441),
    ("Phloen Chit", "เพลินจิต", 100.5485, 13.7434),
    ("Nana", "นานา", 100.5550, 13.7407),
    ("Asok", "อโศก", 100.5604, 13.7373),
    ("Phrom Phong", "พร้อมพงษ์", 100.5694, 13.7305),
    ("Thong Lo", "ทองหล่อ", 100.5780, 13.7240),
    ("Ekkamai", "เอกมัย", 100.5852, 13.7197),
    ("Phra Khanong", "พระโขนง", 100.5916, 13.7152),
    ("On Nut", "อ่อนนุช", 100.6014, 13.7058),
    ("Bang Chak", "บางจาก", 100.6053, 13.6963),
    ("Punnawithi", "ปุณณวิถี", 100.6106, 13.6890),
    ("Udom Suk", "อุดมสุข", 100.6166, 13.6794),
    ("Bang Na", "บางนา", 100.6256, 13.6680),
    ("Bearing", "แบริ่ง", 100.6354, 13.6610),
    # BTS Silom Line (selection)
    ("Ratchadamri", "ราชดำริ", 100.5403, 13.7398),
    ("Sala Daeng", "ศาลาแดง", 100.5345, 13.7286),
    ("Chong Nonsi", "ช่องนนทรี", 100.5293, 13.7235),
    ("Surasak", "สุรศักดิ์", 100.5223, 13.7197),
    ("Saphan Taksin", "สะพานตากสิน", 100.5147, 13.7190),
    # MRT Blue Line (selection)
    ("Hua Lamphong", "หัวลำโพง", 100.5170, 13.7378),
    ("Sam Yan", "สามย่าน", 100.5290, 13.7325),
    ("Si Lom", "สีลม", 100.5346, 13.7290),
    ("Lumphini", "ลุมพินี", 100.5443, 13.7253),
    ("Khlong Toei", "คลองเตย", 100.5545, 13.7223),
    ("Queen Sirikit Centre", "ศูนย์การประชุมแห่งชาติสิริกิติ์", 100.5579, 13.7233),
    ("Sukhumvit", "สุขุมวิท", 100.5604, 13.7378),
    ("Phetchaburi", "เพชรบุรี", 100.5635, 13.7479),
    ("Phra Ram 9", "พระราม 9", 100.5654, 13.7570),
    ("Thailand Cultural Centre", "ศูนย์วัฒนธรรมแห่งประเทศไทย", 100.5701, 13.7665),
    ("Huai Khwang", "ห้วยขวาง", 100.5736, 13.7770),
    ("Sutthisan", "สุทธิสาร", 100.5747, 13.7886),
    ("Ratchadaphisek", "รัชดาภิเษก", 100.5740, 13.7995),
    ("Lat Phrao", "ลาดพร้าว", 100.5740, 13.8062),
    ("Phahon Yothin", "พหลโยธิน", 100.5618, 13.8141),
    ("Chatuchak Park", "สวนจตุจักร", 100.5535, 13.8138),
    ("Kamphaeng Phet", "กำแพงเพชร", 100.5495, 13.8027),
    ("Bang Sue", "บางซื่อ", 100.5365, 13.8027),
    # MRT Purple Line (selection)
    ("Tao Poon", "เตาปูน", 100.5289, 13.8055),
    ("Bang Son", "บางซ่อน", 100.5240, 13.8113),
    ("Wong Sawang", "วงศ์สว่าง", 100.5197, 13.8195),
    ("Bang Phlat", "บางพลัด", 100.5050, 13.7935),
    # Airport Rail Link (selection)
    ("Phaya Thai", "พญาไท", 100.5341, 13.7568),
    ("Ratchaprarop", "ราชปรารภ", 100.5413, 13.7566),
    ("Makkasan", "มักกะสัน", 100.5610, 13.7508),
    ("Ramkhamhaeng", "รามคำแหง", 100.6033, 13.7475),
    ("Hua Mak", "หัวหมาก", 100.6418, 13.7470),
    ("Ban Thap Chang", "บ้านทับช้าง", 100.6657, 13.7463),
    ("Lat Krabang", "ลาดกระบัง", 100.7494, 13.7268),
    ("Suvarnabhumi", "สุวรรณภูมิ", 100.7510, 13.6900),
)

# Total feature count target.
TOTAL_FEATURES = 100


def _sensor_value(idx: int) -> float:
    """Closed-form pseudo-random sensor value in a plausible AQ range.

    Range chosen to look like a generic AQ-sensor "raw count" or PM
    proxy — values from ~10 to ~120 with two decimal places. Formula is
    deterministic in `idx`.
    """
    base = 50.0 + 35.0 * math.sin(idx * 0.31 + 0.7)
    return round(base + 12.0 * math.cos(idx * 0.91), 2)


def _pm25(idx: int) -> float:
    """PM2.5 in µg/m³. Bangkok dry-season values commonly fall in
    15–80 µg/m³; we widen slightly to span seasons.
    """
    base = 35.0 + 22.0 * math.sin(idx * 0.21 + 1.3)
    return round(base + 8.0 * math.cos(idx * 0.71 + 0.4), 1)


def _elevation_m(idx: int) -> float:
    """Bangkok is famously flat — elevations 1–25 m AMSL. We round to one
    decimal so the float-typing subcheck has something to verify.
    """
    return round(2.0 + 18.0 * (math.sin(idx * 0.17) * 0.5 + 0.5), 1)


def _coord_offset(idx: int) -> tuple[float, float]:
    """Small, deterministic perturbation in degrees so synthesised
    sensor sites are not coincident with the anchor station.
    """
    dlon = round(0.0009 * math.sin(idx * 1.13 + 0.2), 6)
    dlat = round(0.0009 * math.cos(idx * 0.87 + 0.5), 6)
    return dlon, dlat


def _make_station(idx: int) -> dict:
    """Build one station feature for `idx` in [0, TOTAL_FEATURES).

    The first `len(REAL_STATIONS)` features use real station names and
    coordinates verbatim; the remainder reuse a real station as anchor
    (cycling through the list) and tag the name with a sensor suffix
    plus a tiny coordinate offset, so every feature is plausibly tied
    to a real rail station. The persona's domain — air-quality sensors
    *mounted on* rail stations — admits multiple sensors per station
    site.
    """
    anchor = REAL_STATIONS[idx % len(REAL_STATIONS)]
    name_en, name_th, lon, lat = anchor
    if idx >= len(REAL_STATIONS):
        # Synthetic per-station sensor index, starting at 2 (sensor 1 is
        # the anchor station itself).
        sensor_no = (idx // len(REAL_STATIONS)) + 1
        name_en = f"{name_en} Sensor {sensor_no}"
        name_th = f"{name_th} เซนเซอร์ {sensor_no}"
        dlon, dlat = _coord_offset(idx)
        lon = round(lon + dlon, 6)
        lat = round(lat + dlat, 6)

    station_id = idx + 1  # 1-based stable integer key

    # The defect we are testing: every numeric value is serialised as a
    # JSON string. The persona's vendor exports it this way.
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat],
        },
        "properties": {
            "station_id": str(station_id),
            "name_th": name_th,
            "name_en": name_en,
            "sensor_value": f"{_sensor_value(idx):.2f}",
            "pm25_ug_m3": f"{_pm25(idx):.1f}",
            "elevation_m": f"{_elevation_m(idx):.1f}",
        },
    }


def main() -> None:
    features = [_make_station(i) for i in range(TOTAL_FEATURES)]

    fc = {
        "type": "FeatureCollection",
        "name": "bangkok_aq_stations",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(features)} stations to {OUT}")
    print("Sample feature 0 properties:", features[0]["properties"])
    print("Sample feature 99 properties:", features[99]["properties"])


if __name__ == "__main__":
    main()
