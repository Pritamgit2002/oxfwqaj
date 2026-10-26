"""Command line entry point: `windsight <command>` (see `windsight --help`)."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from windsight.core.config import get_settings
from windsight.core.logging import configure_logging

logger = logging.getLogger("windsight.cli")


def _ingest(args: argparse.Namespace) -> None:
    from windsight.db.session import get_sessionmaker
    from windsight.elexon.client import ElexonClient
    from windsight.services.ingestion import IngestionService

    settings = get_settings()
    with ElexonClient(settings.elexon_base_url, settings.elexon_timeout_seconds) as client:
        service = IngestionService(get_sessionmaker(), client, settings)
        if args.start and args.end:
            results = [
                service.ingest_actuals(args.start, args.end),
                service.ingest_forecasts(args.start, args.end),
            ]
        else:
            results = service.ingest_pilot_window()
    for r in results:
        logger.info("ingested %s: %d rows", r.dataset, r.rows)


def _release(args: argparse.Namespace) -> None:
    """Deploy-time task (e.g. Heroku release phase): migrate the schema, then refresh data."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")
    _ingest(args)


def _export_openapi(args: argparse.Namespace) -> None:
    from windsight.main import create_app

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
    logger.info("wrote %s", path)


def main() -> None:
    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser(prog="windsight")
    sub = parser.add_subparsers(required=True)

    ingest = sub.add_parser("ingest", help="Load Elexon wind data (defaults to the pilot window)")
    ingest.add_argument("--start", type=datetime.fromisoformat, help="UTC ISO start (optional)")
    ingest.add_argument("--end", type=datetime.fromisoformat, help="UTC ISO end (optional)")
    ingest.set_defaults(func=_ingest)

    release = sub.add_parser("release", help="Apply migrations, then ingest the pilot window")
    release.set_defaults(func=_release, start=None, end=None)

    export = sub.add_parser("export-openapi", help="Write the OpenAPI schema to a file")
    export.add_argument("--out", default="openapi.json")
    export.set_defaults(func=_export_openapi)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
