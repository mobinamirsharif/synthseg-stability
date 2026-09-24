import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

def read_rows(relative_path):
    with (ROOT / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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
    for filename in ("clean_reference_dice.png", "mean_volume_drift.png"):
        path = ROOT / "figures/public" / filename
        assert path.is_file()
        assert path.stat().st_size > 0
