"""Authoring-time helper: build the bundled Lagos land-use + hex-grid GeoJSONs.

Produces two GeoJSON files in EPSG:4326 (the input CRS Adeola's consultancy
ships her data in):

  - `lagos_landuse.geojson` — Polygon land-use features with a synthetic
    `pop_density` attribute (people per km²). Real Overture
    `base.land_use` polygons over greater Lagos plus ~3 000 synthetic
    *sliver* polygons (each < 100 m² in EPSG:26331, the canonical metric
    CRS for Nigeria's West Belt) injected to reproduce the inventory's
    "sliver polygons (overlay artefacts)" data-quality issue. The agent
    must filter slivers by metric area before doing the area-weighted
    aggregation, otherwise their per-km² density values pollute the
    result.

  - `lagos_hex_grid.geojson` — ~1 km flat-topped hex grid over the same
    bbox, generated in EPSG:26331 (so cells are metric-true) and
    reprojected to EPSG:4326 for distribution. Each hex carries a
    stable `hex_id`.

Why Overture: the inventory row pins the source to Overture
`base.land_use`. Lagos has decent Overture land-use coverage (~5-10k
polygons over the metro bbox) — the real polygon count is fine for the
medium scale tier. Population density is **synthetic** (hashed from
the Overture id) so the answer is deterministic and not dependent on
external census data — the task is about the geometric pipeline, not
about Lagos demography.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l2-lagos-hotspot-overlaps/inputs/_prepare.py
"""
from __future__ import annotations

import hashlib
import math
import random
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
LANDUSE_OUT = HERE / "lagos_landuse.geojson"
HEX_OUT = HERE / "lagos_hex_grid.geojson"
RELEASE = "2026-04-15.0"

# Greater Lagos bbox (Lagos Island, Mainland, Lekki, Ikeja, Ikorodu strip).
# Wide enough to land in the medium (~10^4) tier and to make the hex grid
# meaningfully large (~700-1000 cells at 1 km flat-to-flat).
XMIN, YMIN, XMAX, YMAX = 3.25, 6.40, 3.65, 6.65

N_SLIVERS = 3000
SLIVER_MAX_AREA_M2 = 99.0  # strictly under the 100 m² filter threshold
SLIVER_MIN_AREA_M2 = 1.0
HEX_FLAT_TO_FLAT_M = 1000.0  # 1 km hex
SEED = 20260508

POP_DENSITY_LO = 500.0       # people per km²
POP_DENSITY_HI = 50_000.0


# ---------- helpers --------------------------------------------------


def _stable_density(seed_str: str) -> float:
    """Map an arbitrary string to a density in [POP_DENSITY_LO, POP_DENSITY_HI]."""
    h = int(hashlib.sha256(f"density|{seed_str}".encode()).hexdigest(), 16)
    frac = (h % 10_000_000) / 10_000_000
    return round(POP_DENSITY_LO + frac * (POP_DENSITY_HI - POP_DENSITY_LO), 1)


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute(
        """
        CREATE OR REPLACE SECRET overture (
            TYPE s3, PROVIDER config, KEY_ID '', SECRET '',
            REGION 'us-west-2', USE_SSL true, URL_STYLE 'path'
        );
        """
    )
    return con


def fetch_landuse(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    df = con.execute(
        f"""
        SELECT
            id,
            class,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=land_use/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
        """
    ).fetchdf()
    print(f"Fetched {len(df)} land_use rows from Overture {RELEASE}")
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    gdf = gdf[gdf.geometry.geom_type.isin(("Polygon", "MultiPolygon"))].copy()
    # Drop empties / invalid.
    gdf = gdf[~gdf.geometry.is_empty]
    gdf = gdf[gdf.geometry.is_valid].copy()
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    return gdf


def make_slivers_metric(bbox_xy: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Generate N_SLIVERS synthetic tiny triangles inside the metric bbox.

    Each triangle has area in [SLIVER_MIN_AREA_M2, SLIVER_MAX_AREA_M2]
    (strictly under the 100 m² filter threshold).
    """
    rng = random.Random(SEED)
    minx, miny, maxx, maxy = bbox_xy
    triangles = []
    ids = []
    classes = []
    densities = []
    pad = 50.0  # keep slivers a touch inside the bbox interior
    for i in range(N_SLIVERS):
        cx = rng.uniform(minx + pad, maxx - pad)
        cy = rng.uniform(miny + pad, maxy - pad)
        target_area = rng.uniform(SLIVER_MIN_AREA_M2, SLIVER_MAX_AREA_M2)
        # Build a near-equilateral triangle of area `target_area`. For an
        # equilateral triangle of side s: A = (sqrt(3)/4) * s^2 → s=...
        s = math.sqrt(4.0 * target_area / math.sqrt(3.0))
        # Three vertices around the centroid (equilateral, single rotation).
        ang0 = rng.uniform(0.0, 2 * math.pi)
        r = s / math.sqrt(3.0)  # circumradius for equilateral side s
        verts = []
        for k in range(3):
            ang = ang0 + (2 * math.pi * k / 3)
            verts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        poly = Polygon(verts)
        if not poly.is_valid or poly.area <= 0:
            continue
        sid = f"SLIV-{i:05d}"
        triangles.append(poly)
        ids.append(sid)
        classes.append("artefact")
        densities.append(_stable_density(sid))
    gdf = gpd.GeoDataFrame(
        {"id": ids, "class": classes, "pop_density": densities},
        geometry=triangles,
        crs="EPSG:26331",
    )
    return gdf


def build_hex_grid(bbox_xy: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Flat-topped hex grid covering the metric bbox.

    `flat-to-flat` distance = HEX_FLAT_TO_FLAT_M (1 km). Side length
    s = flat_to_flat / sqrt(3). Horizontal column spacing = 1.5 * s,
    vertical row spacing within a column = sqrt(3) * s = flat_to_flat;
    odd columns offset by 0.5 * flat_to_flat.
    """
    minx, miny, maxx, maxy = bbox_xy
    s = HEX_FLAT_TO_FLAT_M / math.sqrt(3.0)
    col_dx = 1.5 * s
    row_dy = HEX_FLAT_TO_FLAT_M

    hexes: list[Polygon] = []
    ids: list[str] = []

    n_cols = int(math.ceil((maxx - minx) / col_dx)) + 2
    n_rows = int(math.ceil((maxy - miny) / row_dy)) + 2
    for c in range(n_cols):
        cx = minx + c * col_dx
        for r in range(n_rows):
            cy = miny + r * row_dy
            if c % 2 == 1:
                cy_eff = cy + row_dy / 2.0
            else:
                cy_eff = cy
            verts = []
            for k in range(6):
                ang = math.radians(60 * k)  # flat-top: vertices at 0°, 60°, ...
                verts.append((cx + s * math.cos(ang), cy_eff + s * math.sin(ang)))
            poly = Polygon(verts)
            # Keep cells whose centroid falls inside the bbox.
            if minx <= cx <= maxx and miny <= cy_eff <= maxy:
                hex_id = f"H{c:03d}-{r:03d}"
                hexes.append(poly)
                ids.append(hex_id)

    gdf = gpd.GeoDataFrame(
        {"hex_id": ids},
        geometry=hexes,
        crs="EPSG:26331",
    )
    gdf = gdf.sort_values("hex_id", kind="stable").reset_index(drop=True)
    return gdf


# ---------- main -----------------------------------------------------


def main() -> None:
    con = _connect()
    landuse_4326 = fetch_landuse(con)

    # Reproject to EPSG:26331 to operate in metres.
    landuse_m = landuse_4326.to_crs("EPSG:26331")

    # Assign synthetic pop_density per real polygon (deterministic on Overture id).
    landuse_m["pop_density"] = landuse_m["id"].map(_stable_density)

    # Determine metric bbox for slivers + hex grid: use bbox of the
    # reprojected real polygons (intersection of the WGS84 bbox with the
    # CRS-reprojection envelope).
    minx, miny, maxx, maxy = landuse_m.total_bounds
    # Round outward slightly so cells cover the rim cleanly.
    minx_b = math.floor(minx / 100.0) * 100.0
    miny_b = math.floor(miny / 100.0) * 100.0
    maxx_b = math.ceil(maxx / 100.0) * 100.0
    maxy_b = math.ceil(maxy / 100.0) * 100.0
    bbox_xy = (minx_b, miny_b, maxx_b, maxy_b)
    print(f"Metric bbox (EPSG:26331) for slivers + hex grid: {bbox_xy}")

    slivers_m = make_slivers_metric(bbox_xy)
    print(
        f"Generated {len(slivers_m)} slivers; area range "
        f"{slivers_m.geometry.area.min():.2f}–"
        f"{slivers_m.geometry.area.max():.2f} m²"
    )

    # Combine real + sliver polygons.
    combined_m = gpd.GeoDataFrame(
        gpd.pd.concat(
            [
                landuse_m[["id", "class", "pop_density", "geometry"]],
                slivers_m[["id", "class", "pop_density", "geometry"]],
            ],
            ignore_index=True,
        ),
        crs="EPSG:26331",
    )
    combined_m = combined_m.sort_values("id", kind="stable").reset_index(drop=True)

    # Build hex grid in the same metric CRS, then reproject for output.
    hex_m = build_hex_grid(bbox_xy)
    print(f"Built hex grid: {len(hex_m)} cells (flat-to-flat = {HEX_FLAT_TO_FLAT_M:.0f} m)")

    # Reproject everything back to EPSG:4326 for distribution as GeoJSON.
    landuse_out = combined_m.to_crs("EPSG:4326")
    hex_out = hex_m.to_crs("EPSG:4326")

    if LANDUSE_OUT.exists():
        LANDUSE_OUT.unlink()
    if HEX_OUT.exists():
        HEX_OUT.unlink()

    # GeoJSON via pyogrio with sorted IDs for deterministic file bytes.
    landuse_out.to_file(LANDUSE_OUT, driver="GeoJSON")
    hex_out.to_file(HEX_OUT, driver="GeoJSON")
    print(f"Wrote {len(landuse_out)} landuse polygons → {LANDUSE_OUT}")
    print(f"Wrote {len(hex_out)} hex cells → {HEX_OUT}")
    n_real = len(landuse_m)
    print(f"  ({n_real} real Overture + {len(slivers_m)} synthetic slivers)")


if __name__ == "__main__":
    main()
