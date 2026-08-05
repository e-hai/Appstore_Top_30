"""Command line interface."""

import argparse
import logging
import webbrowser
from datetime import date as date_type
from pathlib import Path

from . import config, dashboard, db, play_scraper, report, scraper

LOGGER = logging.getLogger(__name__)


def _parse_date(value: str) -> str:
    return date_type.fromisoformat(value).isoformat()


def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="appstore-top30",
        description="Analyze the App Store Top 30 charts by region, category, and chart type.",
    )
    parser.add_argument("--db", type=Path, default=config.DB_PATH, help="SQLite database path")
    parser.add_argument("--reports-dir", type=Path, default=config.REPORTS_DIR, help="Reports output directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch a daily snapshot")
    fetch.add_argument("-d", "--date", type=_parse_date, default=date_type.today().isoformat(), help="Snapshot date (YYYY-MM-DD)")
    fetch.add_argument("--regions", type=_csv_list, default=list(config.REGIONS.keys()), help="Comma-separated region keys")
    fetch.add_argument("--charts", type=_csv_list, default=list(config.CHART_TYPES.keys()), help="Comma-separated chart keys")
    fetch.add_argument("--top-n", type=int, default=config.TOP_N, help="Apps per chart (default 30)")

    report_parser = sub.add_parser("report", help="Generate HTML/CSV report for a date")
    report_parser.add_argument("-d", "--date", type=_parse_date, default=date_type.today().isoformat(), help="Report date (YYYY-MM-DD)")
    report_parser.add_argument("--store", choices=["app_store", "play"], default="app_store", help="Store to report on")
    report_parser.add_argument("--open", action="store_true", help="Open the HTML report in a browser")

    run = sub.add_parser("run", help="Fetch and generate the report in one step")
    run.add_argument("-d", "--date", type=_parse_date, default=date_type.today().isoformat(), help="Snapshot date (YYYY-MM-DD)")
    run.add_argument("--regions", type=_csv_list, default=list(config.REGIONS.keys()), help="Comma-separated region keys")
    run.add_argument("--charts", type=_csv_list, default=list(config.CHART_TYPES.keys()), help="Comma-separated chart keys")
    run.add_argument("--top-n", type=int, default=config.TOP_N, help="Apps per chart (default 30)")
    run.add_argument("--open", action="store_true", help="Open the HTML report in a browser")

    play = sub.add_parser("play", help="Fetch Google Play daily snapshots")
    play.add_argument("-d", "--date", type=_parse_date, default=date_type.today().isoformat(), help="Snapshot date (YYYY-MM-DD)")
    play.add_argument("--regions", type=_csv_list, default=list(config.REGIONS.keys()), help="Comma-separated region keys")
    play.add_argument("--charts", type=_csv_list, default=list(config.CHART_TYPES.keys()), help="Comma-separated chart keys")
    play.add_argument("--top-n", type=int, default=config.TOP_N, help="Apps per chart (default 30)")

    dash = sub.add_parser("dashboard", help="Start the local interactive dashboard")
    dash.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1)")
    dash.add_argument("--port", type=int, default=8000, help="Bind port (default 8000)")
    dash.add_argument("--no-open", action="store_true", help="Do not open the browser automatically")

    sub.add_parser("init", help="Initialize the database")
    return parser


def _validate(regions: list[str], charts: list[str]) -> None:
    unknown_regions = set(regions) - set(config.REGIONS.keys())
    if unknown_regions:
        raise SystemExit(f"unknown regions: {', '.join(sorted(unknown_regions))}")
    unknown_charts = set(charts) - set(config.CHART_TYPES.keys())
    if unknown_charts:
        raise SystemExit(f"unknown charts: {', '.join(sorted(unknown_charts))}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.command == "init":
        db.init_db(args.db)
        LOGGER.info("database initialized at %s", args.db)
        return 0

    if args.command == "fetch":
        _validate(args.regions, args.charts)
        stats = scraper.fetch_day(
            date=args.date,
            db_path=args.db,
            regions=args.regions,
            charts=args.charts,
            top_n=args.top_n,
        )
        LOGGER.info(
            "fetch complete: %s countries, %s/%s feeds ok, %s entries, %s snapshots saved",
            stats["countries"],
            stats["feeds_ok"],
            stats["feeds_total"],
            stats["entries_total"],
            stats["saved_snapshots"],
        )
        if stats["feeds_failed"]:
            LOGGER.warning("%s feed failures: %s", len(stats["feeds_failed"]), stats["feeds_failed"][:5])
        return 0

    if args.command == "report":
        html_path = report.generate_report(args.date, args.db, args.reports_dir, store=args.store)
        LOGGER.info("report written to %s", html_path)
        if args.open:
            webbrowser.open(html_path.as_uri())
        return 0

    if args.command == "play":
        _validate(args.regions, args.charts)
        stats = play_scraper.fetch_day(
            date=args.date,
            db_path=args.db,
            regions=args.regions,
            charts=args.charts,
            top_n=args.top_n,
        )
        LOGGER.info(
            "google play fetch complete: %s countries, %s/%s feeds ok, %s entries, %s snapshots saved",
            stats["countries"],
            stats["feeds_ok"],
            stats["feeds_total"],
            stats["entries_total"],
            stats["saved_snapshots"],
        )
        if stats["feeds_failed"]:
            LOGGER.warning("%s google play feed failures: %s", len(stats["feeds_failed"]), stats["feeds_failed"][:5])
        return 0

    if args.command == "run":
        _validate(args.regions, args.charts)
        stats = scraper.fetch_day(
            date=args.date,
            db_path=args.db,
            regions=args.regions,
            charts=args.charts,
            top_n=args.top_n,
        )
        html_path = report.generate_report(args.date, args.db, args.reports_dir)
        LOGGER.info(
            "run complete: %s entries, %s snapshots, report at %s",
            stats["entries_total"],
            stats["saved_snapshots"],
            html_path,
        )
        if args.open:
            webbrowser.open(html_path.as_uri())
        return 0

    if args.command == "dashboard":
        server = dashboard.start_dashboard(
            db_path=args.db,
            host=args.host,
            port=args.port,
            open_browser=not args.no_open,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            LOGGER.info("dashboard stopped")
        finally:
            server.server_close()
        return 0

    return 1
