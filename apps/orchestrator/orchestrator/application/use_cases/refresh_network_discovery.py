from typing import Callable

from orchestrator.application.ports import DiscoverySnapshotPort, PrinterBindingRepositoryPort
from orchestrator.domain.models import Network, NetworkRange
from orchestrator.domain.network_service import NetworkDiscoveryService
from orchestrator.domain.services import OrchestratorDomainService


class RefreshNetworkDiscoveryUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        network_service: NetworkDiscoveryService,
        discovery_snapshot: DiscoverySnapshotPort,
        discovery_rows_builder: Callable[[Network], list[dict[str, str | bool | int | float | None]]],
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self._binding_repo = binding_repo
        self._network_service = network_service
        self._discovery_snapshot = discovery_snapshot
        self._discovery_rows_builder = discovery_rows_builder
        self._domain_service = domain_service or OrchestratorDomainService()

    def execute(self, cidr: str, timeout_s: float) -> int:
        network = Network(range=NetworkRange.parse(cidr))
        for binding in self._binding_repo.list_all():
            network.merge_device(self._domain_service.device_from_binding(binding))

        discovered = self._network_service.discover(
            network=network,
            timeout_s=timeout_s,
        )
        merged = self._network_service.merge(network, discovered)
        self._network_service.probe(merged.devices, timeout_s=timeout_s)
        self._discovery_snapshot.replace_rows(self._discovery_rows_builder(merged))
        return len(merged.devices)
