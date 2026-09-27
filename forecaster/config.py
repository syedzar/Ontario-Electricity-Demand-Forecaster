"""Project-wide settings. Change years, location, or the test period here."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

# IESO publishes one CSV per year of hourly demand (2002 onward).
IESO_DEMAND_URL = "https://reports-public.ieso.ca/public/Demand/PUB_Demand_{year}.csv"

# Free historical weather API, no key needed.
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# Toronto. Most of Ontario's load is in the GTA, so one weather point is a
# reasonable first approximation (see "Known limitations" in the README).
WEATHER_LAT = 43.65
WEATHER_LON = -79.38

# Years to download. 2019-2024 train the model, 2025 is held out for testing.
DEFAULT_START_YEAR = 2019
DEFAULT_END_YEAR = 2025

# Everything on/after this timestamp is the test set, never seen in training.
TEST_START = "2025-01-01"

# What we predict: "Ontario Demand" = electricity consumed inside Ontario (MW).
# ("Market Demand" also includes exports, which aren't weather-driven.)
TARGET = "ontario_demand"

# Day-ahead framing: every feature must be known at least this many hours
# before the hour being predicted. This is what keeps the forecast honest.
FORECAST_HORIZON_HOURS = 24

# Temperature (C) that splits heating vs cooling degree-hours.
COMFORT_TEMP_C = 18.0

RANDOM_SEED = 42
