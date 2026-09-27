"""Downloading and cleaning the raw data.

IESO demand CSVs look like this:

    \\Hourly Demand Report,,,
    \\Created at 2026-01-31 07:30:13,,,
    \\For 2025,,,
    Date,Hour,Market Demand,Ontario Demand
    2025-01-01,1,17247,13887

"Hour" runs 1-24 and is hour-ENDING, in Eastern Standard Time all year
(IESO does not shift for daylight saving). Hour 1 = 00:00-01:00, so we
label each row with the hour it starts at.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

from . import config

IESO_TIMEZONE_NOTE = "Timestamps are hour-beginning, Eastern Standard Time (UTC-5, no DST)."


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse_ieso_demand(source: str | Path) -> pd.DataFrame:
    """Parse one IESO PUB_Demand CSV (a path, or the raw text) into a
    DataFrame indexed by hourly timestamp."""
    if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source):
        text = Path(source).read_text(encoding="utf-8-sig")
    else:
        text = source

    # Drop IESO's comment lines, which start with a backslash.
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("\\")]
    df = pd.read_csv(io.StringIO("\n".join(lines)))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    df["timestamp"] = pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"] - 1, unit="h")
    df = df.drop(columns=["date", "hour"]).set_index("timestamp").sort_index()
    return df


def load_demand(raw_dir: Path = config.DATA_RAW) -> pd.DataFrame:
    """Load and combine every downloaded PUB_Demand_*.csv."""
    files = sorted(raw_dir.glob("PUB_Demand_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No demand files in {raw_dir}. Run `python -m forecaster download` first."
        )
    df = pd.concat(parse_ieso_demand(f) for f in files)
    df = df[~df.index.duplicated(keep="last")].sort_index()

    # Put every hour on the index, even missing ones, so lag features line
    # up correctly. Missing hours stay NaN and are dropped before training.
    full_index = pd.date_range(df.index.min(), df.index.max(), freq="h")
    missing = len(full_index) - len(df)
    if missing:
        print(f"[data] {missing} missing hour(s) in the demand data (left as NaN).")
    return df.reindex(full_index).rename_axis("timestamp")


def load_weather(raw_dir: Path = config.DATA_RAW) -> pd.DataFrame | None:
    path = raw_dir / "weather_toronto.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")


def load_dataset(raw_dir: Path = config.DATA_RAW) -> pd.DataFrame:
    """Demand joined with temperature (if weather was downloaded)."""
    df = load_demand(raw_dir)
    weather = load_weather(raw_dir)
    if weather is not None:
        df = df.join(weather, how="left")
    else:
        print("[data] No weather file found; continuing without temperature features.")
    return df


# ---------------------------------------------------------------------------
# Downloading
# ---------------------------------------------------------------------------
def download_demand(start_year: int, end_year: int, force: bool = False,
                    raw_dir: Path = config.DATA_RAW) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for year in range(start_year, end_year + 1):
        dest = raw_dir / f"PUB_Demand_{year}.csv"
        if dest.exists() and not force:
            print(f"[download] {dest.name} already exists, skipping.")
            continue
        url = config.IESO_DEMAND_URL.format(year=year)
        print(f"[download] {url}")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


def download_weather(start_year: int, end_year: int, force: bool = False,
                     raw_dir: Path = config.DATA_RAW) -> None:
    """Hourly Toronto temperature from Open-Meteo's historical archive.

    Open-Meteo returns UTC by default; we shift to EST (UTC-5) so it lines
    up with IESO's clock.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / "weather_toronto.csv"
    if dest.exists() and not force:
        print(f"[download] {dest.name} already exists, skipping.")
        return

    frames = []
    for year in range(start_year, end_year + 1):
        params = {
            "latitude": config.WEATHER_LAT,
            "longitude": config.WEATHER_LON,
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "hourly": "temperature_2m",
        }
        print(f"[download] Open-Meteo temperature for {year}")
        resp = requests.get(config.OPEN_METEO_URL, params=params, timeout=60)
        resp.raise_for_status()
        hourly = resp.json()["hourly"]
        frames.append(pd.DataFrame({
            "timestamp": pd.to_datetime(hourly["time"]) - pd.Timedelta(hours=5),
            "temperature_c": hourly["temperature_2m"],
        }))

    weather = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp")
    weather.to_csv(dest, index=False)
    print(f"[download] Saved {len(weather)} hourly temperatures to {dest.name}")
