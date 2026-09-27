import pytest

from forecaster.evaluate import mae, mape, rmse


def test_metrics_on_known_values():
    y_true = [100, 200, 300]
    y_pred = [110, 190, 330]
    assert mae(y_true, y_pred) == pytest.approx((10 + 10 + 30) / 3)
    assert rmse(y_true, y_pred) == pytest.approx(((100 + 100 + 900) / 3) ** 0.5)
    assert mape(y_true, y_pred) == pytest.approx((10 + 5 + 10) / 3)


def test_perfect_forecast_scores_zero():
    assert mae([5, 6], [5, 6]) == 0
    assert mape([5, 6], [5, 6]) == 0
