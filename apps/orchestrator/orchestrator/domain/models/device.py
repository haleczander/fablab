from __future__ import annotations

from dataclasses import dataclass, field

from orchestrator.domain.models.device_params import DeviceParams
from orchestrator.domain.models.device_type import DeviceType
from orchestrator.domain.models.ip_address import IpAddress
from orchestrator.domain.models.mac_address import MacAddress


@dataclass
class Device:
    mac: MacAddress | None = None
    ip: IpAddress | None = None
    business_id: str | None = None
    ignored: bool = False
    type: DeviceType = DeviceType.UNKNOWN
    params: DeviceParams = field(default_factory=DeviceParams)
    serial: str | None = None
    model: str | None = None

    def bind(self, business_id: str) -> None:
        self.business_id = business_id
        self.ignored = False

    def unbind(self) -> None:
        self.business_id = None

    def ignore(self) -> None:
        self.ignored = True

    def unignore(self) -> None:
        self.ignored = False

    def update_ip(self, ip: IpAddress | None) -> None:
        if ip is not None:
            self.ip = ip

    def update_params(self, params: DeviceParams) -> None:
        self.params = params
