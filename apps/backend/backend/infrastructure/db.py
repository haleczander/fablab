from collections.abc import Generator
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel, create_engine

import backend.domain.models  # noqa: F401

from config import BACKEND_DATABASE_URL

engine = create_engine(BACKEND_DATABASE_URL, echo=False, pool_pre_ping=True)


def ensure_sqlite_directory() -> None:
    if not BACKEND_DATABASE_URL.startswith("sqlite"):
        return
    database = make_url(BACKEND_DATABASE_URL).database
    if not database or database == ":memory:":
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    ensure_sqlite_directory()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def describe_schema() -> list[dict[str, object]]:
    ensure_sqlite_directory()
    inspector = inspect(engine)
    schema: list[dict[str, object]] = []
    for table_name in sorted(inspector.get_table_names()):
        columns = []
        for column in inspector.get_columns(table_name):
            columns.append(
                {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": bool(column["nullable"]),
                    "default": column.get("default"),
                    "primary_key": bool(column.get("primary_key")),
                }
            )

        indexes = []
        for index in inspector.get_indexes(table_name):
            indexes.append(
                {
                    "name": index["name"],
                    "columns": index["column_names"],
                    "unique": bool(index.get("unique")),
                }
            )

        schema.append(
            {
                "table": table_name,
                "columns": columns,
                "indexes": indexes,
            }
        )
    return schema

