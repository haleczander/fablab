from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from orchestrator.domain.models.ip_address import IpAddress


@dataclass(frozen=True)
class NetworkRange:
    cidr: str

    @classmethod
    def parse(cls, value: str) -> "NetworkRange":
        network = ipaddress.ip_network(value, strict=False)
        return cls(str(network))

    @classmethod
    def from_network_and_mask(cls, network: str, subnet_mask: str) -> "NetworkRange | None":
        net_raw = str(network or "").strip()
        mask_raw = str(subnet_mask or "").strip()
        if not net_raw or not mask_raw:
            return None
        if mask_raw.startswith("/"):
            mask_raw = mask_raw[1:]
        try:
            return cls.parse(f"{net_raw}/{mask_raw}")
        except ValueError:
            return None

    @property
    def network_address(self) -> str:
        return str(ipaddress.ip_network(self.cidr, strict=False).network_address)

    @property
    def subnet_mask(self) -> str:
        return str(ipaddress.ip_network(self.cidr, strict=False).netmask)

    def contains(self, ip: IpAddress | None) -> bool:
        if ip is None:
            return False
        return ipaddress.ip_address(str(ip)) in ipaddress.ip_network(self.cidr, strict=False)
