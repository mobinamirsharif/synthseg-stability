from pathlib import Path

from scripts.align_segmentation import build_command as alignment_command
from scripts.resample_image import build_command as resampling_command
from scripts.run_synthseg import build_command as synthseg_command


def test_standard_synthseg_command():
    command = synthseg_command("mri_synthseg", "input.nii.gz", "seg.mgz", "vol.csv", "qc.csv")
    assert command == [
        "mri_synthseg", "--i", "input.nii.gz", "--o", "seg.mgz",
        "--vol", "vol.csv", "--qc", "qc.csv", "--threads", "1",
    ]


def test_robust_synthseg_command():
    command = synthseg_command(
        "mri_synthseg", "input.nii.gz", "seg.mgz", "vol.csv", "qc.csv", robust=True
    )
    assert command[-1] == "--robust"
    assert command.count("--robust") == 1


def test_cubic_resampling_command():
    command = resampling_command("mri_convert", Path("in.nii.gz"), Path("out.nii.gz"), 2)
    assert command[3:] == ["--voxsize", "2", "2", "2", "--resample_type", "cubic"]


def test_nearest_neighbor_alignment_command():
    command = alignment_command("mri_convert", "test.mgz", "clean.mgz", "aligned.mgz")
    assert command == [
        "mri_convert", "test.mgz", "aligned.mgz", "--like", "clean.mgz",
        "--resample_type", "nearest",
    ]
