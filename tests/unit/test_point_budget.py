"""Piksel bütçesi sınırları — F4-055."""

import pytest

from sonar_analyzer.application.point_budget import PointBudgetError, points_for_width


def test_budget_scales_with_width_and_has_limits() -> None:
    assert points_for_width(1) == 64
    assert points_for_width(400) == 800
    assert points_for_width(800) == 1600
    assert points_for_width(100_000) == 20_000


@pytest.mark.parametrize("width", [0, -1])
def test_invalid_width_is_rejected(width: int) -> None:
    with pytest.raises(PointBudgetError):
        points_for_width(width)
