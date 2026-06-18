"""Generate broken-solution fixtures from the reference output.

Run inside the project Docker container:

    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l2-tokyo-overture-schools/reference/failures/_make_brokens.py

Failure classes covered:

* `wrong_format`        — emits a CSV under the same filename. Gate 1
                          fails because the file is not a parseable
                          GeoJSON FeatureCollection. Score = 0.
* `no_spatial_crop`     — agent chose the right category set but
                          skipped the spatial-join, so the output
                          includes schools outside the 23-wards bbox.
                          Flips count_within_tolerance,
                          feature_set_jaccard_high, and
                          bbox_crop_applied on the `school`-subset
                          comparison; school_category_selection still
                          passes.
* `strict_school_only`  — agent applied the spatial crop correctly
                          but filtered on `categories.primary =
                          'school'` only, missing the elementary /
                          middle / private subtypes the prompt's
                          age-framing implies. Flips
                          school_category_selection; pipeline
                          subchecks all pass.
* `dropped_attrs`       — agent kept the right feature set but
                          stripped confidence + addresses. Flips
                          confidence_field_present and
                          addresses_field_present; others pass.
* `dropped_catch_all`   — agent applied the crop and picked the right
                          category family, but within the bare `school`
                          rows kept only those carrying an explicit
                          school-level `categories.alternate` tag,
                          dropping the generic catch-all. Produces a
                          clean high-purity subset of the reference
                          `school` ids, so count_within_tolerance and
                          feature_set_jaccard_high are rescued and only
                          generic_school_retained flips (one weight-1
                          point). This is the defensible-but-narrow
                          reading four runs across three agent families
                          converged on (see audit HR-001).
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import shape

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REF = TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_schools.geojson"
PARQUET_GLOB = TASK_DIR / "inputs" / "tokyo_places" / "**" / "*.parquet"
BBOX_PATH = TASK_DIR / "inputs" / "tokyo_23wards_bbox.geojson"

ACCEPTED_CATEGORIES = (
    "school",
    "elementary_school",
    "middle_school",
    "private_school",
    "public_school",
)


def _write_geojson(features: list, path: Path) -> None:
    fc = {
        "type": "FeatureCollection",
        "name": "tokyo_schools",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(fc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def make_wrong_format() -> None:
    out = HERE / "broken_wrong_format" / "outputs" / "tokyo_schools.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "id,name,confidence\n"
        "fake-1,Sample,0.5\n",
        encoding="utf-8",
    )


def _query_categories(categories: tuple[str, ...]):
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    in_list = ", ".join(f"'{c}'" for c in categories)
    return con.execute(
        f"""
        SELECT
            id,
            names.primary AS name,
            confidence,
            addresses[1].freeform AS address_freeform,
            addresses[1].locality AS address_locality,
            addresses[1].postcode AS address_postcode,
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=1)
        WHERE categories.primary IN ({in_list})
        ORDER BY id
        """
    ).fetchdf()


def _none_if_missing(v):
    """Coerce pandas NaN/NA to None so json.dumps emits `null`, not the
    non-standard `NaN` literal, for the nullable address fields."""
    return None if pd.isna(v) else v


def _rows_to_features(rows) -> list:
    features = []
    for _, row in rows.iterrows():
        geom = wkt.loads(row["geom_wkt"])
        conf = row["confidence"]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": row["id"],
                    "name": row["name"],
                    "confidence": (
                        float(conf) if not pd.isna(conf) else None
                    ),
                    "address_freeform": _none_if_missing(row["address_freeform"]),
                    "address_locality": _none_if_missing(row["address_locality"]),
                    "address_postcode": _none_if_missing(row["address_postcode"]),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(geom.x), float(geom.y)],
                },
            }
        )
    return features


def make_no_spatial_crop() -> None:
    """Correct category selection, no bbox crop: every school in the
    accept-list family across the whole slice."""
    rows = _query_categories(ACCEPTED_CATEGORIES)
    features = _rows_to_features(rows)
    out = HERE / "broken_no_spatial_crop" / "outputs" / "tokyo_schools.geojson"
    _write_geojson(features, out)


def make_strict_school_only() -> None:
    """Right pipeline, wrong category selection: spatial crop applied
    but the agent filtered on the bare `categories.primary = 'school'`
    string, missing the elementary / middle / private subtypes the
    prompt's age-framing implies."""
    rows = _query_categories(("school",))
    features = _rows_to_features(rows)

    # Apply the bbox crop (this is the "right pipeline" half).
    bbox_gdf = gpd.read_file(BBOX_PATH)
    bbox_polygon = bbox_gdf.geometry.iloc[0]
    inside = [
        f for f in features
        if bbox_polygon.intersects(
            shape({"type": "Point", "coordinates": f["geometry"]["coordinates"][:2]})
        )
    ]
    out = HERE / "broken_strict_school_only" / "outputs" / "tokyo_schools.geojson"
    _write_geojson(inside, out)


def make_dropped_attrs() -> None:
    """Right feature set, but confidence + address fields are missing
    from properties (replaced with `None` on the keys to make sure the
    field-presence subcheck flips)."""
    fc = json.loads(REF.read_text(encoding="utf-8"))
    new_features = []
    for f in fc["features"]:
        props = {
            "id": f["properties"]["id"],
            "name": f["properties"]["name"],
            # The grader's gate-1 schema check requires these keys to
            # exist; we keep the keys but blank the values so gate 1
            # passes and the per-key subchecks flip.
            "confidence": None,
            "address_freeform": None,
            "address_locality": None,
            "address_postcode": None,
        }
        new_features.append({**f, "properties": props})
    out = HERE / "broken_dropped_attrs" / "outputs" / "tokyo_schools.geojson"
    _write_geojson(new_features, out)


def make_dropped_catch_all() -> None:
    """Right crop + right category family, but the generic `school`
    catch-all is dropped in favour of only the bare-`school` rows that
    carry an explicit school-level `categories.alternate` tag.

    Keeps the labeled subtypes (elementary / middle / private / public)
    in full, plus only the signal-bearing bare-`school` rows. The
    resulting `school`-subset is a clean high-purity subset of the
    reference, so the grader rescues count_within_tolerance and
    feature_set_jaccard_high and flips only generic_school_retained.
    """
    SCHOOL_LEVEL_ALTERNATES = {
        "elementary_school",
        "middle_school",
        "private_school",
        "public_school",
        "high_school",
    }
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    rows = con.execute(
        f"""
        SELECT
            id,
            names.primary AS name,
            confidence,
            addresses[1].freeform AS address_freeform,
            addresses[1].locality AS address_locality,
            addresses[1].postcode AS address_postcode,
            categories.primary AS primary,
            categories.alternate AS alternate,
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=1)
        WHERE categories.primary IN ('school', 'elementary_school',
              'middle_school', 'private_school', 'public_school')
        ORDER BY id
        """
    ).fetchdf()

    def _keep(row) -> bool:
        if row["primary"] != "school":
            # labeled subtypes are always kept
            return True
        alt = row["alternate"]
        try:
            alt_set = set(alt)
        except TypeError:
            alt_set = set()
        return len(alt_set & SCHOOL_LEVEL_ALTERNATES) > 0

    kept = rows[rows.apply(_keep, axis=1)].drop(columns=["primary", "alternate"])
    features = _rows_to_features(kept)

    # Apply the bbox crop (the "right pipeline" half).
    bbox_gdf = gpd.read_file(BBOX_PATH)
    bbox_polygon = bbox_gdf.geometry.iloc[0]
    inside = [
        f for f in features
        if bbox_polygon.intersects(
            shape({"type": "Point", "coordinates": f["geometry"]["coordinates"][:2]})
        )
    ]
    out = HERE / "broken_dropped_catch_all" / "outputs" / "tokyo_schools.geojson"
    _write_geojson(inside, out)


def main() -> None:
    make_wrong_format()
    make_no_spatial_crop()
    make_strict_school_only()
    make_dropped_attrs()
    make_dropped_catch_all()
    print("Wrote five broken solutions.")


if __name__ == "__main__":
    main()
