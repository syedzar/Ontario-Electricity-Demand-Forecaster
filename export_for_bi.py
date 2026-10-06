"""Export the test-set predictions for Excel and Power BI.

    python export_for_bi.py

Reads outputs/predictions.csv (written by `python -m forecaster train`) and writes:

    bi/forecast_results.csv     one row per test hour, the table Power BI loads
    bi/forecast_results.xlsx    the same rows as an Excel Table, plus Summary,
                                Heatmap and Peak week sheets

Every number on the Summary and Heatmap sheets is a live Excel formula over the
Data sheet's table, so the workbook recalculates if the data changes.
"""

from __future__ import annotations

import calendar
from pathlib import Path

import pandas as pd
import xlsxwriter

from forecaster import config
from forecaster.features import add_weather_features

BI_DIR = config.ROOT / "bi"
CSV_NAME = "forecast_results.csv"
XLSX_NAME = "forecast_results.xlsx"

TABLE = "Forecast"                  # name of the Excel Table on the Data sheet
BASELINE = "pred_naive_yesterday"   # the baseline the README headline compares against

# Columns that must be filled in on every row.
REQUIRED = ["actual_mw", "predicted_mw", "baseline_mw", "abs_error_mw", "baseline_abs_error_mw",
            "abs_pct_error", "baseline_abs_pct_error", "hour", "month", "weekday"]

# Same colours as the Streamlit dashboard.
BLUE = "#2a78d6"
INK = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#ecebe7"
HEADER_BG = "#f3f2ef"
HEAT_LOW, HEAT_HIGH = "#fff5eb", "#d94801"

# Summary sheet layout (1-based Excel rows). Columns: A key, B label, C hours,
# D model % error, E baseline % error, F improvement, G model miss in MW.
MONTH_ROW = 19      # first of 12 month rows
HOUR_ROW = 34       # first of 24 hour rows
# Heatmap sheet layout: month numbers in row 5 (B..M), hours in column A.
HEAT_MONTH_ROW = 5
HEAT_ROW = 6        # first of 24 hour rows


def hour_label(h: int) -> str:
    return {0: "12am", 12: "12pm"}.get(h, f"{h % 12}{'am' if h < 12 else 'pm'}")


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------
def load_predictions(outputs: Path | None = None) -> pd.DataFrame:
    path = (outputs or config.OUTPUTS) / "predictions.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `python -m forecaster train` first.")
    return pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")


def build_results(preds: pd.DataFrame, target: str = config.TARGET) -> pd.DataFrame:
    """One row per predicted hour. Percentage errors are fractions (0.034 = 3.4%),
    which is what Excel and Power BI percentage formats expect."""
    out = pd.DataFrame(index=preds.index.rename("timestamp"))
    out["actual_mw"] = preds[target]
    out["predicted_mw"] = preds["pred_xgboost"]
    out["baseline_mw"] = preds[BASELINE]
    out["abs_error_mw"] = (out["predicted_mw"] - out["actual_mw"]).abs()
    out["baseline_abs_error_mw"] = (out["baseline_mw"] - out["actual_mw"]).abs()
    out["abs_pct_error"] = out["abs_error_mw"] / out["actual_mw"]
    out["baseline_abs_pct_error"] = out["baseline_abs_error_mw"] / out["actual_mw"]
    out["hour"] = out.index.hour              # hour beginning, EST (see forecaster/data.py)
    out["month"] = out.index.month
    out["weekday"] = out.index.day_name()
    if "temperature_c" in preds.columns:
        weather = add_weather_features(preds[["temperature_c"]])
        for col in ("temperature_c", "heating_degrees", "cooling_degrees"):
            out[col] = weather[col]

    # Round so the CSV and the workbook hold exactly the same numbers.
    mw = [c for c in out.columns if c.endswith("_mw")]
    pct = [c for c in out.columns if c.endswith("_pct_error")]
    out[mw] = out[mw].round(3)
    out[pct] = out[pct].round(6)
    return out


def summarize(results: pd.DataFrame) -> dict:
    """The numbers the workbook formulas produce, computed with pandas.

    They are stored as each formula's cached result, which is what Excel shows
    before it recalculates (for example in Protected View on a downloaded file).
    """
    r = results
    model, base = r["abs_pct_error"].mean(), r["baseline_abs_pct_error"].mean()
    model_mw, base_mw = r["abs_error_mw"].mean(), r["baseline_abs_error_mw"].mean()

    def grouped(col: str, keys: range) -> pd.DataFrame:
        g = r.groupby(col)
        t = pd.DataFrame({"hours": g.size(), "model": g["abs_pct_error"].mean(),
                          "baseline": g["baseline_abs_pct_error"].mean(),
                          "model_mw": g["abs_error_mw"].mean()}).reindex(keys)
        t["hours"] = t["hours"].fillna(0).astype(int)
        t["improvement"] = (t["baseline"] - t["model"]) / t["baseline"]
        return t

    by_month, by_hour = grouped("month", range(1, 13)), grouped("hour", range(24))
    heatmap = (r.pivot_table(index="hour", columns="month", values="abs_pct_error", aggfunc="mean")
               .reindex(index=range(24), columns=range(1, 13)))
    return {
        "hours": len(r),
        "model": model, "baseline": base, "improvement": (base - model) / base,
        "model_mw": model_mw, "baseline_mw": base_mw,
        "improvement_mw": (base_mw - model_mw) / base_mw,
        "peak_hour": int(by_hour["model"].idxmax()),
        "peak_hour_mw": int(by_hour["model_mw"].idxmax()),
        "hardest_month": int(by_month["model"].idxmax()),
        "easiest_month": int(by_month["model"].idxmin()),
        "by_month": by_month, "by_hour": by_hour, "heatmap": heatmap,
    }


def peak_week(results: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Seven whole days around the highest-demand hour, clipped to the data."""
    peak_day = results["actual_mw"].idxmax().normalize()
    last_start = (results.index.max() - pd.Timedelta(days=7)).normalize()
    start = max(results.index.min().normalize(), min(peak_day - pd.Timedelta(days=3), last_start))
    return start, start + pd.Timedelta(days=7) - pd.Timedelta(hours=1)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def write_csv(results: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(path, lineterminator="\n")


def write_workbook(results: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summarize(results)
    wb = xlsxwriter.Workbook(str(path))
    # A fixed creation date keeps the file identical when the data hasn't changed.
    wb.set_properties({"title": "Ontario demand forecast results",
                       "created": results.index.max().to_pydatetime()})
    fmt = {
        "title": wb.add_format({"bold": True, "font_size": 16}),
        "note": wb.add_format({"font_color": TEXT_2, "italic": True}),
        "section": wb.add_format({"bold": True, "font_size": 12}),
        "header": wb.add_format({"bold": True, "bg_color": HEADER_BG, "bottom": 1,
                                 "align": "center", "text_wrap": True, "valign": "vcenter"}),
        "header_num": wb.add_format({"bold": True, "bg_color": HEADER_BG, "bottom": 1,
                                     "align": "right", "text_wrap": True, "valign": "vcenter"}),
        "label": wb.add_format({"align": "left"}),
        "muted": wb.add_format({"font_color": "#9a9994", "align": "center", "font_size": 9}),
        "int": wb.add_format({"num_format": "#,##0"}),
        "pct": wb.add_format({"num_format": "0.00%"}),
        "pct1": wb.add_format({"num_format": "0.0%", "align": "center"}),
        "mw": wb.add_format({"num_format": '#,##0 "MW"'}),
        "hour": wb.add_format({"num_format": '0":00"', "align": "center"}),
        "hour_value": wb.add_format({"num_format": '0":00"'}),
        "key": wb.add_format({"align": "center"}),
        "text": wb.add_format({"align": "right"}),
        "time": wb.add_format({"num_format": "yyyy-mm-dd hh:mm"}),
        "mw_col": wb.add_format({"num_format": "#,##0.0"}),
        "pct_col": wb.add_format({"num_format": "0.00%"}),
        "temp_col": wb.add_format({"num_format": "0.0"}),
    }
    # Sheets appear in this order; Summary is the one that opens.
    summary = wb.add_worksheet("Summary")
    heatmap = wb.add_worksheet("Heatmap")
    week = wb.add_worksheet("Peak week")
    data = wb.add_worksheet("Data")

    _write_data(data, results, fmt)
    _write_summary(summary, stats, fmt)
    _write_heatmap(heatmap, stats, fmt)
    _write_peak_week(wb, week, results, fmt)
    summary.activate()
    wb.close()


def _write_data(ws, results: pd.DataFrame, fmt: dict) -> None:
    flat = results.reset_index()

    def col_format(name: str):
        if name == "timestamp":
            return fmt["time"]
        if name.endswith("_mw"):
            return fmt["mw_col"]
        if name.endswith("_pct_error"):
            return fmt["pct_col"]
        if name in ("temperature_c", "heating_degrees", "cooling_degrees"):
            return fmt["temp_col"]
        return None

    columns = [{"header": c, "format": col_format(c)} for c in flat.columns]
    ws.add_table(0, 0, len(flat), len(flat.columns) - 1,
                 {"name": TABLE, "style": "Table Style Light 9", "columns": columns,
                  "data": list(flat.itertuples(index=False, name=None))})
    ws.freeze_panes(1, 1)
    for c, name in enumerate(flat.columns):
        ws.set_column(c, c, max(17, len(name) + 4))     # room for the filter button


def _formula(ws, cell: str, formula: str, cell_format, value) -> None:
    """Write a formula with its cached result (blank when there is no data)."""
    ws.write_formula(cell, formula, cell_format, "" if pd.isna(value) else value)


def _write_summary(ws, s: dict, fmt: dict) -> None:
    ws.hide_gridlines(2)
    ws.set_column("A:A", 8)
    ws.set_column("B:C", 14)
    ws.set_column("D:G", 16)
    ws.write("A1", "Forecast accuracy summary", fmt["title"])
    ws.write("A2", f"Every number on this sheet is a live formula over the {TABLE} table "
                   "on the Data sheet. Baseline = same hour yesterday.", fmt["note"])

    m0, m1 = MONTH_ROW, MONTH_ROW + 11
    h0, h1 = HOUR_ROW, HOUR_ROW + 23

    def worst(labels: str, values: str, first: int, last: int, pick: str = "MAX") -> str:
        rng = f"{values}{first}:{values}{last}"
        return f"=INDEX({labels}{first}:{labels}{last},MATCH({pick}({rng}),{rng},0))"

    ws.write("A4", "Overall", fmt["section"])
    overall = [
        ("Hours tested", f"=COUNT({TABLE}[actual_mw])", fmt["int"], s["hours"]),
        ("Average error, model", f"=AVERAGE({TABLE}[abs_pct_error])", fmt["pct"], s["model"]),
        ("Average error, baseline", f"=AVERAGE({TABLE}[baseline_abs_pct_error])", fmt["pct"],
         s["baseline"]),
        ("Improvement vs baseline (% error)", "=(D7-D6)/D7", fmt["pct"], s["improvement"]),
        ("Average miss, model", f"=AVERAGE({TABLE}[abs_error_mw])", fmt["mw"], s["model_mw"]),
        ("Average miss, baseline", f"=AVERAGE({TABLE}[baseline_abs_error_mw])", fmt["mw"],
         s["baseline_mw"]),
        ("Improvement vs baseline (MW)", "=(D10-D9)/D10", fmt["pct"], s["improvement_mw"]),
        ("Peak-error hour (by % error)", worst("A", "D", h0, h1), fmt["hour_value"], s["peak_hour"]),
        ("Peak-error hour (by MW)", worst("A", "G", h0, h1), fmt["hour_value"],
         s["peak_hour_mw"]),
        ("Hardest month (by % error)", worst("B", "D", m0, m1), fmt["text"],
         calendar.month_abbr[s["hardest_month"]]),
        ("Easiest month (by % error)", worst("B", "D", m0, m1, "MIN"), fmt["text"],
         calendar.month_abbr[s["easiest_month"]]),
    ]
    for i, (label, formula, cell_format, value) in enumerate(overall):
        row = 5 + i
        ws.merge_range(f"A{row}:C{row}", label, fmt["label"])
        _formula(ws, f"D{row}", formula, cell_format, value)

    blocks = [("By month", "Month", "month", m0, s["by_month"],
               lambda k: calendar.month_abbr[k], fmt["key"]),
              ("By hour of day (hour beginning, EST)", "Hour", "hour", h0, s["by_hour"],
               hour_label, fmt["hour"])]
    for title, key_name, column, first, table, label_of, key_format in blocks:
        ws.write(f"A{first - 2}", title, fmt["section"])
        ws.set_row(first - 2, 32)
        for c, text in enumerate([key_name, "Label", "Hours", "Avg error (model)",
                                  "Avg error (baseline)", "Improvement vs baseline",
                                  "Avg miss (model)"]):
            ws.write(first - 2, c, text, fmt["header" if c < 2 else "header_num"])
        for i, (key, t) in enumerate(table.iterrows()):
            r = first + i
            match = f"{TABLE}[{column}],$A{r}"
            ws.write(f"A{r}", key, key_format)
            ws.write(f"B{r}", label_of(key), fmt["key"])
            _formula(ws, f"C{r}", f"=COUNTIFS({match})", fmt["int"], t["hours"])
            _formula(ws, f"D{r}", f'=IFERROR(AVERAGEIFS({TABLE}[abs_pct_error],{match}),"")',
                     fmt["pct"], t["model"])
            _formula(ws, f"E{r}",
                     f'=IFERROR(AVERAGEIFS({TABLE}[baseline_abs_pct_error],{match}),"")',
                     fmt["pct"], t["baseline"])
            _formula(ws, f"F{r}", f'=IFERROR((E{r}-D{r})/E{r},"")', fmt["pct"], t["improvement"])
            _formula(ws, f"G{r}", f'=IFERROR(AVERAGEIFS({TABLE}[abs_error_mw],{match}),"")',
                     fmt["mw"], t["model_mw"])


def _write_heatmap(ws, s: dict, fmt: dict) -> None:
    ws.hide_gridlines(2)
    ws.set_column("A:A", 10)
    ws.set_column("B:M", 8)
    ws.write("A1", "Average error by hour of day and month", fmt["title"])
    ws.write("A2", "Model's average % error. Each cell is an AVERAGEIFS formula; "
                   "darker = larger error.", fmt["note"])
    ws.write("A4", "Hour", fmt["header"])
    for month in range(1, 13):
        ws.write(3, month, calendar.month_abbr[month], fmt["header"])
        ws.write(HEAT_MONTH_ROW - 1, month, month, fmt["muted"])    # the AVERAGEIFS criteria
    for hour in range(24):
        r = HEAT_ROW + hour
        ws.write(f"A{r}", hour, fmt["hour"])
        for month in range(1, 13):
            col = xlsxwriter.utility.xl_col_to_name(month)
            _formula(ws, f"{col}{r}",
                     f"=IFERROR(AVERAGEIFS({TABLE}[abs_pct_error],{TABLE}[hour],$A{r},"
                     f'{TABLE}[month],{col}${HEAT_MONTH_ROW}),"")',
                     fmt["pct1"], s["heatmap"].loc[hour, month])
    ws.conditional_format(f"B{HEAT_ROW}:M{HEAT_ROW + 23}",
                          {"type": "2_color_scale", "min_color": HEAT_LOW, "max_color": HEAT_HIGH})
    ws.freeze_panes(HEAT_MONTH_ROW, 1)


def _write_peak_week(wb, ws, results: pd.DataFrame, fmt: dict) -> None:
    ws.hide_gridlines(2)
    start, end = peak_week(results)
    rows = [i + 1 for i, t in enumerate(results.index) if start <= t <= end]   # +1 for the header
    first, last = rows[0], rows[-1]
    ws.write("A1", "Actual vs predicted demand", fmt["title"])
    ws.write("A2", f"{start:%d %b %Y} to {end:%d %b %Y}, the week of the year's highest demand. "
                   "The chart reads straight from the Data sheet.", fmt["note"])

    chart = wb.add_chart({"type": "line"})
    for name, col, line in [("Actual", "actual_mw", {"color": INK, "width": 2}),
                            ("Predicted (day ahead)", "predicted_mw",
                             {"color": BLUE, "width": 2, "dash_type": "dash"})]:
        c = results.columns.get_loc(col) + 1
        chart.add_series({"name": name, "categories": ["Data", first, 0, last, 0],
                          "values": ["Data", first, c, last, c], "line": line})
    chart.set_x_axis({"text_axis": True, "num_format": "ddd d mmm", "interval_unit": 24,
                      "interval_tick": 24, "line": {"color": GRID}})
    low = results["actual_mw"].iloc[first - 1:last].min()
    chart.set_y_axis({"name": "MW", "num_format": "#,##0", "line": {"none": True},
                      "min": int(low // 5000 * 5000),
                      "major_gridlines": {"visible": True, "line": {"color": GRID}}})
    chart.set_chartarea({"border": {"none": True}})
    chart.set_legend({"position": "bottom"})
    chart.set_title({"none": True})
    chart.set_size({"width": 1100, "height": 460})
    ws.insert_chart("A4", chart)


def export(preds: pd.DataFrame, out_dir: Path | None = None) -> pd.DataFrame:
    out_dir = out_dir or BI_DIR
    results = build_results(preds)
    missing = results[REQUIRED].isna().sum()
    if missing.any():
        raise ValueError(f"Missing values in export columns: {missing[missing > 0].to_dict()}")
    write_csv(results, out_dir / CSV_NAME)
    write_workbook(results, out_dir / XLSX_NAME)
    return results


def main() -> None:
    try:
        preds = load_predictions()
    except FileNotFoundError as exc:
        raise SystemExit(f"[export] {exc}")
    results = export(preds)
    s = summarize(results)
    print(f"[export] {len(results):,} rows written to {BI_DIR / CSV_NAME} and {XLSX_NAME}")
    print(f"[export] Average error {s['model']:.2%} vs baseline {s['baseline']:.2%} "
          f"({s['improvement']:.1%} better); average miss {s['model_mw']:,.0f} MW vs "
          f"{s['baseline_mw']:,.0f} MW ({s['improvement_mw']:.1%} better).")


if __name__ == "__main__":
    main()
