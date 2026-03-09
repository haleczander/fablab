from __future__ import annotations

import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class IpAddress:
    value: str

    @classmethod
    def parse(cls, value: str | None) -> "IpAddress | None":
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            ipaddress.ip_address(raw)
        except ValueError:
            return None
        return cls(raw)

    def __str__(self) -> str:
        return self.value
