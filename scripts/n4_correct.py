"""Apply the Phase 3 N4 configuration to a strong-bias image."""

import argparse
from pathlib import Path

import SimpleITK as sitk


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def configure_corrector():
    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrector.SetMaximumNumberOfIterations([50, 50, 30, 20])
    return corrector


def correct_image(image):
    """Correct a float image using the experiment's fixed mask and schedule."""
    mask = sitk.OtsuThreshold(image, 0, 1, 200)
    return configure_corrector().Execute(image, mask)


def main():
    args = parse_args()
    image = sitk.ReadImage(str(args.input), sitk.sitkFloat32)
    corrected = correct_image(image)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(corrected, str(args.output))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
