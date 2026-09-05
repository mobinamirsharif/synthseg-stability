"""Generate the controlled synthetic intensity non-uniformity inputs."""

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strength", choices=("moderate", "strong"), required=True)
    return parser.parse_args()


def make_bias_field(shape, strength):
    x = np.linspace(-1, 1, shape[0])[:, None, None]

    if strength == "moderate":
        y = np.linspace(-1, 1, shape[1])[None, :, None]
        return np.clip(1.0 + 0.30 * x + 0.10 * y, 0.60, 1.40)
    if strength == "strong":
        return np.clip(1.0 + 0.55 * x, 0.45, 1.55)
    raise ValueError(f"Unknown bias-field strength: {strength}")


def apply_bias_field(data, strength):
    field = make_bias_field(data.shape, strength)
    biased = np.asarray(data) * field
    biased[np.asarray(data) == 0] = 0
    return biased, field


def main():
    args = parse_args()
    image = nib.load(args.input)
    data = image.get_fdata()
    biased, field = apply_bias_field(data, args.strength)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = nib.Nifti1Image(biased.astype(np.float32), image.affine, image.header)
    output.set_data_dtype(np.float32)
    nib.save(output, args.output)
    print(f"Saved: {args.output}")
    print(f"Bias range: {field.min():.3f} to {field.max():.3f}")


if __name__ == "__main__":
    main()
