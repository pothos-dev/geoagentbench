"""Grader for geo-l3-antarctica-stations-geodesic.

Hard gate (`format_schema_valid`):
    station_spheres.geoparquet is readable GeoParquet with required
    columns (station_id, station_name, coalition, geometry).
    station_water_overlap.geoparquet is readable GeoParquet with required
    columns (station_id, station_name, water_id, water_name,
    water_subtype, water_source, geometry).

Subchecks:
    station_count_tolerance    — feature count within ±30% of ref.
    station_name_overlap       — ≥60% of reference station names appear
                                  in the submission (fuzzy: case-insensitive).
    coalition_exists           — coalition column has >1 distinct value.
    buffer_area_reasonable     — total area of spheres is within ±40% of
                                  reference.
    crs_is_3031                — CRS authority is EPSG:3031.
    water_output_present       — station_water_overlap has at least 1 feature.
    water_station_overlap      — ≥50% of reference stations with water
                                  portions appear in submission.
    water_source_attribution   — at least one of base.water / base.bathymetry
                                  appears in water_source column.
    water_area_reasonable      — total water overlap area within ±50% of ref.
    geodesic_buffer_check      — mean station sphere area is within ±30% of
                                  ref.
    min_station_count          — at least 5 station spheres present.
    sphere_geometry_types      — sphere geometries are Polygon/MultiPolygon.
    sphere_coords_projected    — sphere coordinates fall in projected
                                  metre range (not degrees).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import CRS

from geo_grading import Gate, ScoreReport, Subcheck
from geo_grading.comparisons import count_within_tolerance

TASK_DIR = Path(__file__).resolve().parent
REF_SPHERES = TASK_DIR / "reference" / "solution" / "outputs" / "station_spheres.geoparquet"
REF_WATER = TASK_DIR / "reference" / "solution" / "outputs" / "station_water_overlap.geoparquet"

SPHERES_NAME = "station_spheres.geoparquet"
WATER_NAME = "station_water_overlap.geoparquet"

REQUIRED_SPHERE_COLS = {"station_id", "station_name", "coalition", "geometry"}
REQUIRED_WATER_COLS = {
    "station_id", "station_name", "water_id", "water_name",
    "water_subtype", "water_source", "geometry",
}

# EPSG:3031 projected coordinates are in metres — typical range for Antarctica
MAX_COORD_M = 5_000_000  # 5000 km from origin is generous
MIN_STATIONS = 5  # At least 5 stations expected


def _read_geoparquet_safe(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_parquet(path)
    except Exception:
        return None


def _is_epsg_3031(crs: CRS | None) -> bool:
    if crs is None:
        return False
    try:
        return crs.to_epsg() == 3031
    except Exception:
        pass
    try:
        return "3031" in crs.to_authority()[1]
    except Exception:
        return False


def _normalise_names(names: pd.Series) -> set[str]:
    """Lowercase, strip whitespace from station names."""
    return set(names.dropna().str.strip().str.lower())


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="geo-l3-antarctica-stations-geodesic")

    sph_path = submission_dir / SPHERES_NAME
    wat_path = submission_dir / WATER_NAME

    # ------------------------------------------------------------------ #
    # Gate 1: format / schema valid                                       #
    # ------------------------------------------------------------------ #
    if not sph_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing {SPHERES_NAME}")
        )
        return report

    sph = _read_geoparquet_safe(sph_path)
    if sph is None:
        report.gates.append(
            Gate("format_schema_valid", False,
                 f"{SPHERES_NAME} not readable as GeoParquet")
        )
        return report

    missing_sph = REQUIRED_SPHERE_COLS - set(sph.columns)
    if missing_sph:
        report.gates.append(
            Gate("format_schema_valid", False,
                 f"{SPHERES_NAME} missing columns: {missing_sph}")
        )
        return report

    if not wat_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing {WATER_NAME}")
        )
        return report

    wat = _read_geoparquet_safe(wat_path)
    if wat is None:
        report.gates.append(
            Gate("format_schema_valid", False,
                 f"{WATER_NAME} not readable as GeoParquet")
        )
        return report

    missing_wat = REQUIRED_WATER_COLS - set(wat.columns)
    if missing_wat:
        report.gates.append(
            Gate("format_schema_valid", False,
                 f"{WATER_NAME} missing columns: {missing_wat}")
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    # ------------------------------------------------------------------ #
    # Subchecks                                                           #
    # ------------------------------------------------------------------ #
    ref_sph = gpd.read_parquet(REF_SPHERES)
    ref_wat = gpd.read_parquet(REF_WATER)

    # 1. Station count tolerance (±30% for L3 — station identification varies)
    count_ok = count_within_tolerance(len(sph), len(ref_sph), pct=0.30)
    report.subchecks.append(
        Subcheck(
            "station_count_tolerance",
            count_ok,
            f"submitted {len(sph)} vs reference {len(ref_sph)} (±30%)",
            weight=2.0,
        )
    )

    # 2. Station name overlap (≥60% of reference names)
    ref_names = _normalise_names(ref_sph["station_name"])
    sub_names = _normalise_names(sph["station_name"])
    if ref_names:
        name_overlap = len(ref_names & sub_names) / len(ref_names)
    else:
        name_overlap = 1.0
    report.subchecks.append(
        Subcheck(
            "station_name_overlap",
            bool(name_overlap >= 0.60),
            f"{name_overlap:.2%} of reference station names found (need ≥60%)",
            weight=2.0,
        )
    )

    # 3. Coalition exists (>1 distinct value)
    n_coalitions = sph["coalition"].nunique()
    report.subchecks.append(
        Subcheck(
            "coalition_exists",
            bool(n_coalitions > 1),
            f"{n_coalitions} distinct coalition values",
        )
    )

    # 4. Buffer area reasonable (total area ±40%)
    sub_total_area = sph.geometry.area.sum()
    ref_total_area = ref_sph.geometry.area.sum()
    if ref_total_area > 0:
        area_ratio = sub_total_area / ref_total_area
        area_ok = bool(0.60 <= area_ratio <= 1.40)
    else:
        area_ratio = 0.0
        area_ok = False
    report.subchecks.append(
        Subcheck(
            "buffer_area_reasonable",
            area_ok,
            f"area ratio {area_ratio:.2f} (need 0.60–1.40)",
            weight=4.0,
        )
    )

    # 5. CRS is EPSG:3031
    crs_ok = _is_epsg_3031(sph.crs)
    report.subchecks.append(
        Subcheck(
            "crs_is_3031",
            crs_ok,
            f"CRS EPSG code: {sph.crs.to_epsg() if sph.crs else None}",
            weight=4.0,
        )
    )

    # 6. Water output present
    water_present = bool(len(wat) > 0)
    report.subchecks.append(
        Subcheck(
            "water_output_present",
            water_present,
            f"water overlap has {len(wat)} features",
        )
    )

    # 7. Water station overlap (≥50% of reference stations with water)
    ref_water_stations = set(ref_wat["station_id"].dropna().unique())
    sub_water_stations = set(wat["station_id"].dropna().unique()) if len(wat) > 0 else set()
    # Compare by name since IDs may differ
    ref_water_names = _normalise_names(
        ref_wat.drop_duplicates("station_id")["station_name"]
    )
    sub_water_names = _normalise_names(
        wat.drop_duplicates("station_id")["station_name"]
    ) if len(wat) > 0 else set()
    if ref_water_names:
        water_station_overlap = len(ref_water_names & sub_water_names) / len(ref_water_names)
    else:
        water_station_overlap = 1.0
    report.subchecks.append(
        Subcheck(
            "water_station_overlap",
            bool(water_station_overlap >= 0.50),
            f"{water_station_overlap:.2%} of reference water-stations found (need ≥50%)",
            weight=2.0,
        )
    )

    # 8. Water source attribution
    if "water_source" in wat.columns and len(wat) > 0:
        sources = set(wat["water_source"].dropna().unique())
        has_source = bool(
            "base.water" in sources or "base.bathymetry" in sources
        )
    else:
        has_source = False
    report.subchecks.append(
        Subcheck(
            "water_source_attribution",
            has_source,
            f"water_source values: {sources if 'sources' in dir() else 'N/A'}",
        )
    )

    # 9. Water area reasonable (±50%)
    if len(wat) > 0 and len(ref_wat) > 0:
        sub_water_area = wat.geometry.area.sum()
        ref_water_area = ref_wat.geometry.area.sum()
        if ref_water_area > 0:
            water_area_ratio = sub_water_area / ref_water_area
            water_area_ok = bool(0.50 <= water_area_ratio <= 1.50)
        else:
            water_area_ratio = 0.0
            water_area_ok = False
    else:
        water_area_ratio = 0.0
        water_area_ok = False
    report.subchecks.append(
        Subcheck(
            "water_area_reasonable",
            water_area_ok,
            f"water area ratio {water_area_ratio:.2f} (need 0.50–1.50)",
            weight=2.0,
        )
    )

    # 10. Geodesic buffer check (mean area ±30%)
    sub_mean_area = sph.geometry.area.mean()
    ref_mean_area = ref_sph.geometry.area.mean()
    if ref_mean_area > 0:
        mean_ratio = sub_mean_area / ref_mean_area
        geodesic_ok = bool(0.70 <= mean_ratio <= 1.30)
    else:
        mean_ratio = 0.0
        geodesic_ok = False
    report.subchecks.append(
        Subcheck(
            "geodesic_buffer_check",
            geodesic_ok,
            f"mean sphere area ratio {mean_ratio:.2f} (need 0.70–1.30)",
            weight=4.0,
        )
    )

    # 11. Minimum viable station count.
    report.subchecks.append(
        Subcheck(
            "min_station_count",
            len(sph) >= MIN_STATIONS,
            f"{len(sph)} station spheres (need ≥{MIN_STATIONS})",
        )
    )

    # 12. Sphere geometry types are Polygon / MultiPolygon.
    valid_types = {"Polygon", "MultiPolygon"}
    geom_types = set(sph.geometry.geom_type.dropna().unique())
    bad_types = geom_types - valid_types
    report.subchecks.append(
        Subcheck(
            "sphere_geometry_types",
            bool(geom_types) and not bad_types,
            f"sphere geom types: {sorted(geom_types)} "
            "(expected Polygon / MultiPolygon)",
        )
    )

    # 13. Sphere coords in projected metre range (not degrees).
    bounds = sph.total_bounds
    coords_projected = not all(abs(b) < 360 for b in bounds)
    report.subchecks.append(
        Subcheck(
            "sphere_coords_projected",
            coords_projected,
            f"spheres bounds {bounds} (expected EPSG:3031 metres, not degrees)",
            weight=4.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
