"""Generate the controlled Gaussian-noise inputs used in Phase 2."""

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Source T1-weighted NIfTI image")
    parser.add_argument("output", type=Path, help="Destination NIfTI image")
    parser.add_argument(
        "--level",
        choices=("mild", "moderate"),
        required=True,
        help="mild = 0.05 x non-zero SD; moderate = 0.10 x non-zero SD",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def generate_gaussian_noise(data, level, seed=42):
    fraction = {"mild": 0.05, "moderate": 0.10}[level]
    data = np.asarray(data, dtype=np.float32)
    mask = data != 0
    if not np.any(mask):
        raise ValueError("Input contains no non-zero voxels")

    sigma = fraction * np.std(data[mask])
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, sigma, size=data.shape).astype(np.float32)
    noisy = data.copy()
    noisy[mask] += noise[mask]
    noisy[~mask] = 0
    return noisy, float(sigma)


def main():
    args = parse_args()
    image = nib.load(args.input)
    data = image.get_fdata().astype(np.float32)
    noisy, sigma = generate_gaussian_noise(data, args.level, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = nib.Nifti1Image(noisy, image.affine, image.header)
    output.set_data_dtype(np.float32)
    nib.save(output, args.output)

    print(f"Saved: {args.output}")
    print(f"Level: {args.level}; seed: {args.seed}; sigma: {sigma:.4f}")


if __name__ == "__main__":
    main()
