import numpy as np
import pytest

from scripts.compute_macro_dice import compute_macro_dice


def test_identical_arrays_have_perfect_dice_and_32_labels():
    clean = np.arange(33, dtype=np.int32)
    macro, scores = compute_macro_dice(clean, clean.copy())
    assert macro == 1.0
    assert len(scores) == 32


def test_controlled_mismatch():
    clean = np.array([1, 1, 2, 2])
    test = np.array([1, 2, 2, 2])
    macro, scores = compute_macro_dice(clean, test, expected_label_count=2)
    assert scores[1] == pytest.approx(2 / 3)
    assert scores[2] == pytest.approx(4 / 5)
    assert macro == pytest.approx((2 / 3 + 4 / 5) / 2)


def test_background_is_excluded():
    clean = np.array([0, 0, 1])
    test = np.array([0, 1, 1])
    _, scores = compute_macro_dice(clean, test, expected_label_count=1)
    assert set(scores) == {1}
    assert scores[1] == pytest.approx(2 / 3)


def test_label_count_mismatch_fails_by_default():
    data = np.array([0, 1, 2])
    with pytest.raises(ValueError, match="Expected 32 foreground labels, found 2"):
        compute_macro_dice(data, data)


def test_label_count_mismatch_can_be_reported(capsys):
    data = np.array([0, 1, 2])
    macro, scores = compute_macro_dice(data, data, strict=False)
    assert macro == 1.0
    assert len(scores) == 2
    assert "Warning: Expected 32 foreground labels, found 2" in capsys.readouterr().out
