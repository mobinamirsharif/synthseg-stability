import numpy as np
import pytest

from scripts.generate_bias_field import apply_bias_field, make_bias_field
from scripts.generate_gaussian_noise import generate_gaussian_noise


@pytest.mark.parametrize("level,fraction", [("mild", 0.05), ("moderate", 0.10)])
def test_gaussian_noise_contract(level, fraction):
    data = np.array([[[0.0, 1.0], [2.0, 4.0]]], dtype=np.float32)
    first, sigma = generate_gaussian_noise(data, level, seed=42)
    second, second_sigma = generate_gaussian_noise(data, level, seed=42)
    assert np.array_equal(first, second)
    assert sigma == pytest.approx(fraction * np.std(data[data != 0]))
    assert second_sigma == sigma
    assert first[data == 0].tolist() == [0.0]


def test_bias_field_ranges():
    moderate = make_bias_field((5, 5, 2), "moderate")
    strong = make_bias_field((5, 5, 2), "strong")
    assert moderate.min() == pytest.approx(0.60)
    assert moderate.max() == pytest.approx(1.40)
    assert strong.min() == pytest.approx(0.45)
    assert strong.max() == pytest.approx(1.55)


@pytest.mark.parametrize("strength", ["moderate", "strong"])
def test_bias_field_preserves_zero_background(strength):
    data = np.ones((5, 5, 2), dtype=np.float32)
    data[0, 0, 0] = 0
    biased, _ = apply_bias_field(data, strength)
    assert biased[0, 0, 0] == 0
