"""Authoring-time helper: build the bundled mixed-geometry GeoJSON.

Hand-crafts a GeoJSON FeatureCollection in EPSG:4326 carrying ten Cairo
heritage sites. Each site contributes:

  * an enclosure polygon — half the sites have a single Polygon (outer
    walls only), the other half have a MultiPolygon (outer wall + inner
    courtyard or detached annex);
  * one or two axial-street LineStrings;
  * two or three significant Point markers (gateway, mihrab, etc.).

Every feature carries a `site_id` (e.g. `EG-CAI-007`) plus a `feature_kind`
discriminator (`enclosure`, `axial_line`, `marker_*`). Geometries are
intermingled in a single FeatureCollection in the order: enclosure,
lines, then points, walking site-by-site — which is *not* sorted by
geometry type, so a naive read-then-write keeps the mix and the
downstream desktop tool fails.

The file is hand-crafted (not Overture-sliced) on purpose: the task is
about handling a *mixed-geometry single FeatureCollection*, which
Overture's themed parquet does not produce. The shapes are stylised
representations of real Cairo monuments — geographically plausible
within the historic-Cairo bbox (31.245-31.270 E, 30.030-30.060 N) but
not surveyed.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l2-cairo-mixedgeom-split/inputs/_prepare.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "heritage_sites.geojson"


# Stylised Cairo heritage sites. Centroids are inside the historic-Cairo
# bbox; site shapes are small (~80-200 m across) and crafted so a few of
# them have detached annexes (MultiPolygon).
SITES = [
    {
        "site_id": "EG-CAI-001",
        "name_en": "Sultan Hassan Mosque-Madrasa",
        "name_ar": "مسجد ومدرسة السلطان حسن",
        "centroid": (31.2566, 30.0322),
        "multi": False,  # single Polygon enclosure
        "n_lines": 2,
        "n_points": 3,
    },
    {
        "site_id": "EG-CAI-002",
        "name_en": "Al-Rifai Mosque",
        "name_ar": "مسجد الرفاعي",
        "centroid": (31.2576, 30.0330),
        "multi": True,  # outer + detached annex
        "n_lines": 1,
        "n_points": 2,
    },
    {
        "site_id": "EG-CAI-003",
        "name_en": "Ibn Tulun Mosque",
        "name_ar": "مسجد ابن طولون",
        "centroid": (31.2497, 30.0287),
        "multi": True,
        "n_lines": 2,
        "n_points": 3,
    },
    {
        "site_id": "EG-CAI-004",
        "name_en": "Al-Azhar Mosque",
        "name_ar": "الجامع الأزهر",
        "centroid": (31.2624, 30.0459),
        "multi": False,
        "n_lines": 2,
        "n_points": 3,
    },
    {
        "site_id": "EG-CAI-005",
        "name_en": "Al-Hussein Mosque",
        "name_ar": "مسجد الحسين",
        "centroid": (31.2626, 30.0479),
        "multi": False,
        "n_lines": 1,
        "n_points": 2,
    },
    {
        "site_id": "EG-CAI-006",
        "name_en": "Bayt Al-Suhaymi",
        "name_ar": "بيت السحيمي",
        "centroid": (31.2620, 30.0530),
        "multi": True,  # courtyard house + detached stable
        "n_lines": 1,
        "n_points": 3,
    },
    {
        "site_id": "EG-CAI-007",
        "name_en": "Bab Zuwayla",
        "name_ar": "باب زويلة",
        "centroid": (31.2580, 30.0432),
        "multi": False,
        "n_lines": 2,
        "n_points": 2,
    },
    {
        "site_id": "EG-CAI-008",
        "name_en": "Khan el-Khalili",
        "name_ar": "خان الخليلي",
        "centroid": (31.2615, 30.0473),
        "multi": True,  # market + detached caravanserai
        "n_lines": 2,
        "n_points": 3,
    },
    {
        "site_id": "EG-CAI-009",
        "name_en": "Sabil-Kuttab of Katkhuda",
        "name_ar": "سبيل وكتاب عبد الرحمن كتخدا",
        "centroid": (31.2605, 30.0510),
        "multi": False,
        "n_lines": 1,
        "n_points": 2,
    },
    {
        "site_id": "EG-CAI-010",
        "name_en": "Mosque of Al-Hakim",
        "name_ar": "مسجد الحاكم بأمر الله",
        "centroid": (31.2630, 30.0555),
        "multi": True,  # mosque + detached fountain
        "n_lines": 1,
        "n_points": 2,
    },
]

# In approximate degrees: ~1 degree lon = 96 km at 30°N. So 0.001° ≈ 96 m.
# Enclosure half-size ~0.0006° (~60 m). Annex offset ~0.0015° (~150 m).
ENCLOSURE_HALF = 0.0006
ANNEX_OFFSET = 0.0014
ANNEX_HALF = 0.00035
LINE_HALF = 0.0010
MARKER_OFFSET = 0.0004


def _round(v: float) -> float:
    return round(v, 7)


def _polygon_ring(cx: float, cy: float, half: float) -> list[list[float]]:
    """Square ring (closed) centred at (cx,cy)."""
    return [
        [_round(cx - half), _round(cy - half)],
        [_round(cx + half), _round(cy - half)],
        [_round(cx + half), _round(cy + half)],
        [_round(cx - half), _round(cy + half)],
        [_round(cx - half), _round(cy - half)],
    ]


def _enclosure_geom(site: dict) -> dict:
    cx, cy = site["centroid"]
    main_ring = _polygon_ring(cx, cy, ENCLOSURE_HALF)
    if not site["multi"]:
        return {"type": "Polygon", "coordinates": [main_ring]}
    # Detached annex offset to the NE (positive lon, positive lat).
    ax, ay = cx + ANNEX_OFFSET, cy + ANNEX_OFFSET * 0.6
    annex_ring = _polygon_ring(ax, ay, ANNEX_HALF)
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [main_ring],
            [annex_ring],
        ],
    }


def _line_geom(site: dict, idx: int) -> dict:
    """Axial street as a 3-point LineString crossing the centroid."""
    cx, cy = site["centroid"]
    # Axis 0: roughly E-W. Axis 1: roughly N-S, slightly rotated.
    if idx == 0:
        coords = [
            [_round(cx - LINE_HALF), _round(cy - 0.0001)],
            [_round(cx), _round(cy)],
            [_round(cx + LINE_HALF), _round(cy + 0.0001)],
        ]
    else:
        coords = [
            [_round(cx + 0.0001), _round(cy - LINE_HALF)],
            [_round(cx), _round(cy)],
            [_round(cx - 0.0001), _round(cy + LINE_HALF)],
        ]
    return {"type": "LineString", "coordinates": coords}


def _point_geom(site: dict, idx: int) -> dict:
    """Point marker offset around the centroid in a deterministic ring."""
    cx, cy = site["centroid"]
    # 5 deterministic positions around the centroid; we only emit
    # n_points <= 5 of them.
    offsets = [
        (0.0, MARKER_OFFSET),
        (MARKER_OFFSET, 0.0),
        (0.0, -MARKER_OFFSET),
        (-MARKER_OFFSET, 0.0),
        (MARKER_OFFSET * 0.7, MARKER_OFFSET * 0.7),
    ]
    dx, dy = offsets[idx]
    return {
        "type": "Point",
        "coordinates": [_round(cx + dx), _round(cy + dy)],
    }


def main() -> None:
    features: list[dict] = []
    for site in SITES:
        # Enclosure first.
        features.append(
            {
                "type": "Feature",
                "geometry": _enclosure_geom(site),
                "properties": {
                    "site_id": site["site_id"],
                    "feature_kind": "enclosure",
                    "name_en": site["name_en"],
                    "name_ar": site["name_ar"],
                },
            }
        )
        # Axial lines.
        for i in range(site["n_lines"]):
            features.append(
                {
                    "type": "Feature",
                    "geometry": _line_geom(site, i),
                    "properties": {
                        "site_id": site["site_id"],
                        "feature_kind": f"axial_line_{i + 1}",
                        "name_en": site["name_en"],
                        "name_ar": site["name_ar"],
                    },
                }
            )
        # Point markers.
        marker_labels = ["gateway", "mihrab", "minaret", "fountain", "tomb"]
        for i in range(site["n_points"]):
            features.append(
                {
                    "type": "Feature",
                    "geometry": _point_geom(site, i),
                    "properties": {
                        "site_id": site["site_id"],
                        "feature_kind": f"marker_{marker_labels[i]}",
                        "name_en": site["name_en"],
                        "name_ar": site["name_ar"],
                    },
                }
            )

    fc = {
        "type": "FeatureCollection",
        "name": "cairo_heritage_sites",
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

    n_poly = sum(1 for x in features if x["geometry"]["type"] in ("Polygon", "MultiPolygon"))
    n_multi = sum(1 for x in features if x["geometry"]["type"] == "MultiPolygon")
    n_line = sum(1 for x in features if x["geometry"]["type"] == "LineString")
    n_pt = sum(1 for x in features if x["geometry"]["type"] == "Point")
    print(f"Wrote {len(features)} features → {OUT}")
    print(
        f"  polygons: {n_poly} ({n_multi} MultiPolygon), "
        f"lines: {n_line}, points: {n_pt}"
    )


if __name__ == "__main__":
    main()
