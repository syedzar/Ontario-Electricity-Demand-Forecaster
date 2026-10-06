# Building the Power BI report

A click-by-click guide for Power BI Desktop on Windows. It takes about 20 minutes and
produces one page with KPI cards, an actual vs predicted line chart with a date slicer,
and an hour-by-month error heatmap.

The finished report is saved next to this guide as `forecast_report.pbix`. To build it
again from scratch, this guide and the two files beside it (`power_query.m`,
`measures.dax`) are everything needed. The steps were followed in Power BI Desktop in
October 2026; menu names can move between versions, so if a label is not where the
guide says, search for it in the ribbon's search box.

## Before you start

1. Install Power BI Desktop (free) from the Microsoft Store.
2. Make sure `bi/forecast_results.csv` exists. It is committed to the repo; to rebuild
   it, run `python export_for_bi.py` from the project folder.

## 1. Load the data

1. Open Power BI Desktop and choose **Blank report**.
2. **Home > Get data > Blank query**. If a "new Get Data experience" prompt appears,
   choose **No thanks**. The Power Query Editor opens.
3. **Home > Advanced Editor**. Select all of the starter text, delete it, and paste in
   all of `power_query.m`. The editor should say "No syntax errors have been detected".
4. On the `FilePath` line, change the path to where `forecast_results.csv` is on your PC.
   Click **Done**.
5. In **Query Settings** on the right, change **Name** from `Query1` to `Forecast`.
   The measures depend on this exact name.
6. Check the preview: 16 columns, `timestamp` showing dates and times, and
   `abs_pct_error` showing percentages.
7. **Home > Close & Apply**.
8. Save the report (Ctrl+S, then **More options > Browse this device**) as
   `bi/power_bi/forecast_report.pbix`.

## 2. Tidy the columns

1. Open **Table view** (the grid icon on the left edge). The status bar should read
   "Table: Forecast (8,751 rows)".
2. Click `month_name` in the Data pane, then **Column tools > Sort by column > month**.
   This puts the months in calendar order instead of alphabetical.
3. Click `hour` in the Data pane, then **Column tools > Summarization > Don't
   summarize**. Do the same for `month`. The Σ icon beside each one disappears.

## 3. Add the measures

For each block in `measures.dax` (there are 10):

1. In the **Data** pane on the right, click the `Forecast` table.
2. **Table tools > New measure** (or **Home > New measure**). The formula bar shows
   `Measure =` already selected.
3. Paste one block, from the measure's name to the end of its formula, and press Enter.
   The `//` comment lines can be pasted too.
4. With the measure selected, set the format in **Measure tools** to what the comment
   above it says. For a percentage, click the **%** button (it gives 2 decimals). For a
   whole number, choose **Format > Whole number** and click the comma button for a
   thousands separator.

## 4. Build the page

Go back to **Report view** (the chart icon on the left edge).

### KPI cards

1. Click an empty part of the canvas, then click **Card** in the **Visualizations** pane.
2. In the Data pane, tick `Avg Abs Error %`, `Baseline Avg Abs Error %`,
   `Improvement vs Baseline %`, `Peak-Error Hour`, and `Hours Tested`, in that order.
   One card visual holds all five as a row of tiles.
3. Drag the visual's edges so it forms a wide, short band along the top.
4. `Hours Tested` shows as "9K" at first. With the card selected, go to **Format visual >
   Callout**, set **Apply settings to > Cards** to `Hours Tested`, and under **Value** set
   **Display units** to **None**. It then shows 8,751.

### Date slicer

1. Click an empty part of the canvas, then click **Slicer**.
2. Tick the `date` column. The slicer appears in "Between" style, with a start date, an
   end date, and a slider. If it shows a list instead, change it in **Format visual >
   Slicer settings > Options > Style > Between**.
3. Type dates into the two boxes to change the range.

### Line chart: actual vs predicted

1. Click an empty part of the canvas, then click **Line chart**.
2. Tick `timestamp`. Power BI turns it into a Year/Quarter/Month/Day hierarchy and draws
   a single point; click the small arrow next to `timestamp` in the X-axis box and choose
   **timestamp** instead of **Date Hierarchy**, so each hour is its own point.
3. Tick the measures `Actual MW` and `Predicted MW`. They go to **Y-axis**.
4. Optional: **Format visual > Lines**, pick `Predicted MW` and set its style to dashed.
5. With the whole year selected the chart is a dense band of 8,751 points. Set the
   slicer to 21 Jun 2025 to 27 Jun 2025 to see the peak-demand week clearly.

### Heatmap: error by hour and month

1. Click an empty part of the canvas, then click **Matrix**.
2. Tick `hour` (it goes to **Rows**), drag `month_name` to **Columns**, and tick the
   measure `Avg Abs Error %` (it goes to **Values**).
3. In the **Values** box, click the small arrow next to `Avg Abs Error %` and choose
   **Conditional formatting > Background color**. Leave **Format style** on
   **Gradient**, pick white for the lowest value and a dark colour for the highest, and
   click **OK**.
4. Leave the Total row and column on. They repeat the by-month and by-hour averages
   from the Excel Summary sheet, which makes them a useful cross-check.

Save the report with Ctrl+S.

## 5. Check your numbers

These values come from the committed `forecast_results.csv` (the 2025 test year). They
match the Summary and Heatmap sheets of `bi/forecast_results.xlsx`, where every number
is a live formula. If you retrain the model, compare against that workbook instead.

With the date slicer covering the whole year (1 Jan 2025 to 31 Dec 2025):

- [ ] `Hours Tested` shows **8,751**
- [ ] `Avg Abs Error %` shows **3.37%**
- [ ] `Baseline Avg Abs Error %` shows **4.58%**
- [ ] `Improvement vs Baseline %` shows **26.42%**
- [ ] `Peak-Error Hour` shows **12** (12pm to 1pm)
- [ ] `Avg Miss MW` shows **580**
- [ ] `Baseline Avg Miss MW` shows **758**
- [ ] `Improvement vs Baseline (MW) %` shows **23.45%**

In the matrix, with the whole year selected:

- [ ] the Total cell in the bottom right shows **3.37%**
- [ ] hour 15, Aug shows **5.73%** (the darkest cell)
- [ ] hour 20, Nov shows **1.51%** (the lightest cell)
- [ ] hour 12, Jul shows **4.46%**
- [ ] hour 0, Jan shows **2.15%**

With the date slicer set to 21 Jun 2025 to 27 Jun 2025 (the peak-demand week):

- [ ] `Hours Tested` shows **168**
- [ ] `Avg Abs Error %` shows **5.37%**
- [ ] `Baseline Avg Abs Error %` shows **10.23%**
- [ ] `Improvement vs Baseline %` shows **47.46%**
- [ ] `Peak-Error Hour` shows **17**

### Why there are two "improvement" numbers

The README says the model's average miss is 23% smaller than the baseline's. That is
measured in megawatts (`Improvement vs Baseline (MW) %`, 23.45%). Measured as a
percentage of demand instead, the improvement is 26.42% (`Improvement vs Baseline %`).
Both are correct. A miss of 500 MW is a bigger percentage at 3am, when demand is low,
than at 3pm. The same reason explains why the largest average miss in MW is at 3pm
(hour 15) but the largest average % error is at noon (hour 12).

## Screenshot

The README shows the finished page as `docs/images/powerbi-dashboard.png`. Retake it if
you change the report.
