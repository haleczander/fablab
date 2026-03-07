import argparse
import json

from backend.infrastructure.db import describe_schema
from backend.infrastructure.migrations import get_current_db_revision, run_db_migrations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backend database administration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Apply Alembic migrations up to head")
    subparsers.add_parser("current", help="Show the current Alembic revision")
    subparsers.add_parser("schema", help="Print the current database schema as JSON")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "migrate":
        run_db_migrations()
        print("Database migrated to head")
        return

    if args.command == "current":
        revision = get_current_db_revision()
        print(revision or "No Alembic revision applied")
        return

    if args.command == "schema":
        print(json.dumps(describe_schema(), indent=2, default=str))
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
