"""Interactive dashboard for the trained model.

    python -m streamlit run app.py

Reads the files that `python -m forecaster train` writes to outputs/.
Designed to be understood at a glance: big numbers first, one takeaway per
chart, technical detail tucked away at the bottom.
"""

import calendar
import json
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from forecaster import config

# ---- colours (one accent, everything else neutral) --------------------------
BLUE = "#2a78d6"        # the model
ORANGE = "#eb6834"      # "look here" highlight
INK = "#0b0b0b"         # real demand
MUTED = "#c9c8c3"       # baselines / non-highlighted bars
TEXT_2 = "#52514e"
GRID = "#ecebe7"
SURFACE = "#fcfcfb"

# Plain-English names, grouped so paired technical columns show up once.
FEATURE_GROUPS = {
    "lag_24h": "Yesterday's demand",
    "lag_48h": "Demand 2 days ago",
    "lag_168h": "Last week's demand",
    "rolling_mean_24h": "Recent average demand",
    "rolling_mean_168h": "Recent average demand",
    "temperature_c": "Temperature",
    "cooling_degrees": "Hot weather",
    "heating_degrees": "Cold weather",
    "hour_sin": "Time of day",
    "hour_cos": "Time of day",
    "doy_sin": "Time of year",
    "doy_cos": "Time of year",
    "month": "Time of year",
    "day_of_week": "Day of the week",
    "is_weekend": "Day of the week",
    "is_holiday": "Holidays",
}


def hour_label(h: int) -> str:
    return {0: "12am", 12: "12pm"}.get(h, f"{h % 12}{'am' if h < 12 else 'pm'}")


def style(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=70, r=16, t=8, b=40),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="Source Sans Pro, Arial, sans-serif", size=14, color=TEXT_2),
        showlegend=False, hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="", zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, ticks="", automargin=True)
    return fig


def card(value: str, label: str, color: str = INK) -> str:
    return (f"<div style='background:#f3f2ef;border-radius:12px;padding:20px 22px;min-height:146px;'>"
            f"<div style='font-size:48px;font-weight:700;line-height:1.05;color:{color};'>{value}</div>"
            f"<div style='font-size:15px;color:{TEXT_2};margin-top:6px;'>{label}</div></div>")


# ---- page -------------------------------------------------------------------
st.set_page_config(page_title="Ontario Demand Forecaster", page_icon="⚡", layout="wide")
st.markdown("<style>.block-container{padding-top:2.2rem;max-width:1200px}</style>",
            unsafe_allow_html=True)
st.title("⚡ Ontario Electricity Demand Forecaster")
st.markdown(f"<p style='font-size:19px;color:{TEXT_2};margin-top:-8px'>Predicts how much "
            "electricity Ontario will use each hour, <b>one day ahead</b>.</p>",
            unsafe_allow_html=True)

needed = ["metrics.csv", "predictions.csv", "feature_importance.csv", "run_info.json"]
if not all((config.OUTPUTS / f).exists() for f in needed):
    st.warning("No results yet. Run `python -m forecaster download` and then "
               "`python -m forecaster train`, then refresh this page.")
    st.stop()

metrics = pd.read_csv(config.OUTPUTS / "metrics.csv")
preds = pd.read_csv(config.OUTPUTS / "predictions.csv", parse_dates=["timestamp"],
                    index_col="timestamp")
importance = pd.read_csv(config.OUTPUTS / "feature_importance.csv")
info = json.loads((config.OUTPUTS / "run_info.json").read_text())
target = info["target"]

model_row = metrics[metrics["model"] == "XGBoost"].iloc[0]
naive_row = metrics[metrics["model"] == "Naive: same hour yesterday"].iloc[0]
improvement = (naive_row["MAE_MW"] - model_row["MAE_MW"]) / naive_row["MAE_MW"] * 100

# ---- 1. the headline --------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.markdown(card(f"{model_row['MAPE_pct']:.1f}%", "average error", BLUE), unsafe_allow_html=True)
c2.markdown(card(f"{improvement:.0f}%", "more accurate than guessing<br>“same as yesterday”"),
            unsafe_allow_html=True)
c3.markdown(card(f"{info['test_hours']:,}", f"hours tested that the model<br>never saw "
                 f"({preds.index.min():%Y})"), unsafe_allow_html=True)
st.write("")

# ---- 2. prediction vs reality ----------------------------------------------
st.subheader("Prediction vs reality")
first_day, last_day = preds.index.min().date(), preds.index.max().date()
peak_day = preds[target].idxmax().date()
default_start = max(first_day, peak_day - timedelta(days=3))
default_end = min(last_day, default_start + timedelta(days=7))

pick_col, _ = st.columns([1, 3])
with pick_col:
    picked = st.date_input("Dates shown", value=(default_start, default_end),
                           min_value=first_day, max_value=last_day,
                           help="Opens on the week with the highest demand of the year.")
if isinstance(picked, (tuple, list)) and len(picked) == 2:
    start, end = picked
else:  # Streamlit briefly returns only the start date while a range is being picked
    start = picked[0] if isinstance(picked, (tuple, list)) and picked else picked
    start = start if isinstance(start, date) else default_start
    end = min(last_day, start + timedelta(days=7))

window = preds.loc[str(start):str(end)]
fig = go.Figure()
fig.add_trace(go.Scatter(x=window.index, y=window[target], name="Real",
                         line=dict(color=INK, width=2),
                         hovertemplate="Real: %{y:,.0f} MW<extra></extra>"))
fig.add_trace(go.Scatter(x=window.index, y=window["pred_xgboost"], name="Predicted",
                         line=dict(color=BLUE, width=2, dash="dash"),
                         hovertemplate="Predicted: %{y:,.0f} MW<extra></extra>"))
last = window.index[-1]
real_end, pred_end = window[target].iloc[-1], window["pred_xgboost"].iloc[-1]
for y, text, color, above in [(real_end, "Real", INK, real_end >= pred_end),
                              (pred_end, "Predicted", BLUE, pred_end > real_end)]:
    # nudge the two end labels apart so they never overlap
    fig.add_annotation(x=last, y=y, text=f"<b>{text}</b>", showarrow=False, xanchor="left",
                       xshift=6, yshift=9 if above else -9, font=dict(color=color, size=13))
style(fig, 380).update_layout(hovermode="x unified", margin=dict(l=70, r=90, t=8, b=40))
fig.update_yaxes(title_text="MW", tickformat=",")
st.plotly_chart(fig, width="stretch", theme=None)
st.caption("Solid = what really happened. Dashed = what the model predicted the day before.")

# ---- 3 + 4. vs guesses, and what it relies on -------------------------------
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Beats simple guesses")
    names = {"XGBoost": "The model", "Naive: same hour yesterday": "Guess: same as yesterday",
             "Naive: same hour last week": "Guess: same as last week"}
    comp = metrics.assign(name=metrics["model"].map(names)).sort_values("MAPE_pct",
                                                                         ascending=False)
    colors = [BLUE if m == "XGBoost" else MUTED for m in comp["model"]]
    bar = go.Figure(go.Bar(x=comp["MAPE_pct"], y=comp["name"], orientation="h",
                           marker=dict(color=colors, cornerradius=4),
                           text=[f"{v:.1f}% off" for v in comp["MAPE_pct"]],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:.2f}% average error<extra></extra>"))
    style(bar, 260).update_layout(bargap=0.45, margin=dict(l=190, r=80, t=8, b=8))
    bar.update_xaxes(visible=False)
    bar.update_yaxes(showgrid=False)
    st.plotly_chart(bar, width="stretch", theme=None)
    st.caption("Average error. Shorter bar = better.")

with right:
    st.subheader("What it pays attention to")
    grouped = (importance.assign(name=importance["feature"].map(FEATURE_GROUPS)
                                 .fillna(importance["feature"]))
               .groupby("name")["importance_mw"].max()
               .sort_values(ascending=False).head(5).iloc[::-1])
    drv = go.Figure(go.Bar(x=grouped.values, y=grouped.index, orientation="h",
                           marker=dict(color=BLUE, cornerradius=4),
                           hovertemplate="%{y}: predictions get %{x:,.0f} MW worse "
                                         "without it<extra></extra>"))
    style(drv, 260).update_layout(bargap=0.45, margin=dict(l=170, r=16, t=8, b=8))
    drv.update_xaxes(visible=False)
    drv.update_yaxes(showgrid=False)
    st.plotly_chart(drv, width="stretch", theme=None)
    st.caption("Top 5 inputs. Longer bar = the model relies on it more.")

# ---- 5. when it struggles ---------------------------------------------------
err = (preds["pred_xgboost"] - preds[target]).abs()
by_hour = err.groupby(preds.index.hour).mean()
by_month = err.groupby(preds.index.month).mean()
worst_hour, worst_month = int(by_hour.idxmax()), int(by_month.idxmax())

st.subheader("When it's hardest to predict")
a, b = st.columns(2, gap="large")
with a:
    st.markdown(f"**Time of day** · toughest around **{hour_label(worst_hour)}**")
    h = go.Figure(go.Bar(x=[hour_label(i) for i in by_hour.index], y=by_hour.values,
                         marker=dict(color=[ORANGE if i == worst_hour else MUTED
                                            for i in by_hour.index], cornerradius=3),
                         hovertemplate="%{x}: off by %{y:,.0f} MW on average<extra></extra>"))
    style(h, 240).update_layout(bargap=0.25)
    h.update_xaxes(tickvals=["12am", "6am", "12pm", "6pm"])
    h.update_yaxes(title_text="Avg miss (MW)")
    st.plotly_chart(h, width="stretch", theme=None)
with b:
    st.markdown(f"**Month** · toughest in **{calendar.month_name[worst_month]}**")
    m = go.Figure(go.Bar(x=[calendar.month_abbr[i] for i in by_month.index], y=by_month.values,
                         marker=dict(color=[ORANGE if i == worst_month else MUTED
                                            for i in by_month.index], cornerradius=3),
                         hovertemplate="%{x}: off by %{y:,.0f} MW on average<extra></extra>"))
    style(m, 240).update_layout(bargap=0.25)
    m.update_yaxes(title_text="Avg miss (MW)")
    st.plotly_chart(m, width="stretch", theme=None)

# ---- 6. details for technical readers --------------------------------------
st.write("")
with st.expander("Technical details"):
    st.markdown(
        f"""
- **Task:** day-ahead forecast of hourly Ontario demand (MW). Every input is known
  at least 24 hours before the hour being predicted.
- **Model:** XGBoost ({info.get('xgboost_trees', '?')} trees, early stopping on the last 10% of
  the training period).
- **Data:** IESO hourly demand + Toronto hourly temperature (Open-Meteo).
  Trained on {info['train_hours']:,} hours (2019-2024), tested on {info['test_hours']:,}
  unseen hours ({preds.index.min():%Y}).
- **Caveat:** uses the temperature that actually occurred, i.e. assumes a perfect
  weather forecast, so real-world error would be somewhat higher.
"""
    )
    t1, t2 = st.columns(2)
    t1.markdown("**Scores** (lower is better)")
    t1.dataframe(metrics.rename(columns={"model": "Method", "MAE_MW": "MAE (MW)",
                                         "RMSE_MW": "RMSE (MW)", "MAPE_pct": "MAPE (%)"})
                 .style.format({"MAE (MW)": "{:,.0f}", "RMSE (MW)": "{:,.0f}",
                                "MAPE (%)": "{:.2f}"}), hide_index=True)
    t2.markdown("**All inputs** (permutation importance)")
    t2.dataframe(importance.rename(columns={"feature": "Input",
                                            "importance_mw": "Error increase (MW)"})
                 .style.format({"Error increase (MW)": "{:,.1f}"}),
                 hide_index=True, height=260)
