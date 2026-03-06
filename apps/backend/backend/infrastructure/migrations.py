from collections.abc import Callable

from sqlmodel import SQLModel

from backend.infrastructure.db import engine


MigrationFn = Callable[[], None]
MIGRATIONS: list[tuple[str, MigrationFn]] = []


def migration(version: str) -> Callable[[MigrationFn], MigrationFn]:
    def _register(fn: MigrationFn) -> MigrationFn:
        MIGRATIONS.append((version, fn))
        return fn

    return _register


def run_db_migrations() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(64) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        )
        existing = {
            row[0]
            for row in connection.exec_driver_sql("SELECT version FROM schema_migrations").fetchall()
        }

    for version, fn in MIGRATIONS:
        if version in existing:
            continue
        fn()
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO schema_migrations (version) VALUES (:version)",
                {"version": version},
            )


@migration("001_initial_schema")
def _initial_schema() -> None:
    SQLModel.metadata.create_all(engine)
