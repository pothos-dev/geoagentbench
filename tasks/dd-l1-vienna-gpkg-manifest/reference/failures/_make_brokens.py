"""Generate broken-solution outputs for dd-l1-vienna-gpkg-manifest.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l1-vienna-gpkg-manifest/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "manifest.json"
OUTPUT_NAME = "manifest.json"

PRIMARY_LAYERS = ("districts", "parks", "schools")


def _load_ref() -> list[dict]:
    with REFERENCE_OUT.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_wrong_format() -> None:
    """Agent flattened the manifest into a CSV. Gate 1 (top-level must be a
    JSON list) rejects the body before any subcheck runs. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    ref = _load_ref()
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["layer_name", "crs", "geometry_type", "feature_count", "bbox"])
        for r in ref:
            writer.writerow(
                [r["layer_name"], r["crs"], r["geometry_type"],
                 r["feature_count"], json.dumps(r["bbox"])]
            )


def make_partial_layers() -> None:
    """Agent only enumerated the three 'primary' layers named in the
    inventory's row (districts, parks, schools) and skipped the four
    auxiliary ones. `layers_complete` fails; the four absent layers' 16
    subchecks fail; the three covered layers' 12 subchecks pass.
    → 12 / 29 ≈ 0.414.
    """
    out_dir = HERE / "broken_partial_layers" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    ref = _load_ref()
    kept = [r for r in ref if r["layer_name"] in PRIMARY_LAYERS]
    with target.open("w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_wrong_crs_bbox() -> None:
    """Agent silently reprojected every layer to EPSG:4326 before
    introspecting it: declares `crs = "EPSG:4326"` and reports the bbox
    in degrees rather than the GPKG's native EPSG:31287 metres. The
    layer set, geometry types, and feature counts are still correct.

    Failures: layers_complete passes (set unchanged), but every layer's
    `crs_correct` and `bbox_correct` subcheck fails. geom_type and count
    pass for all seven layers.
    → 1 + 7 + 7 = 15 / 29 ≈ 0.517.
    """
    out_dir = HERE / "broken_wrong_crs_bbox" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    ref = _load_ref()
    # Realistic-looking WGS84 bboxes for inner Vienna (degrees), unique
    # per layer so the bbox subcheck cleanly fails for each.
    perturbed = []
    for r in ref:
        perturbed.append(
            {
                "layer_name": r["layer_name"],
                "crs": "EPSG:4326",
                "geometry_type": r["geometry_type"],
                "feature_count": r["feature_count"],
                "bbox": [16.34, 48.19, 16.38, 48.22],
            }
        )
    with target.open("w", encoding="utf-8") as f:
        json.dump(perturbed, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    make_wrong_format()
    make_partial_layers()
    make_wrong_crs_bbox()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
