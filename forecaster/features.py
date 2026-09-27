"""Turning timestamps and history into model inputs.

Rule for every feature here: it must be something you would actually know
24 hours before the hour you're predicting (config.FORECAST_HORIZON_HOURS).
Using demand from 1 hour ago would make the numbers look great but
wouldn't be a real day-ahead forecast.
"""

from __future__ import annotations

import holidays
import numpy as np
import pandas as pd

from . import config


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    idx = out.index
    out["hour"] = idx.hour
    out["day_of_week"] = idx.dayofweek          # 0 = Monday
    out["month"] = idx.month
    out["day_of_year"] = idx.dayofyear
    out["is_weekend"] = (idx.dayofweek >= 5).astype(int)

    on_holidays = holidays.CA(subdiv="ON", years=range(idx.year.min(), idx.year.max() + 1))
    out["is_holiday"] = pd.Index(idx.date).isin(list(on_holidays.keys())).astype(int)

    # Cyclical encodings so the model knows 23:00 is next to 00:00 and
    # Dec 31 is next to Jan 1.
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["doy_sin"] = np.sin(2 * np.pi * out["day_of_year"] / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * out["day_of_year"] / 365.25)
    return out


def add_lag_features(df: pd.DataFrame, target: str = config.TARGET,
                     horizon: int = config.FORECAST_HORIZON_HOURS) -> pd.DataFrame:
    """Past demand, only from at least `horizon` hours ago."""
    out = df.copy()
    y = out[target]
    for lag in (horizon, horizon * 2, 168):               # yesterday, 2 days ago, last week
        out[f"lag_{lag}h"] = y.shift(lag)
    known = y.shift(horizon)                               # latest value we'd know
    out["rolling_mean_24h"] = known.rolling(24, min_periods=18).mean()
    out["rolling_mean_168h"] = known.rolling(168, min_periods=120).mean()
    return out


def add_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """Temperature features. NOTE: this uses the *observed* temperature for
    the hour being predicted, i.e. it assumes a perfect weather forecast.
    See README > Known limitations."""
    if "temperature_c" not in df.columns:
        return df
    out = df.copy()
    t = out["temperature_c"]
    out["heating_degrees"] = (config.COMFORT_TEMP_C - t).clip(lower=0)
    out["cooling_degrees"] = (t - config.COMFORT_TEMP_C).clip(lower=0)
    return out


def build_features(df: pd.DataFrame, target: str = config.TARGET) -> tuple[pd.DataFrame, list[str]]:
    """Return the feature table and the list of feature column names."""
    out = add_weather_features(add_lag_features(add_calendar_features(df), target))
    excluded = {target, "market_demand", "hour", "day_of_year"}   # raw hour/doy replaced by sin/cos
    feature_cols = [c for c in out.columns if c not in excluded]
    return out, feature_cols
