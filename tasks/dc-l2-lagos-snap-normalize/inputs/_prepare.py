"""Authoring-time helper: build the bundled Lagos zoning GPKG.

Run once at authoring time inside the project's Docker container. The
output `lagos_zoning_legacy.gpkg` is committed to the repo and served
to systems under test by the harness.

Why hand-crafted rather than Overture-sliced:

The task is *about* a deliberately corrupted zoning snapshot — variant
spellings of the zoning class across six legacy LGA digitisations,
sub-millimetre vertex offsets between adjacent parcels, zero-area
"ghost" polygons from collinear vertices, and blank-class rows from
incomplete data entry. Overture's `base.land_use` ships normalised,
deduplicated polygons with a controlled tag vocabulary; corrupting it
synthetically is identical in effect to constructing the corruption
from scratch, and doing it from scratch keeps every dimension of the
fixture (variant frequency, perturbation magnitude, zero-area count,
blank-class count) under explicit authoring control. This matches the
hand-crafted policy used by `dc-l2-cairo-invalid-dedup`,
`crs-l2-fiji-antimeridian`, and `fio-l2-cairo-mixedgeom-split`.

Determinism:
- All coordinates are closed-form functions of (row, col) on a fixed
  grid in EPSG:26331 metres.
- Variant-spelling cycle, blank-row indices, sub-mm offset pattern,
  and zero-area placements are fixed deterministic functions of the
  parcel index — no random sampling.
- GPKG is written via pyogrio with sorted feature order; the
  `gpkg_contents.last_change` timestamp is overwritten with a fixed
  authoring-date value so two consecutive runs of this helper produce
  byte-identical output.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dc-l2-lagos-snap-normalize/inputs/_prepare.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
OUT = HERE / "lagos_zoning_legacy.gpkg"

FIXED_GPKG_TIMESTAMP = "2026-05-08T00:00:00.000Z"

# Origin in EPSG:26331 (Minna / Nigeria West Belt) metres — anchored to
# a Lagos-Mainland point so the bundled fixture lives in plausible
# real-world coordinates.
ORIGIN_X = 540_000.0
ORIGIN_Y = 720_000.0

# Main grid: 100 rows × 100 cols = 10 000 parcels. Each parcel is a
# 10 m × 10 m square on a 10 m × 10 m grid pitch (perfectly tiled, so
# adjacent parcels share boundaries). Total grid extent 1 000 m × 1 000 m.
N_ROWS = 100
N_COLS = 100
PARCEL_SIDE = 10.0

# The four canonical zoning classes the persona wants. The grid is
# split into four contiguous 50×50 quadrants, one canonical class
# each, so a correct dissolve produces four 500 m × 500 m square
# Polygons (not MultiPolygons or polygons-with-holes).
CANONICAL_CLASSES = ("Residential", "Commercial", "Industrial", "Agricultural")

# Variant-spelling cycle per canonical family. Each parcel's recorded
# `zoning_class` is picked from its canonical family by parcel index
# mod len(family) — every variant in every family is represented at
# roughly equal frequency, so a normaliser that handles only the
# titlecase form fails on ~5/6 of rows.
CLASS_VARIANTS: dict[str, tuple[str, ...]] = {
    "Residential": ("Residential", "RESIDENTIAL", "residential", "Resi.", "resi.", "RESI."),
    "Commercial": ("Commercial", "COMMERCIAL", "commercial", "Comm.", "comm.", "COMM."),
    "Industrial": ("Industrial", "INDUSTRIAL", "industrial", "Indus.", "indus.", "INDUS."),
    "Agricultural": ("Agricultural", "AGRICULTURAL", "agricultural", "Agri.", "agri.", "AGRI."),
}

# Sub-millimetre vertex offsets: parcel (row, col) shifts each of its
# four corners by a tiny per-vertex amount in the [0, 5e-5 m] range
# (≤ 0.05 mm). Adjacent parcels' shared corner gets *different*
# offsets, so a naïve dissolve without snapping produces sliver gaps
# along every shared edge. shapely.set_precision(grid_size=0.001)
# rounds every coordinate to the nearest 1 mm and unifies them.
def _offset(row: int, col: int, vertex: int) -> tuple[float, float]:
    """Deterministic sub-mm offset for parcel (row, col) corner `vertex`."""
    seed = (row * 131 + col * 37 + vertex * 11) % 41
    dx = (seed % 7) * 5e-6  # 0..30 µm
    dy = ((seed // 7) % 6) * 5e-6  # 0..25 µm
    return dx, dy


def _parcel_geometry(row: int, col: int) -> Polygon:
    """Construct a 10 m × 10 m parcel rectangle with sub-mm vertex
    perturbations on each of its four corners.
    """
    x0 = ORIGIN_X + col * PARCEL_SIDE
    y0 = ORIGIN_Y + row * PARCEL_SIDE
    # Corners in CCW order; perturb each by its own offset.
    base_corners = [
        (x0, y0),
        (x0 + PARCEL_SIDE, y0),
        (x0 + PARCEL_SIDE, y0 + PARCEL_SIDE),
        (x0, y0 + PARCEL_SIDE),
    ]
    perturbed = []
    for i, (bx, by) in enumerate(base_corners):
        dx, dy = _offset(row, col, i)
        perturbed.append((bx + dx, by + dy))
    perturbed.append(perturbed[0])  # close the ring
    return orient(Polygon(perturbed), sign=1.0)


def _canonical_for(row: int, col: int) -> str:
    """Quadrant assignment: top-left=Residential, top-right=Commercial,
    bottom-left=Industrial, bottom-right=Agricultural. Each quadrant is
    a contiguous 50×50 block of parcels.
    """
    half = N_ROWS // 2
    if row < half and col < half:
        return "Residential"
    if row < half and col >= half:
        return "Commercial"
    if row >= half and col < half:
        return "Industrial"
    return "Agricultural"


# Blank-class parcel indices inside the main grid, picked at fixed
# positions in each quadrant. After normalisation these rows have a
# blank `zoning_class` and must be filtered out before per-class
# aggregation; because they spatially carve out a hole in their
# quadrant, the agent must filter on the *normalised* class (not on
# the raw variant) before dissolving — otherwise the dissolve picks
# them up under their stray spelling and the per-class polygons end up
# with holes.
#
# Wait — that produces holes in the dissolved quadrant. To keep the
# expected_outputs `Polygon` (not Polygon-with-holes), we instead
# place blank-class rows on a *separate* offset grid that lies outside
# the main 1 000 m × 1 000 m block. Filtering them out leaves the main
# four quadrants untouched. The blank-class strings exercise the
# filter step independently of the dissolve step.
BLANK_OFFSET_X = 2_000.0
BLANK_OFFSET_Y = 0.0
N_BLANK = 50
# Variants of "blank": empty, whitespace, None.
BLANK_VARIANTS: tuple[str | None, ...] = ("", "   ", None, "\t")


def _blank_parcel(seq: int) -> Polygon:
    """Tiny extra parcels in a 10×5 grid east of the main block."""
    row = seq // 10
    col = seq % 10
    x0 = ORIGIN_X + BLANK_OFFSET_X + col * PARCEL_SIDE
    y0 = ORIGIN_Y + BLANK_OFFSET_Y + row * PARCEL_SIDE
    coords = [
        (x0, y0),
        (x0 + PARCEL_SIDE, y0),
        (x0 + PARCEL_SIDE, y0 + PARCEL_SIDE),
        (x0, y0 + PARCEL_SIDE),
        (x0, y0),
    ]
    return orient(Polygon(coords), sign=1.0)


# Zero-area "ghost" polygons: collinear-vertex degenerates that crash
# naïve dissolves. We emit 30 of them, scattered to the south-east of
# the main grid, with stray-but-plausible class labels (so a check
# that filters by class_blank wouldn't catch them — only an explicit
# zero-area filter does). Their geometric area is exactly 0 m².
N_ZERO_AREA = 30
ZERO_OFFSET_X = 2_500.0
ZERO_OFFSET_Y = 500.0


def _zero_area_polygon(seq: int) -> Polygon:
    """Polygon with four collinear vertices on a horizontal segment.
    `Polygon.area` is 0 and shapely treats it as a valid (but
    degenerate) Polygon.
    """
    x0 = ORIGIN_X + ZERO_OFFSET_X + (seq % 10) * 5.0
    y0 = ORIGIN_Y + ZERO_OFFSET_Y + (seq // 10) * 5.0
    # Four collinear points: y is constant. The "ring" closes back on
    # itself, area = 0.
    coords = [
        (x0, y0),
        (x0 + 1.0, y0),
        (x0 + 2.0, y0),
        (x0 + 0.5, y0),
        (x0, y0),
    ]
    return Polygon(coords)


def _stamp_fixed_timestamp(path: Path) -> None:
    """Pin gpkg_contents.last_change for byte-stable output."""
    con = sqlite3.connect(path)
    try:
        con.execute(
            "UPDATE gpkg_contents SET last_change = ?", (FIXED_GPKG_TIMESTAMP,)
        )
        con.commit()
    finally:
        con.close()


def main() -> None:  # pragma: no cover (authoring-time only)
    rows: list[dict] = []
    parcel_id = 0

    # 1. Main grid: 10 000 parcels with sub-mm vertex perturbations and
    #    cycling class-variant spellings.
    for r in range(N_ROWS):
        for c in range(N_COLS):
            parcel_id += 1
            canonical = _canonical_for(r, c)
            family = CLASS_VARIANTS[canonical]
            variant = family[parcel_id % len(family)]
            geom = _parcel_geometry(r, c)
            rows.append(
                {
                    "parcel_id": parcel_id,
                    "lga_source": (
                        "Ikeja", "Surulere", "Yaba", "Apapa", "Eti-Osa", "Ojo"
                    )[parcel_id % 6],
                    "zoning_class": variant,
                    # area_m2 is deliberately stale (carries the nominal
                    # 100.0 even for the perturbed/zero-area rows).
                    "area_m2": 100.0,
                    "geometry": geom,
                }
            )

    # 2. Blank-class parcels (50): offset grid, no canonical class.
    for seq in range(N_BLANK):
        parcel_id += 1
        rows.append(
            {
                "parcel_id": parcel_id,
                "lga_source": "Unassigned",
                "zoning_class": BLANK_VARIANTS[seq % len(BLANK_VARIANTS)],
                "area_m2": 100.0,
                "geometry": _blank_parcel(seq),
            }
        )

    # 3. Zero-area ghosts (30): collinear vertices, plausible class
    #    label, exactly 0 m² shapely area.
    for seq in range(N_ZERO_AREA):
        parcel_id += 1
        # Cycle stray class labels through all four families — these
        # rows must be dropped *before* dissolve, otherwise the
        # dissolve picks up zero-area features under the wrong class.
        canonical = CANONICAL_CLASSES[seq % 4]
        variant = CLASS_VARIANTS[canonical][seq % len(CLASS_VARIANTS[canonical])]
        rows.append(
            {
                "parcel_id": parcel_id,
                "lga_source": "Legacy-Ghost",
                "zoning_class": variant,
                "area_m2": 0.0,
                "geometry": _zero_area_polygon(seq),
            }
        )

    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:26331")
    gdf = gdf.sort_values("parcel_id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GPKG", layer="lagos_zoning_legacy")
    _stamp_fixed_timestamp(OUT)

    print(
        f"Wrote {len(gdf)} features "
        f"({N_ROWS * N_COLS} grid, {N_BLANK} blank-class, "
        f"{N_ZERO_AREA} zero-area) to {OUT}"
    )


if __name__ == "__main__":
    main()
