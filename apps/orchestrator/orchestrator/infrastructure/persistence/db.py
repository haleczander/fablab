from collections.abc import Generator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel, create_engine

from config import ORCH_DATABASE_URL
from orchestrator.infrastructure.persistence import models as _models  # noqa: F401

engine = create_engine(ORCH_DATABASE_URL, echo=False, pool_pre_ping=True)


def _ensure_sqlite_directory() -> None:
    if not ORCH_DATABASE_URL.startswith("sqlite"):
        return
    database = make_url(ORCH_DATABASE_URL).database
    if not database or database == ":memory:":
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)


def _needs_binding_schema_reset() -> bool:
    with engine.connect() as conn:
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='printer_bindings'")
        ).fetchone()
        if not table_exists:
            return False
        cols = conn.execute(text("PRAGMA table_info('printer_bindings')")).fetchall()
        col_names = {str(col[1]) for col in cols}
        required = {"printer_id", "printer_mac", "printer_ip", "printer_model", "is_ignored"}
        return not required.issubset(col_names)


def _reset_local_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS printer_bindings"))
        conn.execute(text("DROP TABLE IF EXISTS device_runtimes"))
        conn.execute(text("DROP TABLE IF EXISTS printer_runtimes"))


def init_db() -> None:
    _ensure_sqlite_directory()
    if ORCH_DATABASE_URL.startswith("sqlite") and _needs_binding_schema_reset():
        _reset_local_tables()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

