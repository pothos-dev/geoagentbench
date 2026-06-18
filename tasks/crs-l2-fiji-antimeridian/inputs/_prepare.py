"""Authoring-time helper: hand-craft Fiji reef-transect LineStrings.

Hand-crafted (not Overture-derived) because the task is *about* an
RFC 7946 §3.1.9 violation: the input must contain LineStrings whose
longitudes are encoded straight across the ±180° antimeridian rather
than split into a MultiLineString as the spec requires. No real-world
source ships this kind of malformed encoding deliberately, so we
synthesise it deterministically from a fixed seed.

Transects are placed in a Fiji-area bbox spanning ~176°E – -178°E (i.e.
~176° to 182° in continuous east-of-Greenwich coords), latitudes -19°
to -16° (Vanua Levu / Taveuni waters). About 1/3 of transects are
generated to cross the antimeridian; for those, the second endpoint's
longitude is encoded with the *opposite* sign (e.g. 179.5 → -179.5)
so a single LineString purports to span ~359° of longitude. Naive
tools draw such lines as great-circle wraps the long way around the
globe, which is the bug Mereani is asking the agent to fix.

Run inside the project's Docker container:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/crs-l2-fiji-antimeridian/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString

HERE = Path(__file__).resolve().parent
OUT = HERE / "fiji_transects_wgs84.geojson"

# Deterministic synthesis: fix the RNG seed so re-running this script
# produces the same set of transects bit-for-bit.
SEED = 20260508
N_TRANSECTS = 30

# Per-transect attribute pools (small, for realism).
VESSELS = ["Vanua I", "Lomaiviti", "Cakaulevu", "Taveuni II", "Bligh"]
DATES = [
    "2025-08-12",
    "2025-08-13",
    "2025-08-15",
    "2025-08-16",
    "2025-08-19",
    "2025-08-20",
]


def _wrap_pm180(lon: float) -> float:
    """Reduce a continuous east-of-Greenwich longitude to (-180, 180]."""
    while lon > 180.0:
        lon -= 360.0
    while lon <= -180.0:
        lon += 360.0
    return lon


def _make_transect(
    rng: np.random.Generator, *, cross_antimeridian: bool
) -> tuple[LineString, dict]:
    """Build one transect as a LineString in WGS84.

    `cross_antimeridian=True` produces a transect whose start and end
    longitudes lie on opposite sides of ±180°. The intermediate
    coordinates are emitted as continuous east-of-Greenwich values up
    to the crossing and then with their sign flipped (per the §3.1.9
    violation we're testing) — the resulting LineString spans ~359° of
    raw longitude.
    """
    # Latitudes lie in southern Fiji waters.
    lat0 = float(rng.uniform(-18.5, -16.5))
    lat1 = float(rng.uniform(-18.5, -16.5))
    # Number of intermediate vertices (small but >2 so straight-line
    # interpolation is not the only option a SUT can use).
    n_intermediate = int(rng.integers(2, 6))

    if cross_antimeridian:
        # Centre near the antimeridian; place start east, end west of 180.
        lon0_continuous = float(rng.uniform(177.5, 179.5))
        # Continuous end longitude on the *east* side of 180 in the
        # short-way sense — i.e. 180° plus a small offset.
        lon1_continuous = float(rng.uniform(180.5, 182.5))
    else:
        # Either fully east of 180 or fully west; pick one block per
        # transect. Half each, deterministically.
        if rng.random() < 0.5:
            lon0_continuous = float(rng.uniform(176.0, 179.0))
            lon1_continuous = float(rng.uniform(176.0, 179.0))
        else:
            # West-of-antimeridian block: -179 to -176, encoded as
            # negative numbers throughout (no wrap problem).
            lon0_continuous = float(rng.uniform(-179.5, -176.5))
            lon1_continuous = float(rng.uniform(-179.5, -176.5))

    # Linearly interpolate vertices in continuous-longitude space.
    ts = np.linspace(0.0, 1.0, n_intermediate + 2)
    lons_continuous = lon0_continuous + ts * (lon1_continuous - lon0_continuous)
    lats = lat0 + ts * (lat1 - lat0)
    # Add small along-track lat jitter so the transect isn't a perfect
    # straight line (but stays near it).
    jitter = rng.normal(0.0, 0.005, size=lats.shape)
    jitter[0] = 0.0
    jitter[-1] = 0.0
    lats = lats + jitter

    # RFC 7946 §3.1.9 violation: encode each vertex with its longitude
    # naively wrapped to (-180, 180] independently of its neighbours.
    # That is exactly the bug — adjacent vertices on opposite sides of
    # the antimeridian end up encoded as e.g. (179.5, -17) → (-179.5,
    # -17), which a naive renderer interprets as a 359°-long line.
    coords = [
        (_wrap_pm180(float(lon)), float(lat))
        for lon, lat in zip(lons_continuous, lats)
    ]
    geom = LineString(coords)

    crosses_flag = bool(cross_antimeridian)
    attrs = {"crosses_antimeridian_flag": crosses_flag}
    return geom, attrs


def main() -> None:
    rng = np.random.default_rng(SEED)

    rows: list[dict] = []
    geoms: list[LineString] = []

    # First 10: cross antimeridian. Next 20: don't. Order then resorted
    # by transect_id below for output stability.
    for i in range(N_TRANSECTS):
        cross = i < 10
        geom, attrs = _make_transect(rng, cross_antimeridian=cross)
        # Deterministic per-transect attribute selection from the pools.
        vessel = VESSELS[int(rng.integers(0, len(VESSELS)))]
        date = DATES[int(rng.integers(0, len(DATES)))]
        rows.append(
            {
                "transect_id": f"T{i + 1:03d}",
                "vessel": vessel,
                "survey_date": date,
                "crosses_antimeridian_flag": attrs["crosses_antimeridian_flag"],
            }
        )
        geoms.append(geom)

    gdf = gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:4326")
    gdf = gdf.sort_values("transect_id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_file(OUT, driver="GeoJSON")
    print(f"Wrote {len(gdf)} transects to {OUT}")
    print(f"Crossing antimeridian: {int(gdf['crosses_antimeridian_flag'].sum())}")
    print(f"CRS: {gdf.crs}")
    print(f"Bounds: {tuple(round(v, 4) for v in gdf.total_bounds)}")


if __name__ == "__main__":
    main()
