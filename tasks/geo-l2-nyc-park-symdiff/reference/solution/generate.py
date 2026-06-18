"""Reference solution for geo-l2-nyc-park-symdiff.

Pipeline:
  1. Read both layers (`parks_official`, `parks_osm`) from the bundled
     GPKG. Both are already in EPSG:6539 (NY State Plane Long Island).
  2. Symmetric difference between the two layers' unioned geometries:
     symdiff = (A ∪ B) − (A ∩ B), or equivalently (A − B) ∪ (B − A).
  3. Decompose into connected-component clusters (a 1 m buffer-merge
     connects symdiff slivers that touch along a shared boundary).
  4. For each cluster, classify the source attribute:
        - "parks_official" if the cluster only carries area from A−B,
        - "parks_osm"      if only from B−A,
        - "both"           if it carries area from both sides
                            (typical for shifted parks).
  5. For each cluster, collect into a MultiPolygon and compute the
     point-on-surface as the label anchor.
  6. Sort clusters by (minx, miny) of bbox, assign deterministic
     `cluster_id` 0..N-1, reproject to WGS84, and write two GeoJSON
     files in EPSG:4326. `area_m2` stays in projected metres².

Determinism: cluster ordering by bounds; rows sorted by `cluster_id`.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_GPKG = TASK_DIR / "inputs" / "nyc_parks.gpkg"
OUTPUTS = HERE / "outputs"
OUT_DISAGREEMENT = OUTPUTS / "parks_disagreement.geojson"
OUT_ANCHORS = OUTPUTS / "park_label_anchors.geojson"

WORK_CRS = "EPSG:6539"  # metric CRS for symdiff, clustering, area math
OUTPUT_CRS = "EPSG:4326"  # WGS84; RFC 7946 GeoJSON write CRS
CLUSTER_BUFFER_M = 1.0  # bridge sub-metre topology gaps


def _to_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    polys = []
    for g in getattr(geom, "geoms", []):
        if g.is_empty:
            continue
        if g.geom_type == "Polygon":
            polys.append(g)
        elif g.geom_type == "MultiPolygon":
            polys.extend(list(g.geoms))
    return MultiPolygon(polys) if polys else None


def _polygon_parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return [p for p in geom.geoms if not p.is_empty]
    parts = []
    for g in getattr(geom, "geoms", []):
        parts.extend(_polygon_parts(g))
    return parts


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    official = gpd.read_file(INPUT_GPKG, layer="parks_official")
    osm = gpd.read_file(INPUT_GPKG, layer="parks_osm")
    if official.crs is None or official.crs.to_epsg() != 6539:
        official = official.to_crs(WORK_CRS)
    if osm.crs is None or osm.crs.to_epsg() != 6539:
        osm = osm.to_crs(WORK_CRS)

    a_union = unary_union(official.geometry.tolist())
    b_union = unary_union(osm.geometry.tolist())

    only_a = a_union.difference(b_union)  # parks_official ∖ parks_osm
    only_b = b_union.difference(a_union)  # parks_osm ∖ parks_official
    symdiff = unary_union([only_a, only_b])

    # Cluster: 1 m buffer-merge to bridge near-coincident boundaries
    # produced by the shifted-park half-moon pairs, then dilate clusters
    # back by -1 m for area accounting.
    merged = symdiff.buffer(CLUSTER_BUFFER_M).buffer(-CLUSTER_BUFFER_M)
    cluster_polys = _polygon_parts(merged)

    # Sort cluster envelopes by (minx, miny) for stable cluster_id.
    cluster_polys = sorted(cluster_polys, key=lambda p: (p.bounds[0], p.bounds[1]))

    # Pre-extract source-tagged pieces for fast classification.
    only_a_parts = _polygon_parts(only_a)
    only_b_parts = _polygon_parts(only_b)

    rows = []
    for cluster_id, cluster in enumerate(cluster_polys):
        # Each cluster_polygon is a Polygon (or could be one) — collect
        # the original symdiff parts that fall inside it.
        a_pieces = [p for p in only_a_parts if p.representative_point().within(cluster)]
        b_pieces = [p for p in only_b_parts if p.representative_point().within(cluster)]
        if not a_pieces and not b_pieces:
            # Can happen if the buffer-merge over-dilated; skip.
            continue
        all_pieces = a_pieces + b_pieces
        cluster_geom = unary_union(all_pieces)
        mp = _to_multipolygon(cluster_geom)
        if mp is None or mp.is_empty:
            continue
        if a_pieces and b_pieces:
            source = "both"
        elif a_pieces:
            source = "parks_official"
        else:
            source = "parks_osm"
        rows.append(
            {
                "cluster_id": cluster_id,
                "source": source,
                "area_m2": float(mp.area),
                "geometry": mp,
            }
        )

    disagreement = gpd.GeoDataFrame(rows, geometry="geometry", crs=WORK_CRS)
    disagreement = disagreement.sort_values("cluster_id", kind="stable").reset_index(
        drop=True
    )

    # Reassign sequential cluster_id (some buffer-merge artefacts may
    # have been skipped, leaving gaps).
    disagreement["cluster_id"] = range(len(disagreement))

    anchors_rows = []
    for _, row in disagreement.iterrows():
        anchor = row.geometry.representative_point()
        anchors_rows.append(
            {
                "cluster_id": int(row.cluster_id),
                "source": row.source,
                "geometry": anchor,
            }
        )
    anchors = gpd.GeoDataFrame(anchors_rows, geometry="geometry", crs=WORK_CRS)

    # Reproject both outputs to WGS84 (RFC 7946) for the GeoJSON write;
    # area_m2 was computed above in the projected CRS and is unaffected.
    disagreement = disagreement.to_crs(OUTPUT_CRS)
    anchors = anchors.to_crs(OUTPUT_CRS)

    if OUT_DISAGREEMENT.exists():
        OUT_DISAGREEMENT.unlink()
    if OUT_ANCHORS.exists():
        OUT_ANCHORS.unlink()
    disagreement.to_file(OUT_DISAGREEMENT, driver="GeoJSON")
    anchors.to_file(OUT_ANCHORS, driver="GeoJSON")

    print(
        f"parks_official: {len(official)}; parks_osm: {len(osm)}; "
        f"clusters: {len(disagreement)}"
    )
    print(disagreement["source"].value_counts().to_string())
    print(f"Total disagreement area: {disagreement['area_m2'].sum():.0f} m²")
    print(f"Wrote {OUT_DISAGREEMENT} and {OUT_ANCHORS}")


if __name__ == "__main__":
    main()
