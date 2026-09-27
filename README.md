# Ontario Electricity Demand Forecaster

Predicts how much electricity Ontario will use each hour, one day ahead, using
public data from Ontario's grid operator (IESO) and historical weather.

![Dashboard overview](docs/images/dashboard-overview.png)

## What it does

- Downloads hourly Ontario electricity demand (2019-2025) and hourly Toronto temperatures.
- Builds features from the calendar, holidays, past demand, and temperature.
- Trains an XGBoost model on 2019-2024 and tests it on all of 2025, a year it never saw during training.
- Compares the model against two simple guesses: "same as this hour yesterday" and "same as this hour last week".
- Shows the results in an interactive Streamlit dashboard.

## Results

Tested on 8,751 hours of 2025 data.

| Method | Average error (MAPE) | Average miss (MAE) | RMSE |
|---|---|---|---|
| XGBoost model | 3.37% | 580 MW | 761 MW |
| Guess: same hour yesterday | 4.58% | 758 MW | 1,031 MW |
| Guess: same hour last week | 7.05% | 1,197 MW | 1,673 MW |

- The model's average miss is 23% smaller than the "same as yesterday" guess.
- The most important inputs are demand at the same hour yesterday, then temperature.
- Errors are smallest overnight and largest in the afternoon, peaking around 3pm.
- July is the hardest month to predict and May is the easiest.

The chart below shows the highest-demand week of 2025, during a late-June heat wave.
The model follows the daily pattern closely but underestimates the highest peaks.
The "same as yesterday" guess falls apart when the weather changes (June 26).

![Forecast vs actual](outputs/forecast_vs_actual.png)

When the model is least accurate:

![When it's hardest to predict](docs/images/dashboard-details.png)

## How to run

Requires Python 3.10 or newer. From the project folder:

```
pip install -r requirements.txt
python -m forecaster download
python -m forecaster train
python -m streamlit run app.py
```

- `download` fetches the demand and weather data into `data/`.
- `train` trains the model and saves results to `outputs/`.
- The last command opens the dashboard in your browser.

To run the tests: `python -m pytest`

To explore the data, open `notebooks/01_explore_data.ipynb`.

## How it works

- **Data:** yearly hourly demand files from IESO, and hourly temperature from the
  Open-Meteo historical weather API. IESO labels each hour by when it ends, in
  Eastern Standard Time all year, so the code converts each row to the hour it starts.
- **Day-ahead rule:** every input must be known at least 24 hours before the hour
  being predicted: demand from 24 hours, 48 hours, and one week earlier, recent
  averages, the time of day and year, weekends, holidays, and temperature. Unit tests
  check that no future data leaks into the features.
- **Time-based testing:** the model trains on 2019-2024 and is tested on 2025, rather
  than on a random split, so the test is a real forecast of unseen data.
- **Feature importance:** each input is shuffled one at a time on the test data to
  measure how much worse the predictions get without it.

## Limitations

- The model is given the actual temperature for the hour it predicts, which assumes
  a perfect weather forecast. A real day-ahead system would only have a forecast, so
  its error would be somewhat higher.
- One weather location (Toronto) stands in for the whole province.
- Results are from a single test year.

## Project structure

```
app.py                  Streamlit dashboard
forecaster/
    config.py           settings (years, test period, weather location)
    data.py             download and clean the IESO and weather data
    features.py         calendar, lag, and temperature features
    models.py           time-based split, simple guesses, XGBoost model
    evaluate.py         error scores and feature importance
    pipeline.py         the full training run
notebooks/              data exploration
tests/                  unit tests
docs/images/            screenshots used in this README
```

## Data sources

- IESO Public Reports, hourly demand: https://reports-public.ieso.ca/public/Demand/
- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
