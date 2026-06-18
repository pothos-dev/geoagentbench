"""Authoring-time helper: synthesise the bundled waterways GeoJSON.

Run once at authoring time inside the project's Docker container. The
output `capetown_waterways.geojson` is committed to the repo and served
to systems under test by the harness. Do not run this at grading time.

Why hand-crafted (rather than a slice of an Overture release):

This task is *about* a malformed contractor export — features with `null`
geometry, features with empty LineString `coordinates`, and `null` values
in the required `waterway_type` and the optional `name` columns. None of
these defects exist in Overture's clean schema; the file we need to ship
is intentionally an artificial export, not a slice of canonical upstream
data. The inventory also anchors the task on the OSM `waterway=*` tag
family (linear watercourses), which has no clean LineString equivalent
in Overture's `base.water` collection (rivers there are predominantly
polygonal water bodies, not centrelines). Hand-crafting is therefore
both permitted (AUTHOR_CONTEXT.md > "intentionally-malformed test
files") and the realistic option.

Determinism: every value is a closed-form function of the row index so
two consecutive runs of this helper produce byte-identical bundled
inputs.

Run:
    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/dc-l1-capetown-waterway-nulls/inputs/_prepare.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "capetown_waterways.geojson"

# Cape Town municipal bounding box (rounded). All synthetic centrelines
# are placed inside this box. The exact coordinates are not under test
# in this task — only that the agent drops the defective rows and keeps
# everything else.
LON_MIN, LON_MAX = 18.35, 18.70
LAT_MIN, LAT_MAX = -34.10, -33.80

WATERWAY_TYPES = ("stream", "river", "drain", "canal", "ditch")
NAME_STEMS = (
    "Liesbeek", "Black River", "Salt", "Diep", "Eerste", "Lourens",
    "Hout Bay", "Disa", "Sand", "Soet", "Klein Liesbeek", "Kuils",
    "Modder", "Princess Vlei", "Riet", "Schaapen", "Steenbras",
    "Sir Lowry", "Constantia", "Klipfontein", "Plumstead", "Camps Bay",
    "Bokramspruit", "Mosselbank", "Skoolspruit", "Vergenoegd",
)

# Defect plan — all keyed by feature_id so the layout is reproducible
# and the failure-mode coverage is auditable.
#
#   1– 5  : geometry is JSON `null`             → drop
#   6–10  : geometry is `{"type": "LineString", "coordinates": []}` → drop
#  11–15  : geometry is JSON `null` AND `waterway_type` is null  → drop
#  16–20  : geometry valid but `waterway_type` is null  → drop
#  21–25  : geometry valid, `waterway_type` valid, `name` is null → KEEP
#  26–100 : fully clean                                          → KEEP
#
# Reference therefore drops 20 rows and keeps 80 (of which 5 have a
# null `name`, since the persona's drop predicate is on geometry +
# waterway_type only, not on name).

NULL_GEOM_IDS = set(range(1, 6))
EMPTY_GEOM_IDS = set(range(6, 11))
NULL_GEOM_AND_TYPE_IDS = set(range(11, 16))
NULL_TYPE_ONLY_IDS = set(range(16, 21))
NULL_NAME_ONLY_IDS = set(range(21, 26))
TOTAL_FEATURES = 100


def _coord_pair(idx: int, offset: float) -> tuple[float, float]:
    """Closed-form pseudo-random lon/lat inside the Cape Town bbox.

    Two trigonometric series ensure each feature gets distinct, plausible
    coordinates without invoking any RNG (so the file is bit-stable).
    """
    span_lon = LON_MAX - LON_MIN
    span_lat = LAT_MAX - LAT_MIN
    # Two unrelated frequencies → quasi-random spread over the bbox.
    u = (math.sin(idx * 1.31 + offset * 0.7) * 0.5 + 0.5)
    v = (math.cos(idx * 0.97 + offset * 1.1) * 0.5 + 0.5)
    lon = round(LON_MIN + u * span_lon, 6)
    lat = round(LAT_MIN + v * span_lat, 6)
    return lon, lat


def _linestring_coords(idx: int) -> list[list[float]]:
    """A 3-vertex centreline path for feature `idx`."""
    return [
        list(_coord_pair(idx, 0.0)),
        list(_coord_pair(idx, 0.4)),
        list(_coord_pair(idx, 0.9)),
    ]


def _name(idx: int) -> str:
    stem = NAME_STEMS[idx % len(NAME_STEMS)]
    return f"{stem} {('River' if idx % 3 == 0 else 'Stream')}"


def _waterway_type(idx: int) -> str:
    return WATERWAY_TYPES[idx % len(WATERWAY_TYPES)]


def main() -> None:
    features = []
    for fid in range(1, TOTAL_FEATURES + 1):
        # Geometry slot.
        if fid in NULL_GEOM_IDS or fid in NULL_GEOM_AND_TYPE_IDS:
            geometry: dict | None = None
        elif fid in EMPTY_GEOM_IDS:
            geometry = {"type": "LineString", "coordinates": []}
        else:
            geometry = {
                "type": "LineString",
                "coordinates": _linestring_coords(fid),
            }

        # Attribute slots.
        if fid in NULL_TYPE_ONLY_IDS or fid in NULL_GEOM_AND_TYPE_IDS:
            waterway_type: str | None = None
        else:
            waterway_type = _waterway_type(fid)

        if fid in NULL_NAME_ONLY_IDS:
            name: str | None = None
        else:
            name = _name(fid)

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "feature_id": fid,
                    "name": name,
                    "waterway_type": waterway_type,
                },
            }
        )

    fc = {
        "type": "FeatureCollection",
        "name": "capetown_waterways",
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
    print(f"Wrote {len(features)} features to {OUT}")
    print(
        f"Defect breakdown: "
        f"null_geom={len(NULL_GEOM_IDS)}, "
        f"empty_geom={len(EMPTY_GEOM_IDS)}, "
        f"null_geom_and_type={len(NULL_GEOM_AND_TYPE_IDS)}, "
        f"null_type_only={len(NULL_TYPE_ONLY_IDS)}, "
        f"null_name_only={len(NULL_NAME_ONLY_IDS)}"
    )


if __name__ == "__main__":
    main()
