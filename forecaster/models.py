"""Baselines and the main model.

Baselines matter: a fancy model is only impressive if it beats the dumb
guesses. Ours are "same hour yesterday" and "same hour last week".
"""

from __future__ import annotations

import pandas as pd
from xgboost import XGBRegressor

from . import config


def time_split(df: pd.DataFrame, test_start: str = config.TEST_START):
    """Split by time, never randomly: train on the past, test on the future.
    A random split would leak future information into training."""
    cutoff = pd.Timestamp(test_start)
    return df[df.index < cutoff], df[df.index >= cutoff]


def naive_yesterday(df: pd.DataFrame, target: str = config.TARGET) -> pd.Series:
    return df[target].shift(24)


def naive_last_week(df: pd.DataFrame, target: str = config.TARGET) -> pd.Series:
    return df[target].shift(168)


def train_xgboost(X: pd.DataFrame, y: pd.Series, validation_fraction: float = 0.1) -> XGBRegressor:
    """Train XGBoost with early stopping.

    The validation slice is the LAST 10% of the training period (still in
    time order), so early stopping never peeks at the test set.
    """
    n_val = int(len(X) * validation_fraction)
    X_tr, X_val = X.iloc[:-n_val], X.iloc[-n_val:]
    y_tr, y_val = y.iloc[:-n_val], y.iloc[-n_val:]

    model = XGBRegressor(
        n_estimators=2000,
        learning_rate=0.03,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        early_stopping_rounds=100,
        random_state=config.RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    print(f"[train] XGBoost stopped at {model.best_iteration + 1} trees.")
    return model
