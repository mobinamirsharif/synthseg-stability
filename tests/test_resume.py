import csv
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from scripts.run_public_experiment import (
    adopt_valid_outputs,
    execute_run,
    paths_for_run,
    parse_runtime_adoption,
    remove_incomplete_outputs,
    run_key,
    validate_run_outputs,
)


def write_valid_outputs(paths):
    paths.segmentation.parent.mkdir(parents=True, exist_ok=True)
    labels = np.arange(33, dtype=np.int16).reshape(33, 1, 1)
    nib.save(nib.Nifti1Image(labels, np.eye(4)), paths.segmentation)
    for path, columns in (
        (paths.volumes, ("subject", "left", "right")),
        (paths.qc, ("subject", "score")),
    ):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerow({name: index + 1 for index, name in enumerate(columns)})


def test_run_key_and_paths_are_deterministic(tmp_path):
    assert run_key("sub-01", "clean", "standard") == "sub-01/clean/standard"
    paths = paths_for_run(tmp_path, "sub-01", "clean", "standard")
    assert paths.segmentation == tmp_path / "sub-01/outputs/standard/clean.mgz"
    assert paths.marker == tmp_path / "sub-01/outputs/standard/clean_complete.json"


def test_completed_run_is_skipped(tmp_path):
    paths = paths_for_run(tmp_path, "sub-01", "clean", "standard")
    write_valid_outputs(paths)

    def must_not_run(_):
        raise AssertionError("runner must not be called for valid completed outputs")

    ran, reason = execute_run([], paths, {}, runner=must_not_run)
    assert ran is False
    assert reason == "valid legacy outputs (no marker)"


def test_partial_run_is_not_complete_and_is_rerun(tmp_path):
    paths = paths_for_run(tmp_path, "sub-01", "resolution_2mm", "standard")
    paths.volumes.parent.mkdir(parents=True)
    paths.volumes.write_text("subject,left\n", encoding="utf-8")
    paths.qc.write_text("subject,score\n", encoding="utf-8")
    valid, reason, _ = validate_run_outputs(paths)
    assert valid is False
    assert "missing" in reason

    calls = []

    def successful_runner(command):
        calls.append(command)
        write_valid_outputs(paths)
        return 12.3456

    ran, _ = execute_run(["fake-synthseg"], paths, {"run_key": "test"}, runner=successful_runner)
    assert ran is True
    assert calls == [["fake-synthseg"]]
    assert paths.marker.is_file()
    marker = json.loads(paths.marker.read_text(encoding="utf-8"))
    assert marker["status"] == "complete"
    assert marker["runtime_seconds"] == 12.346


def test_completion_marker_is_not_written_after_failure(tmp_path):
    paths = paths_for_run(tmp_path, "sub-01", "noise_mild", "robust")

    def failing_runner(_):
        paths.volumes.parent.mkdir(parents=True, exist_ok=True)
        paths.volumes.write_text("subject,left\n", encoding="utf-8")
        raise RuntimeError("simulated inference failure")

    with pytest.raises(RuntimeError, match="simulated inference failure"):
        execute_run([], paths, {}, runner=failing_runner)
    assert not paths.marker.exists()


def test_cleanup_is_scoped_to_one_run(tmp_path):
    incomplete = paths_for_run(tmp_path, "sub-01", "resolution_3mm", "standard")
    unrelated = paths_for_run(tmp_path, "sub-01", "clean", "robust")
    incomplete.volumes.parent.mkdir(parents=True)
    incomplete.volumes.write_text("partial", encoding="utf-8")
    write_valid_outputs(unrelated)

    removed = remove_incomplete_outputs(incomplete)
    assert removed == [incomplete.volumes]
    assert unrelated.segmentation.exists()
    assert unrelated.volumes.exists()
    assert unrelated.qc.exists()


def test_modified_output_invalidates_marker(tmp_path):
    paths = paths_for_run(tmp_path, "sub-02", "clean", "standard")

    def successful_runner(_):
        write_valid_outputs(paths)
        return 1.0

    execute_run([], paths, {"run_key": "sub-02/clean/standard"}, runner=successful_runner)
    paths.qc.write_text("subject,score\n1,changed\n", encoding="utf-8")
    valid, reason, _ = validate_run_outputs(paths)
    assert valid is False
    assert "checksum differs" in reason


def test_runtime_adoption_requires_real_valid_outputs(tmp_path):
    paths = paths_for_run(tmp_path, "sub-01", "clean", "standard")
    with pytest.raises(ValueError, match="Cannot adopt incomplete run"):
        adopt_valid_outputs(paths, {"run_key": "test"}, 440)
    assert not paths.marker.exists()

    write_valid_outputs(paths)
    adopt_valid_outputs(paths, {"run_key": "test"}, 440)
    marker = json.loads(paths.marker.read_text(encoding="utf-8"))
    assert marker["runtime_seconds"] == 440.0
    assert marker["runtime_source"].startswith("observed SynthSeg")


def test_runtime_adoption_argument_parsing():
    assert parse_runtime_adoption("sub-01/clean/standard=440") == (
        "sub-01", "clean", "standard", 440.0
    )
    with pytest.raises(ValueError, match="Invalid"):
        parse_runtime_adoption("not-a-run")
