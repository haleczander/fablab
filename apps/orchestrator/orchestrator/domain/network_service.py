from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from orchestrator.application.ports import ArpNeighborScannerPort, DeviceProberPort
from orchestrator.domain.models import Device, DeviceParams, DeviceType, IpAddress, MacAddress, Network
from orchestrator.shared.autowired import autowired


class NetworkDiscoveryService:
    arp_scanner: ArpNeighborScannerPort = autowired()
    device_prober: DeviceProberPort = autowired()

    def __init__(
        self,
        arp_scanner: ArpNeighborScannerPort | None = None,
        device_prober: DeviceProberPort | None = None,
    ) -> None:
        if arp_scanner is not None:
            self.arp_scanner = arp_scanner
        if device_prober is not None:
            self.device_prober = device_prober

    def discover(
        self,
        network: Network,
        timeout_s: float,
    ) -> list[Device]:
        arp_table = self.arp_scanner.scan(
            network=network.range.network_address,
            subnet_mask=network.range.subnet_mask,
            timeout_s=timeout_s,
        )

        discovered: list[Device] = []
        for ip, mac in arp_table.items():
            parsed_ip = IpAddress.parse(ip)
            parsed_mac = MacAddress.parse(mac)
            if parsed_ip and parsed_mac and network.range.contains(parsed_ip):
                discovered.append(
                    Device(
                        mac=parsed_mac,
                        ip=parsed_ip,
                        type=DeviceType.ARP_NEIGHBOR,
                        params=DeviceParams(status="ON"),
                    )
                )
        return discovered

    def probe(self, devices: list[Device], timeout_s: float) -> list[Device]:
        candidates = [device for device in devices if device.ip is not None]
        with ThreadPoolExecutor(max_workers=min(64, len(candidates) or 1)) as pool:
            futures = {
                pool.submit(self.device_prober.probe, str(device.ip), timeout_s): device
                for device in candidates
            }
            for future in as_completed(futures):
                device = futures[future]
                try:
                    probe = future.result()
                except Exception:
                    probe = None
                if probe and probe.reachable:
                    device.type = DeviceType.from_detected_adapter(probe.adapter_name)
                    device.serial = probe.serial_hint or device.serial
                    device.model = probe.model_hint or device.model
                else:
                    device.type = DeviceType.ARP_NEIGHBOR
                device.params.status = "ON"
        return devices

    def merge(self, network: Network, discovered: list[Device]) -> Network:
        merged = Network(range=network.range, devices=list(network.devices))
        for candidate in discovered:
            existing = merged.device_by_mac(candidate.mac) if candidate.mac else None
            if existing:
                existing.update_ip(candidate.ip)
                existing.type = candidate.type
                existing.serial = candidate.serial or existing.serial
                existing.model = candidate.model or existing.model
                existing.update_params(candidate.params)
                continue
            merged.merge_device(candidate)
        return merged
