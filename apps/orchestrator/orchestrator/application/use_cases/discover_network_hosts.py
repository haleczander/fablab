from __future__ import annotations

import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from orchestrator.application.ports import ArpNeighborScannerPort, DeviceProberPort
from orchestrator.domain.mac import normalize_mac


@dataclass(frozen=True)
class DiscoveredHost:
    adapter_name: str | None
    model_hint: str | None
    serial_hint: str | None
    reachable: bool


@dataclass(frozen=True)
class DiscoverNetworkHostsResult:
    hosts: dict[str, DiscoveredHost]
    arp_table: dict[str, str]


class DiscoverNetworkHostsUseCase:
    def __init__(self, arp_scanner: ArpNeighborScannerPort, device_prober: DeviceProberPort) -> None:
        self._arp_scanner = arp_scanner
        self._device_prober = device_prober

    def execute(
        self,
        network: str,
        subnet_mask: str,
        timeout_s: float,
        max_hosts: int,
    ) -> DiscoverNetworkHostsResult:
        target_network = self._to_network(network, subnet_mask)
        if not target_network:
            return DiscoverNetworkHostsResult(hosts={}, arp_table={})

        arp_table = self._arp_scanner.scan(network=network, subnet_mask=subnet_mask, timeout_s=timeout_s)

        normalized_arp: dict[str, str] = {}
        for ip, mac in arp_table.items():
            normalized = normalize_mac(mac)
            if normalized and self._ip_in_network(ip, target_network):
                normalized_arp[ip] = normalized

        candidate_ips = sorted(normalized_arp.keys())
        # In some containerized networks ARP discovery can be empty.
        # Only then, use a direct host sweep fallback on the target subnet.
        if not candidate_ips:
            fallback_ips = [str(ip) for ip in target_network.hosts()]
            if max_hosts > 0:
                fallback_ips = fallback_ips[:max_hosts]
            candidate_ips = sorted(set(candidate_ips).union(fallback_ips))
            if max_hosts > 0:
                candidate_ips = candidate_ips[:max_hosts]
        elif max_hosts > 0:
            candidate_ips = candidate_ips[:max_hosts]

        hosts: dict[str, DiscoveredHost] = {}
        with ThreadPoolExecutor(max_workers=min(64, len(candidate_ips) or 1)) as pool:
            futures = {
                pool.submit(self._device_prober.probe, ip, timeout_s): ip
                for ip in candidate_ips
            }
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    probe = future.result()
                except Exception:
                    probe = None
                if probe and probe.reachable:
                    hosts[ip] = DiscoveredHost(
                        adapter_name=probe.adapter_name,
                        model_hint=probe.model_hint,
                        serial_hint=probe.serial_hint,
                        reachable=True,
                    )
                elif ip in normalized_arp:
                    hosts[ip] = DiscoveredHost(
                        adapter_name="arp-neighbor",
                        model_hint=None,
                        serial_hint=None,
                        reachable=True,
                    )
        return DiscoverNetworkHostsResult(hosts=hosts, arp_table=normalized_arp)

    @staticmethod
    def _ip_in_network(ip: str, network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return addr in network

    @staticmethod
    def _to_network(network: str, subnet_mask: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
        net_raw = str(network or "").strip()
        mask_raw = str(subnet_mask or "").strip()
        if not net_raw or not mask_raw:
            return None
        if mask_raw.startswith("/"):
            mask_raw = mask_raw[1:]
        try:
            return ipaddress.ip_network(f"{net_raw}/{mask_raw}", strict=False)
        except ValueError:
            return None
