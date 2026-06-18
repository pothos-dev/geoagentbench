"""Authoring-time helper: build the bundled Tokyo buildings GeoJSON.

Run once at authoring time inside the project's Docker container. The
output `tokyo_buildings_legacy.geojson` is committed to the repo and
served to systems under test by the harness. Do not run this at grading
time.

Why we touch the data after slicing Overture:

The task is *about* a wrong-ring-orientation export written by a legacy
in-house tool that follows OGC orientation (exterior CW, interior CCW)
instead of RFC 7946 §3.1.6 (exterior CCW, interior CW). Overture's
buildings collection ships clean RFC-7946-compliant rings, so the
authoring helper:

  1. Slices a small Tokyo bbox out of a pinned Overture release.
  2. Filters and sorts deterministically; takes the first ~100 features.
  3. Injects a synthetic interior ring (a "courtyard" hole) into a fixed
     subset of the buildings so the grader has a non-trivial sample of
     interior rings to score for orientation. Real Overture buildings
     rarely have holes, but a meaningful task on RFC 7946 §3.1.6 must
     test both rules — exterior CCW *and* interior CW.
  4. Reverses every ring (exterior + every interior) so the bundled
     file is in OGC orientation, the malformed state the persona is
     trying to clean up.

Determinism: the slice query is deterministic, the bbox is fixed, the
sort key is stable, the synthetic hole geometry is a closed-form
function of feature index, and the GeoJSON serialisation is hand-rolled
(stable formatting, no driver-side reordering). Two consecutive runs of
this helper produce byte-identical bundled inputs.

Run:
    docker run --rm -v "$PWD":/work geo-bench-author \\
        uv run python tasks/dc-l1-tokyo-ring-orientation/inputs/_prepare.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
from shapely.geometry import Polygon, mapping
from shapely.geometry.polygon import orient
from shapely.wkt import loads as wkt_loads

HERE = Path(__file__).resolve().parent
OUT = HERE / "tokyo_buildings_legacy.geojson"

# Pinned Overture release. See docs/OVERTURE_REFERENCE.md.
RELEASE = "2026-04-15.0"

# Small bbox around Shibuya / Yoyogi, Tokyo.
XMIN, YMIN, XMAX, YMAX = 139.700, 35.658, 139.704, 35.662

# Number of buildings to keep after sort (capacity check inside `main`).
TARGET_FEATURES = 100

# Indices (0-based, after sorting by id) into which we inject a synthetic
# interior ring. Picked at authoring time; fixed for determinism.
HOLE_INDICES: tuple[int, ...] = (5, 17, 31, 49, 73)


def _reverse_ring(coords: list[list[float]]) -> list[list[float]]:
    """Reverse the order of a closed ring's coordinate list.

    The first and last vertex of a closed ring are identical, so reversing
    the entire list keeps the ring closed (the duplicate is symmetric).
    """
    return list(reversed(coords))


def _inject_hole(poly: Polygon, idx: int) -> Polygon:
    """Return a Polygon with a small synthetic interior ring added.

    The hole is a tiny axis-aligned square placed near the polygon's
    centroid, scaled to ~5% of the polygon's bbox. Closed-form so the
    helper stays deterministic. If the candidate hole is not contained
    by the polygon (degenerate footprint), the function returns the
    polygon unchanged — the grader handles this gracefully because the
    interior-ring subcheck is computed over the union of submission and
    reference interior rings, not against a fixed expected count.
    """
    minx, miny, maxx, maxy = poly.bounds
    span_x = maxx - minx
    span_y = maxy - miny
    if span_x <= 0 or span_y <= 0:
        return poly

    # Hole side ~5% of bbox; offset so the hole sits inside the footprint.
    side_x = span_x * 0.05
    side_y = span_y * 0.05
    cx = minx + span_x * (0.45 + 0.01 * (idx % 7))
    cy = miny + span_y * (0.45 + 0.01 * (idx % 5))
    hole_coords = [
        (cx, cy),
        (cx + side_x, cy),
        (cx + side_x, cy + side_y),
        (cx, cy + side_y),
        (cx, cy),
    ]
    candidate = Polygon(poly.exterior, [hole_coords])
    if not candidate.is_valid or not Polygon(hole_coords).within(poly):
        return poly
    # Re-orient to RFC 7946 first (exterior CCW, interior CW). The whole
    # polygon will be flipped to OGC orientation in the calling code.
    return orient(candidate, sign=1.0)


def _polygon_to_geojson_geometry(poly: Polygon) -> dict:
    """Serialise a shapely Polygon to a GeoJSON-style geometry dict with
    every ring reversed (exterior CW, interior CCW — the OGC orientation
    the persona's legacy export wrote).
    """
    geom = mapping(orient(poly, sign=1.0))  # canonical RFC 7946 first
    rings = geom["coordinates"]
    flipped = [_reverse_ring(list(map(list, ring))) for ring in rings]
    return {"type": "Polygon", "coordinates": flipped}


def main() -> None:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute(
        """
        CREATE OR REPLACE SECRET overture (
          TYPE s3,
          PROVIDER config,
          KEY_ID '',
          SECRET '',
          REGION 'us-west-2',
          USE_SSL true,
          URL_STYLE 'path'
        );
        """
    )

    rows = con.execute(
        f"""
        SELECT
            id,
            COALESCE(names.primary, '') AS name_primary,
            COALESCE(class, '') AS building_class,
            height,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=buildings/type=building/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND bbox.xmax BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymax BETWEEN {YMIN} AND {YMAX}
        ORDER BY id
        """
    ).fetchall()

    if len(rows) < TARGET_FEATURES:
        raise RuntimeError(
            f"Overture slice returned only {len(rows)} buildings; "
            f"expected at least {TARGET_FEATURES}. Widen the bbox."
        )

    rows = rows[:TARGET_FEATURES]

    features: list[dict] = []
    hole_set = set(HOLE_INDICES)

    for idx, (overture_id, name_primary, building_class, height, wkt) in enumerate(rows):
        geom = wkt_loads(wkt)
        # Some Overture rows are MultiPolygons; for an L1 single-Polygon
        # task we keep only single-Polygon footprints. Skip non-Polygons
        # quietly — the bbox filter usually keeps this tiny anyway.
        if geom.geom_type != "Polygon":
            continue
        if idx in hole_set:
            geom = _inject_hole(geom, idx)
        feature_id = idx + 1  # 1-based stable id, used by the grader

        features.append(
            {
                "type": "Feature",
                "geometry": _polygon_to_geojson_geometry(geom),
                "properties": {
                    "feature_id": feature_id,
                    "overture_id": overture_id,
                    "name_primary": name_primary,
                    "building_class": building_class,
                    "height": (
                        float(height) if height is not None else None
                    ),
                },
            }
        )

    fc = {
        "type": "FeatureCollection",
        "name": "tokyo_buildings_legacy",
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
    print(f"Wrote {len(features)} buildings to {OUT}")
    print(
        "Sample feature 0 properties:",
        features[0]["properties"],
    )


if __name__ == "__main__":
    main()
