from typing import Callable

from orchestrator.application.dependencies import autowired, discovery_rows_builder as get_discovery_rows_builder
from orchestrator.application.ports import DiscoverySnapshotPort, PrinterBindingPersistencePort
from orchestrator.domain.models import Network, NetworkRange
from orchestrator.domain.network_service import NetworkDiscoveryService
from orchestrator.domain.services import OrchestratorDomainService


class RefreshNetworkDiscoveryUseCase:
    binding_repo: PrinterBindingPersistencePort = autowired()
    network_service: NetworkDiscoveryService = autowired()
    discovery_snapshot: DiscoverySnapshotPort = autowired()
    domain_service: OrchestratorDomainService = autowired()

    def execute(self, cidr: str, timeout_s: float) -> int:
        network = Network(range=NetworkRange.parse(cidr))
        for binding in self.binding_repo.list_all():
            network.merge_device(self.domain_service.device_from_binding(binding))

        discovered = self.network_service.discover(
            network=network,
            timeout_s=timeout_s,
        )
        merged = self.network_service.merge(network, discovered)
        self.network_service.probe(merged.devices, timeout_s=timeout_s)
        self.discovery_snapshot.replace_rows(get_discovery_rows_builder()(merged))
        return len(merged.devices)
