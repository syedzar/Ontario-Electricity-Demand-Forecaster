"""Command line entry point.

    python -m forecaster download        # fetch IESO demand + weather
    python -m forecaster train           # train, evaluate, save outputs
"""

import argparse

from . import config


def main() -> None:
    parser = argparse.ArgumentParser(prog="forecaster",
                                     description="Ontario electricity demand forecaster")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="Download IESO demand and weather data")
    dl.add_argument("--start-year", type=int, default=config.DEFAULT_START_YEAR)
    dl.add_argument("--end-year", type=int, default=config.DEFAULT_END_YEAR)
    dl.add_argument("--no-weather", action="store_true", help="Skip the temperature download")
    dl.add_argument("--force", action="store_true", help="Re-download files that already exist")

    tr = sub.add_parser("train", help="Train the model and write results to outputs/")
    tr.add_argument("--test-start", default=config.TEST_START,
                    help="First timestamp of the held-out test period (default: %(default)s)")

    args = parser.parse_args()

    if args.command == "download":
        from .data import download_demand, download_weather
        download_demand(args.start_year, args.end_year, force=args.force)
        if not args.no_weather:
            try:
                download_weather(args.start_year, args.end_year, force=args.force)
            except Exception as exc:  # weather is optional; don't block the project on it
                print(f"[download] Weather download failed ({exc}). "
                      "You can still train without temperature features.")
    elif args.command == "train":
        from .pipeline import run_training
        try:
            run_training(args.test_start)
        except FileNotFoundError as exc:
            raise SystemExit(f"[train] {exc}")


if __name__ == "__main__":
    main()
