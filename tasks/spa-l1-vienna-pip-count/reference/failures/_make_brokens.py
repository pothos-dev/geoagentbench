"""Generate broken-solution outputs for spa-l1-vienna-pip-count.

Three classes, chosen to give the grader resolution along the
*format / count-completeness / attribute-shape* axes the task probes:

  - broken_wrong_format         — Gate 1 fail. The agent dropped the
                                  ``station_count`` column entirely
                                  (e.g. wrote a 2-column file with
                                  ``district_code, district_name``
                                  only). Score collapses to 0.

  - broken_inner_join           — Gate 1 / 2 pass. The agent grouped
                                  by containing district but never
                                  left-joined the result back onto the
                                  full Bezirk list, so the four zero-
                                  count districts (Mariahilf,
                                  Josefstadt, Simmering, Hernals)
                                  vanish. → 19 rows. Two subchecks
                                  fail: ``exact_count_match`` and
                                  ``district_code_set_complete``. The
                                  per-row attribute and total
                                  subchecks pass on the 19 districts
                                  present. → 3/5 = 0.60.

  - broken_name_used_id         — Gate 1 / 2 pass. The agent did the
                                  count correctly and produced 23 rows
                                  but pulled the OSM relation id into
                                  ``district_name`` instead of the
                                  human-readable Bezirk name (a
                                  classic left/right-of-the-merge
                                  column-confusion bug). Only the
                                  per-row name match fails. → 4/5 =
                                  0.80.

Each broken score range is recorded in metadata.yaml.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l1-vienna-pip-count/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
DISTRICTS_IN = TASK_DIR / "inputs" / "districts.geojson"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "stations_per_district.csv"
OUTPUT_NAME = "stations_per_district.csv"


def _write_csv(target: Path, df: pd.DataFrame) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    df.to_csv(target, index=False)


def make_wrong_format() -> None:
    """Drop the ``station_count`` column. Gate 1 fails. Score = 0."""
    out_dir = HERE / "broken_wrong_format" / "outputs"
    target = out_dir / OUTPUT_NAME
    ref = pd.read_csv(REFERENCE_OUT)
    ref = ref.drop(columns=["station_count"])
    _write_csv(target, ref)


def make_inner_join() -> None:
    """Drop the four zero-count districts (Mariahilf, Josefstadt,
    Simmering, Hernals) — the canonical "inner join, never left-joined
    back to the full Bezirk list" failure. 19 rows.
    """
    out_dir = HERE / "broken_inner_join" / "outputs"
    target = out_dir / OUTPUT_NAME
    ref = pd.read_csv(REFERENCE_OUT)
    sub = ref[ref["station_count"] > 0].reset_index(drop=True)
    _write_csv(target, sub)


def make_name_used_id() -> None:
    """Replace ``district_name`` with the OSM relation id. 23 rows but
    every name is the integer relation id — a column-confusion bug
    that an agent could plausibly hit when carrying attributes through
    a sjoin.
    """
    out_dir = HERE / "broken_name_used_id" / "outputs"
    target = out_dir / OUTPUT_NAME

    districts = gpd.read_file(DISTRICTS_IN)
    code_to_relation = dict(
        zip(
            districts["district_code"].astype(int),
            districts["osm_relation_id"].astype(int),
        )
    )

    ref = pd.read_csv(REFERENCE_OUT)
    ref["district_name"] = ref["district_code"].astype(int).map(code_to_relation)
    if ref["district_name"].isna().any():
        raise RuntimeError("relation-id mapping incomplete; check inputs.")
    _write_csv(target, ref)


def main() -> None:
    if not REFERENCE_OUT.exists():
        raise SystemExit(
            f"Reference output {REFERENCE_OUT} not found. "
            "Run reference/solution/generate.py first."
        )
    make_wrong_format()
    make_inner_join()
    make_name_used_id()
    print("Wrote broken solutions:")
    for d in ("broken_wrong_format", "broken_inner_join", "broken_name_used_id"):
        print(f"  {HERE / d / 'outputs' / OUTPUT_NAME}")


if __name__ == "__main__":
    main()
