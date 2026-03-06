import ipaddress
from typing import Callable

from orchestrator.application.ports import DiscoverySnapshotPort
from orchestrator.application.use_cases.discover_network_hosts import DiscoverNetworkHostsUseCase


class RefreshNetworkDiscoveryUseCase:
    def __init__(
        self,
        discover_network_hosts: DiscoverNetworkHostsUseCase,
        discovery_snapshot: DiscoverySnapshotPort,
        discovery_rows_builder: Callable[
            [dict[str, tuple[str | None, str | None, str | None, bool]], dict[str, str]],
            list[dict[str, str | bool | int | float | None]],
        ],
    ) -> None:
        self._discover_network_hosts = discover_network_hosts
        self._discovery_snapshot = discovery_snapshot
        self._discovery_rows_builder = discovery_rows_builder

    def execute(self, cidrs: list[str], timeout_s: float, max_hosts: int) -> int:
        merged_hosts: dict[str, tuple[str | None, str | None, str | None, bool]] = {}
        merged_arp: dict[str, str] = {}
        for cidr in cidrs:
            network, subnet_mask = self._split_network_and_mask(cidr)
            discovery_result = self._discover_network_hosts.execute(
                network=network,
                subnet_mask=subnet_mask,
                timeout_s=timeout_s,
                max_hosts=max_hosts,
            )
            merged_arp.update(discovery_result.arp_table)
            for ip, host in discovery_result.hosts.items():
                merged_hosts[ip] = (host.adapter_name, host.model_hint, host.serial_hint, host.reachable)

        self._discovery_snapshot.replace_rows(self._discovery_rows_builder(merged_hosts, merged_arp))
        return len(merged_hosts)

    @staticmethod
    def _split_network_and_mask(cidr: str) -> tuple[str, str]:
        network = ipaddress.ip_network(cidr, strict=False)
        return str(network.network_address), str(network.netmask)
