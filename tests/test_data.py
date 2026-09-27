import pandas as pd

from forecaster.data import parse_ieso_demand

# Copied from the real header layout of IESO's PUB_Demand_2025.csv.
SAMPLE = """\\Hourly Demand Report,,,
\\Created at 2026-01-31 07:30:13,,,
\\For 2025,,,
Date,Hour,Market Demand,Ontario Demand
2025-01-01,1,17247,13887
2025-01-01,2,17355,13722
2025-01-01,24,17000,13500
"""


def test_skips_comment_lines_and_renames_columns():
    df = parse_ieso_demand(SAMPLE)
    assert list(df.columns) == ["market_demand", "ontario_demand"]
    assert len(df) == 3


def test_hour_ending_becomes_hour_beginning_timestamp():
    df = parse_ieso_demand(SAMPLE)
    # Hour 1 covers 00:00-01:00, so it's labelled 00:00.
    assert df.index[0] == pd.Timestamp("2025-01-01 00:00")
    assert df.loc[pd.Timestamp("2025-01-01 00:00"), "ontario_demand"] == 13887
    # Hour 24 is 23:00-24:00 on the same date, not the next day.
    assert df.index[-1] == pd.Timestamp("2025-01-01 23:00")
