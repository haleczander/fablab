from orchestrator.domain.models import Network
from orchestrator.infrastructure.network_discovery.cache import (
    build_rows_from_discovery,
    list_snapshot_rows,
    replace_snapshot,
)


class InMemoryDiscoverySnapshotStore:
    def list_rows(self) -> list[dict[str, str | bool | int | float | None]]:
        return list_snapshot_rows()

    def replace_rows(self, rows: list[dict[str, str | bool | int | float | None]]) -> None:
        replace_snapshot(rows)

    def replace_from_network(self, network: Network) -> None:
        replace_snapshot(build_rows_from_discovery(network))
