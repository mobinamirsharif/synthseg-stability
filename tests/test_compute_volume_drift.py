import pytest

from scripts.compute_volume_drift import compute_volume_drifts, summarize_absolute_drifts


def test_zero_drift():
    drifts = compute_volume_drifts({"a": 100.0, "b": 50.0}, {"a": 100.0, "b": 50.0})
    assert drifts == {"a": 0.0, "b": 0.0}
    assert summarize_absolute_drifts(drifts) == {
        "count": 2, "mean": 0.0, "median": 0.0, "iqr": 0.0, "maximum": 0.0
    }


def test_known_percentage_changes_and_zero_reference():
    drifts = compute_volume_drifts(
        {"increase": 100.0, "decrease": 200.0, "zero": 0.0},
        {"increase": 110.0, "decrease": 180.0, "zero": 4.0},
    )
    assert drifts["increase"] == pytest.approx(10.0)
    assert drifts["decrease"] == pytest.approx(-10.0)
    assert "zero" not in drifts
    summary = summarize_absolute_drifts(drifts)
    assert summary["mean"] == pytest.approx(10.0)
    assert summary["median"] == pytest.approx(10.0)
    assert summary["iqr"] == pytest.approx(0.0)
    assert summary["maximum"] == pytest.approx(10.0)


def test_all_zero_references_fail_clearly():
    drifts = compute_volume_drifts({"zero": 0.0}, {"zero": 4.0})
    with pytest.raises(ValueError, match="non-zero clean reference"):
        summarize_absolute_drifts(drifts)
