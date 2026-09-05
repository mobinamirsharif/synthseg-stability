"""Audit completed public runs, provenance, geometry, markers, and result rows."""

import argparse
import csv
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from scripts.run_public_experiment import (
    CONDITIONS,
    MODES,
    RESULT_COLUMNS,
    iter_run_specs,
    paths_for_run,
    sha256,
    validate_run_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config/public_dataset.json")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data/public")
    parser.add_argument("--work-dir", type=Path, default=REPO_ROOT / "work/public")
    parser.add_argument(
        "--results", type=Path, default=REPO_ROOT / "results/public/subject_level/results.csv"
    )
    parser.add_argument(
        "--report", type=Path, default=REPO_ROOT / "work/public/audit_report.json"
    )
    parser.add_argument("--expected-label-count", type=int, default=32)
    return parser.parse_args()


def image_geometry(path):
    image = nib.load(path)
    data = np.asarray(image.dataobj)
    coordinates = np.argwhere(data != 0)
    if coordinates.size == 0:
        raise ValueError(f"Image has no non-zero voxels: {path}")
    lower = coordinates.min(axis=0)
    upper = coordinates.max(axis=0)
    return {
        "shape": list(data.shape),
        "voxel_size_mm": [round(float(value), 6) for value in image.header.get_zooms()[:3]],
        "orientation": list(nib.aff2axcodes(image.affine)),
        "affine": np.asarray(image.affine).round(6).tolist(),
        "nonzero_bbox_inclusive": [lower.tolist(), upper.tolist()],
        "nonzero_margins_voxels": [lower.tolist(), (np.asarray(data.shape) - 1 - upper).tolist()],
    }


def condition_input(data_dir, work_dir, participant, condition):
    if condition == "clean":
        return data_dir / participant / "anat" / f"{participant}_T1w.nii"
    return work_dir / participant / "inputs" / f"{condition}.nii.gz"


def audit(config, data_dir, work_dir, results_path, expected_label_count=32):
    errors = []
    geometry = {}
    dataset_manifest = json.loads((data_dir / "download_manifest.json").read_text(encoding="utf-8"))
    manifest_by_participant = {row["participant"]: row for row in dataset_manifest}

    for participant in config["participants"]:
        source = condition_input(data_dir, work_dir, participant, "clean")
        actual_hash = sha256(source)
        expected_hash = config["sha256"][participant]
        if actual_hash != expected_hash:
            errors.append(f"Input checksum mismatch: {participant}")
        manifest = manifest_by_participant.get(participant, {})
        expected_url = f"{config['download_base'].rstrip('/')}/{participant}/anat/{participant}_T1w.nii"
        if manifest.get("source_url") != expected_url or manifest.get("sha256") != expected_hash:
            errors.append(f"Download manifest mismatch: {participant}")
        geometry[participant] = image_geometry(source)

    marker_count = 0
    runtimes = []
    for participant, condition, mode in iter_run_specs(config):
        paths = paths_for_run(work_dir, participant, condition, mode)
        valid, reason, label_count = validate_run_outputs(paths, expected_label_count)
        if not valid:
            errors.append(f"Invalid run {participant}/{condition}/{mode}: {reason}")
            continue
        if not paths.marker.is_file():
            errors.append(f"Missing completion marker: {participant}/{condition}/{mode}")
            continue
        marker_count += 1
        marker = json.loads(paths.marker.read_text(encoding="utf-8"))
        expected_key = f"{participant}/{condition}/{mode}"
        for field, expected in (
            ("run_key", expected_key),
            ("dataset_id", config["dataset_id"]),
            ("dataset_version", config["snapshot"]),
            ("participant", participant),
            ("condition", condition),
            ("mode", mode),
            ("label_count", expected_label_count),
        ):
            if marker.get(field) != expected:
                errors.append(f"Marker field mismatch {expected_key}: {field}")
        expected_input_hash = sha256(condition_input(data_dir, work_dir, participant, condition))
        if marker.get("input_sha256") != expected_input_hash:
            errors.append(f"Marker input checksum mismatch: {expected_key}")
        try:
            runtime = float(marker["runtime_seconds"])
            if runtime <= 0:
                raise ValueError
            runtimes.append(runtime)
        except (KeyError, TypeError, ValueError):
            errors.append(f"Invalid runtime: {expected_key}")
        if label_count != expected_label_count:
            errors.append(f"Label count mismatch: {expected_key}")

        if condition.startswith("resolution_"):
            aligned = paths.segmentation.with_name(paths.segmentation.stem + "_aligned.mgz")
            clean = paths_for_run(work_dir, participant, "clean", mode).segmentation
            if not aligned.is_file():
                errors.append(f"Missing aligned segmentation: {expected_key}")
            elif nib.load(aligned).shape != nib.load(clean).shape:
                errors.append(f"Aligned segmentation shape mismatch: {expected_key}")

    with results_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        result_columns = tuple(reader.fieldnames or ())
    result_keys = {(row["participant"], row["condition"], row["mode"]) for row in rows}
    expected_keys = set(iter_run_specs(config))
    if len(rows) != len(expected_keys) or result_keys != expected_keys:
        errors.append("Subject-level result rows do not match the 64-run design")
    if result_columns != RESULT_COLUMNS:
        errors.append("Subject-level result schema mismatch")
    for row in rows:
        if row["dataset_id"] != config["dataset_id"] or row["dataset_version"] != config["snapshot"]:
            errors.append("Result provenance mismatch")
            break
        if int(row["label_count"]) != expected_label_count:
            errors.append("Result label-count mismatch")
            break
        for field in (
            "runtime_seconds", "clean_reference_macro_dice",
            "mean_absolute_volume_drift_pct", "median_absolute_volume_drift_pct",
        ):
            float(row[field])

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "dataset_id": config["dataset_id"],
        "dataset_version": config["snapshot"],
        "participants": config["participants"],
        "conditions": list(CONDITIONS),
        "modes": list(MODES),
        "expected_runs": len(expected_keys),
        "valid_markers": marker_count,
        "result_rows": len(rows),
        "runtime_records": len(runtimes),
        "geometry": geometry,
    }


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report = audit(config, args.data_dir, args.work_dir, args.results, args.expected_label_count)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
