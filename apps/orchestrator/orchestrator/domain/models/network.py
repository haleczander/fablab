from __future__ import annotations

from dataclasses import dataclass, field

from orchestrator.domain.models.device import Device
from orchestrator.domain.models.ip_address import IpAddress
from orchestrator.domain.models.mac_address import MacAddress
from orchestrator.domain.models.network_range import NetworkRange


@dataclass
class Network:
    range: NetworkRange
    devices: list[Device] = field(default_factory=list)

    def merge_device(self, candidate: Device) -> None:
        for index, current in enumerate(self.devices):
            if self._same_identity(current, candidate):
                self.devices[index] = candidate
                return
        self.devices.append(candidate)

    def device_by_mac(self, mac: MacAddress | None) -> Device | None:
        if mac is None:
            return None
        for device in self.devices:
            if device.mac == mac:
                return device
        return None

    def device_by_ip(self, ip: IpAddress | None) -> Device | None:
        if ip is None:
            return None
        for device in self.devices:
            if device.ip == ip:
                return device
        return None

    @staticmethod
    def _same_identity(left: Device, right: Device) -> bool:
        if left.mac and right.mac:
            return left.mac == right.mac
        if left.ip and right.ip:
            return left.ip == right.ip
        return False
