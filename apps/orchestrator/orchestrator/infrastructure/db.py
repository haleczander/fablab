from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text

from config import ORCH_DATABASE_URL
from orchestrator.domain import models as _models  # noqa: F401

engine = create_engine(ORCH_DATABASE_URL, echo=False, pool_pre_ping=True)


def _needs_binding_schema_reset() -> bool:
    with engine.connect() as conn:
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='printer_bindings'")
        ).fetchone()
        if not table_exists:
            return False
        cols = conn.execute(text("PRAGMA table_info('printer_bindings')")).fetchall()
        col_names = {str(col[1]) for col in cols}
        required = {"printer_id", "printer_ip", "printer_mac", "printer_serial", "printer_model", "adapter_name"}
        return not required.issubset(col_names)


def _needs_device_schema_reset() -> bool:
    with engine.connect() as conn:
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='device_runtimes'")
        ).fetchone()
        if not table_exists:
            return False
        cols = conn.execute(text("PRAGMA table_info('device_runtimes')")).fetchall()
        col_names = {str(col[1]) for col in cols}
        required = {
            "device_ip",
            "device_mac",
            "device_serial",
            "is_bound",
            "bound_printer_id",
            "detected_model",
            "detected_adapter",
            "probe_reachable",
            "last_printer_serial",
        }
        return not required.issubset(col_names)


def _needs_printer_runtime_schema_reset() -> bool:
    with engine.connect() as conn:
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='printer_runtimes'")
        ).fetchone()
        if not table_exists:
            return False
        cols = conn.execute(text("PRAGMA table_info('printer_runtimes')")).fetchall()
        col_names = {str(col[1]) for col in cols}
        required = {"printer_id", "last_printer_ip", "last_printer_mac", "last_printer_serial"}
        return not required.issubset(col_names)


def _reset_local_tables() -> None:
    # Local persistence is intentionally lightweight: reset is acceptable when schema changes.
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS printer_bindings"))
        conn.execute(text("DROP TABLE IF EXISTS printer_runtimes"))
        conn.execute(text("DROP TABLE IF EXISTS device_runtimes"))


def init_db() -> None:
    if ORCH_DATABASE_URL.startswith("sqlite") and (
        _needs_binding_schema_reset() or _needs_device_schema_reset() or _needs_printer_runtime_schema_reset()
    ):
        _reset_local_tables()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

