from orchestrator.infrastructure.network_discovery.cache import list_snapshot_rows, replace_snapshot


class InMemoryDiscoverySnapshotStore:
    def list_rows(self) -> list[dict[str, str | bool | int | float | None]]:
        return list_snapshot_rows()

    def replace_rows(self, rows: list[dict[str, str | bool | int | float | None]]) -> None:
        replace_snapshot(rows)
