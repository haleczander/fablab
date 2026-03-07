from __future__ import annotations

from enum import StrEnum


class DeviceType(StrEnum):
    PRUSALINK = "prusalink"
    ARP_NEIGHBOR = "arp-neighbor"
    HTTP_UNKNOWN = "http-unknown"
    UNKNOWN = "unknown"

    @classmethod
    def from_detected_adapter(cls, value: str | None) -> "DeviceType":
        normalized = str(value or "").strip().lower()
        if normalized == cls.PRUSALINK:
            return cls.PRUSALINK
        if normalized == cls.ARP_NEIGHBOR:
            return cls.ARP_NEIGHBOR
        if normalized == cls.HTTP_UNKNOWN:
            return cls.HTTP_UNKNOWN
        return cls.UNKNOWN
