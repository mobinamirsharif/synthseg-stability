"""Regenerate the public aggregate-only Phase 2 figures."""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ["lowres_2mm", "lowres_3mm", "noise_mild", "noise_moderate"]
LABELS = ["2 mm", "3 mm", "Noise 5%", "Noise 10%"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def aggregate_plot(rows, standard_column, robust_column, ylabel, title, output, decimals):
    indexed = {row["condition"]: row for row in rows}
    standard = [float(indexed[condition][standard_column]) for condition in CONDITIONS]
    robust = [float(indexed[condition][robust_column]) for condition in CONDITIONS]
    x = np.arange(len(LABELS))
    width = 0.34

    fig, ax = plt.subplots(figsize=(10, 6))
    for offset, name, values, color in (
        (-width / 2, "Standard", standard, "#2878B5"),
        (width / 2, "Robust", robust, "#F28E2B"),
    ):
        bars = ax.bar(x + offset, values, width, label=name, color=color)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value,
                f"{value:.{decimals}f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(x, LABELS)
    ax.set_ylim(bottom=0)
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(f"Saved: {output}")


def phase2(root):
    results = root / "results" / "phase2"
    figures = root / "figures" / "phase2"
    figures.mkdir(parents=True, exist_ok=True)

    aggregate_plot(
        read_rows(results / "aggregate_macro_dice.csv"),
        "mean_standard_macro_dice",
        "mean_robust_macro_dice",
        "Mean Macro Dice (%)",
        "Phase 2 Spatial Stability (Mean Across Two Acquisitions)",
        figures / "aggregate_macro_dice.png",
        decimals=3,
    )
    aggregate_plot(
        read_rows(results / "aggregate_volume_drift.csv"),
        "mean_standard_absolute_volume_drift_pct",
        "mean_robust_absolute_volume_drift_pct",
        "Mean Absolute Volume Drift (%)",
        "Phase 2 Volumetric Stability (Mean Across Two Acquisitions)",
        figures / "aggregate_volume_drift.png",
        decimals=4,
    )


def main():
    phase2(parse_args().repo_root.resolve())


if __name__ == "__main__":
    main()
