"""Compute foreground macro Dice between clean and perturbed segmentations."""

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np

EXPECTED_LABEL_COUNT = 32


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("clean", type=Path)
    parser.add_argument("test", type=Path)
    parser.add_argument("--expected-label-count", type=int, default=EXPECTED_LABEL_COUNT)
    parser.add_argument("--allow-label-count-mismatch", action="store_true")
    return parser.parse_args()


def compute_macro_dice(clean, test, expected_label_count=EXPECTED_LABEL_COUNT, strict=True):
    if clean.shape != test.shape:
        raise ValueError(f"Shape mismatch: {clean.shape} vs {test.shape}; align first")

    labels = sorted((set(np.unique(clean)) | set(np.unique(test))) - {0})
    if expected_label_count is not None and len(labels) != expected_label_count:
        message = f"Expected {expected_label_count} foreground labels, found {len(labels)}"
        if strict:
            raise ValueError(message)
        print(f"Warning: {message}")

    scores = {}
    for label in labels:
        a = clean == label
        b = test == label
        denominator = a.sum() + b.sum()
        if denominator:
            score = 2.0 * np.logical_and(a, b).sum() / denominator
            scores[int(label)] = float(score)

    return float(np.mean(list(scores.values()))), scores


def main():
    args = parse_args()
    clean = np.asarray(nib.load(args.clean).dataobj).astype(np.int32)
    test = np.asarray(nib.load(args.test).dataobj).astype(np.int32)
    macro_dice, scores = compute_macro_dice(
        clean,
        test,
        expected_label_count=args.expected_label_count,
        strict=not args.allow_label_count_mismatch,
    )

    for label, score in scores.items():
        print(f"Label {label:3d}: {score * 100:.2f}%")

    print(f"Labels evaluated: {len(scores)}")
    print(f"Foreground Macro Dice: {macro_dice * 100:.2f}%")


if __name__ == "__main__":
    main()
