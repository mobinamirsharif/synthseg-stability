"""Run the pinned public-data perturbation and SynthSeg experiment end to end."""

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np

from scripts.compute_macro_dice import compute_macro_dice
from scripts.compute_volume_drift import compute_volume_drifts, read_volumes, summarize_absolute_drifts


REPO_ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = (
    "clean",
    "resolution_2mm",
    "resolution_3mm",
    "noise_mild",
    "noise_moderate",
    "bias_moderate",
    "bias_strong",
    "bias_strong_n4",
)
MODES = ("standard", "robust")
RESULT_COLUMNS = (
    "dataset_id", "dataset_version", "participant", "condition", "mode",
    "runtime_seconds", "label_count", "clean_reference_macro_dice",
    "mean_absolute_volume_drift_pct", "median_absolute_volume_drift_pct", "qc_value",
)


@dataclass(frozen=True)
class RunPaths:
    segmentation: Path
    volumes: Path
    qc: Path
    marker: Path

    def derived_outputs(self):
        return (self.segmentation, self.volumes, self.qc, self.marker)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config/public_dataset.json")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data/public")
    parser.add_argument("--work-dir", type=Path, default=REPO_ROOT / "work/public")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "results/public/subject_level/results.csv")
    parser.add_argument("--expected-label-count", type=int, default=32)
    parser.add_argument(
        "--check-resume",
        action="store_true",
        help="Inspect all run outputs without preprocessing, inference, cleanup, or result writes.",
    )
    parser.add_argument(
        "--adopt-runtime",
        action="append",
        default=[],
        metavar="RUN_KEY=SECONDS",
        help=(
            "Attach an observed console runtime to valid pre-marker outputs, "
            "for example sub-01/clean/standard=440."
        ),
    )
    return parser.parse_args()


def require_commands():
    missing = [name for name in ("mri_convert", "mri_synthseg") if shutil.which(name) is None]
    if missing:
        raise RuntimeError("Required FreeSurfer commands not found on PATH: " + ", ".join(missing))


def run(command):
    print("Running:", " ".join(map(str, command)), flush=True)
    started = time.perf_counter()
    subprocess.run([str(item) for item in command], check=True)
    return time.perf_counter() - started


def script(name):
    return REPO_ROOT / "scripts" / name


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_key(participant, condition, mode):
    return f"{participant}/{condition}/{mode}"


def paths_for_run(output_root, participant, condition, mode):
    directory = Path(output_root) / participant / "outputs" / mode
    stem = directory / condition
    return RunPaths(
        segmentation=stem.with_suffix(".mgz"),
        volumes=stem.with_name(stem.name + "_volumes.csv"),
        qc=stem.with_name(stem.name + "_qc.csv"),
        marker=stem.with_name(stem.name + "_complete.json"),
    )


def csv_has_data(path):
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return bool(reader.fieldnames) and next(reader, None) is not None
    except (OSError, UnicodeError, csv.Error):
        return False


def validate_run_outputs(paths, expected_label_count=32):
    """Return (valid, reason, label_count) without changing any output."""
    missing = [path.name for path in (paths.segmentation, paths.volumes, paths.qc) if not path.is_file()]
    if missing:
        return False, "missing: " + ", ".join(missing), None
    if not csv_has_data(paths.volumes):
        return False, "volume CSV has no data row", None
    if not csv_has_data(paths.qc):
        return False, "QC CSV has no data row", None
    try:
        segmentation = np.asarray(nib.load(paths.segmentation).dataobj)
    except Exception as error:  # nibabel raises several format/IO exception types
        return False, f"segmentation unreadable: {type(error).__name__}", None
    if segmentation.ndim != 3 or not all(size > 0 for size in segmentation.shape):
        return False, f"invalid segmentation shape: {segmentation.shape}", None
    label_count = len(set(np.unique(segmentation)) - {0})
    if label_count != expected_label_count:
        return False, f"expected {expected_label_count} foreground labels, found {label_count}", label_count

    if paths.marker.is_file():
        try:
            marker = json.loads(paths.marker.read_text(encoding="utf-8"))
            expected_hashes = marker["output_sha256"]
            if marker.get("status") != "complete":
                return False, "completion marker status is not complete", label_count
            for name, path in (
                ("segmentation", paths.segmentation), ("volumes", paths.volumes), ("qc", paths.qc)
            ):
                if expected_hashes.get(name) != sha256(path):
                    return False, f"{name} checksum differs from completion marker", label_count
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            return False, f"invalid completion marker: {type(error).__name__}", label_count
    return True, "valid outputs" if paths.marker.is_file() else "valid legacy outputs (no marker)", label_count


def remove_incomplete_outputs(paths):
    """Remove only the four derived files belonging to one incomplete run."""
    removed = []
    for path in paths.derived_outputs():
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


def write_completion_marker(paths, metadata):
    """Atomically write a marker after validated inference outputs exist."""
    payload = dict(metadata)
    payload.update(
        {
            "status": "complete",
            "output_sha256": {
                "segmentation": sha256(paths.segmentation),
                "volumes": sha256(paths.volumes),
                "qc": sha256(paths.qc),
            },
        }
    )
    paths.marker.parent.mkdir(parents=True, exist_ok=True)
    temporary = paths.marker.with_suffix(paths.marker.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, paths.marker)


def execute_run(command, paths, metadata, expected_label_count=32, runner=run):
    valid, reason, _ = validate_run_outputs(paths, expected_label_count)
    if valid:
        return False, reason
    remove_incomplete_outputs(paths)
    paths.segmentation.parent.mkdir(parents=True, exist_ok=True)
    elapsed = runner(command)
    valid, reason, label_count = validate_run_outputs(paths, expected_label_count)
    if not valid:
        raise RuntimeError(f"Inference returned but outputs are incomplete: {reason}")
    write_completion_marker(
        paths,
        {
            **metadata,
            "runtime_seconds": round(float(elapsed), 3),
            "label_count": label_count,
        },
    )
    return True, "completed"


def marker_runtime(paths):
    if not paths.marker.is_file():
        return ""
    try:
        return json.loads(paths.marker.read_text(encoding="utf-8")).get("runtime_seconds", "")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return ""


def parse_runtime_adoption(value):
    try:
        key, seconds_text = value.rsplit("=", 1)
        participant, condition, mode = key.split("/")
        seconds = float(seconds_text)
    except (ValueError, TypeError) as error:
        raise ValueError(f"Invalid --adopt-runtime value: {value}") from error
    if seconds <= 0:
        raise ValueError("Adopted runtime must be positive")
    return participant, condition, mode, seconds


def adopt_valid_outputs(paths, metadata, runtime_seconds, expected_label_count=32):
    valid, reason, label_count = validate_run_outputs(paths, expected_label_count)
    if not valid:
        raise ValueError(f"Cannot adopt incomplete run: {reason}")
    if paths.marker.exists():
        raise ValueError(f"Run already has a completion marker: {paths.marker}")
    write_completion_marker(
        paths,
        {
            **metadata,
            "runtime_seconds": round(float(runtime_seconds), 3),
            "runtime_source": "observed SynthSeg console timing from prior successful run",
            "label_count": label_count,
        },
    )


def create_inputs(source, directory):
    directory.mkdir(parents=True, exist_ok=True)
    outputs = {"clean": source}
    for millimetres in (2, 3):
        name = f"resolution_{millimetres}mm"
        outputs[name] = directory / f"{name}.nii.gz"
        if not outputs[name].is_file():
            run([sys.executable, script("resample_image.py"), source, outputs[name], "--voxel-size", millimetres])
    for level in ("mild", "moderate"):
        name = f"noise_{level}"
        outputs[name] = directory / f"{name}.nii.gz"
        if not outputs[name].is_file():
            run([sys.executable, script("generate_gaussian_noise.py"), source, outputs[name], "--level", level, "--seed", 42])
    for strength in ("moderate", "strong"):
        name = f"bias_{strength}"
        outputs[name] = directory / f"{name}.nii.gz"
        if not outputs[name].is_file():
            run([sys.executable, script("generate_bias_field.py"), source, outputs[name], "--strength", strength])
    outputs["bias_strong_n4"] = directory / "bias_strong_n4.nii.gz"
    if not outputs["bias_strong_n4"].is_file():
        run([sys.executable, script("n4_correct.py"), outputs["bias_strong"], outputs["bias_strong_n4"]])
    return outputs


def first_numeric_csv_value(path):
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle), {})
    for value in row.values():
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return ""


def evaluate(clean_seg, test_seg, clean_volumes, test_volumes, expected_label_count, aligned_seg=None):
    comparison = aligned_seg or test_seg
    clean = np.asarray(nib.load(clean_seg).dataobj).astype(np.int32)
    test = np.asarray(nib.load(comparison).dataobj).astype(np.int32)
    dice, scores = compute_macro_dice(clean, test, expected_label_count=expected_label_count)
    drifts = compute_volume_drifts(read_volumes(clean_volumes), read_volumes(test_volumes))
    summary = summarize_absolute_drifts(drifts)
    return dice, len(scores), summary


def iter_run_specs(config):
    for participant in config["participants"]:
        for mode in MODES:
            for condition in CONDITIONS:
                yield participant, condition, mode


def report_resume_status(config, work_dir, expected_label_count):
    specs = list(iter_run_specs(config))
    completed = 0
    statuses = []
    for index, (participant, condition, mode) in enumerate(specs, start=1):
        paths = paths_for_run(work_dir, participant, condition, mode)
        valid, reason, _ = validate_run_outputs(paths, expected_label_count)
        completed += int(valid)
        state = "complete, would skip" if valid else f"incomplete, would rerun ({reason})"
        print(f"[{index}/{len(specs)}] {participant} {condition} {mode} - {state}")
        statuses.append((run_key(participant, condition, mode), valid, reason))
    print(f"Completed: {completed}/{len(specs)}")
    print(f"Remaining: {len(specs) - completed}/{len(specs)}")
    return statuses


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    valid_specs = set(iter_run_specs(config))
    for value in args.adopt_runtime:
        participant, condition, mode, seconds = parse_runtime_adoption(value)
        spec = (participant, condition, mode)
        if spec not in valid_specs:
            raise ValueError(f"Run key is not part of the configured experiment: {run_key(*spec)}")
        paths = paths_for_run(args.work_dir, *spec)
        source = args.data_dir / participant / "anat" / f"{participant}_T1w.nii"
        input_path = source if condition == "clean" else args.work_dir / participant / "inputs" / f"{condition}.nii.gz"
        if not input_path.is_file():
            raise FileNotFoundError(f"Cannot adopt run; input is missing: {input_path}")
        adopt_valid_outputs(
            paths,
            {
                "run_key": run_key(*spec),
                "dataset_id": config["dataset_id"],
                "dataset_version": config["snapshot"],
                "participant": participant,
                "condition": condition,
                "mode": mode,
                "input_sha256": sha256(input_path),
                "freesurfer_home": os.environ.get("FREESURFER_HOME", ""),
            },
            seconds,
            args.expected_label_count,
        )
        print(f"Adopted validated run metadata: {run_key(*spec)} ({seconds:.3f} seconds)")
    if args.check_resume:
        report_resume_status(config, args.work_dir, args.expected_label_count)
        return

    require_commands()
    records = []
    specs = list(iter_run_specs(config))
    completed = sum(
        validate_run_outputs(paths_for_run(args.work_dir, *spec), args.expected_label_count)[0]
        for spec in specs
    )
    for participant in config["participants"]:
        source = args.data_dir / participant / "anat" / f"{participant}_T1w.nii"
        if not source.is_file():
            raise FileNotFoundError(f"Missing public input; run download_public_data.py: {source}")
        inputs = create_inputs(source, args.work_dir / participant / "inputs")
        for mode in MODES:
            robust = mode == "robust"
            for condition in CONDITIONS:
                index = specs.index((participant, condition, mode)) + 1
                paths = paths_for_run(args.work_dir, participant, condition, mode)
                valid, reason, _ = validate_run_outputs(paths, args.expected_label_count)
                if valid:
                    print(f"[{index}/{len(specs)}] {participant} {condition} {mode} - already complete, skipping")
                    continue
                print(f"[{index}/{len(specs)}] {participant} {condition} {mode} - running ({reason})")
                command = [
                    sys.executable, script("run_synthseg.py"), inputs[condition],
                    paths.segmentation, paths.volumes, paths.qc,
                    *(["--robust"] if robust else []),
                ]
                ran, _ = execute_run(
                    command,
                    paths,
                    {
                        "run_key": run_key(participant, condition, mode),
                        "dataset_id": config["dataset_id"],
                        "dataset_version": config["snapshot"],
                        "participant": participant,
                        "condition": condition,
                        "mode": mode,
                        "input_sha256": sha256(inputs[condition]),
                        "freesurfer_home": os.environ.get("FREESURFER_HOME", ""),
                    },
                    args.expected_label_count,
                )
                completed += int(ran)
                print(f"Completed: {completed}/{len(specs)}; Remaining: {len(specs) - completed}/{len(specs)}")

    if completed != len(specs):
        raise RuntimeError(f"Expected {len(specs)} complete runs, found {completed}")

    for participant, condition, mode in specs:
        paths = paths_for_run(args.work_dir, participant, condition, mode)
        clean_paths = paths_for_run(args.work_dir, participant, "clean", mode)
        aligned = None
        if condition.startswith("resolution_"):
            aligned = paths.segmentation.with_name(paths.segmentation.stem + "_aligned.mgz")
            if not aligned.is_file():
                run([sys.executable, script("align_segmentation.py"), paths.segmentation, clean_paths.segmentation, aligned])
        dice, label_count, drift = evaluate(
            clean_paths.segmentation, paths.segmentation, clean_paths.volumes,
            paths.volumes, args.expected_label_count, aligned,
        )
        records.append({
            "dataset_id": config["dataset_id"],
            "dataset_version": config["snapshot"],
            "participant": participant,
            "condition": condition,
            "mode": mode,
            "runtime_seconds": marker_runtime(paths),
            "label_count": label_count,
            "clean_reference_macro_dice": f"{dice:.8f}",
            "mean_absolute_volume_drift_pct": f"{drift['mean']:.8f}",
            "median_absolute_volume_drift_pct": f"{drift['median']:.8f}",
            "qc_value": first_numeric_csv_value(paths.qc),
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    print(f"Wrote {len(records)} real run records: {args.output}")


if __name__ == "__main__":
    main()
