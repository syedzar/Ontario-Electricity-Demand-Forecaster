# Building the Power BI report

A click-by-click guide for Power BI Desktop on Windows. It takes about 20 minutes and
produces one page with KPI cards, an actual vs predicted line chart with a date slicer,
and an hour-by-month error heatmap.

There is no `.pbix` file in this repo. Power BI Desktop has to create it, so this guide
and the two files next to it (`power_query.m`, `measures.dax`) are everything needed to
build one. Menu names can move between Power BI versions; if a label is not where the
guide says, search for it in the ribbon's search box.

## Before you start

1. Install Power BI Desktop (free) from the Microsoft Store.
2. Make sure `bi/forecast_results.csv` exists. It is committed to the repo; to rebuild
   it, run `python export_for_bi.py` from the project folder.

## 1. Load the data

1. Open Power BI Desktop and choose **Blank report**.
2. **Home > Get data > Blank query**. The Power Query Editor opens.
3. **Home > Advanced Editor**. Delete what is there and paste in all of `power_query.m`.
4. On the `FilePath` line, change the path to where `forecast_results.csv` is on your PC.
   Click **Done**.
5. In **Query Settings** on the right, change **Name** from `Query1` to `Forecast`.
   The measures depend on this exact name.
6. Check the preview: 16 columns, `timestamp` showing dates and times, and
   `abs_pct_error` showing percentages.
7. **Home > Close & Apply**.

## 2. Tidy the columns

1. Open **Table view** (the grid icon on the left edge).
2. Click the `month_name` column header, then **Column tools > Sort by column > month**.
   This puts the months in calendar order instead of alphabetical.
3. Click the `hour` column, then **Column tools > Summarization > Don't summarize**.
   Do the same for `month`.

## 3. Add the measures

For each block in `measures.dax` (there are 10):

1. In the **Data** pane on the right, click the `Forecast` table.
2. **Home > New measure**.
3. Paste one block, from the measure's name to the end of its formula, and press Enter.
   The `//` comment lines can be pasted too.
4. With the measure selected, set the format in **Measure tools** to what the comment
   above it says (Percentage with 2 decimals, or Whole number).

## 4. Build the page

Go back to **Report view** (the chart icon on the left edge).

### KPI cards

1. Click an empty part of the canvas, then click **Card** in the **Visualizations** pane.
2. Drag the measure `Avg Abs Error %` onto the card.
3. Repeat for `Baseline Avg Abs Error %`, `Improvement vs Baseline %`, and
   `Peak-Error Hour`, so there are four cards in a row along the top.
4. Optional: add a fifth card with `Hours Tested`.

### Date slicer

1. Click an empty part of the canvas, then click **Slicer**.
2. Drag the `date` column onto it.
3. With the slicer selected, **Format visual > Slicer settings > Options > Style > Between**.

### Line chart: actual vs predicted

1. Click an empty part of the canvas, then click **Line chart**.
2. Drag `timestamp` to **X-axis**. Power BI turns it into a Year/Quarter/Month/Day
   hierarchy; click the small arrow next to `timestamp` in the X-axis box and choose
   **timestamp** instead of **Date Hierarchy**, so each hour is its own point.
3. Drag the measures `Actual MW` and `Predicted MW` to **Y-axis**.
4. Optional: **Format visual > Lines**, pick `Predicted MW` and set its style to dashed.
5. Set the slicer to 21 Jun 2025 to 27 Jun 2025 to see the peak-demand week.

### Heatmap: error by hour and month

1. Click an empty part of the canvas, then click **Matrix**.
2. Drag `hour` to **Rows**, `month_name` to **Columns**, and the measure
   `Avg Abs Error %` to **Values**.
3. **Format visual > Cell elements**, choose the series `Avg Abs Error %`, and turn on
   **Background color**. Click the **fx** button next to it, set **Format style** to
   **Gradient**, pick a light colour for the lowest value and a dark one for the
   highest, and click **OK**.
4. **Format visual > Row subtotals** off, and **Column subtotals** off.

Save the report as `bi/power_bi/forecast_report.pbix`.

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

## After you build it

Take a screenshot of the finished page, save it as `docs/images/powerbi-dashboard.png`,
and replace the placeholder line in the README's "BI reporting" section with the image.
