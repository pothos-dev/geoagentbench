"""Authoring-time helper: build the bundled Cairo parcels GeoJSON.

Run once at authoring time inside the project's Docker container. The
output `cairo_parcels_legacy.geojson` is committed to the repo and
served to systems under test by the harness.

Why hand-crafted rather than Overture-sliced:

The task is *about* a deliberately corrupted parcel snapshot — invalid
self-intersecting rings, exact duplicate geometries with conflicting
metadata, sliver polygons under 1 m², and a Polygon/MultiPolygon mix
that all violate clean-record contracts. Overture's `divisions` and
`buildings` themes ship valid, deduplicated geometry; corrupting them
synthetically is identical in effect to constructing the corruption
from scratch, and doing it from scratch keeps every dimension of the
fixture (counts of each defect class, exact duplication relationships,
sliver areas) under explicit authoring control. This matches the
hand-crafted policy used by `crs-l2-fiji-antimeridian` and
`fio-l2-cairo-mixedgeom-split`.

Determinism:
- All coordinates are closed-form functions of (row, col) on a fixed
  grid in EPSG:22992 metres.
- Corruption indices, duplicate pairings, and sliver placements are
  fixed integer constants, not stochastic samples.
- GeoJSON is written via `json.dump` with stable formatting — pyogrio's
  driver is bypassed so attribute ordering and coordinate-array layout
  are byte-stable.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dc-l2-cairo-invalid-dedup/inputs/_prepare.py
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
OUT = HERE / "cairo_parcels_legacy.geojson"

# Origin in EPSG:22992 (Egypt Red Belt) metres — anchored to a Maadi-area
# point in Cairo so the bundled fixture lives in plausible real-world
# coordinates. All parcels are placed on a grid offset from this origin.
ORIGIN_X = 640_000.0
ORIGIN_Y = 815_000.0

# Grid: 14 rows × 15 cols = 210 parcels, each a 30 m × 40 m rectangle on
# a 50 m × 60 m grid pitch. Total grid extent ~750 m × 840 m.
N_ROWS = 14
N_COLS = 15
PARCEL_W = 30.0
PARCEL_H = 40.0
PITCH_X = 50.0
PITCH_Y = 60.0

# Indices (parcel_id, 1-based) into which we inject self-intersecting
# bowtie rings. shapely.make_valid() repairs each into a MultiPolygon of
# two triangles (a valid 2-part shape).
BOWTIE_IDS: tuple[int, ...] = (
    7, 23, 41, 58, 76, 94, 112, 130, 148, 166, 17, 35, 53, 71, 89,
    107, 125, 143, 161, 179,
)  # 20 invalid

# Indices that should be emitted as a 2-part MultiPolygon (the parcel
# annexes a small detached strip, modelling the real-world case where
# a registry record carries a main parcel + a detached lot).
MULTIPART_IDS: tuple[int, ...] = (
    11, 29, 47, 65, 83, 101, 119, 137, 155, 173,
    14, 32, 50, 68, 86, 104, 122, 140, 158, 176,
    19, 37, 55, 73, 91, 109, 127, 145, 163, 181,
)  # 30 multi-part

# Pairings (clean parcel_id, dup_seq) — the source parcel is
# duplicated with a new parcel_id (DUP_ID_BASE + dup_seq) and a
# *conflicting* `parcel_class` attribute, modelling the legacy provincial
# systems writing the same boundary under two different classifications.
# Sources are picked from clean (non-bowtie, non-multipart) parcels.
DUPLICATE_SOURCE_IDS: tuple[int, ...] = (
    1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 13, 15, 16, 18, 20,
    21, 22, 24, 25, 26, 27, 28, 30, 31, 33, 34, 36, 38, 39, 40,
    42, 43, 44, 45, 46, 48, 49, 51, 52, 54, 56, 57, 59, 60, 61,
    62, 63, 64, 66, 67,
)  # 50 duplicates
DUP_ID_BASE = 900_000

# Sliver polygons: 30 tiny axis-aligned squares with side ≈ 0.7 m
# (area ≈ 0.49 m², well below the 1 m² threshold). Placed on a fixed
# integer offset grid outside the main parcel grid to avoid touching
# real parcels.
N_SLIVERS = 30
SLIVER_ID_BASE = 800_000
SLIVER_SIDE = 0.7


def _row_col(idx: int) -> tuple[int, int]:
    """Map 0-based parcel index → (row, col) on the grid."""
    return idx // N_COLS, idx % N_COLS


def _base_polygon(idx: int) -> Polygon:
    """Construct the canonical (clean, valid) rectangular parcel for
    parcel_id = idx + 1 on the grid.
    """
    row, col = _row_col(idx)
    x0 = ORIGIN_X + col * PITCH_X
    y0 = ORIGIN_Y + row * PITCH_Y
    coords = [
        (x0, y0),
        (x0 + PARCEL_W, y0),
        (x0 + PARCEL_W, y0 + PARCEL_H),
        (x0, y0 + PARCEL_H),
        (x0, y0),
    ]
    return orient(Polygon(coords), sign=1.0)


def _bowtie_polygon(idx: int) -> Polygon:
    """Self-intersecting bowtie: swap two opposite vertices of the
    rectangle so the ring crosses itself once. shapely.make_valid()
    resolves this into a 2-triangle MultiPolygon whose total area is
    smaller than the original rectangle (the two triangles meet at the
    crossing point), but it is *valid*.
    """
    row, col = _row_col(idx)
    x0 = ORIGIN_X + col * PITCH_X
    y0 = ORIGIN_Y + row * PITCH_Y
    # Bowtie ring: lower-left → upper-right → upper-left → lower-right
    # → lower-left. Crosses itself once on the diagonal.
    coords = [
        (x0, y0),
        (x0 + PARCEL_W, y0 + PARCEL_H),
        (x0, y0 + PARCEL_H),
        (x0 + PARCEL_W, y0),
        (x0, y0),
    ]
    return Polygon(coords)


def _multipart_polygon(idx: int) -> MultiPolygon:
    """A two-part MultiPolygon: the main parcel rectangle plus a small
    detached annex 5 m east of the parcel.
    """
    main = _base_polygon(idx)
    row, col = _row_col(idx)
    ax0 = ORIGIN_X + col * PITCH_X + PARCEL_W + 5.0
    ay0 = ORIGIN_Y + row * PITCH_Y + 5.0
    annex = orient(
        Polygon(
            [
                (ax0, ay0),
                (ax0 + 8.0, ay0),
                (ax0 + 8.0, ay0 + 10.0),
                (ax0, ay0 + 10.0),
                (ax0, ay0),
            ]
        ),
        sign=1.0,
    )
    return MultiPolygon([main, annex])


def _sliver_polygon(seq: int) -> Polygon:
    """Tiny square parcel — area ≈ 0.49 m², below the 1 m² threshold."""
    # Place slivers in a 6×5 mini-grid to the south-east of the main
    # parcel grid, at +1100 m / +1100 m offsets.
    row = seq // 6
    col = seq % 6
    x0 = ORIGIN_X + 1_100.0 + col * 5.0
    y0 = ORIGIN_Y + 1_100.0 + row * 5.0
    return orient(
        Polygon(
            [
                (x0, y0),
                (x0 + SLIVER_SIDE, y0),
                (x0 + SLIVER_SIDE, y0 + SLIVER_SIDE),
                (x0, y0 + SLIVER_SIDE),
                (x0, y0),
            ]
        ),
        sign=1.0,
    )


def _classify(parcel_id: int) -> str:
    """Synthetic parcel-class assignment, deterministic in parcel_id."""
    return ("residential", "commercial", "industrial", "agricultural")[
        parcel_id % 4
    ]


def _district(parcel_id: int) -> str:
    """One of three legacy provincial systems, by id mod 3."""
    return ("Cairo-Central", "Giza-East", "Qalyubia-South")[parcel_id % 3]


def _to_geojson_geometry(geom: Polygon | MultiPolygon) -> dict:
    """Serialise via shapely.geometry.mapping with explicit type kept.

    Bowtie polygons are *invalid*; shapely.geometry.mapping still
    produces a structurally valid GeoJSON Polygon for them — the
    self-intersection lives in the coordinate sequence, not in the
    encoding. That is precisely the persona's complaint.
    """
    return mapping(geom)


def main() -> None:  # pragma: no cover (authoring-time only)
    bowtie_set = set(BOWTIE_IDS)
    multipart_set = set(MULTIPART_IDS)
    if bowtie_set & multipart_set:
        raise RuntimeError("Bowtie and multipart parcel id sets overlap.")

    n_total_parcels = N_ROWS * N_COLS
    if n_total_parcels < max(*BOWTIE_IDS, *MULTIPART_IDS, *DUPLICATE_SOURCE_IDS):
        raise RuntimeError(
            f"Grid size {n_total_parcels} too small for fixed corruption ids."
        )

    features: list[dict] = []
    record_seq = 0

    # 1. Base parcels P001..P210, with bowtie / multipart corruption.
    for parcel_id in range(1, n_total_parcels + 1):
        idx = parcel_id - 1
        if parcel_id in bowtie_set:
            geom = _bowtie_polygon(idx)
        elif parcel_id in multipart_set:
            geom = _multipart_polygon(idx)
        else:
            geom = _base_polygon(idx)

        record_seq += 1
        features.append(
            {
                "type": "Feature",
                "geometry": _to_geojson_geometry(geom),
                "properties": {
                    "parcel_id": parcel_id,
                    "record_seq": record_seq,
                    "parcel_class": _classify(parcel_id),
                    "district": _district(parcel_id),
                    # area_m2 is deliberately *stale* (not recomputed)
                    # for parcels we corrupted, to mimic legacy data
                    # where the area cache was written before the bowtie
                    # was introduced. The reference recomputes from
                    # geometry.area after make_valid; the agent must too.
                    "area_m2": round(PARCEL_W * PARCEL_H, 2),
                },
            }
        )

    # 2. Duplicate insertions: same geometry as the source parcel, but
    # different parcel_id, conflicting parcel_class, and a *later*
    # record_seq (so the dedup keep-rule "earliest record" picks the
    # original). These mimic the second-provincial-system entries.
    for dup_seq, source_pid in enumerate(DUPLICATE_SOURCE_IDS, start=1):
        source_idx = source_pid - 1
        # Pick the same geometry the base parcel was emitted with. Since
        # all duplicate sources are clean (non-bowtie, non-multipart by
        # construction), this is just the base rectangle.
        if source_pid in bowtie_set or source_pid in multipart_set:
            raise RuntimeError(
                f"Duplicate source {source_pid} must be a clean parcel."
            )
        geom = _base_polygon(source_idx)

        record_seq += 1
        dup_pid = DUP_ID_BASE + dup_seq
        # Conflicting class: shift by 1 so the dup carries a *different*
        # class than the source. Same parcel — wrong classification on
        # the dup — exactly the "conflicting metadata" defect.
        conflict_class = (
            "residential",
            "commercial",
            "industrial",
            "agricultural",
        )[(source_pid + 1) % 4]
        features.append(
            {
                "type": "Feature",
                "geometry": _to_geojson_geometry(geom),
                "properties": {
                    "parcel_id": dup_pid,
                    "record_seq": record_seq,
                    "parcel_class": conflict_class,
                    "district": _district(dup_pid),
                    "area_m2": round(PARCEL_W * PARCEL_H, 2),
                },
            }
        )

    # 3. Slivers: 30 tiny squares with synthetic parcel_ids. They survive
    # neither make_valid (they are valid already) nor dedup (no
    # duplicates) — only the area-threshold filter removes them.
    for seq in range(N_SLIVERS):
        geom = _sliver_polygon(seq)
        record_seq += 1
        sliver_pid = SLIVER_ID_BASE + seq + 1
        features.append(
            {
                "type": "Feature",
                "geometry": _to_geojson_geometry(geom),
                "properties": {
                    "parcel_id": sliver_pid,
                    "record_seq": record_seq,
                    "parcel_class": "unknown",
                    "district": "border-sliver",
                    "area_m2": round(SLIVER_SIDE * SLIVER_SIDE, 4),
                },
            }
        )

    fc = {
        "type": "FeatureCollection",
        "name": "cairo_parcels_legacy",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::22992"},
        },
        "features": features,
    }

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(
        f"Wrote {len(features)} features "
        f"({n_total_parcels} base, {len(DUPLICATE_SOURCE_IDS)} dups, "
        f"{N_SLIVERS} slivers) to {OUT}"
    )


if __name__ == "__main__":
    main()
