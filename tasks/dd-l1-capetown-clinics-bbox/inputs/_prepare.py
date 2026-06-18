"""Authoring-time helper: synthesise the bundled clinic-inventory CSV.

Run once at authoring time inside the project's Docker container. The
output `capetown_clinics.csv` is committed to the repo and served to
systems under test by the harness. Do not run this at grading time.

Why hand-crafted (rather than a slice of an Overture release):

The inventory anchors this task on the OSM `amenity=clinic` tag family.
Overture's `places.place` collection does not carry a clean
`amenity=clinic` equivalent — clinic-style POIs are scattered across
several health-related categories with inconsistent labelling, and the
Cape Town coverage is too sparse to support a deterministic ~80-row
bundled fixture. The task is *about* CSV-with-WKT parsing + count +
bounding-box + group-by, not about the realism of the underlying point
set; the persona has explicitly handed the agent a legacy CSV export.
AUTHOR_CONTEXT.md permits hand-crafting in this case ("intentionally
artificial test files" + "OSM tag family with no clean Overture
equivalent" both apply). The synthesis is fully deterministic: every
coordinate, name, and subdistrict assignment is a closed-form function
of `clinic_id`, so two consecutive runs of this helper produce a
byte-identical CSV.

Subdistrict layout matches the eight City of Cape Town Metropolitan
Health Services subdistricts (Western, Southern, Tygerberg, Northern,
Eastern, Klipfontein, Mitchells Plain, Khayelitsha). Each subdistrict
gets a hand-picked sub-bbox inside the Cape Town metropolitan area;
clinics are placed deterministically inside that sub-bbox. Counts per
subdistrict are intentionally non-uniform (so an agent that "assumes
equal split" fails the grader).

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l1-capetown-clinics-bbox/inputs/_prepare.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "capetown_clinics.csv"

# Per-subdistrict sub-bboxes (lon_min, lon_max, lat_min, lat_max) — hand-
# picked to roughly match the geographic footprint of each Cape Town
# Metropolitan Health Services subdistrict. The exact polygon outline is
# not under test; we only need each clinic to plausibly sit inside its
# declared subdistrict.
SUBDISTRICTS: list[tuple[str, int, tuple[float, float, float, float]]] = [
    ("Western",         12, (18.380, 18.480, -33.980, -33.880)),
    ("Southern",        12, (18.420, 18.500, -34.080, -33.990)),
    ("Tygerberg",       11, (18.570, 18.680, -33.920, -33.830)),
    ("Northern",        10, (18.580, 18.730, -33.820, -33.700)),
    ("Eastern",         10, (18.700, 18.820, -33.940, -33.830)),
    ("Klipfontein",      9, (18.500, 18.580, -34.000, -33.940)),
    ("Mitchells Plain",  8, (18.580, 18.680, -34.060, -34.000)),
    ("Khayelitsha",      8, (18.650, 18.750, -34.060, -34.000)),
]

# Stems used for clinic names; cycled deterministically by clinic_id.
NAME_STEMS = (
    "Mokoena", "Ndlovu", "Pieterse", "van der Merwe", "Khumalo",
    "Botha", "Naidoo", "Adams", "Hendricks", "Jansen",
    "Mthembu", "Cloete", "September", "October", "Williams",
    "Patel", "Solomons", "du Toit", "Plaatjies", "Mbeki",
)


def _coord(idx: int, span: float, base: float, freq: float, phase: float) -> float:
    """Closed-form pseudo-spread inside [base, base+span]."""
    u = math.sin(idx * freq + phase) * 0.5 + 0.5
    return round(base + u * span, 6)


def main() -> None:
    rows: list[dict[str, str]] = []
    clinic_id = 1
    for sd_name, sd_count, (lon_min, lon_max, lat_min, lat_max) in SUBDISTRICTS:
        for j in range(sd_count):
            lon = _coord(clinic_id, lon_max - lon_min, lon_min, 1.31, 0.7 * j)
            lat = _coord(clinic_id, lat_max - lat_min, lat_min, 0.97, 1.1 * j)
            stem = NAME_STEMS[(clinic_id - 1) % len(NAME_STEMS)]
            name = f"{stem} {sd_name} Clinic"
            rows.append(
                {
                    "clinic_id": str(clinic_id),
                    "name": name,
                    "subdistrict": sd_name,
                    "wkt_geom": f"POINT({lon} {lat})",
                }
            )
            clinic_id += 1

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["clinic_id", "name", "subdistrict", "wkt_geom"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} clinic rows to {OUT}")
    print(
        "Subdistrict counts: "
        + ", ".join(f"{sd}={n}" for sd, n, _ in SUBDISTRICTS)
    )


if __name__ == "__main__":
    main()
