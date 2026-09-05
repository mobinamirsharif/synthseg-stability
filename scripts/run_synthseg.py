"""Run standard SynthSeg or SynthSeg-robust with the Phase 1-3 settings."""

import argparse
import shutil
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_segmentation", type=Path)
    parser.add_argument("output_volumes", type=Path)
    parser.add_argument("output_qc", type=Path)
    parser.add_argument("--robust", action="store_true")
    return parser.parse_args()


def build_command(executable, input_path, segmentation, volumes, qc, robust=False):
    command = [
        executable,
        "--i", str(input_path),
        "--o", str(segmentation),
        "--vol", str(volumes),
        "--qc", str(qc),
        "--threads", "1",
    ]
    if robust:
        command.append("--robust")
    return command


def main():
    args = parse_args()
    executable = shutil.which("mri_synthseg")
    if executable is None:
        raise RuntimeError("mri_synthseg was not found on PATH; install/configure FreeSurfer")

    for path in (args.output_segmentation, args.output_volumes, args.output_qc):
        path.parent.mkdir(parents=True, exist_ok=True)

    command = build_command(
        executable,
        args.input,
        args.output_segmentation,
        args.output_volumes,
        args.output_qc,
        args.robust,
    )

    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
