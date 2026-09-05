"""Generate an orthogonal-slice QC contact sheet from public OpenNeuro runs."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("sub-01", "clean", "standard"),
    ("sub-01", "clean", "robust"),
    ("sub-01", "noise_moderate", "standard"),
    ("sub-01", "bias_strong", "standard"),
    ("sub-02", "clean", "standard"),
    ("sub-03", "noise_moderate", "robust"),
    ("sub-04", "bias_strong_n4", "robust"),
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data/public")
    parser.add_argument("--work-dir", type=Path, default=REPO_ROOT / "work/public")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "figures/public/public_qc_contact_sheet.png",
    )
    return parser.parse_args()


def input_path(data_dir, work_dir, participant, condition):
    if condition == "clean":
        return data_dir / participant / "anat" / f"{participant}_T1w.nii"
    return work_dir / participant / "inputs" / f"{condition}.nii.gz"


def segmentation_path(work_dir, participant, condition, mode):
    return work_dir / participant / "outputs" / mode / f"{condition}.mgz"


def centre_of_segmentation(segmentation):
    coordinates = np.argwhere(segmentation != 0)
    if coordinates.size == 0:
        raise ValueError("Segmentation contains no foreground voxels")
    return tuple(np.round(np.median(coordinates, axis=0)).astype(int))


def display_slice(array, axis, index):
    return np.rot90(np.take(array, index, axis=axis))


def plot_contact_sheet(data_dir, work_dir, output):
    fig, axes = plt.subplots(len(CASES), 3, figsize=(10.5, 18), constrained_layout=True)
    plane_names = ("Sagittal", "Coronal", "Axial")
    for row, (participant, condition, mode) in enumerate(CASES):
        image = np.asarray(nib.load(input_path(data_dir, work_dir, participant, condition)).dataobj)
        segmentation = np.asarray(
            nib.load(segmentation_path(work_dir, participant, condition, mode)).dataobj
        )
        if image.shape != segmentation.shape:
            raise ValueError(
                f"QC overlay geometry mismatch for {participant}/{condition}/{mode}: "
                f"{image.shape} vs {segmentation.shape}"
            )
        centre = centre_of_segmentation(segmentation)
        foreground = image[segmentation != 0]
        low, high = np.percentile(foreground, (1, 99))
        for axis, ax in enumerate(axes[row]):
            anatomy = display_slice(image, axis, centre[axis])
            mask = display_slice(segmentation != 0, axis, centre[axis])
            ax.imshow(anatomy, cmap="gray", vmin=low, vmax=high, interpolation="nearest")
            ax.contour(mask.astype(float), levels=[0.5], colors=["#00E5FF"], linewidths=0.65)
            if row == 0:
                ax.set_title(plane_names[axis])
            ax.set_axis_off()
        axes[row, 0].text(
            -0.08,
            0.5,
            f"{participant}\n{condition}\n{mode}",
            transform=axes[row, 0].transAxes,
            ha="right",
            va="center",
            fontsize=9,
        )
    fig.suptitle("OpenNeuro ds005125 v1.0.0 — public segmentation QC", fontsize=14)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)
    print(f"Saved: {output}")


def main():
    args = parse_args()
    plot_contact_sheet(args.data_dir, args.work_dir, args.output)


if __name__ == "__main__":
    main()
