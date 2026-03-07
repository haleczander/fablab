from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.infrastructure.db import engine, ensure_sqlite_directory
from config import BACKEND_DATABASE_URL


def _build_alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", BACKEND_DATABASE_URL.replace("%", "%%"))
    return config


def run_db_migrations() -> None:
    ensure_sqlite_directory()
    command.upgrade(_build_alembic_config(), "head")


def get_current_db_revision() -> str | None:
    ensure_sqlite_directory()
    with engine.connect() as connection:
        if not inspect(connection).has_table("alembic_version"):
            return None
        result = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    return None if result is None else str(result[0])
