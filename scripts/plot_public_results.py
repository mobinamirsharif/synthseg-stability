"""Create public-data point and paired-difference plots from committed CSVs."""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
GROUPS = (
    ("Resolution", ("resolution_2mm", "resolution_3mm"), ("2 mm", "3 mm")),
    ("Noise", ("noise_mild", "noise_moderate"), ("Noise 5%", "Noise 10%")),
    ("Bias", ("bias_moderate", "bias_strong", "bias_strong_n4"),
     ("Moderate\nbias", "Strong\nbias", "Strong bias\n+ N4")),
)
COLORS = {"standard": "#2474A6", "robust": "#E67E22"}
MEAN_COLOR = "#8E2C2C"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=REPO_ROOT / "results/public/subject_level/results.csv")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "figures/public")
    return parser.parse_args()


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def style_axis(axis):
    axis.set_facecolor("white")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color="#D9DEE3", linewidth=0.7, alpha=0.75)
    axis.set_axisbelow(True)


def draw_group(axis, lookup, participants, conditions, labels, ylabel, show_y_label):
    width = 0.32
    standard_means = []
    robust_means = []
    for x, condition in enumerate(conditions):
        standard = np.asarray([lookup[(participant, condition, "standard")] for participant in participants])
        robust = np.asarray([lookup[(participant, condition, "robust")] for participant in participants])
        standard_mean = float(np.mean(standard))
        robust_mean = float(np.mean(robust))
        standard_means.append(standard_mean)
        robust_means.append(robust_mean)
        mean_difference = float(np.mean(robust - standard))
        axis.annotate(
            f"Δ {mean_difference:+.2f} pp", xy=(x, max(standard_mean, robust_mean)),
            xytext=(0, 8), textcoords="offset points", ha="center", va="bottom",
            fontsize=8, color=MEAN_COLOR, annotation_clip=False,
        )

    positions = np.arange(len(conditions))
    axis.bar(positions - width / 2, standard_means, width, color=COLORS["standard"], label="Standard", zorder=2)
    axis.bar(positions + width / 2, robust_means, width, color=COLORS["robust"], label="Robust", zorder=2)
    if show_y_label:
        axis.set_ylabel(ylabel)
    axis.set_xticks(positions, labels)
    axis.tick_params(axis="x", pad=7)
    axis.set_xlim(-0.55, len(labels) - 0.45)
    highest = max(standard_means + robust_means)
    axis.set_ylim(0, highest + max(highest * 0.045, 0.16))
    style_axis(axis)


def paired_plot(rows, metric, ylabel, filename, scale=1.0, title="OpenNeuro public replication"):
    lookup = {(r["participant"], r["condition"], r["mode"]): float(r[metric]) * scale for r in rows}
    participants = sorted({r["participant"] for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.15), gridspec_kw={"width_ratios": [2, 2, 3]})
    fig.patch.set_facecolor("white")
    for column, (group_title, conditions, labels) in enumerate(GROUPS):
        draw_group(
            axes[column], lookup, participants, conditions, labels,
            ylabel, show_y_label=column == 0,
        )
        axes[column].set_title(group_title, fontsize=10.5, fontweight="bold", pad=7)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=COLORS["standard"], label="Standard"),
        plt.Rectangle((0, 0), 1, 1, color=COLORS["robust"], label="Robust"),
    ]
    fig.suptitle(title, fontsize=12.5, fontweight="bold", y=0.985)
    fig.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.94),
        ncol=2, frameon=False, fontsize=9, handletextpad=0.5, columnspacing=1.2,
    )
    fig.subplots_adjust(left=0.065, right=0.992, bottom=0.13, top=0.79, wspace=0.18)
    fig.savefig(filename, dpi=300, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()
    rows = [row for row in read_rows(args.input) if row["condition"] != "clean"]
    if not rows:
        raise ValueError("No non-clean public records to plot")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paired_plot(
        rows, "clean_reference_macro_dice", "Macro Dice (%)",
        args.output_dir / "clean_reference_dice.png", scale=100,
        title="Clean-reference segmentation stability",
    )
    paired_plot(
        rows, "mean_absolute_volume_drift_pct", "Volume drift (%)",
        args.output_dir / "mean_volume_drift.png", title="Mean absolute volume drift",
    )
    print(f"Saved public figures to {args.output_dir}")


if __name__ == "__main__":
    main()
