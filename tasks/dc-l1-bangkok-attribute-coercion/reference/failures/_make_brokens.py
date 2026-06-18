"""Generate broken-solution outputs for dc-l1-bangkok-attribute-coercion.

Three classes, chosen to give the grader resolution along the
*type-coercion-awareness* axis (the central skill of the task):

  - broken_wrong_format        — Gate 1 fail (missing required property
                                  `pm25_ug_m3`).
  - broken_no_coercion         — agent passed the input through
                                  unchanged; every numeric column is
                                  still a JSON string.
  - broken_partial_coercion    — agent coerced the float columns but
                                  left `station_id` as a string.

Each broken score range is recorded in metadata.yaml.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dc-l1-bangkok-attribute-coercion/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "bangkok_aq_typed.geojson"
RAW_INPUT = TASK_DIR / "inputs" / "bangkok_aq_stations.geojson"
OUTPUT_NAME = "bangkok_aq_typed.geojson"


def _write(target: Path, fc: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with target.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_wrong_format() -> None:
    """The agent produced GeoJSON in EPSG:4326 with correctly typed
    numeric columns but dropped the `pm25_ug_m3` column on the way out
    (e.g., kept only `station_id`, `name_th`, `sensor_value`,
    `elevation_m` before writing).

    Gate 1's required-property check fails. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    with REFERENCE_OUT.open("r", encoding="utf-8") as f:
        fc = json.load(f)
    for feat in fc["features"]:
        feat["properties"].pop("pm25_ug_m3", None)
    _write(out_dir / OUTPUT_NAME, fc)


def make_no_coercion() -> None:
    """The agent passed the input through unchanged: every numeric
    column is still a JSON string, the persona's bug fully intact.

    Gates pass (file readable, CRS=4326, properties present, Point
    geometry, count match). Subchecks: all four type subchecks fail;
    the four content / set / geometry subchecks pass because the
    underlying values, names, ids, and coordinates are unchanged. The
    `feature_id_set_via_geopandas` subcheck also passes (set is the
    same set, just stringified). → 5/9 ≈ 0.556.
    """
    out_dir = HERE / "broken_no_coercion" / "outputs"
    target = out_dir / OUTPUT_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    # The simplest "didn't fix coercion" failure is a verbatim copy of
    # the malformed input under the expected output name. Numbers
    # remain quoted; the file is otherwise valid GeoJSON.
    shutil.copyfile(RAW_INPUT, target)


def make_partial_coercion() -> None:
    """The agent coerced the float columns (`sensor_value`,
    `pm25_ug_m3`, `elevation_m`) to floats but forgot `station_id` —
    it remains a JSON string in the output.

    Gates pass. Subchecks: only `station_id_is_integer` fails;
    everything else passes (floats are numbers, content matches,
    name_th preserved, geometry preserved, set preserved). → 8/9 ≈ 0.889.
    """
    out_dir = HERE / "broken_partial_coercion" / "outputs"
    target = out_dir / OUTPUT_NAME
    target.parent.mkdir(parents=True, exist_ok=True)

    with RAW_INPUT.open("r", encoding="utf-8") as f:
        fc = json.load(f)

    for feat in fc["features"]:
        props = feat["properties"]
        # station_id stays as string.
        for field in ("sensor_value", "pm25_ug_m3", "elevation_m"):
            props[field] = float(props[field])

    fc["features"].sort(
        key=lambda feat: int(feat["properties"]["station_id"])
    )
    _write(target, fc)


def main() -> None:
    make_wrong_format()
    make_no_coercion()
    make_partial_coercion()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
