import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DICE = {
    "lowres_2mm": (2, 87.860, 88.465, 0.605),
    "lowres_3mm": (2, 88.645, 89.485, 0.840),
    "noise_mild": (2, 98.875, 99.070, 0.195),
    "noise_moderate": (2, 97.745, 98.310, 0.565),
}

EXPECTED_DRIFT = {
    "lowres_2mm": (2, 3.4060, 1.8560, -1.5500),
    "lowres_3mm": (2, 4.4370, 4.0010, -0.4360),
    "noise_mild": (2, 0.4590, 0.3110, -0.1480),
    "noise_moderate": (2, 0.9085, 0.6230, -0.2855),
}

PRIVATE_ARTIFACTS = (
    "results/phase2/two_subject_summary.csv",
    "results/phase2/two_subject_volume_drift_summary.csv",
    "results/phase3/phase3_summary.csv",
    "figures/phase2/two_subject_macro_dice.png",
    "figures/phase2/two_subject_volume_drift.png",
    "figures/phase3/phase3_macro_dice.png",
    "figures/phase3/phase3_volume_drift.png",
)


def read_rows(relative_path):
    with (ROOT / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_restricted_phase2_aggregate_dice_values_are_preserved():
    rows = read_rows("results/restricted/phase2/aggregate_macro_dice.csv")
    actual = {
        row["condition"]: (
            int(row["n_acquisitions"]),
            float(row["mean_standard_macro_dice"]),
            float(row["mean_robust_macro_dice"]),
            float(row["mean_robust_minus_standard_pp"]),
        )
        for row in rows
    }
    assert actual == EXPECTED_DICE


def test_restricted_phase2_aggregate_volume_drift_values_are_preserved():
    rows = read_rows("results/restricted/phase2/aggregate_volume_drift.csv")
    actual = {
        row["condition"]: (
            int(row["n_acquisitions"]),
            float(row["mean_standard_absolute_volume_drift_pct"]),
            float(row["mean_robust_absolute_volume_drift_pct"]),
            float(row["mean_robust_minus_standard_pp"]),
        )
        for row in rows
    }
    assert actual == EXPECTED_DRIFT


def test_private_result_artifacts_are_not_tracked():
    tracked = set(
        subprocess.run(
            ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.splitlines()
    )
    assert tracked.isdisjoint(PRIVATE_ARTIFACTS)
    assert not any(path.startswith("results/phase2/supporting/") for path in tracked)


def test_restricted_aggregate_figures_exist():
    assert (ROOT / "figures/restricted/phase2/aggregate_macro_dice.png").is_file()
    assert (ROOT / "figures/restricted/phase2/aggregate_volume_drift.png").is_file()


def test_completed_public_artifacts_are_consistent():
    subject_rows = read_rows("results/public/subject_level/results.csv")
    aggregate_rows = read_rows("results/public/aggregate/summary.csv")
    cohort_rows = read_rows("results/public/aggregate/cohort_summary.csv")
    assert len(subject_rows) == 64
    assert len(aggregate_rows) == 16
    assert len(cohort_rows) == 8
    assert {row["participant"] for row in subject_rows} == {
        "sub-01", "sub-02", "sub-03", "sub-04"
    }
    assert {int(row["label_count"]) for row in subject_rows} == {32}
    assert {int(row["n_participants"]) for row in aggregate_rows} == {4}
    assert {int(row["n_participants"]) for row in cohort_rows} == {4}
    for filename in (
        "clean_reference_dice.png", "mean_volume_drift.png", "public_qc_contact_sheet.png"
    ):
        path = ROOT / "figures/public" / filename
        assert path.is_file()
        assert path.stat().st_size > 0
