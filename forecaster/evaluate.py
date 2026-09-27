"""Scoring forecasts."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance


def mae(y_true, y_pred) -> float:
    """Mean absolute error: on average, how many MW off we are."""
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def rmse(y_true, y_pred) -> float:
    """Root mean squared error: like MAE but punishes big misses more."""
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def mape(y_true, y_pred) -> float:
    """Mean absolute percentage error: average % off."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)


def score(y_true, predictions: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for name, y_pred in predictions.items():
        rows.append({"model": name, "MAE_MW": mae(y_true, y_pred),
                     "RMSE_MW": rmse(y_true, y_pred), "MAPE_pct": mape(y_true, y_pred)})
    return pd.DataFrame(rows).sort_values("MAPE_pct").reset_index(drop=True)


def feature_importance(model, X: pd.DataFrame, y: pd.Series, seed: int = 42) -> pd.DataFrame:
    """Permutation importance on the test set: shuffle one feature at a time
    and measure how much worse the model gets. Bigger drop = more important."""
    result = permutation_importance(model, X, y, n_repeats=5, random_state=seed,
                                    scoring="neg_mean_absolute_error", n_jobs=-1)
    return (pd.DataFrame({"feature": X.columns, "importance_mw": result.importances_mean})
            .sort_values("importance_mw", ascending=False).reset_index(drop=True))
