"""Compute percentage volume drift relative to a clean-mode reference."""

import argparse
import csv
from pathlib import Path

import numpy as np


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("clean", type=Path)
    parser.add_argument("test", type=Path)
    return parser.parse_args()


def read_volumes(path):
    with path.open(newline="") as handle:
        row = next(csv.DictReader(handle))
    values = {}
    for key, value in row.items():
        if key is None or key.lower() == "subject":
            continue
        try:
            values[key] = float(value)
        except (TypeError, ValueError):
            continue
    return values


def compute_volume_drifts(clean, test):
    drifts = {}
    for metric in sorted(set(clean) & set(test)):
        if clean[metric] == 0:
            continue
        drifts[metric] = (test[metric] - clean[metric]) / clean[metric] * 100.0
    return drifts


def summarize_absolute_drifts(drifts):
    values = np.abs(list(drifts.values()))
    return {
        "count": len(values),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
    }


def main():
    args = parse_args()
    clean = read_volumes(args.clean)
    test = read_volumes(args.test)
    drifts = compute_volume_drifts(clean, test)
    summary = summarize_absolute_drifts(drifts)
    for metric, drift in drifts.items():
        print(f"{metric}: {drift:+.3f}%")
    print(f"Metrics evaluated: {summary['count']}")
    print(f"Mean absolute volume drift: {summary['mean']:.3f}%")
    print(f"Median absolute volume drift: {summary['median']:.3f}%")


if __name__ == "__main__":
    main()
