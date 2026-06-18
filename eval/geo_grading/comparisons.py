"""Comparison primitives for geometric and attribute equivalence.

These functions are the five named in design.md §5.1 plus a Jaccard
helper that comes up often enough to justify a primitive. Each function
is pure and side-effect-free; pass GeoDataFrames in, get a number /
boolean / structured result out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import geopandas as gpd
import pandas as pd
from pyproj import CRS
from shapely.errors import GEOSException
from shapely.geometry import GeometryCollection
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid


def is_wgs84(crs: CRS | None) -> bool:
    """Return True if *crs* is WGS 84 geographic (EPSG:4326 or OGC:CRS84).

    A ``None`` CRS is accepted as WGS 84, matching the GeoJSON spec
    (RFC 7946) where the absence of a CRS member implies WGS 84.
    """
    if crs is None:
        return True
    if crs.to_epsg() == 4326:
        return True
    try:
        return crs.equals(CRS.from_authority("OGC", "CRS84"))
    except Exception:
        return False


def is_wgs84_fc(fc: dict) -> bool:
    """Check WGS 84 on a raw GeoJSON FeatureCollection dict.

    Inspects the ``crs`` member that some writers embed. Absent ``crs``
    is WGS 84 per RFC 7946.
    """
    crs = fc.get("crs")
    if crs is None:
        return True
    name = ((crs.get("properties") or {}).get("name") or "").upper()
    return any(t in name for t in ("CRS84", "EPSG:4326", "EPSG::4326", "4326"))


def check_and_normalize_crs(
    gdf: gpd.GeoDataFrame | None,
    accepted_epsgs: Iterable[int],
    target_epsg: int,
) -> tuple[bool, str, gpd.GeoDataFrame | None, int | None]:
    """Validate a GeoDataFrame's CRS against an accept-list and reproject.

    Use when a task is willing to accept any of several equivalent
    metric CRSes (e.g. Lambert-93 *or* UTM 31N for Paris), but its
    spatial subchecks compare against a reference in one canonical
    ``target_epsg``. The helper combines the Gate-1 accept check and the
    pre-comparison reprojection that every such grader was hand-rolling.

    Returns a 4-tuple ``(ok, reason, normalized, original_epsg)``:

    - ``ok``: True iff the input has a CRS, the CRS has an EPSG code,
      and that code is in ``accepted_epsgs``.
    - ``reason``: empty when ``ok``; otherwise a one-line diagnostic
      suitable for a ``Gate``'s reason field.
    - ``normalized``: when ``ok``, the input reprojected to
      ``target_epsg`` (or returned unchanged if already there). When
      not ``ok``, the input is returned as-is so callers can build
      diagnostics without crashing on downstream access.
    - ``original_epsg``: the EPSG of the input, or ``None`` when the
      input had no CRS / no EPSG code. Useful for follow-up subchecks
      like "did the agent pick the official CRS?".

    ``target_epsg`` must appear in ``accepted_epsgs``; otherwise raises
    ``ValueError`` (a target outside the accept list is always a bug).
    """
    accepted = set(accepted_epsgs)
    if target_epsg not in accepted:
        raise ValueError(
            f"target_epsg={target_epsg} must be in accepted_epsgs={sorted(accepted)}"
        )
    if gdf is None:
        return False, "GeoDataFrame is None", gdf, None
    if gdf.crs is None:
        return False, "GeoDataFrame has no CRS", gdf, None
    epsg = gdf.crs.to_epsg()
    if epsg is None and gdf.crs.to_authority() == ("OGC", "CRS84"):
        # OGC:CRS84 is WGS84 lon/lat — same datum as EPSG:4326, only the
        # formal axis order differs. RFC 7946 GeoJSON is always lon/lat on
        # disk regardless of the tag, so this normalisation is geometrically
        # safe and just rescues spec-compliant GeoJSON writers from a false fail.
        epsg = 4326
    if epsg is None:
        return False, f"CRS has no EPSG code ({gdf.crs})", gdf, None
    if epsg not in accepted:
        return (
            False,
            f"CRS EPSG:{epsg} not in accepted set {sorted(accepted)}",
            gdf,
            epsg,
        )
    if epsg == target_epsg:
        return True, "", gdf, epsg
    return True, "", gdf.to_crs(epsg=target_epsg), epsg


@dataclass
class CrsGradeResult:
    """Outcome of :func:`grade_crs_soft` — gate verdict + two subcheck flags.

    The grader uses this to populate one hard gate and two soft subchecks:
    - ``gate_ok``: passes unless the input has no usable CRS at all.
    - ``is_canonical``: True iff ``original_epsg`` is in the task's
      canonical set (which is ``{canonical_epsg}`` when a single int is
      passed, or the supplied iterable when several EPSGs are accepted
      as equally canonical).
    - ``in_meaningful_set``: True iff ``original_epsg`` is in the
      task's meaningful set.

    When the gate passes, ``normalized`` is the input reprojected to
    ``min(canonical_set)`` so downstream geometric subchecks have a
    stable reference frame regardless of which canonical CRS the agent
    picked.
    """

    gate_ok: bool
    gate_reason: str
    normalized: gpd.GeoDataFrame | None
    original_epsg: int | None
    is_canonical: bool
    in_meaningful_set: bool


def grade_crs_soft(
    gdf: gpd.GeoDataFrame | None,
    meaningful_epsgs: Iterable[int],
    canonical_epsg: int | Iterable[int],
    *,
    treat_none_as_wgs84: bool = False,
) -> CrsGradeResult:
    """Soft-fail CRS grading with reproject-to-canonical for downstream subchecks.

    Use when the task wants to *grade* the agent's CRS pick (canonical vs
    merely meaningful vs neither) rather than hard-gate on it. The only
    hard failure is when the input has no usable CRS at all — without
    that, the grader cannot reproject and downstream geometric subchecks
    are undefined.

    ``canonical_epsg`` may be a single int **or** an iterable of ints
    when two or more EPSGs are equally defensible "canonical" picks
    (e.g. EPSG:26331 and EPSG:26391 are both legitimate readings of
    "Nigeria's national grid" — same Minna datum, different convention).
    ``is_canonical`` then means *the agent's CRS is in the canonical
    set*. When a set is supplied, downstream reprojection always targets
    ``min(canonical_set)`` (deterministic) — callers must therefore make
    sure the reference data is in that same EPSG.

    Behavior:
    - ``gdf`` is ``None`` → gate fails ("no GeoDataFrame").
    - ``gdf.crs`` is ``None`` and ``treat_none_as_wgs84=False`` → gate
      fails. Set ``treat_none_as_wgs84=True`` for GeoJSON readers that
      return ``crs=None`` for RFC 7946 inputs without a ``crs`` member,
      where the spec implies WGS 84.
    - ``gdf.crs`` has no EPSG code (custom WKT, unrecognised authority)
      → gate fails. Reprojecting from an unknown CRS to canonical is
      unsafe.
    - Otherwise → gate passes. ``normalized`` is the input reprojected
      to the canonical reprojection target (unchanged if already there).
      The two subcheck flags grade the agent's choice.

    Every member of ``canonical_epsg`` must appear in
    ``meaningful_epsgs``; otherwise raises ``ValueError`` (a canonical
    pick outside the meaningful set is always a bug).
    """
    meaningful = set(meaningful_epsgs)
    if isinstance(canonical_epsg, int):
        canonical_set = {canonical_epsg}
    else:
        canonical_set = set(canonical_epsg)
    if not canonical_set:
        raise ValueError("canonical_epsg must contain at least one EPSG code")
    extra = canonical_set - meaningful
    if extra:
        raise ValueError(
            f"canonical_epsg={sorted(canonical_set)} must be a subset of "
            f"meaningful_epsgs={sorted(meaningful)}; outside set: {sorted(extra)}"
        )
    reproject_to = min(canonical_set)
    if gdf is None:
        return CrsGradeResult(False, "GeoDataFrame is None", None, None, False, False)
    if gdf.crs is None:
        if treat_none_as_wgs84:
            epsg = 4326
            normalized = gdf if reproject_to == 4326 else gdf.set_crs(4326).to_crs(epsg=reproject_to)
            return CrsGradeResult(
                True,
                "",
                normalized,
                epsg,
                epsg in canonical_set,
                epsg in meaningful,
            )
        return CrsGradeResult(False, "GeoDataFrame has no CRS", None, None, False, False)
    epsg = gdf.crs.to_epsg()
    if epsg is None and gdf.crs.to_authority() == ("OGC", "CRS84"):
        # See check_and_normalize_crs: OGC:CRS84 ≡ EPSG:4326 for grading.
        epsg = 4326
    if epsg is None:
        return CrsGradeResult(
            False, f"CRS has no EPSG code ({gdf.crs})", None, None, False, False
        )
    normalized = gdf if epsg == reproject_to else gdf.to_crs(epsg=reproject_to)
    return CrsGradeResult(
        True,
        "",
        normalized,
        epsg,
        epsg in canonical_set,
        epsg in meaningful,
    )


def _recover_crs(crs_obj):
    """Best-effort CRS recovery from a GeoParquet ``crs`` value pyproj refused.

    Tries, in order: full PROJJSON, a ``properties.name`` (e.g. "EPSG:4326"),
    then an authority ``id``. Returns a :class:`~pyproj.CRS` or ``None``.
    """
    if crs_obj is None:
        return None
    if isinstance(crs_obj, str):
        try:
            return CRS.from_user_input(crs_obj)
        except Exception:
            return None
    if isinstance(crs_obj, dict):
        try:
            return CRS.from_json_dict(crs_obj)
        except Exception:
            pass
        props = crs_obj.get("properties") or {}
        name = props.get("name") or crs_obj.get("name")
        if isinstance(name, str):
            try:
                return CRS.from_user_input(name)
            except Exception:
                pass
        ident = crs_obj.get("id") or props.get("id")
        if isinstance(ident, dict):
            auth, code = ident.get("authority"), ident.get("code")
            if auth and code is not None:
                try:
                    return CRS.from_authority(str(auth), str(code))
                except Exception:
                    pass
    return None


def read_geoparquet_lenient(path) -> tuple[gpd.GeoDataFrame | None, bool]:
    """Read a GeoParquet, tolerating a non-compliant / underspecified CRS.

    GeoParquet stores the CRS as PROJJSON in the file's ``geo`` metadata. A
    hand-rolled writer may emit an underspecified form such as
    ``{"type": "GeographicCRS", "properties": {"name": "EPSG:4326"}}`` that
    PROJ 9 rejects ("Missing datum_ensemble key"), so the standard
    ``gpd.read_parquet`` raises before any content can be graded — collapsing
    an otherwise-correct submission to a hard 0.

    Returns ``(gdf, crs_compliant)``:
    - clean ``gpd.read_parquet`` succeeds -> ``(gdf, True)``;
    - reader fails but geometry is recoverable -> rebuild the GeoDataFrame from
      the WKB/WKT geometry column and recover the CRS by name/authority
      -> ``(gdf, False)``;
    - the file is unreadable even as a plain table -> ``(None, True)``.

    Graders should treat ``crs_compliant is False`` as a soft penalty (the
    geometry is usable but the CRS metadata is off-spec), not a hard fail.
    """
    from pathlib import Path
    import json

    import pyarrow.parquet as pq
    from shapely import from_wkb, from_wkt

    path = Path(path)
    try:
        return gpd.read_parquet(path), True
    except Exception:
        pass
    try:
        table = pq.read_table(path)
    except Exception:
        return None, True
    meta = (table.schema.metadata or {}).get(b"geo")
    if not meta:
        return None, True
    try:
        geo = json.loads(meta)
    except Exception:
        return None, True
    primary = geo.get("primary_column", "geometry")
    col_meta = (geo.get("columns") or {}).get(primary, {})
    df = table.to_pandas()
    if primary not in df.columns:
        return None, True
    encoding = (col_meta.get("encoding") or "WKB").upper()
    try:
        if encoding == "WKT":
            geom = from_wkt(df[primary].to_numpy())
        else:
            geom = from_wkb(df[primary].to_numpy())
    except Exception:
        return None, True
    gdf = gpd.GeoDataFrame(df.drop(columns=[primary]), geometry=geom)
    crs = _recover_crs(col_meta.get("crs"))
    if crs is not None:
        gdf = gdf.set_crs(crs, allow_override=True)
    return gdf, False


def iou_with_tolerance(
    a: BaseGeometry | gpd.GeoSeries | gpd.GeoDataFrame,
    b: BaseGeometry | gpd.GeoSeries | gpd.GeoDataFrame,
    eps: float = 1e-6,
) -> float:
    """Geometric intersection-over-union of two geometry collections.

    Each input is unioned into a single geometry first, so a list of
    polygons is treated as the geometric union of all its parts. The
    result is in [0, 1]; 1.0 means identical, 0.0 means disjoint.

    The `eps` argument is reserved for future buffering / tolerance use;
    currently it triggers a tiny buffer-and-shrink that closes
    sub-millimetre topology gaps before the IoU is computed.
    """
    geom_a = _coerce_to_geometry(a)
    geom_b = _coerce_to_geometry(b)
    if geom_a.is_empty and geom_b.is_empty:
        return 1.0
    if geom_a.is_empty or geom_b.is_empty:
        return 0.0
    if eps > 0:
        geom_a = geom_a.buffer(eps).buffer(-eps)
        geom_b = geom_b.buffer(eps).buffer(-eps)
    inter_area = geom_a.intersection(geom_b).area
    union_area = geom_a.union(geom_b).area
    if union_area == 0:
        return 1.0 if inter_area == 0 else 0.0
    return inter_area / union_area


def feature_set_equality_by_id(
    a: gpd.GeoDataFrame | pd.DataFrame,
    b: gpd.GeoDataFrame | pd.DataFrame,
    key: str,
) -> float:
    """Jaccard similarity over the feature-id sets of two GeoDataFrames.

    Returns a value in [0, 1]. Identity ignores attribute and geometry
    differences — only the membership of `key` matters. Use when the
    grader only cares "did the agent return the same set of features?"
    """
    set_a = set(a[key].dropna().astype(str).tolist())
    set_b = set(b[key].dropna().astype(str).tolist())
    return jaccard_similarity_set(set_a, set_b)


def attribute_match(
    a: gpd.GeoDataFrame | pd.DataFrame,
    b: gpd.GeoDataFrame | pd.DataFrame,
    fields: Sequence[str],
    key: str,
    tolerance: float = 0.0,
) -> dict[str, float]:
    """Per-field match rate between two DataFrames keyed by `key`.

    For each field in `fields`, returns the fraction of rows (over the
    intersection of `key` sets) where the values agree. Numeric fields
    are compared with `tolerance` as a relative tolerance; string fields
    require exact match (caller is responsible for normalisation).

    The result dict has one entry per field plus an `_overall` mean.
    """
    keys_a = a[key].astype(str)
    keys_b = b[key].astype(str)
    common = sorted(set(keys_a) & set(keys_b))
    if not common:
        return {field: 0.0 for field in fields} | {"_overall": 0.0}

    a_idx = a.set_index(keys_a)
    b_idx = b.set_index(keys_b)

    per_field: dict[str, float] = {}
    for field in fields:
        if field not in a_idx.columns or field not in b_idx.columns:
            per_field[field] = 0.0
            continue
        series_a = a_idx.loc[common, field]
        series_b = b_idx.loc[common, field]
        per_field[field] = _value_match_rate(series_a, series_b, tolerance)
    per_field["_overall"] = (
        sum(per_field.values()) / len(per_field) if per_field else 0.0
    )
    return per_field


def topology_equal_within_epsilon(
    a: BaseGeometry | gpd.GeoSeries | gpd.GeoDataFrame,
    b: BaseGeometry | gpd.GeoSeries | gpd.GeoDataFrame,
    eps: float = 1e-6,
) -> bool:
    """Topological equivalence within a Hausdorff distance.

    Two geometries are equal-within-eps if their Hausdorff distance is
    less than or equal to `eps` (every vertex of either geometry has a
    counterpart on the other within eps). This is the right metric for
    catching topology mismatches that area-based metrics smooth over.
    """
    geom_a = _coerce_to_geometry(a)
    geom_b = _coerce_to_geometry(b)
    if geom_a.is_empty and geom_b.is_empty:
        return True
    if geom_a.is_empty or geom_b.is_empty:
        return False
    return geom_a.hausdorff_distance(geom_b) <= eps


def count_within_tolerance(
    a: int | gpd.GeoDataFrame | pd.DataFrame,
    b: int | gpd.GeoDataFrame | pd.DataFrame,
    pct: float = 0.05,
) -> bool:
    """Whether two counts are within a relative percentage tolerance.

    Accepts either DataFrames (uses `len()`) or raw integers. The check
    is symmetric: |a - b| / max(a, b) ≤ pct. Returns True when both
    inputs are zero.
    """
    n_a = a if isinstance(a, int) else len(a)
    n_b = b if isinstance(b, int) else len(b)
    if n_a == 0 and n_b == 0:
        return True
    denom = max(n_a, n_b)
    if denom == 0:
        return False
    return abs(n_a - n_b) / denom <= pct


def jaccard_similarity_set(a: Iterable, b: Iterable) -> float:
    """Standard Jaccard similarity for two iterables.

    Empty-set vs. empty-set returns 1.0 (vacuous agreement).
    """
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def _safe_make_valid(geom: BaseGeometry | None) -> BaseGeometry | None:
    if geom is None:
        return None
    try:
        return geom if geom.is_valid else make_valid(geom)
    except GEOSException:
        return None


def _coerce_to_geometry(
    obj: BaseGeometry | gpd.GeoSeries | gpd.GeoDataFrame,
) -> BaseGeometry:
    """Reduce a geometry / GeoSeries / GeoDataFrame to a single geometry.

    Defensively repairs invalid geometries with make_valid before
    unioning so a pathological submission fails its IoU subcheck only,
    not the entire grade run via a propagating GEOSException.
    """
    if isinstance(obj, BaseGeometry):
        return _safe_make_valid(obj) or GeometryCollection()
    if isinstance(obj, gpd.GeoDataFrame):
        geoms = obj.geometry.tolist()
    elif isinstance(obj, gpd.GeoSeries):
        geoms = obj.tolist()
    else:
        raise TypeError(f"Cannot coerce {type(obj).__name__} to a geometry")
    cleaned = [g for g in (_safe_make_valid(g) for g in geoms) if g is not None]
    if not cleaned:
        return GeometryCollection()
    try:
        return unary_union(cleaned)
    except GEOSException:
        return GeometryCollection()


def _value_match_rate(
    series_a: pd.Series, series_b: pd.Series, tolerance: float
) -> float:
    """Pairwise match rate between two Series, with optional rel-tolerance."""
    if pd.api.types.is_numeric_dtype(series_a) and pd.api.types.is_numeric_dtype(
        series_b
    ):
        if tolerance == 0:
            matches = (series_a == series_b)
        else:
            denom = series_a.abs().clip(lower=1e-12)
            matches = ((series_a - series_b).abs() / denom) <= tolerance
    else:
        matches = series_a.astype(str) == series_b.astype(str)
    return float(matches.fillna(False).mean())
