"""Generate broken-solution outputs for dd-l1-capetown-clinics-bbox.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l1-capetown-clinics-bbox/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "clinic_inventory.json"
OUTPUT_NAME = "clinic_inventory.json"


def _load_ref() -> dict:
    with REFERENCE_OUT.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_wrong_format() -> None:
    """Agent wrote the inventory as CSV instead of JSON. Gate 1 (cannot
    parse JSON object) rejects the file before any subcheck runs.
    Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    ref = _load_ref()
    # Pretend the agent emitted a flat CSV roll-up.
    lines = ["subdistrict,count", f"_total,{ref['count']}"]
    for sd, n in ref["count_per_subdistrict"].items():
        lines.append(f"{sd},{n}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_wrong_bbox() -> None:
    """Agent reported the bbox in [ymin, xmin, ymax, xmax] (lat-lon
    swapped) instead of [xmin, ymin, xmax, ymax]. All four bbox
    componentwise subchecks fail; count and subdistricts are correct.
    → 4 / 8 = 0.500.
    """
    out_dir = HERE / "broken_wrong_bbox" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    ref = _load_ref()
    xmin, ymin, xmax, ymax = ref["bbox"]
    swapped = {
        "count": ref["count"],
        "bbox": [ymin, xmin, ymax, xmax],
        "count_per_subdistrict": ref["count_per_subdistrict"],
    }
    with target.open("w", encoding="utf-8") as f:
        json.dump(swapped, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_wrong_attributes() -> None:
    """Agent listed all eight subdistricts but assumed an equal split
    (80 / 8 = 10 per subdistrict). The actual distribution is
    non-uniform (12, 12, 11, 10, 10, 9, 8, 8), so only the two
    subdistricts that happen to land on 10 (Eastern, Northern) match
    the reference. Effects:
      * count_correct passes (still 80).
      * Four bbox subchecks pass.
      * subdistrict_keys_match passes (all eight names present).
      * subdistrict_counts_match fails (only 2 / 8 per-key values
        agree).
      * count_equals_subdistrict_sum passes (8 × 10 == 80).
    → 7 / 8 = 0.875.
    """
    out_dir = HERE / "broken_wrong_attributes" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    ref = _load_ref()
    equal_split = {sd: 10 for sd in ref["count_per_subdistrict"].keys()}
    body = {
        "count": ref["count"],
        "bbox": ref["bbox"],
        "count_per_subdistrict": equal_split,
    }
    with target.open("w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    make_wrong_format()
    make_wrong_bbox()
    make_wrong_attributes()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
