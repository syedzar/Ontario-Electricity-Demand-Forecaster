"""End-to-end training run: load -> features -> split -> train -> score -> save."""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")  # save plots to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd

from . import config
from .data import load_dataset
from .evaluate import feature_importance, score
from .features import build_features
from .models import naive_last_week, naive_yesterday, time_split, train_xgboost


def run_training(test_start: str = config.TEST_START) -> pd.DataFrame:
    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    target = config.TARGET

    df = load_dataset()
    feats, feature_cols = build_features(df, target)
    feats["pred_naive_yesterday"] = naive_yesterday(df, target)
    feats["pred_naive_last_week"] = naive_last_week(df, target)

    # Only keep hours where the target and every input are known.
    usable = feats.dropna(subset=[target, *feature_cols,
                                  "pred_naive_yesterday", "pred_naive_last_week"])
    train, test = time_split(usable, test_start)
    if train.empty or test.empty:
        raise ValueError(f"Empty train or test set. Check your years vs TEST_START={test_start}.")
    print(f"[train] {len(train):,} training hours ({train.index.min():%Y-%m-%d} to "
          f"{train.index.max():%Y-%m-%d}), {len(test):,} test hours "
          f"({test.index.min():%Y-%m-%d} to {test.index.max():%Y-%m-%d}).")
    print(f"[train] {len(feature_cols)} features: {', '.join(feature_cols)}")

    model = train_xgboost(train[feature_cols], train[target])
    test = test.copy()
    test["pred_xgboost"] = model.predict(test[feature_cols])

    metrics = score(test[target], {
        "XGBoost": test["pred_xgboost"],
        "Naive: same hour yesterday": test["pred_naive_yesterday"],
        "Naive: same hour last week": test["pred_naive_last_week"],
    })
    importance = feature_importance(model, test[feature_cols], test[target], config.RANDOM_SEED)

    # ---- save everything the dashboard and README need -------------------
    metrics.to_csv(config.OUTPUTS / "metrics.csv", index=False)
    importance.to_csv(config.OUTPUTS / "feature_importance.csv", index=False)
    cols = [target, "pred_xgboost", "pred_naive_yesterday", "pred_naive_last_week"]
    if "temperature_c" in test.columns:
        cols.append("temperature_c")
    test[cols].to_csv(config.OUTPUTS / "predictions.csv", index_label="timestamp")
    model.save_model(config.OUTPUTS / "xgboost_model.json")
    (config.OUTPUTS / "run_info.json").write_text(json.dumps({
        "target": target,
        "test_start": test_start,
        "train_hours": len(train),
        "test_hours": len(test),
        "features": feature_cols,
        "used_weather": "temperature_c" in df.columns,
        "xgboost_trees": int(model.best_iteration + 1),
    }, indent=2))
    _plot_sample_week(test, target)

    print("\n" + metrics.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    print("\nTop 5 features:\n" + importance.head(5).to_string(index=False))
    print(f"\n[train] Outputs written to {config.OUTPUTS}")
    return metrics


def _plot_sample_week(test: pd.DataFrame, target: str) -> None:
    """Forecast vs actual for the week with the highest demand in the test set
    (the hardest, most interesting week to get right)."""
    peak = test[target].idxmax()
    week = test.loc[peak - pd.Timedelta(days=3): peak + pd.Timedelta(days=4)]
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(week.index, week[target], label="Actual", linewidth=2)
    ax.plot(week.index, week["pred_xgboost"], label="XGBoost forecast", linestyle="--")
    ax.plot(week.index, week["pred_naive_yesterday"], label="Naive (yesterday)", alpha=0.5)
    ax.set_title("Ontario demand: day-ahead forecast vs actual (peak week of test period)")
    ax.set_ylabel("MW")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.OUTPUTS / "forecast_vs_actual.png", dpi=150)
    plt.close(fig)
