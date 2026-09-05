import json
from pathlib import Path

import pytest

from scripts.download_public_data import load_config, t1w_url
from scripts.n4_correct import configure_corrector
from scripts.plot_public_results import paired_plot
from scripts.run_public_experiment import CONDITIONS, MODES, RESULT_COLUMNS, require_commands
from scripts.summarize_public_results import cohort_summary, summarize


ROOT = Path(__file__).resolve().parents[1]


def test_public_manifest_is_pinned_and_cc0():
    config = load_config(ROOT / "config/public_dataset.json")
    assert config["dataset_id"] == "ds005125"
    assert config["snapshot"] == "1.0.0"
    assert config["license"] == "CC0-1.0"
    assert config["participants"] == ["sub-01", "sub-02", "sub-03", "sub-04"]
    assert config["doi"] == "10.18112/openneuro.ds005125.v1.0.0"
    assert set(config["sha256"]) == set(config["participants"])
    assert all(len(value) == 64 for value in config["sha256"].values())


def test_public_download_url_is_deterministic():
    config = load_config(ROOT / "config/public_dataset.json")
    assert t1w_url(config, "sub-01") == (
        "https://s3.amazonaws.com/openneuro.org/ds005125/sub-01/anat/sub-01_T1w.nii"
    )


def test_public_design_has_all_required_conditions_and_modes():
    assert set(CONDITIONS) == {
        "clean", "resolution_2mm", "resolution_3mm", "noise_mild",
        "noise_moderate", "bias_moderate", "bias_strong", "bias_strong_n4",
    }
    assert MODES == ("standard", "robust")
    assert {"participant", "label_count", "clean_reference_macro_dice",
            "mean_absolute_volume_drift_pct", "median_absolute_volume_drift_pct"} <= set(RESULT_COLUMNS)


def test_missing_freesurfer_commands_fail_before_work(monkeypatch):
    monkeypatch.setattr("scripts.run_public_experiment.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="mri_convert, mri_synthseg"):
        require_commands()


def test_n4_iteration_schedule_is_fixed():
    assert list(configure_corrector().GetMaximumNumberOfIterations()) == [50, 50, 30, 20]


def test_public_aggregation_known_case():
    rows = []
    for participant, dice, drift in (("sub-a", 0.8, 2.0), ("sub-b", 1.0, 4.0)):
        rows.append({
            "participant": participant, "condition": "noise_mild", "mode": "standard",
            "clean_reference_macro_dice": str(dice),
            "mean_absolute_volume_drift_pct": str(drift),
            "median_absolute_volume_drift_pct": str(drift / 2),
            "runtime_seconds": "10",
        })
    result = summarize(rows)[0]
    assert result["n_participants"] == 2
    assert float(result["mean_clean_reference_macro_dice"]) == pytest.approx(0.9)
    assert float(result["mean_mean_absolute_volume_drift_pct"]) == pytest.approx(3.0)


def test_paired_cohort_summary_known_case():
    rows = []
    for participant, standard, robust in (("sub-a", 0.80, 0.85), ("sub-b", 0.90, 0.92)):
        for mode, dice, drift in (("standard", standard, 4.0), ("robust", robust, 3.0)):
            rows.append({
                "participant": participant, "condition": "noise_mild", "mode": mode,
                "clean_reference_macro_dice": str(dice),
                "mean_absolute_volume_drift_pct": str(drift),
                "runtime_seconds": "10",
            })
    result = cohort_summary(rows)[0]
    assert float(result["standard_mean_clean_reference_dice_pct"]) == pytest.approx(85.0)
    assert float(result["robust_mean_clean_reference_dice_pct"]) == pytest.approx(88.5)
    assert float(result["robust_minus_standard_dice_pp"]) == pytest.approx(3.5)
    assert float(result["robust_minus_standard_volume_drift_pp"]) == pytest.approx(-1.0)


def test_manifest_is_valid_json():
    json.loads((ROOT / "config/public_dataset.json").read_text(encoding="utf-8"))


def test_public_paired_plot_accepts_four_participants(tmp_path):
    rows = []
    for participant_index in range(4):
        for condition in (
            "resolution_2mm", "resolution_3mm", "noise_mild", "noise_moderate",
            "bias_moderate", "bias_strong", "bias_strong_n4",
        ):
            for mode, offset in (("standard", 0.0), ("robust", 0.01)):
                rows.append({
                    "participant": f"public-{participant_index}",
                    "condition": condition,
                    "mode": mode,
                    "metric": str(0.9 + offset),
                })
    output = tmp_path / "paired.png"
    paired_plot(rows, "metric", "Metric (%)", output, scale=100)
    assert output.is_file()
    assert output.stat().st_size > 0
