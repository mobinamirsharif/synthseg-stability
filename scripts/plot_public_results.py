"""Create public-data point and paired-difference plots from committed CSVs."""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
ORDER = [
    "resolution_2mm", "resolution_3mm", "noise_mild", "noise_moderate",
    "bias_moderate", "bias_strong", "bias_strong_n4",
]
LABELS = ["2 mm", "3 mm", "Noise 5%", "Noise 10%", "Moderate bias", "Strong bias", "Strong bias + N4"]
COLORS = {"standard": "#2878B5", "robust": "#E07A1F"}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=REPO_ROOT / "results/public/subject_level/results.csv")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "figures/public")
    return parser.parse_args()


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def paired_plot(rows, metric, ylabel, filename, scale=1.0):
    lookup = {(r["participant"], r["condition"], r["mode"]): float(r[metric]) * scale for r in rows}
    participants = sorted({r["participant"] for r in rows})
    fig, (ax, delta) = plt.subplots(2, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for x, condition in enumerate(ORDER):
        offsets = np.linspace(-0.16, 0.16, max(len(participants), 1))
        differences = []
        for offset, participant in zip(offsets, participants):
            standard = lookup[(participant, condition, "standard")]
            robust = lookup[(participant, condition, "robust")]
            ax.plot([x - 0.13 + offset / 4, x + 0.13 + offset / 4], [standard, robust], color="#A7A7A7", lw=0.8, zorder=1)
            ax.scatter(x - 0.13 + offset / 4, standard, color=COLORS["standard"], marker="o", s=28, zorder=2)
            ax.scatter(x + 0.13 + offset / 4, robust, color=COLORS["robust"], marker="D", s=25, zorder=2)
            differences.append(robust - standard)
        delta.scatter(np.full(len(differences), x), differences, color="#3F3F3F", s=24)
        delta.plot([x - 0.2, x + 0.2], [np.mean(differences)] * 2, color="#B22222", lw=2)
    ax.scatter([], [], color=COLORS["standard"], marker="o", label="Standard")
    ax.scatter([], [], color=COLORS["robust"], marker="D", label="Robust")
    ax.set_ylabel(ylabel)
    ax.set_title("OpenNeuro ds005125 public replication")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    delta.axhline(0, color="#777777", lw=0.8)
    delta.set_ylabel("Robust −\nStandard")
    delta.set_xticks(range(len(LABELS)), LABELS, rotation=25, ha="right")
    delta.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(filename, dpi=220)
    plt.close(fig)


def main():
    args = parse_args()
    rows = [row for row in read_rows(args.input) if row["condition"] != "clean"]
    if not rows:
        raise ValueError("No non-clean public records to plot")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paired_plot(rows, "clean_reference_macro_dice", "Clean-reference macro Dice (%)", args.output_dir / "clean_reference_dice.png", scale=100)
    paired_plot(rows, "mean_absolute_volume_drift_pct", "Mean absolute volume drift (%)", args.output_dir / "mean_volume_drift.png")
    print(f"Saved public figures to {args.output_dir}")


if __name__ == "__main__":
    main()
