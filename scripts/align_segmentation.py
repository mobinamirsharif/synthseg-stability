"""Align a test segmentation to its same-mode clean-reference grid."""

import argparse
import shutil
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Resample a degraded-input segmentation onto the corresponding "
            "clean-reference grid using nearest-neighbor interpolation."
        )
    )
    parser.add_argument("test_segmentation", type=Path)
    parser.add_argument("clean_reference", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def build_command(executable, test_segmentation, clean_reference, output):
    return [
        executable,
        str(test_segmentation),
        str(output),
        "--like",
        str(clean_reference),
        "--resample_type",
        "nearest",
    ]


def main():
    args = parse_args()
    executable = shutil.which("mri_convert")
    if executable is None:
        raise RuntimeError("mri_convert was not found on PATH; install/configure FreeSurfer")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = build_command(
        executable,
        args.test_segmentation,
        args.clean_reference,
        args.output,
    )
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
