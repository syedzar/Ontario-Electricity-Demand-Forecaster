// Power Query (M) steps to load and type bi/forecast_results.csv.
//
// In Power BI Desktop: Home > Get data > Blank query, then Home > Advanced Editor,
// replace everything with this file's contents, and rename the query to Forecast.
let
    // Change this to where the repo lives on your machine.
    FilePath = "C:\workspace\ontario-demand-forecaster\bi\forecast_results.csv",

    // 65001 = UTF-8.
    Source = Csv.Document(
        File.Contents(FilePath),
        [Delimiter = ",", Columns = 14, Encoding = 65001, QuoteStyle = QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // "en-US" so the numbers parse the same way whatever the PC's regional settings are.
    // The two error columns are fractions (0.034 = 3.4%), hence Percentage.Type.
    Typed = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"timestamp", type datetime},
            {"actual_mw", type number},
            {"predicted_mw", type number},
            {"baseline_mw", type number},
            {"abs_error_mw", type number},
            {"baseline_abs_error_mw", type number},
            {"abs_pct_error", Percentage.Type},
            {"baseline_abs_pct_error", Percentage.Type},
            {"hour", Int64.Type},
            {"month", Int64.Type},
            {"weekday", type text},
            {"temperature_c", type number},
            {"heating_degrees", type number},
            {"cooling_degrees", type number}
        },
        "en-US"
    ),

    // A plain date for the slicer, and a short month name for the heatmap's columns.
    AddedDate = Table.AddColumn(Typed, "date", each DateTime.Date([timestamp]), type date),
    AddedMonthName = Table.AddColumn(
        AddedDate, "month_name", each Date.ToText([date], "MMM", "en-US"), type text
    )
in
    AddedMonthName
