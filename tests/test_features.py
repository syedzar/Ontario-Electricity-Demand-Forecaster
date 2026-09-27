import numpy as np
import pandas as pd

from forecaster.features import build_features
from forecaster.models import time_split


def make_frame(hours=24 * 30, with_weather=True):
    idx = pd.date_range("2024-06-01", periods=hours, freq="h")
    df = pd.DataFrame({"ontario_demand": np.arange(hours, dtype=float),
                       "market_demand": np.arange(hours, dtype=float)}, index=idx)
    if with_weather:
        df["temperature_c"] = 25.0
    return df


def test_lags_only_use_the_past():
    feats, _ = build_features(make_frame())
    t = feats.index[500]
    assert feats.loc[t, "lag_24h"] == feats.loc[t - pd.Timedelta(hours=24), "ontario_demand"]
    assert feats.loc[t, "lag_168h"] == feats.loc[t - pd.Timedelta(hours=168), "ontario_demand"]


def test_rolling_mean_excludes_the_last_24_hours():
    # Demand = row number, so the mean of hours t-47..t-24 is known exactly.
    feats, _ = build_features(make_frame())
    i = 500
    expected = np.mean(np.arange(i - 24 - 23, i - 24 + 1))
    assert feats["rolling_mean_24h"].iloc[i] == expected


def test_target_is_never_a_feature():
    _, cols = build_features(make_frame())
    assert "ontario_demand" not in cols
    assert "market_demand" not in cols


def test_canada_day_is_a_holiday():
    feats, _ = build_features(make_frame(hours=24 * 45))   # June 1 to mid-July
    assert feats.loc["2024-07-01 12:00", "is_holiday"] == 1
    assert feats.loc["2024-07-02 12:00", "is_holiday"] == 0


def test_degree_features():
    feats, cols = build_features(make_frame())
    assert feats["cooling_degrees"].iloc[0] == 7.0     # 25C vs 18C comfort point
    assert feats["heating_degrees"].iloc[0] == 0.0
    _, cols_no_weather = build_features(make_frame(with_weather=False))
    assert "cooling_degrees" in cols and "cooling_degrees" not in cols_no_weather


def test_time_split_has_no_overlap():
    train, test = time_split(make_frame(), "2024-06-20")
    assert train.index.max() < test.index.min()
    assert len(train) + len(test) == 24 * 30
