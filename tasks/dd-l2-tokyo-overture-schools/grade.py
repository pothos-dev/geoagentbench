"""Grader for dd-l2-tokyo-overture-schools.

One hard gate (``format_schema_valid``) plus a checklist of subchecks.
The hard gate covers cases where the output is unrecoverable for
grading: GeoJSON not parseable, CRS not WGS84, no features, geometries
that aren't Points, or required `properties` keys missing. Everything
else — including id-type sanity and coordinate plausibility for the
Tokyo metropolis window — is scored as subchecks so an agent that
botches one dimension still earns credit on the others.

The task probes two independent dimensions:

  (a) **Category-selection judgment** — the persona's age-8–14 framing
      picks out Overture's compulsory-education primary categories
      ({school, elementary_school, middle_school, private_school,
      public_school}). An agent that submits only the bare `school`
      category misses the family; an agent that includes
      `driving_school` or `preschool` overshoots.

  (b) **Pipeline correctness** — partitioned Parquet read, nested
      attribute filter, spatial-join to the wards bbox, GeoJSON write
      with CJK + confidence + addresses preserved. This dimension
      should be measured *independently of* the category choice.

To keep the two dimensions orthogonal, the feature-count and
feature-set-Jaccard subchecks restrict both submission and reference
to the `categories.primary == 'school'` subset before comparing — the
one category every reasonable answer must include. Category-set
quality is measured by a separate Jaccard against the accept-list.

Subchecks:
    school_category_selection     — Jaccard ≥ 0.6 between the agent's
                                     chosen primary-category set and
                                     {school, elementary_school,
                                     middle_school, private_school,
                                     public_school}.
    count_within_tolerance        — ±5 % feature count on the
                                     `primary='school'` subset (rescued
                                     for a clean dropped-catch-all
                                     subset, see generic_school_retained).
    feature_set_jaccard_high      — ≥ 0.9 Jaccard on the same subset
                                     (rescued for a clean dropped-catch-all
                                     subset).
    generic_school_retained       — the generic `school` tag holds most
                                     real schools and should be kept;
                                     dropping it (a clean high-purity
                                     subset of the reference) is a
                                     defensible-but-narrow reading and
                                     costs one point instead of the full
                                     count + Jaccard budget.
    cjk_names_preserved           — at least 80 % of common ids carry
                                     a non-empty `name`; at least one
                                     CJK character appears in the
                                     submission.
    confidence_field_present      — every feature has a numeric
                                     `confidence` in [0, 1].
    addresses_field_present       — every feature has the three
                                     address_* keys (values may be
                                     null).
    bbox_crop_applied             — every submitted point sits inside
                                     the 23-wards bbox polygon.
    ids_are_strings               — every feature has a non-empty
                                     string `id`.
    coords_in_tokyo_window        — every submitted coordinate lies
                                     inside the generous Tokyo
                                     metropolis window.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from geo_grading import Gate, ScoreReport, Subcheck
from geo_grading.comparisons import (
    count_within_tolerance,
    is_wgs84_fc,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_schools.geojson"
BBOX_PATH = TASK_DIR / "inputs" / "tokyo_23wards_bbox.geojson"
INPUTS_PARQUET_GLOB = TASK_DIR / "inputs" / "tokyo_places"
OUTPUT_NAME = "tokyo_schools.geojson"

REQUIRED_PROPS = (
    "id",
    "name",
    "confidence",
    "address_freeform",
    "address_locality",
    "address_postcode",
)

# Overture primary-category accept-list under the prompt's age-8–14
# framing: Japan's compulsory-education range (小学校 + 中学校) plus the
# generic `school` catch-all and the ownership-tagged sibling
# categories that can host the same age group.
ACCEPTED_CATEGORIES = frozenset({
    "school",
    "elementary_school",
    "middle_school",
    "private_school",
    "public_school",
})

# The category every reasonable answer must include. Used to derive a
# category-invariant subset of both submission and reference for the
# feature-count / Jaccard subchecks, so they measure pipeline quality
# (partitioned read, spatial crop, attribute preservation) rather than
# category-selection.
SCHOOL_SUBSET_CATEGORY = "school"

# Generous Tokyo metropolis window — every school point in the
# bundled slice falls inside.
TOKYO_X = (139.40, 140.00)
TOKYO_Y = (35.40, 35.90)


def _load_geojson(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None



def _load_id_to_primary_category() -> dict[str, str | None]:
    """Build {id -> categories.primary} from the bundled input slice.

    Read once per grade() call; ~13.4k rows, sub-second.
    """
    parts = sorted(INPUTS_PARQUET_GLOB.rglob("part.parquet"))
    if not parts:
        return {}
    frames = [pd.read_parquet(p, columns=["id", "categories"]) for p in parts]
    df = pd.concat(frames, ignore_index=True)
    out: dict[str, str | None] = {}
    for row in df.itertuples(index=False):
        cat_struct = row.categories
        primary = None
        if cat_struct is not None:
            # Parquet may surface the nested struct as a dict or as a
            # pandas Series-like; handle both.
            if isinstance(cat_struct, dict):
                primary = cat_struct.get("primary")
            else:
                try:
                    primary = cat_struct["primary"]
                except (KeyError, TypeError, ValueError):
                    primary = None
        out[str(row.id)] = primary
    return out


def _has_cjk(s: str) -> bool:
    if not isinstance(s, str):
        return False
    for c in s:
        cp = ord(c)
        if 0x3000 <= cp <= 0x9FFF or 0xFF00 <= cp <= 0xFFEF:
            return True
    return False


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dd-l2-tokyo-overture-schools")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Hard gate: format / schema validity ---------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing output file: {OUTPUT_NAME}",
            )
        )
        return report

    fc = _load_geojson(submission_path)
    if fc is None or fc.get("type") != "FeatureCollection":
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "submission is not a parseable GeoJSON FeatureCollection",
            )
        )
        return report

    if not is_wgs84_fc(fc):
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"submission CRS is not WGS84: {fc.get('crs')!r}",
            )
        )
        return report

    features = fc.get("features") or []
    if not features:
        report.gates.append(
            Gate("format_schema_valid", False, "FeatureCollection has no features")
        )
        return report

    bad_geom = 0
    bad_props = 0
    for feat in features:
        geom = feat.get("geometry") or {}
        if geom.get("type") != "Point":
            bad_geom += 1
        props = feat.get("properties") or {}
        if not all(k in props for k in REQUIRED_PROPS):
            bad_props += 1

    if bad_geom:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"{bad_geom}/{len(features)} features are not Point geometries",
            )
        )
        return report

    if bad_props:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                (
                    f"{bad_props}/{len(features)} features missing required "
                    f"properties {REQUIRED_PROPS}"
                ),
            )
        )
        return report
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks -----------------------------------------------------
    ref_fc = json.loads(REFERENCE_OUT.read_text(encoding="utf-8"))
    ref_features = ref_fc["features"]
    ref_ids = {f["properties"]["id"] for f in ref_features}
    sub_ids = {f["properties"]["id"] for f in features}

    # Look up each id's categories.primary from the input slice once;
    # used by the category-selection subcheck and by the school-subset
    # filtering for count / Jaccard.
    id_to_primary = _load_id_to_primary_category()
    sub_primaries = {id_to_primary.get(i) for i in sub_ids}
    # Drop None values (ids not found in input — agent invented an id).
    sub_categories = {c for c in sub_primaries if c}

    # 1. School-category selection — Jaccard against the accept-list.
    #    Measures whether the agent read the persona's age-framing as
    #    pointing at the compulsory-education school family rather
    #    than the bare `school` string.
    if sub_categories:
        cat_jaccard = (
            len(sub_categories & ACCEPTED_CATEGORIES)
            / len(sub_categories | ACCEPTED_CATEGORIES)
        )
    else:
        cat_jaccard = 0.0
    report.subchecks.append(
        Subcheck(
            "school_category_selection",
            cat_jaccard >= 0.6,
            detail=(
                f"chosen categories {sorted(sub_categories)!r} vs accept-list "
                f"{sorted(ACCEPTED_CATEGORIES)!r}; Jaccard = {cat_jaccard:.4f} "
                f"(need ≥ 0.6)"
            ),
            weight=2.0,
        )
    )

    # School-subset filtering: restrict both sides to
    # `categories.primary == 'school'` so the count / id-Jaccard
    # subchecks measure pipeline correctness (partitioned read,
    # spatial crop) independently of category-selection.
    sub_school_ids = {
        i for i in sub_ids
        if id_to_primary.get(i) == SCHOOL_SUBSET_CATEGORY
    }
    ref_school_ids = {
        i for i in ref_ids
        if id_to_primary.get(i) == SCHOOL_SUBSET_CATEGORY
    }

    # School-subset precision / recall. The count and id-Jaccard
    # subchecks below detect *pipeline* faults via over-inclusion: a
    # skipped spatial crop or a junk filter add `school`-subset ids the
    # reference does not contain (precision drops), so those subchecks
    # must still fire. But an agent that deliberately keeps only the
    # bare-`school` rows carrying an explicit age-level signal -- and
    # drops the generic catch-all -- produces a clean high-purity
    # *subset* of the reference (precision ~ 1.0, recall low). That is a
    # defensible-but-narrow reading of the persona's age-8-14 framing,
    # not a pipeline failure, so it should cost a single low-weight point
    # rather than the full count + Jaccard budget. We detect the
    # clean-subset signature here and route its penalty to
    # `generic_school_retained` below.
    inter = sub_school_ids & ref_school_ids
    precision = len(inter) / len(sub_school_ids) if sub_school_ids else 0.0
    recall = len(inter) / len(ref_school_ids) if ref_school_ids else 0.0
    clean_subset = bool(sub_school_ids) and precision >= 0.95 and recall < 0.9

    # 2. count tolerance on the school subset (rescued for a clean subset)
    count_ok = (
        count_within_tolerance(len(sub_school_ids), len(ref_school_ids), pct=0.05)
        or clean_subset
    )
    report.subchecks.append(
        Subcheck(
            "count_within_tolerance",
            count_ok,
            detail=(
                f"submitted {len(sub_school_ids)} `school` features vs "
                f"reference {len(ref_school_ids)} (±5 % tolerance; "
                f"category-invariant subset; clean dropped-catch-all "
                f"subset rescued: {clean_subset})"
            ),
            weight=2.0,
        )
    )

    # 3. feature-set Jaccard on the school subset (rescued for a clean subset)
    jac = jaccard_similarity_set(sub_school_ids, ref_school_ids)
    jac_ok = jac >= 0.9 or clean_subset
    report.subchecks.append(
        Subcheck(
            "feature_set_jaccard_high",
            jac_ok,
            detail=(
                f"Jaccard over `school`-subset ids = {jac:.4f} (need ≥ 0.9; "
                f"clean dropped-catch-all subset rescued: {clean_subset})"
            ),
            weight=3.0,
        )
    )

    # 3b. generic-school catch-all retained. Most real schools in the
    # slice carry only the generic `school` primary tag, so a correct
    # answer keeps the catch-all (precision and recall both high ->
    # passes). An agent that narrows to only the explicitly-age-tagged
    # bare-`school` rows produces a clean subset and loses just this one
    # weight-1 point -- a slight, deliberate penalty for a defensible
    # reading rather than a full pipeline-failure cost.
    report.subchecks.append(
        Subcheck(
            "generic_school_retained",
            not clean_subset,
            detail=(
                f"`school`-subset precision {precision:.3f} / recall "
                f"{recall:.3f}; dropped-catch-all signature: {clean_subset}"
            ),
            weight=1.0,
        )
    )

    # 4. CJK name preservation
    common = sub_ids & ref_ids
    sub_by_id = {f["properties"]["id"]: f["properties"] for f in features}
    ref_by_id = {f["properties"]["id"]: f["properties"] for f in ref_features}
    if common:
        non_empty = sum(
            1 for i in common if isinstance(sub_by_id[i].get("name"), str)
            and sub_by_id[i]["name"].strip()
        )
        cjk_in_sub = any(
            _has_cjk(sub_by_id[i].get("name") or "") for i in common
        )
        cjk_expected = any(
            _has_cjk(ref_by_id[i].get("name") or "") for i in common
        )
        names_ok = (non_empty / len(common) >= 0.8) and (
            cjk_in_sub or not cjk_expected
        )
        report.subchecks.append(
            Subcheck(
                "cjk_names_preserved",
                names_ok,
                detail=(
                    f"non-empty name on {non_empty}/{len(common)} common ids; "
                    f"CJK present in submission: {cjk_in_sub} "
                    f"(expected: {cjk_expected})"
                ),
                weight=3.0,
            )
        )
    else:
        report.subchecks.append(
            Subcheck(
                "cjk_names_preserved",
                False,
                "no common ids with reference",
                weight=3.0,
            )
        )

    # 5. confidence field present and numeric in [0, 1]
    conf_ok = True
    bad_conf = 0
    for feat in features:
        v = feat["properties"].get("confidence")
        if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
            conf_ok = False
            bad_conf += 1
    report.subchecks.append(
        Subcheck(
            "confidence_field_present",
            conf_ok,
            detail=f"{bad_conf}/{len(features)} features have invalid confidence",
        )
    )

    # 6. address fields present (keys exist; null values OK)
    addr_keys = ("address_freeform", "address_locality", "address_postcode")
    addr_ok = all(
        all(k in feat["properties"] for k in addr_keys) for feat in features
    )
    report.subchecks.append(
        Subcheck(
            "addresses_field_present",
            addr_ok,
            detail="every feature carries the three address_* keys",
        )
    )

    # 7. bbox crop applied: every submitted point inside the 23-wards bbox
    bbox_gdf = gpd.read_file(BBOX_PATH)
    bbox_polygon = bbox_gdf.geometry.iloc[0]
    outside = 0
    for feat in features:
        x, y = feat["geometry"]["coordinates"][:2]
        if not bbox_polygon.contains(shape({"type": "Point", "coordinates": [x, y]})):
            # touches/within: also accept on-boundary as inside.
            if not bbox_polygon.intersects(
                shape({"type": "Point", "coordinates": [x, y]})
            ):
                outside += 1
    crop_ok = outside / max(len(features), 1) <= 0.01
    report.subchecks.append(
        Subcheck(
            "bbox_crop_applied",
            crop_ok,
            detail=(
                f"{outside}/{len(features)} submitted points lie outside "
                f"the 23-wards bbox polygon (allowed ≤ 1 %)"
            ),
            weight=2.0,
        )
    )

    # 8. ids are non-empty strings (migrated from old Gate 2).
    bad_id = sum(
        1 for feat in features
        if not isinstance(feat["properties"].get("id"), str)
        or not feat["properties"]["id"]
    )
    report.subchecks.append(
        Subcheck(
            "ids_are_strings",
            bad_id == 0,
            detail=f"{bad_id}/{len(features)} features have non-string/empty id",
        )
    )

    # 9. Coordinates fall inside the generous Tokyo metropolis window
    #    (migrated from old Gate 2). Distinct from `bbox_crop_applied`
    #    which uses the tighter 23-wards polygon.
    bad_xy = 0
    for feat in features:
        coords = feat["geometry"]["coordinates"][:2]
        try:
            x = float(coords[0])
            y = float(coords[1])
        except (TypeError, ValueError, IndexError):
            bad_xy += 1
            continue
        if not (TOKYO_X[0] <= x <= TOKYO_X[1] and TOKYO_Y[0] <= y <= TOKYO_Y[1]):
            bad_xy += 1
    report.subchecks.append(
        Subcheck(
            "coords_in_tokyo_window",
            bad_xy == 0,
            detail=(
                f"{bad_xy}/{len(features)} coordinates outside Tokyo "
                f"metropolis window x={TOKYO_X}, y={TOKYO_Y}"
            ),
            weight=2.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
