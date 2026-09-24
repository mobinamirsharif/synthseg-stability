"""Validate and aggregate completed public experiment records."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("condition", "mode")
METRICS = (
    "clean_reference_macro_dice",
    "mean_absolute_volume_drift_pct",
    "median_absolute_volume_drift_pct",
    "runtime_seconds",
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=REPO_ROOT / "results/public/subject_level/results.csv")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "results/public/aggregate/summary.csv")
    parser.add_argument(
        "--cohort-output",
        type=Path,
        default=REPO_ROOT / "results/public/aggregate/cohort_summary.csv",
    )
    return parser.parse_args()


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in GROUPS)].append(row)
    output = []
    for key, group in sorted(grouped.items()):
        record = dict(zip(GROUPS, key))
        record["n_participants"] = len({row["participant"] for row in group})
        for metric in METRICS:
            values = np.asarray([float(row[metric]) for row in group], dtype=float)
            record[f"mean_{metric}"] = f"{values.mean():.8f}"
            record[f"median_{metric}"] = f"{np.median(values):.8f}"
        output.append(record)
    return output


def cohort_summary(rows):
    indexed = {
        (row["participant"], row["condition"], row["mode"]): row for row in rows
    }
    participants = sorted({row["participant"] for row in rows})
    conditions = sorted({row["condition"] for row in rows})
    output = []
    for condition in conditions:
        pairs = [
            (
                indexed[(participant, condition, "standard")],
                indexed[(participant, condition, "robust")],
            )
            for participant in participants
        ]
        standard_dice = np.asarray([float(pair[0]["clean_reference_macro_dice"]) for pair in pairs]) * 100
        robust_dice = np.asarray([float(pair[1]["clean_reference_macro_dice"]) for pair in pairs]) * 100
        standard_drift = np.asarray([float(pair[0]["mean_absolute_volume_drift_pct"]) for pair in pairs])
        robust_drift = np.asarray([float(pair[1]["mean_absolute_volume_drift_pct"]) for pair in pairs])
        standard_runtime = np.asarray([float(pair[0]["runtime_seconds"]) for pair in pairs])
        robust_runtime = np.asarray([float(pair[1]["runtime_seconds"]) for pair in pairs])
        output.append(
            {
                "condition": condition,
                "n_participants": len(participants),
                "standard_mean_clean_reference_dice_pct": f"{standard_dice.mean():.6f}",
                "robust_mean_clean_reference_dice_pct": f"{robust_dice.mean():.6f}",
                "robust_minus_standard_dice_pp": f"{(robust_dice - standard_dice).mean():.6f}",
                "standard_mean_absolute_volume_drift_pct": f"{standard_drift.mean():.6f}",
                "robust_mean_absolute_volume_drift_pct": f"{robust_drift.mean():.6f}",
                "robust_minus_standard_volume_drift_pp": f"{(robust_drift - standard_drift).mean():.6f}",
                "standard_mean_runtime_seconds": f"{standard_runtime.mean():.3f}",
                "robust_mean_runtime_seconds": f"{robust_runtime.mean():.3f}",
            }
        )
    return output


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("No public experiment records were found")
    output = summarize(rows)
    cohort = cohort_summary(rows)
    write_rows(args.output, output)
    write_rows(args.cohort_output, cohort)
    print(f"Wrote {len(output)} aggregate rows: {args.output}")
    print(f"Wrote {len(cohort)} cohort rows: {args.cohort_output}")


if __name__ == "__main__":
    main()
