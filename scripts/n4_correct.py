"""Apply the Phase 3 N4 configuration to a strong-bias image."""

import argparse
from pathlib import Path

import SimpleITK as sitk


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    image = sitk.ReadImage(str(args.input), sitk.sitkFloat32)
    mask = sitk.OtsuThreshold(image, 0, 1, 200)
    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrector.SetMaximumNumberOfIterations([50, 50, 30, 20])
    corrected = corrector.Execute(image, mask)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(corrected, str(args.output))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()

