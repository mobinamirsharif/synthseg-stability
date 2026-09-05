"""Run the FreeSurfer mri_convert resampling used in Phase 2."""

import argparse
import shutil
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--voxel-size", type=int, choices=(2, 3), required=True)
    return parser.parse_args()


def build_command(executable, input_path, output_path, voxel_size):
    size = str(voxel_size)
    return [
        executable,
        str(input_path),
        str(output_path),
        "--voxsize",
        size,
        size,
        size,
        "--resample_type",
        "cubic",
    ]


def main():
    args = parse_args()
    executable = shutil.which("mri_convert")
    if executable is None:
        raise RuntimeError("mri_convert was not found on PATH; install/configure FreeSurfer")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = build_command(executable, args.input, args.output, args.voxel_size)
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
